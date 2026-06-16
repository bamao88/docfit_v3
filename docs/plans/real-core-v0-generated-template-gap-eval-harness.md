# real-core-v0 生成模板 Word 差距发现计划

Status: Partially implemented
Last reviewed: 2026-06-16

## 执行前约定

```text
Preflight status: EXECUTED_PARTIAL
Task source: plan path
Canonical source: docs/plans/real-core-v0-generated-template-gap-eval-harness.md
Route: durable $intuitive-flow
Goal: 建成 real-core-v0 的生成模板 Word 差距检查模块，让系统能确定性报告 generated_template.docx 和学校模板标准之间的一致、不一致、无法证明之处。

Scope:
- 为 real-core-v0 建立 generated_template.docx 作为明确被测输入，并记录路径/hash
- 从 generated_template.docx 解析 generated_template_tree.json，来源必须来自 Word/OOXML，不从人工审查文本复制
- 用 template_unit_contract.yaml 逐项检查单元、元素、样式、页眉页脚、分页、字段、编号等差距
- 输出 template_gap_report.json、template_gap_report.md、template_gap_report.docx
- 接入 e2e / coverage gate，使缺 generated_template 或缺检查能力时为 UNKNOWN，发现差距时为 FAIL 或 FAIL + UNKNOWN
- 保持 PASS / FAIL / UNKNOWN 阻断语义，UNKNOWN 仍阻断

Non-goals: 不修正模板生成逻辑；不自动修改 generated_template.docx；不更新 signed standard、golden、expected snapshot；不重新判断原始学校 Word 是否正确；不用 AI 或人工临场视觉判断替代确定性检查；不把 LibreOffice/脚本分页当成 Microsoft Word evidence。

Context: must-read=docs/plans/real-core-v0-generated-template-gap-eval-harness.md, README.md, SPEC.md, docs/agents/bootstrap-eval-runbook.md, src/docfit/cli/main.py, src/docfit/stages/template_parse/runner.py, src/docfit/stages/render/runner.py, src/docfit/harness/template_units.py, src/docfit/harness/coverage.py, src/docfit/harness/product_quality.py, src/docfit/harness/word_evidence.py, src/docfit/ooxml/package.py, standards/eval_profiles/real-core-v0/cases.yaml, standards/schools/*/v1/template_unit_contract.yaml, tests/contract/test_real_core_baseline_harness.py, tests/contract/test_real_core_four_stage_problem_checks.py, tests/contract/test_contract_gates.py, tests/e2e/test_bootstrap_cli.py; useful=docs/human/real-core-v0-product-quality-review.md, docs/human/real-core-v0-four-stage-problem-checks.md, reports/real-core-v0/**/artifacts/template_artifact.json, reports/real-core-v0/**/final.docx, reports/real-core-v0/**/evidence/word_image_evidence.json; avoid-unless-needed=整份 docs/human/real-core-v0-review-packet.md 和 reports/** 页面图片大文件。

Acceptance:
- SUCCESS: 三所学校都能把 generated_template.docx 作为被测对象，生成 generated_template_tree.json 和三种 template_gap_report；报告含 known_status、display_status、passed_count、failed_count、unknown_count、blocking_status；坏样本不会 PASS；coverage/e2e 不再把 source-fact binding 或 Word evidence binding 当作模板正确性的充分证明。
- BLOCKED_NEEDS_DECISION: none
- BLOCKED_NEEDS_LOCAL_VALIDATION: Microsoft Word 打开和页面图片证据如果本机 Word 或导出脚本不可用，则不能宣称 Word evidence 完整通过。
- INTERMEDIATE_ONLY: none
- No regressions: bootstrap-core 的 PASS/FAIL/UNKNOWN 行为不变；auto_update_allowed 仍为 false；FAIL/UNKNOWN 不被降级；visible content ledger 和四阶段 gate 规则不被绕过。

Verification: deterministic=uv run pytest tests/unit/test_baseline_comparison.py tests/unit/test_word_evidence.py tests/contract/test_contract_gates.py tests/contract/test_real_core_baseline_harness.py tests/contract/test_real_core_four_stage_problem_checks.py tests/contract/test_real_core_generated_template_gap.py tests/e2e/test_bootstrap_cli.py; integration=uv run pytest tests/contract/test_real_core_generated_template_gap.py -q plus artifact schema/hash/source-ref assertions; product-run=uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage and uv run docfit eval e2e --school hunannongye --student inputs/real-student-003-source.docx --out /tmp/docfit_real_core_template_probe; local-live-manual=uv run python scripts/export_real_core_word_evidence.py, required only for Microsoft Word evidence completion and blocked if Word is unavailable; optional=uv run pytest -q.
Execution: main=监督 $intuitive-flow 按计划分阶段实现、检查产物语义、运行验证并判断 complete/blocked；worker=none；worker-goal=none
To execute: /goal execute docs/plans/real-core-v0-generated-template-gap-eval-harness.md with intuitive-flow
Approval: LGTM/approve/go ahead approves; edits request revision.
```

## 当前实现状态（2026-06-16）

已完成：

- 新增 `docfit eval template-gap --school ... --generated-template ... --out ...`，
  命令会明确接收被测生成模板 Word。
- real-core 的 template/e2e 路径会写出：
  - `artifacts/generated_template.docx`
  - `artifacts/generated_template_tree.json`
  - `artifacts/template_gap_report.json`
  - `artifacts/template_gap_report.md`
  - `artifacts/template_gap_report.docx`
- `generated_template_tree.json` 来自 DOCX/OOXML 解析，包含段落、表格、页眉页脚、
  字段、分页/section、编号引用、段落/运行样式属性和未建模可见对象的来源位置。
- `template_gap_report.json` 保留 `known_status`、`display_status`、
  `passed_count`、`failed_count`、`unknown_count` 和 `blocking_status`。
  当前真实 probe 的模板报告是 `FAIL + UNKNOWN`，说明已经发现确定性差距，
  同时仍有分页、页眉页脚、字段绑定、编号绑定和部分样式继承无法完整证明。
- 差距报告现在显式覆盖 field 和 numbering 两类检查：
  - Word 字段缺失会报 `template_generation_field_missing`。
  - 编号规则还不能绑定到单元/元素时会报 `template_generation_numbering_unverified`。
- 样式检查现在会读取 OOXML 里的字体、字号、加粗和对齐。能确定不一致时会报
  `template_generation_style_mismatch`；缺少行距或继承证据时仍保留
  `template_generation_style_unverified`。
- e2e 不再因为 source-fact binding 或 Word evidence binding 存在就把模板视为通过。
  如果模板差距报告阻断，summary 会保持 `blocked_at: template`，但仍继续生成后续
  内容、放置、渲染诊断产物。
- real-core coverage 会检查 checked-in 的生成模板差距证据；缺证据或报告阻断时，
  coverage 不能通过。

验证证据：

```bash
uv run pytest tests/unit/test_baseline_comparison.py tests/unit/test_word_evidence.py tests/contract/test_contract_gates.py tests/contract/test_real_core_baseline_harness.py tests/contract/test_real_core_four_stage_problem_checks.py tests/contract/test_real_core_generated_template_gap.py tests/e2e/test_bootstrap_cli.py -q
# 44 passed

uv run pytest -q
# 56 passed

uv run docfit eval template-gap --school hunannongye --generated-template inputs/school-hunannongye-requirement.docx --out /tmp/docfit_template_gap_hunannongye
# status = FAIL

uv run docfit eval e2e --school hunannongye --student inputs/real-student-003-source.docx --out /tmp/docfit_real_core_template_probe
# status = FAIL
# summary: template=FAIL, content=UNKNOWN, placement=UNKNOWN, render=FAIL, blocked_at=template

uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
# status = FAIL
```

仍未完成：

- 当前原型还没有真正修正模板生成逻辑；本切片只是把生成模板 Word 作为被测输入并
  报告差距。
- 行距、样式继承、分页、页眉页脚、字段绑定、编号绑定等 OOXML 检查仍有
  `UNKNOWN`，需要继续补解析能力。
- Microsoft Word 打开和页面图片证据仍只覆盖已有 `final.docx` 证据包；生成模板
  Word 的 Word evidence 还不能宣称完整通过。
- 9 个真实成品尚未在修复生成模板、内容、放置、渲染后统一重生。

## 目标

本阶段的目标不是生成正确模板，也不是修正模板生成逻辑。本阶段的目标是建设一个可以独立运行的 eval harness 模块，用人工审查得到的学校模板标准，发现“代码生成的 Word 模板”和“学校标准模板”之间的差距。

本阶段也不是让代码重新判断原始学校 Word 是否正确。原始学校 Word 的正确性已经由人工审查文档确认，并被编译成可执行的模板验收标准。

本阶段真正要做到的是：

1. 把 `generated_template.docx` 当成被测对象，而不是当成默认正确的产物。
2. 从生成出来的 Word 中解析实际结构、样式和 Word 证据。
3. 把实际结构和 `template_unit_contract.yaml` 逐项比对。
4. 报告每个差距：缺了什么、多了什么、顺序哪里不对、样式哪里不对、页眉页脚/分页/字段哪里无法证明。
5. 当前生成模板即使是错的，也可以作为输入；eval harness 必须能在具体检查项上返回 `FAIL` 或 `UNKNOWN`，而不是为了让模板阶段通过而放宽标准。

一句话说明：

```text
人工审查标准负责证明“学校模板应该是什么样”；
本阶段负责发现“代码生成出来的 Word 模板”和“学校模板标准”之间还有哪些差距。
```

## 名词边界

| 名词 | 含义 | 是否是本阶段被验收对象 |
| --- | --- | --- |
| 原始学校模板 Word | 学校提供的模板或要求文档，例如 `inputs/school-*.docx` | 否。它是标准来源，不是本阶段要重新证明正确的对象 |
| 人工审查文档 | 人工把学校模板拆成单元、元素、样式和规则后的说明 | 否。它是标准来源 |
| 模板验收标准 | 从人工审查文档编译出的机器可执行标准，例如 `template_unit_contract.yaml` | 否。它是裁判标准 |
| 生成模板 Word | 代码生成出来、理论上准备给后续内容填充使用的 Word 文件 | 是。本阶段核心被测对象，不默认正确 |
| 生成模板结构树 | 从生成模板 Word 中确定性解析出的实际结构 | 是。它是和标准比对的实际结果 |
| 模板差距报告 | 标准和实际结果逐项比对后的报告 | 是。它是给人看的问题清单 |

## 当前目录和职责

```text
docfit_v3/
├── inputs/
│   ├── school-hunannongye-requirement.docx
│   ├── school-nannong-undergraduate-template.docx
│   ├── school-pku-graduate-template.docx
│   ├── school-hunannongye-template-review.txt
│   ├── school-nannong-undergraduate-template-review.txt
│   └── school-pku-graduate-template-review.txt
│
├── standards/schools/<school_id>/v1/
│   ├── signed_standard.yaml
│   ├── template_contract.json
│   └── template_unit_contract.yaml
│
├── src/docfit/stages/
│   ├── template_parse/runner.py
│   ├── content_extract/runner.py
│   ├── placement/runner.py
│   └── render/runner.py
│
├── src/docfit/harness/
│   ├── template_units.py
│   ├── baselines.py
│   ├── coverage.py
│   ├── product_quality.py
│   └── word_evidence.py
│
└── tests/contract/
    ├── test_real_core_baseline_harness.py
    ├── test_real_core_four_stage_problem_checks.py
    └── test_contract_gates.py
```

现有文件的实际含义：

| 文件 | 当前作用 |
| --- | --- |
| `inputs/school-*-template-review.txt` | 人工审查源。说明学校模板应该有哪些结构和样式 |
| `standards/schools/*/v1/template_unit_contract.yaml` | 模板验收标准。里面的 `expected.units` 是当前最重要的结构化标准 |
| `src/docfit/stages/template_parse/runner.py` | 当前模板阶段入口。会读取 Word 段落和样式，也会从人工审查文本/标准生成模板单元树 |
| `src/docfit/harness/template_units.py` | 把人工审查文本转成结构化单元，并把 artifact 和 expected units 做逐项比对 |
| `src/docfit/stages/render/runner.py` | 当前真正写出 `final.docx` 的地方。它复制模板 Word，再根据 placement plan 添加内容 |
| `src/docfit/harness/product_quality.py` | e2e 后的业务质量检查，会发现当前输出仍有模板说明泄漏、内容追加等问题 |

## 当前真实流程

```text
人工审查文档
      ↓
template_unit_contract.yaml
      ↓
template_parse/runner.py
      ↓
template_artifact.json
      ↓
template_units.py 比对 expected.units
      ↓
PASS / FAIL / UNKNOWN
```

这条链路目前可以证明：

- 模板标准中已经有结构化 `expected.units`。
- 当前 `template_artifact.data.units` 和 `expected.units` 可以逐单元、逐元素、逐样式比对。
- 如果手动篡改 artifact 中某个元素样式，测试能报出类似 `template_element_style_mismatch` 的具体错误。
- 如果缺少结构化标准，验收会返回 `UNKNOWN`。

这条链路目前不能充分发现：

- 代码生成出来的模板 Word 和学校标准模板之间有哪些差距。
- 这个生成出来的 Word 是否被确定性解析过。
- 解析出的实际 Word 结构和模板标准逐项哪里一致、哪里不一致、哪里无法判断。
- 这个生成模板 Word 的页眉页脚、分页、编号、字段、表格和图片占位具体有哪些问题。

## 独立 eval harness 模块边界

这个模块必须可以独立开发、独立运行、独立失败，不要求内容提取、内容放置、最终渲染同时修好。

模块输入：

```text
template_unit_contract.yaml
generated_template.docx
signed_standard.yaml
template_contract.json
```

模块输出：

```text
generated_template_tree.json
template_gap_report.json
template_gap_report.md
template_gap_report.docx
```

模块只负责：

- 读取生成模板 Word。
- 解析生成模板 Word 的实际结构。
- 读取学校模板验收标准。
- 找出实际 Word 和标准之间的差距。
- 以确定性规则输出逐检查项状态，并汇总成差距报告。

模块不负责：

- 修正模板生成逻辑。
- 自动改 `generated_template.docx`。
- 自动更新 `template_unit_contract.yaml`。
- 判断原始学校 Word 是否正确。
- 判断学生内容是否提取正确。
- 判断最终 `final.docx` 是否已经格式正确。

状态语义：

状态必须分成两层：**检查项状态**和**汇总状态**。`UNKNOWN` 不能直接代表“整个模板都是 UNKNOWN”，它只能说明某个检查项、某个元素、某个 Word 能力点无法证明。

检查项状态：

| 状态 | 在本模块里的含义 |
| --- | --- |
| `PASS` | 这个具体检查项已经证明和学校标准一致 |
| `FAIL` | 这个具体检查项的标准明确、检查能运行，并发现生成模板 Word 和标准不一致 |
| `UNKNOWN` | 这个具体检查项无法证明一致，例如缺来源证据、解析器覆盖不足、遇到未建模 Word 对象 |

汇总状态使用同一个组合规则：

```text
先根据已知检查项得到 known_status：
- 只要 failed_count > 0，known_status = FAIL
- 如果 failed_count = 0 且 passed_count > 0，known_status = PASS
- 如果没有任何 PASS/FAIL 检查项，known_status = UNKNOWN

再根据 unknown_count 叠加未知标记：
- unknown_count = 0：展示 known_status
- unknown_count > 0 且 known_status = PASS：展示 PASS + UNKNOWN
- unknown_count > 0 且 known_status = FAIL：展示 FAIL + UNKNOWN
- known_status = UNKNOWN：展示 UNKNOWN
```

汇总状态示例：

| 计数 | 报告应展示 | 含义 |
| --- | --- | --- |
| `passed_count > 0`，`failed_count = 0`，`unknown_count = 0` | `PASS` | 已检查部分全部符合，且没有未证明项 |
| `passed_count > 0`，`failed_count = 0`，`unknown_count > 0` | `PASS + UNKNOWN` | 已检查部分符合，但还有未证明项 |
| `failed_count > 0`，`unknown_count = 0` | `FAIL` | 已确认存在不一致 |
| `failed_count > 0`，`unknown_count > 0` | `FAIL + UNKNOWN` | 已确认存在不一致，同时还有未证明项 |
| 缺标准或缺 `generated_template.docx`，导致无法启动核心检查 | `UNKNOWN` | 不是模板差距结论，而是评测输入不完整 |

报告结构必须同时保留：

- `known_status`：只根据已知检查项得到的 `PASS`、`FAIL` 或 `UNKNOWN`。
- `display_status`：给人看的组合状态，例如 `PASS + UNKNOWN` 或 `FAIL + UNKNOWN`。
- `unknown_count`：未证明检查项数量。
- `failed_count`：已确认不一致的检查项数量。
- `passed_count`：已证明一致的检查项数量。
- `blocking_status`：是否允许这个模块作为完整证据进入后续 gate。

`blocking_status` 仍然使用现有 gate 枚举：

| 汇总计数 | `display_status` | `blocking_status` |
| --- | --- | --- |
| `failed_count = 0` 且 `unknown_count = 0` | `PASS` | `PASS` |
| `failed_count = 0` 且 `unknown_count > 0` | `PASS + UNKNOWN` | `UNKNOWN` |
| `failed_count > 0` 且 `unknown_count = 0` | `FAIL` | `FAIL` |
| `failed_count > 0` 且 `unknown_count > 0` | `FAIL + UNKNOWN` | `FAIL` |
| 核心输入缺失，无法启动检查 | `UNKNOWN` | `UNKNOWN` |

对 eval harness 开发来说，当前阶段的通过标准不是“生成模板 Word 已经 `PASS`”。当前阶段的开发通过标准是：**模块能按同一套组合规则稳定输出 `PASS`、`PASS + UNKNOWN`、`FAIL`、`FAIL + UNKNOWN` 或输入层 `UNKNOWN`，并报告具体差距。**

## 目标流程

```text
阶段 A：标准准备

原始学校模板 Word
      ↓
人工审查
      ↓
template_unit_contract.yaml
      ↓
作为裁判标准


阶段 B：准备被测生成模板 Word

原始学校模板 Word + template_unit_contract.yaml
      ↓
业务代码生成，或者测试夹具提供
      ↓
generated_template.docx
      ↓
作为 eval harness 输入，不要求它当前就是正确的


阶段 C：解析生成模板 Word

generated_template.docx
      ↓
确定性 OOXML / DOCX 解析
      ↓
generated_template_tree.json


阶段 D：生成模板差距检查

template_unit_contract.yaml + generated_template_tree.json
      ↓
逐单元、逐元素、逐样式、逐页眉页脚、逐字段比对
      ↓
template_gap_report.json
template_gap_report.md
template_gap_report.docx
      ↓
known_status + display_status + failed_count + unknown_count + blocking_status
```

后续完整链路：

```text
generated_template.docx
      +
student_content_artifact.json
      +
placement_plan.json
      ↓
final.docx
      ↓
render / Word evidence 验收
```

## 需要新增或调整的产物

```text
reports/<case_or_school>/artifacts/
├── template_artifact.json
├── generated_template.docx
├── generated_template_tree.json
├── template_gap_report.json
├── template_gap_report.md
└── template_gap_report.docx
```

每个产物的开发通过标准：

| 产物 | 通过标准 |
| --- | --- |
| `generated_template.docx` | 是 eval harness 的被测输入；文件有效，hash 被记录；它可以是错的，模块不能默认它正确 |
| `generated_template_tree.json` | 从 `generated_template.docx` 解析得到；每个 unit/element 都有 Word 来源位置；不能从人工审查文本复制 |
| `template_gap_report.json` | 机器可读；每个检查项都有 `PASS`、`FAIL` 或 `UNKNOWN`，汇总层保留 failed/unknown/passed 计数 |
| `template_gap_report.md` | 人可读；能看到生成模板和学校标准哪里一致、哪里不一致、哪里无法判断 |
| `template_gap_report.docx` | 给人工 review 使用；按学校、单元、元素、样式、分页、页眉页脚分组展示问题 |

## 修改计划

### 第 1 阶段：固定 eval harness 边界和输出命名

目标：

- 明确本模块是“生成模板 Word 的差距发现 eval harness”。
- 明确 `generated_template.docx` 是本模块的被测输入，不是本模块要修正的产物。
- 明确 `generated_template_tree.json` 是从生成 Word 解析出来的实际结果。

建议修改：

- 新增或调整 CLI / orchestrator，让 eval harness 能稳定读取或接收 `generated_template.docx`。
- 在 summary/report 中明确区分：
  - 标准来源：`template_unit_contract.yaml`
  - 被测输入：`generated_template.docx`
  - 实际解析结果：`generated_template_tree.json`
  - 差距报告：`template_gap_report.*`

通过标准：

- 跑单个学校模板差距检查时，命令必须明确使用哪个 `generated_template.docx`。
- 报告不能再让人误以为 `template_artifact.data.units` 本身就是生成 Word 的解析结果。
- 如果没有生成模板 Word，输入层状态必须是 `UNKNOWN`，并说明缺少被测对象；不能把它描述成“生成模板整体未知”。

### 第 2 阶段：实现生成 Word 的确定性解析器

目标：

- 从 `generated_template.docx` 中解析实际结构，而不是从人工审查文本生成实际结构。

解析范围：

- 段落文本、段落顺序、段落样式。
- 表格、行列、单元格文本、表格样式。
- 图片和图片占位。
- 页眉页脚文本、字段、页码。
- section、分页符、分节符。
- 编号、标题层级、列表样式。
- 可填槽位、固定模板块、系统生成字段、手工填写字段。

建议新增：

```text
src/docfit/stages/template_generate/
src/docfit/harness/generated_template_inspector.py
src/docfit/harness/generated_template_gap.py
```

通过标准：

- `generated_template_tree.json` 中每个节点都能回指到 Word 来源，例如段落、表格单元格、页眉或页脚。
- 解析器遇到无法识别但可能影响可见格式的对象时，返回 `UNKNOWN`，不能忽略。
- 单元测试能证明：删掉一个固定标题、改错一个样式、缺少一个可填槽位，都会被差距检查发现。

### 第 3 阶段：把模板标准和生成 Word 实际结构逐项比对

目标：

- 用 `template_unit_contract.yaml` 检查 `generated_template_tree.json`。
- 比对粒度必须到 unit、element、sub_element、style、page、header/footer、field。

检查逻辑：

```text
expected.units[n]
      ↓
查找 generated_template_tree 中对应 unit
      ↓
检查元素顺序
      ↓
检查每个元素的策略
      ↓
检查每个元素的样式
      ↓
检查分页/页眉页脚/字段/编号
      ↓
输出逐检查项 PASS / FAIL / UNKNOWN
      ↓
汇总 known_status、display_status、failed_count、unknown_count、passed_count
```

评测结果标准：

- 标准中每个 required unit 都必须在生成 Word 中找到。
- 标准中每个 required element 都必须在生成 Word 中找到。
- 固定内容不能缺失、不能被改写。
- 可填元素必须有明确可写位置。
- 手工填写元素必须保留但不能被自动填错。
- 系统生成元素必须有生成规则或占位，不允许静默缺失。
- 样式不一致必须 `FAIL`，样式无法判断必须 `UNKNOWN`。
- 页眉页脚、页码、字段缺失或无法判断必须 `FAIL` 或 `UNKNOWN`。

模块开发通过标准：

- 构造一个完全匹配标准的最小夹具时，报告 `display_status = PASS`，`unknown_count = 0`，`failed_count = 0`。
- 构造一个样式错误夹具时，报告 `display_status = FAIL`，并指出具体 element/style。
- 构造一个缺来源证据夹具且没有不一致时，报告 `display_status = PASS + UNKNOWN`，也就是 `known_status = PASS`、`unknown_count > 0`、`blocking_status = UNKNOWN`。
- 构造一个既有样式错误又有缺来源证据的夹具时，报告 `display_status = FAIL + UNKNOWN`，也就是 `known_status = FAIL`、`unknown_count > 0`、`blocking_status = FAIL`。
- 当前真实生成模板如果仍有问题，应该输出 `FAIL`、`FAIL + UNKNOWN` 或 `PASS + UNKNOWN`，这不算模块失败；这正是模块应该暴露的问题。

### 第 4 阶段：生成正式差距报告

目标：

- 让人能够直接打开报告，看出生成模板 Word 和学校标准之间的具体差距。

报告结构：

```text
学校
├── 已知状态：known_status = PASS / FAIL / UNKNOWN
├── 展示状态：display_status = PASS / PASS + UNKNOWN / FAIL / FAIL + UNKNOWN / UNKNOWN
├── 检查计数：passed_count / failed_count / unknown_count
├── gate 状态：是否允许作为完整证据进入后续流程
├── 生成模板 Word：路径、hash
├── 标准文件：路径、hash
├── 单元差距检查
│   ├── cover
│   ├── abstract_cn
│   ├── body_main
│   └── ...
├── 样式差距检查
├── 页眉页脚差距检查
├── 分页/分节差距检查
├── 字段/页码差距检查
└── 阻断问题列表
```

通过标准：

- 每个失败项都必须包含：
  - 标准期望是什么；
  - 实际生成 Word 是什么；
  - 对应 Word 来源位置；
  - 检查项状态是 `FAIL` 还是 `UNKNOWN`；
  - 下一步应该改生成逻辑、解析逻辑，还是标准。
- 报告不能只有“证据存在”，必须说明每个检查项是通过、不一致，还是无法证明。
- 报告不能因为某个检查项是 `UNKNOWN` 就把所有已经证明通过的检查项都盖成 `UNKNOWN`。
- 报告不能因为存在 `FAIL` 就丢掉同时存在的 `UNKNOWN` 项；`FAIL` 是主结论，`UNKNOWN` 仍然是需要补证据的问题。

### 第 5 阶段：接入 e2e 和 coverage gate

目标：

- 在独立 eval harness 可运行之后，把差距检查结果接入 e2e 和 coverage。
- 接入后，后续内容填充、placement、render 不能绕过模板差距报告。

建议修改：

- e2e 中模板阶段如果没有 `generated_template.docx`，输入层直接 `UNKNOWN`。
- coverage 中新增模板生成能力点：
  - `template_generation.output_docx`
  - `template_generation.actual_tree`
  - `template_generation.unit_match`
  - `template_generation.element_match`
  - `template_generation.style_match`
  - `template_generation.header_footer_match`
  - `template_generation.page_rule_match`
  - `template_generation.report`

通过标准：

- 当前错误输出不能因为有 source-fact binding 或 Word evidence binding 就通过。
- 缺任一关键能力点时，对应能力点是 `UNKNOWN`；汇总状态按同一套组合规则展示为 `PASS + UNKNOWN` 或 `FAIL + UNKNOWN`。
- 生成模板差距检查未完成时，不允许声称后续 `final.docx` 的格式验收完成。
- 如果生成模板差距检查返回 `FAIL` 或 `FAIL + UNKNOWN`，e2e 可以继续生成诊断用产物，但 summary 必须保持阻断状态。

### 第 6 阶段：Word 打开和页面证据

目标：

- 在确定性 OOXML 差距检查完成后，用本机 Microsoft Word 导出页面图片证据，证明 Word 能打开并分页。

通过标准：

- `generated_template.docx` 和后续 `final.docx` 都能被 Microsoft Word 打开。
- manifest 绑定 DOCX hash、Word 版本、导出方式、页数和页面图片 hash。
- Word 证据只能作为补充证明，不能替代前面的确定性差距检查。
- LibreOffice 或脚本分页不能替代 Microsoft Word evidence。

## 测试计划

### 单元测试

新增测试重点：

- 解析 `generated_template.docx` 的段落、表格、页眉页脚、字段和样式。
- 改错一个元素样式会 `FAIL`。
- 删除一个 required element 会 `FAIL`。
- 缺少 source ref 会 `UNKNOWN`。
- 遇到未知可见对象会 `UNKNOWN`。

### 合同测试

新增或更新：

```text
tests/contract/test_real_core_generated_template_gap.py
```

检查：

- 三所学校都能把 `generated_template.docx` 作为被测输入。
- 三所学校都能从被测 Word 生成 `generated_template_tree.json`。
- 三所学校都能生成可读差距报告。
- 标准和实际结构逐项比对。
- 坏样本不会 PASS。

### e2e 测试

更新：

```text
tests/contract/test_real_core_baseline_harness.py
tests/contract/test_real_core_four_stage_problem_checks.py
tests/e2e/test_bootstrap_cli.py
```

检查：

- bootstrap 行为不被破坏。
- real-core 模板生成未通过时，后续阶段不能假装通过。
- `UNKNOWN` 仍然阻断。
- `auto_update_allowed` 仍然必须是 false。

### 产品运行命令

建议最终验收命令：

```bash
uv run pytest tests/unit/test_baseline_comparison.py tests/unit/test_word_evidence.py tests/contract/test_contract_gates.py tests/contract/test_real_core_baseline_harness.py
uv run pytest tests/contract/test_real_core_generated_template_gap.py
uv run pytest tests/e2e/test_bootstrap_cli.py
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
```

需要本机 Word 的验收：

```bash
uv run python scripts/export_real_core_word_evidence.py
```

## 每个阶段怎么算通过

| 阶段 | 通过标准 |
| --- | --- |
| 标准准备 | 人工审查文档已经编译成 `template_unit_contract.yaml`，且 `expected.units` 完整、`auto_update_allowed: false` |
| 生成模板 Word | eval harness 能接收 `generated_template.docx` 作为被测输入；文件有效，来源和 hash 可追溯 |
| 解析生成 Word | 从 `generated_template.docx` 得到 `generated_template_tree.json`，节点都有 Word 来源证据 |
| 标准比对 | 每个 required unit/element/style/page/header/footer/field 都有明确 PASS/FAIL/UNKNOWN |
| 报告输出 | 生成 JSON、Markdown、DOCX 三种差距报告，人能直接看出失败位置和原因 |
| gate 接入 | e2e 和 coverage 不再把证据绑定当作业务正确；缺检查即 UNKNOWN |
| Word evidence | Microsoft Word 能打开并导出页面图片，manifest 与 DOCX hash 绑定 |

## 当前最高风险

1. 当前 `template_parse` 的命名会让人误解：它现在不是“解析生成模板 Word”的完整验收链路。
2. 当前没有稳定的 `generated_template.docx` 产物，导致模板生成阶段和 render 阶段混在一起。
3. 当前模板结构树可以和标准一致，但这不等于生成 Word 已经符合标准。
4. 当前差距报告还不是稳定 CLI 输出，人工 review 体验容易混乱。
5. 页眉页脚、分页、字段、编号这些 Word 格式细节需要 OOXML 检查和 Microsoft Word evidence 分层证明。

## 非目标

- 不要求代码独立判断原始学校 Word 是否正确。
- 不自动更新模板标准、signed standard、golden 或 expected baseline。
- 不用 AI 或人工临场视觉判断替代确定性验收。
- 不在模板差距检查完成前宣称 9 个真实 `final.docx` 格式验收完成。
- 不把 LibreOffice 或脚本分页当作 Microsoft Word evidence。

## 建议的下一步

把这份文档作为 preflight 输入，下一步只选一个清晰执行目标：

```text
实现 real-core-v0 的 generated_template.docx 产物、
generated_template_tree.json 解析器、
以及 template_unit_contract.yaml 对生成 Word 的逐元素差距报告。
```
