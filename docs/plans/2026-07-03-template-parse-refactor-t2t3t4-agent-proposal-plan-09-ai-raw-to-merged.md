---
status: draft
owner: template-generation
stage: T2T3T4
topic: agent-ai-raw-to-merged
doc_type: plan
plan_id: T2T3T4-AGENT-PLAN-09
source_issue:
  id: T2T3T4-AGENT-ISSUE-09
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-09-ai-raw-not-merged.md
previous_plan:
  id: T2T3T4-AGENT-PLAN-07
  doc: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-plan-07-end-to-end-workflow-integration.md
created: 2026-07-03
last_updated: 2026-07-03
---

# T2/T3/T4 Agent Plan 09：让 AI raw 进入 merged 权威产物

## Summary

本轮只解决 Issue 09：AI raw 已经在同 run 生成，但 T2/T3/T4 没有真正进入 merged。

验收口径改为：

```text
AI/code 全链路通 = T2/T3/T4 都能从 ai_raw 生成 executable proposal，
经过 comparison/reconciler，被 accepted，并进入 merged 权威产物或明确记录 explicit_noop_with_reason。
```

## Implementation Plan

### Phase 1：修 T2 bridge collection/kind

```text
src/docfit/template_generation/agent/observation_bridge.py

现状：
  existing unit 的 boundary_adjustment proposal 被放进 proposals["t2"]，
  _submissions_from_proposals 固定写入 unit_candidates，
  schema 期望 kind=unit_candidate，因此全部 rejected。

改动：
  - proposals["t2"] 从 list 改为 per-collection dict：
      unit_candidates
      boundary_adjustments
      block_candidates
  - existing unit range 变化写入 boundary_adjustments，kind=boundary_adjustment。
  - new unit 写入 unit_candidates，kind=unit_candidate。
  - exact match 继续 noop，但要进入 proposal_map。
```

完成信号：

```text
T2 schema_error 数量为 0；若 AI range 可执行，decisions 有 accepted T2 proposal。
```

### Phase 2：让 T3 可执行 observation 进入 overlay

```text
src/docfit/template_generation/agent/observation_bridge.py
src/docfit/template_generation/agent/overlay.py

改动：
  - 修 policy 映射：instruction_remove -> remove_instruction。
  - 修 policy 映射：template_default -> fixed。
  - 对有 source_seq_refs 且 policy 可执行的 observation 生成 element_policy_candidate。
  - T3 low confidence 不再在 bridge 阶段硬阻断，但保留 observation_confidence；
    是否进入 merged 由 deterministic target binding、comparison 和 reconciler 决定。
  - target_candidate_id 优先用 source_seq_refs 绑定，避免 AI element_id 与 deterministic element_id 不同导致 target missing。
```

完成信号：

```text
T3 proposals > 0；至少有 accepted T3 proposal；agent_t3_overlay 非空；
post_agent_hashes.element_spec != round0_hashes.element_spec 或 explicit_noop_with_reason 可审计。
```

### Phase 3：让 T4 observation 影响 merged global_spec

```text
src/docfit/template_generation/agent/reconciler.py
src/docfit/template_generation/agent/loop.py
src/docfit/template_generation/runner.py

改动：
  - 接受 section_profile_hint 后，不只写 agent_t4_hints。
  - 新增 T4 overlay artifact，记录 accepted section_profile_hint。
  - 将 accepted T4 layout payload 合并到最终 global_spec 的 agent_observation_hints / section profile evidence。
  - T4 merged route hash 与 code route 的关系可审计。
```

完成信号：

```text
T4 decisions 有 accepted proposal，target_path 指向 global_spec 或 t4 overlay；
04.2_t4_merged_global_spec.yaml 包含 agent observation merge evidence。
```

### Phase 4：验收门禁

```text
1. 单测覆盖 T2 bridge collection/kind。
2. 单测覆盖 T3 executable policy proposal accepted。
3. 单测覆盖 T4 accepted hint 进入 merged global_spec evidence。
4. 真实 hunannongye replay run 输出：
   - T2/T3/T4 ai_raw AVAILABLE
   - T2/T3/T4 decisions 至少各有 accepted 或 explicit_noop_with_reason
   - merged route 可解释 changed/noop
```

## Out of Scope

```text
1. 不放宽 T2/T4 的 confidence 门禁；T3 的 low confidence 只取消 bridge 硬阻断。
2. 不改变 default-off。
3. 不解决 L1 输入契约和图片/PDF 事实边界，继续归 Issue 08。
4. 不做完整 T1-T6 route evaluator，继续归 Standard Judge Plan 03。
```
