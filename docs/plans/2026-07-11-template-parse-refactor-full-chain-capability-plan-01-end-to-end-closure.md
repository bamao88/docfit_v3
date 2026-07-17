---
status: implemented_in_part
owner: template-generation
stage: full-chain
topic: remaining-capability-closure
doc_type: plan
plan_id: TEMPLATE-GENERATION-FULL-CHAIN-PLAN-01
source_issue:
  id: TEMPLATE-GENERATION-FULL-CHAIN-ISSUE-01
  doc: docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-issue-01-remaining-end-to-end-gaps.md
created: 2026-07-11
last_updated: 2026-07-13
related_plans:
  - docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-plan-03-full-chain-three-route-evaluator.md
  - docs/plans/2026-07-10-template-parse-refactor-t1l1-input-contract-plan-08-l1-projection-bundle-gate.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-10-t4-ai-primary-layout-consumption.md
  - docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md
---

# 模板生成全链路能力闭环 Plan 01：端到端执行与诊断闭环

## Plan Ledger

- Plan status: ACTIVE
- Session scope: template-cli-entrypoints
- Parent plan: none
- Child plans: Plan 08 已在独立 session 验证完成；T3 Plan 06 仍待执行
- Last updated: 2026-07-13
- Current slice: MINIMAL_LIVE_VERIFIED — CLI 入口、本地验证和最小 T2/T3/T4 live stage 通路已完成；全链质量仍停留在 implemented_in_part。
- Next action: 基于 Plan 08 已验证的 sealed L1，继续收敛 T3 residual、object binding、route replay 和 AI-primary 晋升门禁。
- Blocked on: none for minimal live stage validation; remaining blockers are tracked capability/quality gaps, not missing API credentials.
- Do not touch from this session: Plan 08 的 L1 消费迁移、T3 Plan 06 质量改造、entropy-cleanup 之外的历史清理。

## Summary

本计划闭环 `TEMPLATE-GENERATION-FULL-CHAIN-ISSUE-01` 中记录的跨阶段剩余能力。实施分两批，但 issue 关闭必须以两批全部通过为准：

```text
Batch A:
  一行全流程入口、post-T6 gap 自动证据、full_summary、真实 render/L1 底座、T3 真实残留门禁。

Batch B:
  T5/T6/T7/post-T6 三路线隔离重放、T4 section/page-numbering 执行消费、
  配置开启的 AI observation、AI-primary 晋升门禁和回退证据。
```

## Execution Contract

### Target Capability

```text
source DOCX -> T1/render -> sealed L1
  -> T2/T3/T4 code + AI semantic routes
  -> T5 L1-bound merge
  -> T6 L1-resolved exact execution
  -> T7/post-T6/judge diagnosis
```

完成后，L1 必须既是 T2/T3/T4 唯一的事实判断输入，也是 T5/T6/T7 受限使用的身份、执行和验证底座。任何 route 都必须能沿同一 L1 hash 从源事实追踪到最终 Word，且下游不得重新建立事实坐标或补猜上游语义。

### Non-Goals

1. 不在 L1 输入迁移中顺带修改 T2/T4 判断质量或 T5/T6 动作语义。
2. 不把学校标准、gold、judge 结果或 AI proposal 写入 L1。
3. 不用 T7/post-T6 报告修补生成产物或掩盖上游错误。
4. 不在 AI-primary 门禁通过前改变默认 deterministic/merged 路线。

### Completion Signals

1. Plan 08 的 Migration Complete Definition 全部满足并标记 `verified`。
2. T3 Plan 06 的 span identity 从 L1 经 decision、T5、T6 manifest 到最终 DOCX 全链可回查。
3. T5/T6/T7 使用同一 sealed L1；T5 不补猜语义，T6 不重建 mapper 或扩大动作范围，T7 不反向改写产物。
4. 三校 code_raw/ai_raw/merged route 的 L1/T2/T3/T5/T6/T7/post-T6 证据可隔离、可比较、不可静默串线。
5. 错误 source hash、悬空身份、越界 span、缺视觉和 unavailable route 均按契约失败、unknown 或 NOT_AVAILABLE，不静默 fallback。
6. 三校真实 full summary、residual、反例、standard judge、route-eval 和最终 Word 同时满足各阶段门禁。

### Anti-Degradation Rules

1. L1 artifact 存在、coverage 非空、单测通过或单次 replay 成功不等于迁移完成。
2. T2/T3/T4 改读 Adapter，但 Adapter 仍以旧 packet 或私有 index 为权威，不算统一输入。
3. T5/T6 复制 L1 字段后维护独立 run/span/source 映射，不算身份贯通。
4. T6 绑定失败后退化成 source_seq/整段删除或替换，不算可执行闭环。
5. T7/post-T6 只能报告 mismatch，不能用报告状态替代最终 Word 和真实残留验收。

## Public Interfaces

```text
docfit template generate --template <source.docx> --out <run> [--ai off|live|replay|bundle]
docfit template stage t2|t3|t4 --run <template-generate-run> --out <stage-run> [--ai live|replay|bundle]
docfit template verify --school <school> --template <source.docx> --out <full-run> [--ai off|live|replay|bundle]
docfit template inspect --run <run> [--stage t1|l1|t2|t3|t4|t5|t6|t7]

Compatibility aliases:
  docfit eval template-generate
  docfit eval template-observe
  docfit eval template-generation-full
  docfit eval template-generation-judge
```

统一 AI 模式：`off` 为确定性；`live` 为真实 API；`replay` 消费固定 transcript；
`bundle` 消费已有 observation bundle。`--llm` 仅作为 `--ai live` 的兼容简写。

阶段入口优先消费已有 run 的 T1/L1/render/upstream artifact。T3 默认要求固定 T2 route 或
显式 artifact；只有 `--with-upstream` 才允许补跑 T2，并把补跑、hash、model、API/cache/error
写入 `run_manifest.json`。inspect 永远只读，不生成、不调用 API、不修补缺失产物。

固定输出：

```text
eval_runs/template_generate/
eval_runs/template_gap/
eval_runs/template_generation_judge/
full_summary.json
full_summary.md
```

`template-generation-judge` 默认在同一 run root 发现或派生 post-T6 `template_gap_report.json`；`--no-derive-template-gap` 保留只读诊断模式。

## Implementation

1. 新增 full-chain 编排入口。
   - 依次运行 template-generate、template-gap、template-generation-judge。
   - 任一阶段 UNKNOWN/FAIL 时继续产出后续可诊断报告。
   - 汇总 `full_summary.json/md`，包含阶段状态、最终 gap、first_bad_stage、route 缺口、owner、next verification、render/L1/T3/T4/AI-primary gate。

2. 补 post-T6 gap 自动证据。
   - judge 若未发现 `template_gap_report.json`，使用当前 run 的 `fillable_template.docx` 和同 school/version 标准派生 gap。
   - 派生输出写到 run root 的 `eval_runs/template_gap/` 或 judge 输出旁的 `template_gap/`，不覆盖原始 template-generate run。

3. 提升 render/L1 为默认证据底座。
   - 默认生成 L1 时构建 render packet；缺 `soffice/pdftoppm/pdftotext` 时记录 UNKNOWN 环境原因。
   - 保持 T1/L1 禁止语义字段边界；T2/T3/T4 通过只读 L1 projection/adapter 消费事实。
   - T5 通过 sealed L1 校验 hash、identity 和 source trace，不根据 L1 补猜语义。
   - T6 通过 sealed L1 resolver 校验源 package 和精确动作前置条件，不重建独立 mapper 或扩大 fallback。
   - T7 以 L1 + T5/T6 + 最终 DOCX 做 expected-vs-observed 对账和 owner 归因；POST_T6 仅把 L1 用于诊断。

4. 新增 T3 真实残留门禁。
   - 扫描 `03.2_t3_merged_element_spec.yaml` 和最终 DOCX 可见文本。
   - 覆盖 issue-05 格式说明残留、issue-06 placeholder-like 残留、反例保留理由。
   - 诊断进入 full summary 和 standard judge route eval 的四层报告。

5. 补齐三路线与 AI 权威化。
   - 对 code_raw、ai_raw、merged 隔离物化 T5/T6/T7/post-T6 证据。
   - `NOT_EVALUABLE` 只允许表达阶段契约级 out-of-scope，必须带 reason/evidence。
   - accepted T4 section/page-numbering hint 升级为一等字段；有效动作或 explicit noop 都要写 build_manifest 证据。
   - 生成 `ai_primary_gate_decision`；T3/T4 只有在三校 route-eval 满足 `ai_raw >= code_raw` 且 `merged >= both` 后才允许默认 AI-primary。

## Test Plan

```text
uv run pytest tests/unit/test_template_generation_input_contract.py tests/contract/test_template_generation_standard_judge.py -q
uv run pytest tests/contract/test_template_generation_full_chain.py -q
uv run pytest tests/contract/test_template_generate_agent_replay.py -q
uv run pytest tests/unit/template_generation_agent -q
```

真实三校验收：

```text
for school in hunannongye nannong-undergraduate pku-graduate:
  uv run docfit eval template-generation-full \
    --school $school \
    --template inputs/targets/$school/raw/source_template.docx \
    --out /private/tmp/docfit_full_chain_$school
```

通过条件：

```text
1. 三校均产出 template_generate、template_gap、template_generation_judge、full_summary。
2. POST_T6.merged 绑定真实 gap 证据。
3. L1 render 为 real_render，或 UNKNOWN 且带环境/依赖原因。
4. object binding gap 清零，或逐项有审计理由。
5. T3 8/66 残留清零，或逐条有保留理由；反例不误删。
6. 配置开启 AI observation 时，T2/T3/T4 ai_raw 为 AVAILABLE 或 explicit_noop_with_reason。
7. AI-primary 未通过三校门禁前保持关闭并记录回退证据。
8. Plan 08 的输入统一、身份贯通、旧链清零、迁移等价和真实闭环五类完成标准全部通过。
9. T5/T6/T7 均绑定同一 L1 hash；manifest 能回查 resolver/precondition/action/result，错误绑定反例无整段 fallback。
10. L1 到最终 DOCX 的 trace 可由 T7/judge 对账；学校标准、gold 和 judge 结论未进入或反写 L1。
```

## Assumptions

```text
1. 完整 `template generate` / `template verify` 默认 `--ai off`；
   显式 `--ai live` 时运行 T2/T3 文本 API 和 T4 视觉 API。单阶段
   `template stage t2|t3|t4` 默认 live，也支持 replay/bundle；`--llm` 仅是兼容简写。
2. 正式三校验收环境必须安装 soffice、pdftoppm、pdftotext。
3. T1/L1 不输出 unit_id/policy/confidence/is_toc_entry 等下游语义判断字段。
4. route replay 派生产物只写 judge/eval 输出目录，不反写 template-generate 原始 run。
```

## Progress

```text
2026-07-11:
  已实现：
    - 新增 docfit eval template-generation-full。
    - 新增 run_template_generation_full_eval Python API。
    - template-generation-judge 默认派生 post-T6 template-gap；支持 --no-derive-template-gap。
    - 默认生成 render packet 并纳入 L1 coverage；render_error 进入 full_summary。
    - 新增 full_summary.json/md。
    - route-eval 后段 code_raw/ai_raw 不再用“未实现” NOT_EVALUABLE 占位：
      可物化的 T5 写 route replay artifact；不能物化的路线写 OUT_OF_SCOPE/NOT_AVAILABLE reason。
    - T4 section_profile_hint/page_numbering_hint 进入 global_spec/template_spec/build_manifest
      的 explicit noop 消费证据。
    - T3 residual gate 接入 route-eval/full_summary。
    - AI-primary gate 默认保持 merge，并输出 T3/T4 晋升阻断理由。
    - 新增 `--llm` 简化入口和 `template-observe --stage t2|t3|t4`
      单阶段 live API 入口；T3 缺上游时自动先跑 AI T2。
    - T4 live observation 正式接入 MiniMax 逐页视觉 responder；无 real_render
      时单阶段命令明确失败。
    - 新增 canonical `docfit template generate|stage|verify|inspect`，统一
      `--ai off|live|replay|bundle`；旧 eval 入口保留并显示迁移提示。
    - stage 优先复用已有 run，T3 默认固定 T2 route/产物；只有
      `--with-upstream` 才补跑 T2，且不改写源 run。
    - generate/verify/stage 写 `run_manifest.json`，包含 source/render/L1/upstream hash、
      provider/model、API 调用数、cache hit、failure 和输出产物。
  已验证：
    - uv run pytest -q -> 336 passed。
    - CLI/API 默认收敛后 `uv run pytest -q` -> 304 passed（同期旧测试面清理后的当前全量）。
    - `template-observe --help` 明确 T2/T3/T4 live 阶段口径；
      `template-generate --help` 明确 `--llm` 为显式开关且默认 offline。
    - 完成 manifest provenance 审计后当前全量 `uv run pytest -q` -> 316 passed。
    - verify 根 manifest 继承嵌套 generate 的 source/render/L1/API trace；run-backed stage
      在源 Word 已移动时仍从 T1 facts 保留 source template hash。
    - demo-school 真实 `docfit template generate` -> `UNKNOWN`（质量门禁），但完整产出
      编号产物和 run manifest；manifest 证明 `ai_mode=off`、`api_call_count=0`、
      source/render/L1 hash 齐全。`template inspect --stage t3` 只读列出三路线产物。
    - 三校 template-generation-full 均产出 eval_runs/template_generate、
      eval_runs/template_gap、eval_runs/template_generation_judge 和 full_summary。
    - 2026-07-13 最小 live stage 验证完成：
      - 本轮新增统一 live API provider 配置层；`template stage` 与
        `generate/verify --ai live` 共用同一套 text/vision provider 编排。
      - demo-school 离线 run：
        `/private/tmp/docfit_live_min_t2t3t4.0BavJ1/template_generate`，
        `render_status=real_render`，页图数 1，
        `source_render_hash=sha256:da8bfa2f9ffb9a2d082b62bc93a814dbaca68fbbfb14ce44bbb3af5e1f548830`。
      - T2 live：
        `/private/tmp/docfit_live_min_t2t3t4.0BavJ1/stage_t2`，
        provider Kimi，model `kimi-for-coding`，API calls 1，cache 0，failures 0。
      - T3 live：
        `/private/tmp/docfit_live_min_t2t3t4.0BavJ1/stage_t3`，
        pinned upstream T2 artifact from stage_t2，`ran_upstream_t2=false`，
        provider Kimi，model `kimi-for-coding`，API calls 3，cache 0，failures 0。
      - T4 live：
        `/private/tmp/docfit_live_min_t2t3t4.0BavJ1/stage_t4`，
        provider MiniMax，model `MiniMax-M3`，API calls 1，cache 0，failures 0。
      - Verification:
        `uv run pytest tests/unit/template_generation_agent -q` -> 142 passed；
        `uv run pytest -q` -> 318 passed。
  仍未质量闭环：
    - Plan 08 已于 2026-07-11 验证：L1 输入统一、T5/T6/T7 受限消费、旧链退出、三校 live 无明显回退和固定 replay 等价均已闭环。
    - 三校 full_summary 仍为 FAIL，first_bad_stage=T3。
    - T3 residual gate 仍暴露格式说明/placeholder-like 残留。
    - nannong/pku 仍有 object binding gap；pku render fallback 带 LibreOffice 转 PDF 失败原因。
    - 未配置 AI observation 时 ai_raw_not_available 仍按预期阻断 AI-primary。
    - 本轮只完成最小 Kimi / MiniMax live 通路验证；尚未用三校真实质量门禁证明 AI route 可晋升。
```
