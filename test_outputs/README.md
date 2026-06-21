# DocFit 测试输出目录

一句话结论：`test_outputs/` 放评测、调试和本地验证跑出来的文件；这里的内容默认可以删除后重新生成。

目标结构：

```text
test_outputs/
  eval_runs/
  debug/
    template_generation/
    template_parsing/
    content_extraction/
    content_placement/
    docx_rendering/
  workbench/
```

| 目录 | 放什么 |
| --- | --- |
| `eval_runs/` | `docfit eval ...`、coverage、e2e 和 convert 报告目录 |
| `debug/` | 单阶段调试快照；每个阶段单独放到下面的阶段目录 |
| `workbench/` | 人工整理包、临时 review packet、可丢弃草稿 |

`debug/` 下的阶段目录：

| 目录 | 放什么 |
| --- | --- |
| `debug/template_generation/` | 模板生成调试文件，例如 source tree、规则发现、生成计划、manifest 和 debug index |
| `debug/template_parsing/` | 模板解析/模板理解调试文件，例如 template artifact、样式字段和单元识别快照 |
| `debug/content_extraction/` | 用户内容提取调试文件，例如可见内容台账、unsupported 对象和提取 artifact |
| `debug/content_placement/` | 内容放置调试文件，例如 placement plan、去向检查和放置失败定位 |
| `debug/docx_rendering/` | DOCX 渲染调试文件，例如 render manifest、feature snapshot、最终 DOCX 打开检查证据 |

后续新增阶段输出时，先在 `debug/<stage_name>/` 下建目录和 `.gitkeep`，
再把该阶段的临时输出写进去。目录占位可以提交，目录里的运行产物默认按可再生成文件处理。

如果某个输出被人工签收为标准，必须迁到 `standards/` 并补齐签收记录；不能继续留在这里当标准。
