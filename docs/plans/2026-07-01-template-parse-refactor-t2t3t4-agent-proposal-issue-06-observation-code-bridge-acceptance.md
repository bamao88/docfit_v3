---
status: implemented
owner: template-generation
stage: T2T3T4
topic: agent-observation-code-bridge-acceptance
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-06
issue_sequence: 06
previous_issue:
  id: T2T3T4-AGENT-ISSUE-05
  doc: docs/plans/2026-06-30-template-parse-refactor-t2t3t4-agent-module1-issue-05-observation-input-followups.md
previous_optimization:
  doc: docs/plans/template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md
  summary: Plan 04 已打通 layered submission 与 comparison/manual review/reconciler 的代码生成桥接，但没有把 Module 1 的 ai_observation_bundle 作为主入口，也没有形成桥接后产物对阶段标准的准确率验收口径。
next_plan: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-plan-06-observation-code-bridge-acceptance.md
created: 2026-07-01
last_updated: 2026-07-01
---

# T2/T3/T4 Agent Issue 06：AI 观察产物到代码生成桥接与标准验收缺口

## 真实运行口径

当前已存在两条相关链路：

```text
Module 1:
  render packet -> ai_unit_observation / ai_element_observation / ai_layout_observation

Module 2:
  layered_submission -> comparison -> process_proposal / overlay / regenerate -> attribution
```

阶段标准验收当前通过：

```text
template_generate run dir
  -> template-generation-judge
  -> stage standard diff reports
  -> mismatches[] / root_causes[] / owner_assignments[] / fix_plan[]
```

## Expected vs observed

Expected：

```text
1. Module 1 的 ai_observation_bundle 能作为 AI 初版主入口进入代码生成桥接。
2. 观察产物只能先转成可校验 proposal/hint，再复用 comparison / reconciler，不直接写最终 artifact。
3. unknown、demotion、低置信、hash 不一致、证据缺失和 T4 无真实渲染必须进入人工待决。
4. 桥接后的 unit_map / element_spec / global_spec / template_spec 需要按阶段标准验收，并输出准确率。
5. 准确率不能替代差异诊断；报告仍必须保留 mismatches[]、root_causes[]、owner_assignments[]、fix_plan[]。
```

Observed：

```text
1. run_template_agent 只消费 layered submission replay/live，不消费 ai_observation_bundle。
2. observation_eval 只评 AI 原始观察 vs 标准，不能说明 AI+代码桥接后的最终阶段产物准确率。
3. template-generation-judge 已有阶段标准 diff 和四层诊断，但没有面向 agent bridge 的验收汇总。
4. CLI 缺少直接传入 observation bundle 的入口，端到端验收需要手工拼接。
```

## 疑似根因

```text
1. Plan 04 先落地 overlay-on-parse 的 executable proposal 通道，Module 1 观察产物当时还未稳定。
2. Module 1 观察评估和 Module 2 代码桥接属于两个独立产物面，还没有桥接 adapter。
3. 标准裁判优先补了 stage diff diagnosis，尚未把 agent attribution/bridge artifact 纳入验收摘要。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. Module 1 已能产 ai_observation_bundle、quality_report.demotions 和 replay 核心测试。
2. Module 2 已能对 layered submission 做 comparison/manual_review/process_proposal/attribution。
3. template-generation-judge 已能输出阶段标准 diff、root cause、owner 和 fix plan。
```

未解决：

```text
1. ai_observation_bundle 不能直接驱动代码生成桥接。
2. observation demotions / low confidence / hash mismatch 没有并入 template_agent_manual_review_items。
3. agent attribution 不能说明最终变化是否来自 observation bridge。
4. 缺少桥接后输出与阶段标准的准确率验收报告。
```

## 后续验收门禁

```text
1. CLI 能通过 --agent-observation-bundle 运行 template-generate，并输出 bridge/comparison/manual_review/attribution artifacts。
2. 低置信、unknown、demotion、hash mismatch 不自动进入 process_proposal。
3. T2/T3 可靠 observation 能转成 proposal，并继续经过 comparison/reconciler。
4. template-generation-judge 输出 template_agent_bridge_standard_acceptance，包含 bridged_output_accuracy 与四层诊断。
5. default-off 合同保持不变。
```
