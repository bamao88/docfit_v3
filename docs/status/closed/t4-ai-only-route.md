---
status: superseded
owner: template-generation
stage: T4/T5/T6/T7
created: 2026-07-26
last_updated: 2026-07-26
plan: T2T3T4-AGENT-PLAN-13
superseded_by: T2T3T4-AGENT-PLAN-14
---

# T4 AI-only 路线收敛

> 本状态记录已被 `docs/status/active/t4-production-skip.md` 取代。AI-only 清理是已发生的
> 历史实现，但不再是当前生产目标。

## 当前结论

T4 生产代码已从 Code/AI/Merged 三路线收敛为单一 AI final。正式运行只保留
`04.1_t4_ai_layout_observation.yaml` 和 `04_global_spec.yaml`；后者只由前者经
identity/evidence/schema materializer 发布。

## Expected vs Observed

- Expected：AI 是唯一 T4 语义主权；程序只验证、绑定和物化。
- 变更前 observed：确定性 `build_global_spec`、AI 候选、merged 候选及
  hint bridge/reconciler 并存。
- 当前 observed：旧生产者、消费者、writer、CLI、route replay 和 bridge 报告已删除；
  AI abstain 或跨 run 输入会发布 `NOT_AVAILABLE`，不会回退 Code。

## 影响

- T5 只读取唯一 T4 final，并保守合并 availability。
- T6/T7 不再看到 T4 route candidate。
- judge 的 T4 route 只有 `ai`；Code/Merged delta 和 hint consumption 已退出。
- 历史 run 中的旧编号文件仅是历史证据，不是当前兼容输入。

## 验证与残留

已实施的验证面：

- T4 raw materialization 和 final publisher 单测；
- AI success、abstain、render/L1 hash mismatch 反例；
- template-generate replay/bundle 合同；
- standard judge canonical route 合同；
- 旧生产符号残留扫描。

2026-07-26 实施证据：

- `uv run pytest -q tests/unit/template_generation_agent tests/unit/test_template_generation*.py tests/contract/test_template_generate*.py tests/contract/test_template_generation*.py`
  → `249 passed`；
- `uv run python -m compileall -q src tests` → 通过；
- 旧 T4 artifact、Code/Merged builder、hint/bridge、route replay 符号及已删除模块
  import 的生产代码扫描 → 0 命中。

仍未闭环：

- 三校 T4 canonical gold 仍需按 AI-only scored universe 复核；
- 三校真实 MiniMax live layout accuracy 和最终 Word 版式效果尚未完成；
- 因此本项状态为 `implemented`，不是 `verified`。

关联 issue/plan：

- Issue 13：`docs/plans/2026-07-26-template-parse-refactor-t4-ai-only-issue-13-multi-route-authority-conflict.md`
- Plan 13：`docs/plans/2026-07-26-template-parse-refactor-t4-ai-only-plan-13-single-ai-final.md`
