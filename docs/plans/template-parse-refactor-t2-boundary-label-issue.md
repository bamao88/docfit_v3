---
status: resolved
resolved_at: 2026-06-25
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
  - docs/plans/template-parse-refactor-t2-visual-pagination.md
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/artifacts.py
---

# T2 边界检测与标签器调优 issue

> **【状态：已解决 — 2026-06-25】历史 issue 文档，勿据此定位新问题。**
>
> 本文档描述的 ISSUE-001~004（TOC 未作 block 专门切分、`text_properties` 单独过阈值导致过切、标签闭集过窄、duplicate 一刀切降 `other`）**已在 Phase 2 确定性主干实施中全部修复**（TOC block segmenter + 加锁、`text_properties` candidate-only、表格单元格 veto、Heading-2+ 不切顶层、canonical_title + alias + `custom_unit` 标签模型）。三校门禁：湖南/南农/北大 TOC 20/20·25/25·17/17，`other`=0，leak=0。实施后状态与残余见 **§4**。
>
> **后续做优化时，请勿再依据本文档 §1~§3 的旧现象/旧数据定位**——它们描述的是修复前的状态。当前真相来源：
> - **残余问题与现状（含湖南 abstract_cn 丢失 R1、北大正文过切 R2、page_policy 未实现）**：本文档 §4。
> - **后续视觉分页 / page_policy 计划**：`docs/plans/template-parse-refactor-t2-visual-pagination.md`。
> - **T2 设计总纲**：`docs/plans/template-parse-refactor-t2-open-label-unit-recognition.md`。

Last updated: 2026-06-25

一句话结论：当前 T2 优化版把旧逻辑的"关键词撞目录"问题显性化了，也补出了 `t2_input.json` 和 typed `open_questions`；但它还没有达到可交付效果。主要问题是 **TOC block 没有作为专门单元切分**、**仅文字属性即可过阈值导致过切**、**标签器闭集过窄导致大量 `other`**。架构边界（T1 只产原子事实、T2 禁止消费 T1 语义字段）见 §0。

本文件只记录 issue 现象、数据与根因，不含修复方案。

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

准确率优化的前提也因此改变：不是"让 T1 更早标好 TOC"，而是让 T1 给足可观测事实，让 T2 有更强的派生规则和 block-level segmenter。

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

- 湖南退化方向是**欠切（漏边界）**，不是关键词抢条目：基线至少切出 `toc | 目录` 单元（盖住目录标题 seq 22-26），当前**连 toc 单元都消失**。目录标题（seq 24 `目□□录`）与全部 20 个 TOC 条目（seq 27-49）被并入前一个 `integrity_statement`（诚信声明，seq 18-59）。实测 seq 22-59 整段没有任何 boundary candidate，下一个边界直接跳到 seq 60。20 个 TOC 条目当前全部落在 `integrity_statement`，仍是 0/20，但失败机制与基线不同。
- 北大过切严重：`9 units -> 76 units`，其中 `68 other`。
- 三校 overall 仍是 `UNKNOWN`，`first_bad_stage` 仍是 `T2`。
- findings 上升，说明当前规则更会暴露不确定性，但还没有转化成确定性质量提升。

---

## 2. 问题拆解

### T2-ISSUE-001：TOC 没有作为 block 专门处理

当前 TOC 仍混在通用边界检测流程里：目录标题、目录条目、真实标题都通过同一套 boundary score 竞争。

这导致两种不同的失败机制：

- 基线（关键词抢条目，over-claim）：目录标题被切成 `toc` 单元但**只盖到标题、停在条目前**（湖南 seq 22-26）；20 个条目被关键词逐段切走——`摘要/关键词→abstract_cn`、`前言/一级标题→body_main`、`参考文献→references`。
- 当前版（漏边界 / 区块被吞，under-claim）：keyword-only 边界被新规则压掉（改成仅 exact-title fallback），而目录条目是 Normal 样式、不触发 `text_properties`（centered AND large/bold），导致目录区**整段无边界候选**。
  - 南农：修好了，25/25 进入 `toc`。
  - 湖南：toc 单元彻底消失，目录标题 + 20 条目被并入前一个 `integrity_statement`（seq 18-59）。这是欠切，与基线"被关键词抢走"是相反方向的失败。
  - 北大：仍有 3 个 TOC 条目进入 `other`。

根因：

- 没有显式的 `toc block segmenter`：目录块既可能被相邻关键词单元切碎（基线），也可能因无信号被前一单元整体吞掉（当前湖南）。
- `toc_entry_like` 只是边界 veto 或普通证据，而不是先验 block 归属规则。
- `toc_title_like` 识别过窄，对 `目□□录（二号黑体，居中）`、空格分隔、格式注释等不够稳——湖南 seq 24 的目录标题当前完全没有产生边界。

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

- 湖南有农理工科/文科类两套模板块，重复出现的闭集标题被逐个降级成 `other`。
- 目录内条目重复出现时也会触发同一逻辑，加剧碎片化。
- 结果是真实变体块被切成多个零碎 `other`，而不是被识别为同一结构的两套变体。

---

## 3. 非目标

- 不在 T1 恢复或新增 `is_toc_entry` 等语义字段。
- 不在 T2 消费旧 `is_toc_entry` / `structural_signals` 字段。
- 不在本 issue 中实现 AI 合并 `t2_ai_response.json`。
- 不做完整 variant model；本轮最多聚合为 `other + variant_block_detected`。
- 不解决 T3 段内元素切分。
- 不解决 T4 页码/分节 high confidence。

---

## 4. Phase 2 确定性主干实施后状态（2026-06-25 更新）

口径：三校真实模板工作树重跑（`scripts/t2_metrics.py` + 完整 `generate_template`），`t2_ai_visual_enabled=false`。

### 4.1 已解决

| 原 issue | 状态 | 证据 |
| --- | --- | --- |
| ISSUE-001 TOC 未作 block | 已修 | TOC block segmenter（加锁）上线；湖南 20/20、南农 25/25、北大 17/17 条目归入 `toc`；非 `toc` 单元 `toc_entry_like` 泄漏 = 0 |
| ISSUE-002 `text_properties` 单独过切 | 已修 | `text_properties` 降为 candidate-only；表格单元格 veto；裸 Heading-2+ 不再切顶层 → 北大 80→21 unit |
| ISSUE-003 标签闭集过窄 | 已修 | canonical_title + alias 注册表 + `custom_unit` 兜底 → 三校 `other`=0；未知高置信一级单元落 `custom_detected` 并进 `taxonomy_review_queue` |
| ISSUE-004 duplicate 一刀切降 other | 已修 | 重复核心单元/未知强边界 → `custom_unit`（保留 raw_title/display_name），不再碎成 other |

### 4.2 残余结构问题

- **R1 湖南 `abstract_cn` 丢失（P1）**：中文摘要标题 `□□摘□要（小四黑体）：`（seq 57）含格式注释 `（小四黑体）`，被 `_looks_like_instruction` 判成说明文字而进入 boundary veto；keyword-exact 兜底因此被跳过，未切出 `abstract_cn`。该区被前序 `toc` 区域顺延吞并（`toc` = seq 24-64，越过最后一条目 seq 49，盖住中文标题/摘要/英文标题 50-64）。环节：`structure_candidates._looks_like_instruction` / `_boundary_vetoes` + TOC 区域未在最后一条目处收口。
- **R2 北大正文过切（P2，计划归 T3/AI）**：正文 Heading-1 章节（研究背景 / 插图公式与表格 / 结论与讨论 等）各自升为 `custom_unit`，`body_main` 仅 seq 214-218。无 TOC 交叉引用时，确定性无法区分"正文章节"与"顶层单元"。计划 §19 归 Phase 3 AI / T3 章节层级，本轮不处理。
- **R3 噪声 custom（P3）**：`二〇 年 月`、`TITLE`/`English Title…` 等短碎行被升为 `custom_unit`。需更严的 custom 准入（最小内容量、排除纯日期/占位行）。

### 4.3 page_policy（分页策略）尚未实现

- **现状**：`unit_map.units[].page` 为空 `{}`；无 unit 级 `page_policy`，无 `requires_new_page`，无 keep-together / 独占页约束。
- T1 的 `mechanical_break` 事实当前仅被 `_preceded_by_break` 当作**边界证据**消费，未产出 `page_policy`，也未传给 T4。
- **实测湖南**：全文仅 1 个 `sectPr`（文末 `body/sectPr`），封面/诚信/目录等各 unit 起点 `page_break_before=False` —— 即该模板**无机械分页信号**，纯确定性无法判定"封面、诚信声明各自独立成页"。计划 §2.2 / §19 将此类无机械信号的强制分页归 Render（Phase 1B）+ AI 视觉（Phase 3）。
- **未覆盖的产品诉求**（均属 page_policy 推断 + T4 实现，见计划 §10 / §12.1）：
  1. 核心单元强制另起页（封面、目录、诚信声明等）。
  2. 单元不可跨页 / keep-together（一页放不下时整单元下移，不把末元素遗留在上一页）。
  3. 独占页单元（目录满页顺延到次页，但次页剩余空间不接其他单元）。
- **确定性可做的增量（尚未实现）**：当源文档**存在** `page_break_before` / `sectPr` 时，T2 可确定性输出 `page_policy.mechanical.has_explicit_break=true` 与 `generation_policy.requires_new_page=true, source=mechanical_fact`（计划 §9.4 case 8、§14.3）。湖南三校恰好缺机械信号，对其无效，但对带真实分页符的模板有效，并为 T4 消费打基础。
