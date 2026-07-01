---
status: implemented
owner: template-generation
stage: T3
topic: element-policy
plan_id: T3-ELEMENT-PLAN-04
created: 2026-07-01
last_updated: 2026-07-01
source_issue:
  id: T3-ELEMENT-ISSUE-04
  doc: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-issue-04-instruction-manual-confusion.md
previous_plan:
  id: none
  doc: none
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/constants.py
  - tests/contract/test_template_generate.py
---

# T3 元素策略 Plan 04：表单说明优先识别为 instruction_remove

## 目标

让 T3 在表单类 unit 中优先识别“注/此表/请在/不得更改/下载填写”等使用说明为 `remove_instruction`，避免其落入 `manual_only` 并进入最终 `fillable_template.docx`。

## 实施顺序

1. 在 T3 策略层补充表单说明识别规则，位置应早于 `manual_only` 默认策略。
2. 明确反例：短标签或真实手填字段继续走 `manual_only`。
3. 添加回归测试，覆盖 hunannongye 真实残留文本和签名/意见字段反例。
4. 跑相关单测/契约测试，确认 `remove_instruction_text` action 生成并在 DOCX 中删除。
5. 重新跑 hunannongye 真实模板生成，核查最终 DOCX 残留。
6. 重新跑 standard judge，记录 judge 对该问题的覆盖情况。

## 设计约束

```text
1. 不改变 T1 事实边界，不向 T1 增加语义字段。
2. 不把所有含“签名/意见/成绩”的文本都删除；只有句式上是使用说明时删除。
3. 不影响正文、摘要、参考文献等 fillable content unit 的学生内容。
4. 不引入学校专用硬编码；样本可来自 hunannongye，但规则应描述通用表单说明。
```

## 完成信号

```text
1. tests/contract/test_template_generate.py 中新增用例通过。
2. 相关模板生成契约测试通过。
3. hunannongye 新生成 fillable_template.docx 不再包含 issue 文档中的代表性说明文本。
4. final 汇报包含：T3 根因、修复点、真实运行输出路径、judge 是否覆盖该类差异。
```

## 执行结果

```text
1. 已在 structure_candidates.py 增加表单使用说明识别规则，优先于 manual_only 默认策略。
2. 已新增契约测试，覆盖 hunannongye 真实残留说明样本与签名/意见字段反例。
3. 已重新生成 hunannongye：
   test_outputs/debug/template_generation/20260701_real_template_generate_after_t3fix/hunannongye/fillable_template.docx
4. 代表性残留文本 XML 搜索无命中；build_manifest 中 remove_instruction_text action 数量为 56。
5. template-generation-judge 输出 PASS / SIGNABLE / mismatches=[]；这说明当前 judge 尚未覆盖“最终 DOCX 残留说明文本”差异。
```

## 风险与回退

```text
1. 风险：过度删除含“此表/填写”的真实业务字段。
   控制：规则要求说明句式或说明前缀，并通过签名/意见反例测试。
2. 风险：合并段落中同时含标签和说明，整段删除过多。
   控制：本轮只解决独立说明段/合并说明块；段内拆分仍归 T3-ELEMENT-ISSUE-03。
```
