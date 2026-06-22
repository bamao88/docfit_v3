# 模板生成评测与测试架构

Last updated: 2026-06-22

一句话结论：这份文档只说明模板生成相关的“怎么验、测试怎么组织、报告怎么聚合”；它不定义模板生成五步怎么优化，也不决定某个单元最终应该怎么生成。

## 文档范围

本文关注评测层和测试层：

| 范围内 | 范围外 |
| --- | --- |
| 最终 `generated_template.docx` 是否符合学校标准 | 模板生成五步内部应该怎么重写 |
| 每个阶段产物将来如何接检查器 | 每个阶段最终有哪些业务字段 |
| 检查结果如何表达 `PASS` / `FAIL` / `UNKNOWN` | 某个 unit 应该 `whole_unit_copy` 还是局部 patch |
| 如何从最终 gap 追溯到可能出错的阶段 | 用学生源内容决定模板生成策略 |
| 测试应该证明哪些评测行为 | 自动更新学校标准、golden 或 expected snapshot |

这里说的“阶段检查器”在代码里可以叫 verifier。它的普通含义是：读取某个阶段的输入和输出，用已定义标准判断这个阶段是否可证明正确，然后产出状态和问题列表。

## 两层评测

模板生成相关评测分成两层，不要混成一件事：

| 层次 | 要回答的问题 | 当前真实状态 | 输入 | 输出 |
| --- | --- | --- | --- | --- |
| 最终结果验证 | 最终 `generated_template.docx` 是否符合学校签收标准 | 已经有 `template-gap`，是当前唯一稳定可用的模板生成验收检查 | `generated_template.docx`、`template_unit_contract.yaml` | `generated_template_tree.json`、`template_gap_report.*`、状态 |
| 阶段产物验证 | 每个中间阶段的输出是否符合该阶段标准 | 还没有统一骨架；大部分阶段缺少已签收的输出标准 | 某阶段输入产物和输出产物 | 阶段状态、问题列表、可疑的首次出错阶段 |

最终结果验证可以先跑，因为它的检查对象和标准已经存在。阶段产物验证要等每个阶段的输入、输出和输出标准明确后再逐个补，不应该提前把临时实现写成验收标准。

## 当前真实实现

| 能力 | 当前真实情况 | 说明 |
| --- | --- | --- |
| 模板生成命令 | `docfit eval template-generate` 能写出 `source_template_tree.json`、`template_structure_candidates.json`、`template_generation_model.json`、`template_generation_plan.json`、`generated_template.docx` 和 `template_generation_manifest.json` | 这个命令返回 `PASS` 只说明生成流程完成，不说明 Word 已符合学校标准 |
| 最终 gap 检查 | `docfit eval template-gap` 会检查被测 `generated_template.docx` | 这是当前可作为阶段化评测示例的真实检查器 |
| 阶段检查聚合 | 当前没有统一的“阶段产物 -> 检查器 -> 状态/问题 -> 聚合报告”骨架 | 所以现在更像是有阶段产物和最终 gap，缺少中间统一评测层 |
| 合同测试 | `tests/contract/test_template_generate.py` 覆盖模板生成产物链；`tests/contract/test_real_core_generated_template_gap.py` 覆盖最终 gap | 现有测试还没有证明阶段检查聚合架构存在 |

因此，当前最小目标不是马上写完所有阶段检查器，而是先把评测架构留出正确位置：哪些阶段已配置检查器，哪些阶段只是有产物但还没有标准，最终 gap 如何作为第一个可运行示例接入。

## 阶段编号

评测阶段命名必须带数字前缀，并且和模板生成阶段产物编号对齐。这样人看报告时，可以直接从检查结果跳到同编号的产物文件。

| 编号 | 评测阶段 ID | 对应产物 | 当前检查状态 |
| --- | --- | --- | --- |
| `00` | `00_input_request` | `template_generation_request.json`、`00_input_source_template.docx` | 先登记输入，不作为独立质量验收 |
| `01` | `01_source_parse` | `source_template_tree.json` | `not_configured` |
| `02` | `02_structure_discovery` | `template_structure_candidates.json` | `not_configured` |
| `03` | `03_generation_model` | `template_generation_model.json` | `not_configured` |
| `04` | `04_plan_build` | `template_generation_plan.json` | `not_configured` |
| `05` | `05_action_execution` | `05.0_copy_source_docx.docx`、`05.1_generated_template.docx`、`generated_template.docx`、`05.2_template_generation_manifest.json` | `not_configured` |
| `06` | `06_final_template_gap` | `generated_template_tree.json`、`template_gap_report.json`、`template_gap_report.md`、`template_gap_report.docx` | `enabled` |
| `99` | `99_debug_index` | `99_template_generation_debug_index.json` | 调试索引，不是 verifier 阶段 |

`00` 和 `99` 是运行上下文和索引，不应该被写成业务质量 `PASS`。真正会逐步接检查器的是 `01` 到 `06`；当前只有 `06_final_template_gap` 已经有稳定检查器。

## 产品评测能力和测试代码边界

| 文件或目录 | 身份 | 当前用途 |
| --- | --- | --- |
| `src/docfit/cli/` | 产品 CLI 入口 | 暴露 `docfit eval template-generate` 和 `docfit eval template-gap` |
| `src/docfit/convert/orchestrator.py` | 产品评测编排代码 | 串联 eval 命令、产物写出、报告写出 |
| `src/docfit/harness/generated_template_inspector.py` | 产品评测能力 | 读取被测 Word，生成 `generated_template_tree.json` |
| `src/docfit/harness/generated_template_gap.py` | 产品评测能力 | 用 `template_unit_contract.yaml` 对照 Word 解析证据，生成 gap 结果 |
| `src/docfit/stages/template_generate/**` | 产品支撑流程代码 | 生成可填写模板和过程证据；不是测试辅助代码 |
| `tests/contract/**` | 测试代码 | 调用产品能力，证明检查器不会把 `FAIL` / `UNKNOWN` 误放成 `PASS` |
| `test_outputs/**` | 运行证据 | 存放每次 eval 的产物、报告和 debug 文件 |

这意味着：评测代码有一部分确实属于产品能力，例如 inspector、gap checker、orchestrator；测试只是调用这些能力来锁住行为。

## 目标骨架

阶段化评测需要一张统一清单。每一项至少说清：

| 字段 | 含义 |
| --- | --- |
| `stage_id` | 带编号的阶段 ID，例如 `01_source_parse` 或 `06_final_template_gap` |
| `input_artifacts` | 检查器读取哪些输入产物 |
| `output_artifacts` | 检查器检查哪些输出产物 |
| `verifier_state` | 检查器是否已配置，例如 `enabled`、`not_configured`、`missing_standard` |
| `gate_enabled` | 这个阶段当前是否参与 gate |
| `status` | 已启用检查器的结果，只能是 `PASS`、`FAIL` 或 `UNKNOWN` |
| `findings` | 人和机器都能读的问题列表 |
| `first_bad_stage` | 如果能定位，说明问题第一次出现在哪个阶段 |

建议先把它写成类似 `template_generation_stage_checks.json` 的聚合产物。名字可以后续定，但语义必须保持：未配置检查器不是 `PASS`，也不是 `FAIL`，它只能说明这个阶段暂时没有纳入 gate。

## 阶段清单

| 阶段 | 检查对象 | 当前检查状态 | 当前建议 |
| --- | --- | --- | --- |
| `01_source_parse` | `source_template_tree.json` 是否完整表达源 Word 事实 | `not_configured` | 先登记输入输出，等解析标准明确后再启用 |
| `02_structure_discovery` | `template_structure_candidates.json` 是否正确识别候选 unit 和 logical element | `not_configured` | 先登记输入输出，不把当前启发式当标准 |
| `03_generation_model` | `template_generation_model.json` 是否把候选结构转成正确策略 | `not_configured` | 先登记输入输出，等学校标准和策略标准明确 |
| `04_plan_build` | `template_generation_plan.json` 是否完整表达要执行的 Word action | `not_configured` | 先登记输入输出，后续检查 action 来源和冲突 |
| `05_action_execution` | `generated_template.docx` 和 `template_generation_manifest.json` 是否与 plan 对齐 | `not_configured` | 先登记输入输出，后续检查 action 是否真的执行 |
| `06_final_template_gap` | `generated_template.docx` 是否满足 `template_unit_contract.yaml` | `enabled` | 当前第一个可运行示例，继续使用现有 `template-gap` |

这张表的重点是先把“有产物”和“产物已验收”分开。前五个阶段现在可以有产物、可以有 debug、可以被人工排查，但不能因为命令跑完就算阶段验证通过。

## 聚合状态规则

| 情况 | 聚合时怎么表达 |
| --- | --- |
| 已启用检查器返回 `FAIL` | 聚合结果必须阻断；报告列出失败项和对应阶段 |
| 已启用检查器返回 `UNKNOWN` | 聚合结果必须阻断；报告说明缺证据、缺标准或检查器不足 |
| 已启用检查器全部 `PASS`，但有阶段 `not_configured` | 可以说明“当前已启用检查通过”，但不能声称所有阶段都已验证 |
| 阶段没有标准或检查器 | 写 `verifier_state = not_configured` 或 `missing_standard`，不要写 `PASS` |
| 最终 gap 失败但中间阶段未配置检查器 | 报告先给最终失败，再用现有产物帮助人工追溯，不伪造中间阶段结论 |

`template_generate` 自己的执行状态和评测状态也要分开：

| 状态 | 含义 |
| --- | --- |
| 生成执行 `PASS` | 命令完成并写出了预期产物 |
| 阶段检查 `PASS` | 某个已启用检查器证明对应产物符合标准 |
| 最终 gap `PASS` | 被测生成模板符合学校签收的模板差距标准 |

## 关键边界

- `template_generate` 当前不读取学生源 Word，也不应该用“学生源内容台账里有没有某段内容”来决定生成模板策略。
- 如果识别出某个位置是用户填写位，它就是模板里的填写位；这件事来自源模板、学校标准或产品规则，不来自某一次学生源文档是否有内容。
- 学生内容是否存在、是否放置、是否渲染正确，属于后续内容提取、内容放置和最终渲染评测，不属于生成模板评测。
- `template_generation_manifest.json` 只能证明生成器执行了什么，不能证明最终 Word 符合学校标准。
- `generated_template_tree.json` 是从被测 Word 解析出来的事实证据；`template_gap_report.*` 是检查结果；两者都不是学校标准本身。
- AI 可以读报告帮助解释和归因，不能决定 `PASS`、`FAIL` 或 `UNKNOWN`。

## 测试策略

当前已有测试分工：

| 测试 | 当前证明什么 | 不证明什么 |
| --- | --- | --- |
| `tests/contract/test_template_generate.py` | 模板生成产物链、debug 编号、`source_seq` 追踪、copy-only 内部候选行为 | 不证明最终 Word 符合学校标准 |
| `tests/contract/test_real_core_generated_template_gap.py` | 最终 `template-gap` 能对真实学校生成模板输出 `PASS` / `FAIL` / `UNKNOWN` | 不证明中间阶段都有阶段检查器 |

后续补阶段化评测骨架时，最小测试应覆盖：

| 测试目标 | 期望 |
| --- | --- |
| 阶段清单稳定 | 报告里列出 `01_source_parse` 到 `06_final_template_gap` |
| 未配置阶段不伪装成通过 | `verifier_state = not_configured` 时没有 `status = PASS` |
| 最终 gap 作为示例接入 | `06_final_template_gap` 能复用现有 gap 检查结果 |
| 缺最终 gap 输入 | 返回 `UNKNOWN`，不能跳过检查后成功 |
| 聚合报告可读 | 人能看到哪些检查启用、哪些只是等待标准 |

## 当前最小落地顺序

1. 先新增阶段检查聚合结构，只登记阶段和检查状态。
2. 把现有 `template-gap` 挂成 `06_final_template_gap` 的第一个已启用检查器。
3. 让未配置阶段明确显示 `not_configured`，不参与 gate，也不显示成 `PASS`。
4. 等每个阶段的输入和输出标准定下来后，再逐个补阶段检查器。
5. 每补一个检查器，都补合同测试证明它的 `PASS` / `FAIL` / `UNKNOWN` 行为。

这样做的目的不是把架构写大，而是防止两个误判：一是最终 gap 失败时不知道从哪里追；二是中间阶段只有产物却被误认为已经验收通过。
