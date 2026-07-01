---
status: implemented
owner: template-generation
stage: T2T3T4
topic: agent-observation-code-bridge-acceptance
doc_type: plan
plan_id: T2T3T4-AGENT-PLAN-06
source_issue:
  id: T2T3T4-AGENT-ISSUE-06
  doc: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-issue-06-observation-code-bridge-acceptance.md
previous_plan:
  id: T2T3T4-AGENT-PLAN-04
  doc: docs/plans/template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md
created: 2026-07-01
last_updated: 2026-07-01
---

# T2/T3/T4 Agent Plan 06：Observation Bundle 到代码生成桥接与标准验收

## Summary

本轮把 Module 1 的 `ai_observation_bundle` 接到现有代码生成桥接层：观察产物先转成现有 proposal/hint，再复用 comparison、schema/reconciler、overlay/regenerate、manual review 和 attribution。生成完成后通过 `template-generation-judge` 输出 `template_agent_bridge_standard_acceptance`，按阶段标准给出桥接后产物准确率，并保留四层差异诊断。

## Key Changes

```text
1. 新增 agent/observation_bridge.py：
   - 校验 observation bundle 与 render packet 的 source_render_hash。
   - T2 medium/high observation -> add_unit / adjust_unit_range proposal。
   - T3 medium/high observation -> set_candidate_policy proposal；instruction_remove 映射到 remove_instruction。
   - T4 observation -> advisory section_profile_hints；无真实 render 仍由 comparison 拦截。
   - unknown、low confidence、demotions、hash mismatch -> manual review seeds。

2. 扩展 agent 入口：
   - AgentConfig 增加 observation_bundle_path。
   - CLI 增加 --agent-observation-bundle。
   - observation bridge 生成 T2/T3/T4 三个 synthetic pass，确保 T3 在 post-T2 checkpoint 后执行。

3. 扩展 artifacts：
   - 输出 template_agent_observation_bridge。
   - manual_review 合并 bridge manual items。
   - attribution 增加 observation_bridge 摘要。

4. 扩展标准验收：
   - template-generation-judge 写出 template_agent_bridge_standard_acceptance.json/md。
   - 报告包含 bridged_output_accuracy.stages、aggregate_accuracy、bridge/attribution 摘要。
   - 报告复用现有 mismatches[]、root_causes[]、owner_assignments[]、fix_plan[]。
```

## Acceptance

```text
1. default-off 不输出 agent artifacts。
2. --agent-observation-bundle 不需要 layered transcript，也能跑出 bridge/comparison/manual_review/attribution。
3. 只有 medium/high 且有 evidence binding 的 T2/T3 observation 进入 comparison。
4. T3 policy 命名差异只允许 instruction_remove -> remove_instruction 这一条显式映射。
5. template-generation-judge 新增 bridge acceptance 报告；没有 bridge artifact 时 bridge_present=false，准确率不伪造。
```

## Test Plan

```text
uv run pytest tests/unit/template_generation_agent/test_agent_observation_bridge.py
uv run pytest tests/unit/test_template_generation_standard_diff_diagnosis.py
uv run pytest tests/contract/test_template_generate_agent_replay.py
uv run pytest tests/contract/test_template_generation_standard_judge.py
```
