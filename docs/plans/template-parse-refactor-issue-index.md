---
status: active
owner: template-generation
created: 2026-06-25
last_updated: 2026-07-26
---

# 模板解析重构 issue 迭代索引

> 文档职责：本文只保存模板解析 issue/plan 的历史迭代链。当前变化、缺陷、影响和闭环状态以 `docs/status/INDEX.md` 为准。

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
| 07 | issue | `docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-issue-07-end-to-end-workflow-not-integrated.md` | draft | 计划 06 / route-eval 03 已落代码与 artifact 槽位，但默认真实 run 未贯通 Module 1→桥接→三路线；03.1 常为 NOT_AVAILABLE 占位且语义与 abstain 混用。 |
| 07 | optimization plan | `docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-plan-07-end-to-end-workflow-integration.md` | draft | 四阶段：NOT_AVAILABLE 占位修正 → 同 run Module1 编排 → hunannongye replay contract → 运行口径文档与 T3 route summary。 |
| 08 | issue | `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-08-t1-l1-input-contract.md` | closed | 2026-07-11 已由 Plan 08 关闭：纯事实 L1、run/object/page identity、T2-T7 shared hash 与旧输入退出均完成。 |
| 08 | optimization plan | `docs/plans/2026-07-10-template-parse-refactor-t1l1-input-contract-plan-08-l1-projection-bundle-gate.md` | verified | 三校迁移前后真实 API 无明显回退报告 PASS；最终代码固定 replay 的 T1-T6 语义全等、T6 identity failure=0、canonical L1 hash 可重算。 |
| 09 | issue | `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-09-ai-raw-not-merged.md` | draft | 同 run AI raw 已经 AVAILABLE 且 hash 对齐，但 T2 schema 拒绝、T3 manual review、T4 advisory-only 导致 AI 未进入 merged 权威产物。 |
| 09 | optimization plan | `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-09-ai-raw-to-merged.md` | draft | 修 T2 bridge collection/kind、T3 executable overlay、T4 merged global_spec evidence，并用 hunannongye replay 验证每层 accepted/merged。 |
| 10 | issue | `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-10-t4-observation-downstream-dead-end.md` | superseded | T4 hint 死端事实已由 Issue 13 的 AI-only 权威模型取代。 |
| 10 | optimization plan | `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-10-t4-ai-primary-layout-consumption.md` | superseded | 原 AI-primary + deterministic fallback + merged 方案已被 Plan 13 的唯一 AI final 取代。 |
| 11 | issue | `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-11-unit-pagination-signal-loss.md` | draft | T2 signed standard 已有四维分页策略，但 runtime page 可全空；T5/T6 双轨消费且 T2 judge 对空 page 仍 PASS/SIGNABLE。 |
| 11 | optimization plan | `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-11-unit-pagination-alignment.md` | implemented_in_part | 已落 canonical page、T2 page audit、T2 AI page proposal、T5/T6 单一消费链和 manifest provenance；三校离线生成/judge 与最终 Word template-gap 已跑，人工 T2-style page policy 注入已证明 T5/T6/T7 可消费并更新 DOCX；仍因真实 T2 `t2_page_policy_mismatch` 未 verified，live route 需显式授权。 |
| 12 | issue | `docs/plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-issue-12-source-boundary-model-conflict.md` | implemented_in_part | AI-only 页面生产链已解决旧 source 边界与同页单元冲突；学校页面 gold 和 live 验收仍待闭环。 |
| 12 | implementation plan | `docs/plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-plan-12-exclusive-contiguous-page-contract.md` | implemented_in_part | 页图优先、严格 page-range 输出、确定性 source binding 和固定分页策略已落代码；三校 gold/verifier、MiniMax live 与最终 Word 验收待完成。 |
| 13 | issue | `docs/plans/2026-07-26-template-parse-refactor-t4-ai-only-issue-13-multi-route-authority-conflict.md` | superseded | T4 AI-only 清理已落地，但“required T4 final”目标被 Issue 14 的 copy-first 跳过决策取代。 |
| 13 | implementation plan | `docs/plans/2026-07-26-template-parse-refactor-t4-ai-only-plan-13-single-ai-final.md` | superseded | 唯一 AI final 是历史中间态；不再补三校 T4 live/gold。 |
| 14 | issue | `docs/plans/2026-07-26-template-parse-refactor-t4-skip-issue-14-copy-first-stage-has-no-execution-effect.md` | impact_confirmed | copy-first 已保留源全局版式，T4 final 没有产生 T6 版式动作却阻塞 availability。 |
| 14 | implementation plan | `docs/plans/2026-07-26-template-parse-refactor-t4-skip-plan-14-remove-required-stage-and-preserve-source-layout.md` | approved | 跳过 T4，以 L1 section 基线、T5 确定性绑定、T6 preservation 和 T7/POST_T6 最终验证接管上下游责任。 |
| 15 | issue | `docs/plans/2026-07-26-template-parse-refactor-t1l1-fact-foundation-issue-15-leaf-identity-and-split-artifacts.md` | impact_confirmed | Plan 08 后续能力缺口：T1 尚未形成正文/全局/render 三组件，L1 尚无叶子级 `source_atom_seq`、membership、text-address 和 locator 契约。 |
| 15 | implementation plan | `docs/plans/2026-07-26-template-parse-refactor-t1l1-fact-foundation-plan-15-centralize-facts-and-preserve-stage-inputs.md` | draft | 把分散客观事实集中到三组件 T1 与 sealed L1；现有 T2/T3 stage-input shape 和 T5/T6/T7 业务逻辑保持，T4 仅兼容，gold 最后由 Plan 03 接管。 |
| — | direction proposal | `docs/plans/2026-07-03-template-parse-refactor-ai-primary-staged-migration-proposal.md` | superseded | T2/T3 AI-only 仍由 Plan 12/07 管理；T4 已由 Plan 14 改为暂停并跳过。 |

## Template generation full-chain capability closure

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-issue-01-remaining-end-to-end-gaps.md` | implemented_in_part | 一行全流程入口、post-T6 自动 gap、full_summary 和 Plan 08 L1 强制消费已落地；仍记录三路线后段隔离重放、真实 object binding、T4 hint 执行、AI-primary 晋升和 T3 真实残留门禁等未闭环质量问题。 |
| 01 | optimization plan | `docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-plan-01-end-to-end-closure.md` | implemented_in_part | 已落一行全流程、post-T6 gap 派生、full summary、Plan 08 sealed L1、T3 residual gate、route replay reason、T4 explicit noop 消费和 AI-primary gate；真实三校仍暴露 T3 residual、object binding 等质量门禁。 |

## Template generation entropy cleanup

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/2026-07-11-template-generation-entropy-cleanup-issue-01-stale-surfaces.md` | closed | 旧四阶段 CLI/stage、三套 artifact path 和选定无生产调用 evaluator/compatibility leaves 已删除。 |
| 01 | implementation plan | `docs/plans/2026-07-11-template-generation-entropy-cleanup-plan-01-delete-stale-surfaces.md` | verified | leaf cleanup、旧 workflow 删除和唯一编号输出树均完成；304 tests 与三校 full-chain 验证通过运行/证据契约。 |

## Standard judge

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/template-parse-refactor-standard-judge-issue-01-run-bundle-stage-verifiers.md` | draft | 模板生成标准裁判模块：标准质量、run bundle、T1-T5 阶段 verifier、聚合报告和输出命名 |
| 01 | optimization plan | `docs/plans/template-parse-refactor-standard-judge-plan-01-stage-diff-root-cause.md` | draft | 明确 verify 报告、阶段产物 vs 阶段标准 diff、root cause/owner 归因三层目标和实施顺序 |
| 02 | issue | `docs/plans/template-parse-refactor-standard-judge-issue-02-stage-standard-diff-diagnosis-priority.md` | draft | 纠偏：stage standard diff diagnosis 优先于 gate。**待拆分**：正文混入了 plan 内容，应迁到独立 `plan-02` 文档 |
| 02 | optimization plan | TBD | pending | 对应 issue-02；从 issue-02 正文拆出实施计划后登记 |
| 03 | issue | `docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-issue-03-full-chain-three-route-gap.md` | draft | 当前缺口：模板生成全链路尚未统一比较 code_raw、ai_raw、merged，T3 元素级 draft gold、T5/T6 隔离重放和 template-gap 证据未纳入同一诊断闭环 |
| 03 | optimization plan | `docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-plan-03-full-chain-three-route-evaluator.md` | implemented_in_part | route-eval 已覆盖 T1/L1/T2/T3/T4/T5/T6/T7/POST_T6 共 23 个 route candidates；后段 route replay 已写可物化 T5 或 OUT_OF_SCOPE/NOT_AVAILABLE reason，template-gap 可由 judge/full-chain 派生。 |

## Stage standards completeness

| 顺序 | 类型 | 文档 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/2026-07-03-template-parse-refactor-stage-standards-issue-01-incomplete-stage-standards.md` | draft | T1-T5 标准文件存在且 judge 可 PASS，但 T3 未覆盖人审元素/run-span 级标准，T6/T7 仍无阶段标准，最终 template-gap FAIL 无法回链 |
| 01 | optimization plan | `docs/plans/2026-07-03-template-parse-refactor-stage-standards-plan-01-stage-standard-completeness-audit.md` | draft | 先新增标准完整性审计：final_template 已有元素清单但 T3 标准缺元素覆盖时降级为 UNKNOWN/NOT_SIGNABLE，并输出四层诊断 |
| 02 | optimization plan | `docs/plans/2026-07-03-template-parse-refactor-stage-standards-plan-02-t3-run-span-standard-fill.md` | implemented | 补齐三校 T3 `element_expectations` 与 `run_span_ledger`，以人审 final_template 为标准，以真实 T1/T3 artifact 绑定 run/span 证据 |
| 03 | issue | `docs/plans/2026-07-25-template-parse-refactor-stage-standards-issue-03-duplicated-gold-sources.md` | impact_confirmed | 每校 final 与 T1–T5 六份 gold/standard 独立维护，重复 source/review/unit 事实并产生 hash 与语义漂移风险 |
| 03 | implementation plan | `docs/plans/2026-07-25-template-parse-refactor-stage-standards-plan-03-canonical-gold-stage-projections.md` | draft | 每校收敛为一份 `school_template.gold.yaml`；阶段评测使用确定性投影视图，shadow parity 后原子切流并删除旧事实源 |

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
| 05 | issue | `docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-issue-05-inline-style-instruction-fixed-merge.md` | draft | issue-04 修复后暴露的新残余：行内括号格式说明被合并进 fixed/fill/generated/manual_only，未作为 instruction_remove 删除；hunannongye 当前扫描命中 8 处并残留到最终 DOCX |
| 05 | optimization plan | `docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md` | draft | 与 issue-06 共用综合 plan-06；依赖 Plan 08，按 L1+T2 构造 run/span/视觉输入并做完整 merged/T6 精确消费；issue-05 为 also_resolves |
| 06 | issue | `docs/plans/2026-07-02-template-parse-refactor-t3-element-policy-issue-06-placeholder-span-granularity.md` | draft | `□` / `××` / `……` placeholder-like 文本缺少子 span 粒度；典型字段行被整段标为 fixed，扫描命中 66 个非删除元素 |
| 06 | optimization plan | `docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md` | draft | 综合 plan：L1 run/span/视觉 Stage Input、同形 code/AI decisions、span coverage、完整 merged、T6 精确动作和 AI-primary 真实门禁；同时覆盖 issue-05 |
| 07 | issue | `docs/plans/2026-07-22-template-parse-refactor-t3-hierarchical-ai-issue-07-flat-stage-input-and-output.md` | implemented_in_part | 层级树、稀疏覆盖和精确消费已实施；L1 merge/field 所有权和三校准确率仍未闭环。 |
| 07 | optimization plan | `docs/plans/2026-07-22-template-parse-refactor-t3-hierarchical-ai-plan-07-stage-input-sparse-decisions.md` | implemented_in_part | 正式 live/replay 已切 hierarchy；真实结构门禁通过，Accuracy Promotion Gate 因 baseline 与 live 调用放大未验证。 |
