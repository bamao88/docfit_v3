---
status: draft
owner: template-generation
stage: T2
created: 2026-06-25
last_updated: 2026-06-25
version: 1
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/plan.py
  - src/docfit/template_generation/executor.py
  - src/docfit/template_generation/word_ops.py
  - src/docfit/template_generation/runner.py
  - src/docfit/template_generation/source_tree.py
related_docs:
  - docs/plans/template-parse-refactor-t2-open-label-unit-recognition.md
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md
---

# 视觉分页（page_policy）实施计划

## 背景

T2 现在已经能正确识别各单元（目录 / 摘要 / 参考文献 / 自定义单元等），但**没有任何机制控制单元级分页**。生成器走 `source_copy_scaffold` 策略——基本是复制源 docx，所以成品的分页 = 源文档分页。产品需要：

1. **强制另起页**：核心单元各自独立成页（封面 / 诚信声明 / 目录 各自另起页）。
2. **单元不可跨页（keep-together）**：单元不能被切到两页；放不下时整单元下移到下一页。
3. **独占页（own-page）**：独占页单元（如目录）若溢出到第 2 页，第 2 页剩余空间不得被下一单元占用——下一单元必须另起新页。

两个关键事实决定了方案形态：

- **T4 已经具备"强制另起页"的完整通路**——`plan.py:36-60` 读取 `unit.page.page_break` / `section_isolation` 并产出 `insert_page_break_before_unit` / `insert_section_break_before_unit`，由 `executor.py:49-68` + `word_ops.py:59-114` 执行。唯一缺口：**T2 把 `unit.page` 留成空 `{}`**（`structure_candidates.py:203`）。所以确定性这一半主要是接线工作。
- **最难的湖南没有任何机械分页符**——已实测：全文 1 个 `sectPr`（文末），各 unit 起点 `page_break_before=False`。要给它强制分页，只能靠**视觉**推断 → 渲染 + AI。

已确认的决策：**本轮 AI 走 fixture-only**（先把机器建好；CI 用"从真实渲染生成的 fixture"驱动；live Claude 留作后续非门禁 eval job）。**渲染 = LibreOffice（`soffice`，本机已存在于 `/opt/homebrew/bin/soffice`）做 docx→pdf + pymupdf 做 pdf→png/bbox。**

设计依据文档：`docs/plans/template-parse-refactor-t2-open-label-unit-recognition.md` 的 §2.2、§7、§8、§9.4、§10、§14.3。不变量：T1 只产事实；T2 负责 page_policy 推断；T4 负责 OOXML 实现；确定性主干在 AI 关闭时必须仍通过门禁；CI 绝不调 live model。

各阶段顺序保证确定性价值先落地；每个阶段都可独立合并。

---

## Phase 0 — page_policy schema + feature flag + 确定性机械分页通路

对"本身带机械分页符"的模板立即生效，并把后续各阶段要写入的 schema 全部铺好。

**`src/docfit/template_generation/source_tree.py`** — `_text_facts_for_entry`（约 359 行）：把三个 T1 事实从 `style_details.paragraph` 透出：`page_break_before`、`keep_next`、`keep_lines`（是事实而非判断，符合 §4.1）。

**`src/docfit/template_generation/structure_candidates.py`**
- 新增 `_mechanical_page_policy_for_unit(unit, entries_by_seq, break_context) -> dict` → 产出三层模型（§10.1）。Phase 0 只填 `mechanical` + `generation_policy`；`observed = {}`。单元首个 source_seq 的"机械另起页"判定 = 该段落索引在 `break_context["page_break_paragraphs"]` **或** `section_break_paragraphs`，**或**该 entry 的 `text_facts.page_break_before` 为真。（注意 `data.breaks[]` 只含 `w:br`/`sectPr`——必须同时读每段的 `pageBreakBefore`。）`mechanism`/`enforcement_hint` 区分 section 与 page。无分页符 → `requires_new_page="unknown"`、`source="skipped"`。
- 把 `"page": {}`（约 203 行）替换为携带结构化 `page_policy` 的 `page` dict，并同时保留旧的 `page_break`/`section_isolation` 中文字符串键（本阶段让现有 `plan.py` 通路零改动地继续工作），同时预留 `keep_together`/`own_page` 布尔（默认 False）。

**`request.py` / `runner.py` / `cli/main.py`** — 串入 `t2_ai_visual_enabled: bool = False` 开关：`generate_template` 形参 → `build_template_generation_request` 字段 → 传入 `build_template_structure_candidates(..., t2_ai_visual_enabled=...)`（Phase 3 前不使用）。在 `src/docfit/cli/main.py` 加 `--t2-ai-visual / --no-t2-ai-visual` 选项。

**T4 消费契约**（写进设计文档）：T4 **只**读 `page_policy.generation_policy.requires_new_page`（`true|false|unknown`）和 `.enforcement_hint`；`unknown` → 不产出任何分页动作。这是唯一的前向契约。

**验收**：`tests/unit/test_t2_page_policy.py`（合成单元首段 `page_break_before=True` → `mechanical.has_explicit_break`、`requires_new_page=True`、`source="mechanical_fact"`；无分页符单元 → 不强制）。`tests/contract/test_template_generate.py` 加契约测试：对一个带真实 `pageBreakBefore` 的 fixture docx 跑生成，断言 `build_manifest["page_breaks"]` 非空且输出段落的 `page_break_before` 为真。扩展 `scripts/t2_metrics.py` 打印三校 `requires_new_page` 按 source 的计数（湖南 → 全为 `unknown`/`skipped`，证明最难的情况留待 AI）。

---

## Phase 0b — T4 keep-together + own-page（在 Phase 0 后可合并）

在 OOXML 层实现诉求 #2、#3，由 `page_policy` 驱动。

**`src/docfit/template_generation/word_ops.py`** — 新增 helper（仿照现有 `_insert_page_break_before`）：
- `_set_keep_together_unit(doc, paragraph_map, source_refs)` → 对单元除最后一段外的每段设 `keep_with_next=True`，每段设 `keep_together`（keepLines）。
- `_set_table_cant_split(doc, source_ref)` → 给每个表行的 `trPr` 追加 `<w:cantSplit/>`（复用 `_cell_for_ref` 风格的表查找；该原语 `inspector.py:390-447` 今天已能检测）。
- own-page（#3）没有原生 OOXML 属性 → 实现为：本单元首段 page_break_before **加** **下一个单元**首段 page_break_before（复用 `_insert_page_break_before`）。

**`executor.py`**（约 68 行后）：处理 `set_keep_together_unit` / `set_table_no_split_unit`；在返回的 manifest dict 中加 `keep_together` / `table_no_split` 列表（与现有 `page_breaks`/`section_breaks` 并列，约 189-217），供 `manifest.py` 透出。

**`plan.py`**（单元循环约 33-77）：把分页判定改为读 `page.page_policy.generation_policy`（`requires_new_page is True` 时按 `enforcement_hint` 产 page/section break 动作）；保留对旧中文字符串键的 `_page_break_rule_requires_break` 作为并行兜底，二者汇聚到**同一批动作**。新增：`own_page` → 本单元产 `set_keep_together_unit` + 对**下一单元**首段产 `insert_page_break_before_unit`（用 `own_page_next_refs` 集合去重）；`keep_together` → 产 `set_keep_together_unit`（若单元含表再加 `set_table_no_split_unit`）。

**`structure_candidates.py` / `constants.py`** — 用小白名单给确定性种子：`own_page=True` 给 `toc`；`keep_together=True` 给原子核心单元（`integrity_statement`、cover）。AI/reconciler（Phase 4）可在有证据时上调。

**验收**：三个 `word_ops` helper 的单测；契约测试——被标 `toc` 的 docx，输出在 toc 首段和下一单元首段都有 `page_break_before`，且 toc 内部有 `keep_with_next` 链。风险：超过一页长的单元无法真正 keep-together（Word 仍会切）→ 进 `page_policy_review`，文档化为 best-effort。

---

## Phase 1A — 渲染 docx→pdf→png、source_seq→页码绑定（新增 `src/docfit/render/`）

- `engine.py` — `render_docx_to_pdf(docx, out_dir)`，用 `subprocess` 调 `soffice --headless --convert-to pdf`；记录 `render_engine`/`render_version`/`pdf_hash`。若 `soffice` 缺失 → 返回 `RenderResult(status="skipped")`，绝不硬失败（主干在渲染关闭时仍可用）。
- `pdf_to_images.py` — `pdf_to_pngs(pdf, dpi)`，用 **pymupdf (fitz)** → 页数、每页 PNG、以及文本 span + bbox（一个依赖同时为 Phase 1B 铺路）。
- `page_text_index.py` — 每页 `[{source_seq, source_ref, text, in_table, page_order}]`。把渲染出的 span 按归一化文本匹配回 `source_context["by_source_seq"]`（`structure_candidates.py:84`）；空/歧义时在可信邻居间插值 `page_no`（source_seq 与正文顺序单调）；记录 `binding_confidence`。本阶段目标 = **Tier 0**（page_no + 标注 source_seq）。硬规则：没有标注 source_seq → AI 不得使用该 entry（§7.2）。
- `annotate.py` — 用 Pillow 在页面 PNG 副本上叠加 `[NN]` source_seq 标签 → `annotated_page_images`。
- `models.py` — `RenderResult`/`PageImage`/`PageTextIndexEntry` 等 TypedDict。

**依赖**：`pyproject.toml` 新增可选组：`render = ["pymupdf>=1.24", "pillow>=10.4"]`。LibreOffice = 系统依赖（README + CI `apt-get install libreoffice-writer`）。

**接线**：`runner.py` — 当 `t2_ai_visual_enabled` 且 soffice 可用时，渲染**源** docx（我们观察源文档的视觉分页），存 `render_artifacts`。`outputs.py` — 把 PNG 写到 `render/`；在 `t2_input` 加 `render_artifacts` 块（§11.2）；在 `json_keys` 注册 `t2_render_index`。

**验收**：`tests/fixtures/render/` 放一个 2 页 fixture docx → 2 张 PNG、页码绑定正确；稳定性断言针对**抽取出的文本布局**（不是 PNG 哈希——LibreOffice 像素不确定；PNG 哈希记录但不门禁）。`pytest.mark.skipif(shutil.which("soffice") is None)`，让没有 LibreOffice 的 CI 仍通过。风险：LibreOffice≈Word 分页差异——记录 engine/version，T6 视为近似、绝不当 Word 真值。

---

## Phase 1B — page_layout_index（bbox、比例、peer pattern）

`src/docfit/render/page_layout_index.py` — `build_page_layout_index(pages, page_text_index)`：每 source_seq 的 `page_no`、`bbox`、`page_top_ratio`、`page_bottom_ratio`（来自 pymupdf 矩形）；每页 `previous_page_blank_ratio`；`peer_unit_pattern`（同标签/样式的单元是否都在页首）。**降级规则**：bbox 不可靠 → 布局字段置 `None`、`tier=0`、消费方按 `observed.*=unknown` 处理；无 bbox 时视觉 page_policy 上限 `medium`，无 blank_ratio 时 `unknown`（§7.2 硬规则）。注入 `t2_input.contexts[].entries[].layout_facts`（§11.2）。

**验收**：合成页——页首标题 y≈0.1·h 判为页首；上一页内容止于 0.4·h → blank_ratio≈0.6；无矩形 entry → 布局 None + 置信度封顶。

---

## Phase 3 — AI 视觉通道（fixture 驱动；live 客户端延后）— 新增 `src/docfit/ai_visual/`

- `input_pack.py` — `build_t2_ai_input(...)`（§8.1）：clean+annotated 图片引用、page_text_index、page_layout_index、T1 事实切片、deterministic_candidates（来自 units + t2_input）、known_taxonomy（核心标签 + `constants.py` 的 alias 注册表）。Schema `t2_input.v2`。
- `schema.py` — `T2_AI_VISUAL_RESPONSE_V1` 常量（§8.2）+ 手写 `validate_ai_response` / `validate_candidate`（不引 jsonschema 依赖；匹配项目风格）。
- `prompt.py` — 含 §8.3 硬约束的模板；`PROMPT_VERSION="t2_ai_visual.v1"`。
- `client.py` — `run_ai_visual_pass(ai_input, *, transport)`。**本轮提供 `FixtureTransport`**（按 render_hash 加载已提交 fixture）；`LiveTransport` 为抛 `NotImplementedError` 的桩 + TODO。本轮不引 `anthropic` 依赖。

**Fixtures**（`tests/fixtures/ai_visual/`，从真实湖南渲染生成以保证 source_seq 可绑定）：`t2_ai_response.valid.json` / `.invalid.json` / `.partial.json` / `.conflict.json`。

**接线**：`runner.py` — flag 开 + 有渲染 → 打包 ai_input、经 FixtureTransport 运行、写 `t2_ai_visual_response.json`；在 `outputs.py` `json_keys` 注册。

**验收**（CI，仅 fixture）：`tests/unit/test_t2_ai_response.py` 按 §17.2——requires_source_seq、rejects_unknown_source_seq、rejects_hallucinated_title、schema valid/invalid/partial、`ai_off_does_not_require_response`。风险：幻觉 → 每个 candidate 的 source_seq 都对 `page_text_index` 校验；不可绑定 → 进 open_questions，绝不成 unit。

---

## Phase 4 — T2 reconciler — 新增 `src/docfit/template_generation/reconciler.py`

`reconcile_t2(deterministic_units, deterministic_blocks, ai_response, t1_facts, layout_index)` → 更新后的 units + `t2_reconciler_trace`（§11.4）。实现 §9.1 固定优先级表（1 locked block → 7 abstain）和 page_policy 合并（§9.4 case 8-10）：机械分页 → high/`mechanical_fact`；AI 视觉（title_at_page_top + previous_page_has_remaining_space + peer pattern）且 source_seq 可绑定 → true/`ai_visual_inference`；证据弱/无 peer → `unknown` + `page_policy_review`。Partial accept + 去重（block 优先于重叠的 unit；同 title_source_seq 按 confidence 去重）；全程写 trace。

**接线**：在 `structure_candidates.py`/`runner.py` 中，**仅当** flag 开且有 ai_response 时运行 reconciler——在确定性构建**之后**、最终 units **之前**。flag 关 → 确定性 units 原样透传（保证 AI 关闭时三校门禁不变）。写 `t2_reconciler_trace.json`；在 `outputs.py` 注册。

**验收**：`tests/unit/test_t2_reconciler.py`（§17.2/§17.3）——accepts_ai_toc_block_when_det_misses、ai_cannot_override_locked_toc_block、records_conflicts、partial_accepts、dedups_overlapping、page_policy_mechanical_high、page_policy_ai_visual_without_mechanical、page_policy_natural_flow_is_unknown。三校行为：**湖南**（无机械分页符）→ AI 开 + fixture 把封面/诚信/目录升为 `true`/`ai_visual_inference`，目录 `own_page=true`；**南农/北大**（有分页符）→ 确定性机械路径在 Phase 0 已给 `true`/`mechanical_fact`，AI 只补证据（绝不推翻，§9.1 优先级 3）。

---

## Phase 5 — 指标门禁与回归

- 扩展 `scripts/t2_metrics.py`：page_policy 列（`requires_new_page` × source）、每单元 keep-together/own-page、AI accepted/rejected 计数；加 `--ai-fixture <dir>` 模式以在不调 live 的情况下跑通 reconciler。
- `tests/regression/`：AI 关闭对三校跑生成——现有 TOC 门禁（湖南 20/20、南农 25/25、北大 17）仍成立，且没有单元从非机械来源获得强制分页（证明没伪造分页符，§16.2）。
- e2e：湖南开 AI fixture 跑生成 → 渲染输出（Phase 1A）→ 断言封面/诚信/目录各自起页、目录之后的单元另起新页。

---

## 复用的现成原语（勿重造）
- T4 分页通路：`plan.py:36-60`、`executor.py:49-68`、`word_ops.py:_insert_page_break_before`(59)、`_insert_section_break_before`(75)、`_next_page_section_properties`(106)。
- source ref / 解析：`refs.py`（`_paragraph_for_ref`、`_cell_for_ref`）。
- 分页事实：`inspector.py`（`pageBreakBefore`/`keepNext`/`keepLines`/`cantSplit` 已检测，约 270-661、1389）、`data.breaks[]`、`structure_candidates._boundary_context`（约 257）。
- 产物 I/O：`outputs.py`（`json_keys`、debug snapshot）、`runner.py` artifacts dict。
- 指标 harness：`scripts/t2_metrics.py`。

## 已锁定的关键决策
- **渲染**：LibreOffice（`soffice`）+ pymupdf（pdf→png + bbox 一个 wheel 搞定）+ Pillow（标注）。
- **AI**：本轮 fixture-only；`FixtureTransport` 上线，`LiveTransport` 留桩；`anthropic` SDK + 非门禁 eval job 延后。
- **own-page（#3）**：本单元 page_break_before + 下一单元 page_break_before（OOXML 无原生"不填充"属性）。

## 主要风险
1. LibreOffice ≈ Word 分页差异 → 视觉观察是近似，隔离在 `src/docfit/render`（引擎可换），T6 记录差异，绝不写成 T1 事实。
2. 无可靠 bbox → Tier-0 兜底强制 `observed.*=unknown`，page_policy 封顶 `medium`。
3. AI 幻觉 → source_seq 对 `page_text_index` 校验；不可绑定 → 仅进 open_questions。
4. 超长单元无法 keep-together（Word 仍切）→ best-effort + `page_policy_review`。
