---
status: resolved
resolved_at: 2026-06-25
owner: template-generation
stage: T3
topic: element-policy
issue_id: T3-ELEMENT-ISSUE-01
issue_sequence: 1
severity:
  - P1
created: 2026-06-25
last_updated: 2026-06-25
previous_issue:
  id: none
  doc: none
previous_optimization:
  doc: docs/plans/template-parse-refactor-stage-issues.md
  summary: "initial stage issue ledger that recorded T3 element confidence noise"
next_issue:
  id: T3-ELEMENT-ISSUE-02
  doc: docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md
next_plan: TBD
related_docs:
  - docs/plans/template-parse-refactor-issue-index.md
  - docs/plans/template-parse-refactor-stage-issues.md
  - docs/current/template-generation-stage-optimization.md
related_code:
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/verifier.py
---

# T3 元素策略 Issue 01：element confidence 全员 medium 噪声

> **状态：已解决。** 本文只作为历史 issue 入口，说明上一轮 T3 优化解决了什么，以及为什么后续问题转入 issue-02。

## 0. 问题

上一轮优化前，T3 `_element_from_entries()` 默认给 element 写 `confidence: medium`。结果是大量明确的固定文本、说明文字、生成字段也进入 `UNKNOWN`，verification report 里 `t3_element_confidence_needs_review` 成为噪声大头。

这类 finding 不能有效区分：

- 真正需要审核的 fill/generated 判定。
- 确定性固定文本。
- 明确 instruction_remove。
- 空白或弱证据元素。

## 1. 上一轮优化

上一轮优化把 `element_spec` 的 confidence 改为基于最终 policy、marker、label 和 `role_hint` 计算：

- 明确 fixed / instruction / generated 可升为 `high`。
- 弱证据 fill 保持 `medium`。
- role_hint 与 final policy 冲突时保持 `medium`，让 copy-only 降级浮现。

相关背景文档：

- `docs/plans/template-parse-refactor-stage-issues.md`
- `docs/current/template-generation-stage-optimization.md`

## 2. 已解决验收

当前三校重跑后，T3 不再是全员 medium：

| 学校 | element 总数 | high / medium / low |
| --- | ---: | --- |
| 湖南农大 | 320 | 275 / 45 / 0 |
| 南农本科 | 103 | 93 / 10 / 0 |
| 北大研究生 | 359 | 319 / 40 / 0 |

## 3. 转入下一轮的问题

confidence 噪声清理后，真正残余问题转入：

`docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md`

issue-02 不再讨论“全员 medium”，只讨论优化后暴露的真实问题：

- copy-only 内部 fill/generated 候选被压成 fixed。
- 推断 fill 缺 gold 无法精确判。
- 行内格式注释无法段内剥离。
- T5 重投影 T3 flag。
