---
status: partially_implemented
implemented: phase-2-deterministic-backbone
implemented_at: 2026-06-25
owner: template-generation
stage: T2
created: 2026-06-25
last_updated: 2026-06-25
version: 4
review_patch:
  - claude-code-review
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/artifacts.py
related_docs:
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md
  - docs/plans/template-parse-refactor-t2-visual-pagination.md
  - docs/plans/t2-unit-segmentation-correct-logic.md
---

# T2 单元识别：开放标签 + AI 视觉推理 + 分页策略方案

> **【实施状态 — 2026-06-25】本文档是 T2 设计总纲；其中 Phase 2 确定性主干已落地，其余 Phase 已拆分。**
>
> - **已实施完成（§6 / §15 Phase 2 确定性主干）**：T2 派生信号层、TOC block segmenter（加锁）、`text_properties` candidate-only、canonical_title + alias 注册表 + `custom_unit` 兜底标签模型、variant/form 标注。三校结构门禁通过（湖南/南农/北大 TOC 20/20·25/25·17/17，`other`=0，leak=0）。对应代码见 `structure_candidates.py`，单测见 `tests/unit/test_t2_unit_map.py`，门禁脚本 `scripts/t2_metrics.py`。
> - **尚未实施**：Phase 0（feature flag / page_policy 三态字段预留）、Phase 1A/1B（渲染子项目）、Phase 3（AI 视觉通道）、Phase 4（reconciler）、Phase 5（视觉/AI 门禁）。
> - **page_policy / 视觉分页的落地细化已拆分到独立计划**：`docs/plans/template-parse-refactor-t2-visual-pagination.md`（含 Phase 0~5 的文件级实施步骤）。本文档保留为设计总纲与契约依据。
> - 修复前的具体 issue 现象见已解决的 `docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md`（勿据其旧数据定位新问题）。

## 0. 一句话结论

T2 不应继续只靠规则和关键词表解决所有学校模板差异。新版方案采用：

```text
T1 fact-only
+ deterministic T2 derived signals
+ block-first segmentation
+ open label taxonomy
+ custom_unit fallback
+ rendered / annotated page images
+ AI visual structure pass
+ T2 reconciler
+ unit-level page_policy
+ downstream generic contract
+ deterministic fallback gates
```

核心判断：

```text
1. 边界识别不能依赖预设关键词。
2. 核心语义标签保持闭集，学校/模板自定义章节走开放扩展。
3. AI 可以提供视觉证据，尤其是未知章节、表单块、无 mechanical break 的强制分页意图。
4. AI 不直接写最终 unit_map；最终结果必须由 T2 reconciler 合并规则证据和 AI 证据。
5. 确定性主干必须先独立可用；AI 是增强和兜底，不是 P0 结构修复的唯一依赖。
6. 湖南 TOC 欠切必须由 Phase 2 deterministic path 修复；AI 只能兜底，不能成为唯一修复路径。
7. 强制分页策略属于 T2 的 unit-level page_policy；具体 page break / section break 的 OOXML 实现属于 T4。
```

## 1. 背景问题

当前 T2 的问题不是单一阈值问题，而是多个机制叠加：

1. **TOC 没有作为 block 先整体识别**  
   目录标题、目录条目、真实章节标题仍然在同一套 boundary score 中竞争。结果可能是目录条目被摘要、正文、参考文献等关键词抢走，也可能是整块目录被前一个单元吞掉。

2. **`text_properties` 单独命中即可切正式 unit**  
   `centered AND (large_font OR bold)` 在真实模板里太宽，会把局部标题、表头、说明段标题、阶段标签误切成顶层单元。

3. **标签器闭集过窄**  
   切出了边界，但标题不在短词表里，就大量落成 `other`。

4. **学校/学院/专业存在自定义章节**  
   每个学校都可能有任务书、开题报告、中期检查表、评审意见、答辩材料、过程记录、专业附件等。这些标题不适合全部写进全局核心标签表。

5. **有些强制分页没有显式 DOCX 机械信号**  
   源模板里可能没有 `page_break_before`、`sectPr`、style break 等明确事实，但从渲染效果上能看出某个一级单元必须另起页。例如：上一页还有明显空白，下一个一级标题仍然出现在新页页首；多个同级单元都重复这个模式。

因此，本方案把 T2 定义为 **unit contract 生成层**。T2 输出每个 unit 的：

```text
boundary
block ownership
label / label_status
custom_unit 状态
confidence
evidence
page_policy
open_questions / review queues
```

## 2. 层级职责边界

### 2.1 总体边界

| 层级 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| **T1 facts** | 抽取源文档客观事实：文本、样式、表格、显式分页/分节、段落顺序、容器引用 | 不判断是不是目录、标题、单元、强制分页 |
| **Render artifacts** | 把源模板渲染成页面图片，并把 `source_seq` / 段落定位回绑到页面 | 不做结构语义判断 |
| **T2 unit map** | 单元边界、block 归属、单元标签、custom_unit、unit-level page_policy、置信度、问题队列 | 不解析单元内部字段，不决定具体 OOXML 实现 |
| **T3 element map** | 单元内部结构：字段、表格项、表单项、小节、段内元素 | 不决定一级单元是否另起页 |
| **T4 renderer/generator** | 根据 T2 page_policy 落实 page break / section break / 页码机制 | 不重新判断单元语义和分页意图 |
| **T5 validation** | 校验核心单元、custom_unit 合法性、page_policy 可消费性 | 不要求所有 unit 都属于 core label |
| **T6 rendering eval** | 评估生成结果与模板视觉/结构一致性，记录 LibreOffice / Word 渲染差异 | 不把渲染近似当作源文档机械事实 |

### 2.2 强制分页的归属

强制分页需要拆成三层：

```text
mechanical_break
  源 DOCX 中实际存在的分页/分节/样式分页事实。

visual_new_page_pattern
  渲染结果中表现出的新页开始模式。

unit_generation_page_policy
  生成新文档时，这个 unit 是否应强制另起页。
```

归属如下：

```text
T1:
  负责 mechanical_break fact。

Render artifacts:
  负责 visual_new_page_pattern 的可观测输入，例如 page image、page index、bbox、上一页空白比例。

T2:
  负责推断 unit_generation_page_policy。

T4:
  负责把 unit_generation_page_policy 转成具体实现。
```

关键原则：

```text
没有 mechanical_break
≠
生成时不需要强制分页
```

如果源文档没有显式分页事实，但视觉模式高度一致，T2 可以输出：

```json
{
  "page_policy": {
    "generation_policy": {
      "requires_new_page": true,
      "source": "ai_visual_inference",
      "confidence": "high"
    }
  }
}
```

但 T2 不能伪造 T1 事实，不能说源文档“实际存在 page_break_before”。

## 3. 目标与非目标

### 3.1 目标

1. 保持 T1 fact-only：T1 只输出客观事实，不输出“是不是目录/标题/强制分页”这类语义判断。
2. T2 从 T1 原子事实派生结构软信号，并把证据写入 T2 artifact。
3. Phase 2 确定性主干必须先独立可用；三校结构门禁不依赖 AI。
4. 引入 AI visual structure pass，使用页面图片判断视觉结构、未知章节、表单块、强制分页模式。
5. AI 输出必须通过 `source_seq` / page / bbox 回绑到源文档，不能只输出自然语言结论。
6. 确定性失败时，AI high confidence 且可绑定的 block/unit/page_policy 允许被 reconciler 接受为救场证据。
7. 先识别 TOC / variant / form-like block，再对剩余段落做通用 boundary。
8. 切边界和贴标签彻底分离。
9. 核心单元用闭集标签，保证下游稳定。
10. 标题变体通过 alias registry 解决。
11. 学校/模板自定义章节通过 `custom_unit` 保留，不再无差别降成 `other`。
12. T2 输出 unit-level `page_policy`，包含机械事实、视觉观察、生成策略三层。
13. 未确认的新标题进入 taxonomy review queue，后续可提升为 global / school / template alias。
14. 对事实不足或判断不足的区域显式 `abstain`，输出 `open_questions` 和 `missing_facts`。
15. 明确无 AI 降级路径：关闭 AI 后，确定性结构指标仍要过三校门禁，尤其湖南 TOC 20/20。
16. 明确 T3/T4/T5/T6 对 `custom_unit` 和 `page_policy` 的消费契约，避免下游继续假设 `unit_id ∈ CORE_SET`。

### 3.2 非目标

1. 不在 T1 恢复或新增 `is_toc_entry`、`likely_unit_heading`、`large_font` 等语义字段。
2. 不在 T2 消费旧 `structural_signals` 或旧语义字段。
3. 不试图一次性枚举所有学校的所有章节标题。
4. 不让 AI 直接覆盖最终 `unit_map.units[]`。
5. 不让 AI 生成或改写正文内容。
6. 不在本轮实现完整 variant model；本轮最多做 `variant_block` 或 `other/custom + variant_block_detected`。
7. 不解决 T3 段内元素切分。
8. 不在 T2 决定 page break / section break 的底层 OOXML 写法；这是 T4 责任。

## 4. 核心原则

### 4.1 T1 只产事实，T2 才做判断

T1 应输出：

```text
text
style_name / style_id
has_tab
trailing_token
leader_chars
paragraph.alignment
dominant_run.font_size_pt
dominant_run.bold
page_break_before
sectPr / breaks
container_ref / table_id / cell_id
```

T1 不输出：

```text
is_toc_entry
is_spacing_line
looks_like_instruction_text
likely_unit_heading
large_font
short_text
requires_new_page
```

这些判断由 T2 或渲染/视觉链路在 T2 artifact 中派生。

### 4.2 切边界和贴标签是两步

```text
boundary detection:
  问题是“这里是不是一个新的顶层单元开头？”

labeling:
  问题是“这个已经切出来的单元应该叫什么？”
```

关键词不能直接切边界。关键词只能在候选单元形成之后，用于贴标签或辅助提升置信度。

### 4.3 先 block，后 boundary

目录、变体块、表单/表格区这类整块结构必须先被圈走。被 block 接收的段落加锁，不再参与普通章节 boundary 竞争。

### 4.4 标签体系采用“核心闭集 + 开放扩展”

核心标签是闭集，例如：

```text
toc
abstract_cn
abstract_en
body_main
references
acknowledgement
appendix
integrity_statement
post_forms
```

但真实学校模板中存在大量自定义章节。因此标签层必须有开放 fallback：

```text
core_matched
alias_matched
school_alias_matched
template_alias_matched
custom_detected
unmapped
candidate_only
```

未知但高置信的一级单元应该成为 `custom_unit`，而不是 `other`。

### 4.5 AI 是视觉证据提供者，不是最终裁判

AI 可以输出：

```text
这个 source_seq 视觉上像一级单元标题
这个 block 视觉上像目录 / 表单 / 变体块
这个标题更像某个 core label 或 custom_unit
这个 unit 是否表现出强制另起页意图
```

AI 不可以直接做：

```text
绕过 source_seq 生成最终 unit
伪造 T1 机械事实
修改原文内容
凭空创建源文档中不存在的章节
决定 T4 用 page break 还是 section break
```

所有 AI 输出必须经过 T2 reconciler：

```text
AI suggestion
  + deterministic evidence
  + source_seq binding
  + conflict checks
  + confidence rules
  => final unit_map
```

### 4.6 宁可保留未知，也不要乱猜

当边界证据强，但标签不在核心闭集里：

```text
输出 custom_unit
保留 raw_title / normalized_title / display_name
记录 label open_question
进入 taxonomy review queue
```

当边界证据也弱：

```text
只输出 boundary_candidate / open_question
不进入正式 unit_map.units[]
```

当分页策略不确定：

```text
page_policy.generation_policy.requires_new_page = "unknown"
进入 page_policy_review
不直接强制分页
```

## 5. 运行时流水线

推荐运行时顺序如下：

```text
Source template
  ↓
T1 document_facts
  ↓
Render clean page images
  ↓
Render annotated page images with source_seq labels
  ↓
Build page_text_index / page_layout_index
  ↓
T2 text_facts adapter
  ↓
T2 deterministic derived signals
  - toc_title_like
  - toc_entry_like
  - instruction_like
  - spacing_line_like
  - unit_heading_like
  - variant_marker_like
  - form_block_like
  - mechanical_break_like
  ↓
Deterministic block segmenter
  - toc block
  - variant block
  - form/table block candidate
  ↓
Deterministic boundary candidates
  ↓
AI visual structure pass
  - visual unit headings
  - visual block candidates
  - label suggestions
  - page policy suggestions
  ↓
T2 reconciler
  - bind AI output to source_seq
  - merge deterministic and AI evidence
  - reject unbound / hallucinated items
  - resolve conflicts by fixed priority table
  ↓
unit span creation
  ↓
canonical title normalization
  ↓
label classification
  - core closed-set match
  - global alias match
  - school alias match
  - template alias match
  - custom_unit fallback
  - unmapped/candidate
  ↓
page_policy finalization
  ↓
confidence calculation
  ↓
open_questions / missing_facts / taxonomy_review_queue / page_policy_review
```

## 6. 确定性主干：Phase 2 必须先独立可用

AI 不能成为 P0 结构修复的唯一依赖。Phase 2 需要在 `t2_ai_visual_enabled=false` 时通过三校结构门禁。

### 6.1 T2 派生信号层

T2 派生信号层只读取 T1 原子事实。

```python
def _t2_text_facts(entry) -> dict:
    return {
        "text": ...,
        "normalized_text": ...,
        "style_name": ...,
        "style_id": ...,
        "has_tab": ...,
        "trailing_token": ...,
        "leader_chars": ...,
        "alignment": ...,
        "font_size_pt": ...,
        "bold": ...,
        "page_break_before": ...,
        "section_break_before": ...,
        "container_ref": ...,
        "table_id": ...,
        "cell_id": ...,
    }
```

派生信号：

```python
def _looks_like_toc_title(entry) -> Signal: ...
def _looks_like_toc_entry(entry) -> Signal: ...
def _looks_like_instruction(entry) -> Signal: ...
def _looks_like_spacing_line(entry) -> Signal: ...
def _looks_like_unit_heading(entry) -> Signal: ...
def _looks_like_variant_marker(entry) -> Signal: ...
def _looks_like_form_block(entry) -> Signal: ...
```

每个 `Signal` 包含：

```json
{
  "value": true,
  "confidence": "medium",
  "evidence": [
    {"fact": "alignment", "op": "eq", "value": "center"},
    {"fact": "font_size_pt", "op": ">=", "value": 14}
  ],
  "missing_facts": []
}
```

输出位置：

```text
template_structure_candidates.t2_derived_signals_by_source_seq
unit_map.debug.t2_derived_signals_by_source_seq
t2_input.contexts[].entries[].t2_derived_signals
```

硬约束：

```text
1. 不写回 document_facts。
2. 字段名带 t2_ 或只放在 T2 artifact 下。
3. 不读取 structural_signals。
4. 不接受 is_toc_entry / likely_unit_heading 作为输入。
```

### 6.2 TOC block segmenter

TOC block 必须在通用 boundary 前运行。

```text
强 TOC block:
  toc_title_like
  + 后续 >= 2 条 toc_entry_like
  => confidence=high/medium

弱 TOC block:
  连续 >= 3 条 toc_entry_like
  + 回看前 1-3 段找弱 toc_title_like
  + 找不到标题也可建 low confidence toc block
  => 必须打 open_question
```

TOC block 内的 entry 加锁：

```text
locked_by_block = "toc"
```

加锁后，任何目录条目中的“摘要”“前言”“参考文献”等关键词都不能触发普通 unit boundary 或 label。

Phase 2 硬门禁：

```text
- 湖南 TOC 20/20 条目必须由 deterministic path 归入 toc。
- 南农 TOC 25/25 条目归入 toc。
- 北大 TOC 17/17 条目归入 toc，或达到本轮明确的 deterministic 门禁。
- 非 toc 单元中的 toc_entry_like 数为 0。
```

### 6.3 variant block

短期不做完整 variant model。规则：

```text
1. 检测 variant_marker_like：
   农理工科 / 文科 / 文法经管 / XX类专业用 / 以下...用

2. 如果重复闭集单元或重复表单块出现在 variant marker 附近：
   聚合为 variant_block 或 custom_unit + variant_block_detected。

3. variant block 内部不继续细碎切成多个 other。
```

### 6.4 form/table block candidate

规则侧先识别：

```text
table density high
+ title-like line before table
+ title 或邻近文本包含 表/单/意见/记录/检查/评审/答辩/任务/开题
```

AI 可补充：

```text
这是一页或多页表单块
标题是 source_seq X
表格从 source_seq Y 开始
该表单块是否是顶层 unit
```

### 6.5 boundary detection

基本规则：

```text
explicit page/section break + heading evidence:
  strong boundary

top-level heading style:
  strong boundary

text_properties alone:
  candidate_only

text_properties + core/alias label:
  formal boundary

text_properties + strong_context:
  formal boundary as custom_unit candidate

keyword alone:
  不切 boundary，只参与 label
```

注意：`T1 mechanical_break` 本身不能单独切 top-level boundary。它是 page_policy 的强证据；只有同时有 heading/block/unit evidence 时，才可支持 boundary。

### 6.6 unknown heading promotion

为了解决学校自定义章节，必须允许未知标题升格：

```text
text_properties alone:
  candidate_only

text_properties + core_label:
  formal boundary

text_properties + strong_context:
  formal boundary as custom_unit / unmapped_unit
```

`strong_context` 可包括：

```text
1. page_break_before 或 section_break_before。
2. AI 看到 title_at_page_top。
3. AI 看到 previous_page_has_remaining_space。
4. 标题出现在 TOC block 中的一级条目。
5. 前后都是已识别一级单元，当前位置像独立顶层块。
6. 后面跟随成段内容或完整表格/表单块。
7. 非表格内部、非目录条目、非说明文字。
```

TOC 相关强上下文有额外约束：

```text
“标题出现在 TOC block 中的一级条目”只有在 TOC block 已经被 deterministic 或 AI block 确认后才生效。
不能反过来用未确认 TOC 证明自身。
```

### 6.7 label model：核心闭集 + alias + custom_unit

标题归一化：

```python
def canonical_title(text: str) -> str:
    text = strip_format_annotations(text)
    text = remove_placeholders(text)       # □、×、__
    text = remove_leader_and_page_suffix(text)
    text = normalize_width_case_space(text)
    text = normalize_cn_punctuation(text)
    return text
```

`label_status`：

```text
core_matched
alias_matched
school_alias_matched
template_alias_matched
custom_detected
unmapped
candidate_only
```

`other` 不再表示“没匹配上核心标签”。`other` 只用于：

```text
1. 明显不是一级单元的杂项块。
2. 变体块短期兜底。
3. 边界和标签都不稳定的低置信兜底。
```

未知但高置信的一级章节应输出 `custom_unit`，而不是 `other`。

## 7. Render 工程子项目

AI 视觉推理的最大工程增量不是 prompt，而是 DOCX → 页面图 → `source_seq` 回绑。该能力应作为独立子项目管理，不能隐含在 T2 小改里。

### 7.1 渲染引擎选择

可选路线：

```text
LibreOffice:
  优点：CI / Linux 环境容易自动化，已有 pdftoppm 类脚本可复用。
  风险：和 Microsoft Word 的分页、字体替换、表格布局可能存在差异。

Microsoft Word / Office automation:
  优点：最接近真实用户编辑环境。
  风险：CI、容器化、授权、跨平台自动化成本高。

第三方渲染服务:
  优点：可以稳定产出图片和布局。
  风险：引入外部依赖和服务成本，回放一致性要额外保证。
```

短期建议：

```text
Phase 1 / 1.5 使用 LibreOffice + PDF + pdftoppm 建立可回放基线。
把 render_engine、render_version、font_fallback、pdf_hash、image_hash 写入 artifact。
T6 继续记录 LibreOffice≈Word 的近似风险，不把 LibreOffice 视觉结论伪装成 Word 绝对真值。
```

### 7.2 source_seq 标注和 bbox 分级

bbox 能力按三档推进：

```text
Tier 0: page_no + page_order + annotated source_seq
  能做：AI 结构候选、block 兜底、粗粒度 page_policy。
  不能做：可靠 blank_ratio、可靠 title_at_page_top 数值判断。
  降级：page_policy.observed 中 bbox 相关字段为 unknown。

Tier 1: approximate bbox
  来源：PDF text extraction / layout heuristics / 段落顺序估计。
  能做：page_top_ratio、page_bottom_ratio、粗略 previous_page_blank_ratio。
  降级：强制分页最多 medium，除非有 peer pattern 和人工 fixture 验证。

Tier 2: reliable paragraph bbox
  来源：稳定 PDF layout 映射或 Word API。
  能做：high-confidence visual page_policy、blank_ratio 门禁、精确 source_seq 回绑。
```

硬规则：

```text
没有 annotated source_seq：AI 不能进入正式候选。
没有 bbox：AI 可以帮助 label / block，但 page_policy 只能 high 依赖 mechanical；视觉分页推断默认 unknown 或 medium 以下。
blank_ratio 无法计算：不能仅凭 title_at_page_top 判定强制分页。
```

### 7.3 Phase 1.5 交付边界

建议把 Phase 1 拆成：

```text
Phase 1A:
  clean page images
  annotated source_seq images
  page_text_index
  render hash

Phase 1B / 1.5:
  page_layout_index
  bbox
  page_top_ratio / page_bottom_ratio
  previous_page_blank_ratio
  peer_unit visual pattern support
```

Phase 1A 足够支持 AI 结构兜底；Phase 1B 才支持较高置信的视觉强制分页。

## 8. AI 视觉通道

### 8.1 AI 输入设计

AI 不应只拿裸图片。最佳输入是一组可回放、可定位的结构化上下文。

必需输入：

```text
1. clean_page_images
   原始渲染页面图片，用于观察真实版式。

2. annotated_page_images
   在段落旁边覆盖 source_seq，例如 [24]、[25]、[26]。
   AI 必须引用这些 source_seq 输出判断。

3. page_text_index
   每页包含 source_seq、source_ref、文本、是否表格内、段落顺序。

4. page_layout_index
   每个 source_seq 的 page_no、bbox、page_top_ratio、page_bottom_ratio。
   如果短期拿不到精确 bbox，至少要有 page_no 和页面内大致顺序。

5. t1_atomic_facts
   alignment、font_size、bold、style_name、page_break_before、sectPr、table_id 等。

6. deterministic_candidates
   规则侧已识别的 toc candidates、boundary candidates、custom candidates、open_questions。

7. known_taxonomy
   core labels、global aliases、school aliases、template aliases。
```

可选输入：

```text
previous_page_blank_ratio
peer_unit_patterns
source_render_hash
prompt_version / schema_version
```

输入窗口策略：

```text
full-pass overview:
  给 AI 全文低分辨率缩略图 + page index，让它识别整体单元结构和分页模式。

focused-pass review:
  对 deterministic pass 中低置信的区间，给 AI 高分辨率局部页面 + annotated source_seq。
```

湖南这类 300+ 段、多表格模板的整本高清图输入成本高、context 压力大，因此 Phase 3 需要预留 focused-pass 接口。即使第一版只实现 full-pass，也要预留缓存、prompt_version、render_hash 和候选区间切片。

### 8.2 AI 输出契约

AI 必须输出 JSON，不输出散文结论。

顶层 schema：

```json
{
  "schema_version": "t2_ai_visual_response.v1",
  "prompt_version": "...",
  "source_render_hash": "...",
  "model": "...",
  "unit_candidates": [],
  "block_candidates": [],
  "page_policy_candidates": [],
  "conflicts": [],
  "open_questions": []
}
```

unit candidate：

```json
{
  "candidate_id": "ai-unit-001",
  "title_source_seq": 60,
  "start_source_seq": 60,
  "end_source_seq": 88,
  "page_no": 8,
  "raw_title": "毕业论文（设计）开题报告",
  "normalized_title": "毕业论文设计开题报告",
  "structural_type": "top_level_unit",
  "label_suggestion": {
    "canonical_label_id": null,
    "label_status": "custom_detected",
    "display_name": "毕业论文（设计）开题报告"
  },
  "visual_evidence": [
    "title_at_page_top",
    "centered_or_prominent_title",
    "followed_by_form_like_content"
  ],
  "confidence": "high"
}
```

block candidate：

```json
{
  "candidate_id": "ai-block-001",
  "block_type": "toc",
  "start_source_seq": 24,
  "end_source_seq": 49,
  "page_range": [2, 3],
  "visual_evidence": [
    "toc_title_visible",
    "multiple_entries_with_leaders_and_page_numbers"
  ],
  "confidence": "high"
}
```

page policy candidate：

```json
{
  "candidate_id": "ai-page-policy-001",
  "unit_title_source_seq": 60,
  "observed": {
    "starts_new_page": true,
    "title_at_page_top": true,
    "previous_page_has_remaining_space": true,
    "peer_units_follow_same_pattern": true,
    "source": "rendered_page_image",
    "confidence": "high"
  },
  "generation_policy_suggestion": {
    "requires_new_page": true,
    "source": "ai_visual_inference",
    "confidence": "high",
    "reason": [
      "unit title appears at top of a new page",
      "previous page has visible remaining space",
      "peer units follow the same new-page pattern"
    ]
  }
}
```

输出硬约束：

```text
1. 每个 unit_candidate 必须有 title_source_seq 和 start_source_seq。
2. 每个 source_seq 必须存在于 page_text_index。
3. AI 不能输出源文档中不存在的标题。
4. AI 不能修改 raw_title。
5. AI 不能直接输出 final unit_id，必须输出 label_suggestion。
6. 如果无法绑定 source_seq，必须放入 open_questions，不能进入 candidates。
7. page_policy_candidate 必须绑定到 unit_title_source_seq。
8. top-level schema 无效时整批 AI fallback。
9. 单个 candidate 无效时只拒绝该 candidate，允许 partial accept。
10. candidate 被接受、拒绝、去重都必须写入 t2_reconciler_trace。
```

### 8.3 Prompt 关键约束

```text
- A title appearing on a new page is not enough by itself to infer forced pagination.
- Forced pagination is more likely when the previous page has visible remaining space and peer units follow the same pattern.
- TOC entries are not top-level units.
- Table headers and section labels inside a form are not top-level units unless they begin a whole template unit.
- Unknown school-specific sections should be marked as custom_detected, not forced into existing core labels.
- Only source_seq labels visible in the annotated images and present in page_text_index may be referenced.
- Return JSON only.
```

### 8.4 CI 不调用 live model

CI 单测不调 live API。所有 AI 测试使用 fixture：

```text
t2_ai_response.valid.json
t2_ai_response.invalid.json
t2_ai_response.partial.json
t2_ai_response.conflict.json
```

可选 eval job：

```text
- 非 CI gate。
- 可以定期调用 live model 跑小规模模板回归。
- 产出 drift report：accepted/rejected candidate 差异、page_policy 差异、token/cost。
- live eval 失败不能阻塞 Phase 2 deterministic P0 修复 merge。
```

## 9. T2 reconciler

T2 reconciler 是最终裁判，负责把以下证据合并：

```text
T2 deterministic signals
T2 deterministic block candidates
T2 deterministic boundary candidates
AI visual unit candidates
AI visual block candidates
AI page_policy candidates
alias registry
T1 mechanical facts
render layout facts
```

### 9.1 Reconciler 有序优先级表

reconciler 必须按固定顺序合并，避免不同实现各自为政：

| 优先级 | 输入/条件 | final 行为 |
| ---: | --- | --- |
| 1 | locked block：`toc` / `variant` / `form` | block 范围内段落不再参与普通 boundary；AI 不能拆 locked block |
| 2 | T1 mechanical_break / section_break | 只更新 `page_policy.mechanical` 和 `generation_policy`；不单独切 boundary |
| 3 | deterministic high confidence boundary / block | 接受为 final；AI 只能补证据或提出 conflict |
| 4 | deterministic 与 AI 一致 | 接受为 final，并提升 confidence / evidence |
| 5 | AI high confidence + deterministic `candidate_only` | 可升格为 formal boundary / block；必须 source_seq 可绑定 |
| 6 | AI high confidence block + deterministic 未识别 | 可作为兜底接受，TOC 需满足 §9.2 case 2 |
| 7 | 冲突未解、source_seq 不可绑定、证据不足 | `abstain` + `open_question`，不得写入正式 unit |

补充规则：

```text
- block_candidate 与 unit_candidate 重叠时，block 优先；block 内 unit_candidate 默认拒绝或降为 block 内部元素候选。
- 多个 candidate 的 title_source_seq 相同或 source_seq range 高度重叠时，按优先级和 confidence 去重；被去重项写入 trace。
- deterministic high confidence 不等于不可审计；AI 冲突必须记录，但不在本轮自动推翻。
- AI-only 且 deterministic 完全无候选时，只有 block 兜底可以进入 final；unit boundary 必须至少有可解释 strong_context。
```

### 9.2 block 相关规则

```text
case 1: deterministic locked block 优先
  deterministic TOC / variant / form block high confidence
  => final locked block
  => AI 只能补充证据，不能把 block 内条目拆走，也不能让块内关键词触发普通 boundary

case 2: AI 兜底 TOC block
  deterministic 未识别 TOC block
  + AI block_candidate(block_type=toc) high confidence
  + start_source_seq / end_source_seq 均可绑定
  + block 内存在足够 toc_entry_like 或视觉目录证据
  + 与已锁定 block 不冲突
  => reconciler 接受 AI toc block
  => 注入 toc block boundary
  => locked_by_block="toc"
  => 写入 t2_reconciler_trace.accepted_ai_candidates

case 3: AI 兜底 variant / form block
  deterministic 未识别 block
  + AI block_candidate high confidence
  + source_seq range 可绑定
  + range 不跨越已确认核心 unit
  => 可接受为 locked block 或 block_candidate
  => 低于 TOC 优先级；冲突时进入 open_question
```

注意：AI 兜底 TOC 是为 deterministic 欠切准备的安全网，不能替代 Phase 2 的确定性 TOC 修复。湖南 TOC 必须在关闭 AI 时也能 20/20 归入 `toc`。

### 9.3 boundary / label 相关规则

```text
case 4: AI 提出 top_level_unit，但 source_seq 不存在
  => reject，进入 open_question

case 5: AI 提出 top_level_unit，source_seq 存在，且 deterministic side 至少 candidate_only
  => 可升格为 formal boundary
  => confidence=medium/high 取决于证据数量

case 6: AI 提出 custom_unit，规则侧 label unknown，但边界证据强
  => final custom_unit
  => label_status=custom_detected
  => taxonomy_review_queue

case 7: deterministic high confidence boundary
  => final boundary
  => AI 一致时补证据；AI 冲突时记录 conflict，但不直接推翻
```

### 9.4 page_policy 相关规则

```text
case 8: T1 有 explicit page_break / section_break
  => generation_policy.requires_new_page=true
  => source=mechanical_fact
  => confidence=high
  => 注意：mechanical_break 只直接影响 page_policy；不能在没有 heading/block 证据时单独切 top-level boundary

case 9: T1 无 explicit break，但 AI 看到 title_at_page_top + previous_page_has_remaining_space + peer pattern
  => generation_policy.requires_new_page=true
  => source=ai_visual_inference
  => confidence=high/medium

case 10: AI 看到新页页首，但上一页写满或没有 peer pattern
  => generation_policy.requires_new_page=unknown
  => page_policy_review
```

### 9.5 unresolved conflict

```text
case 11: AI 与 deterministic side 冲突，且无法按优先级表解决
  => 不做隐式保守猜测
  => final_decision=abstain 或 candidate_only
  => 写 open_question(kind=boundary|label|page_policy|block_range)
  => 写 conflict evidence
```

冲突结构：

```json
{
  "conflict_id": "conflict-001",
  "kind": "boundary | label | page_policy | block_range",
  "source_seq_range": [60, 88],
  "deterministic_decision": "candidate_only",
  "ai_decision": "formal_boundary",
  "final_decision": "formal_boundary",
  "reason": "ai visual evidence plus page_top pattern promoted unknown heading",
  "confidence": "medium"
}
```

### 9.6 Partial accept 与 fallback

```text
top-level JSON schema 无效:
  整个 AI response fallback，T2 继续使用 deterministic path。

单个 candidate schema 无效:
  拒绝该 candidate，保留其它有效 candidate。

source_seq 不存在或 raw_title 无法对齐:
  拒绝该 candidate，不影响同批其它 candidate。

AI 服务不可用 / feature flag off:
  不生成 t2_ai_response 或标记 skipped；T2 deterministic path 必须独立产出 unit_map。
```

## 10. page_policy model

### 10.1 字段结构

建议在 `unit_map.units[]` 中新增：

```json
{
  "page_policy": {
    "observed": {
      "starts_new_page": true,
      "title_at_page_top": true,
      "previous_page_has_remaining_space": true,
      "peer_units_follow_same_pattern": true,
      "source": "rendered_page_image",
      "confidence": "high"
    },
    "mechanical": {
      "has_explicit_break": false,
      "mechanism": "none",
      "source": "t1_facts",
      "confidence": "high"
    },
    "generation_policy": {
      "requires_new_page": true,
      "enforcement_hint": "insert_page_break_before",
      "source": "ai_visual_inference",
      "confidence": "high",
      "reason": [
        "title_at_page_top",
        "previous_page_has_remaining_space",
        "peer_units_follow_same_pattern"
      ]
    },
    "conflicts": []
  }
}
```

### 10.2 字段语义

```text
observed:
  渲染图上看到什么。

mechanical:
  源 DOCX 里实际存在什么。

generation_policy:
  生成新文档时应该遵守什么策略。

conflicts:
  规则、AI、机械事实之间的冲突。
```

### 10.3 requires_new_page 的取值

```text
true:
  T2 确认该 unit 生成时应另起页。

false:
  T2 确认该 unit 可以接续上一单元。

unknown:
  证据不足，进入 page_policy_review。
```

建议允许 `true | false | unknown` 三态。

### 10.4 高置信强制分页条件

AI 或 reconciler 判断 high confidence 至少应满足下面条件中的两到三条：

```text
1. 当前标题是顶层 unit heading。
2. 标题出现在新页页首。
3. 前一页有明显剩余空间。
4. 多个同级单元重复出现同样的新页页首模式。
5. 该标题也出现在已确认的 TOC 一级条目中。
6. 单元后跟随完整正文/表单/声明页内容，而不是局部小标题。
```

### 10.5 不能直接判强制分页的情况

```text
1. 前一页刚好写满，下一个标题自然流到下一页。
2. 只有单点出现，没有 peer pattern。
3. 标题其实是表格标题、栏目名、小节标题。
4. AI 无法绑定 source_seq。
5. 规则侧认为它不是顶层 unit。
```

这些情况应输出：

```json
{
  "generation_policy": {
    "requires_new_page": "unknown",
    "source": "insufficient_evidence",
    "confidence": "low"
  }
}
```

并进入 `page_policy_review`。

## 11. 输出 artifacts

### 11.1 `unit_map.json`

新增或更新字段：

```json
{
  "units": [
    {
      "unit_id": "custom:template:opening_report",
      "canonical_label_id": null,
      "label_status": "custom_detected",
      "raw_title": "毕业论文（设计）开题报告",
      "normalized_title": "毕业论文设计开题报告",
      "display_name": "毕业论文（设计）开题报告",
      "start_source_seq": 60,
      "end_source_seq": 88,
      "confidence": "high",
      "evidence": [],
      "page_policy": {}
    }
  ],
  "open_questions": [],
  "taxonomy_review_queue": [],
  "page_policy_review": [],
  "debug": {}
}
```

### 11.2 `t2_input.json`

在原有事实切片基础上增加图像和布局引用：

```json
{
  "schema_version": "t2_input.v2",
  "render_artifacts": {
    "clean_page_images": [
      {"page_no": 1, "path": "...", "hash": "..."}
    ],
    "annotated_page_images": [
      {"page_no": 1, "path": "...", "hash": "..."}
    ]
  },
  "contexts": [
    {
      "reason": "boundary_candidate_or_ai_review",
      "entries": [
        {
          "source_seq": 60,
          "source_ref": "...",
          "text": "...",
          "text_facts": {},
          "layout_facts": {
            "page_no": 8,
            "bbox": [0, 0, 0, 0],
            "page_top_ratio": 0.12
          },
          "t2_derived_signals": {}
        }
      ]
    }
  ]
}
```

### 11.3 `t2_ai_response.json`

保存原始 AI JSON 输出，用于回放和 debug。

### 11.4 `t2_reconciler_trace.json`

保存合并轨迹：

```json
{
  "schema_version": "t2_reconciler_trace.v1",
  "accepted_ai_candidates": [],
  "rejected_ai_candidates": [],
  "conflicts": [],
  "promotion_decisions": [],
  "page_policy_decisions": []
}
```

## 12. 下游契约影响

T2 开放 `custom_unit` 后，下游不能继续假设 `unit_id ∈ CORE_SET`。需要明确哪些模块只认 core，哪些模块必须接受 custom。

### 12.1 下游消费矩阵

| 下游 | 对 core unit 的行为 | 对 `custom_unit` 的默认行为 | 禁止行为 |
| --- | --- | --- | --- |
| **T3 element policy** | 使用 core-specific parser，例如摘要关键词、参考文献、声明页字段 | 使用 generic block/form/table parser；保留 raw spans；不强行套 core schema | 因 `canonical_label_id=null` 直接丢弃 unit |
| **T4 renderer/generator** | 按 core policy 生成分页、标题、页眉页脚等 | 按 T2 `page_policy.generation_policy` 和 generic unit render policy 执行 | 重新猜 custom_unit 是哪个 core label |
| **T5 validation** | 检查 core 必需单元齐全、顺序、字段完整性 | 检查 custom_unit source_seq 连续、raw_title 保留、未被误删 | 把 custom_unit 全部视为失败 |
| **T6 rendering eval** | 验证 core unit 版式还原 | 验证 custom_unit 未丢失、分页策略可执行 | 要求 custom_unit 必须有 core-specific layout |
| **generic fill/remove policy** | core-specific 内容填充/删除 | custom_unit 默认保留结构；可做 generic placeholder fill/remove | 默认删除 unknown/custom unit |

### 12.2 `canonical_label_id=null` 的默认行为

```text
canonical_label_id=null
+ label_status=custom_detected
+ boundary confidence >= medium
=> 这是有效 unit，不是错误。

canonical_label_id=null
+ label_status=unmapped/candidate_only
+ boundary confidence low
=> 进入 open_question，不能作为高置信 final unit 使用。
```

默认处理：

```text
- 保留该 unit，不降成 other。
- 使用 display_name 展示标题。
- 使用 generic T3/T4 policy。
- 不参与 core required-unit 计数。
- 不触发 core-specific validator。
- 必须进入 taxonomy_review_queue，除非 label_status=template_alias_matched 或 school_alias_matched。
```

### 12.3 core-only 逻辑边界

以下逻辑只对 core unit 生效：

```text
abstract_cn / abstract_en 的关键词字段强校验
references 的参考文献条目规则
body_main 的章节层级规则
integrity_statement 的签名/日期字段规则
acknowledgement / appendix 的 core-specific 顺序规则
```

以下逻辑必须支持 custom_unit：

```text
unit span 保留
generic placeholder extraction
generic table/form block extraction
page_policy 执行
taxonomy_review_queue
human review UI / trace visualization
artifact serialization 和 replay
```

## 13. taxonomy review queue

### 13.1 目的

新学校模板中出现未知但高置信的一级章节时，不应该马上扩大全局闭集，也不应该丢成 `other`。应先进入 review queue。

### 13.2 schema

```json
{
  "review_id": "taxonomy-001",
  "raw_title": "毕业论文（设计）开题报告",
  "normalized_title": "毕业论文设计开题报告",
  "display_name": "毕业论文（设计）开题报告",
  "source_seq": 60,
  "school_id": "hunannongye",
  "template_id": "hunannongye-undergraduate-2026",
  "suggested_scope": "template",
  "suggested_alias_key": "opening_report",
  "evidence": [
    "custom_unit_detected",
    "ai_visual_top_level_unit",
    "form_block_like"
  ],
  "status": "pending"
}
```

### 13.3 提升路径

```text
pending
  ↓
人工或模型复核
  ↓
如果通用：promote to global_alias
如果学校专用：promote to school_alias
如果模板专用：promote to template_alias
如果误判：mark rejected
```

## 14. confidence 规则

### 14.1 boundary confidence

| confidence | 条件 |
| --- | --- |
| `high` | explicit break/section + heading evidence；top-level heading style + core/alias label；strong TOC block；deterministic + AI 两侧一致 |
| `medium` | text_properties + core/alias label；AI visual heading + deterministic candidate；unknown heading promotion |
| `low` | keyword-only、duplicate、variant、label unknown、AI-only but weak context |
| `candidate_only` | 只有 text_properties；或 AI 无法绑定完整 source_seq |

### 14.2 label confidence

| confidence | 条件 |
| --- | --- |
| `high` | canonical core label exact match；school/template alias exact match |
| `medium` | AI label suggestion + title normalization + weak alias match |
| `low` | label unknown；custom_detected 但无 taxonomy 历史 |

### 14.3 page_policy confidence

| confidence | 条件 |
| --- | --- |
| `high` | T1 explicit break；或 AI visual pattern + previous page blank + peer pattern |
| `medium` | AI visual pattern + one supporting signal |
| `low` | 单点视觉新页；上一页可能自然写满；无 peer pattern |
| `unknown` | 证据不足或冲突未解 |

## 15. 实施顺序

### Phase 0：契约与 feature flag

1. 增加 `t2_ai_visual_enabled` feature flag。
2. 定义 `t2_input.v2`、`t2_ai_visual_response.v1`、`t2_reconciler_trace.v1` schema。
3. 在 `unit_map.units[]` 中预留 `page_policy`。
4. 明确 `requires_new_page: true | false | unknown` 三态。

### Phase 1A：渲染与基础回绑

Phase 1A 是 render 子项目的第一阶段，不作为 Phase 2 deterministic 修复的阻塞项。

1. 导出 clean page images。
2. 导出 annotated page images，在页面上覆盖 source_seq。
3. 生成 page_text_index。
4. 写入 render_engine、render_version、render_hash、image_hash。
5. 短期至少支持 page_no + page_order + source_seq 回绑。

### Phase 1B / 1.5：bbox / blank ratio 增强

1. 生成 page_layout_index，包括 bbox、page_top_ratio、page_bottom_ratio。
2. 计算 previous_page_blank_ratio。
3. 计算 peer_unit visual pattern。
4. 如果 bbox 不可靠，page_policy 中视觉分页字段必须降级为 unknown 或 medium 以下。
5. 明确 LibreOffice 渲染与 Word 渲染的差异风险，并把该风险纳入 T6 eval 说明。

### Phase 2：确定性主干

1. T2 本地派生信号层。
2. TOC block segmenter。
3. `text_properties` candidate-only。
4. canonical core-label classifier。
5. alias registry + custom_unit fallback。
6. variant/form block 最小聚合。

Phase 2 硬门禁：

```text
- t2_ai_visual_enabled=false 时，三校结构指标仍必须可用。
- 湖南 TOC 20/20 条目必须由 deterministic path 归入 toc，不能等待 AI。
- 非 toc 单元中的 toc_entry_like 数必须为 0。
- 北大不能因 text_properties 单独命中继续暴涨 unit。
```

Phase 2 允许先 merge 到 main：只要通过三校确定性结构门禁，即使 AI visual pass 尚未启用，也可以合并，避免 P0 修复被 render/AI 工程阻塞。

### Phase 3：AI visual structure pass

1. 实现 AI 输入打包。
2. 实现 prompt + JSON schema。
3. AI 输出 `unit_candidates`、`block_candidates`、`page_policy_candidates`。
4. 保存 `t2_ai_response.json`。
5. 对 AI 输出做 schema validation 和 source_seq validation。
6. CI 使用 fixture，不调用 live model。

### Phase 4：T2 reconciler

1. 合并 deterministic candidates 与 AI candidates。
2. 实现固定优先级表。
3. 实现 AI rescue path：TOC block、custom_unit、page_policy。
4. 实现 unknown heading promotion。
5. 实现 custom_unit finalization。
6. 实现 page_policy finalization。
7. 实现 partial accept / reject 和 dedup。
8. 输出 `t2_reconciler_trace.json`。

### Phase 5：指标门禁与回归测试

1. 三校结构指标。
2. 无 AI 降级指标。
3. custom_unit 指标。
4. AI 绑定 source_seq 指标。
5. 强制分页策略指标。
6. 冲突和 open question 指标。

## 16. 验收指标

### 16.1 结构指标

| 指标 | 目标 |
| --- | --- |
| 非 `toc` 单元中的 `toc_entry_like` 数 | 0 |
| `toc` 覆盖全部 TOC 条目 | 100% |
| `other` 数 | 明显下降，且不再承载高置信自定义一级单元 |
| `custom_unit` | 每个都必须有 raw_title、normalized_title、source_seq、evidence |
| 必需核心单元 | `toc`、`abstract_cn`、`abstract_en`、`body_main`、`references` 等齐全 |
| unit 数量 | 不暴涨 |
| T2 flags | 下降或更集中，不能无意义扩散 |

### 16.2 无 AI 降级指标

`t2_ai_visual_enabled=false` 时必须满足：

| 指标 | 目标 |
| --- | --- |
| 三校结构指标 | 仍按 deterministic path 通过 |
| 湖南 TOC | 20/20 条目归入 `toc`，不依赖 AI |
| 南农 TOC | 25/25 条目归入 `toc` |
| 北大 TOC | 17/17 条目归入 `toc` 或达到本轮确定性门禁 |
| `page_policy.generation_policy` | 只能来自 `mechanical_fact` 或 deterministic policy；视觉来源为 `unknown/skipped` |
| `observed` 视觉字段 | 没有 render/AI 时为 `unknown` 或缺省，不得伪造 |
| 系统可用性 | 关闭 AI 不能导致 unit_map 不生成 |
| 空跑反馈 | typed open_questions、missing_facts、t2_input slices 仍正常输出 |

### 16.3 AI 质量指标

| 指标 | 目标 |
| --- | --- |
| AI candidate source_seq 绑定率 | 100%；无法绑定的不得进入正式候选 |
| AI hallucinated title 数 | 0 |
| AI schema validation | top-level schema 必须 pass；单个 candidate 可 partial reject / partial accept |
| accepted_ai_candidates | 必须有 reconciler reason |
| rejected_ai_candidates | 必须有 rejection reason |
| AI 与 deterministic 重叠候选 | 必须 dedup，并写入 trace |

### 16.4 page_policy 指标

| 指标 | 目标 |
| --- | --- |
| 有 T1 explicit break 的 unit | `generation_policy.requires_new_page=true`，source=`mechanical_fact` |
| 无 T1 break 但视觉强分页的 unit | 可输出 `requires_new_page=true`，source=`ai_visual_inference` |
| 自然流页导致的新页 | 不误判成强制分页；证据不足则 unknown |
| page_policy_review | 每条必须绑定 unit/source_seq 和冲突原因 |
| T4 可消费性 | T4 只需读取 `generation_policy.requires_new_page` 和 `enforcement_hint` |

## 17. 单测建议

### 17.1 确定性规则

```text
test_t2_derives_toc_entry_like_from_atomic_facts
test_t2_ignores_legacy_t1_semantic_fields_if_present
test_t2_toc_block_claims_all_toc_entries
test_t2_text_properties_only_is_candidate_not_unit_boundary
test_t2_unknown_heading_promotion_with_strong_context
test_t2_canonical_title_classifier_handles_format_annotations
test_t2_custom_unit_not_other_for_high_confidence_unknown_heading
test_t2_duplicate_variant_block_is_grouped
test_t2_hunan_toc_20_of_20_without_ai
```

### 17.2 AI response validation

CI 单测不调用 live model。所有 AI 测试使用 fixture：

```text
test_t2_ai_response_requires_source_seq
test_t2_rejects_ai_candidate_with_unknown_source_seq
test_t2_rejects_ai_hallucinated_title
test_t2_accepts_ai_custom_unit_when_deterministic_candidate_exists
test_t2_accepts_ai_toc_block_when_deterministic_misses_and_binding_valid
test_t2_ai_cannot_override_locked_toc_block
test_t2_reconciler_records_ai_conflicts
test_t2_reconciler_partial_accepts_valid_candidates
test_t2_reconciler_dedups_overlapping_unit_and_block_candidates
test_t2_ai_off_does_not_require_t2_ai_response
```

可选 live eval：

```text
- 非 CI gate。
- 定期调用 live model 跑小规模模板回归。
- 产出 drift report：accepted/rejected candidate 差异、page_policy 差异、token/cost。
- live eval 失败不能阻塞确定性 P0 修复 merge。
```

### 17.3 page_policy

```text
test_t2_page_policy_mechanical_break_high_confidence
test_t2_page_policy_ai_visual_forced_break_without_mechanical_signal
test_t2_page_policy_natural_page_flow_is_unknown_not_forced
test_t2_page_policy_requires_unit_binding
test_t4_consumes_generation_policy_not_mechanical_fact
```

### 17.4 下游契约

```text
test_t3_accepts_custom_unit_with_generic_policy
test_t4_applies_page_policy_for_custom_unit
test_t5_does_not_fail_on_custom_unit_with_null_canonical_label
test_generic_fill_remove_policy_preserves_custom_unit_by_default
```

## 18. 风险与缓解

### 18.1 高风险

| 风险 | 说明 | 缓解 |
| --- | --- | --- |
| 渲染回绑不准 | 无 bbox 或 source_seq overlay 不准时，AI 说的“页首标题”无法稳定落到源段落 | annotated images 必需；无 bbox 时 page_policy 默认 unknown/low；所有 AI candidate 必须 source_seq validation |
| AI 救不了确定性欠切 | 如果 reconciler 只保护 deterministic high block，不接受 AI high block，湖南这类 deterministic missed TOC 无法受益 | 明确 case：AI toc block 可兜底，accepted_reason=`ai_rescue_toc_block` |
| scope 膨胀 | Render + AI + reconciler + page_policy + taxonomy 同时推进 | Phase 2 先独立交付；AI feature flag；Render 拆 Phase 1.5 子项目 |
| custom_unit 下游未跟进 | T3/T4/T5/T6 继续假设 `unit_id ∈ CORE_SET` | 增加下游契约矩阵；core-only 与 generic policy 分开 |

### 18.2 中风险

| 风险 | 说明 | 缓解 |
| --- | --- | --- |
| 自然分页误判为强制分页 | 上一页刚好写满，标题自然到下一页 | 检查 previous_page_has_remaining_space + peer pattern；证据不足输出 unknown |
| full-pass 成本 | 大模板 300+ 段、多页高清图输入贵且可能超 context | 先 full-pass fixture；后续 focused-pass，只送可疑区间 + 相关页面 |
| schema 校验过严 | 一个坏 candidate 造成整批 fallback，丢掉有效 AI 结果 | 顶层 schema 失败才整批 fallback；candidate 级 partial accept/reject |
| AI 与 deterministic 重复候选 | unit_candidate 和 block_candidate 重叠，导致重复边界 | dedup 规则：同 source_seq 合并，locked block 吃掉内部 candidate |
| peer pattern 难稳定 | 长模板中同级单元样式不完全一致 | peer pattern 只做加分，不作为唯一 high confidence 条件 |

### 18.3 低风险

| 风险 | 说明 | 缓解 |
| --- | --- | --- |
| taxonomy queue 积压 | 新学校模板会产生大量 custom_unit | 短期允许；后续人工/模型 promote 到 template/school/global alias |
| prompt 漂移 | 模型升级导致输出风格变化 | prompt_version + schema_version + render_hash + fixture 回归 |
| AI 解释不一致 | reason 文本漂移 | 只把结构化字段作为 gate，reason 用于 trace/调试 |

## 19. AI 对三校问题的预期覆盖

| 模板 | 当前问题 | 主要修复路径 | AI 角色 |
| --- | --- | --- | --- |
| 湖南农大 | TOC 消失 / 欠切 | Phase 2 确定性：标题归一化 + TOC block 注入 boundary | 仅兜底；不能作为 Hunan TOC 唯一修复路径 |
| 湖南农大 | 变体两套模板 | variant_block 规则 + 最小聚合 | 可辅助识别 form/variant block |
| 湖南农大 | 无 heading 样式 | text_properties candidate + strong_context | AI visual heading 可辅助 custom_unit 升格 |
| 南农本科 | TOC 已基本可用 | locked TOC block | AI 主要用于 page_policy / 边缘 case |
| 北大研究生 | 过切 + 大量 other | text_properties candidate-only + alias/custom_unit | AI 可辅助表单块识别、抑制局部标题过切 |

AI 最有价值的场景：

```text
学校自定义章节：开题报告、中期检查、答辩表、评审意见等。
无 mechanical break 的强制分页。
表单块/表格块视觉识别。
规则只留下 candidate_only 的未知顶层标题。
```

AI 不应承担的场景：

```text
TOC block primary path。
Hunan TOC 20/20 的 P0 修复。
已 locked block 的重新切分。
T1 mechanical fact 的伪造或改写。
```

## 20. 需要拍板的问题

1. `page_policy.generation_policy.requires_new_page` 是否允许三态：`true | false | unknown`？建议允许。
2. `enforcement_hint` 是否由 T2 给出？建议 T2 只给 hint，T4 决定具体 OOXML 机制。
3. AI visual pass 是默认开启，还是先 feature flag？建议先 feature flag。
4. 渲染链路短期是否能提供 bbox？如果不能，先提供 page_no + source_seq + annotated images。
5. `custom_unit` 的 `unit_id` scope 用 `custom:school:*` 还是 `custom:template:*`？建议默认 template，复核后再提升到 school/global。
6. `other` 是否继续保留？建议保留，但只用于杂项/变体/低置信兜底，不再承载高置信未知一级单元。
7. AI 是否允许直接建议 core label？建议允许 suggestion，但 final label 必须由 T2 reconciler 决定。
8. Phase 2 是否允许 merge 到 main 而不启用 AI？建议允许；Phase 2 过三校结构门禁即可 merge，AI 作为 opt-in feature。
9. AI high-confidence TOC block 是否可在 deterministic 未识别时兜底？建议允许，但必须 source_seq 可绑定、range 合法、证据通过，并写 trace。
10. `AI-only unit boundary` 是否允许进入 final？建议默认不允许；除非存在可解释 strong_context，并通过 source_seq / block / page_policy 校验。

## 21. 最终推荐落地版本

本轮建议交付：

```text
1. T1 fact-only 约束不变。
2. T2 deterministic 主干继续保留：derived signals + block-first + candidate-only + open taxonomy。
3. Phase 2 先独立通过三校结构门禁，尤其湖南 TOC 20/20，不等待 AI。
4. 新增 rendered page images 和 annotated page images；bbox / blank_ratio 作为 Phase 1.5 增强。
5. 新增 AI visual structure pass，feature flag 默认可关闭。
6. 新增 T2 reconciler，禁止 AI 直接写 final unit_map。
7. 新增明确的 reconciler 优先级表、AI 兜底 TOC block 规则、partial accept / dedup 规则。
8. 新增 unit-level page_policy。
9. 强制分页策略归 T2，具体分页实现归 T4。
10. 新增下游 custom_unit 契约，确保 T3/T4/T5/T6 可消费开放标签。
11. 新增 t2_ai_response.json 和 t2_reconciler_trace.json。
12. 新增无 AI 降级、AI fixture、page_policy、custom_unit 验收指标。
```
