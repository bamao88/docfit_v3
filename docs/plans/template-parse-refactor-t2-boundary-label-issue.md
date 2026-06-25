---
status: draft
owner: template-generation
stage: T2
severity:
  - P0
  - P1
created: 2026-06-25
last_updated: 2026-06-25
related_docs:
  - docs/plans/template-parse-refactor-t1-fact-coverage-issues.md
  - docs/plans/template-parse-refactor-t2-unit-map.md
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/artifacts.py
---

# T2 边界检测与标签器调优 issue

Last updated: 2026-06-25

一句话结论：当前 T2 优化版把旧逻辑的"关键词撞目录"问题显性化了，也补出了 `t2_input.json` 和 typed `open_questions`；但它还没有达到可交付效果。主要问题是 **TOC block 没有作为专门单元切分**、**仅文字属性即可过阈值导致过切**、**标签器闭集过窄导致大量 `other`**。后续必须明确：**T1 只产原子事实；T2 禁止消费 `is_toc_entry`、`likely_unit_heading` 等 T1 语义字段；T2 只能从原子事实派生 `toc_entry_like`、`instruction_like`、`unit_heading_like` 等内部信号，并在 T2 artifact 中暴露这些派生证据。**

---

## 0. 已确认的架构边界

### 0.1 T1 不能产出语义判断

T1 后续目标是 fact-only。它不能输出这些字段：

- `is_toc_entry`
- `is_spacing_line`
- `looks_like_instruction_text`
- `likely_unit_heading`
- `large_font`
- `short_text`

这些字段都需要词表、阈值、上下文或业务意义组合，属于 T2/T3 推断，不属于 T1。

T1 应输出的是原子事实，例如：

- `text`
- `style_name` / `style_id`
- `has_tab`
- `trailing_token`
- `leader_chars`
- `paragraph.alignment`
- `dominant_run.font_size_pt`
- `dominant_run.bold`
- `page_break_before`
- `sectPr` / `breaks`
- `container_ref` / `table_id` / `cell_id`

### 0.2 T2 可以、也必须派生结构语义

T2 的职责是基于 T1 原子事实做单元边界和归属判断。因此，下面这些应是 **T2 内部派生信号**：

| T2 派生信号 | 含义 | 输入事实 |
| --- | --- | --- |
| `toc_title_like` | 目录标题 | 文本规范化、样式、位置 |
| `toc_entry_like` | 目录条目 | tab、leader、尾部页码 token、样式名 |
| `instruction_like` | 模板说明文字 | 原文、括号内容、字体/字号词 token |
| `spacing_line_like` | 空行/空格说明 | 原文、括号内容、数字 token |
| `unit_heading_like` | 单元标题候选 | 样式、居中、字号、加粗、短文本、分页/分节 |

文档和代码表述应避免说"如果 T1 的 `is_toc_entry=True`"，正确说法是：

> T2 从 T1 原子事实派生出的 `toc_entry_like` 段落，一旦被 T2 的目录块 segmenter 接收，就必须归入 `toc` unit，不能再被摘要/正文/参考文献等关键词抢走。

### 0.3 无过渡硬约束

本 issue 按目标架构讨论，不设"兼容旧 T1 语义字段"的过渡阶段。实现和测试应假设 T1 **不会**生产 `is_toc_entry`、`is_spacing_line`、`looks_like_instruction_text`、`likely_unit_heading` 等字段。

硬约束：

1. T2 不读取 `document_facts.body_flow[].structural_signals`。
2. T2 不读取 `is_toc_entry=True` 这类语义字段，即使旧 artifact 里存在也视为无效输入。
3. T2 只能读取 T1 原子事实，例如 `text`、`style_name`、`has_tab`、`trailing_token`、alignment、font size、bold、breaks、container facts。
4. 如果原子事实不足以判定，T2 必须 `abstain`：输出 `open_question` / `t2_input.json`，不能用旧语义字段补救。
5. T2 输出 `t2_derived_signals`，明确标记为 T2 派生证据。

准确率优化的前提也因此改变：不是"让 T1 更早标好 TOC"，而是**让 T1 给足可观测事实，让 T2 有更强的派生规则和 block-level segmenter**。

### 0.4 无 T1 语义字段时的准确率优化原则

T2 准确率不靠消费 T1 的 `is_toc_entry`，而靠以下四层：

1. **原子事实足够可判定**：T1 必须提供 tab、leader、尾部页码 token、样式名、alignment、font size、bold、breaks、container facts 等可观测事实。T2 判不准时，先检查是不是事实缺失，而不是把语义塞回 T1。
2. **T2 派生信号可解释**：`toc_entry_like`、`toc_title_like`、`unit_heading_like`、`instruction_like` 都由 T2 计算，并在 T2 artifact 里写出命中/未命中的证据。
3. **先 block，后 boundary**：目录、变体块、表格表单这类结构块先整体识别；块内段落不再和普通章节标题竞争边界分数。
4. **宁可 abstain，不要乱切**：单一弱信号只能进入 `open_question`，不能直接切正式 unit；缺事实时写 `missing_facts[]`，让问题可定位。

对应的调优目标不是让某个布尔字段更早出现，而是让 T2 对每个边界能回答：

```text
这个段落为什么像/不像 toc_entry？
这个段落为什么像/不像 unit boundary？
如果判断不了，缺哪些 T1 原子事实？
```

---

## 1. 当前效果数据

对比口径：

- 基线：`26989af`
- 当前：`HEAD=c52b380`
- 模板：`hunannongye`、`nannong-undergraduate`、`pku-graduate`
- 输出位置：`/private/tmp/t2_compare.E33B1e`

### 1.1 总体指标

| 学校 | 版本 | overall | findings | unit 数 | `other` 数 | T2 flags | TOC 条目正确归入 toc |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 湖南农大 | 基线 | UNKNOWN | 648 | 9 | 0 | 9 | 0/20 |
| 湖南农大 | 当前 | UNKNOWN | 735 | 19 | 14 | 39 | 0/20 |
| 南农本科 | 基线 | UNKNOWN | 228 | 9 | 0 | 9 | 0/25 |
| 南农本科 | 当前 | UNKNOWN | 272 | 16 | 9 | 23 | 25/25 |
| 北大研究生 | 基线 | UNKNOWN | 727 | 9 | 0 | 9 | 0/17 |
| 北大研究生 | 当前 | UNKNOWN | 1167 | 76 | 68 | 159 | 14/17 |

### 1.2 结论

已有改善：

- `t2_input.json` 已独立输出，三校都有。
- `unit_map.open_questions[]` 从无类型 flag 投影变成 typed queue（`boundary` / `label` / `required_missing` / `flag`）。
- confidence 不再 100% `medium`，可以区分 `high` / `medium` / `low`。
- 南农 TOC 明显改善：25/25 个 TOC 条目归入 `toc`。

主要退化：

- 湖南仍没有正确形成 `toc`，20 个 TOC 条目仍进入非 `toc` 单元。
- 北大过切严重：`9 units -> 76 units`，其中 `68 other`。
- 三校 overall 仍是 `UNKNOWN`，`first_bad_stage` 仍是 `T2`。
- findings 上升，说明当前规则更会暴露不确定性，但还没有转化成确定性质量提升。

---

## 2. 问题拆解

### T2-ISSUE-001：TOC 没有作为 block 专门处理

当前 TOC 仍混在通用边界检测流程里：目录标题、目录条目、真实标题都通过同一套 boundary score 竞争。

这导致：

- 旧版：目录条目被摘要/正文/参考文献关键词抢走。
- 当前版：南农修好了，但湖南仍失败；北大仍有 3 个 TOC 条目进入 `other`。

根因：

- 没有显式的 `toc block segmenter`。
- `toc_entry_like` 只是边界 veto 或普通证据，而不是先验 block 归属规则。
- `toc_title_like` 识别过窄，对 `目□□录（二号黑体，居中）`、空格分隔、格式注释等不够稳。

### T2-ISSUE-002：`text_properties` 单独过阈值，导致过切

当前打分：

```text
centered AND (large_font OR bold) => +2
threshold = 2
```

因此单独命中文字属性就会切成正式 unit boundary。

这对真实学校模板过宽。很多局部标题、表格栏目名、说明段标题、阶段标题都可能居中/加粗/大字号，但它们不是一级模板单元。

表现：

- 北大当前 `76 units`，`68 other`。
- 大量 `label_unknown` 和 `boundary` open question。

### T2-ISSUE-003：标签器闭集过窄，切出边界后贴不上标签

当前标签器主要依赖 `UNIT_DEFINITIONS` 中的短词表：

```python
("toc", "目录", ("目录", "目 录"))
("abstract_cn", "中文摘要", ("摘要", "摘 要", "关键词"))
("body_main", "正文", ("正文", "绪论", "第一章", "1 "))
...
```

问题：

- 标题变体多：`中文摘要`、`摘要及关键词`、`ABSTRACT`、`Key Words`、`第1章 绪论`、`1 前言`。
- 当前 `_unit_for_text()` 是宽泛 contains，容易误识别；但 `_is_exact_unit_heading_text()` 又过窄，容易漏识别。
- 没有区分"目录中的标题文本"和"正文中的真实标题"。

结果：

- 切边界召回上来了，但贴标签能力没跟上，大量进入 `other`。

### T2-ISSUE-004：duplicate label 处理过粗

当前同一个 `unit_id` 第二次出现，会降成 `other` 并打 `unit_label_duplicate`。

这对"重复误识别"有用，但对真实模板变体不够：

- 湖南有农理工科/文科类两套模板块。
- 目录内条目重复出现时应被 TOC block 吃掉。
- 真正的变体块应聚合为 `variant_block` 或 `other + variant flag`，而不是被继续细碎切成多个 `other`。

---

## 3. 优化方案

### 3.1 先实现 T2 派生信号层

新增 T2 内部函数，全部只读 T1 原子事实；如果事实不存在，函数返回 `unknown` / `False` 并记录缺失证据，不读取旧语义字段：

```python
def _t2_text_facts(entry) -> dict:
    return {
        "text": ...,
        "normalized_text": ...,
        "style_name": ...,
        "has_tab": ...,
        "trailing_token": ...,
        "leader_chars": ...,
        "alignment": ...,
        "font_size_pt": ...,
        "bold": ...,
        "page_break_before": ...,
    }

def _looks_like_toc_title(entry) -> bool:
    ...

def _looks_like_toc_entry(entry) -> bool:
    ...

def _looks_like_instruction(entry) -> bool:
    ...

def _looks_like_spacing_line(entry) -> bool:
    ...
```

输出位置：

- `template_structure_candidates.t2_derived_signals_by_source_seq`
- 或每个 candidate / boundary 的 `evidence[].value`
- `t2_input.contexts[].entries[].t2_derived_signals`

约束：

- 不写回 `document_facts`。
- 字段名带 `t2_` 或放在 T2 artifact 下，避免再次污染 T1。
- 不读取 `structural_signals`，不接受 `is_toc_entry` 作为输入。

### 3.2 TOC block segmenter 独立于通用边界检测

在通用 `_boundary_decision()` 之前先跑 TOC block 识别。

#### 规则草案

1. 找 `toc_title_like`。
2. 从标题后开始收集连续 `toc_entry_like`。
3. 允许中间有少量空白/格式说明/目录版本说明，但要打 `confidence=medium`。
4. 若只有连续 `toc_entry_like`，回看前 1-3 段找弱目录标题；找不到则创建低置信 `toc`。
5. TOC block 内的 entry 不参与摘要/正文/参考文献等普通边界检测。

伪代码：

```python
toc_blocks = []
for i, entry in enumerate(entries):
    if not looks_like_toc_title(entry):
        continue
    j = i + 1
    while j < len(entries) and (
        looks_like_toc_entry(entries[j])
        or looks_like_toc_continuation(entries[j])
    ):
        j += 1
    if has_toc_entries(entries[i:j]):
        toc_blocks.append(Block("toc", start=i, end=j, confidence=...))
```

验收：

- 南农：25/25 TOC 条目在 `toc`。
- 北大：17/17 TOC 条目在 `toc`。
- 湖南：20/20 TOC 条目在 `toc`。
- 非 `toc` 单元包含 `toc_entry_like` 数为 0。

### 3.3 调整边界阈值：`text_properties` 改为 candidate-only

规则改为：

| 命中 | 当前行为 | 建议行为 |
| --- | --- | --- |
| `text_properties` 单独命中 | 正式切 boundary | 只记 `boundary_candidate`，不切正式 unit |
| `text_properties + closed_label` | 切 boundary | 切，`medium` |
| `text_properties + break/section` | 切 boundary | 切，`medium/high` |
| `heading_style` 单独命中 | 切 boundary | 切，但若 label unknown，需看上下文 |
| `keyword` 单独命中 | fallback 低置信 boundary | 只允许 exact title fallback |

具体改法：

```python
if score >= 2:
    if hits == {"text_properties"}:
        return CandidateOnly(...)
    return Boundary(...)
```

或者改为双阈值：

```text
boundary_threshold = 3
candidate_threshold = 2
```

- `score >= 3`：正式 boundary
- `score == 2`：candidate，进入 `open_question`，默认不切
- `score < 2`：非 boundary

讨论点：湖南没有标题样式，可能需要 `text_properties + exact label` 保留为正式 boundary，否则会漏切。

### 3.4 标签器改为 canonical title classifier

标签前先规范化标题：

```python
def canonical_title(text):
    strip_format_annotations(text)
    remove_placeholders(text)      # □、×、__
    remove_leader_and_page_suffix(text)
    normalize_width_case_space(text)
    return normalized
```

然后做闭集分类，避免宽泛 contains：

| unit_id | 推荐模式 |
| --- | --- |
| `toc` | `^目[录錄]$` |
| `abstract_cn` | `^(中文)?摘要(及关键词|关键词)?$` |
| `abstract_en` | `^(abstract|englishabstract|keywords|key words)$` |
| `body_main` | `^(正文|绪论|前言|第[一二三四五六七八九十0-9]+章.*|[0-9]+[.、 ].{1,20})$` |
| `references` | `^(参考文献|references)$` |
| `acknowledgement` | `^(致谢|acknowledgements?)$` |
| `appendix` | `^(附录|appendix)([a-z0-9一二三四五六七八九十]*)?$` |
| `integrity_statement` | `(诚信声明|原创性声明|授权书)` exact/prefix |
| `post_forms` | `(任务书|开题报告|评审表|答辩|成绩评定)` exact/prefix |

注意：

- `body_main` 的数字标题必须排除 `toc_entry_like`。
- `abstract_cn` 的 `关键词` 不能单独作为新摘要边界，除非上下文显示它是摘要标题的一部分。
- `toc` 标签优先级高于其他关键词。

### 3.5 duplicate / variant 处理

重复闭集单元不应一律打散成多个 `other`。

建议规则：

1. 如果重复出现在 TOC block 内：归 `toc`，不参与 duplicate。
2. 如果重复附近有变体标记：
   - `农理工科`
   - `文科`
   - `文法经管`
   - `以下...用`
   - `...类专业用`

   则聚合为：

```json
{
  "unit_id": "other",
  "name": "模板变体块",
  "flags": [
    {
      "type": "variant_block_detected",
      "status": "UNKNOWN"
    }
  ]
}
```

3. 如果重复是同一真实单元的二级标题，则不切新 unit，只作为上一 unit 内部 element。

讨论点：本轮是否只做 `other + variant_block_detected`，不做完整 variant model。建议先这样，和既定"方案 C：维护者后续手工删源模板另一套"一致。

### 3.6 confidence 规则重写

建议：

| confidence | 条件 |
| --- | --- |
| `high` | TOC block 强确认；或 `heading_style + closed_label`；或 `break/section + closed_label` |
| `medium` | `text_properties + closed_label`；或 `heading_style` 但 label 需上下文确认 |
| `low` | keyword-only fallback、duplicate、variant、label unknown |
| `candidate_only` | 只有 `text_properties`，默认不切正式 unit |

这样能降低无意义 T2 flags，同时保留需要人工/AI 判断的证据。

---

## 4. 实施顺序

建议按下面顺序做，不要先大范围调权重：

1. **T2 本地派生信号层**：从 T1 原子事实计算 `toc_entry_like` 等；不读旧 `structural_signals`。
2. **TOC block segmenter**：先解决最大污染源。
3. **`text_properties` candidate-only**：压住北大过切。
4. **canonical title classifier**：提高 closed label 命中率，减少 `other`。
5. **duplicate / variant 聚合**：减少湖南多版本块造成的碎片化。
6. **三校指标门禁**：把下面指标写成测试或脚本。

---

## 5. 验收指标

### 5.1 三校结构指标

| 指标 | 湖南目标 | 南农目标 | 北大目标 |
| --- | ---: | ---: | ---: |
| 非 `toc` 单元中的 `toc_entry_like` 数 | 0 | 0 | 0 |
| `toc` 覆盖 TOC 条目 | 20/20 | 25/25 | 17/17 |
| `other` 数 | < 8 | < 5 | < 10 |
| 必需闭集单元 | `toc`、`abstract_cn`、`abstract_en`、`body_main`、`references` | 同左 | 同左 |
| unit 数量 | 不暴涨 | 不暴涨 | 不暴涨 |
| T2 flags | 下降 | 下降 | 下降 |

### 5.2 单测建议

新增或扩展：

- `test_t2_derives_toc_entry_like_from_atomic_facts`
- `test_t2_ignores_legacy_t1_semantic_fields_if_present`
- `test_t2_toc_block_claims_all_toc_entries`
- `test_t2_text_properties_only_is_candidate_not_unit_boundary`
- `test_t2_canonical_title_classifier_handles_format_annotations`
- `test_t2_duplicate_variant_block_is_grouped_as_other_with_variant_flag`

### 5.3 输出契约

`t2_input.json` 应包含：

```json
{
  "contexts": [
    {
      "entries": [
        {
          "source_ref": "...",
          "text": "...",
          "text_facts": {},
          "t2_derived_signals": {
            "toc_entry_like": true,
            "toc_title_like": false,
            "unit_heading_like": false
          }
        }
      ]
    }
  ]
}
```

注意：`t2_derived_signals` 只能出现在 T2 artifact 中，不能写回 `document_facts.json`。

---

## 6. 需要讨论的问题

1. `text_properties` 单独命中时，是完全不切，还是切成 `candidate_only` 后参与 span 但不进入正式 `unit_map.units[]`？
2. TOC block 中允许多少个非 `toc_entry_like` 的间隔段？例如"（农理工科类专业用）"、空行、格式说明。
3. `body_main` 的数字标题规则要多宽？`1 前言` 应识别正文，但目录条目和表格编号不能误伤。
4. 湖南变体块是只归 `other + variant_block_detected`，还是要开始引入 `variant_group_id`？
5. 当 T1 原子事实不足时，T2 应该如何表达不可判定？建议统一走 `open_question(kind=boundary|label|required_missing)`，并在 `signals_summary.missing_facts[]` 写清缺失项。

---

## 7. 非目标

- 不在 T1 恢复或新增 `is_toc_entry` 等语义字段。
- 不在 T2 消费旧 `is_toc_entry` / `structural_signals` 字段。
- 不在本 issue 中实现 AI 合并 `t2_ai_response.json`。
- 不做完整 variant model；本轮最多聚合为 `other + variant_block_detected`。
- 不解决 T3 段内元素切分。
- 不解决 T4 页码/分节 high confidence。
