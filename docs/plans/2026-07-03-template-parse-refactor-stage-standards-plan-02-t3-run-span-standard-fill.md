---
status: implemented
owner: template-generation
stage: t3
topic: stage-standards
plan_id: STAGE-STANDARDS-PLAN-02
created: 2026-07-03
last_updated: 2026-07-03
source_issue:
  id: STAGE-STANDARDS-ISSUE-01
  doc: docs/plans/2026-07-03-template-parse-refactor-stage-standards-issue-01-incomplete-stage-standards.md
previous_plan:
  id: STAGE-STANDARDS-PLAN-01
  doc: docs/plans/2026-07-03-template-parse-refactor-stage-standards-plan-01-stage-standard-completeness-audit.md
---

# 阶段标准 Plan 02：补齐 T3 元素与 run/span 标准

## 目标

把当前只会暴露“不完整”的 T3 标准，补成能执行、能追责的元素级和 run/span 级标准。标准来源以人审 `template_quality/final_template.expected.yaml` 为准；真实 `01_document_facts.json` 和 `03_element_spec.yaml` 只用于定位 OOXML/run 证据、发现当前生成器反例，不能反写成标准答案。

## 实施顺序

1. 从三校 `final_template.expected.yaml#/expected/units[].elements[]` 生成 `expected.element_expectations`，每条绑定 `unit_id`、`element_id`、人审 `policy`、元素名、内容锚点和来源。
2. 用真实 `01_document_facts.json` / `03_element_spec.yaml` 做交叉定位：能定位到真实 T3 element 的，补 `source_seq_refs`、`raw_run_ids`、`logical_run_ids`；不能定位的，保留人审锚点并标明 `evidence_state: not_observed_in_latest_run`。
3. 扩展 T3 verifier，让 `element_expectations` 成为可执行标准：逐条检查 actual `element_spec` 的 policy、内容锚点和 run refs，不允许只靠数量通过。
4. 补 `run_span_ledger`：至少覆盖最新真实 T1 中可见 raw run 的处理归属，字段包括 `raw_run_id`、`logical_run_id`、`source_seq`、`expected_policy`、`expected_element_ref`、`text_anchor`。
5. 扩展 verifier 校验 `run_span_ledger`：每个声明 raw run 必须被 actual T3 某个 element 覆盖，且 unit/policy 与标准一致；未覆盖或 policy 错误均输出 T3 mismatch。
6. 跑 real-core 三校：标准质量应不再因为 T3 标准缺元素覆盖而 UNKNOWN；若当前生成器不符合人审标准，`template-generation-judge` 应 FAIL/NOT_SIGNABLE，并输出具体 element/run mismatch。

## 完成信号

- 三校 T3 标准包含不少于人审 final_template 元素数量的 `element_expectations`。
- 三校 T3 标准包含面向真实 T1 raw run 的 `run_span_ledger`，能定位每个声明 run 的处理归属。
- `template-generation-standard-quality --profile real-core-v0` 不再出现 `t3_standard_element_expectations_missing`。
- `template-generation-judge` 的失败原因从“标准缺失”转为具体 T3 产物与标准不一致，例如 policy、content anchor、raw run coverage。
- 新增测试覆盖：标准存在但 artifact policy 错、run 未覆盖、content anchor 缺失时会 FAIL。

## 实施结果

- hunannongye：`element_expectations=175`，`run_span_ledger=708`。
- nannong-undergraduate：`element_expectations=133`，`run_span_ledger=574`。
- pku-graduate：`element_expectations=78`，`run_span_ledger=1461`。
- `template-generation-standard-quality --profile real-core-v0`：`PASS`。
- 三校真实 run 的 `template-generation-judge`：`FAIL / NOT_SIGNABLE`，`first_bad_stage=T3`，失败类型为 `t3_element_expectation_mismatch` 与 `t3_run_span_ledger_mismatch`。
