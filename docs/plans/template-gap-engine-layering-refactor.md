# 模板差距检测引擎优化计划

Status: Implemented
Created: 2026-06-17
Last reviewed: 2026-06-17

Implementation evidence:

- `uv run pytest tests/contract/test_real_core_generated_template_gap.py -q` → 17 passed.
- `uv run pytest tests/contract/test_real_core_generated_template_gap.py tests/contract/test_contract_gates.py tests/e2e/test_bootstrap_cli.py -q` → 34 passed.
- `uv run pytest tests/unit tests/contract tests/e2e -q` → 68 passed.
- 三校 `docfit eval template-gap` 使用
  `inputs/simulated-generated-templates/real-core-v0/<school_id>/generated_template.docx`
  均能产出 v2 分层报告，当前仍按真实差距和未知能力阻断为 `FAIL`。
- `uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage`
  → `status = FAIL`，没有绕过 real-core gate。
- `uv run docfit eval e2e --school hunannongye --student inputs/real-student-003-source.docx --out /tmp/docfit_real_core_e2e_hna`
  → `status = FAIL`，仍在模板问题处阻断。

Current result:

- `template_gap_report.json` 已升级为 `artifact_version: 2.0`，主结构为
  `input`、`units`、`unmodeled_objects`、`summary.per_unit`，不再公开
  `check_items`。
- real-core 自动 gap 入口已固定为虚拟业务生成模板输入；CLI 显式
  `--generated-template` 行为保持不变。
- 湖南农业 `template_generation_element_missing` 从实跑参考里的 121 降到 79；
  南农从 98 降到 55；无搜索词项改为
  `template_generation_element_uncheckable` / `UNKNOWN`。
- 北大模板中不少单元仍无法可靠定位；字段和编号的 OOXML 证据会被解析出来，
  但单元范围不可靠时保持 `UNKNOWN`，这是后续要补的定位能力，不是本轮放行项。

## 预检执行契约

```text
Preflight status: DRAFT
Task source: plan path
Canonical source: docs/plans/template-gap-engine-layering-refactor.md
Route: durable $intuitive-flow
Goal: 把 template-gap 改成只检查业务生成模板输入，报告按单元分层输出，并修掉明显的元素缺失误报。

Scope:
- 执行计划里的 C0-C5：被测对象统一、最小 PASS 夹具、分层报告树、匹配去噪、单元内匹配、coverage/e2e 回归。
- 当前仓库里没有 inputs/simulated-generated-templates/.../generated_template.docx；执行时先创建或恢复这三份“虚拟业务生成模板”输入，并在 inputs/README.md 说清它们只是当前阶段的验收尺子输入，不是 golden。
- 删除公开的 check_items 输出，迁移调用方和测试到结果树。
Non-goals: 不实现真正模板生成器；不更新 signed standards、goldens、expected snapshots；不保留旧 check_items 兼容输出；不修内容抽取、内容放置、最终渲染；不加学校硬编码补丁。
Context: must-read=docs/plans/template-gap-engine-layering-refactor.md, README.md, SPEC.md, docs/agents/bootstrap-eval-runbook.md, inputs/README.md, standards/eval_profiles/real-core-v0/cases.yaml, standards/schools/*/v1/template_unit_contract.yaml, src/docfit/harness/generated_template_gap.py, src/docfit/harness/generated_template_inspector.py, src/docfit/harness/coverage.py, src/docfit/harness/profiles.py, src/docfit/convert/orchestrator.py, tests/contract/test_real_core_generated_template_gap.py; useful=docs/human/real-core-v0-generated-template-gap-live-run-report.md, docs/human/real-core-v0-generated-template-gap-test-quality-review.md, docs/plans/template-gap-engine-optimization-guide.md; avoid-unless-needed=reports/** 页面图片证据和 out/** 生成物。

Acceptance:
- SUCCESS: 三校 real-core gap 使用 inputs/simulated-generated-templates/real-core-v0/<school_id>/generated_template.docx 或 CLI 显式传入的 generated_template.docx；template_gap_report.json 为 v2 分层树并包含 summary.per_unit；最小 PASS 夹具得到 blocking_status == PASS；单样式变异、删 required 元素、无搜索词、跨单元同文都能定点证明；湖南农业和南农误报型 element_missing 明显下降，真差距仍是 FAIL。
- BLOCKED_NEEDS_DECISION: 如果三份虚拟业务生成模板不能从仓库内资产确定性创建；如果用户要求保留旧 check_items 公开兼容层；如果需要改 signed standard/golden/expected snapshot。
- BLOCKED_NEEDS_LOCAL_VALIDATION: none。
- INTERMEDIATE_ONLY: 只有用户明确批准时，C0+C1 可作为阶段性检查点。
- No regressions: 终态只允许 PASS/FAIL/UNKNOWN，UNKNOWN 仍阻断；不自动更新标准或金标；docfit convert/e2e 不绕过阶段检查。

Verification: deterministic=uv run pytest tests/contract/test_real_core_generated_template_gap.py -q; uv run pytest tests/contract/test_real_core_generated_template_gap.py tests/contract/test_contract_gates.py tests/e2e/test_bootstrap_cli.py -q; final=uv run pytest tests/unit tests/contract tests/e2e -q; integration=uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage; product-run=三校分别运行 uv run docfit eval template-gap --school <school_id> --generated-template inputs/simulated-generated-templates/real-core-v0/<school_id>/generated_template.docx --out /tmp/docfit_gap_<school_id>，并至少运行一个 real-core e2e：uv run docfit eval e2e --school hunannongye --student inputs/real-student-003-source.docx --out /tmp/docfit_real_core_e2e_hna; local-live-manual=none; optional=对比执行前后的 template_generation_element_missing 数量。
Execution: main=主会话监督执行、保护标准/金标、按 C0-C5 分段验证；worker=none；worker-goal=none
To execute: /goal execute docs/plans/template-gap-engine-layering-refactor.md with intuitive-flow
Approval: LGTM/approve/go ahead approves; edits request revision.
```

本文档分成两部分：

- **第一部分给非研发读者**：说明为什么要改、改完会看到什么、哪些结论该怎么理解。
- **第二部分给研发执行**：按 C0-C5 写清具体文件、函数、测试和验证命令。

---

# 第一部分：非研发阅读指南

## 1. 这份计划在解决什么问题

`template-gap` 是自动检查 Word 模板是否符合学校验收标准的模块。它拿验收标准
`template_unit_contract.yaml` 对照被测的 `generated_template.docx`，输出哪里通过、哪里失败、哪里暂时无法证明。

当前管道已经能跑通，也能阻断不合格结果，但报告还不能稳定作为开发排期清单。

| 现象 | 说明 |
| --- | --- |
| 管道能跑通、能阻断 | 测试能过，三校评测仍是 `FAIL + UNKNOWN`，说明门禁没有被绕过 |
| 报告不适合作为开发清单 | 失败项平铺刷屏，很难按“封面 / 目录 / 摘要”分块阅读 |
| `element_missing` 有明显误报 | 湖南农业 121 条元素缺失里，至少约 54 条不是可靠缺失证据 |
| 测试不能证明检查器会判对 | 目前没有“全对样本必须 PASS”的测试，也没有“只改一处只失败一处”的测试 |

本计划的目标不是让三校模板立刻变绿，而是先把验收逻辑做准，让报告能可靠回答：

```text
被测 generated_template.docx 是否存在
  → 每个单元能不能定位
  → 每个单元里的元素在不在
  → 样式、分页、页眉页脚、字段、编号有没有证据
  → 失败是真差距、系统查不了，还是检查器自己判错了
```

## 2. 被测对象边界

本计划里，gap 检查只承认一种被测 Word：

```text
generated_template.docx  —— 业务生成模板
```

当前业务模板生成逻辑还没有跑通，所以先使用已经准备好的**虚拟业务生成模板**来测试验收逻辑。它的产品身份就是“当前阶段用于测试验收尺子的业务生成模板输入”。

| 学校 | 当前被测 generated_template.docx |
| --- | --- |
| 湖南农业 | `inputs/simulated-generated-templates/real-core-v0/hunannongye/generated_template.docx` |
| 南农本科 | `inputs/simulated-generated-templates/real-core-v0/nannong-undergraduate/generated_template.docx` |
| 北大研究生 | `inputs/simulated-generated-templates/real-core-v0/pku-graduate/generated_template.docx` |

后续文档、报告、评审和排期里统一使用“虚拟业务生成模板”或“业务生成模板”这个口径，不再引入第二套被测对象概念。

### 和验收标准的分工

```text
template_unit_contract.yaml     验收标准：应该长什么样
generated_template.docx         被测对象：实际长什么样
```

未来真正的模板生成逻辑跑通后，eval 链路仍然检查 `generated_template.docx`。变化的只是这个文件由生成器产出，而不是由当前虚拟模板夹具提供。

## 3. 三类结论分别代表什么

读报告时先分清三种状态：

| 状态 | 含义 | 怎么处理 |
| --- | --- | --- |
| `PASS` | 有证据，且符合标准 | 可以认为这一项过关 |
| `FAIL` | 有证据，确实不符合标准 | 这是真差距，需要修模板生成或模板内容 |
| `UNKNOWN` | 当前系统无法证明正确 | 不能算模板过错，需要补解析能力、匹配能力或证据 |

本轮要修的核心问题之一是：很多本该是 `UNKNOWN` 的“查不动”，现在被错误标成了 `FAIL`。

## 4. 当前两大问题

### 问题 A：报告像“不分章节的错题本”

验收标准是按“单元 → 元素 → 样式/分页/字段/编号”组织的，检查过程也天然有层级。但当前输出把结果压成一条平铺的 `check_items` 列表，只靠 `cover.e_005.style` 这种字符串残留归属关系。

后果：

- 人读报告时很难按单元排期。
- 匹配时容易全文搜索，把 A 单元的文字当成 B 单元的证据。
- 样式检查容易绑定到错误段落。

### 问题 B：检查规则本身产生误报

真实运行里，湖南农业约 54 条不可靠 `element_missing` 主要来自两类：

| 类型 | 数量约 | 原因 |
| --- | ---: | --- |
| 无搜索词却判 FAIL | 37 | 标准里只有描述性内容，检查器不知道搜什么，却直接判缺失 |
| 内容实际存在但搜法太糙 | 17 | 被测 Word 里有 `□`、`×××`、格式说明、点引线，普通子串匹配看不懂 |

这说明报告里有不少“检查器没看懂”被误写成“模板缺了”。

## 5. 改完以后会看到什么变化

### 5.1 被测对象口径统一

所有 gap 检查都面对 `generated_template.docx`。real-core 链路不再把其他路径混进 gap 被测入口。

报告里的 `generated_template.path` / `source_path` 应指向：

- `inputs/simulated-generated-templates/real-core-v0/<school_id>/generated_template.docx`
- 或开发者通过 CLI 显式传入的 `generated_template.docx`

### 5.2 报告按单元组织

改前：一张 200 多条的长清单。

改后：按单元分组。

```text
报告
├── 输入检查
├── 单元：封面
│   ├── 本单元是否定位
│   ├── 本单元总评与计数
│   ├── 元素：存在性、样式
│   └── 维度：分页、页眉页脚、字段、编号
├── 单元：目录
└── 总摘要：每个单元一行小结
```

### 5.3 误报型元素缺失减少

| 改动 | 效果 |
| --- | --- |
| 匹配前去掉 `□`、`×××`、格式批注、点引线 | 带占位符的文本能和标准里的正常文本对上 |
| 复合字段拆开搜 | 不要求整段一字不差 |
| 查不动的 fixed/manual_only 元素改成 UNKNOWN | 不再把检查能力边界误写成模板失败 |
| 先定位单元，再在单元范围内搜 | 减少跨单元串台 |

### 5.4 测试能证明检查器会对也会拦

新增最小 PASS 样本，证明全对时能通过。新增隔离变异测试，证明只改一处样式、删一个必填元素、遇到无搜索词、跨单元同名文本时，检查器能给出定点结论。

## 6. 五步执行总览

| 步骤 | 做什么 | 解决什么 |
| --- | --- | --- |
| C0 | 固定被测对象为 `generated_template.docx` | 避免被测对象口径混乱 |
| C1 | 建立最小 PASS 夹具 | 证明检查器正确时能 PASS |
| C2 | 报告改成分层结果树 | 让报告按单元可读、可排期 |
| C3 | 匹配去噪 + UNKNOWN 分类 | 减少误报型 `element_missing` |
| C4 | 单元范围内匹配 + 样式绑定 | 减少跨单元串台和样式错绑 |
| C5 | coverage / e2e 回归 | 确认门禁仍然正确阻断 |

关键顺序：**C1 必须先做**。没有“能 PASS”的底线测试，后续重构只能证明会失败，不能证明改对了。

## 7. 本计划明确不做什么

- 不实现真正的模板生成器。
- 不把虚拟业务生成模板签成 golden。
- 不自动更新 `template_unit_contract.yaml`。
- 不保留旧 `check_items` 兼容输出。
- 不为了减少 FAIL 而把明确违反标准的项降成 UNKNOWN。
- 不修内容抽取、内容放置、最终 Word 渲染。

## 8. 完成标准

- [x] real-core gap 检查使用 `inputs/simulated-generated-templates/.../generated_template.docx` 作为被测生成模板输入。
- [x] `template_gap_report.json` 以分层树为主结构，不再公开平铺 `check_items`。
- [x] 最小 PASS 夹具能让真实 parser → checker 链路得到 `blocking_status == PASS`。
- [x] 单样式变异、删 required 元素、无 needle 元素、跨单元同文这四类测试都能定点证明结果。
- [x] 湖南农业和南农的误报型 `element_missing` 明显减少；真差距仍为 `FAIL`。
- [x] coverage / e2e 仍按 `summary.blocking_status` 正确阻断。

---

# 第二部分：研发执行指南

## 9. Scope 与实跑证据

Scope：只优化生成模板验收逻辑，不实现真正的模板生成器，不更新 signed standard、golden 或 expected snapshot。

实跑证据：

- `uv run pytest tests/unit tests/contract tests/e2e -q` 能通过。
- 三校 `docfit eval template-gap` 都是 `FAIL + UNKNOWN`。
- 湖南农业 121 条 `template_generation_element_missing` 里，至少约 54 条不可靠：37 条无 needle 自动 FAIL，17 条 token 实际存在但匹配器看不懂。
- contract 测试没有干净 PASS 夹具，也没有隔离变异测试。

## 10. C0：统一被测对象为业务生成模板

不要再引入第二套被测对象概念。gap 的被测对象只有：

```text
generated_template.docx
```

当前阶段，三校使用 `simulated-generated-templates/` 下的虚拟业务生成模板充当该输入。

### 10.1 文件改动

| 文件 | 改动 |
| --- | --- |
| `inputs/README.md` | 新增“虚拟业务生成模板输入”一节，说明这些文件是 gap 被测对象 |
| `standards/eval_profiles/real-core-v0/cases.yaml` | 每校增加 `generated_template_docx` |
| `src/docfit/harness/profiles.py` | `EvalCase` 增加 `generated_template_docx`；`REAL_CORE_SCHOOLS` 同步 |
| `src/docfit/convert/orchestrator.py` | real-core gap 检查改用 `generated_template_docx` |

### 10.2 路径登记

`standards/eval_profiles/real-core-v0/cases.yaml` 每个学校增加：

```yaml
generated_template_docx: inputs/simulated-generated-templates/real-core-v0/<school_id>/generated_template.docx
```

`src/docfit/harness/profiles.py`：

- `EvalCase` 增加字段 `generated_template_docx: Path | None = None`。
- `REAL_CORE_SCHOOLS` 每项增加同名路径。
- `_real_core_template_cases()` 和 `_real_core_e2e_cases()` 把该路径写进 `EvalCase`。

`src/docfit/convert/orchestrator.py` 增加 helper：

```python
def _generated_template_docx_for_school(root: Path, school_id: str) -> Path | None:
    ...
```

核心替换：

```python
# 改前
evaluate_generated_template_gap(bundle, bundle.template_docx, out_dir)

# 改后
evaluate_generated_template_gap(bundle, generated_template_docx, out_dir)
```

要求：

- `run_template_eval()`：gap 用 `generated_template_docx`；`template_docx` 仍只用于模板解析等原本职责。
- `run_e2e_eval()`：real-core gap 用 `generated_template_docx`。
- `run_template_gap_eval()`：保持 `--generated-template` 显式输入不变。

### 10.3 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py::test_real_core_template_gap_outputs_tree_and_reports_for_all_schools -q

uv run docfit eval template-gap --school hunannongye \
  --generated-template inputs/simulated-generated-templates/real-core-v0/hunannongye/generated_template.docx \
  --out /tmp/docfit_gap_hna
```

完成后，`template_gap_report.json["generated_template"]["path"]` / `source_path` 不应指向 `inputs/school-*.docx`。

## 11. C1：建立最小 PASS 夹具

必须先做。否则后续重构只能证明检查器会失败，不能证明正确时会通过。

### 11.1 新增测试 helper

放在 `tests/contract/test_real_core_generated_template_gap.py`：

```python
def unit_by_id(report, unit_id): ...
def element_by_id(unit, element_id): ...
def collect_checks(report, *, type=None, category=None, status=None): ...
def write_minimal_gap_standard(root, school_id, expected_units): ...
def write_docx(path, paragraphs): ...
```

### 11.2 新增测试

`test_template_gap_minimal_fixture_can_pass_cleanly`

要求：

- 在 `tmp_path` 下创建最小 school standard、`template_unit_contract.yaml` 和完全匹配的 `generated_template.docx`。
- 跑真实 `run_template_gap_eval(tmp_root, school_id, generated_template, out_dir)`。
- 断言：

```python
result.status == Status.PASS
report["summary"]["blocking_status"] == "PASS"
report["summary"]["failed_count"] == 0
report["summary"]["unknown_count"] == 0
unit_by_id(report, "cover")["verdict"] == "PASS"
```

### 11.3 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py::test_template_gap_minimal_fixture_can_pass_cleanly -q
```

## 12. C2：分层结果树替代平铺 `check_items`

不保留旧 `check_items` 兼容层。

### 12.1 新报告结构

`template_gap_report.json` 改为 v2.0：

```python
{
    "artifact_type": "template_gap_report",
    "artifact_version": "2.0",
    "school_id": "...",
    "generated_template": {
        "path": ".../generated_template.docx",
        "source_path": "...",
        "sha256": "...",
        "input_role": "generated_template"
    },
    "input": CheckResult,
    "units": [
        {
            "unit_id": "cover",
            "name": "封面",
            "order": 10,
            "status": "required",
            "located": {
                "found": True,
                "source_ref": "word/document.xml:p[1]",
                "order_range": [1, 23]
            },
            "presence": CheckResult,
            "elements": [
                {
                    "element_id": "e_001",
                    "name": "学校名称",
                    "policy": "fixed",
                    "order": 1,
                    "presence": CheckResult,
                    "style": CheckResult,
                    "verdict": "PASS"
                }
            ],
            "dimensions": {
                "page": [CheckResult],
                "header_footer": [CheckResult],
                "fields": [CheckResult],
                "numbering": [CheckResult]
            },
            "counts": {"passed": 0, "failed": 0, "unknown": 0},
            "verdict": "FAIL"
        }
    ],
    "unmodeled_objects": [CheckResult],
    "summary": {
        "known_status": "FAIL",
        "display_status": "FAIL + UNKNOWN",
        "blocking_status": "FAIL",
        "passed_count": 0,
        "failed_count": 0,
        "unknown_count": 0,
        "per_unit": [
            {"unit_id": "cover", "verdict": "FAIL", "counts": {...}}
        ]
    },
    "coverage": {...}
}
```

### 12.2 `CheckResult`

```python
{
    "check_id": "template_generation.element_match",
    "status": "PASS|FAIL|UNKNOWN",
    "type": "template_generation_element_found",
    "message": "...",
    "expected": "...",
    "actual": "...",
    "category": "element|style|page_rule|...",
    "path": ["units", "cover", "elements", "e_001", "presence"],
    "evidence_refs": ["word/document.xml:p[1]"],
    "next_step": "..."
}
```

`path` 替代旧的点号 `affected_ids` 作为报告内部定位。生成 `Finding` 时，从 `path` 派生 `affected_ids`，例如 `["cover.e_001.presence"]`。

### 12.3 `generated_template_gap.py` 改动

1. `_check()` 包一层 `_check_result(path=...)`，强制写入 `path`。
2. `build_template_gap_report()` 输出 `input`、`units`、`unmodeled_objects`、`summary`，不再创建 `check_items`。
3. `summarize_check_items()` 改成 `summarize_template_gap_report()`，或只保留为测试迁移期间的私有兼容 helper。
4. `findings_from_template_gap_report()` 递归遍历结果树。
5. `render_template_gap_markdown()` / `write_template_gap_docx()` 按单元分组。
6. `template_generation_coverage()` 改为调用 `template_generation_coverage_from_report(report, tree)`。

### 12.4 旧测试改写

- `report["check_items"]` 改为 `collect_checks(report, ...)` 或具体 unit/element 路径。
- `item["affected_ids"] == ["cover.e_001"]` 改成检查 `path` 或 `unit_by_id(...)/element_by_id(...)`。
- `test_template_gap_status_combination_rules` 改成测试 `summarize_template_gap_report()`。

### 12.5 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py -q
```

## 13. C3：匹配去噪和 UNKNOWN 分类

### 13.1 新增函数

```python
def _normalize_for_match(value: Any) -> str: ...
def _strip_format_annotations(text: str) -> str: ...
def _split_match_tokens(text: str) -> list[str]: ...
```

规则：

- `_normalize_text()` 继续用于报告展示。
- `_normalize_for_match()` 仅用于匹配：删 `□`、`×`/`×××`、点引线、格式批注括号；保留语义括号，如 `毕业论文(设计)`。
- `_candidate_needles()` 返回 query dict：

```python
{
    "full": ["目 录"],
    "tokens": ["学生姓名", "学号", "年级专业及班级"],
    "min_tokens": 2
}
```

- `_find_best_match()`：full 命中任一即 PASS；tokens 命中 `>= min_tokens` 即 PASS。
- 无有效 query 的 fixed/manual_only 元素返回 `UNKNOWN template_generation_element_uncheckable`。

### 13.2 必须覆盖的回归例子

- `目 录` 能命中 `目□□录   (二号黑体，居中)`。
- `摘 要：` 能命中 `□□摘要……………………………………………………………………………1`，但不能误判成正文摘要内容已存在。
- `学生姓名：；学号：；年级专业及班级：` 能命中分散字段标签。
- 无 needle 的 fixed/manual_only 元素不再 FAIL。

### 13.3 新增测试

- `test_template_gap_unsearchable_fixed_element_is_unknown_not_fail`
- `test_template_gap_normalizes_template_noise`

### 13.4 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py \
  -k "normalizes_template_noise or unsearchable_fixed_element" -q

uv run docfit eval template-gap --school hunannongye \
  --generated-template inputs/simulated-generated-templates/real-core-v0/hunannongye/generated_template.docx \
  --out /tmp/docfit_gap_hna_after_match
```

检查 `template_generation_element_missing` 数量应明显下降；无 needle 项应转为 UNKNOWN。

## 14. C4：单元范围内匹配和样式绑定

### 14.1 新增 helper

```python
def _visible_entries_by_order(tree) -> list[dict[str, Any]]: ...
def _match_query_for_element(element) -> dict[str, Any]: ...
def _find_best_match(entries, query, order_range=None) -> dict[str, Any] | None: ...
def _locate_units(expected_units, entries) -> dict[str, dict[str, Any]]: ...
def _entries_in_range(entries, order_range) -> list[dict[str, Any]]: ...
```

普通 dict 就够用，不需要为了本轮引入额外模型层。

### 14.2 单元定位规则

1. 锚点优先取前 3 个 `policy in {"fixed", "manual_only"}` 且能生成有效 query 的元素。
2. 如果元素没有有效 query，再尝试 unit name。
3. 全局搜索锚点一次，得到 `anchor_order`。
4. 范围为 `[本单元 anchor_order, 下一单元 anchor_order)`，最后一个单元到 `+infinity`。
5. required 单元无锚点：unit FAIL；下级元素 `UNKNOWN template_generation_element_unit_unlocated`，不全文搜。
6. optional 单元无定位：unit UNKNOWN；下级不全文搜。

### 14.3 元素匹配规则

```python
match = _find_best_match(entries, query, unit["located"]["order_range"])
```

- 命中：presence PASS；style 用同一个 match。
- 未命中：有 query 的 fixed/manual → FAIL missing；无 query → UNKNOWN uncheckable。

### 14.4 样式绑定纠偏

1. `_style_check()` 的 match 必须来自本单元 `_find_best_match()`。
2. `iter_visible_text_entries()` 对 table cell 补 `style_details`。
3. `_actual_style_properties()` 回退顺序：`dominant_run` → `paragraph_run_properties` → `style_inheritance.run` → UNKNOWN。
4. `_expected_style_requirements()` 去掉 4 字体白名单，通用抽取字体名。

### 14.5 新增测试

- `test_template_gap_single_style_mutation_fails_only_that_element`
- `test_template_gap_missing_required_element_is_presence_fail`
- `test_template_gap_matches_repeated_text_inside_unit_range`

### 14.6 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py \
  -k "repeated_text_inside_unit_range or single_style_mutation" -q
```

## 15. C5：coverage 与 e2e 回归

### 15.1 `coverage.py`

`_real_core_template_gap_findings()` 继续检查：

```text
generated_template.docx
generated_template_tree.json
template_gap_report.json
template_gap_report.md
template_gap_report.docx
```

不变：

- hash 必须绑定 artifacts 里的 `generated_template.docx`。
- `blocking_status in {FAIL, UNKNOWN}` 仍生成 `generated_template_gap_blocking`。

改动：

- `summary` 要求包含 `per_unit`。
- 不再要求 `check_items`。

### 15.2 `template_generation_coverage_from_report(report, tree)`

| 能力点 | 判断来源 |
| --- | --- |
| `output_docx` | `report["input"].status == PASS` |
| `actual_tree` | `tree.input_valid_docx` 且可见 entry 有 `source_ref` |
| `unit_match` | 存在 unit presence check |
| `element_match` | 存在 element presence check |
| `style_match` | 存在 element style check |
| `header_footer_match` | 任一 unit `dimensions.header_footer` 非空 |
| `page_rule_match` | 任一 unit `dimensions.page` 非空 |
| `field_match` | 任一 unit `dimensions.fields` 非空 |
| `numbering_match` | 任一 unit `dimensions.numbering` 非空 |
| `report` | 有 `summary` 且有 `units` |

### 15.3 新增测试

- `test_real_core_gap_uses_simulated_generated_template_fixture`

### 15.4 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py \
  tests/contract/test_contract_gates.py \
  tests/e2e/test_bootstrap_cli.py -q

uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
```

## 16. 关键文件索引

| 文件 | 职责 |
| --- | --- |
| `src/docfit/harness/generated_template_gap.py` | 主战场：结果树、匹配、汇总、报告渲染 |
| `src/docfit/harness/generated_template_inspector.py` | 解析树、`order`、`style_details` |
| `src/docfit/harness/coverage.py` | 能力点派生、blocking 校验 |
| `src/docfit/harness/profiles.py` | `generated_template_docx` 配置 |
| `src/docfit/convert/orchestrator.py` | eval 入口切换被测对象 |
| `tests/contract/test_real_core_generated_template_gap.py` | contract 测试主文件 |

复用：`merge_statuses`；`inspect_generated_template_docx` 解析树主体不大改。

## 17. 完整测试清单

| 测试 | 证明什么 |
| --- | --- |
| `test_template_gap_minimal_fixture_can_pass_cleanly` | 全对样本会 PASS |
| `test_template_gap_single_style_mutation_fails_only_that_element` | 定点样式 FAIL |
| `test_template_gap_missing_required_element_is_presence_fail` | 删必填元素 → presence FAIL |
| `test_template_gap_unsearchable_fixed_element_is_unknown_not_fail` | 无 needle → UNKNOWN |
| `test_template_gap_matches_repeated_text_inside_unit_range` | 跨单元同文不串台 |
| `test_template_gap_normalizes_template_noise` | 去噪匹配 |
| `test_real_core_gap_uses_simulated_generated_template_fixture` | 被测对象路径正确 |

## 18. 执行顺序速查

```text
C0 固定被测对象 → 三校 gap 只读虚拟业务生成模板
C1 最小 PASS 夹具 → 必须先绿
C2 分层结果树 → contract 测试全绿
C3 匹配去噪 + UNKNOWN → 误报型 missing 下降
C4 单元范围匹配 + 样式绑定 → 串台/样式定点测试
C5 coverage + e2e → 全量回归
```
