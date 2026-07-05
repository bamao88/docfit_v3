---
status: draft
owner: template-generation
stage: T3
topic: element-policy
issue_id: T3-ELEMENT-ISSUE-06
issue_sequence: 06
severity:
  - P1
created: 2026-07-02
last_updated: 2026-07-03
previous_issue:
  id: T3-ELEMENT-ISSUE-05
  doc: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-issue-05-inline-style-instruction-fixed-merge.md
  status: draft
previous_optimization:
  doc: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-plan-04-instruction-manual-confusion.md
  summary: 已解决表单使用说明误判为 manual_only；后续真实 run 暴露 T3 对同一元素内部的标签、布局占位和示例值缺少子 span 粒度。
next_plan: docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/generation_model.py
  - src/docfit/template_generation/plan.py
  - src/docfit/template_generation/executor.py
evidence_fixture:
  target: hunannongye
  run_bundle: test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye
  t3_merged: test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/03.2_t3_merged_element_spec.yaml
  output_docx: test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/fillable_template.docx
---

# T3 元素策略 Issue 06：占位符与示例值缺少子 span 粒度

## 问题摘要

hunannongye 最新真实 run 中，T3 对包含 `□` / `××` / `……` 的元素仍以整段 element 为主要粒度，缺少“固定标签 / 布局占位 / 示例值 / 学生填写槽”的子 span 语义。典型样本：

```text
□□□□□□学□□号：20××××××××××
```

T3 当前把整行作为 `cover.e_021`，并标为 `fixed/template_fixed`。这导致 `□□□□□□`、`学□□号` 内部 spacing token、`20××××××××××` 示例学号都不会进入删除或替换计划。

## 真实运行口径

运行包：

```text
test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye
```

核查命令：

```bash
rg -n "□□□□□□学□□号|20××××××××××" \
  test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/01_document_facts.json \
  test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/03.2_t3_merged_element_spec.yaml \
  test_outputs/debug/template_generation/20260701_real_template_generate_after_t3_three_docs/hunannongye/05_template_spec.yaml
```

关键证据：

```text
01_document_facts.json:
- source_seq=10 / word/document.xml:p[13]
- run 1: "□□□□□□"，font=黑体，16pt，bold=true
- run 2: "学□□号："，font=黑体，16pt，bold=true
- run 3: "20××××××××××"，font=楷体_GB2312;楷体，16pt，bold=true

03.2_t3_merged_element_spec.yaml:
- element_id: e_021
- unit_id: cover
- policy: fixed
- role: template_fixed
- source_seq_refs: [10]
- raw_run_ids: [p_0013.r_001, p_0013.r_002, p_0013.r_003]
- logical_run_ids: [p_0013.lr_001, p_0013.lr_002]
- content: □□□□□□学□□号：20××××××××××
```

## Expected vs observed

Expected：

```text
1. `□□□□□□` 是布局占位符，不应作为最终可见文本保留。
2. `学□□号：` 应归一为可见标签 `学号：`，内部 `□□` 只是字宽 spacing token。
3. `20××××××××××` 是示例值，应删除或替换为学号填写槽/SDT。
4. T3 输出应能表达这些子 span 的不同处置：保留标签、删除布局占位、替换示例值、生成填写控件。
5. T6 不应只能在整段之后追加 content control；它需要可消费的 run/span 级替换目标。
```

Observed：

```text
1. T1 已经提供 run 级事实，可区分三个 run。
2. T3 merged 仍把整行合并为一个 element，并标为 fixed/template_fixed/high。
3. 该 element 继续进入 05_template_spec.yaml。
4. build_manifest 对 cover.e_021 没有删除/替换动作，因为 fixed 元素不会生成 fillable slot 或 remove_instruction_text。
```

## 扩展扫描结果

扫描口径：

```text
在 03.2_t3_merged_element_spec.yaml 中搜索 content 含 `□`、连续 `×`、`20×` 或 `……`，且 policy != instruction_remove 的元素。
```

当前命中 66 个非删除元素：

```text
by_policy:
- fixed: 15
- fill: 25
- generated: 23
- manual_only: 3

by_pattern:
- leading_squares: 36
- internal_squares: 15
- example_x_runs: 23
- ellipsis_placeholder: 37
```

代表性样本：

```text
cover.e_017 fill: □□□□□□学生姓名
cover.e_021 fixed: □□□□□□学□□号：20××××××××××
cover.e_022 fill: □□□□□□年级专业及班级：20××级×××（×）班
cover.e_023 fixed: □□□□□□指导老师及职称：×××□教授
cover.e_024 fill: □□□□□□学□□院：××××学院  （学院名用全称）
abstract_cn.e_005 fill: □□关键词：×××；×××；×××；×××
abstract_en.e_002 fixed: □□Key words: ×××； ×××；×××； ×××
body_main.e_005 fill: 2□××××
references.e_003 fill: ……
```

注意：这些命中不全是同一种责任。`fixed` 中包含占位符通常是 T3 policy/粒度错误；`fill` / `generated` 中包含占位符说明 T3 虽识别了大类，但仍缺少可供 T6 替换原文的子 span 契约。

## 疑似根因

```text
1. T3 当前 element 粒度主要按段落/run-slice 聚合，缺少 field-line parser：label、layout spacer、sample value、input slot 没有独立 span 类型。
2. `□` 同时承担布局空格、字段名间距、目录缩进和勾选框等多种含义，当前规则没有按上下文区分。
3. `××` / `20××` / `……` 被当作普通 content 或 fill content，而不是“应被替换的示例值”。
4. T6 当前可创建 SDT，但没有收到“替换哪一个 run/span”的明确指令时，会出现源文本残留或在原文后追加控件。
5. standard judge 没有把最终 DOCX 中的 placeholder-like residual 纳入 T3/T6 差异诊断。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. T3-ELEMENT-ISSUE-03：T3 已能携带 raw_run_ids/logical_run_ids，具备 run 级定位基础。
2. T3-ELEMENT-ISSUE-04：表单说明误判为 manual_only 的问题已修复。
3. T3-ELEMENT-ISSUE-05：已记录格式说明括号残留，不与本 issue 的 `□`/`××`/`……` 占位符混淆。
```

未解决：

```text
1. 字段行内部缺少子 span 粒度，不能表达“标签保留、占位删除、示例值替换”。
2. fixed/fill/generated/manual_only 中仍大量携带 placeholder-like 文本。
3. 当前验收仍可能 PASS，但最终 fillable_template.docx 里保留大量模板示例字符。
```

## 后续验收门禁

```text
1. `□□□□□□学□□号：20××××××××××` 应被拆分或标注为：删除 leading □、保留/归一 `学号：`、将 `20××××××××××` 替换为学号填写槽。
2. 代表性 cover 字段（学生姓名、学号、年级专业班级、指导老师、学院、提交日期）最终 DOCX 不应残留 `□□□□□□`、字段内 `□□` spacing token、`××` 示例值。
3. 正文真实业务括号和合法文本不能误删，例如 `论文（设计）`、`卷（期）`、`百分制`。
4. T3/T6 诊断报告应输出 placeholder residual 的 mismatch、root_cause、owner_assignment、fix_plan。
5. 修复后重新跑 hunannongye 真实生成，并用 DOCX 拼接文本扫描确认代表性 placeholder residual 清零。
```

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-02 | 初稿：记录 `□□□□□□学□□号：20××××××××××` 在 T3 中整行固定化，以及 66 个非删除 placeholder-like 元素扫描结果 |
| 2026-07-03 | 登记方案：作为主 source_issue 进入综合 plan-06（run/span 子元素模型 + AI 为主，同时覆盖 issue-05），`next_plan` 已指向该 plan |
