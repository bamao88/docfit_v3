# DocFit 测试输入目录

一句话结论：`test_inputs/` 放仓库随附的可复现评测输入，不放运行输出、标准、golden 或 expected。

目标结构只保留两层：

```text
test_inputs/
  template_generation/
  content_extraction/
  template_gap/
```

| 目录 | 放什么 |
| --- | --- |
| `template_generation/` | 学校原始模板、学校格式要求、人工模板 review、模板生成单页调试输入 |
| `content_extraction/` | 用户/学生原始论文、人工内容 review、内容提取回归输入 |
| `template_gap/` | 已经生成好的 `generated_template.docx` fixture，用来单独测试生成模板差距检查 |
