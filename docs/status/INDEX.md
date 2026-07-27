# DocFit 状态索引

Last updated: 2026-07-26

本文是当前变化、缺陷、影响和闭环情况的统一入口。具体事实和证据以对应状态项为准；具体修改步骤以关联 plan 为准。

## Active

| 状态项 | 阶段 | 状态 | 当前结论 | 关联 plan |
| --- | --- | --- | --- | --- |
| [`t1-l1-fact-foundation-and-atom-identity.md`](./active/t1-l1-fact-foundation-and-atom-identity.md) | 模板生成 T1/L1 | planned | Plan 15 把分散事实集中到三组件 T1 与 sealed L1，并保持现有 T2/T3 stage input 和 T5/T6/T7 业务逻辑；T4 只兼容，gold 最后迁移 | Plan 15 |
| [`t2-ai-input-accuracy.md`](./active/t2-ai-input-accuracy.md) | 模板生成 T2 | impact_confirmed | 工作流与视觉输入已更新；三校 live 证据仍受配额和边界准确率残留影响 | Plan 11 |
| [`t2-page-exclusive-unit-contract.md`](./active/t2-page-exclusive-unit-contract.md) | 模板生成 T2/T3/T5/T6/T7 | implemented | AI-only 页面链已收敛，正式/调试入口完成隔离，三校 MiniMax live 与最终 Word 分页已通过；人工暂定准确率 100%，正式 page-native gold、school verifier 和 T3 gold contract 仍待闭环 | Plan 12 |
| [`t3-hierarchical-stage-input.md`](./active/t3-hierarchical-stage-input.md) | 模板生成 T3 | implemented | T2 final/L1 分层输入、Keep/Fill/Delete/Split、稀疏覆盖与安全物化、adaptive run/span 指标及唯一 T3 final 合同已落地并写入 canonical 文档；三校仍待人工签核且保持 `PARTIAL`，merge/field 所有权及准确率门禁未闭环 | Plan 07 |
| [`t3-ai-only-downstream-adaptation.md`](./active/t3-ai-only-downstream-adaptation.md) | 模板生成 T1/L1/T2/T3/T4/T5/T6/T7 | implemented | 统一 Final Publisher、唯一业务输入、hash/availability 链、T7 连续性 finding 和湖南农大真实重算已落地；route/judge 展示与 legacy reader 仍待验证 | Plan 07 |
| [`t4-production-skip.md`](./active/t4-production-skip.md) | 模板生成 T4/T5/T6/T7/POST_T6 | planned | copy-first 长期契约已决定暂停并跳过 T4；代码仍需删除 T4 调用/产物/gate，并把 L1 section binding 与最终 Word 版式保护接到 T5-T7 | Plan 14 |
| [`template-generation-canonical-gold-projection.md`](./active/template-generation-canonical-gold-projection.md) | 模板生成 T1/L1/T2/T3/T4/T5/T6/T7/POST_T6 | planned | 每校只维护一份 canonical school gold；Plan 03 同时完成三校 T1-T5/final 全量 gold、L1/T6/T7 合同评测接入和所有消费者切流，任何阶段不得以 PARTIAL/MISSING 延期 | Stage Standards Plan 03 |
| [`template-cli-entrypoints.md`](./active/template-cli-entrypoints.md) | 模板生成全链路 | implemented | 四类入口已落地；真实阶段质量仍由关联能力缺口约束 | Full-chain Plan 01 |
| [`template-generation-test-contract-coverage.md`](./active/template-generation-test-contract-coverage.md) | 模板生成测试全链路 | impact_confirmed | 测试契约已收敛；T3 adaptive gold 的代理 Word 审查和 span 物化已落地，仍待人工签核；阶段 fixture、统一 CLI/报告仍未全部闭环 | Route-eval Plan 03 / Full-chain Plan 01 |
| [`unit-pagination-consumption.md`](./active/unit-pagination-consumption.md) | 模板生成 T2/T5/T6 | implemented | 新分页契约和下游执行链已落地；真实 T2 质量仍未 verified | Plan 11 |

## Closed

| 状态项 | 阶段 | 状态 | 关闭结论 |
| --- | --- | --- | --- |
| [`t3-conservative-unit-routing.md`](./closed/t3-conservative-unit-routing.md) | 模板生成 T3 | verified | 单元路由、保守删除、gold 上游评测和回归证据已闭环 |
| [`t4-ai-only-route.md`](./closed/t4-ai-only-route.md) | 模板生成 T4/T5/T6/T7 | superseded | T4 AI-only 清理已发生，但生产目标随后改为暂停并跳过 T4，由 Plan 14 接管 |
| [`template-generation-false-green.md`](./closed/template-generation-false-green.md) | 模板生成评测 | verified | 双状态、required-check ledger、T6 fresh observation 和假绿反例门禁已闭环 |

## 新增状态项

新增前先搜索本索引和 `active/`，避免同一影响被重复登记。命名使用简短 kebab-case；跨阶段问题在“阶段”列列出全部受影响阶段。
