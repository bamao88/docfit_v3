---
status: draft
owner: template-generation
stage: T2
topic: unit-recognition
issue_id: T2-UNIT-ISSUE-02
issue_sequence: 2
created: 2026-06-25
last_updated: 2026-06-25
version: 1
previous_issue:
  id: T2-UNIT-ISSUE-01
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md
previous_optimization:
  doc: docs/plans/template-parse-refactor-t2-open-label-unit-recognition.md
  summary: Phase 2 deterministic mainline for derived signals, TOC block, boundary/label rewrite, custom_unit fallback
next_plan: TBD
evidence_run:
  code_checkpoint: e861aa5
  command: "uv run python -B -c 'from pathlib import Path; from docfit.convert.orchestrator import run_template_generate_eval; ...'"
  output_root: /private/tmp/docfit_t2_current_run
followup_runs:
  - label: toc_block_range_fix
    command: "uv run pytest tests/unit/test_t2_unit_map.py -q && uv run python scripts/t2_metrics.py && run_template_generate_eval for three real templates"
    output_root: /private/tmp/docfit_t2_after_block_range_fix
    summary: TOC block unit range no longer overflows; residual unowned ranges and taxonomy/body segmentation issues remain
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/verifier.py
  - tests/unit/test_t2_unit_map.py
  - scripts/t2_metrics.py
related_docs:
  - docs/plans/template-parse-refactor-issue-index.md
  - docs/plans/template-parse-refactor-t2-open-label-unit-recognition.md
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md
  - docs/plans/template-parse-refactor-t2-visual-pagination.md
---

# T2 单元识别 Issue 02：Phase 2 优化后残余问题

## 0. 记录目的

本文件记录上一轮 T2 单元识别优化之后，按当前代码真实运行三校模板生成仍然存在的问题。后续讨论 T2 优化时，先以本文件为事实基线，再讨论哪些问题需要解决、如何解决、以及哪些验收门禁必须补上。

重要口径：

1. 本文件不复用旧 issue 的历史结论。
2. 本文件只引用当前代码真实生成结果。
3. 上一轮优化不是只修 TOC：它已经改动了 T2 派生信号、TOC block、边界判定、canonical label、custom_unit fallback、form/variant 标记等整条识别链。
4. 当前残余问题说明：上一轮框架改造有效，但最终 unit_map 仍未达到“真实学校单元准确识别”的可交付口径。

后续阶段优化流程约定：

- 讨论某阶段优化前，先新增或更新对应 `docs/plans/*issue*.md`。
- 文档必须包含：真实运行命令、输出位置、expected vs observed、疑似根因、验收门禁。
- 方案文档不能直接把“计划要解决”当作“已经解决”；必须有生成 artifact 或测试门禁证明。

## 0.1 迭代链与命名

本轮 T2 单元识别文档链：

| 顺序 | 类型 | 文档 | 状态 | 用途 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md` | resolved | 上一轮优化前的边界/标签问题记录 |
| 01 | optimization plan | `docs/plans/template-parse-refactor-t2-open-label-unit-recognition.md` | draft/implemented in part | 上一轮 Phase 2 确定性主干优化方案 |
| 02 | issue | `docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md` | draft | 本文档：上一轮优化后仍存在的真实生成问题 |
| 02 | optimization plan | TBD | pending | 后续针对本文档讨论出的下一轮修复方案 |

命名约定：

```text
template-parse-refactor-{stage}-{topic}-issue-{NN}-{short-name}.md
template-parse-refactor-{stage}-{topic}-plan-{NN}-{short-name}.md
```

同一个 topic 下，issue 和 plan 使用同一轮编号。比如本文件是 `issue-02`，后续若形成修复方案，应优先命名为 `template-parse-refactor-t2-unit-recognition-plan-02-*.md`。

## 1. 当前真实运行口径

运行时间：2026-06-25。

代码 checkpoint：`e861aa5 chore: checkpoint template generation refactor state`。

运行方式：对三校真实模板执行 `run_template_generate_eval(...)`，输出到 `/private/tmp/docfit_t2_current_run/{school}`。

结果摘要：

| 学校 | summary.status | first_bad_stage | unit 数 | T2 finding 数 | 结论 |
| --- | --- | --- | ---: | ---: | --- |
| hunannongye | UNKNOWN | T2 | 10 | 15 | T2 仍有阻断问题 |
| nannong-undergraduate | UNKNOWN | T2 | 10 | 6 | T2 仍有阻断问题 |
| pku-graduate | UNKNOWN | T2 | 21 | 16 | T2 仍有阻断问题 |

对照指标：

- `scripts/t2_metrics.py` 当前可通过三校 TOC 条目覆盖门禁：湖南 20/20、南农 25/25、北大 17/17，leak=0。
- 但该指标只证明 TOC 条目归属，不证明最终 unit 边界、单元标签、后置单元、正文主体范围正确。

## 2. 上一轮已经做过的优化

当前代码中已经存在这些上一轮优化痕迹：

1. T2 派生信号输出：`debug.t2_derived_signals_by_source_seq`。
2. TOC block segmenter：`_segment_toc_blocks()`、`_toc_block_anchor()`、locked indices。
3. 边界判定重写：`text_properties` 单独命中只进入 candidate；table cell veto；裸 Heading-2+ 不切顶层。
4. canonical title + alias：`canonical_title()`、`_CORE_ALIAS_EXACT`。
5. custom_unit fallback：未知强边界进入 `custom:template:*`，不再落 `other`。
6. form/variant 标记：`form_block_detected`、`variant_block_detected`。

所以当前问题不是“上一轮只修了 TOC”，而是这些机制没有覆盖最终生成所需的全部单元语义与 range 收口。

## 3. 当前残余问题

### P0-1 湖南 TOC block 已识别，但 unit range 没按 block end 收口

Status after quick fix: fixed in working tree after consuming `anchor.block_range.end_index` when building unit ranges. Keep this issue item as historical context and as a regression target.

Observed：

- debug `toc_blocks` 显示 TOC block 为 seq 24-49，`entries_count=20`。
- 最终 `unit_map.units[].toc.source_seq_range` 为 seq 24-64。
- seq 50-64 已经是正文题名、中文摘要标签、英文标题前置内容。
- `abstract_cn` 没有单独出现在 unit_map 中。

关键段落：

```text
seq 24 目□□录
seq 27-49 TOC 条目
seq 50 正文基本格式...
seq 57 □□摘□要（小四黑体）：...
seq 65 □□Abstract...
```

疑似根因：

- `_toc_block_anchor()` 记录了 `block_range.end_source_seq`，但 `_infer_units()` 构造 `region_entries` 时仍使用“当前 anchor 到下一个 anchor”的通用切片逻辑。
- 即 block 自己知道结束位置，但最终 unit range 没消费这个 end。
- `□□摘□要...` 未形成 `abstract_cn` anchor，导致下一个 anchor 直到 seq 65。

应补门禁：

- 湖南 `toc` end 必须等于最后一个 TOC entry，而不是吞并正文题名/摘要。
- 湖南必须识别 `abstract_cn`，且 seq 57 属于 `abstract_cn` 或正文题名/摘要复合单元，而不能属于 `toc`。

Fix verification：

- `uv run pytest tests/unit/test_t2_unit_map.py -q` -> 15 passed.
- `uv run python scripts/t2_metrics.py` -> 三校 TOC 门禁仍 PASS。
- 三校真实生成输出：`/private/tmp/docfit_t2_after_block_range_fix`。
- 湖南 `toc` 从 seq 24-64 收敛为 seq 24-49。
- 南农 `toc` 从 seq 9-36 收敛为 seq 9-34。
- 北大 `toc` range 无外溢变化，但仍存在 figure/table list taxonomy 问题。

修复后暴露的新事实：

- 湖南 seq 50-64 目前无人认领，说明 `body_title_block` / `abstract_cn` 仍未被识别。
- 南农 seq 35-36 目前无人认领，且后置 `appendix` / `acknowledgement` 仍被吞并。

### P0-2 湖南中文摘要未切出

Observed：

- seq 57 `□□摘□要（小四黑体）：...` 是中文摘要标签。
- 当前没有 `abstract_cn` unit。

疑似根因：

- `_boundary_decision()` 早期通过 `_unit_for_boundary_text()` / `_unit_for_text()` 生成 unit hint。
- `_unit_for_text()` 使用 `_normalize_text()`，不会去掉 `□`、格式注释、标点。
- `canonical_title()` 能把 `摘□要（三号黑体）` 归一为 `摘要`，但 canonical 只在 label 阶段使用；如果早期没有 boundary/hint，label 阶段没有机会补救。

应补门禁：

- 带占位符和格式注释的 `摘□要` 仍应作为 `abstract_cn` 边界候选或正式边界。
- `instruction_like` 不能 veto 掉短标题主体明确的核心单元标签。

### P0-3 南农后置单元边界被前一单元吞并

Observed：

- `references` 当前覆盖 seq 89-110，其中 seq 109 是 `附 录 附录名称（三号黑体，居中）`。
- `custom:template:相关的学术成果目录:111` 当前覆盖 seq 111-116，其中 seq 113 是 `致 谢（三号黑体，居中）`。
- 最终没有标准 `appendix` unit，也没有 `acknowledgement` unit。

关键段落：

```text
seq 89  参考文献
seq 109 附 录 附录名称（三号黑体，居中）
seq 111 相关的学术成果目录（三号黑体，居中）
seq 113 致 谢（三号黑体，居中）
```

疑似根因：

- `附 录...`、`致 谢...` 同时命中 heading 和 instruction-like 格式注释。
- `_boundary_vetoes()` 对 `instruction_text` 采用硬 veto，导致这些核心标题没有成为边界。
- `academic_achievements` 不在当前核心 taxonomy 中，`相关的学术成果目录` 只能落成 custom。

应补门禁：

- 南农必须识别 `appendix`、`academic_achievements`、`acknowledgement` 的独立边界。
- 带格式注释的 Heading 1 核心标题不能因 instruction-like 被直接 veto。

### P0-4 北大图目录/表目录不可能正确产出

Observed：

- 当前 `toc` 从 seq 31 `图目录` 开始，覆盖 seq 31-49。
- seq 46 是 `表目录`，也被包含在同一个 `toc` 中。
- 没有 `figure_list` / `table_list` 单元。

疑似根因：

- `UNIT_DEFINITIONS` 没有 `figure_list` / `table_list`。
- `_CORE_ALIAS_EXACT` 把 `图目录`、`表目录` 都映射为 `toc`。
- `_TOC_TITLE_NORMALIZED` 也把主目录、图目录、表目录都作为同一种 TOC title 处理。

应补门禁：

- 北大应独立识别 `toc`、`figure_list`、`table_list`。
- 图目录/表目录可以复用 TOC-like block 机制，但最终 unit_id 必须区分。

### P1-1 北大正文主体被过切成多个顶层 custom_unit

Observed：

- seq 50 `研究背景`、seq 92 `插图、公式与表格`、seq 221 `其他注意事项`、seq 302 `结论与讨论` 等 Heading 1 被切成多个 `custom:template:*`。
- `body_main` 反而从 seq 214 `自动编号在新一章没有从1开始的修复` 开始，只覆盖 seq 214-218。

疑似根因：

- 当前规则中 Heading 1 是强 top-level unit boundary。
- 缺少“进入正文主体后，章标题属于 body_main 内部结构”的状态机。
- 缺少利用 TOC / 样式层级 / 前后置单元序列判断正文范围的 reconciler。

应补门禁：

- 北大 `body_main` 应从第一个正文章标题 `研究背景` 开始，并覆盖到真正的后置 `references` 之前。
- 正文章标题不应默认升级为顶层 `custom_unit`。

### P1-2 duplicate core -> custom 规则过粗

Observed：

- 北大 seq 306 `参考文献` 被识别成 `custom:template:参考文献:306`，而不是最终 references。
- 北大末尾 `原创性声明` 被识别成 custom，而不是合适的后置声明单元。

疑似根因：

- `_label_boundaries()` 遇到重复 core label 时统一转 custom。
- 该规则能避免重复 core 误覆盖，但没有结合位置、阶段、后置区、正文内外上下文。

应补门禁：

- 正文说明里的 `参考文献` 小节标题可以留在 body_main 内部。
- 后置区真正的 `参考文献` 标题必须识别为 `references`。
- 后置声明页应有明确 taxonomy，而不是普通 custom。

### P1-3 必需核心单元门禁过弱

Observed：

- `CORE_REQUIRED_UNIT_IDS = {"body_main"}`。
- 因此缺少 `abstract_cn`、`appendix`、`acknowledgement`、`figure_list`、`table_list` 等不会触发 required missing。

疑似根因：

- T2 仍按极小核心必需集运行，避免过早阻塞。
- 三校真实模板的学校级必需单元没有进入 T2 验收。

应补门禁：

- 至少在三校 regression 中定义 expected unit ids 与关键 source_seq 归属。
- required set 需要区分 global core、school expected、template optional。

### P2-1 AI / reconciler 仍未接入当前生成

Observed：

- 当前 `src/ tests/ scripts` 中没有 `t2_ai_visual_enabled`、`ai_visual`、`FixtureTransport`、`reconcile_t2` 等实现。
- 当前只有 `t2_input`、open_questions、debug signals 等前置数据形状。

影响：

- 任何“AI 会兜底 unknown heading / visual block / page policy”的计划目前都不会影响真实生成。
- 所有上面的问题都必须先按 deterministic 当前路径判断，不能假设 AI 已参与。

## 4. 哪些属于上一轮应该解决但未完全解决

初步判断：

| 问题 | 是否属于上一轮应解决范围 | 说明 |
| --- | --- | --- |
| TOC block range 不收口 | 是 | 上一轮引入 TOC block，最终 unit range 应消费 block end，否则 block 只是半成品 |
| 带格式注释核心标题被 instruction veto | 是 | canonical title / core label 已引入，应该避免核心标题被格式注释误伤 |
| 湖南 `abstract_cn` 缺失 | 是 | 计划验收写过必需核心单元齐全，但未落成门禁 |
| 南农 appendix / acknowledgement 被吞 | 是 | 属于核心/学校默认后置单元边界准确性 |
| 北大 figure_list / table_list 缺失 | 部分是 | 计划中提到核心闭集示例未覆盖，但北大标准明确需要，三校门禁应补 |
| 北大正文 Heading 1 过切 | 部分延期 | 上一轮降低了 text_properties 过切，但 Heading 1 内部章节 vs 顶层单元仍需正文状态机/AI/T3 协同 |
| AI/reconciler 未接入 | 否，若按 Phase 2 | 计划将 AI/reconciler 放在后续 Phase；但后续文档不能把它写成当前能力 |

## 5. 后续讨论入口

后续不要直接从 page_policy 开始实现。建议先讨论 T2 residual fix 的范围：

1. 是否先补 deterministic range/label 修复，确保三校最终 unit_map 对齐。
2. 是否扩展 taxonomy：`figure_list`、`table_list`、`academic_achievements`、`copyright_notice`、`authorization_statement`、`originality_authorization_statement` 等。
3. 是否引入正文状态机：front matter -> body_main -> back matter。
4. 是否把 school expected unit ids/source_seq 归属写成 regression 门禁。
5. 是否在 AI/reconciler 上线前禁止文档声称“AI 已可兜底”。

最小下一步建议：

- 新增 `scripts/t2_metrics.py --unit-ranges` 或新脚本，输出 expected vs actual unit ids/ranges。
- 新增三校真实模板 regression：
  - 湖南：`toc` 不得包含 seq 50-64；必须有 `abstract_cn`。
  - 南农：必须有 `appendix`、`academic_achievements`、`acknowledgement`。
  - 北大：必须有 `figure_list`、`table_list`；`body_main` 从 seq 50 附近开始；后置 `references` 不得变 custom。

## 6. TOC block range 快速修复后的当前残余

本节记录 quick fix 后的真实生成结果，作为下一步讨论的当前基线。

运行输出：`/private/tmp/docfit_t2_after_block_range_fix`。

验证：

```text
uv run pytest tests/unit/test_t2_unit_map.py -q
15 passed

uv run python scripts/t2_metrics.py
hunannongye            20/20 leak=0 PASS
nannong-undergraduate  25/25 leak=0 PASS
pku-graduate           17/17 leak=0 PASS
```

当前残余：

| 学校 | 已改善 | 仍存在 |
| --- | --- | --- |
| 湖南 | `toc` 正确收口到 seq 24-49 | seq 50-64 无 unit 认领；`abstract_cn` 仍缺失；正文题名/摘要复合区域未建模 |
| 南农 | `toc` 正确收口到 seq 9-34 | seq 35-36 无 unit 认领；`appendix` 未切出；`academic_achievements` 吞并 `acknowledgement` |
| 北大 | TOC coverage 仍 PASS，无新增外溢 | `figure_list` / `table_list` 缺失；正文 Heading 1 仍过切为 custom；后置 `references` 仍错位为 custom |

下一步优先级建议：

1. 先处理“block 收口后出现的 unowned ranges”：这些是之前被外溢掩盖的真实边界缺口。
2. 补 taxonomy 和 regression：`figure_list`、`table_list`、`academic_achievements`、后置声明类单元。
3. 再处理正文状态机，避免正文章标题被当作顶层 custom unit。
