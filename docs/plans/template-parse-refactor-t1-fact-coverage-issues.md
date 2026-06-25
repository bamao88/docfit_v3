---
issue_scope: template-parse-t1-fact-coverage
status: PROPOSED
severity:
  - P0
  - P1
created: 2026-06-25
last_updated: 2026-06-25
evidence_outputs:
  - test_outputs/debug/template_generation/t1_document_facts_20260625_current/hunannongye
  - test_outputs/debug/template_generation/t1_document_facts_20260625_current/nannong-undergraduate
  - test_outputs/debug/template_generation/t1_document_facts_20260625_current/pku-graduate
related_code:
  - src/docfit/template_gap/inspector.py
  - src/docfit/template_generation/source_tree.py
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/verifier.py
---

# T1 阶段事实覆盖缺口 issue

Last updated: 2026-06-25

一句话结论：上一轮 T1 已经修复了 run 降噪和 run 级空白保留，但系统性审计后确认 T1 仍有两类缺口：一类是**事实覆盖缺口**（段落坐标混用、表格/页眉页脚没有 run trace、TOC 等嵌套 run 漏采、可见对象只停留在 data 层、verifier 误报 T1 `PASS`）；另一类是**职责越权**（`document_facts.body_flow[].structural_signals` 混入 `is_toc_entry` 等语义判断）。本文档既是 issue 台账，也给出可落地的优化方案与分阶段实施计划。

## 0. T1 硬边界

T1 `document_facts` 的职责只有一个：把源 DOCX 读全读对，输出可追溯、可复现的事实。T1 不回答“这段是什么含义”，只回答“Word 里有什么”。

允许 T1 输出：
- 文本事实：可见文本、tab、换行、空格、控制符。
- 位置事实：part name、OOXML source_ref、paragraph/run/table/cell/header/footer id。
- 样式事实：style id/name、字体、字号、加粗、斜体、下划线、颜色、段落对齐、缩进、间距、继承来源。
- 结构事实：表格、单元格、页眉页脚、字段、图片、文本框、脚注、content control、分页/分节。
- trace 事实：raw run、logical run、merged_from、source_refs、container refs。

不允许 T1 输出：
- `is_*` 语义标签，例如 `is_toc_entry`、`is_spacing_line`。
- `looks_like_*` / `likely_*` 判断，例如 `looks_like_instruction_text`、`likely_unit_heading`。
- 阈值判断标签，例如 `large_font`、`short_text`。T1 应输出 `font_size_pt` 和原始文本长度所需事实，由 T2/T3 自己设阈值。
- 下游职责字段，例如 `unit_id`、`policy`、`confidence`、`generated/fill/manual_only`。
- “是不是标题/边界/目录条目/说明文字/空行说明”这类合成判断。

归属规则：
- T2 基于 T1 事实判断单元边界、目录条目、空行说明、标题样式信号、`unit_id` 和 boundary confidence。
- T3 基于 T1/T2 判断固定文本、说明文字、填空槽、人工填写、系统生成字段。
- T4 基于 T1 字段/分节/页眉页脚事实判断页码、分节和页面规则。

开发约束：未来新增 T1 字段时，字段名和含义必须能直接对应到 DOCX 可观测事实；如果字段需要词表、阈值、上下文或业务含义组合才能得出，它不属于 T1。

### 0.1 术语与字段模型（读 issue 前先读）

避免把不同层级的概念混为一谈：

| 概念 | 层级 | 含义 | 在 JSON 里 |
| --- | --- | --- | --- |
| **段落** | Word 物理层 | 一个 `<w:p>` | `body_flow[]` 一条（通常） |
| **容器** | Word 物理层 | `w:hyperlink`、field、`w:sdt` 等包装节点 | 未来 `container_refs[]` |
| **raw run** | Word 物理层 | 一个 `<w:r>`，可能只含 tab/空格 | `runs[].merged_from[]`、`raw_run_ids[]` |
| **logical run** | DocFit 加工层 | 相邻且 `effective_style` 相同的 raw run 合并结果 | `runs[]` 一条、`logical_run_ids[]` |
| **body_flow** | DocFit 索引层 | 按阅读顺序的可见文本块（段落/单元格/页眉脚项） | `document_facts.body_flow[]` |
| **semantic signal** | T2/T3 推断层 | 如 `is_toc_entry` | **不应出现在 T1** |

关系：

```text
body_flow[]（段落卡）
  ├── text / style / source_ref / paragraph_id
  ├── raw_run_ids[] ──────→ runs[] 里的 raw run
  ├── logical_run_ids[] ──→ runs[] 里的 logical run
  └── text_facts{}         → T2/T3 可消费的原子事实（优化后新增）

runs[]（run 详情册）
  └── logical run：text、effective_style、merged_from、source_refs、container_refs
```

当前实现误区：T1 内部并非“一条统一管线”，而是**读字**与**建 run 索引**用了不同深度的扫描，再拼成 `body_flow`。因此会出现“`body_flow` 有记录、`raw_run_ids` 为空”的状态——不是 Word 没字，而是 join 断了。

```text
读字：root.iter("w:t")           → 递归，hyperlink 里的字能读到 → body_flow.text ✅
读 run：paragraph.findall("w:r") → 只扫直接子级               → runs[] 可能为空 ❌
坐标：source_ref 用 python-docx index；run id 用 xml_index   → 两套坐标 ❌
```

## 1. 当前证据

证据来自当前三校调试输出：

```text
test_outputs/debug/template_generation/t1_document_facts_20260625_current/hunannongye/01_document_facts.json
test_outputs/debug/template_generation/t1_document_facts_20260625_current/nannong-undergraduate/01_document_facts.json
test_outputs/debug/template_generation/t1_document_facts_20260625_current/pku-graduate/01_document_facts.json
```

复现命令（2026-06-25 本地审计）：

```bash
uv run python -c "
from pathlib import Path
from docfit.template_generation.source_tree import inspect_document_facts_docx
facts = inspect_document_facts_docx(Path('inputs/targets/nannong-undergraduate/raw/source_template.docx'))
for seq in [9, 10]:
    item = next(x for x in facts['body_flow'] if x['source_seq'] == seq)
    print(seq, item['source_ref'], item.get('paragraph_id'), item['raw_run_ids'], item['text'][:20])
"
# 9 word/document.xml:p[25] p_0025 ['p_0046.r_001', ...] 目  录
# 10 word/document.xml:p[28] p_0028 [] 摘  要\tⅠ
```

### 1.1 覆盖缺口总表

| 学校 | body_flow | 段落项 | 表格单元格无 raw trace | 页眉页脚无 raw trace | `source_ref` 指向 XML 文本不匹配 | raw 前缀与 `source_ref` 不匹配 | TOC 条目无 raw trace | XML 可见段落存在嵌套 run | data 层可见对象 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 湖南农大 | 320 | 145 | 175/175 | 0/0 | 41/145 | 41 | 0 | 0 | 无 |
| 南农本科 | 124 | 114 | 1/1 | 9/9 | 111/114 | 90 | 24 | 26，其中 24 个 direct 可见 run=0 | fields 3、text_boxes 1、images 2 |
| 北大研究生 | 366 | 202 | 154/154 | 10/10 | 201/202 | 184 | 17 | 55，其中 54 个 direct 可见 run=0 | fields 139、content_controls 1、text_boxes 2、footnotes 1、images 15 |

解释：
- `source_ref` 指向 XML 文本不匹配：`body_flow[].source_ref` 里的 `word/document.xml:p[n]` 去源 DOCX OOXML 找到的段落文本，和 `body_flow[].text` 不是同一段。
- raw 前缀与 `source_ref` 不匹配：例如 `source_ref=word/document.xml:p[3]`，但 `raw_run_ids` 是 `p_0024.r_001` 这一类。
- TOC 条目无 raw trace：目录条目有 `body_flow.text`，但 `raw_run_ids=[]`、`logical_run_ids=[]`。
- XML 可见段落存在嵌套 run：可见文本藏在 `w:hyperlink`、field 等容器下，当前 `paragraph.findall(w:r)` 取不到或取到的是空占位 run。

### 1.2 具体例子：南农标题段落坐标错位（T1-ISSUE-001）

当前 `body_flow`（`source_seq=2`）：

```json
{
  "source_seq": 2,
  "source_ref": "word/document.xml:p[3]",
  "paragraph_id": "p_0003",
  "text": "南京农业大学本科生毕业论文（设计）原创性声明",
  "raw_run_ids": ["p_0024.r_001", "p_0024.r_002", "p_0024.r_003", "p_0024.r_004", "p_0024.r_005", "p_0024.r_006", "p_0024.r_007", "p_0024.r_008"],
  "logical_run_ids": ["p_0024.lr_001"]
}
```

问题点：
- `source_ref` / `paragraph_id` 指向 python-docx visible index `p[3]`。
- raw run trace 使用 OOXML `xml_index=24` → `p_0024`。
- 源 DOCX 的 `word/document.xml:p[3]` 实际文本是 `本科生毕业论文（设计）`，不是这条声明标题。

这不是展示层问题。T2/T3/T6 若按 `source_ref` 定位会跳到错误节点；若按 raw id 定位又与 `paragraph_id` 不一致。

### 1.3 具体例子：南农目录标题 vs 目录条目（T1-ISSUE-001 + 003）

两类失败模式不同，应分开看。

#### 1.3.1 目录标题 `source_seq=9`：有 run，但坐标分裂

当前 `body_flow`：

```json
{
  "source_seq": 9,
  "source_ref": "word/document.xml:p[25]",
  "paragraph_id": "p_0025",
  "text": "目  录",
  "style": "Heading 1",
  "raw_run_ids": ["p_0046.r_001", "p_0046.r_002", "p_0046.r_003"],
  "logical_run_ids": ["p_0046.lr_001"]
}
```

源 DOCX OOXML（`inputs/targets/nannong-undergraduate/raw/source_template.docx`）：

```text
word/document.xml:p[46]  text='目  录'
  direct r[1] '目 '
  direct r[2] ' '
  direct r[3] '录'
```

- run 合并已正确（3 raw → 1 logical，空格保留）。
- 但 `source_ref=p[25]`、`paragraph_id=p_0025` 与 run 前缀 `p_0046` 不在同一坐标系。

#### 1.3.2 目录条目 `source_seq=10`：坐标错 + run 完全缺失

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

中间层 `data.paragraphs[]` 记录（步骤 1 输出）：

```text
index=28          # python-docx visible index → 写入 source_ref
xml_index=49      # OOXML index → run id 本应使用这个
source_ref=word/document.xml:p[28]
runs=[]           # 浅扫 + 过滤后为空
```

源 DOCX OOXML `word/document.xml:p[49]`：

```text
text='摘  要Ⅰ'（含 tab）
  direct r[1..3] ''           # 3 个空占位 direct run（被 _visible_text 过滤掉）
  hyperlink[1]:
    r[1] '摘'
    r[2] '  '
    r[3] '要'
    r[4] ''                   # tab 控制符
    r[5] 'Ⅰ'
```

根因叠加：
1. `source_ref` 使用 python-docx index（28），不是 OOXML index（49）。
2. run 抽取 `paragraph.findall(w:r)` 只拿 direct run，且过滤空可见文本；hyperlink 内 5 个 run 完全未进 `runs[]`。
3. `is_toc_entry` 是 T2 语义，不应在 T1 输出（见 T1-ISSUE-007）。

字段生命周期（`source_seq=10`）：

```text
Word p[49] hyperlink→run×5
       │
步骤1 inspector
  text ─────────────────────→ ✅ body_flow.text
  source_ref ──index=28──────→ ❌ p[28]
  runs ──浅扫+过滤空run────→ ❌ []
       │
步骤2 run_index（runs 为空则跳过）
       │
步骤3 body_flow 组装
  raw_run_ids ──索引 miss───→ ❌ []
  is_toc_entry ──T2逻辑误放─→ ⚠️ true
```

### 1.4 具体例子：表格单元格是可见正文，但没有 run trace（T1-ISSUE-002）

南农 `source_seq=1` 是封面表格单元格：

```json
{
  "flow_item_type": "table_cell",
  "kind": "table_cell",
  "source_ref": "word/document.xml:tbl[1]/tr[1]/tc[1]",
  "text": "本科生毕业论文（设计）\n题    目:\n姓    名:\n...",
  "raw_run_ids": [],
  "logical_run_ids": []
}
```

三校统计里，表格单元格没有任何 raw trace：
- 湖南农大：175/175
- 南农本科：1/1
- 北大研究生：154/154

根因：`_runs_from_inspection()` 只遍历顶层 `data.paragraphs`（`doc.paragraphs`），不覆盖单元格内段落。

### 1.5 具体例子：T1 semantic signals 越权（T1-ISSUE-007）

当前 `source_tree.py` 在构造 `document_facts.body_flow[]` 时直接写入 `structural_signals`：

```python
"structural_signals": _structural_signals(entry)
```

`_structural_signals()` 位于 `structure_candidates.py`（T2 模块）。当前 T1 输出里包含 `is_toc_entry`、`is_spacing_line`、`looks_like_instruction_text`、`likely_unit_heading` 等。

| 当前 T1 字段 | 应归属 | T1 应改为输出的事实 |
| --- | --- | --- |
| `is_toc_entry` | T2 | `style_name=toc 1`、`has_tab`、`trailing_page_token=Ⅰ`、`leader_chars=…` |
| `is_spacing_line` | T2/T3 | 原始文本、括号文本、包含“空”、包含行/格、数字 token |
| `looks_like_instruction_text` | T3，T2 可消费 | 原始文本、括号文本、字体/字号词 token |
| `likely_unit_heading` | T2 | alignment、font_size_pt、bold、样式名、分页/分节、原始文本 |
| `large_font` / `short_text` | T2/T3 | `font_size_pt`、`text_length` 等原始值 |

## 2. 根因定位

### 2.1 段落坐标混用（T1-ISSUE-001）

相关代码：
- `inspector.py` `_paragraphs()`：`source_ref = word/document.xml:p[{index}]`，`index` 来自 `enumerate(doc.paragraphs)`。
- 同函数：`xml_index = _xml_paragraph_indices(doc).get(paragraph._p, index)` 已计算 OOXML 序号，但未写入 `source_ref`。
- `source_tree.py` `_runs_from_inspection()`：用 `xml_index` 生成 `p_{xml_index:04d}.r_*`。
- `source_tree.py` `_stable_ids_for_entry()`：从 `source_ref` 解析 `paragraph_id` → 得到 visible index 坐标。

```text
body_flow.source_ref / paragraph_id  → python-docx visible index
runs.raw_run_id / logical_run_id     → OOXML xml_index
```

### 2.2 run 索引只覆盖顶层 `data.paragraphs`（T1-ISSUE-002、004）

`source_tree.py` `_runs_from_inspection()` 只遍历 `tree["data"]["paragraphs"]`。

不覆盖：表格单元格内段落、页眉页脚段落、文本框、脚注、部分 content control 内段落。

### 2.3 run 抽取只看直接子 `w:r`（T1-ISSUE-003）

`inspector.py` `_paragraph_style_details_by_index()`：

```python
runs = [
    _run_style(run, paragraph_run_properties)
    for run in paragraph.findall(f"{W_NS}r")
    if _visible_text(run, strip=False)
]
```

漏采：hyperlink、field、smartTag、sdt 等容器内的 run；且空占位 direct run 被过滤，导致“有 nested run、visible direct run=0”的段落 `runs=[]`。

### 2.4 页眉页脚只聚合 part 文本（T1-ISSUE-004）

`data.headers_footers` 有聚合 `text`，body_flow 页眉脚项无 raw/logical run。

### 2.5 verifier 无覆盖率门禁（T1-ISSUE-006）

`verifier.py` `_verify_t1_document_facts()` 只检查 schema 形状，不检查 trace 覆盖率与坐标一致性 → false PASS。

### 2.6 semantic signals 在 T1 生成（T1-ISSUE-007）

`source_tree.py` import `structure_candidates._structural_signals`，事实抽取与语义判断模块边界混淆。

## 3. Issue 列表

| ID | 标题 | 级别 | 状态 |
| --- | --- | --- | --- |
| T1-ISSUE-001 | canonical paragraph id / source_ref 不统一 | P0 | OPEN |
| T1-ISSUE-002 | 表格单元格缺 run trace | P0 | OPEN |
| T1-ISSUE-003 | TOC / field / hyperlink 嵌套 run 漏采 | P0 | OPEN |
| T1-ISSUE-004 | 页眉页脚缺 paragraph/run 明细 | P1 | OPEN |
| T1-ISSUE-005 | data 层可见对象未建模 | P1 | OPEN |
| T1-ISSUE-006 | verifier 缺覆盖率门禁 | P0 | OPEN |
| T1-ISSUE-007 | structural_signals 语义越权 | P0 | OPEN |

各 issue 期望行为与验收标准见 §3.1–§3.7（与原台账一致，略）。

### T1-ISSUE-001：canonical paragraph id / source_ref 不统一

严重级别：P0

期望行为：
- `body_flow[].source_ref` 必须指向源 DOCX 中真实承载该文本的 OOXML 节点。
- `body_flow[].paragraph_id`、`raw_run_ids`、`logical_run_ids` 必须在同一坐标系（OOXML paragraph index）。
- python-docx visible index 保留为 `python_docx_index`，不得伪装成 `word/document.xml:p[n]`。

验收标准：
- 有 raw trace 的段落项，`paragraph_id` 与 raw id 前缀一致。
- 三校 `source_ref` 指向 XML 文本不匹配数 → 0。
- verifier 新增 `document_facts_paragraph_trace_mismatch`。

### T1-ISSUE-002：表格单元格缺 run trace

严重级别：P0

期望行为：可见 `table_cell` 必须有可回放 trace（聚合级 `raw_run_ids` 或 `cell_paragraph_refs` / `cell_run_refs`）。

验收标准：三校可见表格单元格无 raw trace 数 → 0；verifier 新增 `document_facts_visible_table_cell_trace_missing`。

### T1-ISSUE-003：嵌套 run 漏采

严重级别：P0

期望行为：按 OOXML 文档顺序遍历段落内所有可见 `w:r`；保留 `w:tab` / `w:br`；记录 `container_refs`。

验收标准：南农 24 条、北大 17 条 TOC 类条目均有 raw/logical trace；`direct 可见 run=0` 且 `nested run>0` 的段落不再丢 run。

### T1-ISSUE-004：页眉页脚缺 paragraph/run 明细

严重级别：P1

期望行为：页眉页脚 part 有 paragraph/run 级事实；PAGE 字段可回链到 run。

### T1-ISSUE-005：data 层可见对象未建模

严重级别：P1

期望行为：可见对象进入 body_flow、带 `modeled_as` 旁路关系、或 `unknown_objects`。

### T1-ISSUE-006：verifier 缺覆盖率门禁

严重级别：P0

建议新增 finding：`document_facts_paragraph_trace_mismatch`、`document_facts_visible_paragraph_trace_missing`、`document_facts_visible_table_cell_trace_missing`、`document_facts_header_footer_trace_missing`、`document_facts_nested_run_trace_missing`、`document_facts_visible_object_unmodeled`、`document_facts_semantic_field_in_t1`。

### T1-ISSUE-007：structural_signals 语义越权

严重级别：P0

期望行为：T1 移除 `is_*` / `looks_like_*` / `likely_*` / 阈值标签；改输出 `text_facts` 原子字段；T2/T3 自行计算语义信号。

验收标准：`01_document_facts.json` 不再含上述语义字段；`source_tree.py` 不再 import `_structural_signals`；T2 边界结果等价且只出现在 T2 artifacts。

---

## 4. 优化方案总览

目标：把 T1 从“python-docx 浅读 + 两套坐标拼接”改为“**OOXML canonical extractor + 单一坐标系 + 统一 join**”。

```text
                    ┌─────────────────────────────────┐
                    │  OoxmlPartExtractor (新模块)       │
                    │  输入: docx zip 各 part xml      │
                    │  输出: canonical paragraph/run   │
                    └───────────────┬─────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
      paragraphs[]            runs[]               containers[]
      (OOXML index)      (深扫 w:r + tab/br)    (hyperlink/field/...)
              │                     │
              └──────────┬──────────┘
                         ▼
              body_flow[] + indexes
              (同一 paragraph_id 坐标系)
                         │
                         ▼
              text_facts{}（原子事实，替代 structural_signals）
```

设计原则：
1. **单一坐标系**：OOXML paragraph index 为 canonical；`source_ref=word/{part}.xml:p[{n}]` 的 `n` 必须是 OOXML 序号。
2. **单一 extractor**：正文、表格、页眉脚、文本框、脚注共用同一 run 遍历逻辑。
3. **先事实、后语义**：T1 只产出 `text_facts`；`is_toc_entry` 等迁到 T2。
4. **先红后绿**：verifier 覆盖率门禁先于功能修复合入，避免 false PASS。

### 4.1 已拍板的设计决策（原 §5 讨论项）

#### D1：表格单元格在 body_flow 中怎么表达？→ **选 C**

- 保留 `table_cell` 聚合节点（服务 T2 整表语义）。
- 新增 `cell_paragraph_refs[]` / `cell_run_refs[]` 指向单元格内 canonical paragraph/run（服务 T3/T6）。
- 单元格内段落**不**单独占用正文 `source_seq`，避免打乱阅读顺序；通过 `container_ref` 与 `parent_table_cell_id` 关联。

#### D2：页眉页脚是否进入 body_flow？→ **选 C**

- 保留 body_flow 中的页眉脚聚合项（便于 T2 看到存在性）。
- 新增 `part_flows[]`（或 `data.header_footer_paragraphs[]`）按 part 输出 paragraph/run 明细。
- T4/T6 按 `part_name` + `source_ref` 消费，不与正文 `source_seq` 混排。

#### D3：图片、文本框、脚注的 verifier 严格度？→ **选 B**

- 允许旁路建模：`modeled_as: "image" | "text_box" | "footnote" | "field"` + `parent_ref` / `source_seq_ref`。
- 可见但未建模 → `unknown_objects` 或 verifier `document_facts_visible_object_unmodeled`。
- 不强制所有对象进入正文 `source_seq`。

---

## 5. 优化方案详细设计

### 5.1 Phase 0：verifier 覆盖率门禁（T1-ISSUE-006）

**目的**：让当前三校输出先变红，防止“修一半仍 PASS”。

**改动文件**：`src/docfit/template_generation/verifier.py`、新增 `tests/unit/test_t1_fact_coverage_verifier.py`

**新增检查**（对 `body_flow[]` 每项）：

| Finding code | 条件 | 严重度 |
| --- | --- | --- |
| `document_facts_paragraph_trace_mismatch` | `paragraph_id` 前缀 ≠ `raw_run_ids[0]` 前缀（若有 raw） | UNKNOWN |
| `document_facts_visible_paragraph_trace_missing` | `kind=paragraph` 且 `visible=true` 且 `text` 非空且 `raw_run_ids=[]` | UNKNOWN |
| `document_facts_visible_table_cell_trace_missing` | `kind=table_cell` 且 `visible=true` 且无任何 cell trace | UNKNOWN |
| `document_facts_header_footer_trace_missing` | 页眉脚 body_flow 项无 part-local trace | UNKNOWN |
| `document_facts_semantic_field_in_t1` | body_flow 出现 `is_*` / `looks_like_*` / `likely_*` | FAIL |
| `document_facts_source_ref_text_mismatch` | 回源 DOCX 校验 `source_ref` 段落文本与 `body_flow.text` 不一致 | UNKNOWN |

**验收**：对 `t1_document_facts_20260625_current` 三校输出跑 verifier → T1 状态为 `UNKNOWN`（非 PASS）。

### 5.2 Phase 1：统一 canonical 坐标（T1-ISSUE-001）

**改动文件**：`inspector.py` `_paragraphs()`、`source_tree.py` `_stable_ids_for_entry()`、`_raw_run_ids_for_entry()`

**规则**：

```python
# 修复前
source_ref = f"word/document.xml:p[{index}]"           # python-docx index
paragraph_id = f"p_{index:04d}"                        # 从 source_ref 解析

# 修复后
canonical_index = xml_index                            # OOXML index
source_ref = f"word/document.xml:p[{canonical_index}]"
paragraph_id = f"p_{canonical_index:04d}"
python_docx_index = index                              # 辅助字段，仅供 debug
```

**join 修复**：`_raw_run_ids_for_entry()` 对 `kind=paragraph` 改用 `paragraph_id` 查 `runs_by_paragraph_id`，不再用错误的 `source_ref` 键（当前 visible index）。

**验收**：
- 南农 `source_seq=9`：`source_ref=p[46]`，`paragraph_id=p_0046`，`raw_run_ids` 前缀 `p_0046`。
- 南农 `source_seq=2`：`source_ref` 指向声明标题真实 OOXML 段落，与 `p_0024` 一致或合并为同一 id。

### 5.3 Phase 2：OOXML 深扫 run extractor（T1-ISSUE-003）

**新模块建议**：`src/docfit/template_gap/ooxml_runs.py`（或扩展现有 `inspector.py` 内聚函数）

**核心算法**：

```python
def iter_paragraph_runs(paragraph_el, *, part_name, paragraph_index):
    """按文档顺序深度遍历段落内所有 w:r，跳过 w:del 等不可见节点。"""
    run_index = 0
    for event, node in walk_paragraph_content(paragraph_el):
        if node.tag == W_R:
            run_index += 1
            yield RunRecord(
                source_ref=f"{part_name}:p[{paragraph_index}]/r[{run_index}]",
                container_ref=current_container_ref,  # hyperlink[1] 等
                text=visible_text_with_tab_br(node),
                ...
            )
```

**要点**：
- 遍历范围：`paragraph.iter()` 中所有 `w:r`，而非 `paragraph.findall(w:r)`。
- 空占位 run：若含 `w:tab` / `w:br` / `w:sym`，仍产出 run，`text` 可为 `"\t"` / `"\n"` / `""`。
- 容器路径：`source_ref` 扩展为 `p[49]/hyperlink[1]/r[3]`；`runs[].container_refs[]` 记录容器链。
- 与 logical run 合并：仍在 `source_tree._runs_from_inspection()` 按 `effective_style` 相邻合并；`merged_from` 覆盖全部 raw id。

**南农 `source_seq=10` 修复后期望**：

```json
{
  "source_seq": 10,
  "source_ref": "word/document.xml:p[49]",
  "paragraph_id": "p_0049",
  "text": "摘  要\tⅠ",
  "style": "toc 1",
  "raw_run_ids": ["p_0049.r_001", "p_0049.r_002", "p_0049.r_003", "p_0049.r_004", "p_0049.r_005"],
  "logical_run_ids": ["p_0049.lr_001"],
  "text_facts": {
    "style_name": "toc 1",
    "style_id": "10",
    "has_tab": true,
    "trailing_page_token": "Ⅰ"
  }
}
```

`runs[]` 中 `p_0049.lr_001` 的 `merged_from` 含 hyperlink 内 5 个 raw run；`container_refs` 含 `word/document.xml:p[49]/hyperlink[1]`。

### 5.4 Phase 3：表格与页眉脚 part 覆盖（T1-ISSUE-002、004）

**表格**：

1. `OoxmlPartExtractor` 遍历 `w:tbl` → `w:tr` → `w:tc` → 内嵌 `w:p`。
2. 每个单元格段落进入 `cell_paragraphs[]`，带 `table_id` / `cell_id` / `cell_paragraph_index`。
3. `body_flow` 聚合项增加：

```json
{
  "kind": "table_cell",
  "source_ref": "word/document.xml:tbl[1]/tr[1]/tc[1]",
  "cell_paragraph_refs": ["word/document.xml:tbl[1]/tr[1]/tc[1]/p[1]", "..."],
  "cell_run_refs": ["p_????.r_001", "..."],
  "raw_run_ids": ["..."],
  "logical_run_ids": ["..."]
}
```

**页眉脚**：

1. 对 `word/header*.xml`、`word/footer*.xml` 运行同一 extractor。
2. 输出 `part_flows[]`：

```json
{
  "part_name": "word/footer2.xml",
  "paragraphs": [...],
  "runs": [...],
  "fields": [...]
}
```

3. body_flow 页眉脚项通过 `part_flow_ref` 指向 `part_flows[]` 子树。

### 5.5 Phase 4：T1 原子事实字段 + 移除 semantic signals（T1-ISSUE-007）

**从 body_flow 移除**：`structural_signals` 整块；verifier 对任何旧 T1 语义字段报 `document_facts_semantic_field_in_t1`。

**新增 `text_facts`**（每段 body_flow 项，均可从 DOCX 直接观测）：

```json
{
  "text_facts": {
    "raw_text": "摘  要\tⅠ",
    "normalized_text": "摘  要\tⅠ",
    "char_count": 6,
    "has_tab": true,
    "has_line_break": false,
    "parenthesized_segments": [],
    "trailing_token": "Ⅰ",
    "leader_char_run": null,
    "style_id": "10",
    "style_name": "toc 1",
    "alignment": "left",
    "dominant_font_size_pt": 12.0,
    "dominant_bold": false
  }
}
```

**T2 迁移**：把 `structure_candidates._is_toc_entry()` / `_is_spacing_line()` 改为消费 `text_facts`，输出到 `template_structure_candidates.json` 或 `unit_map` 的 `boundary_signals`，不再写回 T1。

**T3 迁移**：`looks_like_instruction_text` 改读 `text_facts.parenthesized_segments` 等。

**无过渡兼容策略**：
- `artifact_version` 升至 `1.1`。
- T2 只读 `text_facts` 和其他 T1 原子事实；旧 `structural_signals` / `is_toc_entry` 等语义字段即使存在也视为无效输入。
- 合同测试锁定：新输出不得含 semantic 字段。

### 5.6 Phase 5：data 层可见对象建模（T1-ISSUE-005）

| 对象类型 | 策略 | 产物字段 |
| --- | --- | --- |
| PAGE/TOC field | 已有 `data.fields[]` | 增加 `paragraph_ref` / `run_ref` / `container_ref` |
| image | 旁路 | `modeled_as: image`，`parent_paragraph_ref` |
| text_box | 旁路 + part_flow | `part_flows[].text_boxes[]` |
| footnote | 旁路 | `part_flows[].footnotes[]` 或 `unknown_objects` |
| content_control | 容器 | `container_refs` + 内嵌 paragraph/run |

未覆盖类型进入 `unknown_objects`，T1 verifier 非 PASS。

---

## 6. 分阶段实施计划

| 阶段 | 内容 | 主要 issue | 预估改动面 | 退出标准 |
| --- | --- | --- | --- | --- |
| **P0** | verifier 覆盖率门禁 | 006 | verifier + 单测 | 三校旧输出 T1=UNKNOWN |
| **P1** | canonical 坐标统一 | 001 | inspector + source_tree | `source_ref` 文本不匹配=0；id 前缀一致 |
| **P2** | 深扫 nested run | 003 | 新 ooxml_runs + source_tree | 南农 24 TOC 条目有 trace |
| **P3** | 表格 cell trace | 002 | inspector tables + source_tree | 三校表格 cell 无 trace=0 |
| **P4** | 页眉脚 part_flow | 004 | inspector headers/footers | 南农/北大页眉脚有 trace |
| **P5** | 移除 semantic + text_facts | 007 | source_tree + structure_candidates | T1 无 `is_*`；T2 等价 |
| **P6** | data 对象建模 | 005 | inspector + schema | 可见对象均有 modeled_as 或 unknown |

建议同一 PR 系列按 P0→P1→P2 顺序合入；P3/P4 可并行；P5 在 P2 后（避免在脏 trace 上叠新字段）；P6 可最后。

```text
P0 verifier ──→ P1 坐标 ──→ P2 深扫 run ──→ P5 text_facts
                              ├──→ P3 表格
                              └──→ P4 页眉脚
                                        └──→ P6 data 对象
```

---

## 7. 目标 schema 片段（artifact_version 1.1）

```json
{
  "artifact_type": "document_facts",
  "artifact_version": "1.1",
  "body_flow": [
    {
      "source_seq": 10,
      "node_id": "body_0010",
      "kind": "paragraph",
      "source_ref": "word/document.xml:p[49]",
      "paragraph_id": "p_0049",
      "python_docx_index": 28,
      "text": "摘  要\tⅠ",
      "style": "toc 1",
      "raw_run_ids": ["p_0049.r_001", "p_0049.r_002", "p_0049.r_003", "p_0049.r_004", "p_0049.r_005"],
      "logical_run_ids": ["p_0049.lr_001"],
      "text_facts": {
        "style_name": "toc 1",
        "style_id": "10",
        "has_tab": true,
        "trailing_page_token": "Ⅰ"
      }
    }
  ],
  "runs": [
    {
      "logical_run_id": "p_0049.lr_001",
      "paragraph_id": "p_0049",
      "text": "摘  要\tⅠ",
      "merged_from": ["p_0049.r_001", "p_0049.r_002", "p_0049.r_003", "p_0049.r_004", "p_0049.r_005"],
      "source_refs": [
        "word/document.xml:p[49]/hyperlink[1]/r[1]",
        "word/document.xml:p[49]/hyperlink[1]/r[2]",
        "word/document.xml:p[49]/hyperlink[1]/r[3]",
        "word/document.xml:p[49]/hyperlink[1]/r[4]",
        "word/document.xml:p[49]/hyperlink[1]/r[5]"
      ],
      "container_refs": ["word/document.xml:p[49]/hyperlink[1]"]
    }
  ],
  "part_flows": [],
  "indexes": {
    "runs_by_paragraph_id": { "p_0049": ["p_0049.r_001", "..."] },
    "runs_by_source_ref": { "word/document.xml:p[49]": ["p_0049.r_001", "..."] }
  }
}
```

---

## 8. 非目标

- T2 unit 边界识别准确率调优（本 issue 只保证 T2 输入事实完整）。
- T3 段内语义切分规则。
- T4 页码规则最终 high confidence 判定。
- 样式级联 gold 级精确验证（另开 issue）。

---

## 9. 验证建议

### 9.1 单元与合同测试

```bash
uv run pytest tests/unit/test_t1_structural_facts.py -q
uv run pytest tests/unit/test_t1_fact_coverage_verifier.py -q   # Phase 0 新增
uv run pytest tests/contract -q
uv run pytest -q
```

### 9.2 三校输出验证

```bash
uv run docfit eval template-generate \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --out test_outputs/debug/template_generation/t1_fact_coverage_fix/hunannongye
uv run docfit eval template-generate \
  --template inputs/targets/nannong-undergraduate/raw/source_template.docx \
  --out test_outputs/debug/template_generation/t1_fact_coverage_fix/nannong-undergraduate
uv run docfit eval template-generate \
  --template inputs/targets/pku-graduate/raw/source_template.docx \
  --out test_outputs/debug/template_generation/t1_fact_coverage_fix/pku-graduate
```

### 9.3 审计断言（修复后必须满足）

| 断言 | 湖南农大 | 南农本科 | 北大研究生 |
| --- | ---: | ---: | ---: |
| `source_ref` 文本不匹配 | 0 | 0 | 0 |
| 段落 id 与 raw 前缀不一致 | 0 | 0 | 0 |
| 可见段落 `raw_run_ids` 为空 | 0 | 0 | 0 |
| 可见表格 cell 无 trace | 0 | 0 | 0 |
| TOC 类条目无 trace | 0 | 0 | 0 |
| T1 含 `is_*` / `likely_*` 字段 | 0 | 0 | 0 |
| T1 verifier | PASS | PASS | PASS |

### 9.4 回归样例（建议新增 fixtures）

| 样例 | 覆盖 issue | 说明 |
| --- | --- | --- |
| `nested_toc_hyperlink.docx` | 003 | hyperlink 内 5 run + tab |
| `table_cover_cell.docx` | 002 | 单元格多段落 + run trace |
| `header_page_field.docx` | 004 | footer PAGE field + run ref |
| `coordinate_mixed.docx` | 001 | 表格前有空段，visible index ≠ xml index |

---

## 10. 相关文档

- `docs/plans/template-parse-refactor-t1-document-facts.md` — T1 职责与上轮 run 归一化修复
- `docs/plans/template-parse-refactor-t2-unit-map.md` — T2 边界检测（`is_toc_entry` 归属）
- `docs/plans/template-parse-refactor-schema.md` — artifact 字段契约
- `docs/plans/template-parse-refactor-execution.md` — 总执行顺序
