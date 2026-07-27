# T2 独占连续页面单元契约

- status: implemented
- discovered: 2026-07-24
- stage: 模板生成 T2/T3/T5/T6/T7
- source_issue: `docs/plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-issue-12-source-boundary-model-conflict.md`
- source_plan: `docs/plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-plan-12-exclusive-contiguous-page-contract.md`

## 发生了什么

用户已决定把 T2 单元收敛为“独占的连续页面区间”：一页只能属于一个 T2 单元，每个单元拥有一段连续页面，下一个单元一定从下一页开始。

旧生产契约曾允许：

- 用 `source_seq` 在同一页内部切分多个 T2 单元；
- `page_policy.start=same_page_allowed`；
- `page_policy.scope=shareable_flow`；
- 由 AI 分别判断边界和分页策略。

这些生产分支现已退出。三校人工 T2 标准仍保存旧 source 边界审阅证据，尚未重签为页面 gold。

## 影响

- T2 输入要从“正文顺序优先”改为“页图优先、每页绑定客观正文事实”。
- T2 AI 输出边界要从 `source_seq` 首尾改为渲染页首尾。
- `page_policy` 不再是 AI 判断，而应由程序按固定规则派生。
- T2 materializer 仍需把页面区间确定性映射为 T3 使用的 `source_seq_refs`。
- T3 不再接收同一页上的多个顶层 unit root。
- T5/T6 要删除 `same_page_allowed` 和 `shareable_flow` 分支；每个非首单元都必须另起页。
- T2 gold、route-eval、verifier 和 judge 要从 source 边界主评分迁移到页面区间主评分。

## 当前状态

Plan 12 已由用户批准执行。运行时已经收敛为 MiniMax AI-only 页面分组路线：

- Prompt 和 AI raw 只使用 `unit_id/unit_name/boundary.start_page/end_page`；
- 真实页图与逐页客观事实构成唯一 T2 输入；
- schema/materializer 校验页面完整覆盖并派生 L1 source bindings 和固定 `page_policy`；
- T2 code、comparison、bridge、overlay 和 merged 生产路线已删除；
- 未配置 AI、真实渲染不可用或 AI 输出非法时明确失败，不回退代码结果。

当前代码、replay、三校付费 MiniMax live 和最终 Word fresh 分页验收均已通过：

- 正式完整流程、单阶段调试和共享 provider 已拆为独立模块，正式 runtime 不导入
  调试适配器；普通 `unit_map` 只能在命名 T3 调试入口包装，并标记
  `producer_mode=debug_fixture`；
- T2 正式 final 只有一个生产 publisher；旧 taxonomy、overlay/attribution、
  混合 T2/T4 transcript、整单元 copy-only 和旧 `--agent-*` 配置入口已删除；
- 页图重复项和声明 hash 都在调用模型前校验；开放式 `unit_id` 不再被下游固定
  taxonomy 消费；
- 三校 live 各调用一次 `MiniMax-M3`，共 3 次，无缓存命中、无 API 失败；
- 56 个真实渲染页被 26 个连续页面组完整且唯一覆盖，gap/overlap 为 0；
- 人工视觉复核暂定页面组区间、页面归属、相邻页切分和单元语义均为 100%；
- 三校最终 Word 页数保持 17、12、27，23 个非首单元均在已有正确页边界开始，
  没有重复分页或新增空白页；
- 当前全仓 `pytest -q` 350 passed，正式/调试模块边界与 T2 关键切片 45 passed；
  三校最终 Word fresh render packet 均重新通过严格 T2 page precondition。

尚未完成的是把人工复核签署为三校 page-native gold、迁移 school verifier，
以及更新 T3 gold contract 后重跑完整 judge。因此本状态项是“实现和真实运行已
验证，但正式标准验收未闭环”，不能转为 `verified`。

## 当前切片

- 把学校 T2 verifier 从旧 source-range gold 迁移到 page-native gold；
- 将本轮人工复核结果经独立审核后签署为三校 page-native gold；
- 更新 T3 gold contract 后重跑完整 judge。

## 下一门禁

下一门禁是正式签署人工页面 gold 并迁移 verifier。不得因为本轮 live 人工复核为
100%，就直接把同一次 AI 输出自动写成 signed gold。

## 完成证据

完成与关闭必须同时具备：

1. T2 AI 页区间输出、严格 schema 和 materializer 已落地；
2. 每个真实渲染页恰好归属一个连续 unit range；
3. T3/T5/T6 只消费新的 final T2，且不存在同页跨 unit；
4. 三校 replay 和 MiniMax live T2 均通过页面覆盖、边界、单元顺序及下游消费门禁；
5. 最终 Word 中每个非首单元确实从新页开始；
6. 旧 `same_page_allowed`、`shareable_flow` 和 AI 自报 `page_policy` 的业务消费残留清零。
