---
status: draft
owner: template-generation
stage: T2T5T6T7
topic: unit-pagination-consumption
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
  doc: docs/plans/template-parse-refactor-t2-visual-pagination.md
  summary: 旧视觉分页草案已落机械 page policy 和 page/section break 执行原语，但未形成当前 T2→T5→T6 权威消费链；由 Plan 11 接管剩余目标。
next_plan: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-11-unit-pagination-alignment.md
created: 2026-07-03
last_updated: 2026-07-16
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/agent/observation_materialize.py
  - src/docfit/template_generation/agent/observation_bridge.py
  - src/docfit/template_generation/agent/schema.py
  - src/docfit/template_generation/agent/reconciler.py
  - src/docfit/template_generation/agent/overlay.py
  - src/docfit/template_generation/plan.py
  - src/docfit/template_generation/executor.py
  - src/docfit/template_generation/verifier.py
  - src/docfit/template_generation/t2_standard.py
  - src/docfit/harness/template_generation_stage_verifiers.py
  - src/docfit/harness/template_generation_judge_reports.py
cross_issue:
  - docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-issue-01-remaining-end-to-end-gaps.md
---

# T2/T5/T6 Issue 11：单元分页策略没有形成权威消费闭环

## 问题摘要

阶段契约和三校 T2 标准已经把单元分页归属定义为 T2 责任，并为每个单元给出
`page_break`、`page_isolation`、`allow_multi_page`、`keep_together`。当前运行链路却没有
把这组语义稳定物化为 T2 权威输出，更没有让 T5/T6、verifier 和 judge 以同一契约消费。

这不是单一字段遗漏，而是三个相互叠加的问题：

1. **T2 产出不完整**：真实输出中的 `units[].page` 可以全部为空，`page_start` 仍由默认值补齐。
2. **下游双轨**：T5 从 `unit_map` 复制单元；T6 的生成计划却绕过 T5，直接读取
   `generation_model.data.units[].page`。
3. **门禁失真**：T2 standard 包含分页期望，但当前 T2 standard verifier 只比较单元、顺序和
   anchor ownership；空分页仍可得到 `PASS` / `SIGNABLE`。

## 当前事实链

```text
T2 code_raw
  structure_candidates._mechanical_page_policy_for_unit
  -> 仅在源 OOXML 存在 pageBreakBefore / w:br / sectPr 时写 units[].page
  -> build_unit_map 原样复制 page
  -> _page_start_for_unit 对空 page 自动写 preserve_source_flow

T2 ai_raw / merged
  T2 prompt contract 只要求 unit_id/source_seq_refs/confidence
  -> materializer 虽会透传额外 page_start，但 prompt、schema 和 bridge 不把分页作为正式契约
  -> _bridge_t2 在单元范围相同时直接 noop，分页差异不会单独形成 proposal
  -> 当前 T2 proposal schema 没有 page policy collection/kind

T5
  `build_template_spec` 通过 `**unit` 原样复制 `units[].page/page_start`
  -> 不检查分页语义完整性、来源、冲突或可执行性

T6
  build_template_generation_plan(generation_model=...)
  -> 分页循环读取 generation_model.data.units[].page，而不是 T5 template_spec
  -> 只支持“单元前插 page/section break”
  -> 不消费 page_isolation / allow_multi_page / keep_together
  -> executor/manifest 的分页摘要不保留 page policy 来源和 proposal trace

T7 / judge
  runtime verifier 只检查 page_start 是否非空
  -> preserve_source_flow 默认值足以避开 page finding
  T2 standard verifier 不比较 expected.units[].page
  -> 空 page 仍可能 PASS / SIGNABLE
```

## 2026-07-16 真实复现

命令：

```bash
uv run docfit eval template-generate \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --out /tmp/docfit-t2-pagination-audit-20260716

uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run /tmp/docfit-t2-pagination-audit-20260716 \
  --out /tmp/docfit-t2-pagination-judge-20260716 \
  --no-derive-template-gap
```

Observed：

```text
02_unit_map.yaml:
  16/16 units[].page == {}
  1 个 page_start=document_start
  15 个 page_start=preserve_source_flow

02.2_t2_ai_unit_observation.yaml:
  route=NOT_AVAILABLE（默认离线运行，符合预期）

05_template_spec.yaml:
  16/16 units[].page 仍为 {}

06.2_build_manifest.json:
  page_breaks=[]
  section_breaks=[]
  pagination actions=0

07_verification_report.json:
  T2=UNKNOWN，但 page findings=[]

template-generation-judge:
  t2_unit_pagination=PASS
  02_unit_map standard report=PASS / SIGNABLE
  page mismatches=[]
  silent_drop_count=0
```

该复现证明：当前系统既没有在 T2 主产物中表达分页策略，也没有把“分页策略缺失”诊断出来。

## Expected vs observed

Expected：

1. T2 merged 对每个单元输出完整、规范化的分页语义，证据不足时显式 `unknown`，不能用
   `preserve_source_flow` 默认值冒充已识别策略。
2. code/AI/merged 三条 T2 route 都能独立比较分页维度；单元边界相同不代表分页 proposal 是 noop。
3. T5 无损保留 T2 分页语义、来源、冲突和 review flags，不重新推断。
4. T6 只从 T5 权威规格读取分页语义，并把可执行策略转成可溯源 Word 动作；不可执行项给出结构化原因。
5. T2/T5/T6 verifier、route-eval 和最终 Word gap 能分别证明“识别正确、汇总未丢、执行生效”。

Observed：

1. `units[].page` 可全部为空；`page_start` 只是兼容默认值。
2. T2 AI 输出契约和 proposal schema 都没有正式分页维度。
3. T5 只做被动复制；T6 分页动作读取另一份中间模型。
4. T6 只实现单元前 page/section break，不支持独占页和 keep-together 语义。
5. T2 standard verifier 没有消费标准里已经存在的 `expected.units[].page`。

## 根因归属

| 根因 | Owner | 说明 |
| --- | --- | --- |
| T2 runtime contract 与 T2 signed standard 分裂 | T2 | 标准有四个分页维度，runtime/prompt/schema 没有同形表达。 |
| T2 boundary proposal 与 pagination proposal 耦合 | T2 agent bridge/reconciler | 相同 unit range 会直接 noop，无法只更新分页策略。 |
| T5 与 T6 存在两个单元事实入口 | T5/T6 | T5 是文档声明的权威规格，但 T6 page planner 仍读 generation_model。 |
| verifier/judge 只查字段存在或 unit order | T7/judge | `page_start` 默认值和 unit order PASS 会遮住分页语义缺失。 |

## 已解决 / 未解决

已解决：

1. L1 已提供 `page_no`、page position、break facts 和 render binding，T2 有可回查事实输入。
2. 源 OOXML 存在显式分页/分节证据时，机械 page policy 能生成 before-unit action。
3. page break / section break 已有 Word 执行原语。

未解决：

1. T2 四维分页语义的统一 runtime contract、AI 输出和 merged 规则。
2. T5→T6 单一权威消费，以及 page isolation / keep-together 的执行映射。
3. 标准、运行 verifier、route-eval、最终 Word 之间的分层验收。

## 后续验收门禁

1. 当前湖南农大复现必须从“16 个空 page 仍 T2 PASS”变成明确 T2 mismatch；实现完成后再由正确的
   merged page policy 消除 mismatch。
2. T2 merged 的每个单元必须有四维分页语义或显式 unknown，并带 origin/confidence/evidence/conflict trace。
3. T5 对 T2 page policy 做逐单元无损保留；T6 page planner 不再读取 generation_model 的 page 字段。
4. 每个已确认策略必须对应 executed action，或对应 `no_action_required` / `manual_review` 的结构化理由。
5. 三校真实离线生成 + judge 不得出现分页 silent drop；有授权时补真实 T2 AI route，merged 不劣于 code/AI。
6. 最终 DOCX 必须用真实 OOXML 检查和渲染后 gap 证明 page break / isolation / keep 约束生效，不能只看 manifest。

本 issue 只记录问题事实；唯一执行契约见 Plan 11。

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-03 | 初稿：记录 AI 独占页信号未进入分页动作。 |
| 2026-07-16 | 按当前代码与湖南农大真实离线 run 重审：根因扩展为 T2 contract 缺失、T5/T6 双轨消费和 judge 假绿；移除已失真的 T4 page_policy_hint 旧假设。 |
