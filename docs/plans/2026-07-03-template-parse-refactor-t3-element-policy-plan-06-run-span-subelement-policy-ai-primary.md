---
status: draft
owner: template-generation
stage: T3
topic: element-policy
doc_type: plan
plan_id: T3-ELEMENT-PLAN-06
source_issue:
  id: T3-ELEMENT-ISSUE-06
  doc: docs/plans/2026-07-02-template-parse-refactor-t3-element-policy-issue-06-placeholder-span-granularity.md
also_resolves:
  id: T3-ELEMENT-ISSUE-05
  doc: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-issue-05-inline-style-instruction-fixed-merge.md
previous_plan:
  id: T3-ELEMENT-PLAN-04
  doc: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-plan-04-instruction-manual-confusion.md
blocked_by:
  id: T1L1-INPUT-CONTRACT-PLAN-08
  doc: docs/plans/2026-07-10-template-parse-refactor-t1l1-input-contract-plan-08-l1-projection-bundle-gate.md
contract:
  doc: docs/current/template-generation-stage-contracts.md
related_direction:
  doc: docs/plans/2026-07-03-template-parse-refactor-ai-primary-staged-migration-proposal.md
created: 2026-07-03
last_updated: 2026-07-11
---

# T3 元素策略 Plan 06：L1 run/span/视觉输入与完整元素合并

## Summary

issue-05（行内格式说明并入保留元素，8 处残留）和 issue-06（placeholder/sample 缺少子 span 粒度，66 个非删除元素）共享同一根因：T3 没有贯穿输入、判断、集合、merged 和 T6 执行的稳定 span identity。

2026-07-11 复核进一步确认：当前 T3 prompt 要求按 run/span 拆分，但输入只给整段文字和 run ID 列表，没有 run ID 对应的文字/样式，也没有真正发送页面图片；物化器又按 `source_seq` 互斥，使合法的同段多 span 互相冲突；bridge 最终只 patch `candidate_policy`，丢弃完整 span 语义。

本计划不再给单个残留追加启发式，而是在 Plan 08 完成 L1 唯一输入迁移后，建立 `T3 Stage Input = L1 + 对应 route 的 T2`，并让 code、AI、merged、T6 全链消费同一 run/span 身份。

## Execution Contract

### Target Capability

```text
sealed L1 + corresponding T2 route
  -> T3 run/span/visual stage input
  -> code decisions + AI decisions
  -> span-identity comparison and merged elements
  -> T6 exact span actions
```

完成后必须具备：

1. 同一段落可以包含多个不同 policy 的 span，不被 `source_seq` overlap 清空。
2. T3 输入能按 run/span 回查文字、样式、源位置、page/bbox 和视觉证据。
3. AI 只引用 L1/T3 Stage Input 中存在的身份，不自造权威 element ID 或 content。
4. T3 code、AI、merged 在同一 span identity 上可比较。
5. merged 消费 policy、role、fill/generated/manual、confidence、evidence 和 origin，不只 patch policy。
6. T6 能按 raw run/char range 精确删除 instruction、替换 sample、保留 label 和创建 slot。
7. issue-05/06 真实残留清零或逐条有保留理由，反例不误删。
8. AI-primary 只在三校真实 route-eval 证明不劣后晋升；否则保持 deterministic/merged 回退。

### Dependency Stop Gate

本 plan 在以下条件满足前不得进入实现：

1. Plan 08 的 L1 已在 T2/T3/T4 前封存。
2. `run_index` 可回查 raw/logical run 文字和样式。
3. T3 不再直接读取 render packet/page_text_index。
4. T2 route 输出与 L1 hash 稳定绑定。
5. T5/T6/T7 已具备 Plan 08 定义的 sealed L1 hash/identity resolver/verification input。
6. Plan 08 Gate D 的旧事实读取和重复 mapper 残留为零。

不满足时，本 plan 状态保持 `draft` 或 `blocked_by=T1L1-INPUT-CONTRACT-PLAN-08`。

### Non-Goals

1. 不修改 T2 单元识别质量；只消费对应 T2 route。
2. 不修改 T4 版式识别质量。
3. 不把学校标准或 gold 作为 T3 生成输入。
4. 不默认信任 AI 自由文本或低置信结果。
5. 不在本轮扩展学生内容放置流程。
6. 表格复杂对象若需要新的业务模型，先记录下一轮 issue，不在段落 span 模型中暗补。

### Completion Signals

以下信号必须同时满足：

1. T3 Stage Input 包含 L1/T2/route hash、unit window、source、run/span、object 和 visual availability。
2. 模型看到每个 run/span 的真实文字和有效样式，而非只有 ID 列表。
3. multimodal route 真正发送图片内容；text-only route 明确 `visual_evidence_used=false`。
4. AI 输出以 `span_refs` 为主键，authoritative content 从 L1 确定性重建。
5. span coverage 满足 owned/unknown/contested/explicit-ignore 全覆盖且互斥。
6. 同段 fixed + inline instruction 代表样本产生两个可执行处置。
7. bridge/target guessing/source_seq overlap/policy-only overlay 调用方清零并删除。
8. `03.2_t3_merged_element_spec.yaml` 能逐项证明 accepted decision 的实际消费。
9. T5 保留 span/source/L1 trace，不重新查看 L1 补猜 policy 或动作语义。
10. T6 通过 sealed L1 resolver 精确解析 span/raw run/char range，并在 build manifest 记录 L1 hash、precondition、span action 和执行结果。
11. span 无法绑定、char range 越界或源 package hash 不一致时结构化失败，不扩大到 source_seq/整段 fallback。
12. T7 能沿 `L1 span -> T3 decision -> T5 element -> T6 action -> final DOCX` 对账并归因。
13. 三校真实 residual、反例、standard judge、route-eval 和最终 DOCX 验证通过。

### Migration Complete Definition

本 plan 的“迁移完成”不是 T3 新 schema 或 AI artifact 已生成，而是同一 L1 span identity 已形成可验证的闭环：

```text
sealed L1 span
  -> route-bound T3 Stage Input
  -> code/AI decisions
  -> complete merged element
  -> T5 template spec with unchanged L1 trace
  -> T6 L1-resolved exact action
  -> build manifest + final DOCX
  -> T7/judge expected-vs-observed attribution
```

只有同时满足以下条件才算完成：

1. code、live AI、replay、merged 全部读取同形 Stage Input，并绑定同一 L1 hash 和对应 T2 route hash。
2. 每个 accepted/unknown/contested/ignored span 都能回查 L1；AI 自造或越界身份全部被拒绝。
3. T5/T6 不复制 run/span/source 映射，不丢失或模糊 span identity，也不根据 L1 重新推断策略。
4. 每个执行动作都能从 manifest 回查到 L1 span 和 T3 decision；执行前置条件失败时无扩大 fallback。
5. 三校 issue-05/06 residual、反例、最终 Word 和 route-eval 同时通过；仅 schema、artifact、单测或 replay 成功不算完成。

### Anti-Degradation Rules

1. 只给 element 增加 `spans[]` 字段、下游不消费，不算完成。
2. 只改 prompt、不补 run text/style/visual 输入，不算完成。
3. 只生成 AI observation/proposal/overlay side artifact，不算 merged 完成。
4. 不允许用 `source_seq` 互斥替代 span coverage。
5. 不允许 AI 返回的 content 覆盖 L1 authoritative text。
6. 不允许为提高 coverage 自动执行 low-confidence 或 unbound decision。
7. 不以单个 fixture、replay、artifact `AVAILABLE` 或测试通过替代三校真实残留与反例。
8. 不允许 T5/T6 为消费 span 新建第二套 run/span/source index，或把精确绑定失败降级成 source_seq/整段操作。
9. 不允许 build manifest 只记录 element/action 而丢失 L1 hash、span identity、precondition 和执行结果。

## T3 Stage Input Contract

### Route Binding

| T3 route | 对应 T2 输入 | 不可用时 |
| --- | --- | --- |
| `code_raw` | `T2.code_raw` | 明确 `NOT_AVAILABLE`，不借用 merged |
| `ai_raw` | `T2.ai_raw` | 明确 `NOT_AVAILABLE`，不借用 code/merged |
| `merged` | `T2.merged` | 阻断最终 T3/T5，不伪造权威结果 |

三条 route 必须记录同一 L1 artifact hash。T2 route hash 不同是预期，但不得静默串线。

### Required Input Shape

```text
identity:
  l1_hash / t2_hash / route_id / window_id / unit_id

unit_scope:
  order / source_seq_refs / page_nos / neighbor_context

source_rows:
  source_seq / source_ref / text / style / text_facts / page_no / bbox

atomic_spans:
  span_id / parent_source_seq / logical_run_id / raw_run_ids
  text / effective_style / source_refs / optional char_range

objects:
  object_id / object_type / source binding / page binding

visual_evidence:
  page_image_ref / crop_ref / page_no / bbox / availability / reason
```

T3 Stage Input 是从 L1 和 T2 构造的阶段视图，不是第二套事实源。所有身份必须回查 L1。

## T3 Decision Contract

AI 和 deterministic code 均产出同形 decision：

```text
decision_id
unit_id
span_refs[]
policy
role
confidence
evidence_refs[]
origin
fill_source? / generated? / manual_semantics? / removal_reason?
```

规则：

1. 模型不输出权威 `element_id`；element ID 在确定性物化后生成。
2. 模型不输出权威 content；content 从 `span_refs` 拼接。
3. `fill` 必须有 `fill_source`。
4. `generated` 必须有 `generated.field_type`。
5. `manual_only` 必须有 `manual_semantics`。
6. `instruction_remove` 必须有 removal reason/evidence。
7. 全链统一 canonical policy：`fixed/template_default/fill/manual_only/generated/instruction_remove`。

## Span Collection and Merge Rules

1. 不同 span 共用一个 `source_seq`：合法，不冲突。
2. 相同 span + 相同 policy：dedupe/confirmed。
3. 相同 span + 不同 policy：conflict，进入比较和人工待决/回退。
4. 相邻且 policy/role/条件语义相同的 span：可确定性合成一个 element。
5. 同一 span 需要部分处置：使用 run 内 `char_range`，不得扩大到整段。
6. 每个 span 最终属于 accepted element、unknown、contested 或 explicit ignore。
7. source_seq coverage 只做摘要，不参与元素互斥。

Merged 以 L1 span identity 对 code/AI decisions 对账：

```text
agree      -> confirmed decision
AI adds evidence-bound low-risk span -> accepted after deterministic checks
conflict   -> manual review or configured deterministic fallback
unbound    -> rejected
unknown    -> preserved as unknown, not silently assigned
```

## Implementation Plan

### Phase 0：Plan 08 Handoff

- [ ] 验证 Dependency Stop Gate 全部满足。
- [ ] 记录当前三校 T3 code/AI/merged baseline 和 8/66 residual baseline。
- [ ] 确认 T3 只接收 L1 + T2 route，不保留旧事实 fallback。
- [ ] 确认 T5/T6/T7 的 L1 受限接口已经可用，T6 不再依赖独立 mapper 或整段 fallback。

### Phase 1：Stage Input 与 span identity

- [ ] 建立 T3 Stage Input builder，按 route 生成 unit windows。
- [ ] 从 L1 run index 构造 atomic spans，必要时表达 run 内 char range。
- [ ] 绑定 object/page/bbox/image/crop evidence。
- [ ] 增加 span identity、回查和 coverage schema tests。
- [ ] 可选持久化 debug stage input，但不得成为第二权威事实源。

### Phase 2：确定性 code decisions

- [ ] 将现有 code T3 改为消费 Stage Input spans。
- [ ] 保留既有 policy 语义，先建立同形 span decisions。
- [ ] 字段行拆分 label/layout spacer/sample/input slot。
- [ ] 尾随格式说明按 run/style/text facts 拆为 `instruction_remove`。
- [ ] 保护论文（设计）、卷（期）、百分制、学校固定名称等反例。

### Phase 3：AI text/visual decisions

- [ ] 重写 T3 prompt/schema，输入 run/span 文字、有效样式和视觉 availability。
- [ ] text-only Adapter 明确不使用图片。
- [ ] multimodal Adapter 发送真实页面图/局部 crop，不只传文件路径。
- [ ] AI 只返回 span decisions 和证据绑定。
- [ ] 截断、无效 JSON、缺条件字段或越界身份时降级 unknown/abstain。

### Phase 4：Span Materialization and Merged

- [ ] 用 span coverage 替换 source_seq overlap。
- [ ] 在同一 span identity 上比较 code/AI decisions。
- [ ] 生成完整 merged elements：span refs、policy、role、条件语义、confidence、origin、trace。
- [ ] 删除 element ID 猜测、模糊 target binding、policy-only proposal/overlay。
- [ ] accepted/rejected/conflict 必须逐项解释并进入 manual review/attribution。

### Phase 5：T6 精确执行

- [ ] T5 原样保留 accepted element 的 L1 hash、span refs、raw run 和 char range，不重新推断语义。
- [ ] `inline_instruction/layout_spacer` 生成 run/span 级删除动作。
- [ ] `sample_value` 生成精确替换为 slot 的动作。
- [ ] label/content 保留并维持样式与结构。
- [ ] action 携带 L1 hash、span/raw run/char range 和 element/decision trace。
- [ ] T6 通过 sealed L1 resolver 校验 source package、expected text/style 和 char range 后才执行。
- [ ] binding/precondition 失败时拒绝扩大到 source_seq/整段，并输出结构化 owner/fix evidence。
- [ ] build manifest 记录执行前后证据、resolver/precondition 结果和失败原因。
- [ ] T7 沿 L1/T3/T5/T6 trace 验证动作是否精确落到最终 DOCX。

### Phase 6：质量门禁与 AI-primary

- [ ] issue-05 的 8 处格式说明残留清零或逐项有保留理由。
- [ ] issue-06 的 66 个 placeholder-like 非删除元素清零或逐项有保留理由。
- [ ] 代表性反例零误删。
- [ ] 三校 code_raw/ai_raw/merged 做 span 级 route-eval。
- [ ] 只有 `ai_raw >= code_raw` 且 `merged >= both` 时才允许 AI-primary 晋升。
- [ ] 未通过时保留 deterministic/merged 默认和回退证据。

## Legacy Deletion Ledger

| 旧逻辑 | 替代能力 | 删除条件 |
| --- | --- | --- |
| 旧 T3 evidence / Plan 08 兼容 Adapter | T3 Stage Input | code/AI/replay/live 全部改读 Stage Input |
| AI 自造 `element_id` | span decision + deterministic materialization | prompt/schema/fixture 全部迁移 |
| `source_seq` 级 overlap | span coverage/ownership | 同段多 span 回归通过 |
| `_target_candidate_id` 拼接 | span identity binding | bridge consumer 清零 |
| source_seq 子集模糊 target binding | exact span refs | code/AI compare tests 通过 |
| observation bridge 丢 run identity |同形 span decisions | merged 直接消费 decisions |
| policy 同义映射 | canonical ontology policy | 所有消费者统一枚举 |
| policy-only overlay | full merged element materialization | attribution/manifest 能证明完整消费 |
| low-confidence 自动执行 | confidence/risk/unknown gate | manual review 和 fallback 测试通过 |
| T5/T6 独立 run/span/source mapper | sealed L1 identity resolver | caller 为零，精确绑定与反例通过 |
| source_seq/整段执行 fallback | exact span precondition + structured failure | unbound/越界/hash mismatch 反例通过 |

## Stop Gates

### Gate 0：L1 Ready

Plan 08 未 `verified`，本 plan 不进入实现。

### Gate 1：Span Identity

同段多 span、run 回查和 coverage 不变量未通过，不进入 AI/merged。

### Gate 2：Merged Consumption

accepted decision 未实际改变或确认 `03.2` 权威 element，或未携带同一 L1 span trace 进入 T5，不进入 T6。

### Gate 3：Exact Execution

T6 未通过 sealed L1 resolver 精确绑定、precondition 和失败不扩大反例，或 T7 无法沿 L1/T3/T5/T6 对账，不进入产品质量验收。

### Gate 4：Product Quality

真实 residual、反例和最终 DOCX 未通过，不得标记 `verified` 或开启 AI-primary。

## Verification Matrix

| Gate | Command / Evidence | Required Result |
| --- | --- | --- |
| unit | `uv run pytest tests/unit/template_generation_agent -q` | Stage Input、prompt、span coverage、materialize、merge 单测通过 |
| focused T3 | T3 generation/model/plan/executor 聚焦单测 | 同段多 span、char range、条件字段和精确动作通过 |
| contract | `uv run pytest tests/contract/test_template_generate.py tests/contract/test_template_generate_agent_default_off.py tests/contract/test_template_generation_standard_judge.py -q` | 默认和 AI route 合同不回归 |
| identity execution | T5/T6/manifest/verifier 聚焦测试 | 同一 L1 hash、resolver/precondition、完整 trace 和精确动作通过 |
| negative binding | source hash mismatch、unbound span、越界 char range、expected text/style mismatch | 结构化失败，无 source_seq/整段 fallback |
| deterministic product | 三校 `template-generation-full` 默认 run | code/merged 可复现，无新增上游退化 |
| live text | 三校或代表校 `template-observe --stage t3` | 模型收到真实 run/span 事实，输出可绑定 decisions |
| live visual | 至少一校 T3 multimodal run | 实际发送图片/crop，视觉 evidence trace 可审计 |
| residual | issue-05/06 扫描 + 反例 | 8/66 清零或逐项保留，反例零误删 |
| route-eval | 三校 code_raw/ai_raw/merged | span 级差异可解释；晋升条件有证据 |
| final Word | `template-gap` + 人工聚焦检查 | 指令/sample 不残留，slot/固定文字/样式结构正确 |

## Residual Policy

1. 只完成 Stage Input/span schema：`implemented_in_part`，不能声称质量改善。
2. live provider 凭证或费用不可用：`BLOCKED_NEEDS_LOCAL_VALIDATION`，不能标记 merge-ready。
3. 表格/对象需要独立语义模型：记录新 issue，当前 span 能力不得用段落启发式伪装覆盖。
4. AI 不劣门禁未通过：保持 AI-primary 关闭，记录 fallback，不阻断 deterministic 产品路线。
5. T5/T6 需要第二套 mapper、模糊绑定或整段 fallback：停止在 Gate 3，回到 Plan 08 或创建新的根因 issue，不得在 executor 暗补。
6. 任一真实残留未清零：回写 issue/plan/index，不能只在最终回复说明。

## Plan Ledger

| 日期 | 状态 | 说明 |
| --- | --- | --- |
| 2026-07-03 | draft | 初稿：run/span 子元素、确定性 parser、AI observation、T6 精确执行和全量门禁 |
| 2026-07-11 | draft | 依据 L1/T3 输入审计重写并补齐全链迁移标准：增加 Plan 08 stop gate、T3 Stage Input、真实视觉 Adapter、span coverage、T5/T6 L1 身份消费、精确执行与 T7 对账；撤销“现有 evidence 输入已经具备”的错误假设 |
