# Template Generation False Green

status: verified

source_plan: `docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-plan-01-end-to-end-closure.md`

latest_user_intent: 按已确认顺序修复模板生成阶段假绿。

current_slice: 双状态、required-check ledger、T1/T3/T4/T5 语义校验、T6 最终 DOCX 重验、route availability 和 run bundle hash 溯源已闭环。

completed_slice_batch:

- `run_status` 与 `quality_status` 分离；单独 generate 未运行学校裁判时质量保持 `UNKNOWN`。
- T1-T5 标准审计输出 required-check ledger；未消费 expected 字段、未运行 verifier 或缺证据不能 `PASS`。
- T3 校验 policy ontology；T4/T5 复用运行时语义校验并补上游顺序、编号、hash、section 和 element 绑定。
- T6 在生成和历史 run 裁判时都重新解析最终 DOCX，验证分页、分节和 keep 属性，不信任 manifest 自述。
- route `NOT_AVAILABLE` 与缺 availability 证据降为 `UNKNOWN`；缺 debug index 或声明 hash 的 run bundle 降为 `UNKNOWN`。
- 增加空产物、非法 policy、坏布局、错 hash、悬空 section、伪造分页动作和路线不可用等反例测试。

last_proven_evidence:

- `uv run pytest -q ...` 聚焦 T1-T7、agent route、run bundle、标准裁判和反例门禁：`170 passed in 22.95s`。
- 最终 full 聚合 finding 收口后重跑两组合同测试：`19 passed in 21.20s`。
- `/tmp/docfit-false-green-judge-20260718-r2`: `run_status=PASS`、`quality_status=FAIL`、`first_bad_stage=T2`、`signoff=NOT_SIGNABLE`。
- 同一真实回放中 T1/T4 ledger 为 `PASS`，T2/T3/T5 暴露真实不一致；T6 fresh observation 为 `FAIL`，不再由旧 manifest/verification report 伪绿。
- `git diff --check`：通过；仓库未配置 Ruff，未新增格式器。

next_action: 继续按现有 Plan 11 / T3 Plan 06 修真实 T2/T3/T5 学校质量差距；这些是当前显式 FAIL/UNKNOWN，不属于本轮假绿残留。

next_proof: 每次修真实质量后重跑三校 generate + template-gap + template-generation-judge，并检查 `run_status`、`quality_status`、required-check ledger 和 T6 fresh observation。

stop_condition: 本轮只消除假绿，不把真实 T2/T3/T5 质量失败包装为完成。

no_touch_scope: 不覆盖本轮开始前已有的 Plan 11、issue index 和 `unit-pagination-consumption.md` 未提交改动。

parked_work:

- 湖南农大历史 run 当前 T2 page policy/source range、T3 element/run-span、T5 page/hash 仍不符合当前标准。
- 三校真实质量闭环继续由既有计划追踪；本轮未授权 live API 或修改学校标准。
