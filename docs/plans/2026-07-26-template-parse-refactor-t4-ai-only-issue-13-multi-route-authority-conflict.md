---
status: superseded
owner: template-generation
stage: T4T5T6T7
topic: t4-ai-only
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-13
issue_sequence: 13
severity:
  - P1
previous_issue:
  id: T2T3T4-AGENT-ISSUE-12
  doc: docs/plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-issue-12-source-boundary-model-conflict.md
previous_optimization:
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-10-t4-ai-primary-layout-consumption.md
  summary: Plan 10 仍以 AI-primary、Code fallback 和三路线比较为目标；用户最新决定是 T4 只保留 AI 路线。
next_plan: docs/plans/2026-07-26-template-parse-refactor-t4-ai-only-plan-13-single-ai-final.md
created: 2026-07-26
last_updated: 2026-07-26
related_status:
  - docs/status/closed/t4-ai-only-route.md
---

# T4 Issue 13：多路线权威与 AI-only 目标冲突

> 2026-07-26：本 issue 的 AI-only 目标已完成代码清理，但随后被 Issue 14
> “copy-first 生产链暂停并跳过 T4”取代。本文保留为历史演进证据，不再作为当前目标。

## 问题摘要

用户已决定 T4 改为 AI-only。变更前的生产链仍同时生成确定性
`global_spec`、AI observation、AI 物化候选和 merged 候选，并通过 hint bridge /
reconciler 把 AI 记录为对 Code 结果的佐证。

## Expected vs Observed

Expected：

1. T4 布局语义只来自 AI。
2. 程序只负责 sealed L1/render 输入、身份和证据校验、结构物化及 Final Publisher。
3. 正式产物只有 AI raw 和一个 T4 final。
4. AI 未运行、弃权、输出无有效 section、跨 run 或证据绑定失败时，T4 final 为
   `NOT_AVAILABLE`，不得回退 Code。
5. T5/T6/T7 只消费或传播唯一 T4 final。

Observed：

1. `build_global_spec` 可不经 AI 生成完整 T4 语义。
2. T4 同时发布 `code_raw`、`ai_raw`、`merged` 三个正式比较面。
3. observation bridge、pass plan、comparison、manual review、reconciler 和 T4 hints
   仍围绕旧多路线工作。
4. 无 AI 输出时，确定性 section profile 仍可让 T4 看起来可用。
5. CLI、judge、route replay、测试和 current 文档继续把 merged 当主结论。

## 影响与风险

- 业务无法判断最终版式究竟来自 AI 还是 Code。
- AI 失败会被确定性 fallback 掩盖，availability 出现假绿。
- 旧 bridge/hint 产物没有独立业务价值，却扩大维护面。
- route evaluator 用不存在的三路 delta 代替唯一 AI final 的准确率。

## 验收门禁

1. 生产代码不再生成、读取或写出 T4 Code/Merged/hint/bridge 产物。
2. `04_global_spec.yaml` 的 `producer_mode=ai`，且只引用
   `04.1_t4_ai_layout_observation.yaml`。
3. AI abstain 和跨 run bundle 反例均得到 `NOT_AVAILABLE` 且 section profiles 为空。
4. T5 availability 保守传播 T4 不可用状态。
5. CLI、judge、测试和 canonical 文档只描述 T4 AI route。
6. 聚焦测试、合同测试和旧符号残留扫描通过。

本 issue 只记录问题事实；执行契约见 Plan 13。T4 三校 live 准确率与正式 gold
仍是后续质量闭环，不因代码清理自动完成。
