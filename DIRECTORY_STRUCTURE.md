# DocFit 目录模板

一句话结论：新增输入、输出、测试、标准或文档前，先按这个文件判断应该放哪里；完整解释以
`docs/human/project-directory-structure.md` 为准。

## 快速判断

| 你要新增什么 | 放到哪里 | 不能放哪里 |
| --- | --- | --- |
| 学校源模板、学校格式要求、人工模板 review | `test_inputs/template_generation/` | 不放 `standards/`，也不放旧 `inputs/` |
| 学生源论文、人工内容 review、内容提取样例 | `test_inputs/content_extraction/` | 不放 `tests/`，也不放旧 `inputs/` |
| 单独测试 generated-template 差距的被测 Word | `test_inputs/template_gap/` | 不当成真实生成器输出或 signed standard |
| 正式 eval、coverage、e2e、convert 的运行输出 | `test_outputs/eval_runs/` | 不放 `reports/` 或 `out/` |
| 单阶段临时调试输出 | `test_outputs/debug/<stage_name>/` | 不放 `tests/` |
| 人工整理包、review packet、可丢弃草稿 | `test_outputs/workbench/` | 不放 `standards/` |
| pytest 测试代码 | `tests/unit/`、`tests/contract/`、`tests/e2e/`、`tests/regression/` | 不承载运行输出 |
| 已签收标准、expected、golden、学校例外 | `standards/` | 不放 `test_outputs/` |
| 人类可读当前事实、流程和验收规则 | `docs/human/` | 不放大体量运行证据 |
| 面向 agent 的长流程手册 | `docs/agents/` | 不当成产品真相默认入口 |

## Debug 阶段目录

`test_outputs/debug/` 已预建这些阶段目录：

```text
test_outputs/debug/
  template_generation/
  template_parsing/
  content_extraction/
  content_placement/
  docx_rendering/
```

新增或输出调试内容时，按阶段放进对应目录。目录和 `.gitkeep` 可以提交；目录里的
JSON、DOCX、截图、manifest、临时报告等运行产物默认可再生成，不能作为
`PASS` / `FAIL` / `UNKNOWN` 的人工改写依据。

## 当前边界

旧 `inputs/`、`reports/`、`out/` 和 `tests/template/` 不再是默认入口。看到这些名字时，
先检查是不是旧文档说明或 CLI 参数名；不要把新文件放回这些旧目录。

签收标准只属于 `standards/`。如果某个 `test_outputs/` 里的产物要升级成标准，必须先有人工签收证据、
变更原因和对应测试，不能直接拿当前输出覆盖 expected 或 golden。
