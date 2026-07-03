---
status: draft
owner: template-generation
stage: T2T3T4
topic: agent-end-to-end-workflow
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-07
issue_sequence: 07
previous_issue:
  id: T2T3T4-AGENT-ISSUE-06
  doc: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-issue-06-observation-code-bridge-acceptance.md
  status: implemented
previous_optimization:
  doc: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-plan-06-observation-code-bridge-acceptance.md
  summary: Plan 06 已落地 observation bridge、--agent-observation-bundle CLI、bridge acceptance 报告与 contract/replay 测试；route-eval Plan 03 已先落 T3 三份 route artifact 槽位。但默认真实 run 仍未贯通 Module 1→Module 2→三路线评测，用户看到的 03.1 仍为 NOT_AVAILABLE 占位。
next_plan: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-plan-07-end-to-end-workflow-integration.md
created: 2026-07-01
last_updated: 2026-07-01
cross_issue:
  - docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-issue-03-full-chain-three-route-gap.md
  - docs/plans/2026-06-30-template-parse-refactor-t2t3t4-agent-module1-issue-05-observation-input-followups.md
  - docs/plans/2026-07-01-template-parse-refactor-module1-observation-dataflow-alignment.md
related_code:
  - src/docfit/template_generation/runner.py
  - src/docfit/template_generation/agent/loop.py
  - scripts/observe_live.py
  - src/docfit/cli/main.py
evidence_run:
  - test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/03.1_t3_ai_element_observation.yaml
---

# T2/T3/T4 Agent Issue 07：端到端主链路未完成，计划交付与可运行流程脱节

## 真实运行口径

当前仓库存在**三条可独立启动、但未默认串联**的入口：

```text
A. template-generate 默认路径（bootstrap / eval 常用）
   docfit eval template-generate --template <docx> --out <dir>
   -> AgentConfig.enabled=False（默认）
   -> 确定性 T1→T6
   -> 写出 03.0 code_raw / 03.1 ai_raw 占位 / 03.2 merged≈code

B. Module 1 独立观察（scripts/observe_live.py）
   document_facts -> run_observation_pipeline -> bundle.json
   -> 含 ai_unit/element/layout_observation
   -> 产物落在独立目录（如 test_outputs/observation_live/）
   -> 不会自动进入 template-generate run bundle

C. template-generate + observation bundle（需显式 flag）
   docfit eval template-generate ... --agent-observation-bundle <bundle.json>
   -> AgentConfig.enabled=True
   -> observation bridge -> comparison/reconciler -> merged
   -> 03.1 才可能有真实 ai_raw 内容
```

本轮问题由真实 run 触发：

```text
test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/
```

## Expected vs observed

Expected（按 Plan 04/06、route-eval Plan 03 的**产品语义**）：

```text
1. 一次 template-generate 真实 run 能稳定产出可评测的三路线 T3 产物：
   03.0 code_raw（AVAILABLE）、03.1 ai_raw（AVAILABLE 或明确 NOT_AVAILABLE）、03.2 merged。
2. Module 1 观察产物是 Module 2 桥接的常规上游输入，不是需要手工拼装的旁路。
3. 默认 run 若未跑 AI，03.1 应明确表达「未参与」，不得伪装成「AI 弃权」。
4. 计划标记 implemented 后，主链路应能被真实学校样本（hunannongye）端到端复现，而非仅 contract/replay fixture 绿。
5. standard-judge / route-eval 能基于同一次 run 解释 code vs ai vs merged 谁更接近标准。
```

Observed（2026-07-01 hunannongye 实测 + 代码路径核对）：

```text
1. 03.1_t3_ai_element_observation.yaml：
   - route.availability = NOT_AVAILABLE
   - reason = no AI observation bundle was supplied for this run
   - items = []
   - abstain = true
   - coverage.unknown_source_seq = 1..320（全量枚举）
   → 语义冲突：NOT_AVAILABLE 表示未跑 AI，abstain+全 unknown 表示 AI 跑了但认领不了。

2. 03.0 与 03.2 元素数均为 366，merged 实质等于 code 直通；ai 路线未参与合并。

3. ai/advisory.json：No AI diagnosis was run in the bootstrap harness.

4. Module 1 已有独立产物（test_outputs/observation_live/bundle.json，含真实 ai_element_observation），
   但与本次 template-generate run 无自动绑定；source_render_hash 也未在同一 run 内对齐校验。

5. run_template_agent 在 agent_config.enabled=False 时直接返回，不触发任何观察或桥接；
   generate_template 内部从不调用 run_observation_pipeline。

6. --agent-live 只走 Module 2 layered submission 循环，不等于 Module 1 观察流水线。

7. Issue 06 / Plan 06 标记 implemented，但验收口径是 CLI flag + replay/contract 测试；
   默认真实 run 仍无法体现「AI 观察 → 桥接 → merged」闭环。

8. route-eval Issue 03 / Plan 03 仅先落 T3 三份 artifact 槽位；完整 route evaluator、T5/T6 隔离重放、
   cross-route 分类仍未实现。
```

## 疑似根因

```text
1. 计划分期执行时，把「代码能力具备」与「主链路默认可跑通」混同为完成：
   bridge/CLI/artifact 槽位 / 单测合同先落地，端到端编排后移，但未回写为 open issue。

2. Module 1 与 Module 2 被刻意拆成两个入口（observe_live vs template-generate），
   缺少 run bundle 级的编排契约：谁生产 bundle、谁消费 bundle、hash 如何对齐、失败如何降级。

3. Agent default-off 合同保留正确，但未定义「开启 AI 路线」的产品默认路径
   （例如 eval profile、学校级开关、或组合命令），导致真实 run 长期停留在 code-only。

4. 03.1 NOT_AVAILABLE 占位复用了 abstain 形态（全 unknown_source_seq），
   把「未运行」伪装成「运行后弃权」，放大误判。

5. Module 1 输入/数据流仍有 open items（Issue 05、module1-observation-dataflow-alignment），
   T4 证据断链等问题未收口，进一步推迟了端到端集成优先级。
```

## 上一轮已解决 / 未解决对照

已解决（代码与合同层面）：

```text
1. observation_bridge.py：hash 校验、T2/T3 proposal 映射、manual review seeds。
2. CLI --agent-observation-bundle / AgentConfig.observation_bundle_path。
3. template_agent_observation_bridge、bridge_standard_acceptance 报告与相关单测/合同测。
4. run bundle 写出 03.0 / 03.1 / 03.2 三份 T3 route artifact 文件名与 debug index 说明。
5. Module 1 observe_live 可独立产出 bundle.json（已有 hunannongye 样本产物）。
6. 确定性 T3 code_raw 与 T6 构建在真实样本上可跑通。
```

未解决（端到端与用户可感知层面）：

```text
1. 默认 template-generate 真实 run 不经过 Module 1，03.1 恒为 NOT_AVAILABLE 占位。
2. Module 1 产物与 template-generate 无同 run 自动接线；需人工两次命令 + 路径拼接。
3. 三路线语义未在真实 run 中同时 AVAILABLE，route-eval 无法对 hunannongye 做有意义横向比较。
4. NOT_AVAILABLE 占位与 abstain 语义混用，易误导 judge/人工读包。
5. 无单一「完整模板生成（含 AI 观察）」验收命令或 profile；计划完成度与可运行度脱节。
6. T5/T6 三路线隔离重放、template-gap 纳入 route eval 仍未做（见 STANDARD-JUDGE-ISSUE-03）。
7. Module 1 T4 输入断链、observe_live 未接真实渲染等仍 open（见 MODULE1-ISSUE-05 / dataflow alignment）。
```

## 与相关 issue 的边界

```text
- STANDARD-JUDGE-ISSUE-03：偏「评什么、怎么横向比」；本 issue 偏「跑不起来 / 没接上」。
- T2T3T4-AGENT-ISSUE-06：偏 bridge 能力与验收报告；本 issue 记录其 implemented 后真实主链路仍断。
- MODULE1-ISSUE-05：偏 Module 1 阶段输入质量；本 issue 记录 Module 1 即使已有产物也未进入主 run。
```

本 issue **不展开**具体接线方案（组合命令、default profile、占位符改写、hash 对齐策略等）；方案另建 plan 并登记 `source_issue`。

## 后续验收门禁

```text
1. 存在文档化的「端到端模板生成（code + ai + merged）」标准运行口径，且可用 hunannongye 复现。
2. 同一次 run bundle 内：
   - 03.0 route.availability = AVAILABLE
   - 03.1 为 AVAILABLE（含真实 observation）或 NOT_AVAILABLE（语义纯净，不含 abstain+全 unknown 伪装）
   - 03.2 可证明 ai 路线是否改变了 merged（非必然等于 03.0）
3. Module 1 bundle 与 render packet 的 source_render_hash 不一致时，run 内有明确阻断/降级记录，不 silent fallback。
4. template-generation-judge / route-eval 能在该 run 上输出三路线 availability 与至少 T3 级横向诊断（完整 T1-T6 可分期，但 T3 必须先通）。
5. 计划完成状态与 issue 状态分离：仅当上述门禁在真实样本跑通后，方可将本 issue 标为 resolved。
6. default-off 保持不变；但 bootstrap/eval 文档必须写清「如何开启 AI 路线」，避免读者以为 03.1 异常即实现 bug。
```
