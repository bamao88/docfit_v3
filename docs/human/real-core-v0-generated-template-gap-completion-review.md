# real-core-v0 生成模板差距 harness — 计划完成度审查

日期：2026-06-17
审查对象计划：`docs/plans/real-core-v0-generated-template-gap-eval-harness.md`
被审 commit 范围：`7971280..ea4d85b`（11 个 `feat(real-core)` 提交）
审查方式：**仅静态审查代码、测试、产物结构**。计划里自述的运行数字（如
`FAIL + UNKNOWN`、`PASS 103 / FAIL 148 / UNKNOWN 43`、`11 passed`）**本次未独立复跑**，
标注为「自述」。文末给出用户可自行复核的命令。

## 结论

Code X 已经**实质完成计划的阶段 1–5**：生成模板 Word 被当作被测输入，能确定性
解析成结构树，逐项和 `template_unit_contract.yaml` 比对，输出三种差距报告，并接入
e2e / coverage gate 且 gate 真正阻断。**阶段 6（Microsoft Word 页面证据）未做**，但
这在计划里本就被列为 `BLOCKED_NEEDS_LOCAL_VALIDATION`（本机 Word 不可用即阻塞），
属预期内未完成，不算缺陷。

一句话：**harness 本身做完了，且没有为了让模板阶段通过而放宽标准。** 唯一实质短板
在测试层（见单独的测试质量审查），不在功能完成度。

## 阶段逐项核对

| 阶段 | 计划要求 | 实际实现（file:line） | 判定 |
| --- | --- | --- | --- |
| 1 固定 harness 边界与命名 | CLI 明确接收 `generated_template.docx`；缺输入 → 输入层 UNKNOWN；区分标准/被测/实际/报告 | `docfit eval template-gap --school --generated-template --out`（`cli/main.py:52-59`）→ `run_template_gap_eval`（`convert/orchestrator.py:149-176`）；缺文件 → `template_generation_output_missing`(UNKNOWN)（`harness/generated_template_gap.py:124-135`） | ✅ 完成 |
| 2 确定性解析生成 Word | 从 DOCX/OOXML 解析段落/表格/页眉页脚/字段/分节/编号/样式，每节点带 Word 来源；未建模可见对象 → UNKNOWN | `harness/generated_template_inspector.py`（~1236 行）解析全部上述对象，节点带 `source_ref`（如 `word/document.xml:p[133]/field[64]`）；`template_generation_visible_object_unmodeled`(UNKNOWN)（gap.py:2098 附近） | ✅ 完成 |
| 3 标准 × 实际逐项比对 | 粒度到 unit/element/style/page/header-footer/field/numbering，逐项 PASS/FAIL/UNKNOWN | `harness/generated_template_gap.py`（~2473 行）各类别状态码齐全，含 `*_match/_mismatch/_missing/_unverified` | ✅ 完成 |
| 4 正式差距报告 | json/md/docx 三种；每个失败项含期望/实际/Word 来源/状态/下一步 | 三种报告写出（gap.py:75-77 区域，`render_template_gap_markdown` / `write_template_gap_docx`）；check_item 含 `expected`/`actual`/`evidence_refs`/`type` | ✅ 完成 |
| 5 接入 e2e + coverage gate | gap 阻断不可被 source-fact/Word-evidence 绕过；缺能力点 → UNKNOWN；real_core 阻断后仍产诊断产物但保持 blocked | e2e merge（`orchestrator.py:329-331` + `_merge_generated_template_gap` 80-94）；real_core 即使非 PASS 也不早退（`orchestrator.py:346`）；coverage `_real_core_template_gap_findings`（`coverage.py:518-628`） | ✅ 完成 |
| 6 Microsoft Word 页面证据 | 本机 Word 导出页面图片证据，manifest 绑定 DOCX hash/Word 版本/页数 | 生成模板 Word 的页面证据**未实现**；现有 Word evidence 仅覆盖既有 `final.docx` | ⏸️ 未做（计划允许的本机验证阻塞项，范围内） |

## Acceptance 块逐条对照

**SUCCESS 条件**（计划 28 行）：

- 三校都能把 `generated_template.docx` 作为被测对象 → ✅ contract 测试对三校跑通
  （`tests/contract/test_real_core_generated_template_gap.py:17-62`）。
- 生成 `generated_template_tree.json` + 三种 `template_gap_report` → ✅ 测试断言五个产物均存在（同上 31-43）。
- 报告含 `known_status`/`display_status`/`passed_count`/`failed_count`/`unknown_count`/`blocking_status`
  → ✅ 测试断言这六字段是 summary 子集（同上 50-57）；聚合逻辑 `summarize_check_items`（gap.py:204-238）。
- 坏样本不会 PASS → ⚠️ **部分**：有一个空文档负样本断言 FAIL（test 65-85），但缺「隔离变异」覆盖，见测试质量审查。
- coverage/e2e 不再把 source-fact / Word evidence binding 当模板正确性充分证明 →
  ✅ 旧 `source_facts_ok` 现仅喂 coverage 报告字典与虚拟槽（`template_parse/runner.py:118-149`），
  不再放行 stage；gap status 经 `merge_statuses` 折叠进 template stage。

**No regressions**（计划 32 行）：

- `auto_update_allowed` 仍为 false → ✅ 三校 `template_unit_contract.yaml` 第 9 行均 `false`；
  baseline 校验仍强制（`baselines.py:142-151`）。
- FAIL/UNKNOWN 不被降级、UNKNOWN 仍阻断 → ✅ `blocking_status`：FAIL+UNKNOWN→FAIL、
  PASS+UNKNOWN→UNKNOWN（gap.py:224-229）；coverage 对 FAIL/UNKNOWN 均加阻断 finding（coverage.py:613-627）。
- bootstrap 行为不变 → ✅ gap 评估仅对 `is_real_core_bundle` 触发（orchestrator.py:329），bootstrap 路径不进入。

## 计划自述「仍未完成」清单核对（计划 149-158）

以下都是**计划已明确承认的未完成项**，与 harness 完成度无关：

1. 尚未真正修正模板生成逻辑 —— 本切片只把生成 Word 当被测输入。**符合 Non-goals，正确。**
2. 页面级版面完整性、等价生成机制、脚注编号、复杂题注、复杂样式表缺项、复杂 section
   继承、更细页码规则仍有 `UNKNOWN` —— **属解析能力的渐进补全，已被 UNKNOWN 如实暴露。**
3. 生成模板 Word 的 Microsoft Word 证据未完整 —— 对应阶段 6。
4. 9 个真实成品尚未在修复后统一重生 —— 跨阶段后续工作，不在本 harness 范围。

## 完成度判定

| 维度 | 判定 |
| --- | --- |
| 功能完成度（阶段 1–5） | ✅ 实质完成 |
| 阶段 6（Word 页面证据） | ⏸️ 计划允许的本机阻塞项，未做 |
| 验收语义正确性 | ✅ 与计划两层状态模型逐行一致 |
| gate 阻断有效性 | ✅ 无逃逸口（详见代码质量审查） |
| 测试充分性 | ⚠️ 有实质缺口（详见测试质量审查） |

**总评**：Code X 没有虚报——核心 harness 确实做完且阻断语义正确。建议在宣布「本阶段
完成」前补齐测试质量审查列出的两类测试，再考虑阶段 6 的本机 Word 证据。

## 用户可自行复核命令（本次未复跑）

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py -q   # 自述 11 passed
uv run pytest tests/unit tests/contract tests/e2e -q
uv run docfit eval e2e --school hunannongye --student test_inputs/content_extraction/real-student-003-source.docx --out /tmp/probe
uv run docfit eval coverage --profile real-core-v0 --out /tmp/cov
```
