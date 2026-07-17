---
status: verified
owner: template-generation
stage: full-chain
topic: entropy-cleanup
doc_type: plan
plan_id: TEMPLATE-GENERATION-ENTROPY-CLEANUP-PLAN-01
source_issue:
  id: TEMPLATE-GENERATION-ENTROPY-CLEANUP-ISSUE-01
  doc: docs/plans/2026-07-11-template-generation-entropy-cleanup-issue-01-stale-surfaces.md
created: 2026-07-11
last_updated: 2026-07-11
---

# 模板生成熵清理 Plan 01：删除旧表面并收敛唯一主线

## Plan Ledger

- status: verified
- current_slice: complete
- next_action: none; parked items require a separate product decision
- blocker: none
- active_capsule: none
- no_touch: full-chain capability closure changes, route replay, T1-L7/POST_T6 diagnostics, current T3/T4 fixes

## Execution Contract

### Target Capability

仓库只保留一条模板生成公共主线、一个权威 run artifact tree 和一套 AI/raw/merged 评测 owner；旧四阶段原型、兼容输出副本和无调用叶子全部删除，已存在的 full-chain 质量能力不降级。

### Non-Goals

- 不删除仍被现役生成器消费的 `source_tree`、`structure_candidates`、`generation_model`、`plan` 内部语义。
- 不删除或重设计 MiniMax vision；当前仅记录为 parked。
- 不删除 Module 2 layered proposal producer；当前 issue index 仍把 bridge/reconciler 作为活跃能力。
- 不以拆大文件、移动 helper、格式化或缓存清理充当概念删除。

### Accepted Cleanup Checklist

- [x] 将 standalone `observation_eval` 中独有的 T2/T3/T4 raw accuracy 和 element expectation 指标迁入 standard judge / route-eval owner。
- [x] 删除 `observation_eval.py`、`observation_tools.py`、无调用 replay/alias/private symbols 及只保护旧表面的测试入口。
- [x] 删除旧 `template/content/placement/render/e2e/coverage/convert` CLI 和相应 orchestrator/stage/harness/test/script surface。
- [x] 消费者清零后删除 `template_artifact` legacy downstream view。
- [x] 以顶层编号文件和 `99_template_generation_debug_index.json` 为唯一 template-generate run artifact tree。
- [x] 删除 `artifacts/` 镜像、timestamp human debug snapshot、manifest debug pointer 和 run-bundle compat fallback。
- [x] 更新 current docs、命令、测试和 stale-path references，只保留历史 plan 中的历史上下文。

### Behavior-Change Policy

- Public removal accepted: 旧 CLI 和旧 artifact path 属于本轮明确批准的删除范围，不保留兼容 alias。
- Public behavior preserved: `template-generation-full`、`template-generate`、`template-gap`、`template-generation-judge` 及其质量诊断语义必须保持。
- Internal cleanup: 无生产调用的 helper、class、module 直接迁移消费者后删除。

### Architecture Simplification Claim

```text
before:
  two public workflow families
  three artifact path families
  standalone + route-eval AI quality owners

after:
  one template-generation workflow family
  one numbered run artifact tree
  one standard-judge / route-eval quality owner
```

### Surface Metrics

- stale public commands: 7 -> 0
- old stage implementations: 4 stage packages -> 0
- template-generate artifact path families: 3 -> 1
- standalone AI evaluation owners: 2 -> 1
- compatibility aliases/wrappers: decrease; no new compatibility surface
- new runtime owners: 0

### Verification Matrix

| Layer | Command / evidence | Required result |
| --- | --- | --- |
| L0 | targeted `rg` import/path/CLI scans; `git diff --check` | stale live references = 0 |
| L1 | focused unit tests for route metrics, run bundle and output writer | PASS |
| L2 | template generate/judge/full-chain contract tests plus full `pytest` | PASS |
| L3 | three real schools through `template-generation-full` | run completes and all required evidence remains; quality FAIL/UNKNOWN may remain only for pre-existing diagnosed gaps |

### Stop Condition

全部 checklist 完成、L0-L3 证据满足、当前 full-chain 未提交能力得到保留，且剩余观察仅为 parked 或低价值项时关闭。任何无法迁移的仓库外公共消费者、真实能力回退或无法解释的新质量差异都立即停止对应切片。

## Campaign State

- Campaign overlay: true
- Discovery source: 2026-07-11 `$intuitive-reduce-entropy` saturation packet
- Current quality signal: cleanup verified; 0 stale commands, 1 output path family, 0 old stage packages, selected no-caller leaves removed
- Architecture pressure: 当前 full-chain 已成为 canonical owner，但兼容层仍让旧产品模型和旧 artifact contract 可达
- Checkpoint cadence: each verified vertical slice
- Clear queue: leaf cleanup -> old workflow removal -> output canonicalization
- Parked registry:
  - fingerprint: `template_generation/agent/observation_vision.py:minimax-vision`
    owner layer: Module 1 observation
    park reason: recent intended T4 vision capability is currently unwired; deletion requires a product decision
    exact unblocker: explicit keep-and-wire or remove decision after full-chain closure
    first seen: 2026-07-11
    last confirmed: 2026-07-11
    do-not-reopen-unless: current plan or user intent changes
  - fingerprint: `template_generation/agent:legacy-layered-producer`
    owner layer: Module 2 bridge/reconciler
    park reason: current issue index still treats layered proposals as an active merged compatibility input
    exact unblocker: Module 1 bridge parity proof and an accepted public flag removal
    first seen: 2026-07-11
    last_confirmed: 2026-07-11
    do-not-reopen-unless: parity proof becomes available
- Rejected low-value registry: big-file splitting, CLI helper extraction, cache/DS_Store cleanup
- Low-value stop signal: next change only moves code or changes formatting without deleting an owner/path/contract

## Checkpoint

- Leaf cleanup value: standalone AI evaluation owners 2 -> 1; 2 modules and unused replay/alias/private symbols deleted.
- Canonical owner: `template_generation_judge_reports.build_template_generation_route_eval_report` now records T2/T3/T4 `ai_raw_accuracy`.
- Focused proof: 21 tests passed across observation metrics, T2 standard audit and standard-judge contract.
- Commit: skipped because canonical owner and tests contain pre-existing uncommitted full-chain changes that cannot be staged independently.
- Old workflow removal value: 7 public commands and the complete `stages/**` runtime family removed; obsolete coverage/product-quality/Word-evidence harness and generators removed with their callers.
- Contract owner move: standard capability validation now belongs to `harness/standards.py`; current template-gap retains only the three-school registry and template baseline loader it consumes.
- Focused proof: CLI help exposes only current template commands; 7 standards/profile, 26 generate/agent/judge and 33 template-gap contract tests passed.
- Output canonicalization value: template-generate artifact path families 3 -> 1；`template_artifact`、`artifacts/` 镜像、timestamp human snapshot、manifest debug pointer、un-numbered final Word 和 reader fallback 全部删除。
- Canonical output proof: 23 focused output/agent/run-bundle contracts passed；测试显式检查旧目录和旧文件不存在。
- Full regression proof: `uv run pytest -q` -> `304 passed in 38.57s`；首次全量中的单个 LibreOffice render 环境波动已单独复跑通过，随后全量干净通过。
- Real-school proof: hunannongye、nannong-undergraduate、pku-graduate 三校 `template-generation-full` 均 exit 0，编号必需文件零缺失，旧路径零残留；三校 quality status 仍为既有 `FAIL`。
- Residual scan: stale CLI、stage import、template artifact、debug snapshot、compat path 和 duplicate final Word reader 引用均为 0；`git diff --check` 通过。
