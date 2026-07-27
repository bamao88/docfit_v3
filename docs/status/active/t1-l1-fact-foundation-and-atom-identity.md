---
status: planned
owner: template-generation
stage: T1/L1/T2/T3/T5/T6/T7
created: 2026-07-26
last_updated: 2026-07-26
issue: T2T3T4-AGENT-ISSUE-15
plan: T1L1-FACT-FOUNDATION-PLAN-15
---

# T1/L1 三组件事实底座与叶子身份

> T4 本轮暂缓，只保留兼容边界；gold 必须在本状态 verified 后由 Stage Standards Plan 03 迁移。

## 当前结论

Plan 08 已经完成 sealed L1 和 shared hash，但当前 T1 仍只有一个
`01_document_facts.json`，render 事实没有成为并列 component；L1 也没有叶子级
`source_atom_seq`、统一 membership、text address 和 locator map。

本轮目标是：

- T1 正式产出正文、全局、render 三个 component；
- 现有 `01_document_facts.json` 只作为确定性兼容投影；
- L1 保留现有八组字段并新增四组技术索引；
- 保持 `source_seq` 名称、数值和粒度不变；
- T2/T3 projector 继续产出原有阶段输入；T5/T6/T7 只做兼容回归；
- T6 不切换 locator/resolver，下游 identity cutover 另立后续计划；
- 当前 gold 冻结，最后另行迁移。

## Expected vs observed

Expected：任一源内容叶子都能用唯一 `source_atom_seq` 被查询，经 selection 展开并通过
`locator_ref` 安全定位到 OOXML，同时可绑定 page/bbox；正文、全局和 render facts 来自
同一 source snapshot，且下游只读取 sealed L1 或确定性 stage view。

Observed：当前 `source_seq` 只覆盖较高层正文流，run/object/span/source ref 分担不同定位
职责；T1/L1 缺少统一叶子身份和 locator 契约。L1 一旦升级，完整 artifact hash 会沿
same-run lineage 变化，但这不表示 T2–T7 的业务输入和逻辑都要修改。

## 影响

| 范围 | 当前影响 |
| --- | --- |
| T1/render | 需要新增三个正式 component、hash、coverage 和输出索引 |
| L1 | schema/version/hash 升级，同时兼容当前八组字段 |
| T2 | 只改 stage-input projector 的事实来源；`01.6/02.1` 和业务 final 保持 |
| T3 | projector 可使用 membership，但 `03.0` 和业务 final 保持 |
| T4 | 不设计、不修改、不验收；仅兼容旧 reader 或确认已零读取 |
| T5 | 不改业务代码，只验证 same-run L1 hash/ref 自动传播 |
| T6 | 继续使用当前 resolver，只验证 action/target/DOCX 不变 |
| T7/POST_T6 | 继续使用当前 verifier，只验证报告不回归 |
| gold | 当前冻结；Plan 15 verified 后由 Plan 03 迁移 |

## 对应计划和闭环

- Issue：`docs/plans/2026-07-26-template-parse-refactor-t1l1-fact-foundation-issue-15-leaf-identity-and-split-artifacts.md`
- Plan：`docs/plans/2026-07-26-template-parse-refactor-t1l1-fact-foundation-plan-15-centralize-facts-and-preserve-stage-inputs.md`

当前只完成讨论、影响确认和实施计划，代码/schema/真实样本尚未实施，因此状态为
`planned`。闭环必须至少达到真实 DOCX/render 的 L4 安全阶梯，并完成三校阶段输入、
fixed replay、最终 DOCX/报告语义对比和残留扫描。
