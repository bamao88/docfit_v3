---
status: draft
owner: template-generation
stage: T2
topic: unit-recognition
plan_id: T2-UNIT-PLAN-02
plan_sequence: 2
created: 2026-06-25
last_updated: 2026-06-25
version: 0.1
source_issue:
  id: T2-UNIT-ISSUE-02
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md
previous_issue:
  id: T2-UNIT-ISSUE-01
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md
previous_plan:
  doc: docs/plans/template-parse-refactor-t2-open-label-unit-recognition.md
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/verifier.py
  - tests/unit/test_t2_unit_map.py
  - scripts/t2_metrics.py
related_future_docs:
  - docs/plans/template-parse-refactor-t2-visual-pagination.md
---

# T2 单元识别 Plan 02：Post-Phase2 Residual Fix

## 0. 一句话结论

本轮不是重新设计 T2，也不是马上接入 AI / visual page policy。

本轮目标是：**在当前 Phase 2 deterministic 主干之上，把三校真实模板中仍未收口的 unit boundary、unit label、后置单元、正文主体范围和 regression 门禁补齐**。

优先级判断：

```text
P0：deterministic residual fix
  - unowned range / block range ownership
  - canonical boundary hint
  - instruction_like 对核心标题不再硬 veto
  - taxonomy 扩展
  - 三校 expected unit / source_seq regression

P1：结构上下文修复
  - front matter -> body_main -> back matter 状态机
  - duplicate core contextual rule

P2：AI / visual / page_policy
  - 保留为后续增强
  - 本轮不把 AI 视为当前生成能力
```

本轮成功标准不是“TOC 条目覆盖继续 PASS”，而是：**最终 `unit_map` 的核心单元、学校预期单元、关键 source_seq 归属、正文范围、后置单元都达到可交付基线**。

---

## 1. 背景与事实基线

### 1.1 来源 issue

本计划对应：

```text
issue_id: T2-UNIT-ISSUE-02
issue_sequence: 2
topic: unit-recognition
created: 2026-06-25
```

Issue 02 的口径是：上一轮 Phase 2 deterministic 优化已经完成一批 T2 主干改造，但真实三校模板生成仍存在残余问题。因此，后续讨论应以当前代码真实运行结果为事实基线，而不是复用旧 issue 的历史结论。

### 1.2 当前代码与运行口径

当前真实运行口径：

```text
代码 checkpoint:
  e861aa5 chore: checkpoint template generation refactor state

运行时间:
  2026-06-25

运行方式:
  对三校真实模板执行 run_template_generate_eval(...)

当前输出根目录:
  /private/tmp/docfit_t2_current_run/{school}

TOC block range quick fix 后输出根目录:
  /private/tmp/docfit_t2_after_block_range_fix
```

当前三校总体仍未交付：

| 学校 | summary.status | first_bad_stage | unit 数 | T2 finding 数 | 结论 |
| --- | --- | --- | ---: | ---: | --- |
| hunannongye | UNKNOWN | T2 | 10 | 15 | T2 仍有阻断问题 |
| nannong-undergraduate | UNKNOWN | T2 | 10 | 6 | T2 仍有阻断问题 |
| pku-graduate | UNKNOWN | T2 | 21 | 16 | T2 仍有阻断问题 |

### 1.3 上一轮已经做过的事情

当前代码已经包含上一轮 Phase 2 的主要痕迹：

```text
1. T2 派生信号输出：debug.t2_derived_signals_by_source_seq
2. TOC block segmenter：_segment_toc_blocks()、_toc_block_anchor()、locked indices
3. 边界判定重写：text_properties candidate-only、table cell veto、裸 Heading-2+ 不切顶层
4. canonical title + alias：canonical_title()、_CORE_ALIAS_EXACT
5. custom_unit fallback：未知强边界进入 custom:template:*，不再落 other
6. form / variant 标记：form_block_detected、variant_block_detected
```

因此，本轮不能重复写“先做 TOC block / 开放标签 / candidate-only”这种上一轮计划，而应聚焦：**这些机制为什么还没有覆盖真实生成所需的全部单元语义与 range 收口**。

### 1.4 TOC 指标已经不再代表最终成功

当前 `scripts/t2_metrics.py` 已经可以通过三校 TOC 条目覆盖门禁：

```text
hunannongye            20/20 leak=0 PASS
nannong-undergraduate  25/25 leak=0 PASS
pku-graduate           17/17 leak=0 PASS
```

但这个指标只证明：

```text
TOC 条目被归入了 TOC-like 单元，且没有明显 leak。
```

它不能证明：

```text
1. 最终 unit boundary 正确。
2. 核心 label 正确。
3. 后置单元独立切出。
4. 正文主体范围正确。
5. 学校自定义/扩展单元被正确命名。
6. block 收口后没有 critical unowned range。
```

所以本轮必须新增 `unit-ranges / expected-vs-actual` 门禁。

---

## 2. 本轮目标

### 2.1 总目标

把当前 deterministic T2 主干从“TOC coverage 可通过”推进到“真实三校 unit_map 可交付基线”。

交付结果应至少满足：

```text
1. critical source_seq 不被 TOC / references / custom 等错误吞并。
2. 湖南 abstract_cn 能被识别。
3. 南农 appendix / academic_achievements / acknowledgement 能独立切出。
4. 北大 toc / figure_list / table_list 能区分。
5. 北大 body_main 从第一个正文章标题开始，正文内部 Heading 1 不再过切成多个顶层 custom_unit。
6. 北大后置 references 不再被 duplicate core 规则降成 custom。
7. 后置声明类单元有明确 taxonomy 或 school/template expected label。
8. 三校 expected units 与关键 source_seq 归属进入 regression。
```

### 2.2 P0 目标

| 编号 | 主题 | 成功口径 |
| --- | --- | --- |
| P0-A | unit range ownership / unowned range | 关键段落不再无人认领或被错误单元吞并；新增 range audit |
| P0-B | canonical boundary hint | boundary 阶段能识别带占位符、格式注释、标点的核心标题 |
| P0-C | instruction_like soft veto | 核心/学校预期标题不被格式说明硬 veto |
| P0-D | taxonomy 扩展 | `figure_list`、`table_list`、`academic_achievements`、声明类单元有稳定映射 |
| P0-E | 三校 expected regression | 三校 expected unit ids 与关键 source_seq 归属进入测试或脚本门禁 |

### 2.3 P1 目标

| 编号 | 主题 | 成功口径 |
| --- | --- | --- |
| P1-A | front/body/back state machine | 进入 `body_main` 后，正文 Heading 1 默认归正文内部，直到遇到后置 anchor |
| P1-B | duplicate core contextual rule | duplicate core 不再一律降 custom；结合位置、阶段、TOC/list block、正文内外判断 |

### 2.4 P2 留待后续

AI / visual / page_policy 不在本轮主实现内。后续可以独立开：

```text
T2-UNIT-PLAN-03: AI visual structure pass + T2 reconciler
T2-PAGE-POLICY-PLAN-01: visual pagination / render pipeline
```

本轮可以保留 `t2_input`、`open_questions`、debug signals 作为未来 AI 输入形状，但不能把 AI 写成当前能力。

---

## 3. 非目标

本轮明确不做：

```text
1. 不接入 live AI。
2. 不实现 t2_ai_visual_enabled / ai_visual / FixtureTransport / reconcile_t2 主链路。
3. 不实现 visual page_policy。
4. 不实现 DOCX -> 页面图 -> bbox -> blank_ratio 的 render pipeline。
5. 不做完整 variant model。
6. 不做 T3 单元内部 element parse。
7. 不做 T4 具体分页/分节 OOXML 实现。
8. 不把所有学校自定义章节无限塞进 global core taxonomy。
9. 不恢复 T1 语义字段，也不让 T2 消费旧 structural_signals。
```

特别约束：

```text
任何文档、日志、验收报告不得声称：
  “AI 已兜底 unknown heading / visual block / page_policy”

除非对应 feature 已真实接入当前生成链路并有 fixture / eval 证明。
```

---

## 4. 架构边界

### 4.1 T1 / T2 边界保持不变

T1 只产原子事实：

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

T1 不产：

```text
is_toc_entry
is_spacing_line
looks_like_instruction_text
likely_unit_heading
large_font
short_text
```

这些都属于 T2 派生信号。

### 4.2 T2 只能使用 T2 自己派生的结构语义

T2 可以计算：

```text
toc_title_like
toc_entry_like
instruction_like
spacing_line_like
unit_heading_like
canonical_label_hint
block_candidate
boundary_candidate
```

但这些信号只能存在于 T2 artifact / debug / evidence 中，不能写回 `document_facts`。

### 4.3 block-first 仍然是主线

运行顺序保持：

```text
T1 atomic facts
  ↓
T2 derived signals
  ↓
block segmenter
  ↓
locked block ranges
  ↓
generic boundary detection
  ↓
unit span creation
  ↓
labeling / contextual relabeling
  ↓
range ownership audit
  ↓
required / expected unit check
```

本轮新增的关键在后半段：

```text
canonical boundary hint
instruction veto softening
extended taxonomy
front/body/back state machine
duplicate contextual relabeling
unit range ownership audit
```

---

## 5. 关键概念与新口径

### 5.1 source_seq ownership

每个 `source_seq` 在 T2 层应属于以下之一：

```text
1. 某个正式 unit 的 span。
2. 某个 locked block 的内部段落。
3. 被明确标记为 ignorable / spacer / pure instruction。
4. 被记录为 unowned range，并进入 open_question / range audit。
```

关键段落不能静默无人认领。

本轮新增：

```json
{
  "debug": {
    "unit_range_audit": {
      "unowned_ranges": [],
      "overlaps": [],
      "critical_unowned_ranges": [],
      "expected_source_seq_results": []
    }
  }
}
```

### 5.2 critical unowned range

不是所有 unowned 都是错误。空白、纯说明、可忽略分隔可能允许 unowned。

但以下属于 critical：

```text
1. canonical_label_hint 命中 core / extended / school expected label。
2. unit_heading_like = true。
3. 非表格内、非空白、非纯 spacing_line。
4. 处在两个强单元之间，且文本非空。
5. 是三校 expected source_seq 中指定的关键段落。
```

critical unowned 必须进入门禁。

### 5.3 expected unit 分层

不要把所有单元塞入 global core。

建议分为：

```text
global_core:
  toc
  abstract_cn
  abstract_en
  body_main
  references

global_extended:
  figure_list
  table_list
  appendix
  acknowledgement
  originality_statement
  authorization_statement
  originality_authorization_statement
  copyright_notice
  integrity_statement

school_expected:
  academic_achievements
  opening_report
  task_book
  review_forms
  defense_forms
  score_evaluation

template_optional:
  custom:template:*
  form_block
  variant_block
```

验收时应区分：

```text
缺 global_core：通常阻断。
缺 school_expected：在对应学校模板 regression 中阻断。
缺 template_optional：不阻断，但需保留 raw_title / source_seq / evidence。
```

### 5.4 title + instruction 复合行

很多真实模板标题长这样：

```text
□□摘□要（小四黑体）：...
附 录 附录名称（三号黑体，居中）
致 谢（三号黑体，居中）
```

它们同时具有：

```text
标题主体
+ 格式说明
+ 可能的占位符
+ 可能的标点或冒号
```

本轮要把它们识别为：

```text
title_with_format_annotation
```

而不是：

```text
instruction_text
```

### 5.5 top-level unit 与 body internal heading

`Heading 1` 不必然等于顶层 unit boundary。

在进入 `body_main` 之前，`Heading 1` 可以是强 top-level 候选。

进入 `body_main` 之后：

```text
Heading 1 默认是正文内部章节。
只有命中明确 back_matter label 或 declaration label，才可跳出 body_main。
```

这是解决北大过切的核心。

---

## 6. P0-A：unit range ownership / unowned range 收口

### 6.1 问题

TOC block range quick fix 后，TOC 外溢已收敛，但暴露出新的 unowned ranges：

```text
湖南：seq 50-64 无人认领；abstract_cn 仍缺失。
南农：seq 35-36 无人认领；appendix / acknowledgement 仍被吞并。
北大：TOC coverage 仍 PASS，但 figure_list / table_list taxonomy 缺失，正文和后置区仍错位。
```

### 6.2 根因

上一轮主要解决：

```text
TOC entries 是否归入 toc。
```

但没有系统解决：

```text
block 收口后，下一个真实 unit 的 anchor 是否形成。
每段 source_seq 是否被合法 owner 消费。
关键段落无人认领时是否进入门禁。
```

### 6.3 实现策略

新增 range audit：

```python
def audit_unit_ranges(entries, units, locked_blocks, expected_contract):
    """Return unowned, overlapping, critical_unowned, expected_seq_results."""
```

审计维度：

```text
1. coverage：每个 source_seq 是否被某个 unit / block / ignorable reason 覆盖。
2. overlap：同一 source_seq 是否被多个 final units 覆盖。
3. block ownership：locked block 的 range 是否被最终 unit 消费到正确 end。
4. critical unowned：疑似标题/核心标签/expected source_seq 是否无人认领。
5. expected source_seq：合同中指定的 seq 是否属于预期 unit。
```

### 6.4 输出契约

建议 debug 输出：

```json
{
  "unit_range_audit": {
    "unowned_ranges": [
      {
        "start_source_seq": 50,
        "end_source_seq": 64,
        "severity": "critical",
        "reason": "contains_core_label_hint_or_unit_heading",
        "sample_text": ["正文基本格式...", "□□摘□要（小四黑体）：..."]
      }
    ],
    "overlaps": [],
    "expected_source_seq_results": [
      {
        "school": "hunannongye",
        "source_seq": 57,
        "expected_unit_ids": ["abstract_cn"],
        "actual_unit_id": null,
        "status": "FAIL"
      }
    ]
  }
}
```

### 6.5 验收

```text
湖南：toc 不包含 seq 50-64；seq 57 不再 unowned；abstract_cn 或明确摘要复合单元覆盖 seq 57。
南农：seq 109 不属于 references；seq 113 不属于 academic_achievements；appendix / acknowledgement 独立成 unit。
北大：figure_list / table_list 独立；正文关键 Heading 1 不再成为顶层 custom_unit。
```

---

## 7. P0-B：canonical boundary hint 前移

### 7.1 问题

当前 `canonical_title()` 主要在 label 阶段使用。

但如果 boundary 阶段没有形成 anchor，label 阶段就没有机会补救。

典型失败：

```text
seq 57 □□摘□要（小四黑体）：...
```

这类文本应在 boundary 阶段就得到：

```text
canonical_label_hint = abstract_cn
```

### 7.2 实现策略

将 canonical title classifier 拆成两层：

```python
def canonical_title(text: str) -> str:
    ...

def canonical_label_hint(text: str, *, context=None) -> LabelHint | None:
    ...
```

`canonical_label_hint()` 在 boundary 阶段可使用，但只能作为 hint：

```text
1. 命中 core / extended / school_expected label：增强 boundary evidence。
2. 命中 keyword-only 弱 label：不得单独切 boundary。
3. 命中 body_main 数字标题：必须检查非 TOC、非表格、非 trailing page token。
```

### 7.3 标题归一化要求

`canonical_title()` 至少处理：

```text
1. 删除占位符：□、×、__、下划线串。
2. 删除格式注释：括号中包含字体、字号、加粗、居中、黑体、宋体、Times New Roman 等。
3. 删除行尾冒号/中文冒号后纯格式说明。
4. 删除点引线和尾部页码 token。
5. 统一全半角、大小写、空格。
6. 合并分散字符：摘 要 -> 摘要；目 录 -> 目录；致 谢 -> 致谢。
```

示例：

| raw text | canonical_title | hint |
| --- | --- | --- |
| `目□□录（二号黑体，居中）` | `目录` | `toc` |
| `□□摘□要（小四黑体）：...` | `摘要` | `abstract_cn` |
| `附 录 附录名称（三号黑体，居中）` | `附录附录名称` / `附录` | `appendix` |
| `致 谢（三号黑体，居中）` | `致谢` | `acknowledgement` |
| `图目录` | `图目录` | `figure_list` |
| `表目录` | `表目录` | `table_list` |

### 7.4 boundary 使用规则

建议：

```python
hint = canonical_label_hint(entry.text, context=context)

if hint and hint.scope in {"global_core", "global_extended", "school_expected"}:
    evidence.add("canonical_label_hint", hint.unit_id)
    score += hint.boundary_weight

if instruction_like and hint:
    # instruction_like 不再硬 veto，只降低置信度或要求更多证据。
    veto = False
    confidence_penalty += 1
```

`canonical_label_hint` 不能变成新的宽泛关键词切边界。

硬约束：

```text
keyword-only 仍不能切 boundary。
只有 canonical title 短标题、格式剥离后精确命中 label、且不是 TOC entry / table cell / trailing page token，才允许增强 boundary。
```

### 7.5 验收

```text
湖南 seq 57：产生 abstract_cn boundary 或进入 abstract_cn 复合单元。
南农 seq 109：产生 appendix boundary。
南农 seq 113：产生 acknowledgement boundary。
北大 图目录/表目录：不再映射为主 toc。
```

---

## 8. P0-C：instruction_like 从硬 veto 改成上下文软 veto

### 8.1 问题

当前 `_boundary_vetoes()` 对 `instruction_text` 采用硬 veto。

这会误伤：

```text
附 录 附录名称（三号黑体，居中）
致 谢（三号黑体，居中）
□□摘□要（小四黑体）：...
```

这些不是纯 instruction，而是 `title_with_format_annotation`。

### 8.2 新规则

将 instruction-like 分为：

```text
pure_instruction:
  整段主要是格式说明、填写说明、使用说明。

title_with_format_annotation:
  标题主体明确，括号或冒号后带格式说明。

ambiguous_instruction_title:
  既像标题又像说明，证据不足。
```

决策表：

| 类型 | canonical_label_hint | 行为 |
| --- | --- | --- |
| pure_instruction | none | hard veto |
| pure_instruction | weak keyword only | hard veto / candidate only |
| title_with_format_annotation | core / extended / school_expected | allow boundary，最多降一档 confidence |
| ambiguous_instruction_title | core / extended / school_expected | candidate 或 medium boundary，进入 open_question |
| ambiguous_instruction_title | none | 不切 boundary，进入 open_question |

### 8.3 实现建议

新增：

```python
def classify_instruction_context(entry, canonical_hint) -> InstructionClass:
    ...
```

返回：

```text
pure_instruction
title_with_format_annotation
ambiguous_instruction_title
not_instruction
```

`_boundary_vetoes()` 改为：

```python
if instruction_class == "pure_instruction":
    return Veto("instruction_text")

if instruction_class == "title_with_format_annotation":
    return NoVeto(confidence_penalty="instruction_annotation")

if instruction_class == "ambiguous_instruction_title":
    return CandidateOnlyOrOpenQuestion(...)
```

### 8.4 验收

```text
南农 appendix / acknowledgement 不再被 instruction_text veto。
湖南 abstract_cn 不再被 instruction_text veto。
纯填写说明仍不会被切成顶层 unit。
```

---

## 9. P0-D：taxonomy 扩展与 list block 类型拆分

### 9.1 问题

北大的 `图目录` / `表目录` 当前无法正确产出，因为：

```text
1. UNIT_DEFINITIONS 没有 figure_list / table_list。
2. _CORE_ALIAS_EXACT 把 图目录 / 表目录 都映射为 toc。
3. _TOC_TITLE_NORMALIZED 把主目录、图目录、表目录当作同一种 TOC title。
```

### 9.2 新 taxonomy 层级

建议新增：

```yaml
global_extended:
  figure_list:
    display_name: 图目录
    aliases:
      - 图目录
      - 插图目录
      - List of Figures
      - Figures

  table_list:
    display_name: 表目录
    aliases:
      - 表目录
      - 表格目录
      - List of Tables
      - Tables

  appendix:
    display_name: 附录
    aliases:
      - 附录
      - 附 录
      - Appendix

  acknowledgement:
    display_name: 致谢
    aliases:
      - 致谢
      - 致 谢
      - Acknowledgements
      - Acknowledgments

  originality_statement:
    display_name: 原创性声明
    aliases:
      - 原创性声明
      - 独创性声明
      - 学位论文原创性声明

  authorization_statement:
    display_name: 授权声明
    aliases:
      - 授权声明
      - 学位论文使用授权书
      - 授权书

  originality_authorization_statement:
    display_name: 原创性及授权声明
    aliases:
      - 原创性声明和使用授权书
      - 原创性及授权声明
      - 学位论文原创性声明及使用授权书

school_expected:
  academic_achievements:
    display_name: 相关的学术成果目录
    aliases:
      - 相关的学术成果目录
      - 学术成果目录
      - 攻读学位期间取得的学术成果
```

### 9.3 list block segmenter 泛化

将 TOC block segmenter 泛化为 list-like block segmenter：

```text
main_toc:
  title: 目录 / 目 录
  entries: toc_entry_like
  unit_id: toc

figure_list:
  title: 图目录 / 插图目录
  entries: figure_entry_like 或 toc_entry_like-like
  unit_id: figure_list

table_list:
  title: 表目录 / 表格目录
  entries: table_entry_like 或 toc_entry_like-like
  unit_id: table_list
```

实现上可以复用 block range 收集逻辑，但 block type 必须区分。

### 9.4 标题映射优先级

```text
figure_list / table_list 的 title 不得再映射为 toc。

优先级：
  figure_list exact title
  table_list exact title
  main toc exact title
  generic toc-like block fallback
```

### 9.5 验收

```text
北大：toc、figure_list、table_list 三个 unit 独立存在。
北大：seq 31 图目录 不属于 toc。
北大：seq 46 表目录 不属于 toc 或 figure_list。
北大：figure/table list 可以复用 TOC-like entry 识别，但 final unit_id 必须区分。
```

---

## 10. P0-E：三校 expected unit / source_seq regression

### 10.1 问题

当前 `CORE_REQUIRED_UNIT_IDS = {"body_main"}` 过弱。

缺少：

```text
abstract_cn
appendix
acknowledgement
figure_list
table_list
academic_achievements
```

不会触发 required missing。

### 10.2 新增 expected contract

建议新增 fixture：

```text
tests/fixtures/t2_expected_units/hunannongye.yaml
tests/fixtures/t2_expected_units/nannong_undergraduate.yaml
tests/fixtures/t2_expected_units/pku_graduate.yaml
```

示例：

```yaml
school: hunannongye
expected_units:
  - unit_id: toc
    required: true
    source_seq_contains_any: [24, 27, 49]
    source_seq_excludes: [50, 57, 64]
  - unit_id: abstract_cn
    required: true
    source_seq_contains_any: [57]
  - unit_id: abstract_en
    required: true
    source_seq_contains_any: [65]
critical_unowned_forbidden:
  - [50, 64]
```

```yaml
school: nannong-undergraduate
expected_units:
  - unit_id: toc
    required: true
    source_seq_contains_any: [9, 34]
    source_seq_excludes: [35, 36]
  - unit_id: appendix
    required: true
    source_seq_contains_any: [109]
  - unit_id: academic_achievements
    required: true
    source_seq_contains_any: [111]
  - unit_id: acknowledgement
    required: true
    source_seq_contains_any: [113]
```

```yaml
school: pku-graduate
expected_units:
  - unit_id: toc
    required: true
  - unit_id: figure_list
    required: true
    source_seq_contains_any: [31]
  - unit_id: table_list
    required: true
    source_seq_contains_any: [46]
  - unit_id: body_main
    required: true
    start_source_seq_lte: 50
    source_seq_contains_any: [50, 92, 221, 302]
  - unit_id: references
    required: true
    source_seq_contains_any: [306]
    forbidden_actual_prefix: "custom:template:参考文献"
```

### 10.3 新脚本 / 参数

新增或扩展：

```text
scripts/t2_metrics.py --unit-ranges
```

输出：

```text
school                 expected_units  expected_seq  critical_unowned  overlaps  status
hunannongye            5/5             PASS          0                 0         PASS
nannong-undergraduate  6/6             PASS          0                 0         PASS
pku-graduate           7/7             PASS          0                 0         PASS
```

### 10.4 验收门禁

本轮 CI / regression 至少包含：

```text
1. 三校 TOC coverage 仍 PASS。
2. 三校 expected_units PASS。
3. critical_unowned = 0。
4. expected source_seq 所属 unit 正确。
5. 后置 references / appendix / acknowledgement 不被前一单元吞并。
6. 北大正文内部 Heading 1 不变顶层 custom_unit。
```

---

## 11. P1-A：front matter -> body_main -> back matter 状态机

### 11.1 问题

北大正文主体被切成多个顶层 `custom_unit`：

```text
seq 50  研究背景
seq 92  插图、公式与表格
seq 221 其他注意事项
seq 302 结论与讨论
```

这些在北大模板中应属于 `body_main` 内部章节，而不是顶层单元。

### 11.2 状态定义

```text
front_matter:
  toc
  figure_list
  table_list
  abstract_cn
  abstract_en
  declarations before body
  preface-like blocks before body

body_main:
  正文主体
  包含正文内 Heading 1 / Heading 2 / 数字章标题
  直到遇到 back_matter anchor

back_matter:
  references
  appendix
  acknowledgement
  academic_achievements
  originality_statement
  authorization_statement
  originality_authorization_statement
  other post-body forms
```

### 11.3 状态转移

```text
front_matter -> body_main:
  1. 命中 explicit body_main label；或
  2. 经过 toc / figure_list / table_list / abstracts 后，遇到第一个 body-like top-level heading；或
  3. TOC 中一级正文条目与当前 heading 匹配，且不属于 known back_matter label。

body_main -> back_matter:
  1. 遇到 references / appendix / acknowledgement / declaration / academic_achievements 等明确后置 label；且
  2. 当前段落不在 TOC / list block / table cell 内；且
  3. 位置在 body_main 已开始之后。
```

### 11.4 body_main 内部吸收规则

进入 `body_main` 后：

```text
Heading 1 不再默认产生顶层 custom_unit。

如果 Heading 1 的 canonical_label_hint 不属于 back_matter：
  保留在 body_main span 内。

如果 Heading 1 命中 back_matter：
  结束 body_main，开始对应后置 unit。
```

### 11.5 与 T3 的边界

T2 不解析正文内部章节层级。

T2 只负责：

```text
把正文内部 Heading 1 保留在 body_main span 中。
```

T3 后续再解析：

```text
body_main.sections[]
body_main.headings[]
paragraph elements
figure/table/form elements
```

### 11.6 验收

```text
北大 body_main 从 seq 50 附近开始。
seq 50 / 92 / 221 / 302 属于 body_main。
这些段落不再作为顶层 custom:template:* unit 出现。
body_main 在真正 references 之前结束。
```

---

## 12. P1-B：duplicate core contextual rule

### 12.1 问题

当前 duplicate core 规则过粗：

```text
同一个 core unit_id 第二次出现 -> custom
```

这导致：

```text
北大 seq 306 参考文献 -> custom:template:参考文献:306
北大末尾 原创性声明 -> custom，而不是声明类单元
```

### 12.2 新规则

duplicate core 不直接 custom，先看上下文。

决策顺序：

```text
1. 在 locked toc / figure_list / table_list block 内：
   不参与 duplicate，归所在 block。

2. 在 body_main 内部，且不是 back_matter anchor：
   不切顶层 unit，作为 body_main 内部标题。

3. 在 body_main 之后，且命中 back_matter label：
   允许作为正式 back_matter unit，即使 label 之前在说明文字或目录里出现过。

4. declaration 类标题：
   优先映射到声明 taxonomy，不降 generic custom。

5. 确实重复且上下文无法解释：
   custom_unit 或 open_question(kind=label, reason=duplicate_core_ambiguous)。
```

### 12.3 examples

```text
body_main 内出现 “参考文献格式如下”：
  不切顶层 references。

body_main 后出现独立 “参考文献”：
  切 references。

正文后出现 “原创性声明”：
  切 originality_statement 或 originality_authorization_statement。

TOC block 内出现 “参考文献”：
  归 toc，不参与 duplicate。
```

### 12.4 验收

```text
北大后置 references 不再是 custom:template:参考文献:*。
北大正文说明里的 references-like 文本不误切。
北大声明页不再是普通 custom，而是声明类 taxonomy 或 school_expected unit。
```

---

## 12.5 T2 数据转换逻辑与字段契约（防断层）

本节约束本轮 T2 改造的数据流，目标是避免再次出现：

```text
1. 前面阶段生产了字段，但后面没有消费。
2. debug 里能看到问题，但 verifier / metrics / unit_map 不知道。
3. expected contract 在脚本里 PASS，但真实生成 verification_report 仍无法解释。
4. 某个 hint 被写入 artifact，却没有明确决策责任。
```

### 12.5.1 总体流水线

本轮 T2 的数据转换必须保持单向流：

```text
T1 document_facts
  ↓ source_tree_from_document_facts()
T2 source entries
  ↓ derive_t2_entry_signals()
T2 derived entry signals
  ↓ segment_list_like_blocks()
locked list-like blocks
  ↓ detect_boundary_candidates()
raw boundary candidates / anchors
  ↓ label_boundary_candidates()
preliminary labeled anchors
  ↓ reconcile_document_zones()
front_matter / body_main / back_matter final anchors
  ↓ build_unit_spans()
template_structure_candidates.units
  ↓ audit_unit_ranges_and_expected_contract()
unit_range_audit + expected_unit_results
  ↓ build_unit_map()
unit_map.units + unit_map.flags + unit_map.open_questions
  ↓ verifier / metrics / T3 / T4
verification_report + regression gates + downstream specs
```

硬规则：

```text
1. T1 只提供事实；T2 不把派生字段写回 document_facts。
2. T2 debug 字段只能作为观测面；任何会影响验收的字段必须同步到 flags / open_questions / verifier finding。
3. 每个新增字段必须有明确 consumer；如果只有 debug consumer，字段名和文档必须标明 debug-only。
4. expected source_seq gate 不能只存在于 scripts/t2_metrics.py；真实生成链路也必须能在 T2 finding 中暴露 mismatch。
```

### 12.5.2 输入字段：T2 可以消费什么

T2 入口是 `source_tree.layers.body_flow` 中的 visible body entries。

允许消费的 T1 原子字段：

| 字段 | 来源 | T2 用途 | 禁止事项 |
| --- | --- | --- | --- |
| `source_ref` | T1 OOXML 坐标 | trace、range、evidence | 不得根据字符串猜语义 |
| `source_seq` | T1 body 顺序 | range、ownership、expected contract | 不得重排或复用 |
| `node_id` / `paragraph_id` | T1 trace | debug、entry_refs | 不得作为语义 label |
| `kind` / `flow_item_type` | T1 fact | table cell veto、body flow filter | 不得产出 unit_id |
| `text` | T1 visible text | normalization、TOC/list/title detection | 不得在 T1 预打语义标记 |
| `style` / `style_details.paragraph.style_name` | T1 style fact | heading level、TOC style hint | 不得当作唯一 boundary 证据 |
| `style_details.paragraph.alignment` | T1 paragraph fact | centered/text_properties signal | 不得单独切顶层 unit |
| `style_details.dominant_run.font_size_pt` | T1 run fact | large_font signal | 不得写回 `large_font` 到 T1 |
| `style_details.dominant_run.bold` | T1 run fact | bold/text_properties signal | 不得写回 `bold semantic` 到 T1 |
| `container_ref` / table refs | T1 structural fact | table cell veto、container trace | table 内文本不得开顶层 unit |
| `data.breaks` / section breaks | T1 OOXML fact | break evidence、state hint | 不得替代 label 判定 |

禁止消费的旧 T1 语义字段仍包括：

```text
is_toc_entry
is_spacing_line
looks_like_instruction_text
likely_unit_heading
large_font
short_text
unit_id
policy
confidence
```

如果旧 artifact 中存在这些字段，T2 必须忽略，并重新从原子事实派生。

### 12.5.3 T2 entry derived signals

T2 可以为每个 entry 派生结构信号。它们只存在于 T2 内存、`template_structure_candidates.debug`、boundary evidence、open_question context 中。

建议字段：

| 字段 | 类型 | producer | consumer | 验收作用 |
| --- | --- | --- | --- | --- |
| `toc_title_like` | bool | list title classifier | list block segmenter | debug-only + block evidence |
| `toc_entry_like` | bool | TOC entry classifier | list block segmenter、TOC metric | TOC coverage gate |
| `list_title_type` | enum/null | canonical title classifier | list block segmenter | 区分 `toc` / `figure_list` / `table_list` |
| `list_entry_like` | bool | list entry classifier | list block segmenter | list block coverage |
| `instruction_like` | bool | instruction classifier | instruction class resolver | 不能直接 hard veto 核心标题 |
| `instruction_class` | enum | instruction class resolver | boundary veto、element policy | `pure_instruction` 才 hard veto |
| `spacing_line_like` | bool | spacing classifier | boundary veto、audit ignorable | 可解释 unowned |
| `unit_heading_like` | bool | style/text classifier | boundary candidate、audit | critical unowned 判定 |
| `canonical_title` | string | title normalizer | label hint、debug | 不直接等于 unit_id |
| `canonical_label_hint` | object/null | alias/taxonomy matcher | boundary score、labeling、audit | expected mismatch gate |

`canonical_label_hint` 建议形状：

```json
{
  "unit_id": "abstract_cn",
  "scope": "global_core",
  "match_type": "exact_canonical_title",
  "confidence": "high",
  "normalized_title": "摘要"
}
```

`instruction_class` 可取值：

```text
not_instruction
pure_instruction
title_with_format_annotation
ambiguous_instruction_title
```

消费规则：

```text
pure_instruction:
  - boundary hard veto
  - 可作为 audit ignorable reason

title_with_format_annotation + canonical_label_hint:
  - 不 veto
  - 增加 boundary evidence
  - evidence 记录 `instruction_annotation`

ambiguous_instruction_title:
  - 默认 candidate/open_question
  - 若命中 expected source_seq，升级为 critical audit item
```

### 12.5.4 list-like block 字段

本轮不再把所有目录类 block 都叫 TOC。内部统一称 list-like block。

建议 block 字段：

```json
{
  "block_id": "list-block-0003",
  "block_type": "figure_list",
  "unit_id": "figure_list",
  "start_index": 31,
  "end_index": 45,
  "start_source_seq": 31,
  "end_source_seq": 45,
  "title_source_seq": 31,
  "entries_count": 14,
  "title_led": true,
  "weak": false,
  "locked_source_seq_refs": [31, 32, 33]
}
```

字段消费关系：

| 字段 | consumer | 必须效果 |
| --- | --- | --- |
| `block_type` | block anchor、labeling、metrics | 不能再把 `图目录` / `表目录` 降成 `toc` |
| `unit_id` | `_list_block_anchor()` | 生成对应 unit anchor |
| `start_index` / `end_index` | locked range、unit span builder | block unit 必须按 block end 收口 |
| `start_source_seq` / `end_source_seq` | debug、audit、metrics | 真实输出可解释 |
| `locked_source_seq_refs` | boundary detector、range audit | block 内 entry 不参与 generic boundary |
| `weak` | confidence/open_question | 弱 block 必须进入 review，而不是静默 PASS |

如果 block 字段只进入 debug、不影响最终 unit range，则视为无效实现。

### 12.5.5 boundary candidate / anchor 字段

所有 boundary 来源统一成同一 shape。来源包括：

```text
1. generic boundary decision
2. list-like block anchor
3. keyword exact fallback
4. body_main fallback
5. document start fallback
```

建议字段：

```json
{
  "entry_index": 57,
  "source_ref": "word/document.xml:p[57]",
  "source_seq": 57,
  "text": "□□摘□要（小四黑体）：...",
  "normalized_text": "摘要",
  "canonical_label_hint": {
    "unit_id": "abstract_cn",
    "scope": "global_core",
    "match_type": "exact_canonical_title",
    "confidence": "high"
  },
  "instruction_class": "title_with_format_annotation",
  "score": 4,
  "signals": [
    {"kind": "canonical_label_hint", "weight": 2, "unit_id": "abstract_cn"},
    {"kind": "instruction_annotation", "weight": 0}
  ],
  "vetoes": [],
  "unit_id_hint": "abstract_cn",
  "name_hint": "中文摘要",
  "is_boundary": true,
  "is_candidate": false,
  "confidence": "high",
  "fallback_reason": null,
  "block_range": null
}
```

字段消费关系：

| 字段 | consumer | 说明 |
| --- | --- | --- |
| `canonical_label_hint` | boundary score、labeling、audit | 不能只 debug；要影响核心标题识别 |
| `instruction_class` | veto、open_question、element policy | 避免 pure instruction 和 format annotation 混淆 |
| `signals` | unit evidence、open_questions、debug | 必须能解释为什么切/不切 |
| `vetoes` | open_questions、debug | veto 后仍保留 reason |
| `unit_id_hint` | `_label_boundaries()` | 只是 hint，不是最终 label |
| `block_range` | unit span builder | list block 必须按 block range 收口 |
| `confidence` | open_questions、unit_map flags | medium/low 必须可追踪 |

### 12.5.6 label / taxonomy 字段

label pass 只负责把 boundary anchor 映射成 preliminary unit label。

建议字段：

```json
{
  "unit_id": "figure_list",
  "name": "图目录",
  "label_status": "alias_matched",
  "canonical_label_id": "figure_list",
  "taxonomy_scope": "global_extended",
  "raw_title": "图目录",
  "normalized_title": "图目录",
  "display_name": "图目录",
  "flags": []
}
```

`label_status` 可取值：

```text
core_matched
alias_matched
school_expected_matched
custom_detected
candidate_only
unmapped
duplicate_held
```

`taxonomy_scope` 可取值：

```text
global_core
global_extended
school_expected
template_optional
custom
unknown
```

消费规则：

```text
1. `unit_id` 是下游 T3/T4/T5 的主键，不能随意重命名。
2. `canonical_label_id` 记录 closed-set label；custom unit 为 null。
3. `taxonomy_scope=school_expected` 必须由 expected contract 或学校 profile 支撑。
4. custom unit 必须保留 raw_title / normalized_title / display_name / source_seq，进入 taxonomy_review_queue。
```

### 12.5.7 front/body/back state 字段

状态机是 preliminary anchors 到 final anchors 的中间 pass。它不能只做 debug；必须能改变最终 anchor 行为。

建议 trace 字段：

```json
{
  "source_seq": 92,
  "from_state": "body_main",
  "to_state": "body_main",
  "anchor_unit_id": "custom:template:插图公式与表格:92",
  "decision": "absorb_into_body_main",
  "reason": "heading1_inside_body_without_back_matter_label",
  "result_unit_id": "body_main"
}
```

状态可取值：

```text
front_matter
body_main
back_matter
unknown
```

decision 可取值：

```text
keep_top_level_unit
start_body_main
absorb_into_body_main
start_back_matter_unit
hold_as_custom
open_question
```

消费规则：

```text
1. `absorb_into_body_main` 必须改变最终 unit spans，不能只写 trace。
2. `start_back_matter_unit` 必须结束 body_main range。
3. 无法判断的 transition 必须进入 `open_questions(reason=body_state_transition_ambiguous)`。
4. 北大 seq 50 / 92 / 221 / 302 必须在 trace 中可解释为 body_main 内部 heading。
```

### 12.5.8 unit span 字段

final anchors 生成 final units。unit 是 T2 对下游的主要契约。

建议字段：

```json
{
  "unit_id": "body_main",
  "name": "正文",
  "order": 80,
  "status": "required",
  "label_status": "core_matched",
  "canonical_label_id": "body_main",
  "taxonomy_scope": "global_core",
  "raw_title": "研究背景",
  "normalized_title": "研究背景",
  "display_name": "研究背景",
  "source_refs": ["word/document.xml:p[50]"],
  "source_seq_refs": [50, 51, 52],
  "source_range": {
    "start_source_ref": "word/document.xml:p[50]",
    "end_source_ref": "word/document.xml:p[305]"
  },
  "source_seq_range": {
    "start": 50,
    "end": 305,
    "source_seq_refs": [50, 51, 52]
  },
  "anchors": [],
  "evidence": [],
  "flags": [],
  "confidence": "high"
}
```

字段消费关系：

| 字段 | consumer | 失败时表现 |
| --- | --- | --- |
| `unit_id` | generation_model、T3/T4/T5、metrics | 错 label 会导致下游策略错 |
| `source_seq_refs` | range audit、expected contract、T4/T5 binding | 缺失会导致 ownership gap |
| `source_seq_range` | metrics、debug、template_spec binding | range 错会导致吞并/漏段 |
| `label_status` | unit_map flags、taxonomy review | unknown/custom 必须可审 |
| `canonical_label_id` | downstream known-unit policy | null 只能出现在 custom/unknown |
| `raw_title` / `normalized_title` | review/debug/taxonomy | custom 不能丢标题 |
| `evidence` | verifier/debug | 解释切分原因 |
| `flags` | unit_map、verification_report | UNKNOWN/FAIL 必须进入报告 |

### 12.5.9 range audit 字段

range audit 是本轮防断层的核心。它必须在 unit span 之后运行。

建议字段：

```json
{
  "unit_range_audit": {
    "unowned_ranges": [
      {
        "start_source_seq": 50,
        "end_source_seq": 56,
        "severity": "unknown",
        "reason": "title_fragment_or_instruction",
        "sample_text": ["正文基本格式..."],
        "owner_unit_id": null
      }
    ],
    "overlaps": [],
    "critical_unowned_ranges": [],
    "expected_source_seq_results": [
      {
        "school": "hunannongye",
        "source_seq": 57,
        "expected_unit_ids": ["abstract_cn"],
        "actual_unit_id": "abstract_cn",
        "status": "PASS"
      }
    ]
  }
}
```

消费规则：

```text
1. `unit_range_audit` 原始明细进入 `template_structure_candidates.debug`。
2. `critical_unowned_ranges` 非空时，必须生成 unit_map flag。
3. expected source_seq FAIL 时，必须生成 unit_map flag，并由 verifier 输出 T2 finding。
4. metrics 只能复用 audit 结果，不能重新实现一套不一致的归属逻辑。
5. audit PASS 才能说三校 expected unit/source_seq contract PASS。
```

flag 建议形状：

```json
{
  "type": "unit_range_expected_source_seq_mismatch",
  "status": "FAIL",
  "source_seq": 57,
  "expected": "abstract_cn",
  "actual": null,
  "reason": "expected source_seq is unowned",
  "affected_ids": ["abstract_cn"]
}
```

open_question reason：

```text
critical_unowned_range
expected_source_seq_mismatch
body_state_transition_ambiguous
duplicate_core_ambiguous
title_with_format_annotation_ambiguous
```

### 12.5.10 expected contract 字段

三校 expected contract 是 regression 输入，不是 debug 输出。

建议 YAML schema：

```yaml
school: hunannongye
source_template: inputs/targets/hunannongye/raw/source_template.docx
expected_units:
  - unit_id: toc
    required: true
    source_seq_contains_any: [24, 27, 49]
    source_seq_excludes: [50, 57, 64]
  - unit_id: abstract_cn
    required: true
    source_seq_contains_any: [57]
critical_unowned_forbidden:
  - [57, 57]
allowed_unowned_ranges:
  - range: [50, 56]
    reason: title_fragment_or_instruction
```

字段消费关系：

| 字段 | consumer | 说明 |
| --- | --- | --- |
| `school` | metrics、test id | 必须和 fixture 文件名一致 |
| `source_template` | metrics/manual run | 防止 contract 套错模板 |
| `expected_units[].unit_id` | expected unit checker | required unit gate |
| `source_seq_contains_any` | ownership checker | seq 必须归属 expected unit |
| `source_seq_excludes` | ownership checker | seq 不得被该 unit 吞并 |
| `critical_unowned_forbidden` | range audit | 命中即 FAIL |
| `allowed_unowned_ranges` | range audit | 只允许有明确 reason 的 gap |

contract loader 必须被这些入口复用：

```text
1. tests/unit/test_t2_unit_range_contracts.py
2. scripts/t2_metrics.py --unit-ranges
3. verifier T2 expected-source-seq finding
```

### 12.5.11 structure_candidates -> unit_map 转换

`template_structure_candidates` 是 T2 详细工作台；`unit_map` 是下游正式契约。

转换规则：

```text
structure_candidates.units[*]
  -> unit_map.units[*]

structure_candidates.open_questions
  -> unit_map.open_questions

structure_candidates.taxonomy_review_queue
  -> unit_map.taxonomy_review_queue

structure_candidates.debug.unit_range_audit critical/FAIL items
  -> unit_map.flags
  -> verification_report.findings
```

不能只停留在 `structure_candidates.debug` 的字段：

```text
1. expected source_seq mismatch
2. critical unowned range
3. unit overlap
4. required expected unit missing
5. body_main 状态转移冲突
6. duplicate core ambiguity that affects final unit_id
```

可以 debug-only 的字段：

```text
1. raw derived signal map
2. list block candidate traces that did not affect final units
3. state_machine_trace PASS records
4. duplicate_core_decisions PASS records
```

### 12.5.12 verifier / metrics 分工

`scripts/t2_metrics.py` 负责人类可读 regression 汇总；`verifier.py` 负责真实生成状态。

分工：

| 能力 | metrics | verifier |
| --- | --- | --- |
| TOC coverage | 必须 | 可选 |
| expected units PASS/FAIL | 必须 | 必须消费 FAIL flags |
| expected source_seq owner | 必须 | 必须消费 FAIL flags |
| critical unowned | 必须 | 必须消费 FAIL flags |
| debug trace 打印 | 必须 | 不需要 |
| `summary.first_bad_stage` | 不负责 | 必须负责 |

状态规则：

```text
expected source_seq mismatch:
  - status = FAIL
  - first_bad_stage = T2

critical unowned but not in expected contract:
  - status = UNKNOWN
  - first_bad_stage = T2 unless manually allowed

weak block / ambiguous title:
  - status = UNKNOWN
  - must include open_question
```

### 12.5.13 新增字段前的检查清单

实现本计划时，每新增一个字段，必须回答：

```text
1. Producer 是哪个函数？
2. Consumer 是哪个函数、脚本、测试或 artifact？
3. 如果字段缺失，下游怎么 fail？
4. 如果字段冲突，谁有最终裁决权？
5. 字段是 debug-only，还是会影响 unit_map/verifier？
6. 是否需要进入 expected contract？
7. 是否违反 T1 fact-only 边界？
```

没有 consumer 的字段不得进入正式 artifact；确实只为观测服务的字段必须放在 `debug` 下，并标明不会影响产品决策。

---

## 13. 实施顺序

### Phase 0：regression / metrics 先行

新增：

```text
scripts/t2_metrics.py --unit-ranges
tests/fixtures/t2_expected_units/*.yaml
expected source_seq ownership checker
critical unowned range checker
```

本阶段可以先让测试失败，用来锁定当前残余。

### Phase 1：canonical boundary hint + instruction soft veto

修改：

```text
canonical_title() 可在 boundary 阶段复用。
_unit_for_boundary_text() 使用 canonical_label_hint。
_boundary_vetoes() 对 title_with_format_annotation 不硬 veto。
```

目标：

```text
湖南 abstract_cn
南农 appendix
南农 acknowledgement
```

### Phase 2：taxonomy 扩展 + list block 类型拆分

修改：

```text
UNIT_DEFINITIONS / alias registry
figure_list / table_list
academic_achievements
声明类 taxonomy
list-like block type resolution
```

目标：

```text
北大 toc / figure_list / table_list 区分
南农 academic_achievements 命名稳定
声明类不再 generic custom
```

### Phase 3：range ownership audit 接入门禁

接入：

```text
unit_range_audit
critical_unowned gate
expected source_seq gate
```

目标：

```text
三校 critical source_seq 无静默丢失。
```

### Phase 4：front/body/back state machine

修改：

```text
body_main start / end inference
body internal Heading 1 absorb rule
back_matter anchor rule
```

目标：

```text
北大 body_main 从 seq 50 附近开始。
正文 Heading 1 不再顶层过切。
```

### Phase 5：duplicate core contextual rule

修改：

```text
_label_boundaries() duplicate core handling
context-aware relabeling
post-body declarations
```

目标：

```text
北大后置 references / declaration 正确。
```

### Phase 6：收口与文档同步

更新：

```text
Issue 02 fix verification
Plan 02 status
regression 输出路径
remaining known limitations
下一轮 AI / visual page policy 是否启动
```

---

## 14. 测试计划

### 14.1 单元测试

新增或扩展：

```text
test_canonical_label_hint_handles_placeholders_and_format_annotations
test_instruction_like_does_not_veto_core_title_with_format_annotation
test_instruction_like_still_vetoes_pure_instruction
test_figure_list_and_table_list_not_mapped_to_toc
test_list_block_segmenter_distinguishes_toc_figure_list_table_list
test_academic_achievements_taxonomy
test_declaration_taxonomy
test_duplicate_core_references_after_body_is_allowed
test_duplicate_core_references_inside_body_is_not_top_level
test_body_state_machine_absorbs_heading1_inside_body_main
test_unit_range_audit_reports_critical_unowned_ranges
test_expected_source_seq_contract_checker
```

### 14.2 三校 regression

必须覆盖：

```text
湖南：
  - toc 20/20 leak=0
  - toc 不包含 seq 50-64
  - abstract_cn 存在
  - seq 57 属于 abstract_cn 或明确摘要复合单元
  - critical_unowned 不包含 seq 50-64 中的标题/摘要关键段

南农：
  - toc 25/25 leak=0
  - appendix 存在，覆盖 seq 109
  - academic_achievements 存在，覆盖 seq 111
  - acknowledgement 存在，覆盖 seq 113
  - references 不覆盖 appendix
  - academic_achievements 不覆盖 acknowledgement

北大：
  - toc 17/17 leak=0
  - figure_list 存在，覆盖 seq 31
  - table_list 存在，覆盖 seq 46
  - body_main start_source_seq <= 50
  - seq 50 / 92 / 221 / 302 属于 body_main
  - references 存在，seq 306 不属于 custom:template:参考文献:*
  - 声明类单元不再是普通 custom，或至少进入 declaration taxonomy / expected unit
```

### 14.3 CI 口径

本轮 CI 不调用 live AI。

建议 CI gate：

```text
uv run pytest tests/unit/test_t2_unit_map.py -q
uv run pytest tests/unit/test_t2_unit_range_contracts.py -q
uv run python scripts/t2_metrics.py
uv run python scripts/t2_metrics.py --unit-ranges
```

真实模板生成如果当前 CI 成本过高，可以作为 nightly / manual regression，但 Plan 02 合并前必须至少提供一次三校真实输出路径和结果摘要。

---

## 15. 输出契约影响

### 15.1 unit_map

新增或强化字段：

```json
{
  "unit_id": "abstract_cn",
  "label_status": "core_matched",
  "raw_title": "□□摘□要（小四黑体）：...",
  "normalized_title": "摘要",
  "source_seq_range": {
    "start": 57,
    "end": 64
  },
  "evidence": [
    "canonical_label_hint",
    "title_with_format_annotation"
  ]
}
```

### 15.2 debug

新增：

```json
{
  "debug": {
    "unit_range_audit": {},
    "expected_unit_results": {},
    "state_machine_trace": {},
    "duplicate_core_decisions": []
  }
}
```

### 15.3 open_questions

新增 reason：

```text
critical_unowned_range
duplicate_core_ambiguous
body_state_transition_ambiguous
title_with_format_annotation_ambiguous
expected_unit_missing
expected_source_seq_mismatch
```

### 15.4 对 T3 / T4 的影响

本轮不要求 T3 / T4 立即解析新增单元内部结构。

但 T2 输出必须让下游可以安全处理：

```text
canonical_label_id != null:
  下游可以按 known unit policy 处理。

label_status = custom_detected:
  下游走 generic fill/remove policy。

body_main 内部 Heading 1:
  T2 不拆顶层 unit；T3 后续负责内部章节。

figure_list / table_list:
  下游可先按 list-like unit 处理，不必与 toc 混用。
```

---

## 16. 验收门禁

### 16.1 全局门禁

```text
1. T2 不读取旧 T1 semantic fields。
2. TOC coverage 三校仍 PASS。
3. 非 list block 单元不包含 toc_entry_like。
4. critical_unowned_ranges = 0，或每条都有 open_question 且不影响 expected source_seq。
5. expected source_seq contract PASS。
6. unit 数不暴涨。
7. 后置单元不被前一单元吞并。
8. custom_unit 数量下降或至少语义可解释。
```

### 16.2 学校门禁

| 学校 | 必须通过 |
| --- | --- |
| 湖南 | `toc` 收口；`abstract_cn` 出现；seq 57 不属于 toc / integrity_statement / unowned |
| 南农 | `appendix`、`academic_achievements`、`acknowledgement` 独立；references 不吞 appendix |
| 北大 | `figure_list` / `table_list` 独立；`body_main` 从 seq 50 附近开始；正文 Heading 1 不过切；后置 references 不 custom |

### 16.3 回归门禁

不能回退：

```text
1. 湖南 TOC 20/20。
2. 南农 TOC 25/25。
3. 北大 TOC 17/17。
4. text_properties alone candidate-only。
5. table cell veto。
6. custom_unit fallback 保留 raw_title / normalized_title。
```

---

## 17. 风险与缓解

### 17.1 高风险：taxonomy 膨胀

风险：

```text
把所有学校标题都塞进 global core，导致 core set 失控。
```

缓解：

```text
分层：global_core / global_extended / school_expected / template_optional。
```

### 17.2 高风险：body state machine 误吞后置单元

风险：

```text
进入 body_main 后，把真正 references / appendix / acknowledgement 也吞进正文。
```

缓解：

```text
back_matter anchor 优先级高于 body internal heading。
后置标签 exact / canonical match 时可结束 body_main。
三校 expected source_seq gate 锁住。
```

### 17.3 中风险：instruction soft veto 导致说明文字误切

风险：

```text
纯格式说明被误认为标题。
```

缓解：

```text
必须有 canonical_label_hint 命中 core/extended/school_expected 才放行。
无 hint 的 instruction_like 仍 hard veto 或 candidate-only。
```

### 17.4 中风险：duplicate core 放宽后产生重复标准单元

风险：

```text
多个 references / appendix 被误切。
```

缓解：

```text
结合 front/body/back 状态、locked block、位置、source_seq contract。
无法解释的 duplicate 进入 open_question，不强行 core。
```

### 17.5 低风险：新增 metrics 与真实模板运行成本

风险：

```text
三校真实模板 regression 较重。
```

缓解：

```text
unit tests + fixture contract 进 CI。
真实模板 full run 可作为 nightly/manual gate，但每次 Plan 状态更新必须附输出路径。
```

---

## 18. 需要讨论并拍板的问题

1. **湖南 seq 50-64 如何建模？**
   - 只要求 abstract_cn 覆盖 seq 57？
   - 还是引入 `body_title_block` / `title_page_fragment` 作为前置复合单元？

2. **`figure_list` / `table_list` 属于 global_core 还是 global_extended？**
   - 建议：global_extended。
   - 在北大 regression 中作为 required。

3. **`academic_achievements` 属于 global_extended 还是 school_expected？**
   - 建议：school_expected，后续多校出现后再 promote。

4. **声明类 taxonomy 要拆多细？**
   - 最小可行：`originality_statement`、`authorization_statement`、`originality_authorization_statement`。
   - 是否保留 `integrity_statement` 作为本科/诚信声明总类？

5. **body_main 起点如何判定？**
   - explicit `正文` 优先。
   - 无 explicit 正文时，是否允许“front matter 后第一个 top-level unknown heading”作为 body_main 起点？
   - 建议允许，但要有 TOC / style / sequence 证据。

6. **duplicate core 后置 references 如何与正文说明区分？**
   - 建议依赖 body state + position + exact canonical title。

7. **critical unowned 是否直接 fail？**
   - 建议：三校 expected source_seq 相关的 critical unowned 直接 fail；其他 critical unowned 可以 UNKNOWN + open_question。

8. **Plan 02 是否允许在 AI 未接入时 merge？**
   - 建议：允许。只要 deterministic 三校结构门禁通过，AI 不应阻塞本轮 P0 修复。

---

## 19. 建议的最终落地判断

本轮应按如下顺序推进：

```text
1. 先加 expected-vs-actual / unit-ranges 门禁。
2. 修 canonical boundary hint + instruction soft veto。
3. 扩 taxonomy 并拆 list block 类型。
4. 接入 range ownership audit。
5. 实现 front/body/back state machine。
6. 改 duplicate core contextual rule。
7. 三校真实模板跑通后，再回到 AI visual / page_policy 方案。
```

一句话：

> Plan 02 的目标是把上一轮 Phase 2 deterministic 主干真正收口；AI 仍然是方向，但不能替代当前三校真实 unit_map 的确定性修复。
