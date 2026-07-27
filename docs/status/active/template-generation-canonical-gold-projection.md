# Template Generation Canonical Gold Projection

status: planned

stage: template-generation T1/L1/T2/T3/T4/T5/T6/T7/POST_T6

discovered_at: 2026-07-25

last_updated: 2026-07-26

source_issue: `docs/plans/2026-07-25-template-parse-refactor-stage-standards-issue-03-duplicated-gold-sources.md`

source_plan: `docs/plans/2026-07-25-template-parse-refactor-stage-standards-plan-03-canonical-gold-stage-projections.md`

## 发生了什么

用户决定把学校测试 gold 切换为“一份 canonical school gold、按阶段确定性投影”的模式。

当前每校仍分别维护 `final_template.expected.yaml` 和 T1–T5 阶段 standards。它们来自
同一源 DOCX 与人工审查，却重复保存 source/review/unit 信息，评测器也直接读取这些
独立文件，而不是从一个 canonical source 生成阶段视图。

## Expected vs observed

Expected：每校每版本只维护一份 `school_template.gold.yaml`；T1/T2/T3/T4/T5/POST_T6
评测通过纯函数选择本阶段 gold，L1/T6/T7 通过同一 canonical binding 取得
contract/evidence view，并统一记录 canonical hash、projection version 和 view hash。

Observed：每校维护六份可编辑 gold/standard；共享字段靠合同测试保持部分一致，source
rebind、unit order 或 review 更新仍需要多文件同步。

## 影响

- standards 文件布局与 target 登记；
- standard-quality、verifier、judge、route-eval、template-gap；
- 三校 T1/T2/T3/T4/T5/final-template 的完整 gold 制作、审核与独立认证；
- L1/T6/T7 contract/evidence-only 评测接入；
- source rebind、审核状态、报告 hash 和三校测试。

正常模板生成业务流程不受权读取 gold。

## 当前状态

Issue/Plan 03 已建立，等待用户批准实施。目标方案不永久保留双写或 stage-file fallback：
先 shadow parity，再原子切流，最后删除旧文件。

关键协调项与门禁：

0. T1/L1 Plan 15 必须先完成三组件事实、`source_atom_seq`、selection/locator 和现有
   stage-input compatibility 验证并进入 `verified`；在此之前冻结现有 gold、standard
   和 projector，只作为回归 oracle，不开始 schema 切流或改写学校答案；
1. `PARTIAL/MISSING/unknown` 只允许作为迁移中的诚实状态，不能作为最终切流或关闭条件；
2. T2 使用已批准的 page-native 字段形状，并在本次交付中关闭 Plan 12 剩余的三校
   page gold、verifier、judge 和人工签署门禁；
3. T3 现有 adaptive run/span gold 必须零差异迁移并完成最终签署；
4. T1、T4、T5 和 final-template 必须补齐三校完整 scored universe、证据与
   `VERIFIED` 认证，不能转交给后续计划；
5. L1/T6/T7 不新增虚假的学校答案 gold，但 contract/evidence projector、fixture、
   统一报告和 full-chain owner 归因必须接通；
6. migration diff 必须由 human standard owner 批准并绑定 candidate file/semantic hash；
7. 三校全阶段 gold、真实评测消费者切流、最终 Word 验收和旧路径残留清零后才能关闭。
