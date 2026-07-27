---
status: implemented
owner: template-generation
stage: T3
created: 2026-07-22
last_updated: 2026-07-26
issue: T3-HIERARCHICAL-AI-ISSUE-07
plan: T3-HIERARCHICAL-AI-PLAN-07
---

# T3 Hierarchical Stage Input and Sparse Decisions

## Current conclusion

层级 Stage Input、稀疏递归、atomic coverage、AI 判断物化和唯一 final 发布已经进入正式 live/replay/template-generate 路径。根据用户确认，T3 已收敛为 AI-only：程序只负责事实投影、final/hash 校验、动作约束、继承展开和安全 Keep，不再拥有独立 Code 判断路线，也不执行 Word 动作；Word 动作属于 T6。结构、过程证据、指标口径和最终输出合同已经落地，但三校动作准确率、调用成本和人工 gold 签核尚未闭环，因此本状态项不能进入 verified/closed。

## Expected vs observed

Expected：T3 只从 sealed L1 与本次发布的 T2 final 构造分层输入，从 unit/object 开始，在最粗安全层级停止；只有混合对象沿合法直接 child 下钻；AI 是唯一判断主权，程序将 Keep/Fill/Delete/Split 在共同 atomic identity 上校验并物化。AI 缺失、失败或冲突时显式保留 availability / safe Keep，不回退旧 Code policy。

Observed：T3 正式业务入口已经拒绝 AI observation/candidate/缺 final metadata 的上游，只接收 `02_unit_map.yaml` final；`03.0_t3_hierarchical_stage_input.json` 记录 L1、T2 final artifact/hash/availability 和 tree hash。命名调试入口 `template stage t3 --t2-artifact` 仍有意允许普通 `unit_map` 在本次进程内包装为本地 final handle，以便固定单元范围单独观察 T3；该结果不进入正式验收，也不证明 T2 正确。run 已确定性展开为带精确字符范围的预生成 span 原子叶；动作矩阵、直接 child、Split 默认 Keep、Delete high-confidence、深度/调用预算和 provider failure 都有确定性校验。完整同质 span 可安全投影回 raw run，混合或不完整 span 显式进入 trace 并在执行语义上降级 safe Keep。最终 `03_element_spec.yaml` 带 `stage_id=T3`、`result_role=final`、availability、L1/T2 final/Stage Input refs、AI lineage、正式 elements/ai_traces/flags；原始 observation、sparse trace 和 materialization trace 只作自检证据。旧 T3 Code/Merge、flat/unit-window、proposal/overlay 和正式业务兼容输入均已退出。但 L1 仍缺 merge/nested/empty-cell 完整事实，TOC field 与展开段落缺所有权关系，live 会在目录过度下钻。

## Proven evidence

- 聚焦单测与下游消费：见 Plan 07 Implementation Ledger；最终回归命令和计数由本轮交付记录。
- 2026-07-22 首次 run-leaf 实施快照：tree valid 全部为 true；当时的 run-leaf members 为 812 / 566 / 1470，fallback/manual 为 104 / 0 / 18。该数字是补入 span 原子层前的历史证据，不再作为当前 atomic member 总数。
- run→span 补充检查：三校 run/span 节点分别为 `708/836`、`565/663`、`1449/1496`，multi-span run 为 `76/50/37`；T3 自有 `body_flow` gold run 缺失数均为 0。标准中额外的 `9/12` 条南京农业大学/北京大学 gold 属于不参与本门禁的 `header_footer`。
- 三校 T3 gold 已迁移到 `adaptive_run_or_span` 契约并完成代理 Word 审查：163 个候选中 145 个确认为整 run 统一动作，18 个确认为 mixed run；源重绑定前物化为 77 条 exact span。北大 3 个原 `unknown` 已拆成明确 Keep/Fill。严格校验器证明 span 连续、无重叠、无缺口且与对应 L1 原文一致。代理审查不代替人工签核，因此三校仍保持 `PARTIAL`。
- 2026-07-23 用户确认湖南农大当前 `source_template.docx` 是手工纠错后的 canonical source。active source hash 已由 `6d66a292…` 重绑定到 `776649b4…`；新旧 320 个 source-seq 与 493 个逻辑 run 文本逐项一致，T2 边界保持不变。Word 重存使 raw run 从 708 变为 674、渲染页数从 22 变为 17；T3 gold 已按逻辑 run 和字符位置精确投影，当前覆盖 674 个 raw run，其中 12 个 mixed run 为 52 条 span，严格校验通过。证据位于 `test_outputs/debug/template_generation/20260723_hunannongye_source_rebind_v1/`。
- final contract 反例证明正式 T3 业务链拒绝 AI unit observation、错误 stage/artifact、缺 final metadata 和 L1 hash 不一致的上游；T3 roots 只来自本次 T2 final。命名调试入口包装普通 `unit_map` 是独立的开发工具例外，不纳入该生产合同反例。
- template-generate replay contract 证明有序层级输入与 sparse trace 同 tree hash，coverage member 唯一，canonical `03_element_spec.yaml` 绑定 L1、T2 final 和 Stage Input hash。
- sparse decision 测试覆盖终局停止、合法 Split、inline child、非法 child、低置信 Delete、fill 缺 source、深度/调用预算和 provider 失败 safe Keep；过程产物保留 call count、resolution counts 和 coverage validation。
- T3 gold evaluator 已使用 `adaptive_run_or_span`，输出 exact action accuracy、macro-F1、per-action/per-unit、coverage、conflict/unknown 和 zero-false-delete hard gate。
- T3 清理回归证明 proposal schema 仅允许 T2/T4，observation bridge 不再生成 T3 round；AI 判断绕过 proposal/reconciler 直接物化；AI 关闭时仍写 `t3_materialization_trace` 并保持 `availability=NOT_AVAILABLE`。
- 湖南农大 live 证明直接叶子批量决策可把 cover 从十余次调用缩为一次；TOC 仍过度下钻，run 主动中止且不计 accuracy。
- 湖南农大独立 Word A/B：`test_outputs/debug/template_generation/20260723_t3_gold_t2_code_vs_ai_ab/hunannongye/`。Code 与 AI-primary 的 T2 unit semantic hash 相同且 T2 standard audit 均 PASS；T3 route 分别为 `code_raw` / `ai_raw`，`merge_enabled=false`。两份 DOCX 均可打开并由 LibreOffice 渲染为 19 页 A4。
- 本次 AI live 共 96 次调用、覆盖 812 个 atomic member；403 个 direct/inherited member accepted，409 个因完整性/动作契约降级为 AI 路线自身的 safe Keep。未传 T3 gold，未运行 accuracy baseline，不能用于晋升。

## Impact

- 上游：sealed L1 的 table merge/nested/field range 投影决定 T3 是否能安全终局。
- 当前阶段：T3 hierarchical input、prompt、provider、cache/replay、sparse decision、materializer 和 self-check trace。
- 下游：canonical AI `element_spec`、availability、T5/T6 actions 和 trace；fallback/contested 只能物化为 safe Keep。具体适配见 [`t3-ai-only-downstream-adaptation.md`](./t3-ai-only-downstream-adaptation.md)。
- 文档：AI-only 是已确认的路线契约；动作准确率仍保持未验证，不用路线收敛代替质量门禁。

## Residual and next proof

1. 补 L1→T3 的 `gridSpan/vMerge`、nested table、empty/multi-paragraph cell 和 field→paragraph ownership。
2. 生成真实 target crops，不以整页+bbox 代替 crop 完成。
3. 历史 Word A/B 已暴露旧 Code 与 AI 路线差异；Code 路线现已退出，只保留为历史证据。后续质量判断只评当前 AI canonical 输出。
4. 解决 409 个 fallback member 的完整性/动作契约问题和 TOC/长表调用放大后，再冻结严格可比 baseline，重跑三校同模型 accuracy A/B。
5. 架构、输入/动作/指标和 final 输出合同已按用户确认写入 canonical 文档；达到 exact/macro-F1 +0.05、单校退化和 false-delete 门禁后，才能把本状态从 implemented 晋升为 verified。
6. 三校 gold 的 163 个候选已经过代理 Word 审查；湖南农大 source rebind 后，正式 ledger 当前包含 18 个 mixed run 的 87 条完整 span items，候选队列和 `unknown` 均已清零。剩余门禁是由人工复核完整 scored universe、确认或修正代理结论并补齐 `review_metadata` 的审核人和时间；此前不得把 `gold_status` 从 `PARTIAL` 晋升为 `VERIFIED`。

## No-touch / parked

- 不修改 T2 boundary/taxonomy 和 T4 语义。
- 不把 gold、标准或代码 policy 写回 Stage Input。
- 不在本状态项内重新设计 T5/T6/T7、route replay 和 judge；统一 final 链与剩余诊断口径由 [`t3-ai-only-downstream-adaptation.md`](./t3-ai-only-downstream-adaptation.md) 追踪。
