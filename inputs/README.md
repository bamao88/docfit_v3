# DocFit 输入目录

一句话结论：`inputs/` 放仓库随附的可复现评测输入和人工 review 原文，不放标准、expected、golden 或运行输出。

```text
inputs/
  targets/<target_id>/
    input_manifest.yaml
    raw/
      source_template.docx
      source_review.md
    fixtures/template_gap/
      generated_template.input.docx
  students/<student_id>/
    input_manifest.yaml
    raw/
      source_document.docx
      content_review.md
```

| 目录 | 放什么 |
| --- | --- |
| `targets/<target_id>/raw/` | 学校或目标格式的原始模板 Word、格式要求和人工模板 review |
| `targets/<target_id>/fixtures/` | 用于单独测试某个检查器的冻结输入 fixture |
| `students/<student_id>/raw/` | 学生原始论文和人工内容 review |
| `input_manifest.yaml` | 记录输入文件的相对路径、用途和 sha256 |

如果某个输入被人工签收为标准，签收结果必须写入 `standards/`；不能直接把这里的原始文件当作 PASS 证明。
