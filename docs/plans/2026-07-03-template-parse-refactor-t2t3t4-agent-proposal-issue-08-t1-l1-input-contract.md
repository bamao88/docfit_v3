---
status: closed
owner: template-generation
stage: T1L1
topic: fact-render-input-projection
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-08
issue_sequence: 08
previous_issue:
  id: T2T3T4-AGENT-ISSUE-07
  doc: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-issue-07-end-to-end-workflow-not-integrated.md
  status: draft
previous_optimization:
  doc: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-plan-07-end-to-end-workflow-integration.md
  summary: Plan 07 讨论端到端 Module 1 -> bridge -> merged 编排，但仍未把 T1 结构事实、PDF/页面图事实和 AI/code 统一输入投影字段契约完全摊开。
next_plan: docs/plans/2026-07-10-template-parse-refactor-t1l1-input-contract-plan-08-l1-projection-bundle-gate.md
created: 2026-07-03
last_updated: 2026-07-11
related_code:
  - src/docfit/template_generation/source_tree.py
  - src/docfit/template_gap/inspector.py
  - src/docfit/template_generation/agent/packet.py
  - src/docfit/template_generation/agent/evidence.py
  - src/docfit/template_generation/agent/observation_bridge.py
cross_issue:
  - docs/plans/2026-06-30-template-parse-refactor-t2t3t4-agent-module1-issue-05-observation-input-followups.md
  - docs/plans/2026-07-01-template-parse-refactor-module1-observation-dataflow-alignment.md
  - docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-issue-07-end-to-end-workflow-not-integrated.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-10-t4-observation-downstream-dead-end.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-11-unit-pagination-signal-loss.md
---

# T2/T3/T4 Agent Issue 08：T1 事实与 L1 统一输入投影契约未收口

## Closure

2026-07-11 由 Plan 08 验证关闭：T1/render 在阶段判断前封存为纯事实 L1，T2/T3/T4 code 与 AI 只读取 L1 Stage Input，T5/T6/T7 绑定同一 canonical L1 hash，旧 `08_agent_render_packet.json` 输入身份和 run-backed fallback 已删除。三校真实 API 无明显回退门与固定 replay 等价门共同 `PASS`。T3 span/policy/AI-primary 的质量升级仍归 T3 Plan 06，不属于本 issue 残留。

## 真实运行口径

当前模板生成链路里，后续 deterministic code 与 AI 看到的输入不是同一层契约：

```text
源 DOCX
  -> T1a document_facts：OOXML / python-docx / package 结构事实
  -> T1b render packet：可选 DOCX->PDF->PNG 页面图、PDF bbox、source_seq overlay
  -> L1 投影：
       deterministic code 多数直接读 document_facts / source_tree
       Module 1 AI 读 render packet 的白名单 evidence view
       observation bridge 读外部 ai_observation_bundle + render packet 做 proposal gate
  -> T2/T3/T4/T5/T6
```

现有代码已经有两类事实能力：

1. `inspect_document_facts_docx()` 生成 `document_facts`，包含文本、表格、run、样式、分节、页眉页脚、字段、编号、图片资产、文本框、脚注、未知可见对象等事实。
2. `build_template_agent_render_packet()` 在传入 `source_template_docx + render_artifacts_dir` 时，可以生成 PDF、页面 PNG、PDF text bbox、`source_seq -> page/bbox` 回绑和 annotated page SVG。

但这两类事实没有在 L1 形成统一、稳定、完整的输入投影。尤其是图片资产、PDF 页面图、页面 overlay 与 T1 字段的结合，还没有成为后续 code/AI 都可消费的一等输入。

## Expected vs observed

Expected：

```text
1. T1 事实层拆成两类事实：
   - T1a：DOCX/OOXML 结构事实。
   - T1b：PDF/页面图/overlay/render binding 视觉事实。
2. L1 统一投影层明确列出 code 与 AI 可读取的字段，不让两条路线各自偷拿或漏拿输入。
3. L1 投影只包含事实字段，不包含 unit_id/policy/confidence 等下游判断。
4. 图片事实分两类进入输入契约：
   - DOCX 内嵌图片资产事实：relationship、target、hash、byte_count、source_ref。
   - PDF 页面图事实：clean page images、annotated overlay、page/bbox/render_target。
5. 每个 source_seq、对象、图片和页面证据都能说明是否已绑定到 page/bbox；不能绑定时显式 `binding_status`，不能静默丢失。
6. AI observation bundle 进入 bridge 前必须经过 hash/schema/coverage/source binding gate。
```

Observed：

```text
1. deterministic code 主要读取 document_facts/source_tree，能看到较完整的 T1a 事实。
2. Module 1 AI 主要读取 render packet 的白名单 evidence view，字段比 document_facts 少。
3. T1 body_flow 已有 style/style_details/text_facts/run trace，但 page_text_index 当前没有转入 style/style_details/text_facts。
4. T4 AI evidence 已含 global_layout_facts（sections 页边距/纸张/页码声明、header_footer
   kind/part_name/has_content、numbering_definition_count；见 packet.py `_global_layout_facts`、
   evidence.py `build_t4_evidence`，module1-t4-fix plan-01 已实现）；但仍缺页眉页脚内容文本、
   `data.fields[]`、`data.breaks[]`、per-section source_seq 绑定，且 vision prompt 层完全不含这些事实。
5. scripts/observe_live.py 当前没有传 source_template_docx/render_artifacts_dir，导致真实渲染能力长期退化为 projection_fallback。
6. document_facts.data.images[] 已记录 DOCX 内嵌图片资产，但 render packet / evidence view 没有把它作为 source object 输入。
7. annotated_page_images 当前只 overlay 文本 source_seq bbox；没有把 images/text_boxes/drawings/unknown visible objects 一并标注为对象证据。
8. observation_bridge 只校验 observation bundle 顶层 source_render_hash，再依赖 proposal 级 source binding；没有先统一校验 observation schema 和 coverage invariant。
```

## 阶段输入与字段梳理

### T1a：DOCX/OOXML 结构事实层

输入：

```text
source_template.docx
```

当前输出：`document_facts.json`。

| 字段组 | 当前字段 | 说明 |
| --- | --- | --- |
| 顶层元数据 | `artifact_type`、`artifact_version`、`producer`、`created_at`、`metadata.source_template_docx`、`metadata.source_template_hash`、`metadata.input_exists`、`metadata.input_valid_docx` | 事实来源、运行时间、源文件 hash 和输入合法性。 |
| `body_flow[]` 定位 | `node_id`、`source_seq`、`source_seq_label`、`source_ref`、`part_name`、`order`、`kind`、`flow_item_type`、`structure_layer`、`visible` | 后续阶段引用源内容的主锚点。 |
| `body_flow[]` 文本事实 | `text`、`style`、`style_details`、`text_facts` | 可见文本、段落样式、run 主样式、行距、缩进、文本形态等事实。 |
| `body_flow[]` run/container trace | `raw_run_ids`、`logical_run_ids`、`container_ref`、`run_source_refs`、table/cell trace 字段 | 支撑 T3 run 级元素切分和表格/单元格回查。 |
| `runs[]` | `raw_run_id`、`logical_run_id`、`paragraph_id`、`source_refs`、`merged_from`、`text`、`effective_style`、`style_context` | run 合并后的事实索引，不能带 policy。 |
| `data.paragraphs[]` | `index`、`python_docx_index`、`xml_index`、`text`、`style`、`style_details`、`runs`、`source_ref` | body 段落事实。 |
| `data.tables[]` | `index`、`style`、`row_count`、`column_count`、`first_paragraph_index`、`last_paragraph_index`、`cant_split_row_refs`、`keep_refs`、`cells[]` | 表格整体和分页约束事实。 |
| `data.tables[].cells[]` | `row`、`column`、`global_index`、`text`、`style_details`、`paragraph_indices`、`paragraphs`、`cell_paragraph_refs`、`source_ref`、row/cell trace | 表格单元格内部文本和源段落回查。 |
| `data.headers_footers[]` | `index`、`kind`、`part_name`、`text`、`paragraphs`、`paragraph_refs`、`source_ref` | 页眉/页脚 part 事实。 |
| `data.sections[]` | `index`、`paragraph_index`、`source_ref`、`references`、`effective_references`、`page_numbering`、`page_size`、`page_margins` | 分节、页边距、纸张、页码声明、页眉页脚引用事实。 |
| `data.fields[]` | `index`、`kind`、`field_type`、`instruction`、`part_name`、`paragraph_index`、`end_paragraph_index`、`source_ref` | PAGE、TOC、PAGEREF、HYPERLINK 等字段事实。 |
| `data.content_controls[]` | `index`、`tag`、`alias`、`text`、`part_name`、`source_ref` | 内容控件事实。 |
| `data.footnotes[]` | `index`、`footnote_id`、`text`、`source_ref` | 脚注事实。 |
| `data.text_boxes[]` | `index`、`paragraph_index`、`text`、`source_ref` | 文本框事实。 |
| `data.images[]` | `index`、`paragraph_index`、`relationship_id`、`target`、`source_ref`、`sha256`、`byte_count` | DOCX 内嵌图片资产事实；当前只有资产和段落锚点，没有 page/bbox。 |
| `data.breaks[]` | `index`、`kind`、`paragraph_index`、`type`、`source_ref` | 换行、分页、分节 break 事实。 |
| `data.numbering_refs[]` | numbering 关联字段 | 段落与编号定义的引用关系。 |
| `data.numbering_definitions[]` | numbering 定义字段 | 编号样式与级别事实。 |
| `data.unknown_visible_objects[]` | `object_type`、`source_ref`、`reason` 等 | 尚未完全建模但可见的对象，必须向后传递风险。 |
| `indexes` | `by_source_ref`、`by_source_seq`、`body_order`、`runs_by_paragraph_id`、`runs_by_source_ref`、`runs_by_raw_run_id` | 后续阶段回查事实的索引。 |
| `warnings[]` | `unknown_visible_object` 等 | 事实覆盖风险。 |

T1a 边界：

```text
允许：源 DOCX 的可观测事实、OOXML 位置、run/style、字段、分页/分节、对象、hash。
禁止：unit_id、policy、confidence、is_toc_entry、looks_like_instruction_text 等语义判断。
```

### T1b：PDF / 页面图 / overlay 视觉事实层

输入：

```text
source_template.docx
document_facts.json
render_artifacts_dir
```

当前输出嵌在 `template_agent_render_packet` 内。

| 字段组 | 当前字段 | 说明 |
| --- | --- | --- |
| `render_status` | `real_render` 或 `projection_fallback` | 是否完成真实 DOCX->PDF->页面图渲染。 |
| `render_artifacts.clean_page_images[]` | `page_no`、`path`、`sha256`、`width_px`、`height_px`、`image_type` | 干净页面 PNG。 |
| `render_artifacts.annotated_page_images[]` | `page_no`、`path`、`sha256`、`width_px`、`height_px`、`image_type`、`annotation` | 带 source_seq bbox overlay 的 SVG 页面图。 |
| `render_artifacts` 元数据 | `render_engine`、`render_version`、`pdf_path`、`pdf_sha256`、`page_count`、`text_binding_summary`、`render_error` | 渲染可复现信息和失败原因。 |
| `source_bindings` | `source_seq -> binding_status/page_no/bbox` | T1 文本事实与 PDF text bbox 的绑定结果。 |
| `page_text_index[]` | `source_seq`、`source_ref`、`node_id`、`part_name`、`order`、`text`、`raw_run_ids`、`logical_run_ids`、`page_no`、`bbox`、`render_binding_status`、`render_target_id` | 当前 AI/code page query 的核心行级索引。 |
| `page_layout_index[]` | `page_no`、`source_seq`、`source_ref`、`bbox`、`page_top_ratio`、`tier`、`render_target_id`、`render_binding_status` | 页内位置事实。 |
| `input_windows.full_pass` | `page_thumbnails`、`page_index_summary` | AI prompt 的全文/页图摘要。 |
| `optional_reference.canonical_unit_ids[]` | `unit_id`、`name`、`non_binding` | 非 gold 的标签词典参考。 |

T1b 图片与页面事实注意事项：

```text
1. data.images[] 是 DOCX 内嵌图片资产事实。
2. clean_page_images[] 是 PDF/页面渲染事实，页面上包含文本、图片、表格等最终视觉结果。
3. annotated_page_images[] 是 T1a source_seq 与 T1b page/bbox 的结合加工结果。
4. 当前 overlay 只覆盖文本 source_seq；图片、文本框、drawing、unknown visible objects 还没有对象级 overlay。
5. 当前 PDF bbox 绑定主要来自 pdftotext 文本布局；非文本图片对象无法靠这一路稳定拿到 bbox。
```

### L1：统一输入投影层

输入：

```text
T1a document_facts
T1b render packet / render artifacts
```

L1 应当是 deterministic code 与 AI 的共同输入契约，而不是某条路线私有的临时 shape。

当前已有视图：

| 视图 | 当前消费者 | 当前字段 |
| --- | --- | --- |
| `source_tree` | deterministic structure code | `metadata`、`layers.package_global`、`layers.section_rules`、`layers.header_footer`、`layers.body_flow`、`layers.embedded_resources`、`layers.unknown_objects`、`indexes`、`warnings`、`data` |
| `template_agent_render_packet` | Module 2 agent / Module 1 observation / bridge | `render_status`、`source_render_hash`、`render_artifacts`、`page_text_index`、`page_layout_index`、`input_windows`、`optional_reference`、`round0_snapshot_id` |
| `build_t2_evidence()` | Module 1 T2 AI | `scope`、`source_render_hash`、`render_status`、`rows[source_seq,page_no,render_target_id,text,style]`、`page_thumbnails` |
| `build_t3_evidence()` | Module 1 T3 AI | `scope`、`source_render_hash`、`window_id`、`neighbor_context`、`rows[source_seq,page_no,render_target_id,text,style,style_details,raw_run_ids,logical_run_ids]` |
| `build_t4_evidence()` | Module 1 T4 AI | `scope`、`source_render_hash`、`render_status`、`render_available`、`page_images`、`page_layout_index[page_no,render_target_id,page_top_ratio,bbox]`、`global_layout_facts[sections,header_footer,numbering_definition_count]` |

L1 期望字段组：

| 期望视图 | 应包含字段 | 用途 |
| --- | --- | --- |
| `source_text_index` | `source_seq`、`source_ref`、`node_id`、`part_name`、`kind`、`order`、`text`、`style`、`style_details`、`text_facts`、`raw_run_ids`、`logical_run_ids`、`page_no`、`bbox`、`render_target_id`、`binding_status` | T2/T3 文本、样式、run、页面位置共同输入。 |
| `source_object_index` | `object_id`、`object_type`、`source_ref`、`source_seq_anchor`、`text`、`target`、`sha256`、`byte_count`、`relationship_id`、`binding_status`、`page_no`、`bbox`、`render_target_id` | 图片、文本框、脚注、内容控件、未知可见对象不能静默丢失。 |
| `layout_fact_index` | `sections`、`headers_footers`、`fields`、`breaks`、`numbering_refs`、`numbering_definitions`、`page_size`、`page_margins`、`page_numbering`、`effective_references` | T4 code/AI 共同版式事实输入。即用户所称「明点」（分节结构、每节页眉页脚、页码逻辑）的事实来源。 |
| `visual_page_index` | `clean_page_images`、`annotated_page_images`、`page_layout_index`、`source_bindings`、`render_engine`、`render_hash` | 视觉分页、页首/页尾、source_seq overlay、页面证据。 |
| `t2_input_view` | `source_text_index` 全文压缩 + `source_object_index` 摘要 + `visual_page_index` 页面图 | 单元识别、分页、开放标签判断。 |
| `t3_input_view` | AI/code T2 单元窗口内的 `source_text_index` + 对象切片 + 邻接上下文 | 元素策略、run/span 粒度判断。 |
| `t4_input_view` | `layout_fact_index` + `visual_page_index` + AI 自己的 T2 单元窗口 | 分节、页眉页脚、页码、页面视觉策略判断。 |
| `bundle_gate_view` | observation bundle + packet hash + source_seq/page/render_target universe | bridge 前 hash/schema/coverage/source binding gate。 |

## T2/T3/T4/T5/T6 输入消费

### T2：单元识别与分页

输入：

```text
deterministic: document_facts + source_tree + structure_candidates source_context
AI: L1.t2_input_view
```

当前输出：

| 路线 | 输出 | 核心字段 |
| --- | --- | --- |
| code | `unit_map` | `units[].unit_id/name/order/status/source_refs/source_seq_refs/source_range/source_seq_range/page/page_start/section_profile/confidence/flags/anchors/evidence` |
| AI | `ai_unit_observation` | `items[].unit_id/name/order/source_seq_refs/page_start/confidence/anchors/evidence_refs/flags/ai_rationale`、`coverage`、`unknown_items`、`open_questions`、`quality_report` |
| merged | `unit_map` | accepted T2 proposal 经过 comparison/reconciler 后重建。 |

当前输入风险：

```text
1. AI T2 evidence 白名单允许 style，但 page_text_index 当前没有 style。
2. 图片、文本框、unknown visible objects 没有进入 T2 AI 输入摘要。
3. 页面图在 projection_fallback 时为空；无图时视觉分页只能降级。
```

### T3：元素策略

输入：

```text
deterministic: generation_model，来自 structure_candidates
AI: L1.t3_input_view，窗口来自 AI 自己的 T2 unit observation
```

当前输出：

| 路线 | 输出 | 核心字段 |
| --- | --- | --- |
| code | `element_spec` | `elements[].stable_id/element_id/unit_id/order/policy/role/fill_source/source_refs/source_seq_refs/raw_run_ids/logical_run_ids/content/style/confidence/evidence/flags/generated/manual_semantics` |
| AI | `ai_element_observation` | `items[].element_id/unit_id/order/policy/role/content/source_seq_refs/raw_run_ids/confidence/evidence_refs/fill_source/generated/manual_semantics/ai_rationale/ai_decision_path` |
| merged | `element_spec` | accepted T3 proposal patch `candidate_policy` 后重建。 |

当前输入风险：

```text
1. AI T3 evidence 声称提供 style_details/run facts，但 page_text_index 没完整承载这些字段。
2. T3 可见对象输入偏文本；图片/文本框/未知对象不能稳定参与元素策略判断。
3. 元素级 gold 不完整时，不能只用 T3 准确率证明输入已经足够。
```

### T4：全局版式

输入：

```text
deterministic: document_facts.data.sections/header_footer/fields/numbering/breaks
AI: L1.t4_input_view
```

当前输出：

| 路线 | 输出 | 核心字段 |
| --- | --- | --- |
| code | `global_spec` | `section_profiles[]`、`default_font`、`page_numbering`、`header_footer`、`numbering_rules`、`flags` |
| AI | `ai_layout_observation` | `items[].section_profile_id/boundary/source_seq_refs/page_setup/header_footer/page_numbering/evidence_refs`、`default_font`、`page_numbering`、`header_footer`、`numbering_rules` |
| merged | 当前仍是 `global_spec` code 直通 | T4 hints 只进 `agent_t4_hints`，不 patch `global_spec/template_spec/plan`。 |

当前输入风险：

```text
1. T4 AI evidence 的 global_layout_facts 仍缺页眉页脚内容文本、fields、breaks、
   per-section source_seq 绑定；vision prompt 层不含任何版式事实。
2. observe_live 未接 source_template_docx/render_artifacts_dir 时没有真实 page images。
3. PDF 页面图里能看到图片和版式，但当前对象级 image/textbox/drawing bbox 没有独立绑定。
4. T4 route 文件名里的 merged 容易让人误解为 AI 已合并进 global_spec。
```

### T5：模板规格合并

输入：

```text
unit_map
element_spec
global_spec
document_facts hash
```

输出：`template_spec`。

核心字段：

```text
document_facts_ref
input_hashes
global
units[].section_profile
units[].section_profile_refs
units[].elements
review_flags
review_decisions
```

T5 不应直接读取 AI raw observation；它只消费 merged 后的 T2/T3/T4 主产物。

### T6：DOCX 执行与验证

输入：

```text
source_template_docx
template_generation_plan
template_spec/build_manifest inputs
```

输出：

```text
fillable_template.docx
build_manifest.json
verification_report.json
```

T6 风险来自上游输入错误的传递：T2/T3 accepted proposal 会改变 `unit_map/element_spec/template_spec`；T4 AI hints 当前不会改变 `global_spec`。

## 图片与 PDF 页面图的输入边界

本轮必须区分三类“图片”：

| 类型 | 来源 | 当前状态 | 下游风险 |
| --- | --- | --- | --- |
| DOCX 内嵌图片资产 | `data.images[]` | 有 `target/sha256/byte_count/source_ref/paragraph_index` | 未进入 L1 对象视图，T2/T3/T4 AI 可能不知道模板里有图片资产。 |
| PDF 页面渲染图 | `clean_page_images[]` | packet 支持，但 observe_live 默认未接真实渲染 | T4 与视觉分页长期 abstain 或降级。 |
| annotated overlay 图 | `annotated_page_images[]` | 当前只标注文本 source_seq bbox | 图片、文本框、drawing、unknown objects 无对象框，AI 无法把视觉对象稳定回绑到 T1 对象事实。 |

期望语义：

```text
1. DOCX image asset 是结构事实，不等于页面图。
2. PDF page image 是视觉事实，不等于源对象事实。
3. annotated overlay 是 T1a + T1b 的结合加工结果，用于把页面视觉判断回绑到 source_seq/object_id。
4. 每个对象必须有 binding_status：
   - bound_to_page_bbox
   - bound_to_page_only
   - not_render_bound
   - unsupported_object_type
   - render_unavailable
5. 不允许因为图片/对象没有 text，就从 L1 输入消失。
```

## 疑似根因

```text
1. 历史上先打通 deterministic T1->T6，后加 AI route，导致 code 输入和 AI 输入不是同一个投影契约。
2. render packet 最初是 agent 辅助视图，不是完整 L1 输入契约，因此只投了 prompt 需要的字段。
3. Module 1 为防污染做了严格白名单，但白名单与 page_text_index 实际字段没有同步收口。
4. PDF render/bbox/overlay 能力已经存在，但运行入口和 T4 evidence 没有全部接上。
5. 图片资产事实和页面图片事实语义相近但来源不同，没有建统一 object/page binding 层。
6. observation bridge 复用 proposal gate，但缺少 bundle 级 schema/coverage gate。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. T1a 已能抽取 body_flow、runs、paragraphs、tables、headers_footers、sections、fields、numbering、images、text_boxes、unknown objects。
2. T1b 已有真实 render packet 能力：DOCX->PDF->PNG、PDF bbox、source_seq binding、annotated SVG。
3. Module 1 evidence 有字段白名单和防火墙，能阻止 unit_map/element_spec/template_policy 等结论字段进入 AI evidence。
4. AI observation 已经可以通过 observation_bridge 转成 T2/T3 proposal，并复用 comparison/reconciler。
5. T4 hints 明确是 advisory，不直接改 global_spec。
```

未解决：

```text
1. 缺少正式 L1 输入投影契约，code 与 AI 输入不对齐。
2. style/style_details/text_facts/run facts 没完整进入 page_text_index / AI evidence。
3. T4 AI 输入的明点事实仍不完整：global_layout_facts 已覆盖 sections 元数据与
   header_footer 引用，但缺页眉页脚内容文本、fields、breaks、per-section seq 绑定，
   且 vision prompt 层未注入（T4 切片的收口方案见 plan-10 Phase 1）。
4. observe_live 默认不产真实页面图，导致 T4 视觉输入断链。
5. DOCX 图片资产、文本框、drawing、unknown visible objects 没有进入统一 source_object_index。
6. annotated overlay 只覆盖文本 source_seq，不覆盖对象级 image/textbox/drawing/unknown object。
7. observation bundle 进入 bridge 前缺 schema/coverage invariant 校验。
8. NOT_AVAILABLE 与 abstain 的占位语义仍可能误导 route eval。
```

## 后续验收门禁

```text
1. 存在文档化 L1 输入契约，列明每个字段的 producer、consumer、缺失语义和是否允许给 AI。
2. T2/T3/T4 AI evidence 与 deterministic code 的输入事实来源可对齐，不再出现“code 看得到、AI 看不到”的隐性缺口。
3. page_text_index 至少能承载 text/style/style_details/text_facts/raw_run_ids/logical_run_ids/page_no/bbox/render_target_id。
4. T4 evidence 至少能承载 sections/header_footer/fields/numbering/breaks/page images/page_layout_index。
5. DOCX images/text_boxes/unknown visible objects 在 L1 中有对象记录；不能绑定页面时显式 binding_status。
6. 真实 render 成功时，clean_page_images、annotated_page_images、source_bindings、page_layout_index 都在同一次 run bundle 内可追溯。
7. 外部 ai_observation_bundle 进入 bridge 前必须完成 hash/schema/coverage/source binding 校验。
8. 未运行 AI 时输出纯 NOT_AVAILABLE；AI 运行后无证据时才输出 abstain，不再混用。
```

本文只记录输入事实与投影缺口，不包含实施方案。若决定修复，应另建 plan 文档并在 frontmatter `source_issue` 指向本 issue。

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-03 | 初稿：摊开 T1a/T1b/L1 输入投影契约与各阶段消费缺口 |
| 2026-07-03 | 修订：纠正 T4 evidence 表述（global_layout_facts 已实现，剩余缺口收窄为页眉页脚内容/fields/breaks/seq 绑定/vision prompt 层）；补明点术语映射（明点 → layout_fact_index）；T4 输入切片由 plan-10 Phase 1 承接；cross_issue 增加 issue-10/11 |
