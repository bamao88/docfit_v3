---
issue_scope: template-parse-t1-fact-coverage
status: PROPOSED
severity:
  - P0
  - P1
created: 2026-06-25
evidence_outputs:
  - test_outputs/debug/template_generation/t1_document_facts_20260625_current/hunannongye
  - test_outputs/debug/template_generation/t1_document_facts_20260625_current/nannong-undergraduate
  - test_outputs/debug/template_generation/t1_document_facts_20260625_current/pku-graduate
---

# T1 阶段事实覆盖缺口 issue

Last updated: 2026-06-25

一句话结论：上一轮 T1 已经修复了 run 降噪、run 级空白保留、`is_toc_entry` / `is_spacing_line` 原子信号，但系统性审计后确认 T1 仍有更底层的事实覆盖缺口：段落坐标混用、表格/页眉页脚没有 run trace、TOC 等嵌套 run 漏采、可见对象只停留在 data 层，以及 verifier 误报 T1 `PASS`。

这份文档不是新的实现计划，而是后续讨论用的 issue 台账。先把问题、证据和验收标准写清楚，再决定实现切口。

## 1. 当前证据

证据来自当前三校调试输出：

```text
test_outputs/debug/template_generation/t1_document_facts_20260625_current/hunannongye/01_document_facts.json
test_outputs/debug/template_generation/t1_document_facts_20260625_current/nannong-undergraduate/01_document_facts.json
test_outputs/debug/template_generation/t1_document_facts_20260625_current/pku-graduate/01_document_facts.json
```

### 1.1 覆盖缺口总表

| 学校 | body_flow | 段落项 | 表格单元格无 raw trace | 页眉页脚无 raw trace | `source_ref` 指向 XML 文本不匹配 | raw 前缀与 `source_ref` 不匹配 | TOC 条目无 raw trace | XML 可见段落存在嵌套 run | data 层可见对象 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 湖南农大 | 320 | 145 | 175/175 | 0/0 | 41/145 | 41 | 0 | 0 | 无 |
| 南农本科 | 124 | 114 | 1/1 | 9/9 | 111/114 | 90 | 24 | 26，其中 24 个 direct run=0 | fields 3、text_boxes 1、images 2 |
| 北大研究生 | 366 | 202 | 154/154 | 10/10 | 201/202 | 184 | 17 | 55，其中 54 个 direct run=0 | fields 139、content_controls 1、text_boxes 2、footnotes 1、images 15 |

解释：
- `source_ref` 指向 XML 文本不匹配：`body_flow[].source_ref` 里的 `word/document.xml:p[n]` 去源 DOCX OOXML 找到的段落文本，和 `body_flow[].text` 不是同一段。
- raw 前缀与 `source_ref` 不匹配：例如 `source_ref=word/document.xml:p[3]`，但 `raw_run_ids` 是 `p_0024.r_001` 这一类。
- TOC 条目无 raw trace：`is_toc_entry=true` 的目录条目有文本，但 `raw_run_ids=[]`、`logical_run_ids=[]`。
- XML 可见段落存在嵌套 run：可见文本藏在 `w:hyperlink`、field 等容器下，直接 `paragraph.findall(w:r)` 取不到。

### 1.2 具体例子：南农标题段落坐标错位

当前 `body_flow`：

```json
{
  "source_seq": 2,
  "source_ref": "word/document.xml:p[3]",
  "paragraph_id": "p_0003",
  "text": "南京农业大学本科生毕业论文（设计）原创性声明",
  "raw_run_ids": [
    "p_0024.r_001",
    "p_0024.r_002",
    "p_0024.r_003",
    "p_0024.r_004",
    "p_0024.r_005",
    "p_0024.r_006",
    "p_0024.r_007",
    "p_0024.r_008"
  ],
  "logical_run_ids": ["p_0024.lr_001"]
}
```

问题点：
- `source_ref` 和 `paragraph_id` 说这是 `p[3]` / `p_0003`。
- raw run trace 说真实段落是 `p_0024`。
- 源 DOCX 的 OOXML `word/document.xml:p[3]` 实际文本是 `本科生毕业论文（设计）`，不是这条声明标题。

这不是展示层问题。后续 T2/T3/T6 如果按 `source_ref` 定位，会跳到错误 Word 节点；如果按 raw id 定位，又和 body_flow 的段落 id 对不上。

### 1.3 具体例子：南农目录条目没有 raw trace

当前 `body_flow`：

```json
{
  "source_seq": 10,
  "source_ref": "word/document.xml:p[28]",
  "paragraph_id": "p_0028",
  "text": "摘  要\tⅠ",
  "style": "toc 1",
  "raw_run_ids": [],
  "logical_run_ids": [],
  "structural_signals": {
    "is_toc_entry": true,
    "is_spacing_line": false
  }
}
```

源 DOCX 里这条 TOC 条目的真实 XML 段落是 `word/document.xml:p[49]`，可见文本是 `摘  要\tⅠ`。它有嵌套 run，但没有直接子 `w:r`：

```text
word/document.xml:p[49] text='摘  要\tⅠ' direct_runs=0 nested_runs=3
```

所以这类问题有两个根因叠加：
- `source_ref` 仍然是 python-docx 顶层可见段落序号，不是 OOXML 段落序号。
- run 抽取只看直接子 `w:r`，漏掉 field / hyperlink / TOC 结构里的嵌套 run。

### 1.4 具体例子：表格单元格是可见正文，但没有 run trace

南农 `source_seq=1` 是封面表格单元格：

```json
{
  "flow_item_type": "table_cell",
  "kind": "table_cell",
  "source_ref": "word/document.xml:tbl[1]/tr[1]/tc[1]",
  "text": "本科生毕业论文（设计）\n题    目:\n姓    名:\n学    号:\n学    院:\n专    业:\n指导教师:                 职称\n20   年   月   日",
  "raw_run_ids": [],
  "logical_run_ids": []
}
```

三校统计里，表格单元格没有任何 raw trace：
- 湖南农大：175/175
- 南农本科：1/1
- 北大研究生：154/154

封面、任务书、评审表、成绩表等学校模板核心内容大量在表格中。T1 如果只保留单元格聚合文本，不保留单元格内段落和 run trace，T6 施工很难做到可解释、可回放。

## 2. 根因定位

### 2.1 段落坐标混用

相关代码：
- `src/docfit/template_gap/inspector.py`：`_paragraphs()` 枚举 `doc.paragraphs`，但 `source_ref` 写成 `word/document.xml:p[{index}]`。
- `src/docfit/template_gap/inspector.py`：同一函数里又取 `xml_index = _xml_paragraph_indices(doc).get(paragraph._p, index)`。
- `src/docfit/template_generation/source_tree.py`：`_runs_from_inspection()` 使用 `paragraph.get("xml_index")` 生成 raw run id。
- `src/docfit/template_generation/source_tree.py`：`_stable_ids_for_entry()` 又从 `source_ref` 解析 `paragraph_id`。

结果：同一条段落事实里同时存在两套坐标。

```text
body_flow.source_ref / paragraph_id  -> python-docx visible index
runs.raw_run_id / logical_run_id     -> OOXML xml_index
```

这会让 T1 看似有 trace，实际 join 不稳定。

### 2.2 run 索引只覆盖顶层 `data.paragraphs`

相关代码：
- `src/docfit/template_generation/source_tree.py`：`_runs_from_inspection()` 只遍历 `tree["data"]["paragraphs"]`。

当前 `data.paragraphs` 来自 python-docx 的 `doc.paragraphs` 顶层段落，不覆盖：
- 表格单元格内段落
- 页眉页脚段落
- 文本框段落
- 脚注段落
- 部分 content control 内段落

所以表格和页眉页脚在 body_flow 中有可见文本，但没有 raw/logical run trace。

### 2.3 run 抽取只看直接子 `w:r`

相关代码：
- `src/docfit/template_gap/inspector.py`：`_paragraph_style_details_by_index()` 里使用 `paragraph.findall(f"{W_NS}r")`。

这会漏掉嵌套在以下容器里的可见 run：
- TOC / field 结构
- hyperlink
- smart tag
- content control
- 其他 Word 包装节点

南农有 26 个可见 XML 段落存在 nested run 多于 direct run，其中 24 个 direct run=0。北大有 55 个，其中 54 个 direct run=0。这正是 TOC、图目录、表目录条目没有 raw trace 的主要原因。

### 2.4 页眉页脚只聚合 part 文本，没有 paragraph/run 明细

当前 facts 里 `data.headers_footers` 有页眉页脚文本，但 body_flow 中的页眉页脚项没有 raw/logical run：
- 南农本科：9/9
- 北大研究生：10/10

页码字段、页眉标题、学校模板页脚常常都在这里。T1 不追踪这些 run，T4 页码和 T6 构建就只能靠不完整证据。

### 2.5 verifier 没有覆盖率检查，导致 T1 false PASS

相关代码：
- `src/docfit/template_generation/verifier.py`：`_verify_t1_document_facts()` 当前只检查：
  - artifact type
  - body_flow / runs 重复 id
  - run 必填字段
  - `unknown_objects`

它没有检查：
- 可见 body_flow 项是否有 raw/logical trace
- `source_ref` 是否真的指向该段文本
- `paragraph_id` 是否和 raw run id 前缀一致
- 表格、页眉页脚、TOC 条目是否有可回放的来源
- data 层可见对象是否进入主事实序列或明确建模为旁路对象

所以当前三校 T1 可以 `PASS`，但事实覆盖已经不足以支撑后续阶段。

## 3. Issue 列表

### T1-ISSUE-001：canonical paragraph id / source_ref 不统一

严重级别：P0

期望行为：
- `body_flow[].source_ref` 必须指向源 DOCX 中真实承载该文本的 OOXML 节点。
- `body_flow[].paragraph_id`、`raw_run_ids[].p_xxxx`、`logical_run_ids[].p_xxxx` 必须在同一坐标系里。
- python-docx 的 visible index 只能作为辅助字段，不得伪装成 `word/document.xml:p[n]`。

验收标准：
- 有 raw trace 的段落项，`source_ref` 段落编号和 raw id 前缀一致。
- 三校 `source_ref` 指向 XML 文本不匹配数降到 0，允许差异只来自可解释的 tab/line break 规范化。
- T1 verifier 新增 `document_facts_paragraph_trace_mismatch`，当前三校旧输出应触发 `UNKNOWN`。

### T1-ISSUE-002：表格单元格缺 run trace

严重级别：P0

期望行为：
- 表格单元格如果进入 body_flow 且 `visible=true`，必须有可回放 trace。
- trace 可以是单元格聚合级 `raw_run_ids`，也可以是 `cell_paragraph_refs` / `cell_run_refs` 子结构，但不能只剩一段聚合文本。

验收标准：
- 三校可见表格单元格无 raw trace 数降到 0，或全部带有明确的子 paragraph/run trace。
- 单元格内多段落顺序可回放。
- T1 verifier 新增 `document_facts_visible_table_cell_trace_missing`。

### T1-ISSUE-003：TOC / field / hyperlink 等嵌套 run 漏采

严重级别：P0

期望行为：
- run 抽取要按 OOXML 文档顺序遍历段落内所有可见 `w:r`，不只看直接子节点。
- `w:tab`、`w:br` 等可见控制字符继续保留。
- TOC 条目的 `is_toc_entry=true` 不能成为丢 trace 的理由。

验收标准：
- 南农 24 个 TOC 条目和北大 17 个 TOC/图表目录条目都有 raw/logical run trace。
- XML `direct_runs=0` 但 `nested_runs>0` 的可见段落不再丢 run。
- 新增真实 DOCX 回归样例，覆盖 field/hyperlink/TOC 嵌套 run。

### T1-ISSUE-004：页眉页脚缺 paragraph/run 明细

严重级别：P1

期望行为：
- 页眉页脚 part 不只是 `text` 聚合项，也要有 paragraph/run 级事实。
- PAGE 字段、页眉标题、页脚说明要能回链到具体 part/source_ref/run。

验收标准：
- 南农 9 个、北大 10 个页眉页脚可见项都有 trace 或明确的 part paragraph 子结构。
- T4 page numbering 能引用 T1 的具体 PAGE field/run evidence。
- T1 verifier 新增 `document_facts_header_footer_trace_missing`。

### T1-ISSUE-005：data 层可见对象没有进入主事实序列或建模关系

严重级别：P1

当前 data 层对象：
- 南农本科：fields 3、text_boxes 1、images 2
- 北大研究生：fields 139、content_controls 1、text_boxes 2、footnotes 1、images 15

期望行为：
- 可见对象要么进入 body_flow，要么有明确 `modeled_as` / `parent_ref` / `source_seq_ref` 关系。
- 不应该出现 data 层知道有可见对象，但 T1 verifier 仍完全放行的状态。

验收标准：
- 每类可见对象有处理策略：主序列项、容器子项、旁路事实，或 `unknown_objects`。
- T1 verifier 能区分“已建模但不进入 body_flow”和“可见但未建模”。

### T1-ISSUE-006：T1 verifier 缺覆盖率门禁

严重级别：P0

期望行为：
- T1 verifier 不只检查 schema 形状，还要检查事实覆盖。
- 当前这类 trace 缺口应让 T1 进入 `UNKNOWN`，不能继续 `PASS`。

建议新增 finding：
- `document_facts_paragraph_trace_mismatch`
- `document_facts_visible_paragraph_trace_missing`
- `document_facts_visible_table_cell_trace_missing`
- `document_facts_header_footer_trace_missing`
- `document_facts_nested_run_trace_missing`
- `document_facts_visible_object_unmodeled`

验收标准：
- 用当前旧输出跑 verifier，应能复现 T1 `UNKNOWN`。
- 修复 T1 后，三校 verifier 才恢复 `PASS`。
- 合同测试覆盖每个 finding 的正反例。

## 4. 建议修复顺序

1. 先统一 canonical paragraph id / source_ref。

   把 OOXML paragraph index 作为 canonical id。python-docx visible index 可以保留为 `python_docx_index` 或 `visible_index`，但不能继续写进 `source_ref=word/document.xml:p[n]`。

2. 改 run extractor。

   从 OOXML part 构建 paragraph/run records，按段落内文档顺序取 nested `w:r`，保留 `w:tab` / `w:br` 等可见控制字符。这个 extractor 应覆盖正文、表格、页眉页脚、文本框、脚注等 part。

3. 重建 body_flow 和 run index 的 join。

   `body_flow` 不再通过 visible index 反查 run，而是直接引用 canonical paragraph/run ids。表格单元格需要决定是“聚合节点 + 子 paragraph refs”，还是“单元格内段落也进入 body_flow”。

4. 给页眉页脚和 data 层对象补建模关系。

   页眉页脚至少要有 part paragraph/run facts。图片、文本框、脚注、content control 要有明确进入主序列或旁路事实的规则。

5. 最后加 verifier 覆盖率门禁。

   先让旧输出红起来，再修到绿。否则 T1 仍会继续 false PASS。

## 5. 需要讨论的设计决策

### D1：表格单元格在 body_flow 中怎么表达？

选项：
- A：保留 `table_cell` 聚合节点，新增 `cell_paragraph_refs` / `cell_run_refs`。
- B：把单元格内每个段落都作为 body_flow 项，`table_cell` 只作为 container。
- C：两者都保留，聚合节点服务 T2，子段落服务 T3/T6。

建议先讨论 C。表格整体语义对 T2 很重要，但 T6 施工需要段落/run 级 trace。

### D2：页眉页脚是否进入 body_flow？

选项：
- A：进入 body_flow，和正文统一排序。
- B：留在 `data.headers_footers`，但必须有 paragraph/run facts 和 source refs。
- C：T1 同时输出 part-local flow，T4/T6 按 part 消费。

建议先讨论 C。页眉页脚不是正文顺序的一部分，但需要强 trace。

### D3：T1 verifier 对图片、文本框、脚注的严格度

选项：
- A：所有可见对象未进入 body_flow 就 `UNKNOWN`。
- B：允许旁路建模，但必须有 `modeled_as` 和引用关系。
- C：只对影响模板生成的对象强制，其他先 review。

建议先讨论 B。它能避免把图片、脚注这类对象硬塞进正文流，同时不再让它们静默丢失。

## 6. 非目标

这些不是本 issue 的直接目标：
- T2 unit 边界识别是否准确。
- T3 把一个段落拆成固定文本、说明文本、填空槽的语义切分。
- T4 页码规则的最终 high confidence 判定。
- 样式级联的 gold 级精确验证。

但这些阶段都会依赖 T1 trace。T1 不先修稳，后续阶段的问题会被错误 source_ref 和缺 trace 放大。

## 7. 验证建议

最小验证：

```bash
uv run pytest tests/unit/test_t1_structural_facts.py -q
uv run pytest tests/contract -q
uv run pytest -q
```

三校输出验证：

```bash
uv run docfit eval template-generate --template inputs/targets/hunannongye/raw/source_template.docx --out test_outputs/debug/template_generation/t1_fact_coverage_fix/hunannongye
uv run docfit eval template-generate --template inputs/targets/nannong-undergraduate/raw/source_template.docx --out test_outputs/debug/template_generation/t1_fact_coverage_fix/nannong-undergraduate
uv run docfit eval template-generate --template inputs/targets/pku-graduate/raw/source_template.docx --out test_outputs/debug/template_generation/t1_fact_coverage_fix/pku-graduate
```

新增审计断言建议：
- `source_ref` 指向 XML 文本不匹配数为 0。
- 有 raw trace 的段落项，raw id 前缀和 `paragraph_id` 一致。
- 可见表格单元格都有 run trace 或子 paragraph/run trace。
- TOC 条目都有 raw/logical run trace。
- 页眉页脚可见项都有 part-local trace。
- data 层可见对象都有建模关系或进入 `unknown_objects`。
