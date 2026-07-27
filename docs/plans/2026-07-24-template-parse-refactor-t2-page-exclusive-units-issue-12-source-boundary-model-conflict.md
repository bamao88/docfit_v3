---
status: implemented_in_part
owner: template-generation
stage: T2T3T5T6T7
topic: t2-page-exclusive-units
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-12
issue_sequence: 12
severity:
  - P1
previous_issue:
  id: T2T3T4-AGENT-ISSUE-11
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-11-unit-pagination-signal-loss.md
  status: draft
previous_optimization:
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-11-unit-pagination-alignment.md
  summary: Plan 11 已打通 T2 page_policy 到 T5/T6 的消费链，但仍允许同页单元和可共享页面流；本轮改变的是更上层的单元边界模型。
next_plan: docs/plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-plan-12-exclusive-contiguous-page-contract.md
created: 2026-07-24
last_updated: 2026-07-26
related_status:
  - docs/status/active/t2-page-exclusive-unit-contract.md
---

# T2 Issue 12：source 边界模型与独占连续页面目标冲突

## 当前闭环状态

生产链中的冲突已经消除：T2 只接受 AI 页面分组，旧 code、同页边界、可变分页策略和 merged 选择均已退出。2026-07-26 三校付费 MiniMax live 和最终 Word fresh 分页验收已通过，人工视觉复核的 26 个页面组、56 个页面归属均正确。当前未闭环的是正式验证层：三校标准仍是旧 source 边界审阅证据，尚未独立签署 page-native gold，school verifier 与 T3 gold contract 也未完成迁移。因此本 issue 保持 `implemented_in_part`。

## 问题摘要

当前 T2 把单元定义为一段连续 `source_seq`，允许两个顶层单元出现在同一渲染页，再通过
`page_policy.start/scope` 判断它们能否同页继续。新的产品决定是：

```text
一个 T2 单元 = 一段独占的连续渲染页面；
同一页不能属于两个 T2 单元；
下一个 T2 单元一定从下一页开始。
```

这不是 prompt 微调，而是 T2 顶层单元、边界坐标和分页责任的共同变化。

## Expected vs observed

Expected：

1. T2 先按页图判断哪些连续页面属于同一单元。
2. 每个页面恰好属于一个单元，页面区间连续、无重叠、无遗漏。
3. 同一页上的多个语义块合并为一个页面级 T2 单元，由 T3 在单元内部继续识别元素。
4. T2 AI 只判断单元 ID、名称和页面首尾；固定分页策略由程序派生。
5. 第一单元从文档开头开始，后续单元全部另起页；所有单元都独占自己的连续页面范围。

Observed：

1. 当前 AI 契约输出 `boundary.start_source_seq/end_source_seq`。
2. 当前 `page_policy.start` 允许 `same_page_allowed`，`scope` 允许 `shareable_flow`。
3. 当前边界可以落在页面内部，同一页可被多个 T2 单元覆盖。
4. 当前 AI 需要重复判断 `page_policy`，即使新规则下答案已经能被程序确定。
5. T2 gold、route-eval 和下游消费仍以旧 source 边界与可变分页标签为准。

## 影响与风险

| 影响面 | 需要处理的问题 |
| --- | --- |
| T2 输入 | 页图必须成为主序列；文本 JSON 只能作为页面内客观绑定，不能提前给单元语义。 |
| T2 输出 | 权威边界改为 `start_page/end_page`；AI 不再输出可变 `page_policy`。 |
| materializer | 页面区间要确定性展开为现有下游需要的 `source_seq_refs/source_refs`。 |
| route/merge | 任一路线都不能重新引入页内切分；不合规候选不能进入 final。 |
| T3 | 同一页多个旧 unit root 会合并，T3 需要在更大的页面级窗口内处理元素。 |
| T5/T6 | 每个非首单元都必须另起页；页面独占不能被解释为强制压缩到一页。 |
| gold/judge | 页面区间成为主评分；source 绑定只做派生正确性和可追踪性检查。 |

## 已确认的产品取舍

1. 如果“声明 A”和“声明 B”在同一页，它们不再是两个 T2 单元，而是一个组合单元。
2. `same_page_allowed` 逻辑退出 T2。
3. 单页区间只是当前源模板中的一页，不表示填入学生内容后必须永远保持一页。
4. 一段内容跨页时，只要它仍属于同一功能窗口，就继续归入同一个 T2 单元。
5. 无法判断名称时可以使用 `unknown_unit`，但不能因此遗漏页面。

## 根因归属

这不是单一代码 bug，而是旧产品模型与新产品决定不一致：

- 旧模型把语义块作为 T2 原子；
- 新模型把独占页面组作为 T2 原子；
- 现有 Prompt、schema、materializer、route、gold 和下游都编码了旧模型。

## 验收门禁

1. page 1 到 `page_count` 被 T2 units 完整且唯一覆盖。
2. 相邻单元满足 `next.start_page = previous.end_page + 1`。
3. 任何同页跨 unit、页面 gap、页面 overlap 或越界都使 T2 final 不可发布。
4. AI 输出不再包含 `source_seq` 边界或 `page_policy`；两者均由程序绑定或派生。
5. T3 使用的每个 source 节点都能回查到唯一的 T2 页面区间；跨边界节点冲突必须显式失败或进入人工复核。
6. 最终 Word 中第一单元不插入多余分页，所有后续单元均从新页开始。

本 issue 只记录问题事实；执行契约见 Plan 12。
