---
status: resolved
owner: template-generation
stage: T3
topic: element-policy
issue_id: T3-ELEMENT-ISSUE-03
issue_sequence: 03
severity:
  - P1
created: 2026-06-30
last_updated: 2026-07-01
previous_issue:
  id: T3-ELEMENT-ISSUE-02
  doc: docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md
  status: draft
previous_optimization:
  doc: docs/plans/template-parse-refactor-t1-document-facts.md
  summary: T1 明确段内语义拆分（占位 vs 括号格式说明）归 T3；body_flow 提供 raw_run_ids / logical_run_ids 挂钩 runs[]，但下游未消费。
next_plan: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-plan-03-within-paragraph-run-split.md
related_docs:
  - docs/plans/template-parse-refactor-issue-index.md
  - docs/plans/template-parse-refactor-t1-fact-coverage-issues.md
  - docs/plans/template-parse-refactor-t1-document-facts.md
  - docs/plans/2026-06-30-template-parse-refactor-t2t3t4-agent-module1-issue-05-observation-input-followups.md
related_code:
  - src/docfit/template_generation/source_tree.py
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/agent/packet.py
  - src/docfit/template_generation/agent/evidence.py
evidence_fixture:
  target: hunannongye
  source_template: inputs/targets/hunannongye/raw/source_template.docx
  annotated_preview: test_outputs/debug/annotated-demo/page-1-annotated-preview.png
---

# T3 元素策略 Issue 03：段内未按 run 拆分，占位符与格式说明绑成同一元素

## 问题摘要

同一 Word 段落（一个 `source_seq` / 一个 `<w:p>`）内，**模板占位文字**与**括号内格式说明**（如 `（小二黑体加粗）`）在 T1 已拆成不同 `runs[]`，但 T3 仍按整段 `body_flow` 文本生成**单个 element**，且多为 `fixed` 保留全文。导致格式说明无法单独标为 `remove_instruction`，并连带影响 annotated 红框、AI `query_text` 与 Module 1 T3 证据粒度。

**结论**：`source_seq` 对齐 Word `<w:p>` 是正确事实层；缺口在 **T3 `_infer_elements` 未消费 `logical_run_ids` / `runs[]` 做段内元素化**（文档已归位 T3，代码未接）。

---

## 真实运行口径

复现（本地）：

```bash
uv run python -c "
from pathlib import Path
from docfit.template_generation.source_tree import inspect_document_facts_docx, inspect_source_template_docx
from docfit.template_generation.structure_candidates import build_template_structure_candidates
facts = inspect_document_facts_docx(Path('inputs/targets/hunannongye/raw/source_template.docx'))
tree = inspect_source_template_docx(Path('inputs/targets/hunannongye/raw/source_template.docx'))
candidates = build_template_structure_candidates(tree)
item = facts['body_flow'][5]  # source_seq=6
print('source_ref', item['source_ref'])
print('text', item['text'])
print('raw_run_ids', item['raw_run_ids'])
for unit in candidates['units']:
    if unit.get('unit_id') != 'cover':
        continue
    for el in unit.get('elements', []):
        if 6 in (el.get('source_seq_refs') or []):
            print('element', el.get('element_id'), el.get('candidate_policy'), repr(el.get('content')))
            print('raw_run_ids', el.get('raw_run_ids'))
"
```

---

## Expected vs observed

### Expected（产品 / 计划口径）

```text
1. T1：一个 <w:p> → 一个 source_seq（块级地址不变）；段内 run 事实保留在 runs[] 与 body_flow.raw_run_ids。
2. T3：在同一 source_seq 内，按 logical run 或括号格式说明模式拆成多个 element：
   - 占位/标签文字 → fixed 或 fill
   - 纯格式说明（小二黑体、三号黑体等）→ remove_instruction
3. element_spec 应携带 raw_run_ids / logical_run_ids，证据可反查到具体 run。
4. annotated / page_text_index 可视需要展示段级或 run 级（段级 source_seq 仍为主键）。
```

### Observed（当前）

```text
1. source_seq=6 → word/document.xml:p[7]，单段落：
   text = '毕业论文（设计）中文题目  （小二黑体加粗）'
   raw_run_ids = ['p_0007.r_001', 'p_0007.r_002', 'p_0007.r_003', 'p_0007.r_004']
   runs 内 r_002 / r_003 文本已分开。
2. T3 cover.e_006：candidate_policy=fixed，content 含括号格式说明，source_seq_refs=[6]，raw_run_ids=None。
3. _looks_like_instruction(整段 text) 因「实质占位 + 括号说明」共存返回 False → 不会 remove_instruction。
4. _element_from_entries / _logical_entry_groups 按 body_flow 条目分组，不按 run。
5. annotated 红框：一 source_seq 一框，占位与说明同一框（忠实反映块级索引，非独立 bug）。
```

---

## 因果链（便于对齐 source_seq / body_flow 讨论）

```text
Word 模板：题目占位与（格式说明）在同一 <w:p>（未按 Enter 拆开）
    ↓
T1：1 个 body_flow 行 → source_seq=6；runs[] 有段内细片
    ↓
annotated / query_text / Module1 T3 evidence：按 source_seq 一行
    ↓
T3：1 个 element，policy=fixed，注释无法单独删除
```

与 **Enter vs Shift+Enter** 的关系：

- 中文题目行 vs 英文 TITLE 行：中间 **Enter** → 两个 `<w:p>` → `source_seq` 6 与 7（正确）。
- 题目 vs `（小二黑体）`：同一段内不同 run → 仍 **一个** `source_seq`（正确事实）；**T3 应在此段内再拆**（未做）。

---

## 疑似根因

```text
1. T2/T3 早期实现以 source_seq 为主索引跑通单元/元素，_infer_elements 直接消费 body_flow 条目。
2. T1 文档写明段内拆分归 T3，但 structure_candidates 未实现 run 级 _logical_entry_groups。
3. _element_policy 对整段 text 做启发式判断，_strip_format_annotations 仅用于匹配，不拆 element。
4. element 契约虽有 raw_run_ids 字段，_element_from_entries 未赋值。
5. T1 fact-coverage 仍有个别 body_flow 项 raw_run_ids 为空（join 断），会阻碍全面 run 级落地。
```

**不是根因**：

- `source_seq` 按 `<w:p>` 编号（T1 职责正确）。
- annotated 画一个红框（反映 source_seq 边界正确）。

---

## 建议修复方向（讨论后定稿）

```text
1. T3 _infer_elements：在单条 body_flow 内，按 logical_run_ids 或括号格式说明切分候选 element。
2. 规则：纯（*号*体*）run → remove_instruction；标签+占位 run → fill/fixed；保留 source_seq_refs 并增加 run 级 refs。
3. _element_from_entries：写入 raw_run_ids / logical_run_ids；content 按子片段而非整段拼接（或拆多条 element）。
4. 单测：hunannongye cover source_seq=6 → 至少 2 elements（占位 vs 格式说明）。
5. 连带：Module 1 T3 evidence / annotated 是否 expose run 级 bbox（可选，不替代 source_seq）。
6. 前置：修复 T1 body_flow ↔ runs join 断链（见 t1-fact-coverage-issues.md）。
```

---

## 验收门禁（草案）

```text
1. hunannongye cover：source_seq=6 产出 ≥2 个 T3 element，格式说明 run 为 remove_instruction。
2. element_spec 中对应项含 logical_run_ids，且与 document_facts.runs[] 可回查。
3. 正文长段落（单 <w:p> 多句）不应被 run 碎片过度切碎（需「同样式合并 + 仅括号/说明边界拆」策略）。
4. 标准签收 / template-generation-judge：相关 school standard 更新或注明段内拆分口径后再比。
5. 不改变 source_seq 编号规则（块级地址稳定）。
```

---

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-06-30 | 初稿：记录 cover source_seq=6 占位+格式说明绑死问题；T1 事实正确、T3 未消费 run |
| 2026-07-01 | 已按 Plan 03 修复：T3 段内 run 级元素化、run refs 贯通、run-level 删除和 hunannongye T3 standard 覆盖已落地 |
