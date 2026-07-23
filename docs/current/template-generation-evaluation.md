# 模板生成评测与测试架构

Last updated: 2026-07-11

> 迁移提示：本文描述的是 2026-06-22 以前的模板生成评测设想和 01-05
> 阶段检查骨架。当前已实现的阶段 verifier、artifact 名称和输出文件以
> `docs/current/template-generation.md` 以及
> `docs/plans/template-parse-refactor-verification.md` 为准。

一句话结论：这份文档只说明模板生成相关的“怎么验、测试怎么组织、报告怎么聚合”。首选真实全流程入口是 `docfit template verify`：它运行一次业务生成，再复用同一次 run 的产物做 `template-gap`、`template-generation-judge`、route-eval 和 `full_summary` 汇总。旧 `template-generation-full` 仍作兼容 alias。

阶段标准本身如何准备、后续给哪些环节使用，以及标准质量衡量和运行时 verify 报告的区别，见 `docs/current/template-generation-stage-standards.md`。

## 文档范围

本文关注评测层和测试层：

| 范围内 | 范围外 |
| --- | --- |
| 最终 `06.1_fillable_template.docx` 是否符合学校标准 | 模板生成五步内部应该怎么重写 |
| 每个阶段产物将来如何接检查器 | 每个阶段最终有哪些业务字段 |
| 检查结果如何表达 `PASS` / `FAIL` / `UNKNOWN` | 某个 unit 应该 `whole_unit_copy` 还是局部 patch |
| 如何从最终模板 gap 追溯到 01-05 哪个模板生成阶段先出错 | 用最终 gap 直接改写源模板事实、manifest 或生成策略 |
| 业务生成产物如何作为评测输入复用 | 让评测代码改写业务生成产物 |
| 测试应该证明哪些评测行为 | 自动更新学校标准、golden 或 expected snapshot |

这里说的“阶段检查器”在代码里可以叫 verifier。它的普通含义是：读取某个阶段的输入和输出，用已定义标准判断这个阶段是否可证明正确，然后产出状态和问题列表。

## 两层评测

模板生成相关评测分成三层，不要混成一件事：

| 层次 | 要回答的问题 | 当前真实状态 | 输入 | 输出 |
| --- | --- | --- | --- | --- |
| 全流程质量汇总 | 一次真实生成后，哪个阶段先坏、各阶段产物质量怎样、下一轮先修什么 | `docfit template verify` 已串起生成、gap、judge、route-eval，并写出 `full_summary.json/md` | `--school`、学校原始模板 Word、学校标准 | `eval_runs/*`、`full_summary.json/md`、阶段问题、owner、next verification |
| 最终结果验证 | 最终 `06.1_fillable_template.docx` 是否符合学校签收标准 | `template-gap` 是最终 Word 质量检查器，可单独跑，也会被 full 入口调用 | `06.1_fillable_template.docx`、`final_template.expected.yaml` | `generated_template_tree.json`、`template_gap_report.*`、状态 |
| 阶段产物验证 | 每个中间阶段的输出是否符合该阶段标准 | `template-generation-judge` 消费已有 run bundle，输出 T1-T5 阶段标准裁判、root cause、owner 和 route-eval | 某次 `template-generate` run、对应阶段标准文件 | 阶段状态、问题列表、可疑的首次出错阶段、四层诊断 |

日常验收优先跑 `docfit template verify`。只有需要复用已有 run 或缩小问题范围时，才用 `template inspect`、`template-generation-judge` 或 `template-gap`。

## 业务产物如何进入评测

一句话结论：`template verify` 会先跑一次 `template generate`，随后所有评测都消费这一次留下的 `06.1_fillable_template.docx`、阶段编号产物、manifest 和根目录索引；已有这些文件时，单独评测入口不应该再调用生成器造一套新文件。

当前真实实现和目标边界要分开看：

| 情况 | 当前真实实现 | 应该表达的边界 |
| --- | --- | --- |
| 全流程质量入口 | `docfit template verify` 会在同一 run root 下运行 generate、`template-gap`、`template-generation-judge` 和 route-eval | 这是当前日常验收入口；质量 FAIL 必须如实写入 `full_summary.json/md`，不能为了入口通过绕开门禁 |
| 单独跑业务模板生成 | `docfit template generate` 会运行 00-07，并写出唯一编号产物、`run_manifest.json` 和 `99_template_generation_debug_index.json` | 这是产物生产者，不是学校标准裁判 |
| 单独跑最终 gap | `docfit eval template-gap --generated-template <已有 Word>` 可以直接检查已有 `06.1_fillable_template.docx` | 评测可以消费已有 Word，不需要重新跑 00-07；它是 full 的最终 Word 检查组件，不是唯一全流程入口 |
| real-core 的 `template` / `e2e` 流程 | 当前会在同一个 pipeline 里重新跑模板生成，再把这次生成的 Word 交给 gap | 这是“新跑一遍完整链路”的模式，不等于已有产物包复用模式 |
| T1-T5 阶段产物评测聚合 | `template-generation-judge` 已能消费已有 `template-generate` run 目录 | 读取已有产物包、hash 和 manifest；缺产物时返回 `UNKNOWN`，不能静默重跑 |

复用已有产物包时，评测层只做三件事：

| 动作 | 说明 |
| --- | --- |
| 读取 | 读取同一次 `template-generate` 运行留下的 `summary.json`、`06.1_fillable_template.docx`、阶段编号产物和根目录索引 |
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
| 全流程质量入口 | `docfit eval template-generation-full` 能写出 `eval_runs/template_generate`、`eval_runs/template_gap`、`eval_runs/template_generation_judge`、`full_summary.json/md` | 这是首选验收入口；`full_summary` 必须说明 overall status、first_bad_stage、stage cards、route mismatch、owner、top blockers 和 next verification |
| 模板生成命令 | `docfit eval template-generate` 能写出 `01_document_facts.json`、`02_unit_map.yaml`、`03_element_spec.yaml`、`04_global_spec.yaml`、`05_template_spec.yaml`、`06.1_fillable_template.docx` 和 `06.2_build_manifest.json`；不再写 `artifacts/` 镜像、human 快照或未编号 Word | 这个命令返回 `PASS` 只说明生成流程完成，不说明 Word 已符合学校标准 |
| 最终 gap 检查 | `docfit eval template-gap` 会检查被测 `06.1_fillable_template.docx` | 这是最终 Word 质量检查器；full 入口会调用它并把结果并入 `POST_T6` stage card |
| 已有产物复用 | 最终 gap 和 `template-generation-judge` 都可以直接消费已有 `template-generate` run | 如果只想检查已有 Word，跑 `template-gap`；如果要检查 run bundle 和 T1-T5 阶段标准质量，跑 `template-generation-judge` |
| 阶段标准 | 三校已有 `standards/targets/<target_id>/v1/template_generation/*.standard.yaml`，T1/T2/T3/T4/T5 均使用阶段专用标准文件，且 real-core gate 已开启 | T1 覆盖源 DOCX 事实；T2 覆盖单元识别、顺序、边界范围和分页归属；T3 覆盖元素策略；T4 覆盖全局版式；T5 覆盖 `template_spec` 合并契约。标准来自人工 review 和 `template_quality/final_template.expected.yaml#/expected/units`，不是运行产物 |
| 阶段检查聚合 | 已有“阶段产物 -> 标准文件 -> 检查器 -> 状态/问题 -> 聚合报告”骨架 | `template-generation-judge` 输出 `template_generation_stage_checks.json`、编号化阶段报告和聚合 judge report |
| 合同测试 | `tests/contract/test_template_generate.py` 覆盖模板生成产物链；`tests/contract/test_real_core_generated_template_gap.py` 覆盖最终 gap | 现有测试还没有证明阶段检查聚合架构存在 |

因此，当前最小目标已经从“留出评测架构位置”推进到“用 full 入口生成可行动质量报告”：哪些检查已启用、哪些产物不一致、root cause/owner 是什么，都应进入 `full_summary.json/md`，其中 `template-generation-judge` 负责阶段标准诊断，`template-gap` 负责最终 Word gap。

## 相关目录树

```text
docs/current/template-generation-evaluation.md  # 本文；只定义模板生成评测和测试边界。

standards/
  targets/<target_id>/v1/target.standard.yaml  # 目标模板评测标准入口。
  targets/<target_id>/v1/template_generation/  # 模板生成阶段标准；T1-T5 使用阶段专用标准文件。
    t1_document_facts.standard.yaml
    t2_unit_pagination.standard.yaml
    t3_element_policy.standard.yaml
    t4_global_layout.standard.yaml
    t5_template_spec.standard.yaml
  targets/<target_id>/v1/template_quality/final_template.expected.yaml  # 06_final_template_gap 的检查标准。

eval_profiles/
  real-core-v0/profile.yaml  # 真实学校评测 case 绑定。

src/docfit/cli/main.py  # 暴露 template-generation-full、template-generate、template-gap、template-generation-judge。
src/docfit/convert/orchestrator.py  # full/generate/gap 运行入口和 full_summary 汇总位置。
src/docfit/template_gap/
  inspector.py  # 读取被测 06.1_fillable_template.docx，产出 generated_template_tree.json。
  gap.py  # 对照 final_template.expected.yaml，产出 template_gap_report.* 和状态。
src/docfit/harness/
  coverage.py  # coverage gate 读取 gap 证据，发现缺失或阻断问题。
  reports.py  # 写 summary.json、pm_report.md 和 findings.json。

tests/contract/
  test_real_core_generated_template_gap.py  # 锁住 06_final_template_gap 的 PASS / FAIL / UNKNOWN 行为。

inputs/targets/<target_id>/fixtures/template_gap/
  real-core-v0-<school_id>-generated-template.docx  # 当前 06_final_template_gap 的被测模板 fixture。

<template-generate-run>/  # 后续阶段检查应复用的已有业务产物包；不是 verifier 本身。
  06.1_fillable_template.docx
  artifacts/*.json

<template-gap-out>/artifacts/  # template-gap 评测输出证据。
  06.1_fillable_template.docx
  generated_template_tree.json
  template_gap_report.json
  template_gap_report.md
  template_gap_report.docx

<template-generation-full-run>/  # 首选真实全流程质量输出。
  eval_runs/template_generate/
  eval_runs/template_gap/
  eval_runs/template_generation_judge/
  full_summary.json
  full_summary.md
```

## 阶段编号

一句话结论：`template-generation-full` 的质量报告使用 `T1/L1/T2/T3/T4/T5/T6/T7/POST_T6` 九个 stage cards。`00` 输入记录和 `99` debug index 仍会落盘，但不作为质量 stage card。

评测阶段命名必须和模板生成阶段产物编号对齐。这样人看报告时，可以直接从检查结果跳到同编号的产物文件。T1-T5 由 `template-generation-judge` 的阶段标准 verifier 裁判；T6/T7 来自运行时构建与 verification report；POST_T6 来自 `template-gap`；L1 来自统一输入投影、render/object binding 和 route-eval。

读这张表前，先把三个容易混淆的词分开：

| 表里的列 | 实际意思 |
| --- | --- |
| `主要输出` | 这一编号结束后留下的证据文件。它说明“系统写出了什么”，不等于“这个阶段已经验收通过”。 |
| `当前测试在检查什么` | 当前自动测试守住的行为，例如文件有没有写出、状态有没有误判、报告字段是否稳定。测试代码不是业务产物，也不是 verifier。 |
| `阶段标准` | 检查器读取的签收标准。标准存在说明有裁判口径；是否参与 gate 由 `verifier_state` 和 `gate_enabled` 决定。 |
| `verifier 状态` | 这个阶段有没有正式检查器参与评测 gate。`not_configured` 表示还没有阶段验收检查器，不能写成 `PASS`。 |

当前测试文件可以这样理解：

| 测试文件 | 它在这里的用途 |
| --- | --- |
| `tests/contract/test_template_generate.py` | 检查 00-05 的业务生成链路能稳定写出过程产物，并保留 source_seq、manifest、debug 文件等排查证据。它不证明阶段标准验收通过。 |
| `tests/contract/test_template_generation_standard_judge.py` | 检查 `template-generation-judge` 和 `template-generation-full` 能输出阶段标准裁判、route-eval 和 `full_summary.quality_report.stage_cards[]`。 |
| `tests/contract/test_real_core_generated_template_gap.py` | 检查 POST_T6 的最终模板 gap verifier 能按学校标准输出 `PASS` / `FAIL` / `UNKNOWN`，并写出 tree 和 gap 报告。 |

| 编号 | 阶段 ID | 这个节点做什么 | 主要输入 | 主要输出 | 当前测试在检查什么 | 阶段标准 | verifier 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `00` | `00_input_request` | 记录本次运行拿的是哪个学校原始模板、输出到哪里 | `--template` 指向的学校原始模板 Word、`--out` 输出目录 | 请求记录 JSON、源模板副本 | CLI 能写出请求记录；CLI 只接受模板输入，不接受学校标准作为生成输入 | 不适用 | 输入记录；不作为质量 verifier |
| `T1` | `t1_document_facts` | 把学校原始模板 Word 解析成源 DOCX 事实 | `00_input_request` 里的源模板 Word | `01_document_facts.json`；旧 source tree 只在运行内派生 | 源元素有连续 `source_seq`，可以通过索引反查原始位置；T1 不输出 unit、policy 或 confidence | `template_generation/t1_document_facts.standard.yaml` | `configured / gate_enabled=true` |
| `L1` | `l1_input_contract` | 把 T1 和 render/object/page/run 事实封存成下游唯一事实输入 | `01_document_facts.json`、render facts、对象/page 绑定证据 | `01.5_l1_input_contract.json`、`01.6_t2_l1_stage_input.json`、`01.8_t4_l1_stage_input.json` | render 状态、page/object/run binding、T1/L1 禁止语义越界、canonical hash、route shared input 可用性 | 由 route-eval 和 L1 coverage gate 裁判 | `enabled` |
| `T2` | `t2_unit_pagination` | 从 L1 事实识别模板单元、单元顺序、边界范围和分页归属 | `01.6_t2_l1_stage_input.json` | `02_unit_map.yaml`；structure candidates 只在运行内派生 | 三校单元顺序、关键边界、source_seq 归属和分页口径有签收标准 | `template_generation/t2_unit_pagination.standard.yaml` | `configured / gate_enabled=true` |
| `T3` | `t3_element_policy` | 在唯一 T2 最终结果的单元内，由 AI 把 sealed L1 内容判断并物化为元素策略 | `03.0_t3_hierarchical_stage_input.json`，绑定 sealed L1 与本次运行唯一 T2 最终结果 | 唯一正式结果 `03_element_spec.yaml`；AI observation、sparse trace 和 materialization trace 只作自检证据 | AI canonical policy/fill_source/generated/source trace 稳定，tree/identity/coverage/materialization 自检闭合，availability 如实下传 | `template_generation/t3_element_policy.standard.yaml` | `configured / gate_enabled=true` |
| `T4` | `t4_global_layout` | 从 L1 整理全局页面、分节、页眉页脚、页码和编号规则 | `01.8_t4_l1_stage_input.json` | `04_global_spec.yaml`；说明 section profile、boundary、page numbering、header/footer 和 numbering evidence | section profile 唯一、boundary 可回溯、页码证据和页眉页脚 part 引用稳定 | `template_generation/t4_global_layout.standard.yaml` | `configured / gate_enabled=true` |
| `T5` | `t5_template_spec` | 合并 unit、element 和 global 规则，形成模板解析主规格 | T2/T3/T4、sealed L1 hash/identity | `05_template_spec.yaml`；说明单元、元素、section profile、review flags 和 input hashes 的绑定 | unit 顺序、unit-section 绑定、元素策略保留、review flag 和 L1 hash 稳定 | `template_generation/t5_template_spec.standard.yaml` | `configured / gate_enabled=true` |
| `T6` | `t6_fillable_template` | 根据 template_spec 构建可填写 Word 模板并记录 action 证据 | `05_template_spec.yaml`、源 DOCX package、sealed L1 resolver/hash | `06.1_fillable_template.docx`、`06.2_build_manifest.json` | source hash、identity/precondition、无内部 marker、SDT/action evidence、build manifest 可追溯 | 运行时 verification + route-eval | `enabled` |
| `T7` | `t7_verification_report` | 汇总 T1-T6 的运行时验证状态 | L1、T5/T6、最终 DOCX | `07_verification_report.json` | canonical L1 hash、runtime verification 状态、first_bad_stage、输出 hash | 运行时 verification + route-eval | `enabled` |
| `POST_T6` | `post_t6_template_gap` | 检查被测 `06.1_fillable_template.docx` 是否符合学校 `final_template.expected.yaml` | 被测 `06.1_fillable_template.docx`、学校模板单元标准 | `generated_template_tree.json`、`template_gap_report.json/.md/.docx`、最终状态 | gap verifier 能对真实学校和聚焦 fixture 输出 `PASS` / `FAIL` / `UNKNOWN`；样式、页眉页脚、字段、编号等检查不误判 | `final_template.expected.yaml` | `enabled` |
| `99` | `99_debug_index` | 给调试目录列文件索引，方便人找证据 | debug 目录里的 `00` 到 `05` 快照文件 | `99_template_generation_debug_index.json` | debug 索引包含关键快照，方便从报告跳回过程证据 | 不适用 | 调试索引；不作为质量 verifier |

读这张表时要注意两个边界：

- T1 到 T5 已有三校阶段标准和独立阶段 verifier；是否可签收仍取决于某次 run 的 `template-generation-judge` 报告。
- POST_T6 的测试才是在验证“最终生成模板是否按学校标准检查，并且 FAIL / UNKNOWN 不能误放成 PASS”。
- `full_summary.quality_report.stage_cards[]` 是人读的全链路质量索引，不替代各子报告里的完整证据。

## 检测逻辑和字段层次

一句话结论：00 只有“这次运行是谁、输入是什么”的请求字段；01 开始把 Word 拆成事实层；02 才引入候选 unit / element；03 把候选变成生成策略；04 变成 Word action；05 记录实际执行；06 才把最终生成模板和学校签收标准做确定性比对。

先区分当前真实实现和目标检测口径：

| 范围 | 当前真实实现 | 文档里的检测逻辑指什么 |
| --- | --- | --- |
| `01` 到 `05` | 有产物、合同测试、三校阶段标准和已启用阶段 verifier | `template-generation-judge` 读取同一次 run bundle 后，可以对 T1-T5 输出标准验收 `PASS` / `FAIL` / `UNKNOWN` |
| `06_final_template_gap` | 已有可运行 verifier | 当前真的会读取 `06.1_fillable_template.docx` 和 `final_template.expected.yaml`，生成 `template_gap_report.*` 并输出 `PASS` / `FAIL` / `UNKNOWN` |

最开始只有这些输入和字段：

| 起点 | 字段或证据 | 含义 |
| --- | --- | --- |
| 学校原始模板 Word | `.docx` 包本身 | 这是业务输入，还没有 JSON 层次，也没有 unit、element、policy 或 action |
| `template_generation_request.json` | `artifact_type`、`artifact_version`、`created_at`、`source_template_docx`、`source_template_hash`、`out_dir`、`strategy`、`optional_labels` | 只记录这次运行的输入、输出目录、hash 和策略；不判断模板内容 |

每个阶段新增的层次和关键字段：

| 阶段 | 新增层次 | 新字段或字段组 | 这些字段用来做什么 |
| --- | --- | --- | --- |
| `t1_document_facts` | `document_facts` | `metadata`、`body_flow`、`runs`、`data.sections`、`data.headers_footers`、`data.fields`、`data.numbering_definitions`、`data.numbering_refs`、`data.images`、`indexes`、`warnings` | 把 Word 里的段落、表格、页眉页脚、分节、字段、编号和未知对象保存成事实证据；后续只能引用这些事实，不能改写事实 |
| `t1_document_facts` | `body_flow[]` / `runs[]` | `source_seq`、`source_ref`、`part_name`、`paragraph_id`、`run_id`、`text`、`style_details`、`table/cell` 定位、字段和对象 trace | 给每个可见源元素一个稳定定位。`source_seq` 是后续追溯 first_bad_stage 的主锚点 |
| `t2_unit_pagination` | `unit_map` | `unit_id`、`name`、`order`、`status`、`source_refs`、`source_seq_refs`、`source_range`、`source_seq_range`、`anchors`、`page`、`boundary_signals`、`open_questions` | 把源事实组织成 T2 单元和分页归属；只负责单元/边界/分页，不负责 T3 元素策略 |
| `t2_unit_pagination` | `template_structure_candidates` 调试视图 | `source_template_hash`、`input_hashes.document_facts`、`discovery_method`、`source_context`、`units[]`、`unknowns`、`open_questions` | 兼作调试证据；标准入口不再使用旧结构发现标准文件 |
| `t3_element_policy` | `element_spec` | `artifact_type`、`input_hashes.template_generation_model`、`elements[]`、`ontology_ref`、`ai_traces`、`flags` | 把候选结构整理成元素策略：哪些固定、哪些填写、哪些人工填写、哪些生成、哪些说明文字删除 |
| `t3_element_policy` | `elements[]` | `stable_id`、`unit_id`、`order`、`policy`、`role`、`fill_source`、`manual_semantics`、`generated.field_type`、`source_refs`、`source_seq_refs`、`confidence` | 保留元素策略和证据链；fill 必须有来源，manual_only 必须有人填语义，generated 必须有字段类型 |
| `t4_global_layout` | `global_spec` | `artifact_type`、`section_profiles`、`default_font`、`page_numbering`、`header_footer`、`numbering_rules`、`flags` | 把源 Word 的全局版式事实整理成 section/page/header/footer/numbering 规则 |
| `t4_global_layout` | `section_profiles[]` | `section_profile_id`、`source_ref`、`boundary`、`page_numbering.display.status`、`header_footer.effective_references`、`flags` | 证明分节边界和页码/页眉页脚证据来自 T1 事实，而不是后续猜测 |
| `t5_template_spec` | `template_spec` | `document_facts_ref`、`input_hashes`、`global`、`units[]`、`review_flags`、`review_decisions` | 合并 `unit_map`、`element_spec` 和 `global_spec`，形成模板解析阶段主产物 |
| `t5_template_spec` | `units[]` | `unit_id`、`source_seq_refs`、`section_profile_refs`、`elements[]`、`flags` | 保留单元顺序、元素策略、section profile 绑定和 review flags |
| `06_final_template_gap` | `generated_template_tree` + `template_gap_report` | `generated_template.path/source_path/sha256`、`standard.path/sha256`、`input`、`units[]`、`global_checks`、`unmodeled_objects`、`summary`、`coverage` | 读取最终 Word 的实际结构，并和学校 `final_template.expected.yaml` 比对，输出真正的阻断状态 |

模板生成阶段标准文件也有自己的字段层次。它们不是运行产物，而是未来 verifier 的裁判口径：

| 标准字段 | 含义 |
| --- | --- |
| `baseline_type`、`profile_id`、`school_id`、`stage_id`、`standard_id` | 说明这份标准属于哪个学校、哪个 profile、哪个模板生成阶段 |
| `standard_state`、`verifier_state`、`gate_enabled` | 说明标准是否已签收、检查器是否启用；real-core T1-T5 当前是 `signed_active` + `configured` + `true` |
| `review_metadata` | 谁 review、来源在哪里、为什么改、是否允许自动更新 |
| `accepted_source_facts` | 绑定人工 review、源模板 Word、上游 `final_template.expected.yaml` 和 hash |
| `expected.final_review_unit_order` | 通用阶段标准中的人工签收最终单元顺序；T2 专用标准改用 `expected.unit_order` |
| `expected.final_review_unit_summaries` | 每个单元的名称、顺序、状态、策略、元素数量和处理口径摘要 |
| `expected.final_review_policy_groups` | manual_only、fillable、generated、template_default、fixed/protected 等单元分组 |
| `expected.stage_boundary` | 这个阶段读什么、写什么、检查什么、不允许做什么 |
| `expected.verifier_requirements` | 这个阶段 verifier 最少要检查哪些字段 |
| `dimensions[]` | 将来 verifier 可直接执行的比较维度，例如 exact、subset、ordered_sequence |

阶段 verifier 的检测逻辑按这个顺序走：

| 阶段 | 应该怎么检测 | 出错时怎么判 |
| --- | --- | --- |
| `t1_document_facts` | 读取 `t1_document_facts.standard.yaml` 和 `01_document_facts.json`；检查 `artifact_type`、源模板 hash、必需事实类别 `body_flow/runs/tables/headers_footers/sections/fields/numbering_definitions/unknown_objects`、`source_seq` 连续性、`source_ref` 和索引可回查，并确认没有 T2/T3 语义判断字段 | 文件缺失、hash 对不上、必需事实类别缺失或定位字段缺失应为 `UNKNOWN`；事实明显不完整或 T1 输出 `unit_id/policy/confidence` 等语义字段时可为 `FAIL` |
| `t2_unit_pagination` | 读取 `t2_unit_pagination.standard.yaml` 和 `02_unit_map.yaml`；检查单元顺序、边界、关键 `source_seq_refs` 和分页口径是否符合三校标准 | 无法证明单元来自源事实时 `UNKNOWN`；单元边界、顺序或分页归属明显错时 `FAIL` |
| `t3_element_policy` | 读取 `t3_element_policy.standard.yaml` 和 `03_element_spec.yaml`；检查 policy、role、fill_source、manual_semantics、generated.field_type、source refs 和 confidence flags 是否符合人工 review 的 status/policy/handling | 策略证据缺失为 `UNKNOWN`；把 manual_only 当 fill、把说明文字保留进最终模板等为 `FAIL` |
| `t4_global_layout` | 读取 `t4_global_layout.standard.yaml` 和 `04_global_spec.yaml`；检查 section profile、boundary、page numbering、header/footer part、numbering rules 和 flags 是否可回溯到 T1 事实 | section boundary、页码证据或 header/footer part 缺失为 `UNKNOWN`；检测到页码但缺 PAGE 字段证据为 `FAIL` |
| `t5_template_spec` | 读取 `t5_template_spec.standard.yaml` 和 `05_template_spec.yaml`；检查 unit 顺序、unit-section refs、range overlap、元素策略保留、input hashes 和 review flags | unit 无法绑定 section 为 `UNKNOWN`；引用不存在、range 不相交或 fill_source 丢失为 `FAIL` |
| `06_final_template_gap` | 当前已实现：复制被测 Word 到评测输出目录，解析成 `generated_template_tree.json`，读取 `final_template.expected.yaml#/expected/units`，按单元、元素、样式、页眉页脚、页码、字段、编号和未知对象生成检查项，再汇总状态 | 任一检查项 `FAIL` 则最终阻断；有 `UNKNOWN` 且无 `FAIL` 也阻断；全部可证明才 `PASS` |

这里有两个关键约束：

- 阶段产物字段是证据链，不是越多越好。新增字段必须说明生产者、消费者、门禁影响、缺失后果和 AI 边界。
- 模板生成阶段标准文件是裁判口径；real-core T1-T5 已接入阶段 verifier 和聚合入口。非 real-core 或 fixture 仍可能保持 `not_configured`，不能误报 PASS。

## 产品评测能力和测试代码边界

| 文件或目录 | 身份 | 当前用途 |
| --- | --- | --- |
| `src/docfit/cli/` | 产品 CLI 入口 | 暴露 `docfit eval template-generate` 和 `docfit eval template-gap` |
| `src/docfit/convert/orchestrator.py` | 产品评测编排代码 | 串联 eval 命令、产物写出、报告写出 |
| `src/docfit/template_gap/inspector.py` | 产品评测能力 | 读取被测 Word，生成 `generated_template_tree.json` |
| `src/docfit/template_gap/gap.py` | 产品评测能力 | 用 `final_template.expected.yaml` 对照 Word 解析证据，生成 gap 结果 |
| `src/docfit/template_generation/**` | 产品支撑流程代码 | 生成可填写模板和过程证据；不是测试辅助代码 |
| `tests/contract/**` | 测试代码 | 调用产品能力，证明检查器不会把 `FAIL` / `UNKNOWN` 误放成 `PASS` |
| `runs/**` | 运行证据 | 存放每次 eval 的产物、报告和 debug 文件 |

这意味着：评测代码有一部分确实属于产品能力，例如 inspector、gap checker、orchestrator；测试只是调用这些能力来锁住行为。

最容易混淆的是“评测代码”和“测试代码”不是同一个东西：

| 代码或文件 | 业务/评测身份 | 复用关系 |
| --- | --- | --- |
| `src/docfit/template_generation/**` | 业务支撑流程 | 负责生产 00-05 的 Word、JSON 和 manifest |
| `src/docfit/harness/generated_template_*` | 产品评测能力 | 负责读取已有 Word 和标准，产出 tree、gap report 和状态 |
| `src/docfit/convert/orchestrator.py` | 产品编排层 | 可以选择跑新 pipeline，也可以作为后续“消费已有产物包”的入口位置 |
| `tests/contract/**` | 测试代码 | 只调用产品能力证明行为稳定，不拥有业务产物语义 |
| `runs/**` | 运行证据 | 不是测试 fixture；它记录某次业务运行和评测运行的结果 |

所以后续做阶段化评测时，正确方向是让评测入口接收一个已有 `template-generate` run 目录或明确的 artifact 列表，再读取其中的产物。只有用户明确要做一次新的业务回归或 e2e 时，才应该重新跑模板生成。

## 目标骨架

阶段化评测需要一张统一清单。每一项至少说清：

| 字段 | 含义 |
| --- | --- |
| `stage_id` | 阶段 ID，例如 `t1_document_facts` 或 `06_final_template_gap` |
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
| `artifact_hashes` | 聚合入口实际读取的关键文件 hash，例如 `06.1_fillable_template.docx` 和 `06.2_build_manifest.json` | 阶段检查聚合入口计算 | 阶段检查器、报告、审计 | hash 不一致时不能证明检查对象一致，应阻断 | 缺失应为 `UNKNOWN` | AI 不能手工编辑 |
| `stage_checks[].input_artifacts` | 每个阶段检查器实际读取的输入文件列表 | 阶段检查聚合入口 | 对应阶段 verifier、报告 | 用来证明 verifier 没有偷换输入 | 已启用 verifier 缺输入时应为 `UNKNOWN` | AI 只能引用 |
| `stage_checks[].output_artifacts` | 每个阶段检查器实际检查的输出文件列表 | 阶段检查聚合入口 | 对应阶段 verifier、报告 | 用来证明检查的是哪个阶段产物 | 已启用 verifier 缺输出时应为 `UNKNOWN` | AI 只能引用 |

## 阶段标准文件

一句话结论：模板生成阶段标准不再共用一个 `template_generation_stage_contract.yaml`；T1-T5 均使用阶段专用 `*.standard.yaml`。

当前每所真实学校登记这些文件：

```text
standards/targets/<target_id>/v1/template_generation/
  t1_document_facts.standard.yaml
  t2_unit_pagination.standard.yaml
  t3_element_policy.standard.yaml
  t4_global_layout.standard.yaml
  t5_template_spec.standard.yaml
```

`target.standard.yaml` 通过 `evidence_baselines.template_generation_stages` 登记这些文件，键是阶段 ID，值是相对学校标准目录的文件路径。

关键字段含义：

| 字段 | 含义 | 生产者 | 消费者 | 判定影响 | 缺失后果 | AI 边界 |
| --- | --- | --- | --- | --- | --- | --- |
| `baseline_type` | 标明标准类型；T2/T3/T4/T5 分别为 `template_generation_t2_unit_pagination`、`template_generation_t3_element_policy`、`template_generation_t4_global_layout`、`template_generation_t5_template_spec` | 人工 review 转成签收标准时写入 | 阶段检查聚合、合同测试、人工排查 | 不直接决定 `PASS`；用于确认文件类型 | 类型缺失或错误时应为 `UNKNOWN` | AI 可解释，不能擅自改类型 |
| `stage_id` | 说明这个文件只对应哪一个阶段；T2/T3/T4/T5 专用标准分别写 `T2`、`T3`、`T4`、`T5` | 标准整理流程 | 阶段检查聚合、对应阶段 verifier | 防止拿错阶段标准 | 缺失或和登记键不一致时应为 `UNKNOWN` | AI 只能解释 |
| `accepted_source_facts.*` | 绑定人工 review、源模板 Word、上游 `../template_quality/final_template.expected.yaml`、本次校准运行产物路径和 hash | 标准整理流程 | 阶段检查聚合、审计、人工复核 | 证明标准来自已签收人工材料和已生成阶段产物 | 缺失或 hash 不一致时应为 `UNKNOWN` | AI 只能引用，不能补造 hash |
| `expected.unit_order` | T2/T3/T4/T5 专用标准中的目标单元顺序 | `final_template.expected.yaml#/expected/units` | 对应阶段 verifier | 后续 verifier 启用后可参与 `FAIL` / `UNKNOWN` | 缺失时无法检查单元顺序，应为 `UNKNOWN` | AI 不能把当前运行结果反写进标准 |
| `expected.policy_groups` | 从人工 review 的元素策略抽出的 manual_only、fillable、generated、template_default、fixed 以及 `fixed_units_allow_fill_elements` 等单元分组 | `final_template.expected.yaml#/expected/units` | T3/T5 verifier、first_bad_stage 排查 | 用于检查候选角色、元素策略和 template_spec 合并是否越界；`fixed_units_allow_fill_elements` 只允许固定模板块内部的显式学生填空位，不放宽 manual_only 单元 | 缺失时不能证明策略边界，应为 `UNKNOWN` | AI 只能解释策略，不裁定通过 |
| `expected.*_contract` | 这个阶段的最小检查口径，例如 `element_policy_contract`、`global_layout_contract`、`template_spec_contract` | 人工 review、最终单元标准、阶段边界 | 对应阶段 verifier | 标准存在但 `verifier_state=not_configured` 时不能 `PASS` | 阶段要求缺失时该阶段应为 `missing_standard/UNKNOWN` | AI 可指出缺口，不能补造裁判结果 |
| `expected.calibration_observation` | 本次正式业务流程产物的观察摘要，例如当前候选单元、action 数量、缺失最终单元 | `template-generate` 校准运行 + 人工整理 | 人工排查、first_bad_stage 定位 | 这是校准证据，不是通过证据 | 缺失时仍可保留标准，但无法复核这次校准运行 | AI 可解释，不能把观察值当标准通过 |
| `gate_policy.not_configured_is_not_pass` | 明确未配置检查器不是通过 | 标准文件 | 聚合报告、测试 | 防止阶段产物被误报成 `PASS` | 缺失时聚合报告应保守输出 `UNKNOWN` | AI 不能绕过 |

## 阶段清单

这一节只写 verifier 视角，避免和上面的执行链混淆。

| verifier 阶段 | 检查对象 | 当前检查状态 | 当前建议 |
| --- | --- | --- | --- |
| `t1_document_facts` | `01_document_facts.json` 是否完整表达源 DOCX 事实且不输出语义判断 | `configured / gate_enabled=true` | 读取 `template_generation/t1_document_facts.standard.yaml` 后，检查源 Word 事实、hash、`source_seq`、`source_ref`、索引和禁用字段 |
| `t2_unit_pagination` | `02_unit_map.yaml` 是否正确识别单元、顺序、边界范围和分页归属 | `configured / gate_enabled=true` | 对照 `expected.unit_order`、`expected.units[].boundary`、`expected.units[].page` 和 `source_seq_refs[]` 检查 T2 |
| `t3_element_policy` | `03_element_spec.yaml` 是否把候选结构转成正确元素策略 | `configured / gate_enabled=true` | 对照人工 review 的 unit status/policy/handling 检查元素策略，不把启发式当签收结论 |
| `t4_global_layout` | `04_global_spec.yaml` 是否完整表达页面、分节、页眉页脚、页码和编号规则 | `configured / gate_enabled=true` | 检查 section boundary、page numbering、header/footer part 和 numbering 证据 |
| `t5_template_spec` | `05_template_spec.yaml` 是否正确合并 unit、element 和 global 规则 | `configured / gate_enabled=true` | 检查 unit 顺序、unit-section 绑定、元素策略保留和 review flags |
| `06_final_template_gap` | `06.1_fillable_template.docx` 是否满足 `final_template.expected.yaml` | `enabled` | 当前第一个可运行示例，继续使用现有 `template-gap` |

这张表的重点是先把“有产物”和“产物已验收”分开。前五个阶段现在可以进入标准裁判，但仍必须以 `template-generation-judge` 的阶段报告为准，不能因为 `template-generate` 命令跑完就算阶段验证通过。

阶段清单的输入应该来自同一个 artifact bundle。比如 `t2_unit_pagination` 读取的 `02_unit_map.yaml`，必须和 `t5_template_spec` 读取的 `05_template_spec.yaml` 来自同一次源模板运行；如果聚合入口只能找到零散文件但不能证明它们属于同一次 run，状态应是 `UNKNOWN`，不是自动拼起来继续判定。

## 聚合状态规则

| 情况 | 聚合时怎么表达 |
| --- | --- |
| 已启用检查器返回 `FAIL` | 聚合结果必须阻断；报告列出失败项和对应阶段 |
| 已启用检查器返回 `UNKNOWN` | 聚合结果必须阻断；报告说明缺证据、缺标准或检查器不足 |
| 已启用检查器全部 `PASS`，且没有 signoff blocker | `standard_acceptance_status=PASS`，`signoff_status=SIGNABLE` |
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

- 本文说的模板最终产物只指 `06.1_fillable_template.docx`、`generated_template_tree.json` 和 `template_gap_report.*`。
- `template_generate` 的输入只有学校原始模板 Word；不读取内容提取产物、放置计划或最终论文渲染结果。
- `template_generate` 也不应该把 `standards/targets/**` 当成正常生成输入；这些标准是已知样例的评测和验收材料。
- 如果识别出某个位置是用户填写位，它就是生成模板里的填写位；这件事来自源模板自身的结构、文字、样式、占位符、字段和产品规则，不来自后续业务阶段。
- 内容提取、内容放置和最终论文渲染属于后续业务评测，不作为模板生成评测的输入、裁判依据或最终产物。
- `06.2_build_manifest.json` 只能证明生成器执行了什么，不能证明最终 Word 符合学校标准。
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
| `tests/contract/test_real_core_baseline_harness.py` | 覆盖 real-core 标准登记 | 三校标准入口 | 三校各 5 个模板生成标准入口存在、可解析、绑定到 `target.standard.yaml`；其中 T2 为 `t2_unit_pagination.standard.yaml`，并且 T1-T5 为 `configured/gate_enabled=true` | 不证明某次 run 的产物一定 PASS |

按阶段看当前测试输入输出：

| 阶段 | 测试输入 | 测试输出或断言 |
| --- | --- | --- |
| `00_input_request` | 测试临时生成的学校模板 DOCX；CLI 参数 `--template`、`--out` | 请求 JSON、summary、debug 00 文件存在；CLI 不接受 `--school` |
| `t1_document_facts` | 测试模板 DOCX 里的段落和表格 | `01_document_facts.json` 存在，`source_seq` 连续，`indexes.by_source_seq` 可反查；T1 不产出 `unit_id/policy/confidence` |
| `t2_unit_pagination` | `01_document_facts.json` 里的可见节点 | `02_unit_map.yaml` 里有 unit、`source_seq_refs[]`、边界和分页口径；`template_structure_candidates.json` 只作为调试视图 |
| `t3_element_policy` | `02_unit_map.yaml` 和运行内 generation model | `03_element_spec.yaml` 里 policy、fill_source、manual_semantics、generated.field_type 和 source refs 正确 |
| `t4_global_layout` | `01_document_facts.json` | `04_global_spec.yaml` 里 section profile、boundary、page numbering、header/footer 和 numbering evidence 正确 |
| `t5_template_spec` | `02_unit_map.yaml`、`03_element_spec.yaml`、`04_global_spec.yaml` | `05_template_spec.yaml` 里 unit 顺序、section_profile_refs、元素策略和 review_flags 正确 |
| `06_final_template_gap` | 被测 `06.1_fillable_template.docx` 和 `final_template.expected.yaml` | `generated_template_tree.json`、`template_gap_report.*` 存在；状态组合、样式、页眉页脚、字段、编号等检查不误判 |
| `99_debug_index` | 模板生成编号产物根目录 | `99_template_generation_debug_index.json` 包含本次运行的关键文件名与 hash |

后续补阶段化评测骨架时，最小测试应覆盖：

| 测试目标 | 期望 |
| --- | --- |
| 阶段清单稳定 | 报告里列出 `t1_document_facts` 到 `06_final_template_gap` |
| 阶段标准入口稳定 | 三校 `target.standard.yaml` 都引用 `t1_document_facts.standard.yaml`、`t2_unit_pagination.standard.yaml`、`t3_element_policy.standard.yaml`、`t4_global_layout.standard.yaml` 和 `t5_template_spec.standard.yaml` |
| 阶段标准 gate 已开启 | real-core T1-T5 标准文件明确 `verifier_state = configured`、`gate_enabled = true` |
| 未配置阶段不伪装成通过 | 非 real-core 或 fixture 中 `verifier_state = not_configured` 时没有 `status = PASS` |
| 最终 gap 作为示例接入 | `06_final_template_gap` 能复用现有 gap 检查结果 |
| 已有产物包复用 | 给定一个已有 `template-generate` run 目录时，聚合检查读取现有文件，不重新调用生成器 |
| 缺最终 gap 输入 | 返回 `UNKNOWN`，不能跳过检查后成功 |
| 缺中间产物或 hash 不一致 | 返回 `UNKNOWN` 或阻断失败，报告说明证据来源不一致 |
| 聚合报告可读 | 人能看到哪些检查启用、哪些只是等待标准 |

## 当前最小落地顺序

1. 已完成：三校模板生成阶段标准已拆成 `t1_document_facts.standard.yaml`、`t2_unit_pagination.standard.yaml`、`t3_element_policy.standard.yaml`、`t4_global_layout.standard.yaml`、`t5_template_spec.standard.yaml`，并在 `target.standard.yaml` 中登记。
2. 已完成：`template-generation-judge` 使用已有 `template-generate` run 目录 / artifact bundle 作为阶段检查聚合输入。
3. 已完成：阶段检查聚合结构登记阶段、产物路径、hash、标准路径、audit status、gate status、diff、root cause 和 owner。
4. 已完成：T1-T5 real-core 阶段 verifier 接入并打开 gate；非 real-core 或 fixture 中未配置 verifier 仍显示 `not_configured`，不伪装 PASS。
5. 后续：把 `06_final_template_gap` 挂入同一个聚合视图，消费同一个 bundle 里的 `06.1_fillable_template.docx`。
6. 每补一个检查器或标准维度，都补合同测试证明它的 `PASS` / `FAIL` / `UNKNOWN` 行为，以及复用已有产物时不会偷偷重跑生成器。

这样做的目的不是把架构写大，而是防止两个误判：一是最终 gap 失败时不知道从哪里追；二是中间阶段只有产物却被误认为已经验收通过。
