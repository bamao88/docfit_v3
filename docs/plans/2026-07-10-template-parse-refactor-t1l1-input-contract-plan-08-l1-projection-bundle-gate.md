---
status: implemented_in_part
owner: template-generation
stage: T1L1
topic: fact-render-input-projection
doc_type: plan
plan_id: T1L1-INPUT-CONTRACT-PLAN-08
source_issue:
  id: T2T3T4-AGENT-ISSUE-08
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-08-t1-l1-input-contract.md
previous_plan:
  id: T2T3T4-AGENT-PLAN-10
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-10-t4-ai-primary-layout-consumption.md
created: 2026-07-10
last_updated: 2026-07-10
---

# T1/L1 输入契约 Plan 08：统一事实投影与 bundle gate 闭环

## Summary

本计划解决 issue-08 的剩余输入契约缺口：把 T1a DOCX 事实、T1b render/page 事实和 AI observation bundle gate 汇成一个可审计的 L1 投影产物。该产物不改变 T1 边界，不产生 `unit_id/policy/confidence` 等下游判断，只暴露 code 与 AI 共同可读的事实、绑定状态和覆盖缺口。

## 实施顺序

1. 新增 L1 输入契约 artifact。
   - 产物名：`template_generation_l1_input_contract.json`。
   - 视图：`source_text_index`、`source_object_index`、`layout_fact_index`、`visual_page_index`、`bundle_gate_view`、`coverage`。
   - 输入只来自 `document_facts`、可选 render packet、可选 AI observation bundle / bridge。

2. 补全 source text / object / layout / visual 投影。
   - `source_text_index` 保留 `source_seq/source_ref/text/style/style_details/text_facts/run ids/page/bbox/binding_status`。
   - `source_object_index` 覆盖 images、text_boxes、content_controls、footnotes、unknown visible objects；每项必须带 `binding_status`。
   - `layout_fact_index` 覆盖 sections、header/footer、fields、breaks、numbering。
   - `visual_page_index` 汇总 clean/annotated page images、page layout index、render status/hash。

3. 建立 bundle gate 诊断。
   - 记录 observation bundle 是否存在、`source_render_hash` 是否对齐、T2/T3/T4 schema/coverage 是否通过。
   - 不通过时输出结构化 gate error，不中断模板生成。

4. 接入 run bundle 与 standard judge。
   - run bundle 绑定 L1 artifact。
   - route-eval 把 L1 coverage 作为 T1/T2/T3/T4 输入契约诊断证据。
   - 缺 render、缺对象绑定、缺 bundle gate 时输出 `UNKNOWN/NOT_AVAILABLE` 类诊断，不伪造 PASS。

## 完成信号

1. `template-generate` 默认写出 `template_generation_l1_input_contract.json` 及 ordered debug 文件。
2. L1 artifact 不包含 T2/T3/T4 语义判断字段。
3. 每个 object 证据都有 `binding_status`，不能绑定时显式说明原因。
4. `template-generation-judge` 的 route-eval 报告能展示 L1 coverage 和 bundle gate 状态。
5. 合同测试覆盖：无 render fallback、有 render packet、bundle hash mismatch、对象未绑定四类场景。

## 非目标

1. 不在 T1 输出语义判断字段。
2. 不把 object/page overlay 做成视觉精确定位的最终方案；本轮先要求可追踪和可诊断。
3. 不自动接受 AI observation；bundle gate 只决定可评性和风险归因。

## Progress

```text
2026-07-10:
  已落地 L1 输入契约 artifact：
    - 默认 template-generate 写出 01.5_l1_input_contract.json / template_generation_l1_input_contract。
    - artifact 包含 source_text_index、source_object_index、layout_fact_index、visual_page_index、bundle_gate_view、coverage。
    - run bundle 已绑定该 artifact；standard judge 的 route-eval 已把 L1 纳入统一报告。
    - route-eval 可诊断缺 render、object binding gap、bundle gate invalid stage。
  已验证：
    - uv run pytest tests/unit/test_template_generation_input_contract.py tests/contract/test_template_generation_standard_judge.py -q
    - uv run pytest -q
  仍非闭环项：
    - 精确 object/page overlay 和真实 render 绑定仍作为 coverage/gap 暴露，不在本轮伪造完成。
    - L1 artifact 目前是统一输入投影和诊断证据，尚未强制所有下游 code/AI 只从该投影读取。
```
