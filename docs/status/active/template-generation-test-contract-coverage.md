# Template Generation Test Contract Coverage

status: impact_confirmed

stage: template-generation full-chain / T1 / L1 / T2 / T3 / T4 / T5 / T6 / T7 / POST_T6

discovered_at: 2026-07-20

last_updated: 2026-07-23

## 发生了什么

模板生成已经定义整体和逐阶段测试契约，但阶段冻结输入、独立 gold 状态、统一 stage CLI、统一报告和部分视觉指标尚未全部落地。测试契约本身已经收敛到 `docs/current/template-generation-testing.md`；本文件只追踪实现覆盖和闭环状态。

## 影响范围

| 范围 | 未闭环影响 |
| --- | --- |
| full-chain | 仍需补齐冻结 fixture、T4 视觉指标和统一 gold status |
| T1 | 缺独立 fixture、统一 stage CLI 和 T1 stage report |
| L1 | 缺独立 gold、fixture、统一 CLI 和报告 |
| T2 | 缺完整 fixture、统一 CLI 和统一 stage report |
| T3 | adaptive run/span gold 契约、三校精确 run 身份和计分器已落地；163 个候选已完成代理 Word 审查，18 个 mixed run 当前物化为 87 条 span gold（湖南农大 source rebind 前为 77 条），仍待人工签核且保持 `PARTIAL`；另缺完整 isolated fixture、统一 CLI 和统一 stage report |
| T4 | 视觉指标仍需扩展，缺冻结 render fixture 和统一报告 |
| T5 | 缺冻结直接输入包、独立 CLI 和统一报告 |
| T6 | 缺 fixture、长期 gold/contract 决策、统一 CLI 和报告 |
| T7 | 缺 fixture、长期 gold/contract 决策、统一 CLI 和报告 |
| POST_T6 | 缺统一 gold status 和统一阶段报告外壳 |

## 当前风险

完整链路报告存在不代表各阶段都能被隔离、复现和独立评价；缺少冻结输入或统一报告时，阶段自身误差和上游级联误差仍可能混在一起。

## 关联修改计划

- `docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-plan-03-full-chain-three-route-evaluator.md`
- `docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-plan-01-end-to-end-closure.md`

是否需要新的综合 plan，应在确认剩余工作的共同根因和执行边界后决定。

## 验证状态

当前为 partial。

2026-07-23 已完成的 T3 契约证据：

- 三校现有 ledger item 均补齐 `target_kind=run|span` 和与各自绑定 L1 packet 完全一致的原始 `text`；source rebind 不修改既有字符级 `expected_action`。
- 三校 T3 gold 已声明 `t3-adaptive-run-span-gold-1.0`、`adaptive_run_or_span`、模板版本、T2 standard hash、审核元数据和禁止自动回写。
- 计分器、stage verifier、route evaluator 和 standard-quality 检查均能按精确 run/span identity 校验；span 必须连续、无重叠、无缺口并完整覆盖所属 raw run。
- 76 / 50 / 37 个 policy-neutral multi-span 候选已逐项结合冻结 DOCX、Word 页面和 sealed L1 facts 完成代理审查：145 个动作统一的候选保留为 run gold，18 个真实 mixed run 在原绑定下物化为 77 条连续、无重叠且完整覆盖原文的 span gold；原待审队列已清空，北大 3 个 `unknown` 已消除。
- 三校均记录 `delegated_review_metadata`，严格校验器对 frozen L1 packet 的 adaptive ledger 检查通过；但代理审查不代替人工签核。因 `review_metadata.reviewed_at` 仍缺失，三校 `gold_status` 均保持 `PARTIAL`，完整质量结论必须为 `UNKNOWN`。
- 用户已确认湖南农大当前 `source_template.docx`（`776649b4…`）是手工纠错后的 canonical source。target、T1–T5、final、T2/T3 上游 hash 均已重绑定；新旧 source-seq 文本与逻辑 run 文本逐项一致，T2 gold 保持不变。raw run 从 708 重切分为 674 后，T3 gold 通过字符级投影迁移为 714 条 ledger item（12 个 mixed run、52 条 span），并对新 L1 packet 完成精确分区和完整覆盖校验。

关闭前仍必须证明：对应阶段的固定输入、完整人工复核 gold、统一入口、指标和报告均可复现，并能区分 isolated 与 cascade 结果。
