---
status: draft
owner: template-generation
stage: cross-stage
topic: stage-standards
plan_id: STAGE-STANDARDS-PLAN-01
created: 2026-07-03
last_updated: 2026-07-03
source_issue:
  id: STAGE-STANDARDS-ISSUE-01
  doc: docs/plans/2026-07-03-template-parse-refactor-stage-standards-issue-01-incomplete-stage-standards.md
---

# 阶段标准 Plan 01：标准完整性审计与 T3 元素覆盖门禁

## 目标

先让标准裁判诚实暴露“不完整”，再逐步补深标准内容。第一阶段不尝试一次性人工编完三校所有 run/span 标准，而是新增确定性审计：当 `final_template.expected.yaml` 已有人审元素清单，而阶段标准缺少可执行元素覆盖时，标准质量和 judge 必须降为 `UNKNOWN`，并输出可执行诊断。

## 实施顺序

1. 在标准质量检查中读取 `final_template.expected.yaml#/expected/units[].elements[]`，统计每校人审元素数量。
2. 为 T3 标准增加完整性审计：如果没有 `expected.element_expectations` 或等价元素覆盖声明，则输出 `t3_element_expectations_missing`。
3. 保留现有 `run_level_elements` 检查，但将其定位为局部样例，不允许替代完整元素覆盖。
4. 在 standard judge 的四层诊断中把该缺口归为 `standard_issue`，owner 指向 `standard_owner`，fix plan 指向 T3 标准补全和 run/span ledger。
5. 补测试：构造有 final_template 元素但 T3 标准缺元素 expectation 的标准集，断言质量报告和 judge 不再 PASS/SIGNABLE。
6. 跑 real-core 三校质量和 judge，确认现有不完整标准被标为 UNKNOWN，且最终不会再被写成 SIGNABLE。

## 完成信号

- `template-generation-standard-quality --profile real-core-v0` 不再把当前 T3 标准质量写成 PASS。
- `template-generation-judge` 在 T3 标准缺完整元素覆盖时输出 `standard_acceptance_status != PASS`、`signoff_status=NOT_SIGNABLE`。
- 报告中出现 `mismatches[]`、`root_causes[]`、`owner_assignments[]`、`fix_plan[]`，并能说明“人审元素标准未被阶段标准覆盖”。
- 现有 T1/T2/T4/T5 粗粒度门禁保持可用，不因 T3 完整性缺口误报为代码生成失败。

