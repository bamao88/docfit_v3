---
status: implemented_in_part
owner: template-generation
stage: T3
topic: hierarchical-ai
doc_type: issue
issue_id: T3-HIERARCHICAL-AI-ISSUE-07
issue_sequence: 07
created: 2026-07-22
last_updated: 2026-07-23
previous_issue:
  id: T3-ELEMENT-ISSUE-06
  doc: docs/plans/2026-07-02-template-parse-refactor-t3-element-policy-issue-06-placeholder-span-granularity.md
previous_optimization:
  doc: docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md
  summary: Plan 06 以 run/span 为主要决策粒度，尚未建立单元到对象再按需下钻的稀疏递归输入输出契约。
next_plan: docs/plans/2026-07-22-template-parse-refactor-t3-hierarchical-ai-plan-07-stage-input-sparse-decisions.md
discussion_sources:
  - docs/human/t3-stage-input-hierarchical-structure-discussion.md
  - docs/human/t3-ai-hierarchical-output-principles-discussion.md
---

# T3 Issue 07：当前输入与输出不能按对象层级安全停止或下钻

## 问题摘要

T3 当前已经有单元级路由、table/text-flow 对象摘要和 run 级动作判断，但没有形成一棵由 sealed L1 和对应 T2 route 派生的、可递归引用的节点树。AI 也没有统一的稀疏决策契约来表达“当前对象整体 Keep”或“当前对象 Split，只检查指定直接子节点”。

结果是 T3 容易在两个方向退化：

- 本可对整张表、完整声明或段落整体 Keep，却继续进入大量 run 调用；
- 对象结构需要保留但内部存在 Fill/Delete 时，用宽泛默认策略覆盖内部差异，压低动作召回。

## Expected vs observed

Expected：

```text
1. T3 Stage Input 从每个 T2 unit 根节点开始，提供稳定 unit/object/paragraph/table/row/cell/run 身份、直接父子关系、客观事实、完整性和真实视觉证据。
2. AI 在每个实际访问节点输出 Keep/Fill/Delete 终局动作，或 Split + inspect_child_refs。
3. 终局动作停止该分支调用，程序确定性展开 inherited atomic coverage。
4. 只有 Split 选中的直接子节点继续下钻；run/span 不是默认输出层。
5. 容器结构保留与后代内容 Keep 分开：结构保留但内部动作混合时必须 Split。
6. direct、inherited、fallback、contested 有不同 trace；code/AI 在共同 atomic identity 上比较。
7. 真实图片作为模型附件发送，并与 target/child ref、bbox 和完整性绑定。
```

Observed：

```text
1. unit overview 主要提供 source_seq、对象摘要、代表性表格行和有限页面图。
2. row/cell/paragraph/run 信息存在于不同投影中，但不是统一、完整、可递归引用的节点树。
3. 大表可能只给代表行；visual evidence 以有限页面选择为主，缺少每层 target crop 与完整覆盖契约。
4. preserve_whole 可以停止整个 unit，但没有每个对象通用的 Keep/Split 递归输出协议。
5. 未认领内容由 source_seq/run fallback 展开，无法完整表达“继承自某个对象终局判断”。
6. 当前 T3 prompt 仍以 run 级动作标注为主，与新的分层输出原则不一致。
7. 湖南农业大学固定输入 A/B 中，动作示例精判开启/关闭均为 exact_action_accuracy=0.2782、macro-F1=0.248，尚未证明质量提升。
```

## 影响范围

- T3 Stage Input builder、视觉附件和完整性；
- T3 unit/object/child prompt 与输出 schema；
- stop-or-descend 编排、缓存和 replay；
- direct/inherited/fallback coverage materialization；
- code/AI/merged 跨层比较；
- T3 gold、route-eval、准确率和调用成本报告；
- T5/T6 对 element/span identity 与对象级 trace 的消费边界。

## 非问题范围

- T2 单元识别和分页质量；
- T4 全局版式判断；
- 学生内容提取和内容匹配本身；
- 用关键词规则替代分层输入输出重构；
- 在准确率门禁通过前更新 canonical 长期架构。

## 根因判断

本轮根因不是缺少某一句 prompt，而是输入、输出和编排粒度不一致：输入以单元摘要和局部窗口为主，输出以 run item 为主，缺少共同的层级身份、递归停止条件、完整性和继承覆盖契约。

## 2026-07-22 实施后事实

已落地的能力包括：分层节点树与 validator、稀疏 stop-or-descend 决策、direct/inherited/fallback/contested atomic ledger、正式 live/replay provider 接线、共同 atomic identity 三路对账，以及 run→预生成 exact span 原子层。完整且同质的 span 动作可安全投影到兼容 raw-run 接口；同一 run 内的混合 span 动作保留精确字符范围、显式记为冲突并进入人工复核，不由执行层任意折叠。

真实三校结构检查已证明树和 atomic coverage 可以闭合，但同时确认两类未解决根因：

- sealed L1 的当前表格投影没有 `gridSpan/vMerge`、嵌套表和完整空 cell/多段落 cell 事实；重复 run 身份只能安全标记为 merge alias + manual review，不能宣称合并单元格已完整建模；
- TOC field 对象与其展开 paragraph 仍是并列成员，没有 field→paragraph 所有权，live 模型会在目录单元过度下钻。
- 三校已签 gold 的评分粒度仍是一条 raw run 一个动作，无法表达同一 run 内的混合 span 动作；当前兼容评分将其记为 run conflict，span 级准确率仍需要独立人审 gold 才能闭环。

因此本 issue 保持 `implemented_in_part`；Accuracy Promotion Gate 未运行出合规三校 candidate，不关闭问题，也不迁移 canonical 文档。

## 验收门禁

1. 输入节点树身份和父子关系可从 sealed L1 与对应 T2 route 确定性重建并校验。
2. unit/table/paragraph 整体 Keep 不调用后代模型，覆盖台账完整且标记 inherited。
3. 结构保留但内部动作混合的对象正确 Split，只访问指定直接子节点。
4. 子调用失败、截断或越界时为显式 fallback/manual review，不伪装成正常 inherited Keep。
5. 三校固定输入 A/B 达到 Plan 07 定义的显著提升阈值，且 false delete 不恶化。
6. 未达到质量阈值时保持 discussion/status，不迁入 `docs/current/`，也不宣称正式能力完成。
