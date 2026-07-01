---
status: implemented
owner: template-generation
stage: T3
topic: element-policy
issue_id: T3-ELEMENT-ISSUE-04
issue_sequence: 04
severity:
  - P1
created: 2026-07-01
last_updated: 2026-07-01
previous_issue:
  id: T3-ELEMENT-ISSUE-03
  doc: docs/plans/2026-06-30-template-parse-refactor-t3-element-policy-issue-03-within-paragraph-run-split.md
  status: draft
previous_optimization:
  doc: docs/plans/2026-07-01-template-parse-refactor-t2t3t4-agent-proposal-plan-06-observation-code-bridge-acceptance.md
  summary: AI observation bridge 与 standard acceptance 已接入，但真实模板输出暴露 T3 deterministic policy 仍会把说明文本误判为 manual_only。
next_plan: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-plan-04-instruction-manual-confusion.md
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/plan.py
  - src/docfit/template_generation/executor.py
evidence_fixture:
  target: hunannongye
  run_bundle: test_outputs/debug/template_generation/20260701_real_template_generate/hunannongye
  output_docx: test_outputs/debug/template_generation/20260701_real_template_generate/hunannongye/fillable_template.docx
---

# T3 元素策略 Issue 04：表单说明误判为 manual_only 后进入成稿

## 问题摘要

湖南农业真实模板生成后，`fillable_template.docx` 中仍保留多条“注/此表/请在/不得更改”等说明性文本。追踪 `03_element_spec.yaml` 与 `05_template_spec.yaml` 后确认：这些文本不是 T6 删除失败，而是在 T3 被标为 `manual_only` / `manual_field`，随后按人工填写字段保留。

## 真实运行口径

运行包：

```text
test_outputs/debug/template_generation/20260701_real_template_generate/hunannongye
```

单看输出文档：

```text
test_outputs/debug/template_generation/20260701_real_template_generate/hunannongye/fillable_template.docx
```

核查方式：

```bash
unzip -p test_outputs/debug/template_generation/20260701_real_template_generate/hunannongye/fillable_template.docx word/document.xml
```

并对 `03_element_spec.yaml` / `05_template_spec.yaml` 搜索残留说明文本。

## Expected vs observed

Expected：

```text
1. “注：此表如不够填写，可另加页/附页。”这类表单使用说明应为 instruction_remove。
2. “此表可从毕业论文管理系统下载/填写打印”“请在合适选项前打勾”“不得随意更改”等使用说明应为 instruction_remove。
3. “指导教师签名”“学生签名”“意见”“成绩”等真实人工填写位置仍应为 manual_only。
4. 进入 T6 的 instruction_remove 应生成 remove_instruction_text action，并从 fillable_template.docx 中删除。
```

Observed：

```text
1. 多条说明文本出现在 fillable_template.docx。
2. T3 中这些元素的 policy=manual_only，role=manual_field，manual_semantics 等于原说明文本。
3. T6 只删除已经被 T3 标为 instruction_remove 的元素；被误判为 manual_only 的说明不会进入删除计划。
4. template-generation-judge 目前仍 PASS，说明现有阶段标准没有覆盖“表单说明残留”的真实验收。
```

代表性误判样本：

```text
一、毕业设计任务书是学校根据已经确定的毕业设计题目下达给学生的一种教学文件，是学生在指导教师指导下独立从事毕业设计工作的依据。此表由指导教师填写。
四、任务书一经下达，不得随意更改。
请在合适的对应选项前的“□”内打“√”，科研课题请注明课题项目和名称，项目指“国家青年基金”等。
六、本表可从毕业论文管理系统填写打印或教务处网站下载中心下载填写打印，但签名栏必须相应责任人亲笔签名，且应用黑色签字笔填写。
注：此表如不够填写，可另加附页。
注：此表可从毕业论文管理系统或教务处网站下载中心下载。记录、签名栏必须用黑色笔手工填写。
```

## 疑似根因

```text
1. _element_policy() 在表单类 unit 上默认返回 manual_only。
2. _looks_like_instruction() 的 marker 主要覆盖“格式/要求/说明/模板”等排版说明，没有覆盖“注：此表...”这类表单使用说明。
3. MANUAL_ONLY_MARKERS 包含“签名/意见/成绩/评定”，导致含“签名栏必须...”的说明文本更容易被保留为 manual_only。
4. 当前 standard judge 没有把最终 DOCX 中 instruction-like residual text 作为 T3/T6 端到端差异诊断项。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. AI observation bridge 已能把 instruction_remove 类观察转成代码生成 overlay。
2. T3 已有 instruction_remove -> remove_instruction_text 的代码生成路径。
3. 真实运行产物链可以用于定位 T3 element_spec 与最终 DOCX 残留。
```

未解决：

```text
1. deterministic T3 对表单使用说明的 instruction 覆盖不足。
2. manual_only 与 instruction_remove 的优先级缺少“说明文本优先删除”的防护。
3. stage standard diff diagnosis 没有暴露此类残留为 mismatch。
```

## 后续验收门禁

```text
1. 新增 T3 回归测试：真实残留说明样本应进入 remove_instruction_text，并从输出 DOCX 消失。
2. 新增反例测试：真实人工手填字段（如“指导教师签名：”“评阅教师意见：”）仍为 manual_only。
3. 重新跑 hunannongye 真实模板生成，输出 DOCX 不再包含本 issue 列出的代表性说明文本。
4. 重新跑 template-generation-judge；若 judge 仍 PASS，需要在最终说明中标明它尚未覆盖残留说明 diff。
```

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-01 | 初稿：基于 hunannongye 真实输出记录 T3 表单说明误判为 manual_only 的问题 |
| 2026-07-01 | 已修复：新增表单使用说明识别规则；hunannongye 重新生成后代表性说明文本不再出现在 fillable_template.docx；judge 仍 PASS 且 mismatches=[]，标准残留说明覆盖缺口另行处理 |
