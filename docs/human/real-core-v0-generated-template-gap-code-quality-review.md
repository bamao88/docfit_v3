# real-core-v0 生成模板差距 harness — 代码质量审查

日期：2026-06-17
被审 commit 范围：`7971280..ea4d85b`
审查方式：仅静态审查。结论均带 file:line 取证，非依赖 Code X 自述。

## 结论

代码质量**整体良好**。最关键的两点——状态语义正确、gate 不可旁路——都经过逐行核实，
**没有发现逃逸口**。问题集中在可维护性（超大单文件）和一处需要人工注意的设计细节，
均为**次要项**，不阻断本阶段。

## 审查范围

- `src/docfit/harness/generated_template_gap.py`（差距检查 + 状态聚合 + 报告，~2473 行）
- `src/docfit/harness/generated_template_inspector.py`（OOXML 解析，~1236 行）
- `src/docfit/convert/orchestrator.py`（CLI 入口 + e2e 编排 + gap 合并）
- `src/docfit/harness/coverage.py`（real-core coverage gate）
- `src/docfit/stages/template_parse/runner.py`（旧 source-fact 路径）

## 正面结论（已逐行核实）

### 1. 状态语义与计划逐行一致 — ✅ 强

`summarize_check_items`（gap.py:204-238）实现计划 321-333 的两层模型，零偏差：

```
failed_count>0           → known_status = FAIL
failed_count=0,passed>0  → known_status = PASS
否则                      → known_status = UNKNOWN

known=UNKNOWN             → display = UNKNOWN
known∈{PASS,FAIL},unknown>0 → display = "<known> + UNKNOWN"

failed_count>0  → blocking = FAIL
unknown_count>0 → blocking = UNKNOWN   ← UNKNOWN 仍阻断，未降级
否则             → blocking = PASS
```

要点：`known_status` 只看 PASS/FAIL，`UNKNOWN` 不会把已证明的 PASS 盖掉；`FAIL` 是主
结论但 `unknown_count` 仍保留——完全对应计划 587-588 的要求。

### 2. gate 不可旁路 — ✅ 强（最高回归风险项，已确认改对）

证据链三处咬合：

- **gap 折叠进 template stage**：`_merge_generated_template_gap`（orchestrator.py:80-94）
  用 `merge_statuses([template, gap])` 合并，`blocked_at` 也并入。gap 的 FAIL/UNKNOWN
  无法被 template parse 的 PASS 稀释。
- **旧 source-fact 放行被拆除**：`template_parse/runner.py:118-131` 的 `source_facts_ok`
  现在**只**喂 `real_core_coverage` 字典和一个虚拟 body 槽（132-149），**不再决定 stage
  是否通过**。这正是计划要拆的旧旁路。
- **coverage 独立阻断**：`_real_core_template_gap_findings`（coverage.py:518-628）
  - 缺任一产物 → `missing_generated_template_gap_evidence`(UNKNOWN)（534-547）
  - 报告里 hash 与实际 DOCX 不符 → `generated_template_gap_hash_mismatch`(FAIL)（571-585）
  - summary 字段缺失 → `generated_template_gap_summary_incomplete`(UNKNOWN)（597-611）
  - `blocking_status ∈ {FAIL, UNKNOWN}` → `generated_template_gap_blocking`（613-627）

  即便有人手动把产物补齐，hash 绑定和 blocking_status 仍会拦住伪造或阻断中的报告。

### 3. real_core 阻断后继续产诊断产物，但保持 blocked — ✅ 正确

`orchestrator.py:346` 的早退条件是 `status != PASS and not real_core_run`：对 real_core，
模板 FAIL/UNKNOWN **不早退**，继续 content/placement/render 以产出诊断产物，但
`blocked_at: template` 经合并保留。符合计划 615 行。

### 4. 解析器来源可追溯 — ✅ 强

inspector 每个节点带 `source_ref`（段落 `p[i]`、表格 `tbl[i]/tr/tc`、字段
`p[i]/field[j]`、样式 `styles.xml:style[id]`、编号 `numbering.xml:abstractNum[id]/lvl[n]`）。
这让差距报告能把每个失败精确指回 Word 位置，是 harness 可信度的基础。

## Findings（按严重度）

| # | 严重度 | 位置 | 问题 | 建议 |
| --- | --- | --- | --- | --- |
| C-1 | 🟡 次要 | `generated_template_gap.py`（~2473 行）、`generated_template_inspector.py`（~1236 行） | 两个核心文件均为超大单文件，检查逻辑、聚合、三种报告渲染混在一处，长期可维护性与可测试性受影响 | 后续按类别（unit/style/field/numbering/page/header-footer）拆分 checker 模块，报告渲染独立成 `gap_report_render.py`。非本阶段必须 |
| C-2 | 🟡 次要 | `coverage.py:552` | `except Exception` 读 JSON 失败时返回 UNKNOWN，标了 `# pragma: no cover` | 阻断方向正确（失败→UNKNOWN，不会误放行），可接受；建议至少收窄到 `json.JSONDecodeError/OSError` 避免吞掉无关异常 |
| C-3 | 🟢 观察 | `template_parse/runner.py:118-131` | 旧 `source_facts_ok` 已降级为仅供 coverage 报告，但变量名和位置仍易让人误以为它参与放行 | 加一行注释说明「仅用于 coverage 报告，不再 gate」，或重命名，降低未来误改风险 |
| C-4 | 🟢 观察 | 跨模块 | status 字符串（`"FAIL + UNKNOWN"` 等）以拼接字面量在多处出现 | 已集中在 `summarize_check_items`，目前可控；若未来消费方增多，考虑常量化 |

> 未发现 🔴 阻断级问题。无 status 降级、无 gap 跳过、无缺证据静默放行。

## 判定

| 维度 | 判定 |
| --- | --- |
| 状态语义正确性 | ✅ 强 |
| gate 阻断有效性 / 无逃逸口 | ✅ 强 |
| 来源可追溯性 | ✅ 强 |
| 可维护性（文件体量） | 🟡 次要待改 |
| 错误处理 | 🟡 方向正确、可收窄 |

**总评**：代码可信、阻断语义扎实，可作为后续阶段的依赖。建议把 C-1 的拆分列入技术债，
C-3 的注释顺手补上；二者都不阻断本阶段验收。
