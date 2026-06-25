---
status: implemented
owner: template-generation
stage: T2
topic: copy-only-policy
issue_id: T2-COPY-ONLY-ISSUE-02
issue_sequence: 2
severity:
  - P1
created: 2026-06-25
last_updated: 2026-06-25
previous_issue:
  id: T2-COPY-ONLY-ISSUE-01
  doc: docs/plans/template-parse-refactor-t2-copy-only-policy-issue-01-default-freeze.md
previous_optimization:
  doc: docs/plans/template-parse-refactor-t2-copy-only-policy-issue-01-default-freeze.md
  summary: "copy-only default changed from reverse exclusion list to explicit positive baseline"
next_plan: TBD
related_docs:
  - docs/plans/template-parse-refactor-issue-index.md
  - docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md
  - docs/plans/template-parse-refactor-copy-only-policy-bug.md
related_code:
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/generation_model.py
  - tests/contract/test_template_generate.py
---

# T2 Copy-Only Policy Issue 02：先关闭 copy-only 能力

## 0. 真实运行口径

本轮基于 T3 反馈继续收敛 copy-only 语义。上一轮已把 copy-only 从反向黑名单改成正向白名单，但仍保留 `cover` / `integrity_statement` / `post_forms` 默认 whole-unit copy。

真实问题没有消失：只要单元进入 `whole_unit_copy`，其内部 `fill` / `generated` 候选仍会在 generation model 中坍缩为 `fixed`。这会把“学生应填位置”和“系统生成域”冻结在最终模板里。

## 1. Expected vs Observed

Expected：

- 在没有学校级可验证策略来源前，模板生成不应自动做 `whole_unit_copy`。
- 所有单元先走 `copy_then_patch`，让 T3/T4 能显式处理 `fill`、`generated`、`remove_instruction`。
- 初始源 DOCX 复制仍作为执行底座保留，但不再产生 `preserve_whole_unit_copy` action。

Observed：

- ISSUE-01 后，`custom:template:*` / `other` 已不再默认冻结。
- 但 `cover` / `integrity_statement` / `post_forms` 仍默认 `whole_unit_copy`。
- T3 反馈里的 cover / post_forms 学生填写位仍会被 `_final_policy_for_generation()` 压成 `fixed`。

## 2. 疑似根因

copy-only 当前不是一个已验收的学校策略能力，而是一个全局启发式能力。它缺少：

- school/profile/request 级策略来源；
- copy-only 内部开洞规则；
- role/evidence/final policy 冲突门禁；
- gold expected 对照。

在这些缺口补齐前，继续保留默认 copy-only 会把风险藏在 `fixed` policy 里。

## 3. 上一轮已解决 / 未解决对照

| 项目 | 当前状态 |
| --- | --- |
| unknown/custom 默认冻结 | ISSUE-01 已解决 |
| copy-only 正向白名单 | ISSUE-01 已实现 |
| cover/post_forms 内部 fill 被压 fixed | 未解决，本文用关闭 copy-only 避免默认触发 |
| 学校级 copy-only 扩展入口 | 未解决 |
| copy-only 内部开洞策略 | 未解决 |

## 4. 本轮修复范围

实现口径：

- `COPY_ONLY_DEFAULT_UNIT_IDS` 置为空。
- T2 不再默认调用 `_copy_only_unit_elements()`。
- T3/generation model 不再默认产生 `whole_unit_copy` / `keep_whole_unit_copy`。
- 合同测试改为验证 cover 也走 `copy_then_patch`，且 cover 内部 fill 能生成 `create_fillable_slot`。

非目标：

- 不删除 copy-only 分支代码，后续可以用学校配置重新接入。
- 不移除 executor 对旧 `preserve_whole_unit_copy` action 的兼容处理。
- 不一次性修完 T2 单元边界和 T3 行内注释清理问题。

## 5. 验收门禁

代码门禁：

- `cover`、`references`、`custom:template:*` 默认均为 `copy_then_patch`。
- 计划中不应出现默认 `preserve_whole_unit_copy` action。
- cover 内部 `论文题目：____` 这类 fill 候选不再被坍缩成 fixed，应生成 `create_fillable_slot`。

真实模板门禁：

- 三校真实输出里 `unit_strategies[].generation_mode` 不应出现 `whole_unit_copy`。
- T3 残余中 copy-only 降级类问题应归零；若仍存在，应来自显式配置或旧产物，而不是默认策略。

本轮验证：

- `uv run pytest tests/contract/test_template_generate.py tests/unit/test_t2_unit_map.py -q` -> 27 passed。
- 三校真实生成输出：`/private/tmp/docfit_t2_copy_only_disabled/{school}`。
- 三校 `unit_strategies[].generation_mode == "whole_unit_copy"` 数量均为 0。
- 三校 `template_generation_plan.actions[].action_type == "preserve_whole_unit_copy"` 数量均为 0。
- 三校 `candidate_policy in {fill, generated}` 但最终 `policy=fixed` 的元素数量均为 0。
