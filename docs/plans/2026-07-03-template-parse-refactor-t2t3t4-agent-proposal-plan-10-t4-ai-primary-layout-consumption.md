---
status: draft
owner: template-generation
stage: T4
topic: agent-proposal
doc_type: plan
plan_id: T2T3T4-AGENT-PLAN-10
source_issue:
  id: T2T3T4-AGENT-ISSUE-10
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-10-t4-observation-downstream-dead-end.md
previous_plan:
  id: T2T3T4-AGENT-PLAN-09
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-09-ai-raw-to-merged.md
related_direction:
  doc: docs/plans/2026-07-03-template-parse-refactor-ai-primary-staged-migration-proposal.md
created: 2026-07-03
last_updated: 2026-07-03
---

# T2/T3/T4 Agent Plan 10：T4 明点转 AI 为主 —— 输入补齐 + merged 一等字段 + 下游消费

## Summary

解决 Issue 10：T4 accepted observation 目前只落 `agent_observation_hints` 死端。本 plan 让 T4
按迁移提案转「AI 为主、deterministic 校验兜底」：补齐 AI 输入的明点事实，把被接受的观察升为
merged global_spec 一等字段，并让 T5/T6 真正消费。

验收口径：

```text
T4 打通 = AI 观察（含 vision）可改变或显式确认 merged global_spec 的明点字段，
且该字段被 T5 template_spec / T6 执行消费；与 deterministic 分歧时产生
conflict/manual_review，不静默覆盖。
```

## Implementation Plan

### Phase 1：补齐 T4 明点输入（闭合 issue-08 的 T4 切片）

```text
src/docfit/template_generation/agent/packet.py
src/docfit/template_generation/agent/evidence.py
src/docfit/template_generation/agent/observation_vision.py

现状：
  global_layout_facts 只有 sections（margins/size/numbering/references 元数据）、
  header_footer（kind/part_name/has_content）、numbering_definition_count；
  vision PAGE_PROMPT 只有页面图，无任何版式事实上下文。

改动：
  - _global_layout_facts 扩展：header/footer 内容文本（含空文本显式标记）、
    data.fields[]（PAGE/TOC 等字段事实）、data.breaks[]（分页/分节 break）、
    section 的 per-source_seq 绑定；全部走 assert_firewall_clean 白名单。
  - build_t4_evidence 承载上述新增字段。
  - vision prompt 注入该页对应的版式事实摘要（该页所属 section 的页码声明、
    页眉页脚 part 是否有内容），让模型做「对照事实的确认/纠错」而不是裸猜。
```

完成信号：

```text
t4_evidence 含 header/footer 内容、fields、breaks；防火墙测试通过；
issue-08 验收门禁第 4 条（T4 evidence 承载 sections/header_footer/fields/
numbering/breaks/page images/page_layout_index）在 T4 侧闭合。
```

### Phase 2：accepted 观察升为 merged 一等字段（AI 为主 + 校验）

```text
src/docfit/template_generation/agent/observation_bridge.py
src/docfit/template_generation/agent/reconciler.py
src/docfit/template_generation/runner.py

改动：
  - 定义 vision/text 观察到明点字段的投影：page_number_text/visible ->
    page_numbering；has_header/has_footer -> header_footer 引用确认；
    section 边界观察 -> section_profiles。
  - accepted proposal 直接 patch merged global_spec 对应字段，
    携带 origin=ai_observation 与 evidence_refs 溯源。
  - 每个字段与 deterministic build_global_spec 结果比对：
    一致 -> confirmed；分歧 -> conflict 上报 manual_review，
    该字段回退 deterministic 值（迁移提案回退语义）。
  - AI NOT_AVAILABLE/abstain 时整体回退 deterministic（现状不变）。
```

完成信号：

```text
04.2_t4_merged_global_spec.yaml 的明点字段可含 origin=ai_observation；
post_agent hash 与 round0 的差异可解释（changed_from_code=true 或
explicit_noop_with_reason）；分歧样本出现在 manual_review。
```

### Phase 3：T5/T6 消费 + 移除死端

```text
src/docfit/template_generation/artifacts.py (build_template_spec)
src/docfit/template_generation/runner.py

改动：
  - build_template_spec 的 global 部分消费 merged 一等字段（含 AI origin），
    不再只直通 code 字段。
  - agent_observation_hints 侧信道废弃：字段移除，或降级为纯 debug trace
    并在注释中声明无下游消费者。
```

完成信号：

```text
rg "agent_observation_hints" src/ 无「只写不读」；
05_template_spec.yaml 全局输出可回溯到 AI origin 字段。
```

### Phase 4：门禁与评测

```text
1. 单测：明点字段投影、conflict 回退、NOT_AVAILABLE 兜底。
2. hunannongye 真实复跑：至少一个 accepted T4 observation 改变或显式确认
   05_template_spec.yaml 全局输出（issue-10 门禁 1）。
3. 三路线评测：T4 明点字段级 diff（code_raw vs ai_raw vs merged）三校跑通；
   ai_raw ≥ code_raw 后才允许 per-stage flag 默认开启（迁移提案晋升门禁）。
```

## Out of Scope

```text
1. 单元分页动作（insert_page_break/section_break）—— 归 plan-11。
2. T2 翻转、T3 span 模型 —— 归迁移提案与 t3 plan-06。
3. 三路线统一评测器本体实现 —— 归 standard-judge route-eval plan-03。
4. observe_live 默认接真实渲染 —— 归 issue-08 剩余切片。
```

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-03 | 初稿：四阶段落地 T4 明点 AI 为主——输入补齐、merged 一等字段、T5/T6 消费、三路线门禁 |
