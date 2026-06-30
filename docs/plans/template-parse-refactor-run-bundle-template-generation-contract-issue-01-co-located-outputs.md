---
status: draft
owner: template-generation
stage: run-bundle
topic: template-generation-run-bundle-contract
issue_id: RUN-BUNDLE-ISSUE-01
issue_sequence: 1
created: 2026-06-28
last_updated: 2026-06-28
version: 1
previous_issue:
  id: none
  doc: none
previous_optimization:
  doc: none
  summary: none
next_plan:
  id: RUN-BUNDLE-PLAN-01
  doc: docs/plans/template-parse-refactor-run-bundle-template-generation-contract-plan-01-phased-execution.md
  summary: 将模板生成运行包契约拆成 P0-P7：定名、run root 推导、产物落盘、后续 eval 共址、报告命名、证据绑定、文档同步和验收门禁。
related_code:
  - src/docfit/convert/orchestrator.py
  - src/docfit/template_generation/outputs.py
  - tests/contract/test_template_generate.py
---

# Run Bundle Issue 01：模板生成运行包契约里的共址输出

## 0. 记录目的

模板生成运行包契约规定一次 `template-generate` 运行产生的机器产物、debug 快照、人工排查材料和后续 eval 输入如何打包、命名、归档和被后续流程读取。

本 issue 只处理契约里的输出布局部分：这些产物都属于同一个 run bundle，不应该一部分落在 `test_outputs/debug/template_generation/<run-id>/eval_runs/...`，另一部分又被自动写到 `runs/template_generation/...`。

## 1. 当前真实运行口径

用户刚运行的目标归档根：

```text
/Users/fl/WXP/docfit_v3/test_outputs/debug/template_generation/20260621T160704467333+0800/
```

这个根目录下允许出现：

```text
eval_runs/
human/
```

现有代码路径：

```text
src/docfit/convert/orchestrator.py::_template_generation_project_dir()
```

Observed：

```text
_template_generation_project_dir() 当前固定偏向 root/runs/template_generation。
当 --out 不在 root/runs/template_generation/<id>/eval_runs/... 下时，
debug_root 会退回 root/runs/template_generation/<template_docx.stem>。
```

## 2. Expected vs Observed

Expected：

```text
如果 --out 是：
test_outputs/debug/template_generation/<run-id>/eval_runs/<eval-run-id>

则模板生成伴随产物必须写到：
test_outputs/debug/template_generation/<run-id>/human/<timestamp>

不应额外写到：
runs/template_generation/**
```

Observed：

```text
debug snapshot / human-readable 辅助材料可能被写到 runs/template_generation/**，
导致一次流程的材料拆成两个根目录，后续人工查看和打包都容易漏。
```

## 3. 疑似根因

```text
1. _template_generation_project_dir() 只识别 runs/template_generation 旧布局。
2. debug_root 与 --out 缺少同 bundle 推导规则。
3. 历史文档曾把 test_outputs/debug/template_generation 迁移到 runs/template_generation，
   但当前模板生成调试运行仍需要按 test_outputs/debug/template_generation/<run-id> 打包。
```

## 4. 上一轮已解决 / 未解决对照

已解决：

```text
1. template-generate 已能在 --out 下写出完整阶段产物链。
2. debug snapshot 已有 00-14 编号文件和 99 index。
```

未解决：

```text
1. debug/human 伴随产物的根目录没有跟随 --out bundle。
2. 合同测试没有防止 test_outputs run 同时污染 runs/template_generation。
```

## 5. 后续验收门禁

```text
1. --out 位于 test_outputs/debug/template_generation/<run-id>/eval_runs/<name> 时：
   - public eval 产物写到 eval_runs/<name>
   - debug/human 快照写到 human/<timestamp>
   - 不创建 runs/template_generation/**
2. --out 位于任意包含 eval_runs 的 bundle 时，debug_root 取 eval_runs 的父级 bundle/human。
3. --out 不包含 eval_runs 时，debug_root 收在 --out/human，不再退回仓库固定 runs/template_generation。
4. 合同测试锁住 summary.artifacts.template_generation_debug_dir 指向 human/<timestamp>。
```
