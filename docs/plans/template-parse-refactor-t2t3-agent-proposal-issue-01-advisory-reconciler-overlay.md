---
status: draft
owner: template-generation
stage: T2T3
topic: agent-proposal
issue_id: T2T3-AGENT-ISSUE-01
issue_sequence: 1
created: 2026-06-26
last_updated: 2026-06-26
version: 2
review:
  date: 2026-06-26
  summary: 引入 AI 是新变量，探索期目标是测准 AI 能力并区分 AI/代码致因；reconciler 放开语义与闭集关键词，重心在归因而非阻塞。
previous_issue:
  id: none
  doc: none
previous_optimization:
  id: none
  doc: none
  summary: T2/T3 多轮纯确定性优化后，三校单元识别/元素策略仍与 standard 大量 mismatch；本 issue 首次引入 AI 语义提案层作为新方向。
next_plan:
  id: TBD
  doc: TBD
  summary: 基于 Review 建议产出 plan-01。
source_proposal:
  doc: /Users/fl/Documents/Codex/2026-06-26/ai-agent-ai/outputs/docfit-template-generation-agent-driven.md
  summary: AI 提 proposal、确定性 reconciler 校验并应用 overlay、现有 verifier/template-gap 裁判的中间形态方案。
related_issues:
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-03-state-machine-standard-gates.md
  - docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md
related_code:
  - src/docfit/template_generation/runner.py
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/generation_model.py
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/verifier.py
  - src/docfit/ai_rca/packets.py
---

# T2/T3 Agent 提案层 Issue 01：引入 AI 语义提案 + 确定性 reconciler + overlay

## Review 建议（2026-06-26 讨论）

相对初稿的方向修订。细节见下文各节；本节只记录**问题、目标、大方向**。

### 核心问题：AI 是新变量

引入 AI 后，失败不再只有「确定性代码错了」一种来源，还可能是「AI 提案错了」或「代码 round-0 错了、AI 没修好」。
若不能区分，测试与 issue 追踪会把 AI 过失记到规则引擎头上，或反过来——**归因能力应成为本路径的硬目标，与「AI 提得准不准」同等重要。**

### 探索期要达成的目标

```text
1. 测 AI 真实能力：尽量让 AI 的判断落地并进入后续 verifier / standard-gap，而不是在 reconciler 层提前挡掉。
2. 可区分致因：任一 mismatch / finding，能回答「agent 关时是否已存在」「agent 开且应用了哪些 proposal 后出现/恶化」。
3. AI 输入单独讨论：packet 给什么、给多少，决定 AI 能不能判对——具体方案见 §5.5 与 §8，不在此展开。
```

### 方向修订（三条）

**1）Reconciler：放开，不做语义二审**

初稿把 reconciler 当作「第二道语义裁判」（置信度、闭集本体、破坏性 policy 预审等）。修订为：探索期**默认信任 AI**，reconciler 仅做 pass-through 留痕 + 防 pipeline 崩溃的硬校验（如幻觉 seq、不可执行的 overlay）。
**关键词 / unit_id 开放，就是 reconciler 的探索期指向**：不因「不在闭集 ontology」拒绝 proposal；各校标题变体交给 AI 读文本判断，不再复用 `UNIT_DEFINITIONS` 关键词体系约束 AI 输出。

**2）闭集关键词：从 Agent 路径移除**

规则引擎的关键词问题，正是引入 AI 的原因。Agent 路径不再用闭集关键词或 `unit_candidates` 约束 AI 识别与命名。

**3）归因优先于阻塞**

本阶段重点不是设计更多 gate，而是引入 AI 后仍能**准确追踪问题归属**（AI vs 确定性代码）。
具体 artifact、diff、对照运行等实现留 plan-01；本节只确立：没有可归因留痕，就不应宣称「评估过 AI 路径」。

---

## 0. 记录目的

本 issue 记录「在模板生成 T2/T3 引入 AI」的事实基线、锁定决策和提议方案，作为后续讨论与 plan-01 的基准。

```text
1. 当前 T2/T3 还错在哪里、为什么纯规则优化收敛困难。
2. 为什么这次引入 AI，且采用"中间形态"（AI 提案 + 确定性裁判），而不是 AI 直接改代码或只做 review。
3. AI 介入的确切位置、边界、artifact、reconciler、重生方式、测试与实施顺序。
```

重要边界（与现有架构一致）：

```text
AI 只提语义 proposal，永不裁定 PASS/FAIL。
AI 不改 document_facts / standards / hash / manifest，不伪造 OOXML 证据，不删除不可丢失的可见内容。
确定性系统负责事实校验、artifact 生成、三态 gate 裁判。verify_template_parse_build 仍是唯一 status 权威。
standards/targets/** 仍是验收标准，不作为 T2/T3 生成算法输入；本路径不接 t2_standard gate（已确认其未接入 runner/orchestrator）。
```

## 1. 当前真实运行口径

```text
代码 checkpoint：ac3bcc0（main）。
模板生成主链 src/docfit/template_generation/runner.py::generate_template 全确定性：
  T1 inspect_document_facts_docx
  → T2 build_template_structure_candidates / build_unit_map
  → T3 build_template_generation_model / build_element_spec
  → T4 build_global_spec → T5 build_template_spec → T6 executor/manifest
  → verify_template_parse_build（三态 PASS/FAIL/UNKNOWN，含 first_bad_stage）
仓库零 LLM 依赖（pyproject 仅 python-docx/pyyaml/typer）；测试全离线。
T2/T3 当前为纯规则/启发式（structure_candidates.py 的边界打分 + 元素 policy 推断）。
```

## 2. Expected vs Observed（为什么引入 AI）

依据 `template-parse-refactor-t2-unit-recognition-issue-03-state-machine-standard-gates.md`，三校 `expected.unit_order` 与实际 `unit_map` 大量 mismatch，典型：

```text
湖南农大：body_title_block / abstract_cn / references / acknowledgement / appendix 缺失；
         多个后置表单被 post_forms 或 custom 表达，未映射 standard unit_id。
南农本科：originality_statement / authorization_statement 未按 standard 表达；appendix / acknowledgement 缺失；
         academic_achievements 仍 custom；"第X章结论与展望"被过切出 body_main。
北大研究生：copyright_notice / figure_list / table_list / academic_achievements /
         originality_authorization_statement 缺失；正文 Heading 1 被切成多个 top-level custom；
         后置 references（seq 306）退化为 custom。
```

T3 残余见 `template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md`：多个 "inferred fill" 弱证据 medium、行内格式说明残留、policy 标注粒度过粗（高置信错误静默通过）。

```text
判断：这些是语义判断问题（这段是不是独立开题记录表 / 这个占位是不是学生填充）。
规则复杂度越堆越难收敛，且容易过拟合单校。AI 的语义理解收益最大的正是 T2/T3。
```

## 3. 为什么选"中间形态"

```text
不采用"代码生成完 AI 交叉 review"：只能诊断，不能真正改善产物。
不采用"AI 直接改代码、跑一跑、再改"：那是开发期 agent，不适合产品运行时。
采用：AI 提 proposal → 薄 reconciler（探索期 pass-through）→ overlay 应用 → 现有 verifier / template-gap 裁判。
探索期重心：AI 输入设计 + 事后归因（能否判定问题是否 AI 导致），而非 reconciler 语义阻塞。
AI 改的不是源代码，而是 T2/T3 结构化中间产物的 overlay / proposal。
```

## 4. 锁定决策（已与用户确认；2026-06-26 Review 修订见文首）

```text
1) 范围 = Advisory + 薄 Reconciler（pass-through）+ Overlay 应用 + AI 归因留痕。
   探索期：schema 合法且硬校验通过的 proposal 默认 accepted 并应用；不在 reconciler 做语义/置信拦截。
2) 基础设施 = 直接接真实 Claude API。附加硬约束（不与该选择冲突）：
   - API 调用收敛在单一 client 边界模块（可 mock）。
   - proposals / decisions / overlays 落盘为 artifact，支持 replay 模式离线重跑 overlay+重生。
   - AI 步骤默认关闭，env/CLI flag 显式开启；现有确定性运行与测试 0 变化。
   - 默认模型 claude-opus-4-8，可配置。
3) 阶段聚焦 = T2 + T3 一起；探索期第一优先级 = AI 输入设计 + 归因度量，非 reconciler 阻塞。
4) Agent 路径不使用闭集关键词 / unit_candidates ontology 约束 AI；各校标题变体由 AI 读 text 判断。
5) 排序 = 与确定性 standard-gate 工作（issue-03/plan-03）并行，互不依赖，后期合流。
```

## 5. 提议方案

### 5.1 总体运行时流程

```text
确定性 T2/T3 初稿（round-0）
  → 组 template_agent_packet（输入范围见 §5.5，plan-01 定稿）
  → AI 提 template_agent_proposals
  → reconciler 薄校验（硬约束 only）→ template_agent_decisions（探索期默认 accepted）
  → agent_t2_overlay / agent_t3_overlay
  → patch structure_candidates → 重跑 build_unit_map + build_template_generation_model/build_element_spec
  → verify_template_parse_build 裁判
  → 归因留痕：round-0 vs post-agent diff、proposal_id → 字段变更映射（见文首 Review）
  → 必要时再来一轮，最多 1-2 轮；语义对错由事后 standard/gap 度量，不在 reconciler 预审
```

### 5.2 重生 seam（架构基石，已读码验证）

```text
build_unit_map(document_facts, structure_candidates)          # artifacts.py:41，纯函数
  读 structure_candidates["units"]，自行重算 confidence/flags/section_profile/page_start/input_hashes。
build_template_generation_model(request, structure_candidates) # generation_model.py:16，纯函数
  元素策略由 element["candidate_policy"] 驱动（generation_model.py:130-131）→ build_element_spec。
结论：patch structure_candidates → 重跑这两个函数，即让确定性系统重新派生 verifier 校验的全部字段，
      hash 对 patched 结构诚实重算。AI 不得手写这些派生字段。
推荐：只 patch structure_candidates，不直接 patch 已组装的 unit_map/element_spec。
```

### 5.3 新增模块布局

新建包 `src/docfit/template_generation/agent/`（复用 `ai_rca/packets.py` 的 advisory 边界范式，不耦合其 RCA 诊断面）：

```text
config.py      AgentConfig(enabled=False, model="claude-opus-4-8", max_rounds=2,
               proposals_path=None)；from_env()；探索期不设 confidence_floor
packet.py      build_template_agent_packet(...)   纯投影；输入范围 plan-01 定稿（§5.5）；不含 hash/OOXML 字节
proposals.py   Proposal 类型 + parse_proposals()（永不抛）；
               T2_KINDS=(split_unit,merge_unit,relabel_unit,adjust_boundary,required_missing)
               T3_KINDS=(classify_element_policy,)
client.py      唯一网络边界；anthropic 懒导入；
               TemplateAgentClient(Protocol) / ClaudeTemplateAgentClient / ReplayTemplateAgentClient / AgentUnavailable
reconciler.py  reconcile_proposals(...) -> decisions   探索期 pass-through + 硬校验 only（§5.6）
overlay.py     build_t2_overlay/build_t3_overlay；apply_overlays(...)->patched structure_candidates（deepcopy）
regenerate.py  regenerate_unit_map_and_element_spec(...)->(unit_map,generation_model,element_spec)
decisions.py   decisions artifact 组装/写出；含 applied_proposal_ids 供归因
attribution.py round-0 vs post-agent diff；mismatch → proposal_id 映射（探索期重点）
loop.py        run_template_agent_round(...)->AgentRoundResult（携带 packet/proposals/decisions/overlays/重生产物/changed）
```

### 5.4 runner.py 接入点

```text
改签名：generate_template(..., *, agent_config: AgentConfig | None = None)  # 默认零行为变化
插入位置：element_spec = build_element_spec(generation_model)（第 100 行）之后、build_global_spec 之前。
默认（agent_config 空）：局部变量原样穿过，现有运行/测试 0 变化。
开启时：循环最多 max_rounds 轮，run_template_agent_round 重写 unit_map/generation_model/element_spec；
        用仅 T2/T3 子 verifier peek first_bad_stage 决定是否再来一轮；changed=False 即停。
末尾第 137 行 verify_template_parse_build 保持唯一权威裁判，不变。
convert/orchestrator.py（:151/:323）无需改动（不传 agent_config 即默认关闭）。
```

### 5.5 Artifact JSON 概要（复用现有字段名）

**AI 输入（template_agent_packet）——初稿基线 + Review 待决项**

```text
实现基线（读码）：尚无 agent 包；下列字段为计划投影目标。初稿若仅复用 t2_input.contexts，则 AI 只看到
open_questions 附近 ±2 source_seq、每窗最多 12 条 entry（structure_candidates._entries_near_interval）。
这不是 T1 全文，也覆盖不了 issue-03 中大量「规则引擎未提问」的 mismatch 区域 → 输入策略必须在 plan-01 单独设计。

计划字段（随 plan-01 调整）：
template_agent_packet.json
  advisory_only / status_authority="deterministic_harness_only" / allowed_ai_tasks / forbidden_ai_tasks
  t2_input（structure_candidates.t2_input，可能扩展而非原样透传）
  draft_unit_map（精简）/ draft_element_spec（精简）
  body_flow_windows（初稿：t2_input.contexts；修订方向：unit 边界窗 + 低置信/custom 强制上下文）
  findings_t2_t3（verifier peek；第二轮可扩展 verification_report 片段）
  round0_snapshot_id（归因：关联 round-0 产物哈希）

探索期取消：packet 内 ontology(unit_candidates) / policy_markers 闭集作为 AI 必填输入（见文首 Review）。
可选参考：canonical unit_id 列表可作为「建议命名」非约束字段，不得用于 reconciler 拒绝。
```

**AI 输出与其它 artifact**

```text
template_agent_proposals.json（AI 输出 / replay 输入）
  proposals[]{proposal_id, kind, target_path, operation, source_seq_refs, evidence_refs,
              confidence, reason, risk, requires_review}
  review_questions[]
  operation 按 kind：
    split_unit            {from_unit_id, new_unit_id, split_at_source_seq}
    merge_unit            {unit_ids, into_unit_id}
    relabel_unit          {unit_id, new_unit_id}   # new_unit_id 可为 canonical 或 custom:template:...
    adjust_boundary       {unit_id, edge, new_source_seq}
    required_missing      {unit_id, source_seq_refs}
    classify_element_policy {stable_id, policy, fill_source?, field_type?, manual_semantics?}

template_agent_decisions.json（reconciler 输出；探索期多为 accepted）
  decisions[]{proposal_id, kind, target_path, outcome:accepted|rejected, applied,
              checks[]{check_id, status, reason}}
  applied_proposal_ids[] / rejected_proposal_ids[]
  探索期不产出 degraded 路径；rejected 仅限硬校验失败（§5.6）

agent_t2_overlay.json / agent_t3_overlay.json
  source_structure_candidates_hash（provenance，AI 不写）
  operations[]（携带 from_proposal_id）；T3 op 写回 structure_candidates.units[].elements[].candidate_policy + 支撑字段

agent_attribution.json（探索期新增，见文首 Review）
  round0_hashes / post_agent_hashes
  field_diffs[]{path, before, after, from_proposal_ids[]}
  standard_probe_delta（可选：对接 t2_standard audit 前后对比）
```

### 5.6 Reconciler 校验规则（探索期：薄校验 / pass-through，见文首 Review）

探索期默认信任 AI；reconciler **不做**语义二审、置信拦截、闭集 ontology 拒绝、破坏性 policy 预审 degraded。

```text
默认：parse 合法 + 下列硬校验全过 → outcome=accepted, applied=true。
任一硬校验失败 → outcome=rejected（仅防幻觉坐标或 overlay 不可执行）。
先建 seq→source_ref 索引。

硬校验（保留）
  C-EVIDENCE-EXIST   source_seq_refs/evidence_refs 必须在 document_facts.body_flow 真实存在
  C-OVERLAY-EXEC     split/merge/boundary 应用后不制造 gap/overlap；不得移除 body_main unit
  C-T3-TARGET        classify_element_policy 的 stable_id 必须存在于 round-0 element 列表
  C-SCHEMA           operation 字段满足 kind 契约（parse_proposals 已拦一层）

探索期移除（产品化阶段再评估）
  C-CONFIDENCE / requires_review 拦截
  relabel new_unit_id ∈ 闭集 ontology
  policy ∈ 闭集、fill/manual/generated 预审、instruction_remove 证据、非破坏性 degraded
  review_flags / open_questions 由 reconciler 预写

记录：每条硬校验 append {check_id,status,reason}；accepted 决策写入 applied_proposal_ids 供归因。
```

### 5.7 Claude client

```text
propose 内懒导入 anthropic；model=claude-opus-4-8、thinking=adaptive、max_tokens=16000；
导入失败/无 key → 抛 AgentUnavailable，loop 捕获后 no-op（generate_template 绝不硬失败）。
system prompt 逐字编码边界（角色="提 T2/T3 结构化编辑，绝不裁判"、各 kind operation 契约、
  "只引用 packet 内 source_ref/source_seq，不臆造 OOXML 证据"、forbidden 列表）；
  探索期不写「闭集本体」硬约束；canonical unit_id 仅作命名建议。保持字节稳定以命中 prompt cache。
结构化输出走 output_config.format=json_schema（proposals schema, additionalProperties:false）→ parse_proposals。
重试：SDK 自动重 429/5xx；外加一次"schema 失败带 rejection 摘要重提"；仍畸形则丢弃并记 decisions.schema_rejections。
门禁：仅 enabled（live）或 proposals_path（replay）时实例化 client；默认 generate_template 不构造 client、不触网。
```

### 5.8 测试策略（离线确定性为主覆盖面）

```text
tests/unit/test_template_agent_reconciler.py   硬校验 only：伪造 seq→rejected / 合法 proposal→accepted / body_main 保护
tests/unit/test_template_agent_overlay.py      apply→regenerate 后过 T2/T3 子 verifier；range 连续、hash 重算
tests/unit/test_template_agent_replay.py       ReplayTemplateAgentClient 全链路零网络、决策确定
tests/unit/test_template_agent_packet.py       边界字段在、无 hash/OOXML 泄漏；输入窗覆盖待 plan-01 定稿后加断言
tests/unit/test_template_agent_attribution.py  round-0 vs post-agent diff；proposal_id 映射到 field_diffs
tests/unit/test_template_agent_gating.py       AgentConfig() 默认与不传参运行字节一致（回归护栏）
tests/unit/test_template_agent_client_boundary.py  monkeypatch 懒导入：无 anthropic/key→AgentUnavailable→no-op
tests/contract/test_template_generate.py（扩） replay 端到端：status 仍由 verify_template_parse_build 产出、归因 artifact 落盘
fixtures：tests/fixtures/template_agent/（split_post_forms / classify_cover_fill / fabricated_evidence→rejected）
CI 无 live 调用。
```

## 6. 提议实施顺序（每步独立可验、commit-per-feature）

```text
Phase 0  本 issue 文档 + 文首 Review 建议 + 登记 index
Phase 1  AI 输入（packet）设计定稿 + schema + config（不接 runner）；同步 attribution artifact 形状
Phase 2  overlay+regenerate+薄 reconciler（pass-through + 硬校验）
Phase 3  attribution diff + round-0/post-agent 对照
Phase 4  client 边界+replay+loop；anthropic 放可选依赖组 [dependency-groups] agent
Phase 5  runner 接线（gated, 默认关）；agent artifacts 进 debug snapshot（outputs.py 扩 08_template_agent_*）
Phase 6  CLI/env 开关（--template-agent / --template-agent-proposals 或 DOCFIT_TEMPLATE_AGENT=1）；convert 默认关
Phase 7  live 三校评估 + t2_standard/gap 归因报告（人工+脚本）
```

## 7. 后续验收门禁

```text
1. 默认关闭门禁：不传 agent_config / env 未设 → 输出与当前字节一致；现有用例不破。
2. 离线确定性门禁：薄 reconciler / overlay / regenerate / replay 全链路零网络可测，结果确定。
3. 安全边界门禁：任一运行 AI 均未改 document_facts/standards/hash/manifest，未改写 status。
4. 权威门禁：最终 status 仍由 verify_template_parse_build 产出。
5. replay 端到端门禁：fixture proposals 跑通 → decisions/overlay/attribution 落盘、重生 unit_map 反映变更。
6. AI 归因门禁（探索期重点）：同一模板可对比 agent 关/开；mismatch 变化可映射到 applied_proposal_ids；能回答「是否 AI 判断导致」。
7. live 评估（人工，需 ANTHROPIC_API_KEY）：三校各跑一次，proposals 与 issue-03 expected vs observed 对照 + 归因表。
8. 非回归门禁：T1 不恢复任何 semantic fields；standards/targets/** 不被自动更新；t2_standard gate 接线不被本路径触碰。
```

## 8. 待讨论的开放问题

```text
Q1 packet 输入范围定稿：仅 open_question 窗是否足够；unit 边界窗 / custom 强制上下文 / 全文分段摘要的取舍。
Q2 第二轮是否必须喂 verification_report + t2_standard probe mismatch 区间。
Q3 T2 split/merge 的 source_seq 重切由 overlay 直接从 body_flow 切，还是要求 AI 给出完整 range。
Q4 live 与 replay 的 proposals artifact 是否需要 schema 版本化以便长期回放。
Q5 agent_attribution 与 verification_report / template_gap_report 的字段合流方式。
Q6 产品化阶段是否恢复 reconciler 语义/置信 gate（探索期明确不做）。
Q7 与 issue-03 standard-gate 合流：归因度量是否统一使用 audit_unit_map_against_t2_standard 前后 delta。
```
