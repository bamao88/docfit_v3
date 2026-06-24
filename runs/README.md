# DocFit 运行输出目录

一句话结论：`runs/` 放本地评测、调试和转换命令跑出来的证据；这里的内容默认可以删除后重新生成。

```text
runs/
  eval/
  template_generation/
  convert/
  workbench/
```

| 目录 | 放什么 |
| --- | --- |
| `eval/` | `docfit eval ...` 的报告、artifact 和调试证据 |
| `template_generation/` | `template-generate` 的 source tree、候选结构、生成模型、计划、manifest 和生成模板 |
| `convert/` | `docfit convert` 的临时或人工检查输出 |
| `workbench/` | 人工整理包、临时 review packet、可丢弃草稿 |

如果某个运行输出被人工签收为标准，必须迁到 `standards/` 并补齐签收记录；不能继续留在这里当标准。
