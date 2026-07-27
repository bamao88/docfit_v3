# 模板生成待核实差距清单

Last updated: 2026-06-25

> 迁移状态：本文已停止作为当前缺口入口。未闭环变化和缺陷统一进入 `docs/status/INDEX.md` 与 `docs/status/active/`，具体修改方案进入 `docs/plans/`。本文只保留历史 gap 编号参考。

> 迁移提示：本文记录的是旧 `generated_template.docx` / 00-05 链路下的待核实差距。
> 当前生成入口已经产出 `06.1_fillable_template.docx`、`05_template_spec.yaml` 和
> `07_verification_report.json`。继续核实差距时应先看新的 T1-T6 first_bad_stage，
> 再决定是否回查本文中的历史 gap 编号。
> 2026-06-25 更新：低/中置信和页码 `UNKNOWN` 已接入
> `flags/review_flags -> verification_report -> pm_report/issue_clusters`；
> TG-GAP-003 已部分缓解，但 review queue、gold 比对和学校最终 gap 仍未闭环。

一句话结论：当前模板生成能从学校原始模板 Word 生成 `06.1_fillable_template.docx` 和 00-07 阶段证据；真实学校验收仍失败，下一步要逐项核实的是“源模板自动推断能力”和“阶段证据可解释性”，不是让生成器依赖学校签收标准作为输入。

## 输入边界

| 项 | 当前定义 |
| --- | --- |
| 正常生成输入 | 学校原始模板 Word |
| 不作为生成输入 | `standards/targets/**`、`final_template.expected.yaml`、某一次学生源 Word、学生内容台账 |
| 标准文件用途 | 开发期和验收期的裁判标准，用于 `template-gap` 检查已知样例 |
| 生成器应该做什么 | 从源模板自身的结构、文字、样式、占位符、表格、字段和通用产品规则推断单元和内容责任 |
| 证据不足时怎么办 | 写入 `unresolved_questions[]`、`actions_requiring_review[]` 或后续阶段检查结果；不能伪装成确定策略 |

## 最近真实验收

| 命令 | 结果 | 说明 |
| --- | --- | --- |
| `uv run pytest tests/contract/test_template_generate.py -q` | `PASS`，11 passed | 证明 00-05 产物链、debug 编号、`source_seq` 和当前策略行为没有回归 |
| `uv run docfit eval template-generate --template inputs/targets/hunannongye/raw/source_template.docx --out test_outputs/debug/template_generation/agent_acceptance_20260622_hunannongye/eval_runs/template_generate` | `PASS` | 证明真实源模板能生成 Word 和过程证据 |
| `uv run docfit eval template-gap --school hunannongye --generated-template test_outputs/debug/template_generation/agent_acceptance_20260622_hunannongye/eval_runs/template_generate/06.1_fillable_template.docx --out test_outputs/debug/template_generation/agent_acceptance_20260622_hunannongye/eval_runs/template_gap` | `FAIL` | gap summary 为 `FAIL + UNKNOWN`，`passed=128`、`failed=27`、`unknown=137` |
| `uv run pytest tests/contract/test_real_core_generated_template_gap.py -q` | `PASS`，33 passed | 证明本次 gap 失败不是检查器明显回归 |

这组结果只能说明：生成器能跑，但生成结果还没有通过已知学校样例的验收。

## 待核实差距

| ID | 待核实差距 | 当前证据 | 可能 first_bad_stage | 需要核实的问题 |
| --- | --- | --- | --- | --- |
| TG-GAP-001 | 源模板 unit 发现粒度可能过粗 | 湖南农业真实运行中，T2 识别的 unit 仍粗；gap 标准中可定位或期望的后置单元包括 `design_task`、`proposal`、`proposal_record`、`defense_record`、`topic_change_approval`、`grade_form` 等更细单元 | `T2/t2_unit_pagination` | 源模板里这些表单标题和表格边界是否足以自动拆成独立 unit？如果足够，应该补通用 unit 发现规则；如果不足，应写入不确定性 |
| TG-GAP-002 | 固定/可填/generated 策略仍需要更细标准对照 | 当前 `element_spec` 已表达 policy/fill_source/generated 字段，但还没有接入三校 T3 标准 verifier | `T3/t3_element_policy` | 哪些单元只靠源模板就能判断为固定、学生内容或系统生成？哪些必须进入 review flags？ |
| TG-GAP-003 | `review_flags[]` / `open_questions[]` 仍需和标准聚合 | 已部分修正：`unit_map`、`element_spec`、`global_spec` 的低/中置信和内联 `UNKNOWN` 会进入 `verification_report`；但 review queue 和 gold 比对仍未完成，最终 gap 的 UNKNOWN 还没有全部前移 | `T2/t2_unit_pagination` / `T3/t3_element_policy` / `T5/t5_template_spec` | 哪些 UNKNOWN 应该在解析阶段提前暴露为证据不足？哪些只能由最终 gap 暴露？ |
| TG-GAP-004 | 页面/分节规则还需要接入 T4 标准 | 本次 gap 有 16 个 `template_generation_page_rule_mismatch`；需要判断 `04_global_spec.yaml` 是否已有可解析分页/分节证据，以及 T6 是否正确构建 | `T4/t4_global_layout` / `T6/build` | 源模板中是否存在可解析的分页/分节证据？如果有，T6 为什么没有构建出来？如果没有，是否应登记不确定性？ |
| TG-GAP-005 | 样式修正能力不足或责任边界不清 | 本次 gap 有 6 个 `template_generation_style_mismatch` 和 6 个 `template_generation_style_unverified` | `T1/document_facts` / `T4/t4_global_layout` / `T6/build` / `06_final_template_gap` | 这些样式差异是源模板本身不符合目标、构建阶段没有修样式，还是 inspector 不能证明？ |
| TG-GAP-006 | 生成结果的 unit 顺序和定位仍会偏移 | gap 报告有 `template_generation_unit_order_mismatch`；`references` 在实际识别顺序里落到后置表单之后 | `T2/t2_unit_pagination` / `T5/t5_template_spec` / `T6/build` / `06_final_template_gap` | 是源模板 unit 边界发现错、template_spec 合并错、构建改变了顺序，还是 gap locator 对生成 Word 的定位错？ |
| TG-GAP-007 | 阶段产物独立 verifier 已接入，仍需挂入最终 gap 聚合视图 | `template-generation-judge` 已能对 real-core T1-T5 输出阶段标准裁判报告，且 gate 已开启；`template-gap` 仍是独立最终 Word 检查 | harness/report 层 | 是否把 T1-T5 judge 报告和 `06_final_template_gap` 合并到同一个 first_bad_stage 视图？ |
| TG-GAP-008 | manifest 可读性还不足以直接解释差距 | manifest 有 action 和来源序号，但还没有构建前后 diff 摘要，也没有按问题聚合到源模板元素 | `T6/build` / report 层 | 人工指出“源模板元素 N 不该删/该生成 slot”时，报告是否能一跳定位到 T2/T3/T4/T5 的首次判断？ |

## 核实顺序建议

1. 先核实 `TG-GAP-001`：如果 unit 边界错，后面的策略、action 和 gap 都会被带偏。
2. 再核实 `TG-GAP-004`：分页/分节失败数量明确，且能直接从 plan 和 manifest 判断有没有 action。
3. 再核实 `TG-GAP-003`：把“生成器应提前暴露的不确定性”和“只能由 gap 暴露的不确定性”分开。
4. 最后核实 `TG-GAP-005`、`TG-GAP-006`、`TG-GAP-008`：这些需要结合 generated tree、gap locator 和 Word action diff。

## 不应该做的事

| 不应该做什么 | 原因 |
| --- | --- |
| 不应该让 `template-generate` 强制接收 `--school` | 后续 100/1000 学校规模下不能要求每个学校先准备签收标准 |
| 不应该把 `final_template.expected.yaml` 当成生成器策略输入 | 它是评测裁判，不是正常业务输入 |
| 不应该用某一次学生源内容台账决定模板生成策略 | 模板生成只处理学校模板；学生内容属于后续内容提取和放置 |
| 不应该为了让 gap 变绿修改 standards | 标准只能按人工签收流程变更，不能被当前输出反向驱动 |
| 不应该看到最终 Word 不合格就直接改 gap 报告 | 先定位 first_bad_stage，再决定改源模板解析、结构发现、策略、计划、执行还是 gap locator |
