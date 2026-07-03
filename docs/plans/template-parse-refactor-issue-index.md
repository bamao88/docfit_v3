---
status: active
owner: template-generation
created: 2026-06-25
last_updated: 2026-07-03
---

# 模板解析重构 issue 迭代索引

本文只维护阶段 issue 的命名和迭代链路，避免多轮优化后混淆“上一轮 issue”“上一轮优化文档”和“当前残余 issue”。

目录级命名说明（含日期前缀、历史对照、frontmatter）：[`README.md`](./README.md)。

命名约定：

```text
template-parse-refactor-{stage}-{topic}-issue-{NN}-{short-name}.md
template-parse-refactor-{stage}-{topic}-plan-{NN}-{short-name}.md
```

每个 issue 文档 frontmatter 必须包含：

```yaml
topic: ...
issue_id: ...
issue_sequence: ...
previous_issue:
  id: ...
  doc: ...
previous_optimization:
  doc: ...
  summary: ...
next_plan: ...
```

## T2 unit-recognition

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md` | resolved | Phase 2 优化前的边界/标签问题 |
| 01 | optimization plan | `docs/plans/template-parse-refactor-t2-open-label-unit-recognition.md` | partially_implemented | Phase 2 确定性主干方案 |
| 02 | issue | `docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md` | draft | Phase 2 优化后残余单元识别问题 |
| 02 | optimization plan | `docs/plans/template-parse-refactor-t2-unit-recognition-plan-02-post-phase2-residual-fix.md` | superseded_by_03 | Phase 2 后残余修复计划；字段消费契约已拆到 data contract，但状态机和 standard gate 主线不够清晰 |
| 02 | data contract | `docs/plans/template-parse-refactor-t2-unit-recognition-data-contract.md` | draft | T2 数据转换、字段 producer/consumer、debug vs gate 契约 |
| 03 | issue | `docs/plans/template-parse-refactor-t2-unit-recognition-issue-03-state-machine-standard-gates.md` | draft | 当前 T2 standard 已存在但 verifier/gate 未闭环；正文状态机缺失 |
| 03 | optimization plan | `docs/plans/template-parse-refactor-t2-unit-recognition-plan-03-state-machine-standard-gates.md` | draft | 标准门禁先行，随后 taxonomy/boundary/list-block/state-machine/range-audit 收口 |

## T2 copy-only-policy

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/template-parse-refactor-t2-copy-only-policy-issue-01-default-freeze.md` | implemented | 默认 copy-only 从反向黑名单改为正向白名单，避免 custom/other 默认冻结 |
| 01 | optimization plan | none | skipped | 小范围直接修复，无单独 plan |
| 02 | issue | `docs/plans/template-parse-refactor-t2-copy-only-policy-issue-02-disable-copy-only.md` | implemented | 在学校级策略和开洞门禁补齐前，默认关闭 copy-only 能力 |
| 02 | optimization plan | TBD | pending | 后续若恢复 copy-only，需先定义学校级策略来源和内部开洞门禁 |

## T2T3T4 agent-proposal

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 04 | consolidated plan（唯一保留） | `docs/plans/template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md` | draft | 阶段唯一保留文档，已合并 issue-01/02/03 与 plan-01/02/03/05。主线 = Module 2（AI 与代码生成衔接：comparison、compatible/conflict/missing/unknown、manual_review、attribution，冲突直接上报人工）；Module 1（AI 独立同形产物 ai_unit/element/layout_observation）作为上游输入；附录收敛演进史、当前实现现状与分级 gap、Module 1 详细契约、staged pass 数据契约、不变量、验证矩阵/风险/待决项。 |
| 04 | issue | `docs/plans/2026-06-29-template-parse-refactor-t2t3t4-agent-proposal-issue-04-code-generation-bridge-execution.md` | implemented | 本轮执行 plan-04 的问题记录与验收：已新增 comparison/manual_review artifacts，并把 compatible+validated+low-risk 才进入 process_proposal 的桥接门禁接入 run_template_agent。 |
| 05 | issue | `docs/plans/2026-06-30-template-parse-refactor-t2t3t4-agent-module1-issue-05-observation-input-followups.md` | draft | Module 1 阶段输入后续待办：T2 页图优先+全文交叉验证（待 A/B）、T4 带入 AI-T2 单元上下文；附录记录 query_text/view_pages/终止工具人话说明。 |
| 06 | issue | `docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-issue-06-observation-code-bridge-acceptance.md` | implemented | Module 1 `ai_observation_bundle` 尚未接入 Module 2 代码生成桥接，且桥接后产物缺少对阶段标准的准确率验收口径。 |
| 06 | implementation plan | `docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-plan-06-observation-code-bridge-acceptance.md` | implemented | 新增 observation bridge、CLI/config/artifact 接线、manual review/attribution 合并，以及 `template_agent_bridge_standard_acceptance` 标准验收报告。 |

## Standard judge

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/template-parse-refactor-standard-judge-issue-01-run-bundle-stage-verifiers.md` | draft | 模板生成标准裁判模块：标准质量、run bundle、T1-T5 阶段 verifier、聚合报告和输出命名 |
| 01 | optimization plan | `docs/plans/template-parse-refactor-standard-judge-plan-01-stage-diff-root-cause.md` | draft | 明确 verify 报告、阶段产物 vs 阶段标准 diff、root cause/owner 归因三层目标和实施顺序 |
| 02 | issue | `docs/plans/template-parse-refactor-standard-judge-issue-02-stage-standard-diff-diagnosis-priority.md` | draft | 纠偏：stage standard diff diagnosis 优先于 gate。**待拆分**：正文混入了 plan 内容，应迁到独立 `plan-02` 文档 |
| 02 | optimization plan | TBD | pending | 对应 issue-02；从 issue-02 正文拆出实施计划后登记 |
| 03 | issue | `docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-issue-03-full-chain-three-route-gap.md` | draft | 当前缺口：模板生成全链路尚未统一比较 code_raw、ai_raw、merged，T3 元素级 draft gold、T5/T6 隔离重放和 template-gap 证据未纳入同一诊断闭环 |
| 03 | optimization plan | `docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-plan-03-full-chain-three-route-evaluator.md` | draft | 三路线 route evaluator 计划；已先落 T3 三份 route artifact，完整 T1-T6 route eval 待后续实现 |

## Stage standards completeness

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/2026-07-03-template-parse-refactor-stage-standards-issue-01-incomplete-stage-standards.md` | draft | T1-T5 标准文件存在且 judge 可 PASS，但 T3 未覆盖人审元素/run-span 级标准，T6/T7 仍无阶段标准，最终 template-gap FAIL 无法回链 |
| 01 | optimization plan | `docs/plans/2026-07-03-template-parse-refactor-stage-standards-plan-01-stage-standard-completeness-audit.md` | draft | 先新增标准完整性审计：final_template 已有元素清单但 T3 标准缺元素覆盖时降级为 UNKNOWN/NOT_SIGNABLE，并输出四层诊断 |
| 02 | optimization plan | `docs/plans/2026-07-03-template-parse-refactor-stage-standards-plan-02-t3-run-span-standard-fill.md` | implemented | 补齐三校 T3 `element_expectations` 与 `run_span_ledger`，以人审 final_template 为标准，以真实 T1/T3 artifact 绑定 run/span 证据 |

## Run bundle contract

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/template-parse-refactor-run-bundle-template-generation-contract-issue-01-co-located-outputs.md` | draft | 模板生成运行包契约：伴随产物应跟随本次 run bundle，`eval_runs/` 与 `human/` 统一收在 `test_outputs/debug/template_generation/<run-id>/` 下 |
| 01 | implementation plan | `docs/plans/template-parse-refactor-run-bundle-template-generation-contract-plan-01-phased-execution.md` | draft | 分阶段执行模板生成运行包契约：run root 推导、产物落盘、eval 共址、报告命名、证据绑定、文档同步和验收门禁 |

## T3 element-policy

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/template-parse-refactor-t3-element-policy-issue-01-confidence-noise.md` | resolved | element confidence 全员 medium 噪声 |
| 01 | optimization reference | `docs/current/template-generation-stage-optimization.md` | implemented in part | T3 confidence / copy-only 责任边界相关优化背景 |
| 02 | issue | `docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md` | draft | 默认 copy-only 排除后仍存在的 T3 policy/gold 与行内残留问题 |
| 02 | optimization plan | TBD | pending | 后续围绕 issue-02 讨论产生 |
| 03 | issue | `docs/plans/2026-06-30-template-parse-refactor-t3-element-policy-issue-03-within-paragraph-run-split.md` | resolved | 同 `<w:p>` 内占位与括号格式说明已在 runs[] 分开，但 T3 仍按 source_seq 整段 fixed；已通过 run_slice element、run refs 贯通和 run-level 删除修复 |
| 03 | optimization plan | `docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-plan-03-within-paragraph-run-split.md` | implemented | 分阶段实现 T3 段内 run 级元素化、run refs 传播、remove_instruction_text 精确删除和 judge 覆盖 |
| 04 | issue | `docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-issue-04-instruction-manual-confusion.md` | implemented | hunannongye 真实输出中多条“注/此表/请在/不得更改”等表单说明被 T3 误判为 manual_only，最终未删 |
| 04 | optimization plan | `docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-plan-04-instruction-manual-confusion.md` | implemented | 表单说明优先识别为 instruction_remove，并保留签名/意见等真实手填字段 |
