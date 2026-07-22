---
status: draft
owner: template-generation
stage: T3
topic: hierarchical-ai
doc_type: plan
plan_id: T3-HIERARCHICAL-AI-PLAN-07
source_issue:
  id: T3-HIERARCHICAL-AI-ISSUE-07
  doc: docs/plans/2026-07-22-template-parse-refactor-t3-hierarchical-ai-issue-07-flat-stage-input-and-output.md
previous_plan:
  id: T3-ELEMENT-PLAN-06
  doc: docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md
discussion_sources:
  input: docs/human/t3-stage-input-hierarchical-structure-discussion.md
  output: docs/human/t3-ai-hierarchical-output-principles-discussion.md
created: 2026-07-22
last_updated: 2026-07-22
---

# T3 Plan 07：分层 Stage Input 与稀疏递归 AI 决策

## Summary

本计划把两份讨论稿转成一轮可验证实现：先从 sealed L1 和对应 T2 route 建立完整、可追踪、带真实视觉证据的 T3 节点树；再让 AI 从 unit 开始，在 unit/table/row/cell/paragraph/run/span 中选择最粗安全终局动作或 Split；最后确定性展开 atomic coverage，完成 code/AI/merged 比较并用三校固定输入 A/B 验证准确率。

讨论稿仍不是 canonical 契约。只有本计划的真实准确率和安全门禁通过、且用户确认结论后，才更新 `docs/current/template-generation-architecture.md` 与 `docs/current/template-generation-testing.md`。

## Execution Contract

### Target Capability

```text
sealed L1 + corresponding T2 route
  → complete hierarchical T3 Stage Input with real visual evidence
  → sparse Keep/Fill/Delete/Split decisions
  → stop-or-descend orchestration
  → deterministic inheritance and atomic coverage ledger
  → code/AI comparison and merged element decisions
  → fixed-input three-school accuracy A/B
```

完成后必须具备：

1. 每个 T2 unit 有唯一 T3 根节点；table/paragraph/source_object 等直接子节点可稳定引用。
2. 表格至少能沿 table→row→cell→paragraph→run 下钻；普通文本至少能沿 unit→paragraph→run 下钻。
3. 每层输入提供适合本层判断的完整文字、必要样式/结构、直接子节点摘要和真实图片/crop。
4. 节点终局 Keep 后不再调用后代；后代动作由程序展开为 inherited coverage。
5. 结构保留但内部动作混合时输出 Split，而不是错误整体 Keep。
6. 只有 Split 中的合法直接子节点进入下一次调用；递归有深度、预算、失败和完整性边界。
7. AI 不自造身份、父子关系、content 或 span；越界输出被拒绝。
8. direct/inherited/fallback/contested 在 artifact、比较、merged 和报告中保持可区分。
9. 当前正式 T3 prompt 替换为分层节点 prompt，不再要求所有内容默认进入 run 标注。
10. 三校固定输入 A/B 达到显著提升阈值且误删不恶化后，才允许迁入 canonical 长期文档。

### Non-Goals

1. 不修改 T2 单元边界、taxonomy 或分页语义。
2. 不修改 T4 全局版式识别。
3. 不把 gold、学校标准或下游判断写入 T3 Stage Input。
4. 不用对象级整体 Keep 掩盖输入截断、成员遗漏或视觉不完整。
5. 不默认允许 unit/table 宽泛 Delete；不因递归失败扩大删除范围。
6. 不在本轮重新设计学生内容提取或字段匹配体系。
7. 不以 schema、artifact、replay、单测或调用减少单独作为完成证据。

### Accuracy Promotion Gate

“明显提升”首版量化为以下条件同时满足：

1. 使用 hunannongye、nannong-undergraduate、pku-graduate 三校同一批 sealed L1、T2 gold、T3 gold、模型、temperature 和解码参数。
2. baseline 固定为本计划实施前已提交的正式 T3 路径；candidate 使用新分层输入和输出。
3. 禁止把不同首轮模型随机输出伪装成结构改造收益；优先固定输入并记录全部 prompt/input/model hash，必要时做多次重复采样和置信区间。
4. 三校合并 `exact_action_accuracy` 至少提升 `+0.05` 绝对值。
5. 三校合并 `action_macro_f1` 至少提升 `+0.05`。
6. 至少两校准确率提升，任何单校不得下降超过 `0.02`。
7. false delete 总数不得高于 baseline；若 baseline 为 0，则 candidate 必须继续为 0。
8. Fill/Delete precision 不得因召回提升出现不可接受退化；具体逐动作阈值在 Phase 0 固定 baseline 后写入同一计划，不允许看完 candidate 后倒改门槛。
9. 输入节点 coverage、继承 coverage 和绑定失败不得用排除样本提高表面准确率。

如果未达到以上阈值：

- 状态只能是 `implemented_in_part` 或 `blocked_by`；
- 保留实验实现或按证据回退，但不得晋升为 canonical 正式契约；
- 报告具体是输入完整性、层级停止、Fill/Delete 判断、模型能力还是 gold 粒度导致未提升。

### Completion Signals

1. T3 hierarchical Stage Input schema、builder 和 validator 已进入正式 live/replay/code 路径。
2. unit/table/row/cell/paragraph/run/source_object 代表 fixture 证明身份、父子关系和完整性。
3. 图片作为真实模型附件发送，visual_ref/target_ref/bbox/hash/coverage 可追踪；text-only 明确降级。
4. sparse decision schema、parser 和 stop-or-descend orchestrator 已进入正式路径。
5. 整体 Keep、正确 Split、混合 run、非法 child ref、截断大表、跨页表格和子调用失败反例通过。
6. atomic coverage ledger 完整且 direct/inherited/fallback/contested 互斥可追踪。
7. code/AI/merged 可在共同 atomic identity 上比较，跨层决策不会按原始条目数误判。
8. T3 merged 和下游 element/span trace 实际消费新判断，不只是 side artifact。
9. 单测、契约测试、live/replay、三校 A/B、残留扫描和最终报告全部完成。
10. Accuracy Promotion Gate 通过且用户确认后，才更新 canonical 架构和测试文档。

### Anti-Degradation Rules

1. 不允许只改 prompt，不重构输入树、编排和继承物化。
2. 不允许 unit/table 只看到代表内容或部分页面时产生覆盖全部后代的高置信终局动作。
3. 不允许“保留表格结构”直接等价为“表格所有内容 Keep”。
4. 不允许 AI 枚举所有 run 来模拟稀疏决策树。
5. 不允许失败 Keep 伪装成正常 inherited Keep。
6. 不允许默认 child action 为 Delete。
7. 不允许 AI 自由创建 row/cell/run/span 或跨层 inspect refs。
8. 不允许以调用减少换取动作 accuracy 或 coverage 下降。
9. 不允许 baseline/candidate 使用不同 gold、不同 T2 上游、不同模型参数或未记录的缓存状态。
10. 不达到三校质量门禁时，不更新 `docs/current/` 为正式能力。

### Verification Matrix

| Gate | Command / Evidence | Required Result |
| --- | --- | --- |
| schema/unit | T3 input/decision/validator/materializer focused tests | 节点树、动作矩阵、递归、继承和失败反例全部通过 |
| prompt | assembled messages snapshot/contract tests | 每层 prompt 只消费本层输入；图片引用与附件一致 |
| contract | template-generation agent live/replay contracts | live、replay、fallback 走同一正式编排路径 |
| visual | multimodal transport records + attachment hash audit | unit/object/crop 真实发送，覆盖状态准确 |
| route | code_raw/ai_raw/merged common atomic evaluator | 三路使用相同 identity/gold；merge delta 可解释 |
| real sample | 三校固定输入 baseline/candidate A/B | 达到 Accuracy Promotion Gate |
| safety | false-delete、非法引用、截断、失败注入 | 不扩大删除；fallback/人工复核可追踪 |
| residual | 旧 flat input/run-default prompt/重复 mapper 扫描 | 正式调用方清零或逐项有迁移理由 |
| downstream | merged/T5/T6 trace and final DOCX checks | 新决策被实际消费；身份失败不扩大动作 |
| docs | user approval + canonical diff | 仅质量门禁通过后更新长期文档 |

### Residual Policy

- 未完成输入节点类型：记录 `remaining_gap`，不得用 source_seq 猜测替代。
- 视觉不完整：记录 `visual_incomplete`，不得宣称 multimodal 整体判断。
- span 不可执行：混合 run Keep/manual review，不自由拆分。
- 某校不满足门禁：保留完整 mismatch、owner 和下一轮 issue，不用三校平均掩盖。
- 下游尚未消费：状态保持 `implemented_in_part`，不得迁移 canonical 文档。

## Implementation Checklist

### Phase 0：冻结 baseline 与批准首版选择

- [ ] 记录 baseline commit、三校 L1/T2/T3 gold hash、模型参数、缓存和当前准确率。
- [ ] 固定逐动作 precision/recall 最低门槛，禁止 candidate 出结果后修改。
- [ ] 从输入讨论稿批准首版节点树、visual completeness 和大表策略。
- [ ] 从输出讨论稿批准首版动作矩阵、Split 默认、失败状态和 atomic leaf。
- [ ] 确认 Plan 06 与本计划的职责：本计划接管分层输入输出，Plan 06 保留已完成证据和未覆盖的 T6 精确执行项。

### Phase 1：Hierarchical Stage Input

- [ ] 定义 versioned node/envelope/completeness/visual schema。
- [ ] 从 sealed L1 + 对应 T2 route 构建 unit 根和直接子节点。
- [ ] 建立 table→row→cell→paragraph→run 与普通 paragraph→run 关系。
- [ ] 接入 source_object、跨页、合并单元格、嵌套表格和多段落 cell。
- [ ] 为每层生成完整文字、必要样式/结构和 direct-child 摘要。
- [ ] 生成 unit/page/object/row/cell/paragraph crop，并绑定 visual_ref、bbox、hash 和 coverage。
- [ ] 增加完整性、截断、未绑定成员和树 validator。

### Phase 2：Sparse Decision Contract 与递归编排

- [ ] 定义 terminal Keep/Fill/Delete 与 Split schema、节点动作矩阵和条件字段。
- [ ] 定义 accepted/fallback/manual_review/failed/contested 状态，不与动作枚举混用。
- [ ] 编排从 unit 根开始，只沿合法 inspect_child_refs 递归。
- [ ] 实现终局停止、最大深度/预算、重试、部分结果和失败回退。
- [ ] cache/replay key 绑定 input tree、visual、prompt、model 和 contract version。

### Phase 3：正式 Prompt 与 Provider 接线

- [ ] 将 unit/object/row/cell/paragraph/run prompt 分离为可审阅资源。
- [ ] 每层 prompt 明确当前 target、直接 children、context-only 和允许动作。
- [ ] 删除“所有内容默认逐 run 标注”的旧正式假设。
- [ ] Kimi/MiniMax 使用同一 assembled prompt 和真实视觉附件契约。
- [ ] text-only 路径显式记录 visual unavailable，不伪装多模态。

### Phase 4：继承、覆盖、比较和 Merged

- [ ] 展开 direct/inherited/fallback/contested atomic coverage ledger。
- [ ] 校验每个 atomic member 唯一 resolved action，无 silent gap 或重叠覆盖。
- [ ] code route 生成可比较 sparse decision 或同一 atomic ledger。
- [ ] code/AI 跨层结果在共同 identity 上比较并保留原始停止层级。
- [ ] merged 消费完整动作、条件语义、identity、evidence 和 trace。
- [ ] materializer 按语义组合 element，不把整体 Keep 强制膨胀为无意义 element。

### Phase 5：测试与真实 A/B

- [ ] 单元、对象、表格、row/cell、paragraph、run/span 和 source object fixtures。
- [ ] 整体 Keep、正确 Split、错误提前 Keep、过度下钻和结构保留反例。
- [ ] 跨页、大表、合并/嵌套表格、图片缺失、截断、非法 ref 和失败注入。
- [ ] 运行聚焦单测、agent contract、template-generate/replay 和 route evaluator。
- [ ] 用三校固定输入跑 baseline/candidate；报告 exact accuracy、macro-F1、各动作 precision/recall、false delete、coverage、调用数和层级指标。
- [ ] 对结果做 mismatch/root cause/owner/fix plan，不用总 PASS 掩盖单校或动作退化。

### Phase 6：晋升或残留

- [ ] Accuracy Promotion Gate 通过后由用户确认讨论结论。
- [ ] 通过后更新 canonical T3 架构和测试契约，并同步 status/issue/plan/index。
- [ ] 未通过则保持讨论稿和 `implemented_in_part`，记录下一轮改进，不更新长期文档。

## Commit Strategy

建议按能力分提交，且每个提交只包含本轮相关差异：

1. issue/plan baseline；
2. Stage Input schema/builder/validator + tests；
3. sparse decision/orchestrator + tests；
4. prompt/provider/visual transport + tests；
5. inheritance/comparison/merged + tests；
6. 三校 A/B evidence 与状态；
7. 仅在门禁通过并经用户确认后提交 canonical 文档迁移。

