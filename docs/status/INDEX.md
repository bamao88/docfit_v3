# DocFit 状态索引

Last updated: 2026-07-23

本文是当前变化、缺陷、影响和闭环情况的统一入口。具体事实和证据以对应状态项为准；具体修改步骤以关联 plan 为准。

## Active

| 状态项 | 阶段 | 状态 | 当前结论 | 关联 plan |
| --- | --- | --- | --- | --- |
| [`t2-ai-input-accuracy.md`](./active/t2-ai-input-accuracy.md) | 模板生成 T2 | impact_confirmed | 工作流与视觉输入已更新；三校 live 证据仍受配额和边界准确率残留影响 | Plan 11 |
| [`t3-hierarchical-stage-input.md`](./active/t3-hierarchical-stage-input.md) | 模板生成 T3 | implemented | 层级输入、稀疏决策和 AI-only 精确物化已落地；湖南农大纠错源及 T3 raw-run gold 已重绑定并严格校验；三校仍待人工签核且保持 `PARTIAL`，merge/field 所有权及准确率门禁未闭环 | Plan 07 |
| [`t3-ai-only-downstream-adaptation.md`](./active/t3-ai-only-downstream-adaptation.md) | 模板生成 T3/T5/T6/T7/POST_T6 | impact_confirmed | T3 已收敛为单一 AI final；T5 availability、T6 canonical 动作消费、T7 连续性验证及 route/judge 展示仍待适配 | Plan 07 |
| [`template-cli-entrypoints.md`](./active/template-cli-entrypoints.md) | 模板生成全链路 | implemented | 四类入口已落地；真实阶段质量仍由关联能力缺口约束 | Full-chain Plan 01 |
| [`unit-pagination-consumption.md`](./active/unit-pagination-consumption.md) | 模板生成 T2/T5/T6 | implemented | 新分页契约和下游执行链已落地；真实 T2 质量仍未 verified | Plan 11 |

## 新增状态项

新增前先搜索本索引和 `active/`，避免同一影响被重复登记。命名使用简短 kebab-case；跨阶段问题在“阶段”列列出全部受影响阶段。
