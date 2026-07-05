---
status: draft
owner: template-generation
stage: T2T3T4
topic: ai-primary-migration
doc_type: direction_proposal
created: 2026-07-03
last_updated: 2026-07-03
related_issues:
  - docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-issue-05-inline-style-instruction-fixed-merge.md
  - docs/plans/2026-07-02-template-parse-refactor-t3-element-policy-issue-06-placeholder-span-granularity.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-08-t1-l1-input-contract.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-09-ai-raw-not-merged.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-10-t4-observation-downstream-dead-end.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-11-unit-pagination-signal-loss.md
related_plans:
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-09-ai-raw-to-merged.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-10-t4-ai-primary-layout-consumption.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-11-unit-pagination-alignment.md
  - docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md
  - docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-plan-03-full-chain-three-route-evaluator.md
---

# 方向提案：T2/T3/T4 分阶段转 AI 为主（deterministic code 转校验/兜底）

## 背景与决策

模板生成阶段当前采用「deterministic code 为主 + AI observation 经 bridge/merge 补充」的架构。真实
hunannongye run 暴露三个质量问题，且共享同一个结构性根因：**AI 观察结果在 bridge/merge 后被降级或
丢弃，几乎不影响最终产物**。

```text
1. T3 元素颗粒度太粗：policy 只到 element 级；行内格式说明（issue-05，8 处残留）
   和 placeholder 子 span（issue-06，66 个非删除元素）无法表达；AI 的 T3 观察
   178 条全部进 manual_review，0 条生效（issue-09）。
2. T4 明点（分节/页眉页脚/页码逻辑）AI 侧不准：deterministic build_global_spec
   已完整；AI vision 侧输入不足（issue-08 T4 切片），且识别结果 merge 后只写
   global_spec["agent_observation_hints"]，生产代码无任何读取者（issue-10）。
3. 单元分页与 T2 识别不对齐：plan.py 的分页动作只消费机械 page_break_before
   证据；AI/vision 的单元独占页判断（page_isolation_accuracy=0.6875）在
   bridge 前即丢失（issue-11）。
```

本轮用户决策（2026-07-03）：

```text
D1 明点 = 分节结构、每节页眉页脚、页码逻辑；code 路线已有，AI 路线输入缺失。
D2 本轮先产出分析与方案文档，不直接改代码。
D3 架构方向 = 分阶段转 AI 为主：T4、T3 先行，T2 暂保持 merge；
   用三路线评测（route-eval plan-03）验证后再晋升。
```

## 目标运行模式（分阶段）

| 阶段 | 目标模式 | deterministic code 角色 | 迁移状态 |
| --- | --- | --- | --- |
| T4 全局版式 | **AI 为主**：AI（含 vision）产出 section_profiles / header_footer / page_numbering / 单元页策略，作为 merged 权威 | `build_global_spec`（`artifacts.py`）继续运行，作为字段级校验方与 AI NOT_AVAILABLE 时的兜底权威 | 第一批 |
| T3 元素策略 | **AI 为主**：AI 按 run/span 粒度产出元素边界 + policy + 子 span 处置 | `build_element_spec` 输出作为基线校验；确定性 field-line parser / instruction 规则做反例防护 | 第一批（依赖 span 模型落地） |
| T2 单元识别 | **保持 merge**：deterministic 主干 + AI proposal 补充 | 现状不变 | 明确非目标；待 T3/T4 晋升数据回看后再议 |

「AI 为主」的准确含义：

```text
1. AI observation 是该阶段 merged 权威产物的默认来源；
2. deterministic code 不再是权威，但必须继续运行并逐字段比对，
   分歧 → conflict / manual_review / open_question，不允许静默覆盖任何一方；
3. AI NOT_AVAILABLE 或 abstain 时，deterministic 路线自动回升为权威（兜底）；
4. 三路线 artifact（code_raw / ai_raw / merged）继续全部落盘，可审计可回放。
```

## 各阶段前置依赖

```text
T4 AI 为主：
  ① issue-08 的 T4 输入切片补齐（页眉页脚内容文本、fields、breaks 进 evidence 与 vision prompt）
  ② plan-09 Phase 3（T4 observation 可进入 merged 证据）
  ③ plan-10（merged 一等字段 + T5/T6 消费，替代 agent_observation_hints 死端）

T3 AI 为主：
  ① plan-09 Phase 2（T3 executable overlay，低置信不再 bridge 硬阻断）
  ② t3 plan-06（run/span 子元素模型 + AI span 级观察 + T6 替换契约）
  ③ 三校 T3 element_expectations / run_span_ledger 标准（stage-standards plan-02，已实现）

单元分页对齐：
  plan-11（page_policy_hint 生产 → merged page policy → plan.py 消费）
  与 T4 迁移并行推进，互不阻塞。
```

## 晋升门禁（何时允许 AI 成为权威）

统一用三路线评测（`route-eval plan-03`；其统一评测器尚未实现，是本方向的**前置工程债**）：

```text
1. 分阶段指标，三校（hunannongye 等）全量：
   - T4：明点字段级准确率（page_setup / page_numbering / header_footer_policy
     对 gold 标准），加 page_isolation_accuracy（现状基线 0.6875, 11/16）。
   - T3：元素边界 + policy 准确率对 gold / 人审 element_expectations；
     issue-05 / issue-06 的残留扫描清零作为硬门禁。
2. 晋升条件：ai_raw 路线 ≥ code_raw 路线，且 merged 路线 ≥ 两者。
3. merged 与 code_raw 的差异必须逐条可解释：
   changed_from_code=true 或 explicit_noop_with_reason（沿用 issue-09 门禁口径）。
4. 验收不得只看 PASS/SIGNABLE；必须含代表性残留扫描 + 反例验证
   （AGENTS.md 最高优先级纪律）。
```

## 回退语义

```text
1. 每阶段独立开关（per-stage flag），默认关闭，晋升门禁通过后才默认开启。
2. AI NOT_AVAILABLE（未运行）→ deterministic 权威，route 标注 NOT_AVAILABLE。
3. AI abstain（运行了但无证据）→ deterministic 权威，abstain 语义与
   NOT_AVAILABLE 严格区分（issue-07 已修正占位语义）。
4. AI 与 deterministic 字段级冲突且无 gold 可裁决 → conflict 上报 manual_review，
   该字段回退 deterministic 值，不阻塞整体产物。
```

## 风险与非目标

风险：

```text
1. gold / 人审标准不完整时，晋升门禁可能高估 AI 准确率（stage-standards issue-01）。
2. vision 模型（MiniMax M3）输出方差；需缓存 + 固定 prompt 版本 + 重放验证。
3. render 不可用（projection_fallback）时 T4 vision 断链；回退语义必须覆盖。
4. 三路线统一评测器未实现前，晋升判断只能手工比对，效率低且易漏。
```

非目标：

```text
1. 本轮不翻转 T2（保持 merge）。
2. 不移除 deterministic 代码路径；它永久保留为校验方和兜底。
3. 不改变 agent default-off 的默认配置，直到对应阶段晋升门禁通过。
```

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-03 | 初稿：基于三个质量问题与用户三项决策，确立 T4/T3 先行、T2 保持 merge 的分阶段 AI 为主迁移方向 |
