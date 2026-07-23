---
status: implemented
owner: template-generation
stage: T3
created: 2026-07-22
last_updated: 2026-07-23
issue: T3-HIERARCHICAL-AI-ISSUE-07
plan: T3-HIERARCHICAL-AI-PLAN-07
---

# T3 Hierarchical Stage Input and Sparse Decisions

## Current conclusion

层级 Stage Input、稀疏递归、atomic coverage 和 AI 判断精确物化已经进入正式 live/replay/template-generate 路径。根据 2026-07-23 用户确认，T3 已收敛为 AI-only：程序只负责事实投影、身份校验、继承展开、安全 Keep 和 Word 执行，不再拥有独立 Code 判断路线，也不再生成 Code/Merge 产物。结构与安全能力已实施，但三校动作准确率和调用成本尚未闭环，因此本状态项不能进入 verified/closed。

## Expected vs observed

Expected：T3 从 unit/object 开始，在最粗安全层级停止；只有混合对象沿合法直接 child 下钻；AI 是唯一判断主权，程序将判断在共同 atomic identity 上校验并物化。AI 缺失、失败或冲突时显式 `NOT_AVAILABLE` / safe Keep，不回退到旧 Code policy。

Observed：三校树和 coverage 已可闭合，run 已确定性展开为带精确字符范围的预生成 span 原子叶；完整同质 span 可安全投影回 raw run，混合 span 会显式冲突并降级 safe Keep。T3 的 `t3_authority_mode`、Code/Merge element_spec、三路 atomic comparison 和对应 replay/eval 分支已删除，canonical 输出只剩 AI observation、sparse trace 与 `03_element_spec.yaml`。但 L1 仍缺 merge/nested/empty-cell 完整事实，TOC field 与展开段落缺所有权关系，live 会在目录过度下钻。

## Proven evidence

- 聚焦单测与下游消费：见 Plan 07 Implementation Ledger；最终回归命令和计数由本轮交付记录。
- 2026-07-22 首次 run-leaf 实施快照：tree valid 全部为 true；当时的 run-leaf members 为 812 / 566 / 1470，fallback/manual 为 104 / 0 / 18。该数字是补入 span 原子层前的历史证据，不再作为当前 atomic member 总数。
- run→span 补充检查：三校 run/span 节点分别为 `708/836`、`565/663`、`1449/1496`，multi-span run 为 `76/50/37`；T3 自有 `body_flow` gold run 缺失数均为 0。标准中额外的 `9/12` 条南京农业大学/北京大学 gold 属于不参与本门禁的 `header_footer`。
- template-generate replay contract 证明有序层级输入与 sparse trace 同 tree hash，coverage member 唯一，canonical `03_element_spec.yaml` 标记 AI route。
- 湖南农大 live 证明直接叶子批量决策可把 cover 从十余次调用缩为一次；TOC 仍过度下钻，run 主动中止且不计 accuracy。
- 湖南农大独立 Word A/B：`test_outputs/debug/template_generation/20260723_t3_gold_t2_code_vs_ai_ab/hunannongye/`。Code 与 AI-primary 的 T2 unit semantic hash 相同且 T2 standard audit 均 PASS；T3 route 分别为 `code_raw` / `ai_raw`，`merge_enabled=false`。两份 DOCX 均可打开并由 LibreOffice 渲染为 19 页 A4。
- 本次 AI live 共 96 次调用、覆盖 812 个 atomic member；403 个 direct/inherited member accepted，409 个因完整性/动作契约降级为 AI 路线自身的 safe Keep。未传 T3 gold，未运行 accuracy baseline，不能用于晋升。

## Impact

- 上游：sealed L1 的 table merge/nested/field range 投影决定 T3 是否能安全终局。
- 当前阶段：T3 prompt、provider、cache/replay、decision/materializer、bridge/comparison/overlay。
- 下游：canonical AI `element_spec`、T5/T6 actions 和 trace；fallback/contested 只能物化为 safe Keep。
- 文档：AI-only 是已确认的路线契约；动作准确率仍保持未验证，不用路线收敛代替质量门禁。

## Residual and next proof

1. 补 L1→T3 的 `gridSpan/vMerge`、nested table、empty/multi-paragraph cell 和 field→paragraph ownership。
2. 生成真实 target crops，不以整页+bbox 代替 crop 完成。
3. Word 视觉预览已暴露独立路线差异：Code 封面清理过度；AI-primary 封面保留更多内容，但出现封面顶部页码、目录后移和空白页。先由用户审阅产物，再决定下一轮 T3/T5/T6 owner。
4. 解决 409 个 fallback member 的完整性/动作契约问题和 TOC/长表调用放大后，再冻结严格可比 baseline，重跑三校同模型 accuracy A/B。
5. 达到 exact/macro-F1 +0.05、单校退化和 false-delete 门禁后，才可改为 verified 并迁移 canonical 文档。
6. 现有学校 gold 仍是一行一个 raw run，不能给同一 run 内的混合 span 提供细粒度真值；兼容 run 评分只能报告冲突。若要关闭 span 质量门禁，需要补独立的人审 span gold。

## No-touch / parked

- 不修改 T2 boundary/taxonomy 和 T4 语义。
- 不把 gold、标准或代码 policy 写回 Stage Input。
- 旧 flat helpers 暂作兼容测试面；正式调用方已经切到 hierarchy，后续独立清理。
