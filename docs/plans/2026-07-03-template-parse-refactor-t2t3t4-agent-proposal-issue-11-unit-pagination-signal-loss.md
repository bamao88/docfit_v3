---
status: draft
owner: template-generation
stage: T2T4
topic: agent-proposal
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-11
issue_sequence: 11
severity:
  - P1
previous_issue:
  id: T2T3T4-AGENT-ISSUE-10
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-10-t4-observation-downstream-dead-end.md
  status: draft
previous_optimization:
  doc: docs/plans/2026-07-02-template-parse-refactor-module1-t4-observation-fix-plan-01.md
  summary: module1-t4-fix plan-01 已接通页面图与视觉分页观察，并可对 gold 打分（页隔离 0.6875, 11/16）；但该信号止步于评测，从未进入生成计划的分页动作。
next_plan: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-11-unit-pagination-alignment.md
created: 2026-07-03
last_updated: 2026-07-03
related_code:
  - src/docfit/template_generation/plan.py
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/agent/observation_bridge.py
  - src/docfit/template_generation/agent/observation_vision.py
  - src/docfit/template_generation/agent/observation_eval.py
  - src/docfit/template_generation/agent/schema.py
cross_issue:
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-10-t4-observation-downstream-dead-end.md
---

# T2/T3/T4 Agent Issue 11：单元分页只剩机械证据，AI 独占页信号在 bridge 前丢失

## 问题摘要

T2 阶段（含 AI 观察与 T4 vision）已经能识别「哪个单元应独占一页」，但 T6 执行的分页动作
只消费源 DOCX 的机械 `page_break_before` 证据。识别与执行没有左对齐：AI 识别对了也不影响
生成的 DOCX 分页。

## 真实运行口径

分页动作的唯一生产链路：

```text
structure_candidates.py:393 _mechanical_page_policy_for_unit
  只依据源文档 OOXML page_break_before / break 事实产出 units[].page
  （page_break / section_isolation / page_policy.generation_policy）
    -> generation_model.data.units[].page
    -> plan.py:33-90 依据 page_break_rule / generation_policy 产出
       insert_page_break_before_unit / insert_section_break_before_unit
    -> executor.py 落 DOCX
```

hunannongye 硬事实（module1-t4-fix plan-01 已核实）：

```text
320 段只有 1 个 Word 分节；page_break_before 全 false；fields=0。
=> 每单元分页语义在源事实里不存在，只在渲染后可见。
=> 机械链路对这类模板必然产出空/不完整的分页动作。
```

AI 侧已有但被丢弃的信号：

```text
1. T4 vision（observation_vision.py）逐页输出 is_standalone_page / unit_hint。
2. observation_eval.py:267 已对 gold 计算 page_isolation_accuracy，
   hunannongye 真实结果 0.6875（11/16 单元）——信号存在且大部分正确。
3. T2 AI unit observation 携带 page_start，但 _bridge_t2
   （observation_bridge.py:127-192）产出的 proposal 只有
   unit_candidate / boundary_adjustment，无任何分页字段。
4. schema.py:10,24 已定义 page_policy_hints collection 与
   page_policy_hint kind，但全仓库没有任何生产者——现成槽位空转。
```

## Expected vs observed

Expected：

```text
1. T2/T4 识别出的单元分页语义（独占页/可流动）应进入 merged unit_map 的
   units[].page，与机械证据调和。
2. plan.py 的分页动作应消费调和后的 page policy，动作可溯源
   （mechanical / ai_observation / both）。
3. 生成的 fillable_template.docx 的实际页隔离应与识别结果对齐，可实测。
4. AI 与机械证据冲突时显式上报，不静默丢弃任何一方。
```

Observed：

```text
1. plan.py 只读机械 page 规则；AI/vision 分页信号在 bridge 前即丢失。
2. page_policy_hint 槽位存在但零生产者；_bridge_t4 只产 section_profile_hint。
3. page_isolation_accuracy 只用于评测报告，不进入任何生成产物。
4. 对 hunannongye 这类「源文档无机械分页证据」的模板，生成计划中
   分页动作与 AI 已识别的独占页语义完全脱节。
```

## 疑似根因

```text
1. 分页链路是纯 deterministic 时代的遗留：page policy 生产只认 T1 机械事实，
   AI 路线加入后没有为分页语义设计回流通道。
2. bridge 的 T2 投影只覆盖单元边界（range/label），把 page_start /
   独占页观察当作非目标字段丢弃。
3. T4 vision 的 page_observations 只被 envelope/评测消费，没有到
   unit page policy 的映射（与 issue-10 的消费缺失同源，但目标产物不同：
   issue-10 是 global_spec 明点字段，本 issue 是 units[].page 与分页动作）。
4. schema 先行定义了 page_policy_hints，实现从未跟上。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. 视觉分页观察可产出：真实渲染 + 逐页 is_standalone_page（module1-t4-fix plan-01）。
2. 分页识别可评测：page_isolation_accuracy 对 gold 打分。
3. 机械分页链路本身工作正常：有 page_break_before 证据时动作正确产出。
```

未解决：

```text
1. AI 分页信号无回流通道，merged units[].page 恒等于机械结果。
2. page_policy_hint 槽位无生产者。
3. 生成 DOCX 的实际页隔离没有验收口径（评测只看观察，不看最终产物）。
```

## 后续验收门禁

```text
1. hunannongye 复跑：被 AI（且与 gold 一致）判定独占页的单元，生成计划中
   出现对应 insert_page_break_before_unit / insert_section_break_before_unit
   动作，reason 标明来源（mechanical / ai_observation / both）。
2. 已有机械分页证据的位置不得重复插入分页动作。
3. 对生成的 fillable_template.docx 渲染后实测页隔离，与 gold
   layout_policy 比对；准确率不得低于观察层基线（0.6875）。
4. AI 与机械证据冲突的单元出现在 open_questions / manual_review，
   数量与理由可审计。
```

本 issue 只记录问题，不写实施方案；方案见对应 plan。

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-03 | 初稿：确认分页动作只消费机械证据，AI 独占页信号（评测准确率 0.6875）在 bridge 前丢失，page_policy_hint 槽位零生产者 |
