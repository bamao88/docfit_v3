---
status: draft
owner: template-generation
stage: T3
topic: element-policy
issue_id: T3-ELEMENT-ISSUE-05
issue_sequence: 05
severity:
  - P1
created: 2026-07-01
last_updated: 2026-07-03
previous_issue:
  id: T3-ELEMENT-ISSUE-04
  doc: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-issue-04-instruction-manual-confusion.md
  status: implemented
previous_optimization:
  doc: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-plan-04-instruction-manual-confusion.md
  summary: 已解决表单使用说明误判为 manual_only 的问题；真实 run 继续暴露行内括号格式说明被合并进 fixed/fill/generated/manual_only 元素的残余问题。
next_plan: docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/generation_model.py
  - src/docfit/template_generation/plan.py
  - src/docfit/template_generation/executor.py
evidence_fixture:
  target: hunannongye
  run_bundle: test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye
  t3_code: test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/03.0_t3_code_element_spec.yaml
  t3_merged: test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/03.2_t3_merged_element_spec.yaml
  output_docx: test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/fillable_template.docx
---

# T3 元素策略 Issue 05：行内括号格式说明并入非 instruction 元素后残留

## 问题摘要

上一轮 `T3-ELEMENT-ISSUE-04` 已解决“表单使用说明被误判为 manual_only”的问题，但最新 hunannongye 真实 run 仍发现另一类 T3 残余：行内括号格式说明没有被单独拆成 instruction，而是被合并进 `fixed` / `fill` / `generated` / `manual_only` 元素。

代表样本是 cover 标题行中的 `（一号华文行楷加粗）`：它没有被单独标为 `instruction_remove`，而是和固定标题 `湖 南 农 业 大 学` 合并为同一个 `fixed/template_fixed` 元素。进一步扫描后确认，同类问题不止这一处，且这些格式说明会继续进入 `05_template_spec.yaml` 和最终 `fillable_template.docx`。

## 真实运行口径

运行包：

```text
test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye
```

核查命令：

```bash
rg -n "一号华文行楷加粗|湖 南 农 业 大 学" \
  test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/01_document_facts.json \
  test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/03.0_t3_code_element_spec.yaml \
  test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/03.2_t3_merged_element_spec.yaml \
  test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/05_template_spec.yaml
```

关键证据：

```text
01_document_facts.json:
- source_seq=3 / word/document.xml:p[3]
- r[2] text = "湖 南 农 业 大 学"，font=华文行楷，26.0pt，bold=true
- r[3] text = "（一号华文行楷加粗）"，font=宋体，9.0pt，bold=true
- text_facts.parenthesized_segments = ["一号华文行楷加粗"]

03.2_t3_merged_element_spec.yaml:
- element_id: e_007
- unit_id: cover
- policy: fixed
- role: template_fixed
- raw_run_ids: [p_0003.r_001, p_0003.r_002, p_0003.r_003]
- logical_run_ids: [p_0003.lr_001, p_0003.lr_002]
- content: 湖 南 农 业 大 学（一号华文行楷加粗）

05_template_spec.yaml:
- content 继续包含 "湖 南 农 业 大 学（一号华文行楷加粗）"
```

## 补充扫描结果

扫描口径：

```text
在 03.2_t3_merged_element_spec.yaml 中搜索 content 含格式型括号（号/宋体/黑体/楷体/华文/Times/加粗/居中/空几行等），且 policy != instruction_remove 的元素；再按 DOCX w:t 拼接文本确认最终输出是否残留。
```

当前命中 8 处，最终 DOCX 拼接文本均可见：

| 元素 | policy / role | source_seq | 残留内容 |
| --- | --- | --- | --- |
| `cover.e_007` | `fixed` / `template_fixed` | 3 | `湖 南 农 业 大 学（一号华文行楷加粗）` |
| `cover.e_013` | `fixed` / `template_fixed` | 7 | `TITLE OF GRADUATION PAPER（四号Times New Roman加粗，大写）` |
| `integrity_statement.e_012` | `manual_only` / `manual_field` | 23 | `（空三行）` |
| `toc.e_001` | `generated` / `generated_field` | 24 | `目□□录   (二号黑体，居中)` |
| `abstract_cn.e_009` | `fill` / `student_content` | 60 | `Title of Graduation Paper （四号Times New Roman，加粗，居中）` |
| `abstract_en.e_001` | `fixed` / `template_fixed` | 65 | `□□Abstract(小四号Times New Roman， 加粗):……            (五号Times New Roman)` |
| `references.e_002` | `generated` / `generated_field` | 91 | `[1] 作者.论文题名[J].期刊名，出版年，卷（期）：页码A-B.       (五号宋体)` |
| `acknowledgement.e_002` | `fill` / `student_content` | 95 | `本论文是在×××老师的悉心指导和热情关怀下完成的……。 (小四号宋体)` |

## Expected vs observed

Expected：

```text
1. "湖 南 农 业 大 学" 是封面固定标题，应保留为 fixed/template_fixed。
2. "（一号华文行楷加粗）" 是行内格式说明，应作为独立 instruction_remove/template_instruction 或等价删除元素。
3. 同类格式说明（字体、字号、加粗、居中、空几行等）无论附着在 fixed/fill/generated/manual_only 上，都不应进入最终可填写模板正文。
4. T3 code_raw、AI raw、merged 三路线都应能解释这些元素的边界和 policy 差异。
5. 进入 T6 后，格式说明应生成 remove_instruction_text 或等价 run-level 删除动作，最终 fillable_template.docx 不应残留该括号说明。
```

Observed：

```text
1. T1 事实层已经保留 run 级差异和 parenthesized_segments。
2. T3 code_raw 把 r[2] 标题和 r[3] 格式说明合并为 cover.e_007。
3. T3 merged 沿用 code_raw 结果，policy=fixed，role=template_fixed，confidence=high。
4. 扩展扫描显示，类似格式说明还被并入 fill/generated/manual_only 元素。
5. 这些内容继续进入 05_template_spec.yaml 和最终 DOCX；现有 judge 没有把这类非 instruction 元素内嵌格式说明残留报为 mismatch。
```

## 疑似根因

```text
1. Plan 03 已解决部分段内 run split，但当前规则仍会在 cover 固定标题场景把"固定标题 + 括号格式说明"聚合为同一 element。
2. 现有 instruction 识别更偏向独立说明段、占位字段后的格式注释和表单说明，对"真实内容/占位内容 + 行内格式说明"的尾随括号没有形成稳定边界。
3. T3 policy 一旦把合并后的整段判为 fixed/fill/generated/manual_only，会掩盖尾随 parenthesized_segments 的删除需求。
4. 标准验收当前更关注 policy group / required field contract，缺少"非 instruction 元素内部不得包含格式说明括号"的元素级 diff 口径。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. T3-ELEMENT-ISSUE-03：段内 run refs 已贯通，格式说明具备 run-level 删除基础。
2. T3-ELEMENT-ISSUE-04：表单使用说明不再优先落入 manual_only。
3. 三路线 T3 artifact 已落盘，能同时查看 code_raw、AI raw、merged。
```

未解决：

```text
1. 尾随或行内括号格式说明仍可能被并入 fixed/fill/generated/manual_only。
2. T3 merged 没有把 code_raw 里的 fixed-with-instruction 风险降级为 conflict 或 manual_review。
3. standard judge 没有覆盖此类元素内部残留，因此会给出 PASS 但漏掉实际模板污染。
```

## 后续验收门禁

```text
1. hunannongye cover source_seq=3 应拆出可删除的 "（一号华文行楷加粗）" 元素，且保留 "湖 南 农 业 大 学" 为 fixed。
2. 对应 T3 element 必须携带 raw_run_ids/logical_run_ids，可回查到 document_facts 的具体 run。
3. 补充扫描结果中的 8 个代表性残留，在最终 fillable_template.docx 拼接文本中均应消失；真实内容主体应保留。
4. 新增反例：真实固定标题、学校名称、"论文（设计）"、"卷（期）"、"百分制" 等业务括号不能被误删。
5. standard judge 或 route eval 至少在诊断报告中暴露非 instruction 元素内部 instruction-like residual 的 mismatch / root_cause / owner_assignment / fix_plan。
```

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-01 | 初稿：基于 hunannongye 最新三路线真实 run，记录 `（一号华文行楷加粗）` 被 T3 合并为 fixed 的残余问题 |
| 2026-07-02 | 扩展扫描：T3 merged 中共发现 8 处格式型括号未标为 instruction_remove，且均在最终 DOCX 拼接文本中残留 |
| 2026-07-03 | 登记方案：与 issue-06 共用综合 plan-06（run/span 子元素模型 + AI 为主），`next_plan` 已指向该 plan |
