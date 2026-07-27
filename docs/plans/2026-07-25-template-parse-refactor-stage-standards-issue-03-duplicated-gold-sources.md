---
status: impact_confirmed
owner: template-generation
stage: cross-stage
topic: stage-standards
issue_id: STAGE-STANDARDS-ISSUE-03
issue_sequence: 03
severity:
  - P1
created: 2026-07-25
last_updated: 2026-07-26
previous_plan:
  id: STAGE-STANDARDS-PLAN-02
  doc: docs/plans/2026-07-03-template-parse-refactor-stage-standards-plan-02-t3-run-span-standard-fill.md
  status: implemented
next_plan: docs/plans/2026-07-25-template-parse-refactor-stage-standards-plan-03-canonical-gold-stage-projections.md
related_status:
  - docs/status/active/template-generation-canonical-gold-projection.md
related_docs:
  - docs/current/template-generation-testing.md
  - standards/README.md
---

# 阶段标准 Issue 03：同一学校 gold 被拆成多份独立维护的事实源

## 问题摘要

每所学校当前同时维护：

- `template_quality/final_template.expected.yaml`；
- T1、T2、T3、T4、T5 五份 `template_generation/*.standard.yaml`；
- `target.standard.yaml` 中对这些文件的独立登记。

这些文件都来自同一份学校源 DOCX 和同一轮人工审查，却重复保存 source hash、
review metadata、unit order、unit identity、元素信息和上游引用。评测器不是从一个
canonical school gold 按阶段投影，而是分别读取这些持久文件。

结果是一次学校标准变更需要同时修改多份 YAML。湖南农大 source rebind 已经证明，
即使正文语义不变，仅 raw-run identity 或 source hash 改变，也必须人工排查并同步
T1–T5、final、target 和 T3 上游 hash；漏改任何一处都会造成 binding mismatch 或
真假不明的阶段结论。

## Expected vs observed

Expected：

```text
1. 每所学校、每个模板版本只有一份 canonical school gold。
2. source binding、review provenance、unit catalog/order 等共享事实只写一次。
3. T1/T2/T3/T4/T5/POST_T6 评测从 canonical gold 确定性投影本阶段 gold view；
   L1/T6/T7 从同一 canonical binding 投影 contract/evidence view。
4. 阶段投影只暴露本阶段拥有的 scored、identity/binding 和 review/evidence 字段。
5. 不同阶段可独立声明 VERIFIED/PARTIAL/DISPUTED/MISSING，不能被一个总状态掩盖。
6. 生成的阶段视图是运行证据，不是第二份可人工编辑的 gold。
```

Observed：

```text
1. target.standard.yaml 分别登记 final_template 和 T1–T5 六份持久标准。
2. stage loader 直接读取各阶段 YAML；final_template 只作为另一份标准和一致性参照。
3. T2–T5 重复 unit_order；所有文件重复 source/review binding。
4. T3 已有完整 adaptive run/span ledger，但仍独立于 final_template 的 unit/element 信息。
5. T4 文件主要是 contract/layout policy 骨架，和 final_template 中的版式要求没有统一投影。
6. gold_status 只在 T3 明确存在；跨阶段状态不能从一个地方完整审计。
```

## 影响范围

- `standards/targets/<target>/v1/` 的学校 gold 文件布局；
- `target.standard.yaml` 的 baseline 登记；
- standard-quality loader、stage verifier、judge、route-eval 和 template-gap；
- T2/T3/T4 isolated gold、hash 绑定、报告中的 gold path/hash/status；
- source rebind、模板版本升级、人工 review 和变更审计流程；
- 三校合同测试、真实 run、文档和残留扫描。

正常模板生成业务流程仍不得读取 gold。本问题只影响测试、评测和人工标准维护。

## 根因判断

早期阶段标准以“先拆文件、让 verifier 有入口”为目标，随后 T3 又补入大量 run/span
gold。实现解决了阶段裁判缺内容的问题，但没有建立学校级 canonical 数据模型和
投影边界，因此“阶段专用视图”被实现成了“阶段专用事实源”。

## 已确认约束

1. canonical gold 不能成为 T1–T7 正常业务输入，只能被测试/评测读取。
2. stage projector 不能推断或改写业务答案，只能选择、归一化和绑定 canonical 字段。
3. 某次 actual、AI observation、judge 结果和 accuracy 不能自动反写 canonical gold。
4. T2 canonical 分区使用已批准的 page-native 字段形状；内容不完整时允许以
   `PARTIAL + unknown` 表达迁移中间状态，但 Plan 03 完成前必须执行 Plan 12 剩余门禁，
   补齐三校页面区间并晋升为 `VERIFIED`。
5. T3 当前 adaptive run/span action 和湖南农大 source rebind 必须无损迁移，并完成
   scored universe 的最终签署。
6. T4 缺少的 scored layout item 必须在本次交付中通过 Word、OOXML/L1 和页面截图补齐；
   不能用 contract 字段或 artifact 存在冒充完整 gold，也不能转交给未定义的后续计划。
7. T1、T5 和 final-template 同样必须完成三校 scored universe、review evidence 和
   独立阶段认证，不能把单一事实源迁移缩成 T3 或 T2/T3/T4 的局部工作。
8. L1、T6、T7 按当前测试契约保持 contract/evidence-only，不虚构学校答案 gold，但其
   projector、fixture、报告和 full-chain 消费代码必须一并闭环。

## 关闭门禁

1. 三校每个模板版本只剩一份可人工编辑的 school gold。
2. 所有阶段评测从同一 canonical hash 投影视图，并记录 projection version/view hash。
3. 共享 source/review/unit 信息没有第二份可编辑副本。
4. T3 投影与迁移前 adaptive run/span scored universe 完全一致。
5. 三校 T1/T2/T3/T4/T5/final-template 的学校级 gold 全部补齐并独立
   `VERIFIED`；不存在由未审核内容造成的 `PARTIAL/MISSING/unknown`。
6. Plan 12 的 page-native gold、verifier、judge 和签署残留全部关闭；T4 完整 layout
   scored universe 在本计划中完成。
7. L1/T6/T7 contract/evidence-only 评测接入、fixture、统一报告和 owner 归因闭环。
8. shadow parity、migration approval ledger、三校 standard-quality、逐阶段
   isolated/cascade judge、template-gap、真实 replay、最终 Word fresh observation 和
   残留扫描通过。
9. 旧 stage standard 与 `final_template.expected.yaml` 被删除，不保留静默 fallback。
