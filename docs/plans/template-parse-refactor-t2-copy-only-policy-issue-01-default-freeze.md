---
status: superseded
owner: template-generation
stage: T2
topic: copy-only-policy
issue_id: T2-COPY-ONLY-ISSUE-01
issue_sequence: 1
severity:
  - P1
created: 2026-06-25
last_updated: 2026-06-25
previous_issue: none
previous_optimization:
  doc: docs/current/template-generation-stage-optimization.md
  summary: "copy-only internal candidates were exposed as evidence, but the default copy-only predicate still used a reverse exclusion list"
next_plan:
  doc: docs/plans/template-parse-refactor-t2-copy-only-policy-issue-02-disable-copy-only.md
  summary: "copy-only positive baseline was still too risky; default copy-only is now disabled"
related_docs:
  - docs/plans/template-parse-refactor-issue-index.md
  - docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md
  - docs/plans/template-parse-refactor-copy-only-policy-bug.md
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md
related_code:
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/generation_model.py
  - tests/contract/test_template_generate.py
---

# T2 Copy-Only Policy Issue 01：默认冻结方向反了

> 2026-06-25 follow-up：本文的“正向白名单”修复已被 ISSUE-02 supersede。当前默认 copy-only 能力已关闭，`COPY_ONLY_DEFAULT_UNIT_IDS` 为空。本文仍保留作为“为什么不能反向默认冻结”的历史记录。

## 0. 真实运行口径

依据 T3 残余反馈文档和当前 `/private/tmp/docfit_t3_inspect/{school}` 产物核对：

- 输入：`inputs/targets/<school>/raw/source_template.docx`
- 关键产物：`artifacts/template_structure_candidates.json`、`artifacts/template_generation_model.json`、`03_element_spec.yaml`
- 当前观察点：`unit_strategies[].generation_mode`

## 1. Expected vs Observed

Expected：

- `copy-only` 只表示“这个单元已经被正向确认可以整单元保形复制”。
- 未识别的 `other` 或 `custom:template:*` 单元不能因为未知而默认冻结。
- 自定义单元里出现 `fill` / `generated` 候选时，应至少进入 `copy_then_patch` 路径，让 T3/T4 能看到并处理，而不是被 `whole_unit_copy` 静默压成 `fixed`。

Observed：

- 现有实现用反向排除集判断：除 `abstract_cn`、`abstract_en`、`toc`、`body_main`、`references` 外，其余 unit 全部 copy-only。
- 湖南 `custom:template:开题报告:*`、北大正文过切出的 `custom:template:研究背景:*`、南农 `custom:template:相关的学术成果目录:*` 都被标成 `whole_unit_copy`。
- T3 反馈中，copy-only 内部的 `fill` / `generated` 候选被 `_final_policy_for_generation()` 压成 `fixed`，导致 role/evidence/final policy 打架。

## 2. 疑似根因

根因在 T2 和 T3 之间的默认策略边界：

- T2 `_unit_is_copy_only_by_default(unit_id)` 把“不是已知活单元”解释为“可以整单元复制”。
- T3/generation model 复用同一个判断得到 `whole_unit_copy`。
- `whole_unit_copy` 下除 `remove_instruction` / `manual_only` 外，最终 policy 一律坍缩为 `fixed`。

这让 `copy-only` 从一个正向策略标记变成未知兜底标记。

## 3. 上一轮已解决 / 未解决对照

| 项目 | 当前状态 |
| --- | --- |
| copy-only 单元内部说明文字可进入 cleanup | 已解决 |
| copy-only 单元内部 fill/generated 候选以证据形式可见 | 已解决 |
| 默认 copy-only 仍靠反向黑名单 | 未解决，本文处理 |
| custom/other 默认 whole-copy 冻结 | 未解决，本文处理 |
| cover 内部填写位是否生成 slot | 未处理，保持现有产品口径 |
| 学校级 copy-only 扩展入口 | 未处理，后续单列 |

## 4. 本轮修复范围

最小修复：

- 将默认 copy-only 规则改成正向白名单。
- 默认白名单仅保留当前已稳定依赖的保形单元：`cover`、`integrity_statement`、`post_forms`。
- `custom:template:*` / `other` 不再默认 copy-only，走 `copy_then_patch`。
- 保持封面 copy-only 内部 `fill` 候选降级为 fixed 的旧行为，避免本轮同时改变封面自动开洞策略。

非目标：

- 不实现学校 profile / request 级 copy-only 扩展入口。
- 不决定 `acknowledgement` / `appendix` 是否应该默认 copy-only。
- 不把 T3 role/policy 降级直接升级成 FAIL。

## 5. 验收门禁

代码门禁：

- 新增合同测试：自定义单元默认不是 copy-only，`generation_mode=copy_then_patch`，不会生成 `preserve_whole_unit_copy` action。
- 既有合同测试继续证明 `cover` 仍是 `whole_unit_copy`，`references` 仍是 `copy_then_patch`。

真实模板门禁：

- 三校真实输出里，`custom:template:*` 不应再默认出现 `generation_mode=whole_unit_copy`。
- T3 残余中 `generated_field/student_content -> fixed` 的 custom/other 部分应减少；cover/post_forms 残余若仍存在，应进入下一轮“copy-only 内部开洞策略”讨论。

本轮验证：

- `uv run pytest tests/contract/test_template_generate.py tests/unit/test_t2_unit_map.py -q` -> 27 passed。
- 三校真实生成输出：`/private/tmp/docfit_t2_copy_only_fix/{school}`。
- 湖南：`custom:template:开题报告:*`、`custom:template:开题论证记录表:*`、`custom:template:答辩记录表:*`、`custom:template:成绩评定表:*` 均为 `copy_then_patch`。
- 南农：`custom:template:title:*`、`custom:template:第章结论与展望:*`、`custom:template:相关的学术成果目录:*` 均为 `copy_then_patch`。
- 北大：全部 `custom:template:*` 均为 `copy_then_patch`。
