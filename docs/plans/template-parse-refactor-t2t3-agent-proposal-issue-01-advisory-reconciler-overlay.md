---
status: draft
owner: template-generation
stage: T2T3
topic: agent-proposal
issue_id: T2T3-AGENT-ISSUE-01
issue_sequence: 1
created: 2026-06-26
last_updated: 2026-06-26
version: 1
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
  summary: 基于本文档讨论后再产出 plan-01（实施顺序与门禁细化）。
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
采用：AI 提 proposal → 确定性 reconciler 校验并应用 → 现有 verifier / template-gap 裁判。
AI 改的不是源代码，而是 T2/T3 结构化中间产物的 overlay / proposal。
```

## 4. 锁定决策（已与用户确认）

```text
1) 范围 = Advisory + Reconciler + Overlay 应用（方案 Phase 1-3）。
   proposal 过 reconciler；高置信且可验证 → 写 overlay 并重生 unit_map/element_spec；
   低置信 → review_flags / open_questions，绝不静默应用。
2) 基础设施 = 直接接真实 Claude API。附加硬约束（不与该选择冲突）：
   - API 调用收敛在单一 client 边界模块（可 mock）。
   - proposals 落盘为 artifact，支持 replay 模式离线重跑 reconciler+overlay+重生。
   - AI 步骤默认关闭，env/CLI flag 显式开启；现有确定性运行与测试 0 变化。
   - 默认模型 claude-opus-4-8，可配置。
3) 阶段聚焦 = T2 + T3 一起。
4) 排序 = 与确定性 standard-gate 工作（issue-03/plan-03）并行，互不依赖，后期合流。
```

## 5. 提议方案

### 5.1 总体运行时流程

```text
确定性 T2/T3 初稿（round-0）
  → 组 template_agent_packet
  → AI 提 template_agent_proposals
  → 确定性 reconciler 校验 → template_agent_decisions
  → accepted+可验证 → agent_t2_overlay / agent_t3_overlay
  → patch structure_candidates → 重跑 build_unit_map + build_template_generation_model/build_element_spec
  → verify_template_parse_build 裁判
  → 必要时再来一轮，最多 1-2 轮；剩余进 UNKNOWN / review queue
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
               proposals_path=None, confidence_floor=0.80)；from_env()
packet.py      build_template_agent_packet(...)   纯投影，含边界块/本体/t2_input/draft 摘要/T2T3 findings；不含 hash/OOXML 字节
proposals.py   Proposal 类型 + parse_proposals()（永不抛）；
               T2_KINDS=(split_unit,merge_unit,relabel_unit,adjust_boundary,required_missing)
               T3_KINDS=(classify_element_policy,)
client.py      唯一网络边界；anthropic 懒导入；
               TemplateAgentClient(Protocol) / ClaudeTemplateAgentClient / ReplayTemplateAgentClient / AgentUnavailable
reconciler.py  reconcile_proposals(...) -> decisions   确定性、离线、最大测试面
overlay.py     build_t2_overlay/build_t3_overlay；apply_overlays(...)->patched structure_candidates（deepcopy）
regenerate.py  regenerate_unit_map_and_element_spec(...)->(unit_map,generation_model,element_spec)
decisions.py   decisions artifact 组装/写出
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

```text
template_agent_packet.json
  advisory_only / status_authority="deterministic_harness_only" / allowed_ai_tasks / forbidden_ai_tasks
  ontology(unit_candidates, allowed_policies, policy_markers)
  t2_input（structure_candidates.t2_input 原样）
  draft_unit_map（精简）/ draft_element_spec（精简）/ body_flow_windows（复用 t2_input.contexts）/ findings_t2_t3

template_agent_proposals.json（AI 输出 / replay 输入）
  proposals[]{proposal_id, kind, target_path, operation, source_seq_refs, evidence_refs,
              confidence, reason, risk, requires_review}
  review_questions[]
  operation 按 kind：
    split_unit            {from_unit_id, new_unit_id, split_at_source_seq}
    merge_unit            {unit_ids, into_unit_id}
    relabel_unit          {unit_id, new_unit_id}
    adjust_boundary       {unit_id, edge, new_source_seq}
    required_missing      {unit_id, source_seq_refs}
    classify_element_policy {stable_id, policy, fill_source?, field_type?, manual_semantics?}

template_agent_decisions.json（reconciler 输出）
  decisions[]{proposal_id, kind, target_path, outcome:accepted|degraded|rejected, applied,
              checks[]{check_id, status, reason}, degraded_to}
  review_flags[]（同 unit_map.flags 形状）/ open_questions[]（同 structure_candidates.open_questions 形状）

agent_t2_overlay.json / agent_t3_overlay.json
  source_structure_candidates_hash（provenance，AI 不写）
  operations[]（携带 from_proposal_id）；T3 op 写回 structure_candidates.units[].elements[].candidate_policy + 支撑字段
```

### 5.6 Reconciler 校验规则

首个 FAIL→rejected；UNKNOWN/低证据→degraded；全 PASS 且置信≥floor→accepted+applied。先建 seq→source_ref 索引。

```text
共用
  C-EVIDENCE-EXIST   source_seq_refs/evidence_refs 必须在 document_facts.body_flow 真实存在，否则 rejected（伪造证据）
  C-CONFIDENCE       置信≥floor 且 requires_review=False 才可 accepted
T2
  split    split_at_source_seq 在 from-unit range 内；分裂后两段连续无 gap
  merge    仅相邻且连续；不得吞掉 body_main
  relabel  new_unit_id ∈ 本体或 custom/review 路由；不得造成重复 unit_id
  boundary 调整后两单元非空且连续（无 break/overlap/gap）
  required_missing  required 且当前缺失 + source_seq_refs 指向真实可见内容；纯断言无证据→degraded
T3
  stable_id 必须存在；policy ∈ 本体
  fill→fill_source；manual_only→manual_semantics；generated→field_type
  instruction_remove→evidence_refs 指向非空真实文本
  非破坏性：把有实质内容的固定文本改成 remove/fill 且无 marker → degraded（保留可复核，绝不静默应用）
记录：每条检查 append {check_id,status,reason}；degraded 额外产出 review_flag/open_question（沿用现有形状），
      由现有 verifier _flag_findings 自然以 UNKNOWN 暴露，无需改 verifier。
```

### 5.7 Claude client

```text
propose 内懒导入 anthropic；model=claude-opus-4-8、thinking=adaptive、max_tokens=16000；
导入失败/无 key → 抛 AgentUnavailable，loop 捕获后 no-op（generate_template 绝不硬失败）。
system prompt 逐字编码边界（角色="提 T2/T3 结构化编辑，绝不裁判"、闭集本体、各 kind operation 契约、
  "只引用 packet 内 source_ref/source_seq，不臆造 OOXML 证据"、forbidden 列表）；保持字节稳定以命中 prompt cache。
结构化输出走 output_config.format=json_schema（proposals schema, additionalProperties:false）→ parse_proposals。
重试：SDK 自动重 429/5xx；外加一次"schema 失败带 rejection 摘要重提"；仍畸形则丢弃并记 decisions.schema_rejections。
门禁：仅 enabled（live）或 proposals_path（replay）时实例化 client；默认 generate_template 不构造 client、不触网。
```

### 5.8 测试策略（离线确定性为主覆盖面）

```text
tests/unit/test_template_agent_reconciler.py   表驱动覆盖每个 check_id（证据缺失→rejected / 低置信→degraded /
                                               合法 split/merge/relabel/boundary→accepted / fill 无 source→rejected /
                                               instruction_remove 无证据→rejected / 破坏性→degraded）
tests/unit/test_template_agent_overlay.py      apply→regenerate 后过 T2/T3 子 verifier；body_main 保留、range 连续、hash 重算
tests/unit/test_template_agent_replay.py       ReplayTemplateAgentClient 全链路零网络、决策确定
tests/unit/test_template_agent_packet.py       边界字段在、无 hash/OOXML 泄漏、本体来自 constants
tests/unit/test_template_agent_gating.py       AgentConfig() 默认与不传参运行字节一致（回归护栏）
tests/unit/test_template_agent_client_boundary.py  monkeypatch 懒导入：无 anthropic/key→AgentUnavailable→no-op
tests/contract/test_template_generate.py（扩） replay 端到端：status 仍由 verify_template_parse_build 产出、overlays/decisions 落盘
fixtures：tests/fixtures/template_agent/（split_post_forms / classify_cover_fill / fabricated_evidence→rejected / low_confidence→degraded）
CI 无 live 调用。
```

## 6. 提议实施顺序（每步独立可验、commit-per-feature）

```text
Phase 0  本 issue 文档 + 登记 index（本提交）
Phase 1  schema+packet+config（不接 runner）
Phase 2  reconciler（离线纯函数）
Phase 3  overlay+regenerate+decisions（离线）
Phase 4  client 边界+replay+loop；anthropic 放可选依赖组 [dependency-groups] agent
Phase 5  runner 接线（gated, 默认关）；agent artifacts 进 artifacts/debug snapshot（outputs.py 扩 08_template_agent_*）
Phase 6  CLI/env 开关（--template-agent / --template-agent-proposals 或 DOCFIT_TEMPLATE_AGENT=1）；convert 默认关
```

## 7. 后续验收门禁

```text
1. 默认关闭门禁：不传 agent_config / env 未设 → 输出与当前字节一致；现有用例不破。
2. 离线确定性门禁：reconciler / overlay / regenerate / replay 全链路零网络可测，结果确定。
3. 安全边界门禁：任一运行 AI 均未改 document_facts/standards/hash/manifest，未改写 status，未伪造证据。
4. 权威门禁：最终 status 仍由 verify_template_parse_build 产出；degraded 以 UNKNOWN 暴露，不被降级为 warning。
5. replay 端到端门禁：fixture proposals 跑通 → decisions/overlay 落盘、重生 unit_map 反映变更。
6. live 评估（人工，需 ANTHROPIC_API_KEY）：三校各跑一次，proposals 与 issue-03 expected vs observed 人工对照，评估 AI 真实增益。
7. 非回归门禁：T1 不恢复任何 semantic fields；standards/targets/** 不被自动更新；t2_standard gate 接线不被本路径触碰。
```

## 8. 待讨论的开放问题

```text
Q1 round-0 之后用"仅 T2/T3 子 verifier peek"决定是否进第二轮，是否够；要不要也喂 verification_report 的 T2/T3 findings 给第二轮 packet。
Q2 confidence_floor 默认 0.80 是否合适；高置信但 requires_review=True 的 proposal 是否一律 degraded。
Q3 T2 split/merge 的 source_seq 重切由 overlay 直接从 body_flow 切，还是要求 AI 给出完整 range 再校验。
Q4 live 与 replay 的 proposals artifact 是否需要 schema 版本化以便长期回放。
Q5 是否需要把 accepted 决策沉淀到 template_spec.review_decisions[] 或独立 registry（方案 Phase 6，本轮暂不做）。
Q6 与 issue-03 的 standard-gate 后期合流点：reconciler 的 ontology 校验是否最终复用 standard expected unit set。
```
