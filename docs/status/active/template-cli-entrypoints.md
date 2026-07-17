# Template CLI Entrypoints Active Capsule

- Capsule status: `ACTIVE`
- Source plan: `docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-plan-01-end-to-end-closure.md`
- Latest intent: 按已确认规划实现 generate/stage/verify/inspect 四类研发入口。
- Current slice: 代码、文档、本地证据和最小 T2/T3/T4 live 验证已完成；全链路质量闭环仍受 Plan 08、T3 residual、object binding 等剩余能力约束。
- Blocker fingerprint: none for minimal live stage validation; remaining blockers are capability/quality gaps tracked in the source plan.
- Last proven evidence: 318 tests passed；demo-school canonical offline 真实生成写出完整 manifest，API count=0；inspect 只读成功；`/private/tmp/docfit_live_min_t2t3t4.0BavJ1` 最小 live stage：T2 Kimi 1 call、T3 Kimi 3 calls、T4 MiniMax 1 call，三者 failure=0 且 source_render_hash 一致。
- Completed batch: canonical generate/stage/verify/inspect、统一 AI mode、run-backed stage、固定 T2 upstream、run manifest、旧 alias 迁移提示；verify 根 manifest 继承 generate 的 render/L1/API trace，stage 从 T1 facts 保留 source hash。
- Next action: 继续处理 source plan 中未闭环的 L1 强制消费、T3 residual、object binding、route replay 和 AI-primary 晋升门禁。
- Next proof: 三校 full summary 的阶段质量门禁和 route-eval 残留收敛，而不是仅证明 live transport 可调用。
- Stop condition: 四类入口可用，旧 alias 兼容，run manifest 完整，聚焦与全量测试通过；真实付费 API 验收单独记录。
- No-touch scope: Plan 08 L1 迁移、T3 Plan 06、entropy-cleanup 的无关删除和文档重排。
- Parked work: 真实 API 质量/成本仅完成最小通路验证，尚未作为三校质量晋升依据。
