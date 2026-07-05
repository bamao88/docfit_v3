---
status: draft
owner: template-generation
stage: T2T4
topic: agent-proposal
doc_type: plan
plan_id: T2T3T4-AGENT-PLAN-11
source_issue:
  id: T2T3T4-AGENT-ISSUE-11
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-11-unit-pagination-signal-loss.md
previous_plan:
  id: T2T3T4-AGENT-PLAN-10
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-10-t4-ai-primary-layout-consumption.md
related_direction:
  doc: docs/plans/2026-07-03-template-parse-refactor-ai-primary-staged-migration-proposal.md
created: 2026-07-03
last_updated: 2026-07-03
---

# T2/T3/T4 Agent Plan 11：单元分页对齐 —— AI 独占页信号回流到分页动作

## Summary

解决 Issue 11：让 T2/T4 已识别的单元分页语义（独占页/可流动）回流到 merged
`units[].page`，并由 `plan.py` 消费产出可溯源的分页动作。机械证据保留为校验方，
不删除现有链路。

验收口径：

```text
分页对齐 = AI（与 gold 一致）判定独占页的单元在生成计划中获得分页动作，
动作 reason 可溯源；生成 DOCX 渲染后实测页隔离 ≥ 观察层基线；
AI 与机械证据冲突显式上报。
```

## Implementation Plan

### Phase 1：bridge 生产 page_policy_hint（填上空转槽位）

```text
src/docfit/template_generation/agent/observation_bridge.py

现状：
  schema.py 已定义 page_policy_hints collection / page_policy_hint kind，
  但没有任何生产者。

改动：
  - 新增 _bridge_page_policy：从 observation envelope 的 page_observations
    （is_standalone_page + unit_hint）经 page_layout_index / source_bindings
    把页级观察映射到单元级 {unit_id, standalone: bool, page_nos,
    evidence_refs}，产出 kind=page_policy_hint proposal。
  - 同时消费 T2 ai_unit_observation 的 page_start 字段作为佐证。
  - 页无法绑定到唯一单元（跨单元页/绑定失败）时不产 proposal，
    记入 open_questions，保留证据。
```

完成信号：

```text
hunannongye replay：bridge summary 中 page_policy_hint proposal > 0；
每个 proposal 带 page_nos + evidence_refs 可回查页面图。
```

### Phase 2：merged units[].page 调和（AI + 机械）

```text
src/docfit/template_generation/agent/reconciler.py
src/docfit/template_generation/agent/overlay.py

改动：
  - accepted page_policy_hint patch 到 merged unit_map 的 units[].page：
    机械已判分页 + AI 同意 -> 不变，origin=both；
    机械无证据 + AI 判独占 -> page_break=是，origin=ai_observation；
    机械判分页 + AI 判可流动 -> 保留机械结果，冲突记 manual_review；
  - generation_model 基于 patched candidates 重建（沿用现有 regenerate 链路），
    保证 plan.py 读到调和后的 page。
```

完成信号：

```text
02.2_t2_merged_unit_map.yaml 中出现 origin=ai_observation 的 page 规则；
冲突单元出现在 manual_review，数量与理由可审计。
```

### Phase 3：plan.py 消费与动作溯源

```text
src/docfit/template_generation/plan.py

改动：
  - 分页动作 reason 携带 page policy 来源（mechanical / ai_observation / both）。
  - 保持既有去重语义（page_boundary_refs / section_boundary_refs），
    确保已有机械分页处不重复插入。
```

完成信号：

```text
生成计划中 AI 来源的分页动作可与机械来源区分；无重复动作。
```

### Phase 4：门禁与评测

```text
1. 单测：hint 生产映射、三种调和分支、动作去重与溯源。
2. hunannongye 真实复跑：issue-11 门禁 1/2 达成；
   渲染生成 DOCX 后用 observation_eval 同口径实测页隔离，
   对 gold layout_policy 准确率 ≥ 0.6875（观察层基线）。
3. 三路线评测：分页动作集在 code_raw / ai_raw / merged 三路线间 diff 可解释。
```

## Out of Scope

```text
1. T2 单元边界识别本身（保持 merge，见迁移提案）。
2. global_spec 明点字段（页码/页眉页脚）—— 归 plan-10。
3. 提升 vision 观察准确率本身（prompt/模型迭代）；本 plan 只打通回流，
   准确率提升依赖 plan-10 Phase 1 的事实注入与后续评测迭代。
```

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-03 | 初稿：四阶段打通 AI 独占页信号回流——hint 生产、merged 调和、plan 消费溯源、实测门禁 |
