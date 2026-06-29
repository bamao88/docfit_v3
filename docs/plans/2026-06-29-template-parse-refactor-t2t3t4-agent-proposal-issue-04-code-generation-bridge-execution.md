---
status: implemented
owner: template-generation
stage: T2T3T4
topic: agent-layered-submission-code-bridge
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-04
issue_sequence: 04
previous_issue:
  id: T2T3T4-AGENT-ISSUE-03
  doc: docs/plans/template-parse-refactor-t2t3t4-agent-proposal-issue-03-ai-quality-context-architecture.md
  status: superseded_deleted_by_plan_04
previous_optimization:
  doc: docs/plans/template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md
  summary: 合并版 plan-04 明确 Module 2 主线：AI 输出先与 deterministic round-0 comparison，再把 compatible+validated+低风险项交给现有 schema/reconciler；冲突、不确定、高风险和校验失败统一进入 manual review。
next_plan: docs/plans/template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md
created: 2026-06-29
last_updated: 2026-06-29
---

# T2/T3/T4 Agent Issue 04：代码生成桥接执行前残余问题

## 真实运行口径

本轮按 `template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md` 执行 Module 2，不展开 Module 1 的独立观察流水线。

当前可运行路径是：

```text
deterministic round-0
  -> optional agent replay/live layered_submission
  -> validate_layered_submission
  -> process_proposal / overlay / regenerate
  -> verifier / output artifacts
```

本轮目标运行路径是：

```text
deterministic round-0 + AI layered_submission / observation
  -> template_agent_submission_comparison
  -> template_agent_manual_review_items
  -> compatible + validated + low-risk proposals only
  -> existing process_proposal / overlay / regenerate
  -> agent_attribution
```

## Expected vs observed

Expected：

```text
1. AI 与 deterministic 当前结果先 comparison，产出 compatible/conflict/missing/unknown/manual_review_required。
2. 冲突、不确定、缺 ref、校验失败、高风险变更必须进入 template_agent_manual_review_items。
3. 只有 compatible + schema validated + 低风险 proposal/hint 才能进入 process_proposal。
4. default-off 不产生 agent artifacts，不改变 deterministic 输出。
5. attribution 能指向 accepted proposal、manual review 和 deterministic fallback 的来源。
```

Observed：

```text
1. 现有 agent 落地层已有 schema、reconciler、overlay、regenerate、attribution，但缺 comparison artifact。
2. open_questions / validation failures / conflicts 没有统一 manual review artifact。
3. 当前流程主要按 proposal 校验结果 accepted/rejected，缺少“先对账、再执行”的显式桥接层。
4. 输出模型和 runner artifacts 尚未包含 template_agent_submission_comparison / template_agent_manual_review_items。
```

## 疑似根因

```text
1. 早期实现先验证 overlay-on-parse 可行性，优先打通 schema/reconciler/overlay/regenerate。
2. staged pass 后增加了 open_questions 和 unit window 约束，但人工待决项仍散落在 decisions reason 中。
3. Module 1 独立观察产物尚未落地，Module 2 的 comparison 需要先支持 layered_submission 路线，再兼容 observation 路线。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. layered_submission schema 与 replay transcript 已有基础合同。
2. T2 add_unit / adjust_unit_range、T3 policy overlay、T4 hints 已能通过现有 reconciler 跑通。
3. default-off 合同已有测试保护。
4. staged replay 已能输出 pass_plan、post_t2_checkpoint、post_t2_input、unit_windows。
```

未解决：

```text
1. 缺 template_agent_submission_comparison。
2. 缺 template_agent_manual_review_items。
3. 冲突、高风险和缺证据的拒绝理由没有形成面向人工的稳定问题 id 与影响范围。
4. 兼容 Module 1 ai_unit/element/layout_observation 的 comparison 输入口还没有代码入口。
```

## 后续验收门禁

```text
1. comparison 单测覆盖 compatible、conflict、missing、unknown/manual_review_required。
2. manual_review 单测覆盖 open_questions、comparison conflicts、validation failures、risk rejections。
3. replay 合同测试能看到 comparison/manual_review artifacts。
4. default-off 合同测试继续证明不输出 agent artifacts。
5. 相关测试命令通过：
   uv run pytest tests/unit/template_generation_agent
   uv run pytest tests/contract/test_template_generate_agent_default_off.py
   uv run pytest tests/contract/test_template_generate_agent_replay.py
   uv run pytest tests/contract/test_template_generate_agent_staged_replay.py
```

## 本轮落地结果

```text
1. 新增 template_agent_submission_comparison artifact，记录每个 proposal 的 compatible/conflict/missing/unknown、manual_review_required 和 can_auto_execute。
2. run_template_agent 改为 comparison gate：blocking open_questions、冲突、缺证据、非法 enum、T4 非 real_render、高风险项不进入 process_proposal。
3. 新增 template_agent_manual_review_items artifact，统一汇总 open_questions、comparison manual items 和 validation/reconciler failures。
4. attribution 增加 comparison_summary 与 manual_review 待决 id。
5. outputs / runner / ordered debug snapshot 均写出 comparison 与 manual_review artifacts；default-off 仍不输出 agent artifacts。
```

## 本轮验收结果

```text
uv run pytest tests/unit/template_generation_agent tests/contract/test_template_generate_agent_default_off.py tests/contract/test_template_generate_agent_replay.py tests/contract/test_template_generate_agent_staged_replay.py
=> 53 passed
```
