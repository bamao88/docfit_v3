---
status: implemented_in_part
owner: template-generation
stage: T2T5T6T7
topic: unit-pagination-consumption
doc_type: plan
plan_id: T2T3T4-AGENT-PLAN-11
source_issue:
  id: T2T3T4-AGENT-ISSUE-11
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-11-unit-pagination-signal-loss.md
supersedes:
  - docs/plans/template-parse-refactor-t2-visual-pagination.md
related_contract:
  - docs/current/template-generation-stage-contracts.md
related_full_chain_plan:
  - docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-plan-01-end-to-end-closure.md
created: 2026-07-03
last_updated: 2026-07-17
---

# T2/T5/T6 Plan 11：单元分页策略权威消费闭环

## Summary

把单元分页从“标准里有、运行产物可能为空、T6 偶尔消费机械证据”改成一条可证明的权威链：

```text
L1 页面/OOXML事实
  -> T2 code_raw / ai_raw / merged 识别四维分页语义
  -> T5 无损合并进 template_spec
  -> T6 只从 T5 生成分页/独占页/keep 动作
  -> build_manifest 保留来源与执行结果
  -> T7 / judge / POST_T6 分层验证
```

本计划不再恢复旧的 T4 `page_policy_hint` 设想。单元分页语义归 T2；T4 只提供 section、页眉页脚、
页码等全局物理规则。机械事实是 T2 的高置信证据和冲突校验方，不是 T6 的旁路输入。

## Execution Contract

### Target Capability

完成后，系统必须具备以下能力：

1. 对每个 T2 单元输出 `page_break`、`page_isolation`、`allow_multi_page`、`keep_together`，未知就显式 unknown。
2. code/AI/merged 三条 route 在同一 L1 identity 上独立产出并调和分页策略，保留来源、置信、证据和冲突。
3. T5 无损保留 T2 分页策略并把它作为 T6 唯一分页语义输入。
4. T6 把已确认策略转换成幂等、可回查的 Word 动作；不能执行的策略进入 review，而不是静默忽略。
5. judge 能在 T2 首次识别错误、T5 汇总丢失、T6 动作缺失或最终 Word 未生效时分别归因。

### Canonical Contract

继续沿用 signed standard 和现有产物中的 `units[].page`，不新建并行 `pagination` 对象：

```yaml
page:
  page_break: document_start | true | false | unknown
  page_isolation: true | false | unknown
  allow_multi_page: true | false | unknown
  keep_together: true | false | local_groups_only | unknown
  decision:
    origin: mechanical_fact | ai_observation | both | unknown
    confidence: low | medium | high
    evidence_refs: []
    conflict_status: none | conflict | unresolved
    proposal_ids: []
```

语义约束：

- `page_break` 表示单元是否必须从新页开始；`document_start` 不生成动作。
- `page_isolation` 表示本单元结束后，**下一个单元**必须从新页开始；它不自动要求本单元与前一个单元分开。
  `page_break=true + page_isolation=true` 才表示前后边界都隔离。该语义与南农“原创性声明后连续授权声明、
  授权声明后再隔离目录”的 signed standard 保持一致。
- `allow_multi_page` 是容量约束，不单独生成动作；它约束 keep/isolation 的执行方式和 review。
- `keep_together=true` 仅用于可在一页内的原子单元；`local_groups_only` 只保护局部段落/表格组。
- source 中未发现显式 break 只能得出“无机械证据”，不能直接推断 `page_break=false`。
- 迁移期 `page_start` 和 `page.page_policy.generation_policy` 只能由 canonical `page` 派生，不能继续独立写入或作为权威判断；迁移测试必须保证投影一致。

### Non-Goals

1. 不修改 T2 单元边界/标签识别本身。
2. 不处理 T4 页码、页眉页脚、编号和样式优化。
3. 不让 normal generation 读取学校 standard/gold；standard 只用于开发和验收。
4. 不在本计划内完成所有 T6 `generation_model` 依赖迁移；只消除分页动作对该中间模型的依赖。
5. 不把 LibreOffice 分页当 Microsoft Word 真值；它只作为可重复的近似回归，最终 Word 证据仍按现有产品口径记录限制。
6. 不以 prompt/模型调参提升 AI 准确率为主要目标；本轮先保证合同、消费和归因成立。

### Completion Signals

必须同时满足：

1. 三校 T2 merged 每个单元都有完整 canonical page 或显式 unknown；不存在空 `{}` 和隐式默认冒充策略。
2. T2 AI contract 正式包含四个分页维度，matching unit range 仍能单独产生 page policy proposal/noop trace。
3. T5 对 T2 page/decision/flags 做逐单元 hash 或结构等价检查；任一丢失会在 T5 FAIL。
4. T6 pagination planner 的输入来自 `template_spec.units[]`；相关代码残留扫描不再发现从
   `generation_model.data.units[].page` 读取分页语义。
5. 每个非 unknown 策略都有 `executed`、`no_action_required` 或 `manual_review` 结果，并在 manifest 保留
   `origin/evidence/proposal_ids`。
6. T2 standard verifier 能把当前湖南农大“16 个空 page”判为 FAIL；实现后四维 page policy 与 signed standard
   的 expected vs observed 可逐单元查看。
7. 三校真实生成、judge、route-eval、最终 DOCX OOXML/渲染检查通过本计划矩阵；已有机械分页位置无重复副作用。

### Anti-Degradation Rules

1. 禁止只把 page 字段从 T2 复制到 T5，却不让 T6 消费。
2. 禁止只新增 action/manifest 字段，却不验证最终 DOCX。
3. 禁止用 `page_start=preserve_source_flow`、artifact 存在、`PASS/SIGNABLE` 或单个 replay 替代分页语义正确。
4. 禁止把 AI 未识别、证据不足或 code/AI 冲突静默降为 `false`。
5. 禁止让 T4 重新拥有单元分页判断，或让 T6 基于 L1/机械事实重新推断 T2 语义。
6. 禁止为了三校变绿修改 signed standard；生成逻辑不得读取 standard。

## Current Consumption Map

| 层 | 当前输入/输出 | 当前消费情况 | 计划后的责任 |
| --- | --- | --- | --- |
| T2 code | L1 break facts -> `structure_candidates.units[].page` | 仅有机械 break 时非空 | 输出 canonical page；无证据显式 unknown。 |
| T2 AI | L1 page facts -> `ai_unit_observation.items[]` | prompt/schema/bridge 没有正式 page contract | 输出 evidence-bound page decision；独立 proposal。 |
| T2 merged | proposal -> structure candidates -> unit_map | 只调和 unit/range | 调和 unit/range 与 page，但两个 proposal 维度解耦。 |
| T5 | unit_map -> template_spec | 被动复制，不校验 | 无损合并 + flags/conflicts + hash/结构门禁。 |
| T6 planner | generation_model -> plan | 绕过 T5；只读 before-unit break | 分页动作只读 template_spec canonical page。 |
| executor/manifest | plan -> DOCX/manifest | page/section break；摘要丢 provenance | 支持 isolation/keep；保留 policy/action/result trace。 |
| verifier/judge | unit order/page_start/action success | 四维分页不受检 | 分层检查 T2 识别、T5 保留、T6 执行和 Word 结果。 |

## Implementation Phases

### Phase 0：先把假绿变红，锁定 canonical contract

目标：在修改生产逻辑前，让当前湖南农大空 page 明确失败。

改动面：

- `src/docfit/template_generation/t2_standard.py`
- `src/docfit/harness/template_generation_stage_verifiers.py`
- `src/docfit/harness/template_generation_judge_reports.py`
- `src/docfit/template_generation/verifier.py`
- 对应 unit/contract tests

工作项：

1. T2 standard audit 按 `unit_id` 比较四个 page 字段，报告缺失、值不一致和 unknown；启用已有
   `t2_page_policy_mismatch` 诊断类型，删除仅存在映射却无生产者的死表象。
2. `_verify_t2_unit_map` 检查 canonical page shape；`page_start` 非空不再等于分页策略完整。
3. route-eval 的 T2 AI accuracy 除 unit precision/order 外，增加 page field coverage/accuracy/conflict 指标。
4. 添加当前真实复现的最小合同用例：空 page + 正确 unit order 必须 FAIL，而不是 SIGNABLE。

Stop gate：若 signed standard 的四个字段无法统一解释为 canonical contract，先修标准 schema/文档契约，
不得继续给 T6 写启发式映射。

### Phase 1：T2 code/AI/merged 正式生产分页策略

改动面：

- `src/docfit/template_generation/structure_candidates.py`
- `src/docfit/template_generation/artifacts.py`
- `src/docfit/template_generation/agent/prompt_templates/t2_output_contract.txt`
- `src/docfit/template_generation/agent/prompt_templates/t2_rubric.txt`
- `src/docfit/template_generation/agent/observation_schema.py`
- `src/docfit/template_generation/agent/observation_materialize.py`
- `src/docfit/template_generation/agent/observation_bridge.py`
- `src/docfit/template_generation/agent/schema.py`
- `src/docfit/template_generation/agent/reconciler.py`
- `src/docfit/template_generation/agent/overlay.py`

工作项：

1. code_raw 把机械 break、render page position 和不确定性整理成 canonical page；机械缺失时写 unknown，不写 false。
2. T2 AI output contract 明确要求四个 page 字段、confidence 和 L1 evidence refs；materializer 校验枚举、证据绑定和
   `page_isolation/allow_multi_page/keep_together` 的一致性。
3. 在 **T2** proposal schema 新增 `page_policy_candidates/page_policy_candidate`；不恢复 T4 page hint。
4. `_bridge_t2` 分开比较 boundary 与 page：unit_id/range 相同只能让 boundary noop，page decision 仍要生成
   proposal 或 explicit noop。
5. reconciler 规则：
   - 机械 true + AI true -> `origin=both`；
   - 机械 true + AI false -> 保留 true，记录 conflict/manual review；
   - 无机械证据 + AI medium/high 且证据绑定 -> 接受 AI；
   - 无机械证据 + AI low/unknown -> canonical unknown；
   - code/AI 都不能证明 false 时不得默认 false。
6. overlay patch canonical page 后，通过既有 regenerate 路径重建 `unit_map`；decision trace 必须进入 merged artifact。

Stop gate：若 page proposal 无法唯一绑定到 T2 unit/source_seq，必须留在 open questions，不得按 unit label 猜测 patch。

### Phase 2：T5 无损合并，消除 page 语义双写

改动面：

- `src/docfit/template_generation/artifacts.py`
- `src/docfit/template_generation/runner.py`
- `src/docfit/template_generation/verifier.py`
- `src/docfit/template_generation/outputs.py`

工作项：

1. `build_template_spec` 原样保留 canonical page、decision、conflicts 和 page review flags。
2. T5 verifier 按 unit identity 检查 T2->T5 page 结构等价；字段丢失、类型变化或 origin/evidence 被清空均 FAIL。
3. `page_start` 和旧 `page.page_policy.generation_policy` 改为单向兼容投影，并记录退出条件；禁止两个方向互相回填。
4. 输出/manifest hash 明确绑定最终 T2 merged 和 T5 page policy，便于 route replay 判断哪一层首次变化。

完成信号：T2 merged 与 T5 同 unit 的 canonical page 可机械对账；T5 不产生新的分页判断。

### Phase 3：T6 从 T5 生成并执行完整分页动作

改动面：

- `src/docfit/template_generation/plan.py`
- `src/docfit/template_generation/executor.py`
- `src/docfit/template_generation/word_ops.py`
- `src/docfit/template_generation/manifest.py`
- `src/docfit/template_generation/runner.py`

工作项：

1. pagination planner 改读 `template_spec.units[].page`；`generation_model` 可暂时保留给本计划之外的旧动作，
   但不得再提供 page 语义。
2. 明确 deterministic action mapping：
   - `page_break=true` -> 单元前 page break；`document_start` -> no action；
   - `page_isolation=true` -> 下一单元前边界，按已有边界去重；是否在本单元前断页只由本单元
     `page_break` 决定；
   - `keep_together=true` -> 单元段落 keep-with-next/keep-lines + 表格 row cantSplit；
   - `keep_together=local_groups_only` -> 只保护已识别局部组，不强行锁整单元；
   - `allow_multi_page=true` -> 不做整单元 keep，但仍执行 isolation 的尾边界；
   - unknown/conflict -> 不执行并写 manual review。
3. T2 语义不得自行选择 section break；只有 T4/T5 已绑定的物理 section 规则明确要求时才使用 section action，
   否则默认 page break。
4. 对源 DOCX 已存在的 pageBreakBefore/w:br/sectPr 做幂等检测，区分 `already_satisfied` 与 `inserted`，避免重复分节。
5. manifest 的 page/isolation/keep 记录保留 `unit_id`、canonical policy、origin、confidence、evidence refs、proposal ids、
   action id、precondition、result 和 output ref。

Stop gate：Word 无法可靠执行的 full-unit keep 必须降级为 best-effort + review，不得宣称 hard guarantee。

### Phase 4：分层验收与真实 Word 证明

工作项：

1. T2：signed standard 四字段逐单元 expected vs observed。
2. T5：T2->T5 无损等价和相同 L1/T2 hash。
3. T6：canonical policy -> planned action -> executed action/result 完整链；无动作必须有结构化理由。
4. T7：对 manifest 和最终 OOXML 检查 pageBreakBefore、section 边界、keepNext/keepLines、cantSplit。
5. POST_T6：渲染最终 Word，按 unit page ownership 检查新页、隔离和多页溢出；报告 LibreOffice 与 Word 的证据级别。
6. route-eval：code_raw/ai_raw/merged 分别计算 page coverage/accuracy，merged accepted page decision 必须影响 T5/T6 或记录 explicit noop。
7. silent-drop：T2 page 非 unknown 且 T5/T6 没有等价策略、动作或理由时，`silent_drop_count > 0` 并归因到首次丢失阶段。

## Verification Matrix

| Gate | Command / Evidence | Required Result |
| --- | --- | --- |
| T2 contract/unit | `uv run pytest -q tests/unit/test_t2_unit_map.py tests/unit/test_t2_standard.py tests/unit/template_generation_agent/test_agent_observation_materialize.py tests/unit/template_generation_agent/test_agent_observation_bridge.py tests/unit/template_generation_agent/test_agent_t2_overlay.py` | 四字段 shape、AI materialize、page-only proposal、调和冲突和 explicit unknown 全覆盖。 |
| T5/T6 unit | `uv run pytest -q tests/unit/test_template_generation_artifacts.py tests/unit/test_template_generation_identity_resolver.py` + 新增 page planner/executor tests | T2->T5 无损；T6 只读 T5 page；break/isolation/keep/幂等/provenance 通过。 |
| contract | `uv run pytest -q tests/contract/test_template_generate.py tests/contract/test_template_generation_standard_judge.py tests/contract/test_real_core_generated_template_gap.py` | 空 page 不再假绿；manifest 与最终 OOXML 证据一致。 |
| real samples | 对 `hunannongye`、`nannong-undergraduate`、`pku-graduate` 分别运行 `docfit eval template-generate` 和 `template-generation-judge` | 三校 page policy 可评；无分页 silent drop；已有机械分页无重复副作用。 |
| replay route | 固定同一 L1 的 T2 AI replay，生成 code_raw/ai_raw/merged/T5/T6 | page-only AI decision 能进入 merged 并改变/确认下游；冲突进入 review。 |
| live route（需显式授权） | 至少一校真实 T2 API run + route-eval | ai_raw page coverage 可评，merged 不劣于 code/AI；调用数/模型/成本有记录。 |
| residual scan | 搜索 T6 page planner 对 `generation_model.data.units[].page`、T4 `page_policy_hint`、以 `page_start` 作为完成依据的读取 | 权威消费残留为 0；兼容投影只剩声明过的写入/展示路径。 |
| final Word | OOXML 检查 + 最终 DOCX render/template-gap | page break/isolation/keep 在 Word 结构和页面结果中均有证据；非硬保证项明确 UNKNOWN/review。 |

## Test Scenarios

至少覆盖以下反例，避免按学校/单元白名单修补：

1. 源文档已有 pageBreakBefore，AI 同意：不重复写，origin=both/already_satisfied。
2. 源文档已有 section break，AI 否定：保留机械边界并报冲突，不新插第二个 section。
3. 无机械 break，AI 判新页且证据完整：merged/T5/T6 产生 page break。
4. 无机械 break，AI 低置信：保持 unknown，不产生动作。
5. `page_break=false + page_isolation=true`：本单元可与前一单元连续，但下一单元必须另起页；覆盖南农
   原创性声明/授权声明组合。
6. `page_isolation=true + allow_multi_page=true`：允许单元跨页，但下一单元另起页。
7. `keep_together=true + allow_multi_page=false`：段落/表格保护动作执行；超出一页时报告 best-effort 限制。
8. `keep_together=local_groups_only`：不把长目录/正文整块锁死。
9. unit range 完全相同但 page decision 不同：boundary noop，page proposal 仍被处理。
10. T2 page 正确、T5 人为删字段：T5 verifier FAIL，first bad stage=T5。
11. T5 page 正确、T6 不产 action 且无理由：T6/silent-drop FAIL。

## Dependencies And Sequencing

1. Plan 08 的 sealed L1/page identity 已完成，是本计划输入前提。
2. Plan 11 独立拥有“单元分页语义”闭环，不等待 Plan 10 的 T4 AI layout；T4 只在已有 section binding 上提供物理约束。
3. `template-parse-refactor-t2-visual-pagination.md` 的未完成目标全部收敛到本计划，旧文档标记 superseded，不再并行执行。
4. 实施顺序固定为 Phase 0 -> 1 -> 2 -> 3 -> 4。Phase 0 先建立红灯，避免后续只接字段不接门禁。

## Risks And Defaults

| 风险 | 默认处理 |
| --- | --- |
| 标准 bool/字符串与旧中文字段混用 | canonical 使用 signed standard 现有语义；旧字段单向投影并设退出测试。 |
| 渲染页首不等于“应强制新页” | render 只作 evidence；无足够语义证据保持 unknown。 |
| isolation/keep 没有单一 OOXML 属性 | 拆成可验证原语；不能 hard guarantee 时 best-effort + review。 |
| 页面动作重复破坏版式 | 执行前检测已满足边界，manifest 区分 already_satisfied/inserted。 |
| AI page decision 误覆盖机械事实 | 机械 true 不被 AI false 自动推翻；冲突必须可见。 |
| T6 迁移范围扩大 | 本计划只迁 page planner；其他 generation_model 依赖留给 full-chain plan，不顺手重构。 |

## Residual Policy

1. 任一 phase 只落字段、proposal 或 artifact，但下游未消费，状态必须是 `implemented_in_part`。
2. 未跑三校真实样本、最终 Word 验证或 route-eval 时不得标 `verified`。
3. live API 未授权不阻塞离线实现，但 AI-primary/真实模型能力必须标 `blocked_by=live_t2_authorization`，不能用 replay 替代。
4. 超出本计划的 T2 boundary、T4 layout、T6 全输入迁移残留回写各自既有 issue/plan，不在最终回复中口头搁置。
5. 完成后同步更新 issue 11、issue index、当前阶段契约/运行说明和真实验证证据。

## Planning Loop Review

- Demand gate: **pass**。分页标准已存在且最终 Word 有明确质量影响；这不是新增无需求能力，而是修复已声明能力的断链和假绿。
- Accepted: canonical T2 page contract、T5 单一汇总、T6 从 T5 消费、四维执行映射、分层门禁。
- Rejected: 恢复 T4 `page_policy_hint`；只补 `page_policy_origin`；只让 T5 复制字段；只看 manifest 不验最终 Word。
- Parked: 全量移除 T6 对 generation_model 的其他依赖；AI provider/prompt 准确率专项优化。
- User-review gate: 只有真实 live T2 API 验收需要成本/凭据授权；离线实现和 replay 不需要额外产品决策。
- Saturation status: 当前范围、非目标、阶段顺序、停机门和验收已足够进入用户评审。

## Implementation Status

2026-07-17 状态：`implemented_in_part`。

已落地：

- T2 每个单元输出 canonical `units[].page`；无机械/AI 证据时显式 `unknown`，不再留空 `{}`。
- T2 standard audit 对 signed standard 的四个 page 字段逐单元比较，空 page 触发 `t2_page_policy_mismatch`。
- T2 AI materializer / bridge / schema / overlay 支持 `page_policy_candidates`；单元范围相同但 page decision 不同会走 page-only proposal。
- T5 继续作为 page policy 的唯一汇总事实源，并把 page shape 纳入 verifier。
- T6 pagination planner 改为读取 `template_spec.units[].page`，并生成 page break、isolation 后继断页和 keep-together best-effort action。
- build manifest 保留 `page_policy_results`、page action provenance、proposal ids、evidence refs 和 keep-together 结果。
- route-eval 对 T2 AI observation 增加 page policy coverage / field accuracy；T4 仍明确不评估单元分页。

已验证：

- `uv run pytest -q tests/unit/template_generation_agent/test_agent_observation_eval.py tests/unit/test_t2_unit_map.py tests/unit/test_t2_standard.py tests/unit/test_template_generation_artifacts.py tests/unit/template_generation_agent/test_agent_observation_materialize.py tests/unit/template_generation_agent/test_agent_observation_bridge.py tests/unit/template_generation_agent/test_agent_t2_overlay.py tests/unit/template_generation_agent/test_agent_observation_pipeline.py tests/contract/test_template_generate.py tests/contract/test_template_generation_standard_judge.py`：116 passed。
- `uv run pytest -q tests/unit/template_generation_agent/test_agent_observation_eval.py tests/unit/test_t2_unit_map.py tests/unit/test_t2_standard.py tests/unit/test_template_generation_artifacts.py tests/unit/template_generation_agent/test_agent_observation_materialize.py tests/unit/template_generation_agent/test_agent_observation_bridge.py`：77 passed。
- `uv run pytest -q tests/unit/template_generation_agent/test_agent_t2_overlay.py tests/unit/template_generation_agent/test_agent_observation_pipeline.py tests/contract/test_template_generate.py tests/contract/test_template_generation_standard_judge.py`：39 passed。
- `uv run python -m compileall -q src/docfit/template_generation src/docfit/harness/template_generation_judge_reports.py`：通过。
- 湖南农大真实离线生成：`/tmp/docfit-t2-pagination-impl-20260717-hunannongye`，`02_unit_map.yaml` 中 16 个单元 page 均非空，`05_template_spec.yaml` 无 page 丢失，`06.2_build_manifest.json` 有 16 条 `page_policy_results`。
- 湖南农大 judge：`/tmp/docfit-t2-pagination-impl-20260717-hunannongye-judge-r2`，`t2_unit_pagination=FAIL` 且 finding 为 `t2_page_policy_mismatch`，证明原先“空 page 仍 PASS”的假绿已消失。

未标 `verified` 的原因：

- 仅跑了湖南农大真实离线样本；南农和北大真实样本、最终 Word page OOXML/render 证据尚未全跑。
- 当前离线路径没有 live T2 AI page evidence，多数 page 字段仍是 `unknown`，正确进入 review，但还不能证明学校级分页策略全满足。
- live API route 仍需显式授权；本轮未做真实模型调用。

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-03 | 初稿：page hint、merged 调和、plan 消费、最终页隔离门禁。 |
| 2026-07-16 | 基于当前代码、48 个相关单测和湖南农大真实离线 run 重写：T2 四维 canonical contract、T5 单一汇总、T6 从 T5 执行、judge 假绿修复和最终 Word 分层验收。 |
| 2026-07-17 | implemented_in_part：落地 canonical page、T2 standard/page verifier、T2 AI page proposal、T5/T6 单一消费链、manifest provenance 和 route-eval page 指标；湖南农大真实离线 judge 已从假 PASS 转为 `t2_page_policy_mismatch` FAIL。 |
