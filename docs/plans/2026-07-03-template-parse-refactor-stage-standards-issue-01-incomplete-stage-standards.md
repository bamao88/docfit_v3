---
status: draft
owner: template-generation
stage: cross-stage
topic: stage-standards
issue_id: STAGE-STANDARDS-ISSUE-01
issue_sequence: 01
severity:
  - P1
created: 2026-07-03
last_updated: 2026-07-03
previous_issue:
  id: T3-ELEMENT-ISSUE-06
  doc: docs/plans/2026-07-02-template-parse-refactor-t3-element-policy-issue-06-placeholder-span-granularity.md
  status: draft
previous_optimization:
  doc: docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-plan-03-full-chain-three-route-evaluator.md
  summary: 已建立 T1-T5 阶段裁判报告和三路线 artifact 槽位，但阶段标准仍只覆盖粗粒度字段，不能解释最终 Word 与人审标准之间的具体差异。
next_plan: docs/plans/2026-07-03-template-parse-refactor-stage-standards-plan-01-stage-standard-completeness-audit.md
related_docs:
  - docs/current/template-generation-stage-standard-quality.md
  - docs/current/template-generation-stage-standards.md
  - docs/plans/template-parse-refactor-issue-index.md
evidence_fixture:
  targets:
    - hunannongye
    - nannong-undergraduate
    - pku-graduate
  real_run_root: test_outputs/debug/template_generation/20260701_real_template_generate_t2t4_routes_three_docs
---

# 阶段标准 Issue 01：T1-T5 标准文件存在但缺少可证明完整性的深层验收

## 问题摘要

real-core-v0 三校已经有 T1-T5 阶段标准文件，并且 `template-generation-standard-quality` 与 `template-generation-judge` 当前都能输出 `PASS/SIGNABLE`。但这些标准没有覆盖人审文档中已经存在的元素级、run/span 级、页面和最终 Word 差异验收，因此会把“粗粒度字段匹配”误显示成“阶段标准完整”。

最明显的缺口在 T3：人审 `final_template.expected.yaml` 已经抽取三校元素清单，湖南 175 个元素、南农 133 个元素、北大 78 个元素；而 T3 阶段标准没有完整元素级期望，只有湖南 1 组 run-level 样例，南农和北大没有 run-level 期望。

## 真实运行口径

标准质量探针：

```bash
uv run docfit eval template-generation-standard-quality \
  --profile real-core-v0 \
  --out /tmp/docfit_stage_standard_quality_probe
```

三校阶段裁判探针：

```bash
uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run test_outputs/debug/template_generation/20260701_real_template_generate_t2t4_routes_three_docs/hunannongye \
  --out /tmp/docfit_tg_judge_hunannongye_probe
```

最终 Word gap 探针：

```bash
uv run docfit eval template-gap \
  --school hunannongye \
  --generated-template test_outputs/debug/template_generation/20260701_real_template_generate_t2t4_routes_three_docs/hunannongye/fillable_template.docx \
  --out /tmp/docfit_gap_hunannongye_probe
```

## Expected vs observed

Expected：

```text
1. 如果人审 final_template 已有元素清单，阶段标准质量检查必须证明 T3 标准覆盖这些元素，或明确报 UNKNOWN。
2. 如果 T3 真实 artifact / 最终 DOCX 中仍有格式说明、占位符、示例值残留，standard judge 必须输出 mismatch/root_cause/owner/fix_plan。
3. T6/T7 还没有正式标准时，报告不能把 fillable_template/build_manifest/verification_report 的 run bundle 绑定当作最终签收。
```

Observed：

```text
1. real-core-v0 T1-T5 标准质量报告当前为 PASS。
2. 三校 template-generation-judge 当前为 PASS/SIGNABLE，mismatches/root_causes/owner_assignments/fix_plan 均为空。
3. 三校 template-gap 对最新 fillable_template.docx 均为 FAIL。
4. 湖南最新 T3/DOCX 扫描仍可见格式说明和 placeholder-like residual。
```

## 疑似根因

```text
1. 阶段标准质量检查只审登记、metadata、artifact_under_test、unit_order 等粗粒度结构。
2. T3 阶段标准没有从 final_template.expected.yaml 继承元素级 expectation，也没有声明每个可见 raw run 的处理 ledger。
3. T3 verifier 只检查 policy group、policy 必需字段，以及标准显式列出的少量 run_level_elements。
4. T6/T7 缺少阶段标准，最终 Word 差异尚未作为同一套 stage standard diff diagnosis 的证据层。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. T1 已能输出 run 级事实和 raw/logical run 追踪。
2. T3 已能在 artifact 中携带 raw_run_ids/logical_run_ids。
3. standard judge 已有 mismatches/root_causes/owner_assignments/fix_plan 报告结构。
```

未解决：

```text
1. 标准质量 PASS 不代表人审元素标准已经被 T3 阶段标准覆盖。
2. T3 标准缺少完整 element/run/span ledger。
3. 最终 Word gap FAIL 没有稳定回链到阶段标准缺口。
4. T6/T7 仍是证据绑定，不是签收标准。
```

## 后续验收门禁

```text
1. real-core 三校标准质量报告必须能发现 T3 元素标准未覆盖 final_template 元素清单，并输出 UNKNOWN 或 FAIL。
2. template-generation-judge 不能在 T3 标准未覆盖人审元素清单时输出 SIGNABLE。
3. 报告必须包含四层诊断：mismatches、root_causes、owner_assignments、fix_plan。
4. 后续补全 T3 标准时，每个可见 raw run 必须有明确处理归属或明确 UNKNOWN。
5. 最终 template-gap 的 unit/order/page/style/element 缺口应能回链到 T2/T3/T4/T5/T6 的首个责任阶段。
```

