---
status: draft
owner: template-generation
stage: T4
topic: agent-proposal
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-10
issue_sequence: 10
severity:
  - P1
previous_issue:
  id: T2T3T4-AGENT-ISSUE-09
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-09-ai-raw-not-merged.md
  status: draft
previous_optimization:
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-09-ai-raw-to-merged.md
  summary: Plan 09 Phase 3 计划让 accepted T4 observation 进入 merged global_spec 的 evidence；但其完成信号仍停在 agent_observation_hints 可审计层面，没有任何下游消费者读取该字段。
next_plan: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-10-t4-ai-primary-layout-consumption.md
created: 2026-07-03
last_updated: 2026-07-03
related_code:
  - src/docfit/template_generation/runner.py
  - src/docfit/template_generation/plan.py
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/agent/reconciler.py
  - src/docfit/template_generation/agent/observation_vision.py
  - src/docfit/template_generation/agent/observation_bridge.py
cross_issue:
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-08-t1-l1-input-contract.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-11-unit-pagination-signal-loss.md
---

# T2/T3/T4 Agent Issue 10：T4 accepted observation 无下游消费者（agent_observation_hints 死端）

## 与相邻 issue 的边界

```text
issue-08：输入侧 —— T4 AI 拿不到完整版式事实（本 issue 不重复）。
issue-09 / plan-09 Phase 3：merge 侧 —— accepted T4 observation 进入 merged 的
  可审计证据（agent_observation_hints + merge_trace）。
本 issue：消费侧 —— 即使 merge 证据齐了，merged global_spec 里的 AI 观察
  也没有任何下游读取者，明点（分节/页眉页脚/页码）输出不可能被 AI 改变或确认。
```

## 真实运行口径

明点 = 分节结构、每节页眉页脚、页码逻辑（用户 2026-07-03 定义）。

deterministic 路线已完整：`artifacts.py build_global_spec(document_facts)` 从 T1 事实产出
`section_profiles / default_font / page_numbering / header_footer / numbering_rules`。

AI/vision 路线的产出链路：

```text
observation_vision.py MinimaxVisionResponder.observe_pages
  每页 PNG -> {is_standalone_page, unit_hint, has_header, has_footer,
               page_number_visible, page_number_text, visual_notes}
  -> scripts/observe_live.py（164-202 行）写入 observation envelope 的 page_observations
  -> observation_bridge._bridge_t4：只产出 kind=section_profile_hint 的 proposal
  -> reconciler 接受后只写 agent_t4_hints side artifact
  -> runner.py _merge_t4_agent_hints（452-489 行）：
       将 hints 深拷贝进 global_spec["agent_observation_hints"] 并追加 merge_trace
```

消费侧检查（2026-07-03，src/ 全量 grep）：

```text
rg -n "agent_observation_hints" src/ scripts/ tests/
  -> src/ 内唯一写入点 runner.py:473，零生产代码读取点；
     仅 tests/contract/test_template_generate_agent_replay.py 断言字段存在
     （验证「写入了」，不验证「被消费」）。
plan.py：只读 generation_model.data.units[].page，从不读 global_spec。
build_template_spec（artifacts.py）：global 部分直通 code 字段，不读 hints。
executor.py / manifest.py / verifier.py：均不读 hints。
```

## Expected vs observed

Expected：

```text
1. 被接受的 T4 observation 应能改变或显式确认 merged global_spec 中的明点字段
   （section_profiles / header_footer / page_numbering），并被 T5 template_spec
   与 T6 执行消费。
2. AI 与 deterministic 明点字段分歧时，应产生 conflict / manual_review，
   而不是 AI 结果静默进入无人读取的侧字段。
3. vision 每页观察（页眉页脚可见性、页码文本、独占页）应有明确的下游归宿：
   要么进入明点字段，要么进入单元分页策略（issue-11），要么显式记录不可用原因。
```

Observed：

```text
1. runner.py:452-489 把 accepted hints 写入 global_spec["agent_observation_hints"]，
   生产代码无任何读取者（仅 contract test 断言字段存在）；
   T4 merged 的明点字段永远等于 code 直通。
2. hunannongye replay（issue-09 证据）：T4 ai_raw AVAILABLE、bridge 接受
   1 个 section_profile_hint，但 round0/post_agent global_spec hash 不变。
3. vision 的 has_header / has_footer / page_number_text 观察在 bridge 层
   没有对应的明点字段投影；即使识别正确也无法参与 merged。
4. 因此「T4 明点识别不准」在最终产物上不可观测：不管 AI 报什么，
   05_template_spec.yaml 的全局输出都一样。
```

## 疑似根因

```text
1. T4 merge 设计停留在 advisory-only（issue-09 根因 3 的延续）：
   plan-09 Phase 3 只把 hints 变得可审计，没有定义「谁消费」。
2. global_spec 缺少 AI 观察到明点字段的投影契约：
   vision 输出（page_number_text/has_header 等）与 global_spec 字段
   （page_numbering/header_footer）之间没有映射与冲突裁决规则。
3. 验收口径长期以「artifact 存在 + accepted_count > 0」为完成信号，
   没有硬性要求「下游行为可变化或显式 noop」。
```

## 上一轮已解决 / 未解决对照

已解决（截至 plan-09 / module1-t4-fix plan-01）：

```text
1. T4 evidence 已含 global_layout_facts（packet.py:97、evidence.py:154）。
2. 无图时 Track A 确定性产出全局 section_profile，不再整体 abstain。
3. accepted T4 hint 可落 agent_t4_hints 并进入 global_spec 的
   agent_observation_hints + merge_trace（可审计）。
4. observation_eval 已能对 gold 打分（页隔离 0.6875、全局版式字段对比）。
```

未解决：

```text
1. agent_observation_hints 无消费者，T4 AI 观察对最终产物零影响。
2. vision 页级观察缺少到明点字段的投影与冲突裁决契约。
3. 无合同测试证明 accepted T4 observation 会改变或显式确认 T5/T6 消费的输出。
```

## 后续验收门禁

```text
1. hunannongye 复跑中，至少一个被接受的 T4 observation 可见地改变或显式确认
   05_template_spec.yaml 的全局明点输出（changed_from_code=true 或
   explicit_noop_with_reason）。
2. rg "agent_observation_hints" src/ 不再出现「只写不读」：该字段被消费或被移除。
3. AI 与 deterministic 明点字段分歧时，产生 conflict / manual_review 记录，
   可在 route eval 四层诊断（mismatch/root_cause/owner/fix_plan）中回查。
4. 三路线评测中 T4 merged 与 code_raw 的关系逐字段可解释。
```

本 issue 只记录问题，不写实施方案；方案见对应 plan。

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-03 | 初稿：确认 agent_observation_hints 生产代码零读取者（仅 contract test 断言存在），T4 AI 观察（含 vision 明点识别）对最终产物零影响 |
