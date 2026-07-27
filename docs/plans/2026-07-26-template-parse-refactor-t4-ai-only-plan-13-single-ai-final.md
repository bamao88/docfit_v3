---
status: superseded
owner: template-generation
stage: T4T5T6T7
topic: t4-ai-only
doc_type: plan
plan_id: T2T3T4-AGENT-PLAN-13
source_issue:
  id: T2T3T4-AGENT-ISSUE-13
  doc: docs/plans/2026-07-26-template-parse-refactor-t4-ai-only-issue-13-multi-route-authority-conflict.md
previous_plan:
  id: T2T3T4-AGENT-PLAN-12
  doc: docs/plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-plan-12-exclusive-contiguous-page-contract.md
related_status:
  - docs/status/closed/t4-ai-only-route.md
created: 2026-07-26
last_updated: 2026-07-26
---

# T4 Plan 13：唯一 AI Final

> 2026-07-26：本计划已完成 AI-only 代码清理，但当前产品决定改为暂停并跳过 T4。
> 后续迁移以 Plan 14 为唯一执行契约；不得继续补 T4 live/gold 或恢复其 required final。

## Execution Contract

### Target Capability

T4 只由 AI 判断 section、页面设置、页眉页脚、页码和编号；程序把一份 AI
observation 严格绑定到 sealed L1/render，物化并发布唯一 `04_global_spec.yaml`。

### Non-Goals

- 不在本轮优化 T4 prompt 的学校级准确率。
- 不修改 T2 页面分组或 T3 层级动作算法。
- 不允许用 Code fallback 保持 T4 availability。
- 不用单次 replay 代替三校 live/gold 质量验收。

### Implementation Checklist

1. 新增 T4 AI final publisher，校验 artifact、L1/render hash、section/source identity、
   source range 和 page evidence。
2. 删除确定性 T4 semantic builder、Code/Merged 候选及 runner merge。
3. 让 live/replay responder 都实际调用 T4 AI 输出；无真实 render 时 abstain。
4. 删除旧 T4 bridge、pass plan、comparison、manual review、reconciler、hint 和 route
   replay。
5. 更新 standalone T4、CLI、输出清单、judge 和 canonical route evaluator。
6. 更新测试、current/status/index，并扫描旧符号。

### Completion Signals

- AI raw 和 final 是唯一 T4 生产产物。
- AI success、abstain、跨 run 三类合同测试通过。
- 完整 template-generate 能证明 final lineage 与 availability。
- judge 只暴露 T4 `ai` route。
- 生产代码没有旧 T4 Code/Merged/hint/bridge 读取者。

### Anti-Degradation Rules

- 禁止从 T1/L1 facts 独立构造 section profile 作为 T4 fallback。
- 禁止保留隐藏的 compatibility writer 或自动读取旧 `04.0/04.1.5/04.2`。
- 禁止把 schema 完整、文件存在或安全 shell 当作 `AVAILABLE`。
- 禁止把 identity binding 代码扩张成第二套布局语义判断。

### Verification Matrix

| Gate | Command / Evidence | Required Result |
| --- | --- | --- |
| unit | T4 materializer/publisher/observation pipeline tests | AI-only、abstain、hash mismatch 均符合合同 |
| contract | template-generate、bundle/replay、standard judge tests | 只写 raw + final，T4 route 仅 `ai` |
| propagation | T5/T6/T7 final-chain tests | `NOT_AVAILABLE` 保守向下传播 |
| residual | `rg` 扫生产代码旧 artifact/bridge/hint 符号 | 零生产引用 |
| quality | 三校 T4 gold + live + judge | 后续必须独立闭环，当前不作为代码清理完成声明 |

### Implementation Result

- T4 raw/final、AI success/abstain/cross-run、完整生成、bundle/replay、judge 和下游合同
  相关测试共 `249 passed`。
- `src` 与 `tests` compileall 通过。
- 生产代码的旧 T4 artifact、Code/Merged builder、hint/bridge、route replay 符号扫描
  为 0，已删除模块的 import 扫描为 0。
- 代码清理和合同迁移已完成；三校 gold/live/最终 Word 质量仍按 Residual Policy 单独
  验证。

### Residual Policy

代码和合同清理通过后，本计划保持 `implemented_in_part`，直到 T4 canonical gold、
三校 live layout accuracy 和最终 Word 版式效果完成验证。任何准确率残留继续写入关联
status，不恢复 Code/Merge 路线。
