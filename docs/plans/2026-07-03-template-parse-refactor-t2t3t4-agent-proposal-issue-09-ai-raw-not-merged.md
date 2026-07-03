---
status: draft
owner: template-generation
stage: T2T3T4
topic: agent-ai-raw-to-merged
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-09
issue_sequence: 09
previous_issue:
  id: T2T3T4-AGENT-ISSUE-07
  doc: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-issue-07-end-to-end-workflow-not-integrated.md
  status: partially_resolved
previous_optimization:
  doc: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-plan-07-end-to-end-workflow-integration.md
  summary: Plan 07 已打通同 run Module 1 replay 编排、ai_observation_bundle 落盘、03.1 AVAILABLE 和 hash 对齐；但真实 hunannongye run 显示 T2/T3/T4 AI raw 仍未成为 merged 权威产物。
next_plan: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-09-ai-raw-to-merged.md
created: 2026-07-03
last_updated: 2026-07-03
evidence_run:
  - /private/tmp/docfit_real_school_template_observation_replay_user_check
related_code:
  - src/docfit/template_generation/agent/observation_bridge.py
  - src/docfit/template_generation/agent/schema.py
  - src/docfit/template_generation/agent/comparison.py
  - src/docfit/template_generation/agent/reconciler.py
  - src/docfit/template_generation/agent/overlay.py
  - src/docfit/template_generation/runner.py
---

# T2/T3/T4 Agent Issue 09：AI raw 已生成但未进入 merged 权威产物

## 真实运行口径

本 issue 基于真实学校模板 replay run：

```text
uv run docfit eval template-generate \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --out /private/tmp/docfit_real_school_template_observation_replay_user_check \
  --agent-observation-replay /private/tmp/hunannongye_observation_replay_user_check.json
```

运行结果：

```text
T1 document_facts: body_flow=320, runs=493
T2 code_raw: 16 units, AVAILABLE
T2 ai_raw:   16 items, AVAILABLE
T2 merged:   16 units, AVAILABLE
T3 code_raw: 366 elements, AVAILABLE
T3 ai_raw:   178 items, AVAILABLE
T3 merged:   366 elements, AVAILABLE
T4 code_raw: 1 section profile, AVAILABLE
T4 ai_raw:   1 item, AVAILABLE
T4 merged:   1 section profile, AVAILABLE
T5 template_spec: 16 units
T6 build_manifest: 341 actions, 245 slots
```

AI observation bundle 与 render packet hash 已对齐：

```text
source_render_hash = sha256:2290b9e787d5340fe80b67e8ec17cfd54be9bb9c971744474843cbde2fc65510
OBSERVATION-HASH-MISMATCH = 0
```

## Expected vs observed

Expected：

```text
1. 若 T2/T3/T4 ai_raw 为 AVAILABLE，bridge 应把可执行、证据绑定、低风险的 AI 结果转成 proposal。
2. comparison/reconciler 应把 compatible/missing 且 low-risk 的 proposal 应用到 merged 权威产物。
3. T2 merged 应能体现 AI unit range/label 的接受结果，或明确记录不可合并原因。
4. T3 merged 应能体现 AI element policy 的接受结果，或明确记录不可合并原因。
5. T4 merged 应能体现 AI layout observation 的接受结果；不能只作为 advisory hint 停留在 side artifact。
6. 只有 T2/T3/T4 均存在 AI raw -> bridge -> accepted/merged 的证据时，才能声称 AI/code 全链路打通。
```

Observed：

```text
1. T2 ai_raw 已生成 16 items，但 16 个 T2 proposal 在 schema 阶段被拒：
   - reason = kind must be unit_candidate
   - 根因表现：bridge 把 existing unit 的 boundary_adjustment 放进 unit_candidates collection。

2. T3 ai_raw 已生成 178 items，但没有形成可执行 T3 proposal：
   - observation_bridge.summary.t3_proposals = 0
   - manual_review_required = 178
   - reason 分布：OBSERVATION-LOW-CONFIDENCE=137，OBSERVATION-POLICY-NOT-EXECUTABLE=41
   - T3 merged element count 仍为 366，round0/post_agent element_spec hash 相同。

3. T4 ai_raw 已生成 1 item，bridge 接受 1 个 section_profile_hint：
   - accepted_proposal_ids = ["obs_t4_001"]
   - 但 reconciler 只写 agent_t4_hints，reason = hint accepted as advisory artifact
   - round0/post_agent global_spec 没有变化，T4 merged 仍等于 code route。

4. agent_attribution 显示：
   - overlays.t2 = []
   - overlays.t3 = []
   - t4_hint_counts.section_profile_hints = 1
   - round0_hashes.unit_map == post_agent_hashes.unit_map
   - round0_hashes.element_spec == post_agent_hashes.element_spec
```

## 疑似根因

```text
1. Bridge 层只解决了「同 run 可观察、可对账」，没有完成「观察结果到当前 schema collection」的正确投影：
   existing unit 的 T2 调整进入了错误 collection，导致 schema 层全部拒绝。

2. T3 bridge 过于保守且 policy 命名未完全对齐：
   instruction_remove 被映射为 remove_instruction，但部分 observation policy 仍被判定不可执行；
   低置信观察全部进 manual review，缺少按证据绑定/当前 deterministic target 做可执行升级的路径。

3. T4 reconciler 的设计仍停在 advisory-only：
   即使 AI layout observation AVAILABLE 且被接受，也不会 patch global_spec，因此 T4 merged 不可能体现 AI。

4. 当前验收把「artifact 存在 / availability=AVAILABLE / judge PASS」误当成链路完成；
   没有硬性检查 merged hash 是否变化、accepted proposal 是否影响权威产物、或不可合并原因是否逐层可解释。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. Module 1 replay 可在同一次 template-generate run 内执行。
2. ai_observation_bundle 持久化到 run artifacts。
3. T2/T3/T4 ai_raw route 均可 AVAILABLE。
4. bundle.source_render_hash 与 template_agent_render_packet.source_render_hash 已对齐。
5. NOT_AVAILABLE 占位语义已从「AI 弃权」改为「未运行」。
```

未解决：

```text
1. T2 ai_raw 未进入 merged，且因 schema collection/kind 错误被拒。
2. T3 ai_raw 未进入 merged，绝大多数观察停留在 blocking manual review。
3. T4 ai_raw 未进入 merged，只形成 advisory hint。
4. 缺少合同测试证明 T2/T3/T4 accepted proposal 会改变或确认 merged 权威产物。
5. 缺少真实学校模板验收门禁：AI raw AVAILABLE 但 merged 未受影响时必须判定为未打通。
```

## 后续验收门禁

```text
1. hunannongye replay run 中 T2/T3/T4 均有 AI raw AVAILABLE。
2. bridge summary 中 T2/T3/T4 至少各有一个 executable proposal 或明确每个不可合并原因。
3. decisions 中 T2/T3/T4 均有 accepted proposal，且 target_path 指向对应权威产物或可审计的 merged overlay。
4. post_agent_hashes 至少能证明被接受的 T2/T3/T4 proposal 已进入 merged 计算；不能只写 side artifact。
5. 03.2 / 04.2 与 03.0 / 04.0 的关系必须可解释：changed_from_code=true 或 explicit_noop_with_reason。
6. 若某层 AI 结果只能 manual review，不得声称该层链路打通。
```

本 issue 只记录问题，不写实施方案；方案见对应 plan。
