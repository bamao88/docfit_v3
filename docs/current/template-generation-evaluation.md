# 模板生成评测与测试架构

Last updated: 2026-06-22

一句话结论：这份文档只说明模板生成相关的“怎么验、测试怎么组织、报告怎么聚合”；评测层应优先复用业务生成已经落盘的过程产物，不为了对齐评测再跑一次模板生成。

## 文档范围

本文关注评测层和测试层：

| 范围内 | 范围外 |
| --- | --- |
| 最终 `generated_template.docx` 是否符合学校标准 | 模板生成五步内部应该怎么重写 |
| 每个阶段产物将来如何接检查器 | 每个阶段最终有哪些业务字段 |
| 检查结果如何表达 `PASS` / `FAIL` / `UNKNOWN` | 某个 unit 应该 `whole_unit_copy` 还是局部 patch |
| 如何从最终模板 gap 追溯到 01-05 哪个模板生成阶段先出错 | 用最终 gap 直接改写源模板事实、manifest 或生成策略 |
| 业务生成产物如何作为评测输入复用 | 让评测代码改写业务生成产物 |
| 测试应该证明哪些评测行为 | 自动更新学校标准、golden 或 expected snapshot |

这里说的“阶段检查器”在代码里可以叫 verifier。它的普通含义是：读取某个阶段的输入和输出，用已定义标准判断这个阶段是否可证明正确，然后产出状态和问题列表。

## 两层评测

模板生成相关评测分成两层，不要混成一件事：

| 层次 | 要回答的问题 | 当前真实状态 | 输入 | 输出 |
| --- | --- | --- | --- | --- |
| 最终结果验证 | 最终 `generated_template.docx` 是否符合学校签收标准 | 已经有 `template-gap`，是当前唯一稳定可用的模板生成验收检查 | `generated_template.docx`、`template_unit_contract.yaml` | `generated_template_tree.json`、`template_gap_report.*`、状态 |
| 阶段产物验证 | 每个中间阶段的输出是否符合该阶段标准 | 三校已有 01-05 各自独立的 `template_generation/*_contract.yaml`；统一聚合入口和阶段 verifier 还没有 | 某阶段输入产物和输出产物、对应阶段标准文件 | 阶段状态、问题列表、可疑的首次出错阶段 |

最终结果验证可以先跑，因为它的检查对象、标准和 verifier 都已经存在。阶段产物验证现在已经有标准入口，但还不能输出阶段 `PASS`：下一步要补的是读取已有 run 目录的聚合入口，以及逐个阶段的确定性 verifier。

## 业务产物如何进入评测

一句话结论：`template-generate` 跑完后留下的 `generated_template.docx`、`artifacts/*.json`、manifest 和 debug 快照，就是后续模板评测应该消费的证据；已有这些文件时，评测对齐不应该再调用生成器造一套新文件。

当前真实实现和目标边界要分开看：

| 情况 | 当前真实实现 | 应该表达的边界 |
| --- | --- | --- |
| 单独跑业务模板生成 | `docfit eval template-generate` 会运行 00-05，并写出正式产物和 debug 快照 | 这是产物生产者，不是学校标准裁判 |
| 单独跑最终 gap | `docfit eval template-gap --generated-template <已有 Word>` 可以直接检查已有 `generated_template.docx` | 评测可以消费已有 Word，不需要重新跑 00-05 |
| real-core 的 `template` / `e2e` 流程 | 当前会在同一个 pipeline 里重新跑模板生成，再把这次生成的 Word 交给 gap | 这是“新跑一遍完整链路”的模式，不等于已有产物包复用模式 |
| 01-05 阶段产物评测聚合 | 当前还没有统一入口消费已有 `template-generate` run 目录 | 后续应读取已有产物包、hash 和 manifest；缺产物时返回 `UNKNOWN`，不能静默重跑 |

复用已有产物包时，评测层只做三件事：

| 动作 | 说明 |
| --- | --- |
| 读取 | 读取同一次 `template-generate` 运行留下的 `summary.json`、`generated_template.docx`、`artifacts/*.json` 和 debug 快照 |
| 绑定 | 记录被检查文件的路径、hash、生产者阶段和 run 目录，证明检查的是哪一次业务输出 |
| 判定 | 用已配置 verifier 检查已有产物；标准缺失、文件缺失、hash 对不上或检查器未配置时输出 `UNKNOWN` |

复用模式下不要做这些事：

| 不要做什么 | 为什么 |
| --- | --- |
| 不要为了补齐缺失中间产物自动重跑 `generate_template` | 新跑会产生另一套证据，不能证明原始 run 的 first_bad_stage |
| 不要把 `template-generate` 的执行 `PASS` 当成阶段验收 `PASS` | 执行成功只证明文件写出来，不证明符合学校标准 |
| 不要让 AI 补造 manifest、hash、`source_seq_refs[]` 或阶段状态 | 这些是运行证据，只能由产品代码或检查器产生 |
| 不要用 manifest 替代最终 gap | manifest 说明生成器做了什么，最终 Word 是否合格仍要看 `template-gap` |

## 当前真实实现

| 能力 | 当前真实情况 | 说明 |
| --- | --- | --- |
| 模板生成命令 | `docfit eval template-generate` 能写出 `source_template_tree.json`、`template_structure_candidates.json`、`template_generation_model.json`、`template_generation_plan.json`、`generated_template.docx` 和 `template_generation_manifest.json` | 这个命令返回 `PASS` 只说明生成流程完成，不说明 Word 已符合学校标准 |
| 最终 gap 检查 | `docfit eval template-gap` 会检查被测 `generated_template.docx` | 这是当前可作为阶段化评测示例的真实检查器 |
| 已有产物复用 | 现在只有最终 gap 已经能直接消费已有 `generated_template.docx`；01-05 还没有“读取已有 run 目录并聚合阶段检查”的统一入口 | 所以当前如果只想检查已有 Word，跑 `template-gap`；如果要验证整个新链路，才跑 `template` / `e2e` |
| 01-05 阶段标准 | 三校已有 `standards/schools/<school_id>/v1/template_generation/<stage_id>_contract.yaml` | 每个阶段一个文件；它来自人工 review、`template_unit_contract.yaml#/expected/units` 和阶段校准运行证据，说明该阶段该守住什么；它不是运行产物，也不表示阶段已通过 |
| 阶段检查聚合 | 当前没有统一的“阶段产物 -> 标准文件 -> 检查器 -> 状态/问题 -> 聚合报告”骨架 | 所以现在更像是有阶段产物、阶段标准和最终 gap，缺少中间统一评测入口与 verifier |
| 合同测试 | `tests/contract/test_template_generate.py` 覆盖模板生成产物链；`tests/contract/test_real_core_generated_template_gap.py` 覆盖最终 gap | 现有测试还没有证明阶段检查聚合架构存在 |

因此，当前最小目标不是马上写完所有阶段检查器，而是先把评测架构留出正确位置：哪些阶段已有标准但还没有检查器，哪些检查器已启用，最终 gap 如何作为第一个可运行示例接入。

## 相关目录树

```text
docs/current/template-generation-evaluation.md  # 本文；只定义模板生成评测和测试边界。

standards/
  eval_profiles/real-core-v0/cases.yaml  # 真实学校评测 case 绑定。
  schools/<school_id>/v1/signed_standard.yaml  # 学校评测标准入口。
  schools/<school_id>/v1/template_generation/  # 01-05 阶段标准；每个阶段一个文件，标准已签收，verifier 未启用。
    01_source_parse_contract.yaml
    02_structure_discovery_contract.yaml
    03_generation_model_contract.yaml
    04_plan_build_contract.yaml
    05_action_execution_contract.yaml
  schools/<school_id>/v1/template_unit_contract.yaml  # 06_final_template_gap 的检查标准。

src/docfit/cli/main.py  # 暴露 docfit eval template-gap；template-generate 只是产物生产入口。
src/docfit/convert/orchestrator.py  # run_template_gap_eval 和后续阶段检查聚合入口位置。
src/docfit/harness/
  generated_template_inspector.py  # 读取被测 generated_template.docx，产出 generated_template_tree.json。
  generated_template_gap.py  # 对照 template_unit_contract.yaml，产出 template_gap_report.* 和状态。
  coverage.py  # coverage gate 读取 gap 证据，发现缺失或阻断问题。
  reports.py  # 写 summary.json、pm_report.md 和 findings.json。

tests/contract/
  test_real_core_generated_template_gap.py  # 锁住 06_final_template_gap 的 PASS / FAIL / UNKNOWN 行为。

test_inputs/template_gap/
  real-core-v0-<school_id>-generated-template.docx  # 当前 06_final_template_gap 的被测模板 fixture。

<template-generate-run>/  # 后续阶段检查应复用的已有业务产物包；不是 verifier 本身。
  generated_template.docx
  artifacts/*.json

<template-gap-out>/artifacts/  # template-gap 评测输出证据。
  generated_template.docx
  generated_template_tree.json
  template_gap_report.json
  template_gap_report.md
  template_gap_report.docx
```

## 阶段编号

一句话结论：编号节点一共 8 个：`00`、`01`、`02`、`03`、`04`、`05`、`06`、`99`。其中真正按质量检查逐步接 verifier 的阶段是 6 个：`01` 到 `06`。`00` 是输入和请求记录，`99` 是调试索引，都不是业务质量检查阶段。

评测阶段命名必须带数字前缀，并且和模板生成阶段产物编号对齐。这样人看报告时，可以直接从检查结果跳到同编号的产物文件。当前只有 `06_final_template_gap` 已经有稳定 verifier；`01` 到 `05` 有产物、合同测试和三校标准入口，但还没有阶段产物 verifier。

读这张表前，先把三个容易混淆的词分开：

| 表里的列 | 实际意思 |
| --- | --- |
| `主要输出` | 这一编号结束后留下的证据文件。它说明“系统写出了什么”，不等于“这个阶段已经验收通过”。 |
| `当前测试在检查什么` | 当前自动测试守住的行为，例如文件有没有写出、状态有没有误判、报告字段是否稳定。测试代码不是业务产物，也不是 verifier。 |
| `阶段标准` | 检查器将来应该读取哪个签收标准。标准存在只说明有裁判口径，不等于检查器已启用。 |
| `verifier 状态` | 这个阶段有没有正式检查器参与评测 gate。`not_configured` 表示还没有阶段验收检查器，不能写成 `PASS`。 |

当前测试文件可以这样理解：

| 测试文件 | 它在这里的用途 |
| --- | --- |
| `tests/contract/test_template_generate.py` | 检查 00-05 的业务生成链路能稳定写出过程产物，并保留 source_seq、manifest、debug 文件等排查证据。它不证明 01-05 已经逐阶段验收通过。 |
| `tests/contract/test_real_core_generated_template_gap.py` | 检查 06 的最终模板 gap verifier 能按学校标准输出 `PASS` / `FAIL` / `UNKNOWN`，并写出 tree 和 gap 报告。 |

| 编号 | 阶段 ID | 这个节点做什么 | 主要输入 | 主要输出 | 当前测试在检查什么 | 阶段标准 | verifier 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `00` | `00_input_request` | 记录本次运行拿的是哪个学校原始模板、输出到哪里 | `--template` 指向的学校原始模板 Word、`--out` 输出目录 | 请求记录 JSON、源模板副本 | CLI 能写出请求记录；CLI 只接受模板输入，不接受学校标准作为生成输入 | 不适用 | 输入记录；不作为质量 verifier |
| `01` | `01_source_parse` | 把学校原始模板 Word 解析成源 Word 事实 | `00_input_request` 里的源模板 Word | `source_template_tree.json`；说明源 Word 里实际观察到了哪些段落、表格、页眉页脚和来源序号 | 源元素有连续 `source_seq`，可以通过索引反查原始位置 | `template_generation/01_source_parse_contract.yaml` | `not_configured` |
| `02` | `02_structure_discovery` | 从源 Word 事实识别候选 unit、logical element、角色提示和来源证据 | `source_template_tree.json` | `template_structure_candidates.json`；说明系统把哪些源元素看成候选封面、摘要、正文、说明文字或填写位 | 表格 label/value 合并、跨段落业务句合并、copy-only 内部候选和说明文字识别行为稳定 | `template_generation/02_structure_discovery_contract.yaml` | `not_configured` |
| `03` | `03_generation_model` | 把候选结构整理成模板业务模型和处理策略 | `template_generation_request.json`、`template_structure_candidates.json` | `template_generation_model.json`；说明每个 unit 最终倾向复制、局部 patch、生成 slot、cleanup 或 unresolved question | whole-unit copy、references fillable、copy-only 内部 candidate materialize 等策略行为稳定 | `template_generation/03_generation_model_contract.yaml` | `not_configured` |
| `04` | `04_plan_build` | 把生成模型转成具体 Word action 列表 | `template_generation_model.json` | `template_generation_plan.json`；说明生成器准备对 Word 做哪些动作、每个动作影响哪些源元素 | 每个 action 带 `affected_source_seq_refs[]`；copy-only 和 references 相关 action 类型稳定 | `template_generation/04_plan_build_contract.yaml` | `not_configured` |
| `05` | `05_action_execution` | 先整包复制源 Word，再执行 action，写出生成模板和执行记录 | 源模板 Word、`template_generation_plan.json` | `generated_template.docx`、`template_generation_manifest.json`、copy-only 停点和完整执行后的 debug Word | 生成模板能写出；已有 body slot 不重复；表格说明文字能清理；无效 DOCX 会失败而不是伪装成功 | `template_generation/05_action_execution_contract.yaml` | `not_configured` |
| `06` | `06_final_template_gap` | 检查被测 `generated_template.docx` 是否符合学校 `template_unit_contract.yaml` | 被测 `generated_template.docx`、学校模板单元标准 | `generated_template_tree.json`、`template_gap_report.json/.md/.docx`、最终状态 | gap verifier 能对真实学校和聚焦 fixture 输出 `PASS` / `FAIL` / `UNKNOWN`；样式、页眉页脚、字段、编号等检查不误判 | `template_unit_contract.yaml` | `enabled` |
| `99` | `99_debug_index` | 给调试目录列文件索引，方便人找证据 | debug 目录里的 `00` 到 `05` 快照文件 | `99_template_generation_debug_index.json` | debug 索引包含关键快照，方便从报告跳回过程证据 | 不适用 | 调试索引；不作为质量 verifier |

读这张表时要注意两个边界：

- `01` 到 `05` 已有三校阶段标准，但测试仍只是“产物链和当前生成行为”的合同测试，不等于这些阶段已经有独立验收 verifier。
- `06_final_template_gap` 的测试才是在验证“最终生成模板是否按学校标准检查，并且 FAIL / UNKNOWN 不能误放成 PASS”。

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

最容易混淆的是“评测代码”和“测试代码”不是同一个东西：

| 代码或文件 | 业务/评测身份 | 复用关系 |
| --- | --- | --- |
| `src/docfit/stages/template_generate/**` | 业务支撑流程 | 负责生产 00-05 的 Word、JSON 和 manifest |
| `src/docfit/harness/generated_template_*` | 产品评测能力 | 负责读取已有 Word 和标准，产出 tree、gap report 和状态 |
| `src/docfit/convert/orchestrator.py` | 产品编排层 | 可以选择跑新 pipeline，也可以作为后续“消费已有产物包”的入口位置 |
| `tests/contract/**` | 测试代码 | 只调用产品能力证明行为稳定，不拥有业务产物语义 |
| `test_outputs/**` | 运行证据 | 不是测试 fixture；它记录某次业务运行和评测运行的结果 |

所以后续做阶段化评测时，正确方向是让评测入口接收一个已有 `template-generate` run 目录或明确的 artifact 列表，再读取其中的产物。只有用户明确要做一次新的业务回归或 e2e 时，才应该重新跑模板生成。

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

为了支持“评测复用业务产物”，聚合产物还需要记录产物来源。以下是建议字段，不是当前已实现输出：

| 字段 | 含义 | 生产者 | 消费者 | 判定影响 | 缺失后果 | AI 边界 |
| --- | --- | --- | --- | --- | --- | --- |
| `artifact_source.kind` | 本次检查消费已有产物包，还是新跑了一次完整 pipeline；建议值如 `existing_template_generate_run`、`fresh_pipeline_run` | 阶段检查聚合入口 | 报告、coverage、人工审计 | 不直接决定 `PASS`，但决定证据解释方式 | 缺失时无法说明评测是不是重跑，应为 `UNKNOWN` | AI 只能解释，不能改写 |
| `artifact_source.run_dir` | 被消费的 `template-generate` 运行目录，里面应有 `summary.json`、顶层 Word 和 `artifacts/*.json` | `template-generate` 运行输出或聚合入口绑定 | 阶段检查器、报告、first_bad_stage 排查 | 证明检查对象来自哪次业务运行 | 复用模式下缺失应为 `UNKNOWN` | AI 不能补造路径或目录内容 |
| `artifact_hashes` | 聚合入口实际读取的关键文件 hash，例如 `generated_template.docx` 和 manifest | 阶段检查聚合入口计算 | 阶段检查器、报告、审计 | hash 不一致时不能证明检查对象一致，应阻断 | 缺失应为 `UNKNOWN` | AI 不能手工编辑 |
| `stage_checks[].input_artifacts` | 每个阶段检查器实际读取的输入文件列表 | 阶段检查聚合入口 | 对应阶段 verifier、报告 | 用来证明 verifier 没有偷换输入 | 已启用 verifier 缺输入时应为 `UNKNOWN` | AI 只能引用 |
| `stage_checks[].output_artifacts` | 每个阶段检查器实际检查的输出文件列表 | 阶段检查聚合入口 | 对应阶段 verifier、报告 | 用来证明检查的是哪个阶段产物 | 已启用 verifier 缺输出时应为 `UNKNOWN` | AI 只能引用 |

## 阶段标准文件

一句话结论：01-05 现在是每个阶段一个人工签收标准文件，不再共用一个 `template_generation_stage_contract.yaml`；每个文件都绑定三校人工 review、上游 `template_unit_contract.yaml#/expected/units`，以及本次正式 `template-generate` 运行观察到的对应阶段产物 hash。

当前每所真实学校都有五份：

```text
standards/schools/<school_id>/v1/template_generation/
  01_source_parse_contract.yaml
  02_structure_discovery_contract.yaml
  03_generation_model_contract.yaml
  04_plan_build_contract.yaml
  05_action_execution_contract.yaml
```

`signed_standard.yaml` 通过 `evidence_baselines.template_generation_stage_contracts` 登记这些文件，键是阶段 ID，值是相对学校标准目录的文件路径。

关键字段含义：

| 字段 | 含义 | 生产者 | 消费者 | 判定影响 | 缺失后果 | AI 边界 |
| --- | --- | --- | --- | --- | --- | --- |
| `baseline_type` | 标明这是模板生成阶段标准，固定为 `template_generation_stage_contract` | 人工 review 转成签收标准时写入 | 阶段检查聚合、合同测试、人工排查 | 不直接决定 `PASS`；用于确认文件类型 | 类型缺失或错误时应为 `UNKNOWN` | AI 可解释，不能擅自改类型 |
| `stage_id` | 说明这个文件只对应哪一个阶段，例如 `02_structure_discovery` | 标准整理流程 | 阶段检查聚合、对应阶段 verifier | 防止拿错阶段标准 | 缺失或和登记键不一致时应为 `UNKNOWN` | AI 只能解释 |
| `accepted_source_facts.*` | 绑定人工 review、源模板 Word、上游 `../template_unit_contract.yaml`、本次校准运行产物路径和 hash | 标准整理流程 | 阶段检查聚合、审计、人工复核 | 证明标准来自已签收人工材料和已生成阶段产物 | 缺失或 hash 不一致时应为 `UNKNOWN` | AI 只能引用，不能补造 hash |
| `expected.final_review_unit_order` | 从人工 review 的单元顺序抽出的目标单元顺序 | `template_unit_contract.yaml#/expected/units` | `02_structure_discovery` 到 `05_action_execution` verifier | 后续 verifier 启用后可参与 `FAIL` / `UNKNOWN` | 缺失时无法检查单元顺序，应为 `UNKNOWN` | AI 不能把当前运行结果反写进标准 |
| `expected.final_review_policy_groups` | 从人工 review 的元素策略抽出的 manual_only、fillable、generated、template_default 等单元分组 | `template_unit_contract.yaml#/expected/units` | `02` 到 `04` verifier、first_bad_stage 排查 | 后续用于检查候选角色、模型策略和 plan action 是否越界 | 缺失时不能证明策略边界，应为 `UNKNOWN` | AI 只能解释策略，不裁定通过 |
| `expected.verifier_requirements` | 这个阶段的最小检查口径 | 人工 review、最终单元标准、阶段边界 | 对应阶段 verifier | 标准存在但 `verifier_state=not_configured` 时不能 `PASS` | 阶段要求缺失时该阶段应为 `missing_standard/UNKNOWN` | AI 可指出缺口，不能补造裁判结果 |
| `expected.calibration_observation` | 本次正式业务流程产物的观察摘要，例如当前候选单元、action 数量、缺失最终单元 | `template-generate` 校准运行 + 人工整理 | 人工排查、first_bad_stage 定位 | 这是校准证据，不是通过证据 | 缺失时仍可保留标准，但无法复核这次校准运行 | AI 可解释，不能把观察值当标准通过 |
| `gate_policy.not_configured_is_not_pass` | 明确未配置检查器不是通过 | 标准文件 | 聚合报告、测试 | 防止阶段产物被误报成 `PASS` | 缺失时聚合报告应保守输出 `UNKNOWN` | AI 不能绕过 |

## 阶段清单

这一节只写 verifier 视角，避免和上面的执行链混淆。

| verifier 阶段 | 检查对象 | 当前检查状态 | 当前建议 |
| --- | --- | --- | --- |
| `01_source_parse` | `source_template_tree.json` 是否完整表达源 Word 事实 | `standard_defined_pending_verifier`；verifier 仍是 `not_configured` | 读取 `template_generation/01_source_parse_contract.yaml` 后，检查源 Word 事实、hash、`source_seq`、`source_ref` |
| `02_structure_discovery` | `template_structure_candidates.json` 是否正确识别候选 unit 和 logical element | `standard_defined_pending_verifier`；verifier 仍是 `not_configured` | 对照 `expected.final_review_unit_order`、`final_review_policy_groups` 和 `source_seq_refs[]` 检查候选边界 |
| `03_generation_model` | `template_generation_model.json` 是否把候选结构转成正确策略 | `standard_defined_pending_verifier`；verifier 仍是 `not_configured` | 对照人工 review 的 unit status/policy/handling 检查策略，不把启发式当签收结论 |
| `04_plan_build` | `template_generation_plan.json` 是否完整表达要执行的 Word action | `standard_defined_pending_verifier`；verifier 仍是 `not_configured` | 检查 action 来源、protected/manual_only 边界和 cleanup 依据 |
| `05_action_execution` | `generated_template.docx` 和 `template_generation_manifest.json` 是否与 plan 对齐 | `standard_defined_pending_verifier`；verifier 仍是 `not_configured` | 检查 manifest/hash/action 执行证据，并把最终质量交给 `06_final_template_gap` |
| `06_final_template_gap` | `generated_template.docx` 是否满足 `template_unit_contract.yaml` | `enabled` | 当前第一个可运行示例，继续使用现有 `template-gap` |

这张表的重点是先把“有产物”和“产物已验收”分开。前五个阶段现在可以有产物、可以有 debug、可以被人工排查，但不能因为命令跑完就算阶段验证通过。

阶段清单的输入应该来自同一个 artifact bundle。比如 `02_structure_discovery` 读取的 `source_template_tree.json`，必须和 `05_action_execution` 的 manifest 指向同一次源模板运行；如果聚合入口只能找到零散文件但不能证明它们属于同一次 run，状态应是 `UNKNOWN`，不是自动拼起来继续判定。

## 聚合状态规则

| 情况 | 聚合时怎么表达 |
| --- | --- |
| 已启用检查器返回 `FAIL` | 聚合结果必须阻断；报告列出失败项和对应阶段 |
| 已启用检查器返回 `UNKNOWN` | 聚合结果必须阻断；报告说明缺证据、缺标准或检查器不足 |
| 已启用检查器全部 `PASS`，但有阶段 `not_configured` | 可以说明“当前已启用检查通过”，但不能声称所有阶段都已验证 |
| 阶段没有标准或检查器 | 写 `verifier_state = not_configured` 或 `missing_standard`，不要写 `PASS` |
| 最终 gap 失败但中间阶段未配置检查器 | 报告先给最终失败，再用现有产物帮助人工追溯，不伪造中间阶段结论 |
| 复用已有产物包但关键文件缺失 | 对缺失文件对应阶段写 `UNKNOWN`，不要自动重跑生成器补文件 |
| 复用已有产物包但 hash 或 manifest 对不上 | 聚合结果必须阻断，先提示证据串错或来源不一致 |

`template_generate` 自己的执行状态和评测状态也要分开：

| 状态 | 含义 |
| --- | --- |
| 生成执行 `PASS` | 命令完成并写出了预期产物 |
| 阶段检查 `PASS` | 某个已启用检查器证明对应产物符合标准 |
| 最终 gap `PASS` | 被测生成模板符合学校签收的模板差距标准 |

## 关键边界

- 本文说的模板最终产物只指 `generated_template.docx`、`generated_template_tree.json` 和 `template_gap_report.*`。
- `template_generate` 的输入只有学校原始模板 Word；不读取内容提取产物、放置计划或最终论文渲染结果。
- `template_generate` 也不应该把 `standards/schools/**` 当成正常生成输入；这些标准是已知样例的评测和验收材料。
- 如果识别出某个位置是用户填写位，它就是生成模板里的填写位；这件事来自源模板自身的结构、文字、样式、占位符、字段和产品规则，不来自后续业务阶段。
- 内容提取、内容放置和最终论文渲染属于后续业务评测，不作为模板生成评测的输入、裁判依据或最终产物。
- `template_generation_manifest.json` 只能证明生成器执行了什么，不能证明最终 Word 符合学校标准。
- `generated_template_tree.json` 是从被测 Word 解析出来的事实证据；`template_gap_report.*` 是检查结果；两者都不是学校标准本身。
- 评测复用已有产物时，只能消费已有 Word、JSON、manifest 和 hash；缺失证据要暴露为 `UNKNOWN`，不能用重新生成来填洞。
- 重新跑模板生成只适用于明确的 fresh pipeline / e2e 回归；它会产生新证据，不能反过来证明旧 run 的中间阶段。
- AI 可以读报告帮助解释和归因，不能决定 `PASS`、`FAIL` 或 `UNKNOWN`。

## 测试策略

当前已有测试分工：

| 测试文件 | 当前数量 | 覆盖阶段 | 当前证明什么 | 不证明什么 |
| --- | --- | --- | --- | --- |
| `tests/contract/test_template_generate.py` | 11 个测试 | `00` 到 `05`，以及 `99` debug index | 模板生成能写出完整产物链、debug 编号稳定、`source_seq` 可追踪、阶段二合并和 copy-only 策略行为稳定 | 不证明 `01` 到 `05` 已经有独立 verifier；不证明最终 Word 符合学校标准 |
| `tests/contract/test_real_core_generated_template_gap.py` | 33 个测试 | `06_final_template_gap` | 最终 `template-gap` 能对真实学校和聚焦 fixture 输出 `PASS` / `FAIL` / `UNKNOWN`，并写出 tree 和报告 | 不证明 `01` 到 `05` 的中间产物已经逐阶段验收 |
| `tests/contract/test_real_core_baseline_harness.py` | 覆盖 real-core 标准登记 | 三校标准入口 | 15 个 `template_generation/*_contract.yaml` 存在、可解析、绑定到 `signed_standard.yaml`，并且 `not_configured` 不会被写成 `PASS` | 不证明阶段 verifier 已经实现 |

按阶段看当前测试输入输出：

| 阶段 | 测试输入 | 测试输出或断言 |
| --- | --- | --- |
| `00_input_request` | 测试临时生成的学校模板 DOCX；CLI 参数 `--template`、`--out` | 请求 JSON、summary、debug 00 文件存在；CLI 不接受 `--school` |
| `01_source_parse` | 测试模板 DOCX 里的段落和表格 | `source_template_tree.json` 存在，`source_seq` 连续，`indexes.by_source_seq` 可反查 |
| `02_structure_discovery` | `source_template_tree.json` 里的可见节点 | `template_structure_candidates.json` 里有 unit、element、`source_seq_refs[]`、`merge.type`、`role_hint` |
| `03_generation_model` | `template_structure_candidates.json` 和 request | `template_generation_model.json` 里有 `unit_strategies[]`、最终 `policy`、`slots[]`、`cleanup[]` |
| `04_plan_build` | `template_generation_model.json` | `template_generation_plan.json` 里 action 类型正确，并带 `affected_source_seq_refs[]` |
| `05_action_execution` | 源模板 DOCX 和 `template_generation_plan.json` | `generated_template.docx`、manifest、`05.0`、`05.1`、`05.2` 存在；说明文字被清理；slot 行为正确 |
| `06_final_template_gap` | 被测 `generated_template.docx` 和 `template_unit_contract.yaml` | `generated_template_tree.json`、`template_gap_report.*` 存在；状态组合、样式、页眉页脚、字段、编号等检查不误判 |
| `99_debug_index` | debug 快照目录 | `99_template_generation_debug_index.json` 包含关键快照文件名 |

后续补阶段化评测骨架时，最小测试应覆盖：

| 测试目标 | 期望 |
| --- | --- |
| 阶段清单稳定 | 报告里列出 `01_source_parse` 到 `06_final_template_gap` |
| 阶段标准入口稳定 | 三校 `signed_standard.yaml` 都引用 `template_generation/01_source_parse_contract.yaml` 到 `05_action_execution_contract.yaml` |
| 阶段标准不伪装成通过 | 标准文件里 `gate_policy.not_configured_is_not_pass = true`，01-05 的 `gate_enabled = false` |
| 未配置阶段不伪装成通过 | `verifier_state = not_configured` 时没有 `status = PASS` |
| 最终 gap 作为示例接入 | `06_final_template_gap` 能复用现有 gap 检查结果 |
| 已有产物包复用 | 给定一个已有 `template-generate` run 目录时，聚合检查读取现有文件，不重新调用生成器 |
| 缺最终 gap 输入 | 返回 `UNKNOWN`，不能跳过检查后成功 |
| 缺中间产物或 hash 不一致 | 返回 `UNKNOWN` 或阻断失败，报告说明证据来源不一致 |
| 聚合报告可读 | 人能看到哪些检查启用、哪些只是等待标准 |

## 当前最小落地顺序

1. 已完成：三校 01-05 阶段标准已拆成 `template_generation/*_contract.yaml`，并在 `signed_standard.yaml` 中登记。
2. 下一步定义“已有 `template-generate` run 目录 / artifact bundle”作为阶段检查聚合的输入。
3. 新增阶段检查聚合结构，只登记阶段、产物路径、hash、标准路径和检查状态。
4. 把现有 `template-gap` 挂成 `06_final_template_gap` 的第一个已启用检查器，并让它消费同一个 bundle 里的 `generated_template.docx`。
5. 让 01-05 未配置 verifier 的阶段明确显示 `not_configured`，不参与 gate，也不显示成 `PASS`。
6. 每补一个检查器，都补合同测试证明它的 `PASS` / `FAIL` / `UNKNOWN` 行为，以及复用已有产物时不会偷偷重跑生成器。

这样做的目的不是把架构写大，而是防止两个误判：一是最终 gap 失败时不知道从哪里追；二是中间阶段只有产物却被误认为已经验收通过。
