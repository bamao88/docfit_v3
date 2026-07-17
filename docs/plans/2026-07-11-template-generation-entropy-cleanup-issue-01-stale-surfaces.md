---
status: closed
owner: template-generation
stage: full-chain
topic: entropy-cleanup
doc_type: issue
issue_id: TEMPLATE-GENERATION-ENTROPY-CLEANUP-ISSUE-01
issue_sequence: 01
previous_issue:
  id: none
  doc: none
  summary: 首轮以现役 template-generation-full 为唯一主线的删除型清理。
previous_optimization:
  doc: docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-plan-01-end-to-end-closure.md
  summary: 全链路入口、post-T6 gap、route-eval 和 full summary 已落地，使旧四阶段入口和重复输出契约可以被重新审计。
next_plan: docs/plans/2026-07-11-template-generation-entropy-cleanup-plan-01-delete-stale-surfaces.md
created: 2026-07-11
last_updated: 2026-07-11
---

# 模板生成熵清理 Issue 01：旧公共入口、重复输出和无调用叶子仍存活

## Expected vs observed

| 编号 | Expected | Observed | 影响 |
| --- | --- | --- | --- |
| 01 | `template-generation-full` / `template-generate` 是当前模板阶段唯一公共生成主线。 | CLI 仍暴露旧 `template`、`content`、`placement`、`render`、`e2e`、`coverage` 和 `convert`，旧 stage 原型仍可达。 | 当前文档说学生链路 deferred，但 CLI 给出相反信号。 |
| 02 | 一次 `template-generate` 的每个权威产物只有一个 canonical path。 | 同一 payload 同时写入顶层编号文件、`artifacts/` 兼容路径和 timestamp human debug snapshot。 | reader、测试和人工排查必须维护三套路径语义。 |
| 03 | AI raw 质量只由现役 standard judge / route-eval 负责。 | standalone `observation_eval`、终止工具定义、兼容 replay 类和多个别名没有生产调用，但仍由测试维持。 | 维护者会误判为并行生产能力；当前新增 element gold 指标还没有进入现役 owner。 |

## 当前事实

- 当前公共入口和固定 run root 由 `docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-plan-01-end-to-end-closure.md` 定义。
- `src/docfit/stages/**` 旧 stage 实现约 2,688 行。
- `outputs.py` 同时维护正式写出、ordered 写出和独立 debug snapshot。
- 静态生产引用扫描确认 `observation_tools.py` 无调用者；`observation_eval.py` 只有测试调用。
- 当前工作区包含未提交的 full-chain、route replay、T4 hint 和 element expectation eval 工作，删除必须保留这些现役能力。

## 验收门禁

- 旧 CLI/旧 stage/旧 artifact 路径的引用扫描清零。
- `template-generation-full`、`template-generate`、`template-gap`、`template-generation-judge` 继续可用。
- T1/L1/T2/T3/T4/T5/T6/T7/POST_T6 和 `code_raw/ai_raw/merged` 诊断能力不降级。
- 当前 `observation_eval` 中仍有价值的 element expectation 指标先迁入 route-eval owner，再删除 standalone 模块。
- 聚焦测试、合同测试、全套测试和三校真实模板验证给出可审计结果。

## 不算完成

- 只删文件但保留 CLI、fallback、测试或文档引用。
- 用兼容 wrapper 继续维持旧路径。
- 因删除而让 route-eval、full summary 或真实模板证据变少。
- 只用 import 成功或少量单测替代公共 CLI/artifact 迁移验证。

## 关闭证据

- 旧四阶段 CLI、`src/docfit/stages/**`、obsolete harness/script/test 和无调用 evaluator/compatibility leaves 已删除。
- `template-generate` 只写一套顶层编号产物；`artifacts/` 镜像、timestamp human 快照、未编号 Word、manifest debug pointer 和 reader fallback 已清零。
- `template_artifact` legacy view 已删除；仍参与算法的 source tree、structure candidates、generation model 和 plan 只在运行内消费。
- `uv run pytest -q`：`304 passed`。
- 湖南农大、南农、北大三校 `template-generation-full` 均完成运行，必需编号文件零缺失、旧路径零残留；最终 `FAIL` 为既有质量门禁结果，不是本轮运行或产物契约回退。
