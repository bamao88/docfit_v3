---
status: draft
owner: template-generation
stage: T2T3
topic: agent-proposal
doc_type: implementation_proposal
issue_id: T2T3-AGENT-ISSUE-01
issue_sequence: 1
proposal_id: T2T3-AGENT-PROPOSAL-01
created: 2026-06-26
last_updated: 2026-06-27
version: 4
review:
  date: 2026-06-27
  summary: 文档定位改为基于当前代码的新实施方案；拆成现有确定性代码改进与 AI 增量两条线；探索期测 AI 能力与归因，reconciler 放开语义二审但保留可执行硬校验，AI 主输入改为 PDF/render 可见层。
previous_issue:
  id: none
  doc: none
previous_optimization:
  id: none
  doc: none
  summary: T2/T3 多轮纯确定性优化后，三校单元识别/元素策略仍与 standard 大量 mismatch；本 proposal 在当前代码基础上同时推进确定性契约收口与 AI 语义提案层。
next_plan:
  id: TBD
  doc: TBD
  summary: 基于本 implementation proposal 产出 plan-01。
source_proposal:
  doc: /Users/fl/Documents/Codex/2026-06-26/ai-agent-ai/outputs/docfit-template-generation-agent-driven.md
  summary: AI 提 proposal、确定性 reconciler 校验并应用 overlay、现有 verifier/template-gap 裁判的中间形态方案。
related_issues:
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-03-state-machine-standard-gates.md
  - docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md
  - docs/plans/template-parse-refactor-t2-open-label-unit-recognition.md
  - docs/plans/template-parse-refactor-t2-visual-pagination.md
related_code:
  - src/docfit/template_generation/runner.py
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/generation_model.py
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/verifier.py
  - src/docfit/ai_rca/packets.py
---

# T2/T3 Agent 方案 01：当前代码改进 + AI 语义提案层

## 定位说明（2026-06-27 修订）

这份文档不再按“某一轮优化后的残余 issue”使用，而是作为**基于当前代码的新增方案基线**：

```text
1. 现有代码层面的改进：
   - 保持 T1 fact-only 边界；
   - 梳理 T2/T3 可重生 seam；
   - 补齐 render packet、overlay、replay、归因 artifact、默认关闭门禁；
   - 对现有确定性路径做必要的契约收口，确保 AI 关闭时行为不变。

2. AI 增量：
   - 新增基于 docx→PDF/render 的人类可见层输入；
   - AI 只产结构化语义建议，不裁判 PASS/FAIL；
   - reconciler 探索期不做语义二审，但保留 schema / source_seq / overlay 可执行性 / policy 可执行枚举等硬校验；
   - 通过 round-0 与 post-agent 对照记录 AI 是否改善、引入或放大 mismatch。
```

文件名和 `issue_id` 暂保留，用于既有 `docs/plans/template-parse-refactor-issue-index.md` 链路兼容；后续若拆出正式 plan，可命名为 `template-parse-refactor-t2t3-agent-proposal-plan-01-current-code-ai-overlay.md`。

## Review 建议（2026-06-26 / 2026-06-27 讨论）

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

### 方向修订（四条）

**1）Reconciler：放开，不做语义二审**

初稿把 reconciler 当作「第二道语义裁判」（置信度、闭集本体、破坏性 policy 预审等）。修订为：探索期**默认信任 AI**，reconciler 仅做 pass-through 留痕 + 防 pipeline 崩溃的硬校验（如幻觉 seq、不可执行的 overlay）。
**关键词 / unit_id 开放，就是 reconciler 的探索期指向**：不因「不在闭集 ontology」拒绝 proposal；各校标题变体交给 AI 读文本判断，不再复用 `UNIT_DEFINITIONS` 关键词体系约束 AI 输出。
但“放开语义二审”不等于放开执行层枚举：overlay operation、T3 `candidate_policy`、T4 hint kind 等必须属于当前代码可消费的有限集合；否则会把不可解释字符串写进 generation model / plan / executor。

**2）闭集关键词：从 Agent 路径移除**

规则引擎的关键词问题，正是引入 AI 的原因。Agent 路径不再用闭集关键词或 `unit_candidates` 约束 AI 识别与命名。

**3）归因优先于阻塞**

本阶段重点不是设计更多 gate，而是引入 AI 后仍能**准确追踪问题归属**（AI vs 确定性代码）。
具体 artifact、diff、对照运行等实现留 plan-01；本节只确立：没有可归因留痕，就不应宣称「评估过 AI 路径」。

**4）AI 输入输出：PDF/视觉主输入 + 分层 I/O（对齐 T2/T3/T4）**

初稿（及 §5.5 基线）让 AI 读 `t2_input` / `body_flow_windows` / round-0 初稿——本质是 **T1 整理后的 OOXML 投影 + 规则引擎错题本**。修订为：

```text
AI 推理面 ≠ T1 document_facts / structure_candidates 投影
AI 推理面 = docx→PDF→渲染提取后的「人类可见层」
  - clean / annotated page images（页上叠 source_seq 标签）
  - page_text_index（页内文本 + 段落顺序）
  - page_layout_index（page_no、bbox、page_top_ratio 等，按 Tier 分级）
  基建与契约见 template-parse-refactor-t2-open-label-unit-recognition.md §7–8、
  template-parse-refactor-t2-visual-pagination.md Phase 1A/1B。

AI 输出面 ≠ 扁平 proposals[]{kind: split|merge|classify...}
AI 输出面 = 按现有阶段分层对齐的结构化语义（与 L2 语义解析层一致）：
  - T2 层：unit_candidates、block_candidates（toc/form）、boundary_adjustments
  - T3 层：element_policy_candidates（占位符/表格/填写区策略）
  - T4 层：section_profile_hints、page_numbering_hints、page_policy_candidates（首轮只落 hints，不直接改 T4 产物）
  各层独立 schema（如 t2_ai_response / t3_ai_response / t4_ai_response），
  由 reconciler 分层落 overlay → 重跑对应 build_*，而非一锅扁平 patch。

分层输入策略（参考 open-label §8.1，但本方案首轮收紧 AI 推理主输入，plan-01 定稿调用形态）：
  - full-pass overview：全书低分辨率缩略图 + page index → 整体单元结构与分页模式
  - focused-pass review：按层/按可疑区间给高分辨率局部页
    · T2 窗：单元边界可疑页
    · T3 窗：单元内表格/占位符/填写区页
    · T4 窗：分节变化、页码样式、页眉页脚样本页

明确不给 AI 作为主输入（避免规则视角带偏）：
  - T1 body_flow 全文或整理切片
  - t2_derived_signals、deterministic_candidates、round-0 draft_unit_map / draft_element_spec
  - 闭集 ontology / UNIT_DEFINITIONS 关键词约束

与 open-label §8.1 的关系：
  - 本方案有意收紧 AI 推理主输入，避免 deterministic_candidates / known_taxonomy 带偏；
  - 若为了成本或命名稳定性提供 canonical unit_id 建议列表，只能作为 non-binding reference；
  - T3 不把 round-0 element stable_id 暴露为 AI 主输入，AI 用 source_seq/render evidence 指向目标，reconciler 再映射到 round-0 stable_id。

双轨而非单轨（硬约束保留）：
  - T1 继续服务确定性 hash、verifier、manifest；默认关闭 Agent 时行为不变。
  - AI 走 Render 轨做语义；两轨在 source_seq 汇合（page_text_index 文本回绑，非 T1 语义字段）。
  - 没有 annotated source_seq / page_text_index 可绑定的 AI 输出不得进入正式候选（open-label §7.2）。

round-0 确定性初稿的新定位：
  - 仍要跑（归因 baseline、默认关 Agent 时的正式产物）
  - 不作为 Agent packet 必填输入；agent 开/关对照用于 attribution，不是「让 AI 修草稿」。

待 plan-01 拍板（记入 §8）：
  - 一次调用产出 layers{t2,t3,t4_hints} vs T2→T3 focused-pass + T4 hints later
  - current-code improvements 是否作为 plan-01 Phase 1 独立合并
  - reconciler 探索期是否完全不读 round-0 优先级（仅硬校验 + source_seq 可绑定性）
```

---


## 0. 记录目的

本文记录「在当前模板生成代码基础上同时做确定性代码改进与 AI 增量」的事实基线、锁定决策和提议方案，作为后续 plan-01 的基准。

```text
1. 当前代码有哪些可利用 seam，哪些契约需要先收口。
2. 哪些问题继续由确定性代码改进解决，哪些问题交给 AI 语义建议探索。
3. AI 介入的确切位置、边界、artifact、reconciler、重生方式、归因与测试顺序。
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
1) 范围 = 当前代码契约收口 + Advisory + 薄 Reconciler（pass-through）+ Overlay 应用 + AI 归因留痕。
   探索期：schema 合法且硬校验通过的 proposal 默认 accepted 并应用；不在 reconciler 做语义/置信拦截。

2) 当前代码层面的先决改进：
   - runner seam：round-0 产物保留，post-agent 只通过 patched structure_candidates 重生；
   - artifact seam：packet / response / decisions / overlay / attribution 均落盘并可 replay；
   - executable enum：operation kind、T3 candidate_policy、T4 hint kind 限定在当前代码可消费集合；
   - AI 关闭时不改现有输出、hash、manifest、verifier status。

3) AI 基础设施 = fixture/replay first，live client later。
   - CI 与默认开发流只跑 fixture/replay，不依赖 live API。
   - 网络调用收敛在单一 client/transport 边界模块（可 mock）。
   - live Claude 作为后续非门禁 eval 开关接入；模型名和参数不写死在核心流程，落地时再确认。
   - AI 步骤默认关闭，env/CLI flag 显式开启；现有确定性运行与测试 0 变化。

4) 阶段聚焦 = T2 + T3 一起，T4 首轮只收 hints。
   - T2/T3 可进入 overlay + regenerate；
   - T4 只写 section/page/page-numbering hints artifact，不直接改 global_spec/template_spec/plan，除非后续 plan 明确补齐 T4 overlay 与门禁。

5) Agent 路径不使用闭集关键词 / UNIT_DEFINITIONS 约束 AI 判断。
   - AI 输出 raw_label / display_name / optional canonical_label_id_suggestion；
   - reconciler 不因 label 不在 ontology 拒绝；
   - final unit_id 仍由确定性映射层产出 canonical 或 custom，并写 trace，AI 不直接写最终 unit_id。

6) 排序 = 与确定性 standard-gate 工作（issue-03/plan-03）并行，互不依赖，后期在 audit/gap 归因报告合流。
```

## 5. 提议方案

### 5.1 总体运行时流程

```text
确定性 T2/T3 初稿（round-0，作为 baseline 与重生起点）
  → 可选 render 轨：docx→PDF→page images/page_text_index/page_layout_index
  → 组 template_agent_render_packet（AI 推理主输入，见 §5.5）
  → fixture/replay 或 live transport 产出 layered AI response
  → reconciler 薄校验（硬约束 only）→ template_agent_decisions（探索期默认 accepted）
  → agent_t2_overlay / agent_t3_overlay；T4 首轮只产 hints artifact
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
config.py      AgentConfig(enabled=False, model=None, max_rounds=2,
               response_path=None, transport="replay")；from_env()；探索期不设 confidence_floor
packet.py      build_template_agent_render_packet(...)   纯投影；render 可见层为主输入（§5.5）；
               可带 round0_snapshot_id 供归因关联，但不把 round-0 draft 当作 AI 推理主输入
response.py    LayeredResponse 类型 + parse_layered_response()（永不抛）；
               T2: unit/block/boundary candidates；T3: element_policy candidates；T4: hints only
proposal.py    将 layered response 投影为 overlay proposals；T3 target 先用 source_seq/render target，
               再由 reconciler 映射到 round-0 element stable_id
client.py      唯一 transport/client 边界；
               TemplateAgentTransport(Protocol) / ReplayTemplateAgentTransport / FixtureTemplateAgentTransport /
               ClaudeTemplateAgentTransport(later) / AgentUnavailable
reconciler.py  reconcile_proposals(...) -> decisions   探索期 pass-through + 硬校验 only（§5.6）；
               不做语义/置信拦截，但校验 source_seq、schema、overlay 可执行性、policy 可执行枚举
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

**AI 输入——初稿基线（已被 Review §4 修订；plan-01 以 render packet 为准）**

```text
【初稿，保留作对照】若仅复用 t2_input.contexts，则 AI 只看到 open_questions 附近 ±2 source_seq……
该路径不以 T1 整理投影为主输入，见 Review §4。

【修订方向】template_agent_render_packet.json（名称 plan-01 定稿）
  advisory_only / status_authority / allowed_ai_tasks / forbidden_ai_tasks
  render_artifacts:
    clean_page_images[] / annotated_page_images[]
    page_text_index[] / page_layout_index[]（含 tier）
    render_hash / render_engine / render_version
  input_windows（分层输入）:
    full_pass: {page_thumbnails[], page_index_summary}
    focused_pass[]: {layer: t2|t3|t4, page_nos[], reason}
  optional_reference: canonical unit_id 建议列表（非约束；不得作为拒绝依据）
  round0_snapshot_id（仅归因关联，非推理必填）
  findings_t2_t3（第二轮可选；verifier peek 片段）

明确不含：t2_input.contexts、body_flow_windows、draft_unit_map、draft_element_spec、
          t2_derived_signals、deterministic_candidates、闭集 ontology。

与 open-label §8.1 的差异：open-label 曾把 deterministic_candidates / known_taxonomy
列为 AI 输入，本方案为避免规则视角带偏，首轮不把它们作为推理主输入；若 plan-01
为了命名稳定性保留 canonical 参考，也必须标为 non-binding reference。
```

**AI 输出与其它 artifact**

```text
【修订方向】template_agent_layered_response.json（一次调用）或分文件 t2/t3/t4_ai_response.json（多轮 focused-pass）
  layers:
    t2: {unit_candidates[], block_candidates[], boundary_adjustments[], open_questions[]}
        unit_candidates 输出 raw_label/display_name/canonical_label_id_suggestion，
        不直接输出 final unit_id。
    t3: {element_policy_candidates[], open_questions[]}
        element target 使用 source_seq_refs/render_target_id + visible evidence；
        reconciler 再映射到 round-0 element stable_id。
    t4: {section_profile_hints[], page_numbering_hints[], page_policy_candidates[], open_questions[]}
        首轮只落 hints artifact，不直接 patch T4 artifact。
  schema_version / prompt_version / source_render_hash / model

【初稿扁平形态，保留作 overlay 操作对照】template_agent_proposals.json
  proposals[]{proposal_id, kind, operation, source_seq_refs, ...}
  operation 按 kind：split_unit / merge_unit / relabel_unit / adjust_boundary /
    required_missing / classify_element_policy
  reconciler 可将 layered response 投影为 proposals + overlay operations（plan-01 定稿）；
  投影层负责把 AI 的 source_seq/render target 映射为当前代码可执行 target_path。

template_agent_decisions.json（reconciler 输出；探索期多为 accepted）
  decisions[]{proposal_id, kind, target_path, outcome:accepted|rejected, applied,
              checks[]{check_id, status, reason}}
  applied_proposal_ids[] / rejected_proposal_ids[]
  探索期不产出 degraded 路径；rejected 仅限硬校验失败（§5.6）

agent_t2_overlay.json / agent_t3_overlay.json
  source_structure_candidates_hash（provenance，AI 不写）
  operations[]（携带 from_proposal_id）；T3 op 写回 structure_candidates.units[].elements[].candidate_policy + 支撑字段

agent_t4_hints.json（首轮新增，非 overlay）
  hints[]（section/page/page-numbering）；
  仅供归因和后续 plan 使用，不直接改 global_spec/template_spec/plan。

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
  C-TARGET-BIND      AI target 必须能从 source_seq/render_target 映射到当前 structure_candidates 中的 unit/element；
                     T3 映射结果 stable_id 必须存在于 round-0 element 列表
  C-EXECUTABLE-ENUM  overlay operation kind、T3 candidate_policy、T4 hint kind 必须属于当前代码可消费集合
  C-SCHEMA           operation 字段满足 kind 契约（parse_proposals 已拦一层）

探索期移除（产品化阶段再评估）
  C-CONFIDENCE / requires_review 拦截
  relabel new_unit_id ∈ 闭集 ontology（AI 不直接写 final unit_id；只给 label suggestion）
  policy 的语义预审、fill/manual/generated 是否合理、instruction_remove 证据、非破坏性 degraded
  review_flags / open_questions 由 reconciler 预写

记录：每条硬校验 append {check_id,status,reason}；accepted 决策写入 applied_proposal_ids 供归因。
```

### 5.7 AI transport / client

```text
首轮实现顺序：
  1. ReplayTemplateAgentTransport：读取已落盘 layered response，跑 overlay+regenerate+attribution。
  2. FixtureTemplateAgentTransport：按 render_hash/prompt_version 加载测试 fixture，CI 只走该路径。
  3. ClaudeTemplateAgentTransport：后续非门禁 eval 接入；anthropic 懒导入，导入失败/无 key → AgentUnavailable。

system prompt 逐字编码边界（角色="提 T2/T3 结构化编辑和 T4 hints，绝不裁判"、各 layer schema、
  "只引用 packet 内 source_ref/source_seq/render_target，不臆造 OOXML 证据"、forbidden 列表）；
  探索期不写「闭集本体」硬约束；canonical unit_id 仅作 non-binding naming reference。

结构化输出走 JSON schema（layered response schema, additionalProperties:false）→ parse_layered_response。
schema 失败：Replay/Fixture 直接记录 schema_rejection；Live 后续可加一次"schema 失败带 rejection 摘要重提"。
门禁：仅 enabled 且 transport != off 时实例化 transport；默认 generate_template 不构造 client、不触网。
```

### 5.8 测试策略（离线确定性为主覆盖面）

```text
tests/unit/test_template_agent_reconciler.py   硬校验 only：伪造 seq→rejected / 合法 proposal→accepted / body_main 保护
                                              / 不可执行 policy enum→rejected / T3 source_seq target→stable_id 映射
tests/unit/test_template_agent_overlay.py      apply→regenerate 后过 T2/T3 子 verifier；range 连续、hash 重算
tests/unit/test_template_agent_replay.py       ReplayTemplateAgentClient 全链路零网络、决策确定
tests/unit/test_template_agent_fixture.py      FixtureTemplateAgentTransport 按 render_hash 选 response，CI 零网络
tests/unit/test_template_agent_packet.py       边界字段在、无 OOXML 字节泄漏；render packet 不含 round-0 draft_unit_map/draft_element_spec
tests/unit/test_template_agent_attribution.py  round-0 vs post-agent diff；proposal_id 映射到 field_diffs
tests/unit/test_template_agent_gating.py       AgentConfig() 默认与不传参运行字节一致（回归护栏）
tests/unit/test_template_agent_client_boundary.py  monkeypatch 懒导入：无 anthropic/key→AgentUnavailable→no-op
tests/contract/test_template_generate.py（扩） replay 端到端：status 仍由 verify_template_parse_build 产出、归因 artifact 落盘
fixtures：tests/fixtures/template_agent/（split_post_forms / classify_cover_fill / fabricated_evidence→rejected）
CI 无 live 调用。
```

## 6. 提议实施顺序（每步独立可验、commit-per-feature）

```text
Phase 0  本 proposal 文档定稿 + index 定位修正；明确 current-code improvements vs AI additions
Phase 1  当前代码契约收口：AgentConfig 默认关闭、runner seam、round-0 snapshot、artifact 命名、可执行 enum 常量
Phase 2  render packet schema + response schema + Replay/Fixture transport（不接 live，不接 runner）
Phase 3  layered response → proposals → overlay projection；T3 source_seq/render target 映射 stable_id；T4 hints only
Phase 4  薄 reconciler + overlay + regenerate；pass-through 语义，硬校验 source_seq/schema/exec enum/overlay 可执行
Phase 5  attribution diff + round-0/post-agent 对照；proposal_id → field_diffs / mismatch delta
Phase 6  loop + runner 接线（gated, 默认关）；agent artifacts 进 debug snapshot（outputs.py 扩 08_template_agent_*）
Phase 7  CLI/env 开关（--template-agent / --template-agent-response 或 DOCFIT_TEMPLATE_AGENT=1）；convert 默认关
Phase 8  可选 live Claude transport + 三校 eval；非 CI 门禁，输出 t2_standard/gap 归因报告
```

## 7. 后续验收门禁

```text
1. 默认关闭门禁：不传 agent_config / env 未设 → 输出与当前字节一致；现有用例不破。
2. 当前代码契约门禁：operation kind、T3 candidate_policy、T4 hint kind 有统一可执行 enum；未知值 rejected，不进入 generation model。
3. 离线确定性门禁：薄 reconciler / overlay / regenerate / replay / fixture 全链路零网络可测，结果确定。
4. 安全边界门禁：任一运行 AI 均未改 document_facts/standards/hash/manifest，未改写 status。
5. 权威门禁：最终 status 仍由 verify_template_parse_build 产出。
6. replay/fixture 端到端门禁：fixture response 跑通 → decisions/overlay/attribution 落盘、重生 unit_map/element_spec 反映变更。
7. T3 target 门禁：AI response 只用 source_seq/render target；reconciler 映射到 round-0 stable_id，无法唯一映射则 rejected 或 open_question。
8. T4 首轮门禁：T4 输出只落 hints artifact；不直接 patch global_spec/template_spec/plan。
9. AI 归因门禁（探索期重点）：同一模板可对比 agent 关/开；mismatch 变化可映射到 applied_proposal_ids；能回答「是否 AI 判断导致」。
10. live 评估（人工，需 API key）：三校各跑一次，response 与 issue-03 expected vs observed 对照 + 归因表；不作为 CI 门禁。
11. 非回归门禁：T1 不恢复任何 semantic fields；standards/targets/** 不被自动更新；t2_standard gate 接线不被本路径触碰。
```

## 8. 待讨论的开放问题

```text
Q1 render packet 分层输入定稿：full-pass 缩略图粒度；T2/T3 focused-pass 窗划分与页数上限；T4 首轮 hints 的最小字段。
Q2 首轮 response 形态：一次调用产出 layers{t2,t3,t4_hints}，还是 T2→T3 多轮 focused-pass + T4 hints later。
Q3 current-code improvements 的最小交付面：AgentConfig/runner seam/artifact 命名/exec enum 是否作为 plan-01 Phase 1 独立合并。
Q4 T3 source_seq/render target → round-0 element stable_id 的唯一映射规则；多候选时 rejected 还是 open_question。
Q5 layered response → overlay operations 的投影规则：T2 label suggestion 如何落 canonical/custom；T3 policy 如何写支撑字段。
Q6 reconciler 探索期是否完全不读 round-0 优先级（仅硬校验 + source_seq 可绑定性），还是允许用于 target 映射和冲突 trace。
Q7 第二轮是否喂 verification_report + focused-pass 定向到 mismatch 页（不再喂 t2_input 窗）。
Q8 replay / fixture / live response artifact schema 版本化与 render_hash、prompt_version 绑定方式。
Q9 agent_attribution 与 verification_report / template_gap_report 的字段合流方式。
Q10 产品化阶段是否恢复 reconciler 语义/置信 gate（探索期明确不做）。
Q11 与 issue-03 standard-gate 合流：归因度量是否统一使用 audit_unit_map_against_t2_standard 前后 delta。
```
