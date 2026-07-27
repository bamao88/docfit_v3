---
status: planned
owner: template-generation
stage: T4/T5/T6/T7/POST_T6
created: 2026-07-26
last_updated: 2026-07-26
plan: T2T3T4-AGENT-PLAN-14
---

# T4 生产阶段暂停与上下游迁移

## 当前结论

长期架构契约已决定：copy-first 模板生成暂停并直接跳过 T4。生产链目标为
`L1 + T2 final + T3 final -> T5 -> T6`；源全局版式由复制源 DOCX 保留，质量责任迁移到
L1 事实完整性、T6 preservation 和 T7/POST_T6 最终 Word 验证。

## Expected vs Observed

- Expected：完整生成不调用 T4 AI、不产出 `04_*`、T4 不参与 availability。
- 当前 observed：代码仍运行 T4 text/vision、发布 `04_global_spec.yaml`，T5 仍要求 T4
  final 并用 `section_profile_refs` 绑定单元。
- 因此当前状态为 `planned`；文档契约已更新，生产实现尚未迁移。

## 影响

- 上游：L1 需要提供可稳定绑定的 section identity/range 和源版式 preservation 基线。
- T5：改为只合并 L1/T2/T3，并机械绑定 T2 unit 到 L1 section。
- T6：继续 copy-first，但必须保护 `sectPr`、页眉页脚、PAGE、styles 和 numbering。
- T7/POST_T6：承接原 T4 的最终版式证明责任。
- 工具链：runtime、provider、artifact、CLI、manifest、judge、route-eval、gold 和测试都要
  删除 T4 required 假设。

## 闭环条件

以 Plan 14 的 Verification Matrix 为准。代码迁移、三校真实 Word preservation 和最终
质量均完成前，本状态不得标记 `verified`。
