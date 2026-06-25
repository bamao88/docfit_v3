---
refactor_scope: template-parse-t1-document-facts
status: DONE
accepted_severities:
  - P1
  - P2
last_verified: 2026-06-25
---

# T1 事实层（document_facts）：职责、问题与优化

Last updated: 2026-06-25

一句话结论：T1 只负责把源 docx **读全读对**、产出**事实**，不做语义判断、不做"是不是边界/目录条目/说明文字"的合成决策。当前 T1 的 run 归一化和 run 级空白保留已修复；后续审计确认 `is_toc_entry` / `is_spacing_line` / `looks_like_instruction_text` / `likely_unit_heading` 这类 semantic signals 不应留在 T1，应统一归位到 T2/T3。

> 状态标注：**【已验证】**＝已在三校 `template-generate` 复现确认；**【设计】**＝待实现；**【✅ 已完成】**＝本轮已实现 + 测试通过。

## Status

DONE

已完成范围：
- run 归一化：`_runs_from_inspection()` 现在按同段相邻 + `effective_style` 相等合并 logical run，`merged_from` 覆盖全部 raw run id；`body_flow[].logical_run_ids` 去重但 `raw_run_ids` 原样保留。
- run 级可见空白：OOXML 中单独存在的空格 raw run 不再被 `.strip()` 丢弃；例如南农 `目  录` 会保留为 logical run 文本 `目  录`，并在 `merged_from` 中记录 `目 `、空格、`录` 三个 raw run。
- 有效样式维度：`font_names`、`font_size_pt`、`bold`、`italic`、`underline`、`color` 进入 `effective_style`；underline/color 已从 OOXML run properties 抽取。
- 职责边界：后续审计确认 `_structural_signals()` 混入语义判断，需从 T1 输出移除；当前越权问题统一记录在 T1 fact coverage issue。
- 验证：`uv run pytest tests/unit/test_t1_structural_facts.py -q`（20 passed）、`uv run pytest tests/contract -q`（75 passed）、`uv run pytest -q`（121 passed）。

仍未展开：样式级联 gold 级精确验证；T1 semantic signals 归位到 T2/T3。

后续审计新发现：T1 仍存在事实覆盖缺口，尤其是 canonical paragraph/run 坐标、表格/页眉页脚 trace、嵌套 run 和 verifier 覆盖率。详见 [T1 阶段事实覆盖缺口 issue](template-parse-refactor-t1-fact-coverage-issues.md)。

---

## 0. 职责与边界（先读）

**T1 是什么**：唯一"事实库"。把源 docx 读成结构化事实，后续阶段只按 id/range 引用、不复制内容。**确定性、可复现、不做语义。**

**输出粒度**（两层 + 段落事实）：
- **raw run**：OOXML `<w:r>` 原样切片（可能被 rsid/校对标记切碎）。
- **logical run**：把**相邻、有效样式相同**的 raw run 合并成一个，带 `merged_from` 记来源。
- **段落节点**：`{text, style, raw_run_ids, logical_run_ids, paragraph/style/control facts}` + 分节/分页/编号/字段/表/`unknown_objects`。

**"事实"指什么（澄清用词，避免误读）**：T1 字段必须能直接回到源 DOCX 的可观测内容，例如文本、tab、run、样式、字段、表格、页眉页脚、分节/分页和 source_ref。需要词表、正则、阈值、上下文或业务含义组合出来的字段不属于 T1；`large_font`、`short_text` 也应由下游根据 `font_size_pt` 和文本事实计算。**T1 不切词**，也不判断"这是不是标题/目录条目/说明文字"。

**责任边界（当前有越权，需归位）**：
- ⚠️ **`structural_signals` 是 T1 越权面**：`is_toc_entry`、`is_spacing_line`、`looks_like_instruction_text`、`likely_unit_heading` 都在回答"这段是什么含义"；`large_font`、`short_text` 是阈值判断。它们都应由 T2/T3 基于 T1 facts 计算，不应出现在 `document_facts`。
- **不属于 T1 的语义切分**：标题与行内格式说明的拆分（"摘要" vs "（三号黑体）"）、"标签：+ 填空"的拆分，都是 **T3 职责**。T1 只按样式合并 run，把 `摘要（三号黑体）` 作为**一个** logical run 原样产出，语义切分留给 T3。

---

## 1. 现状问题（均为三校复现实测）

### 1.1 run 归一化未实现（核心缺陷）【✅ 已完成】
**原根因**：`source_tree.py:128-135` —— 每个 raw run 1:1 映射成一个 logical run，`merged_from` 永远是 `[raw_run_id]` 单元素，**没有任何"合并相邻同样式 run"的逻辑**。字段名摆出归一化的样子，实现是纯改名透传。

**修复结果**：`source_tree.py` 现在按段落内相邻 raw run 分组，只有 `effective_style` 完全相同才合并；每个 logical run 的 `text` 是组内 raw run 文本拼接，`merged_from` 记录全部 raw run id，`indexes.runs_by_raw_run_id` 能从任一 raw id 找回所属 logical run。`body_flow[].raw_run_ids` 原样保留，`body_flow[].logical_run_ids` 输出去重后的 logical run id。

**影响**：源文档被 Word 按 rsid/校对切得很碎，facts 因此**过度切分**：

| 学校 | 现在 logical run | 按样式合并后≈ | 减少 | 受影响段落 |
| --- | --- | --- | --- | --- |
| 湖南农大 | 522 | 358 | 164 | 63 |
| 南农本科 | 383 | 111 | 272 | 57 |
| 北大研究生 | 1087 | 203 | **884** | 121 |

实例：南农 `南京农业大学本科生毕业论文（设计）原创性声明` 在 facts 里是 **8 个 logical run**（'南京农业'/'大学'/'本科'/'生'/'毕业'/'论文'/'（设计）原'/'创性声明'），**样式完全相同**（黑体 18pt），本该是 1 个；`目录` 是 2 个（'目'/'录'）。

**后果**（正中规范那句话）："要把有效样式相同的相邻 run 合并成一个逻辑 run，否则 run 级 diff 全是假阳性。" 现在 T3 的 run 级分类、T6 的 run 级施工都建在这些碎片上——T3 会把一个标题当成 8 个元素去判。

### 1.2 semantic signals 混入 T1（需归位）【设计】
**背景**：T2 做边界判定确实需要识别目录条目、空行说明、说明文字、标题候选，但这些是**下游判断**，不是 T1 facts。

**当前问题**：`_structural_signals()` 由 T1 调用并写入 `document_facts.body_flow[]`，其中包含 `is_toc_entry`、`is_spacing_line`、`looks_like_instruction_text`、`likely_unit_heading`、`large_font`、`short_text`。这些字段都应归位到 T2/T3。

**正确方向**：T1 输出原子事实，例如 `style_name=toc 1`、是否包含 tab、尾部页码 token、点引线字符、括号内文本、字体/字号词、对齐、字号、加粗、分页/分节；T2/T3 再基于这些 facts 生成语义信号。

### 1.3 样式级联解析精度未独立验证（open，本轮未展开）【设计】
规范指出 T1 最难的是"把样式解析成最终值"（中文字体主题反查 `theme1.xml`、半磅字号不取整、toggle 异或语义、表格/页眉脚/文本框遍历）。本轮**未对 T1 样式做 gold 级精确验证**，也未确认页眉脚/文本框是否已纳入。标记为待办，需要时单独建 `document_facts.gold.json` 精确比对，不在本份的修复范围。

---

## 2. 优化建议（T1 自己的）

### 2.1 实现 run 归一化（优先级最高）【✅ 已完成】
在 `_runs_from_inspection()`（`source_tree.py`）里：
- 遍历每段的 raw run，按**相邻 + 有效样式相等**分组；每组产出**一个** logical run；`logical_run_id` 按组给；`merged_from` = 该组**全部 raw_run_id**。
- **raw run 与 raw_run_id 原样保留**——T6 仍按 raw id 施工（符合规范 §T6"canonical id = 原始 run 位置 id"）。
- **边界：合并只按样式，不掺语义**。`摘要（三号黑体）` 合成一个 logical run，"摘要 vs（三号黑体）"的语义切分是 T3 的字符级 span 处理，别在 T1 做。
- 有效样式相等的判定维度：中西文字体名、字号(pt)、bold/italic、underline、color（与现 `effective_style` 一致）。

**测试断言**：`目录`→1 个 logical run；`目  录` 保留中间可见空格并记录空格 raw run；那个 8 段标题→1 个；`摘要（三号黑体）`→1 个且 `merged_from` 长度=3；归一化前后文本拼接不变（零丢弃）；bold/underline/color 任一有效样式不同都不会合并。

### 2.2 移除 T1 semantic signals（待统一修复）【设计】
从 `document_facts` 移除 `is_toc_entry`、`is_spacing_line`、`looks_like_instruction_text`、`likely_unit_heading`、`large_font`、`short_text`。T1 改为输出下游需要的原子事实；T2/T3 在自己的 artifact 中计算这些判断。详见 [T1 阶段事实覆盖缺口 issue](template-parse-refactor-t1-fact-coverage-issues.md) 的 `T1-ISSUE-007`。

---

## 3. 验收 / 测试命令
```bash
uv run pytest tests/unit/test_t1_structural_facts.py -q      # 20 passed
uv run pytest tests/contract -q                              # 75 passed
uv run pytest -q                                             # 121 passed
```

---

## 4. 状态小结
| 事项 | 职责 | 状态 |
| --- | --- | --- |
| semantic/threshold signals 归位：`is_toc_entry` / `is_spacing_line` / `looks_like_instruction_text` / `likely_unit_heading` / `large_font` / `short_text` | T2/T3 | ⬜ 需统一移出 T1（见 T1-ISSUE-007） |
| run 归一化（按样式合并 logical run） | T1 | ✅ 已完成（新增 T1 单测 + 合同/全量回归通过） |
| 样式级联解析精度 gold 验证 | T1 | ⬜ 未展开（open） |
