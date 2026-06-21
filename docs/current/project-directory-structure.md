# 项目目录结构约定

Last updated: 2026-06-21

一句话结论：这是目录结构约定的唯一完整正文；根目录 `DIRECTORY_STRUCTURE.md` 只保留短入口，避免两份目录表同时维护。

## 快速判断

| 你要新增什么 | 放到哪里 | 不能放哪里 |
| --- | --- | --- |
| 长期维护的当前项目文档 | `docs/current/` | 不放 `docs/human/`、`docs/plans/` |
| 计划、方案、阶段拆解 | `docs/plans/` | 不冒充当前实现 |
| 人工审查、讨论材料、历史过程 | `docs/human/` | 不放长期维护正文 |
| 面向 agent 的操作手册 | `docs/agents/` | 不作为产品真相默认入口 |
| 学校源模板、学校格式要求、人工模板 review | `test_inputs/template_generation/` | 不放 `standards/`，也不放旧 `inputs/` |
| 学生源论文、人工内容 review、内容提取样例 | `test_inputs/content_extraction/` | 不放 `tests/`，也不放旧 `inputs/` |
| 单独测试 generated-template gap 的被测 Word | `test_inputs/template_gap/` | 不当成真实生成器输出或 signed standard |
| 已签收标准、expected、golden、学校例外 | `standards/` | 不放 `test_outputs/` |
| 不绑定具体模板生成验证的 eval、coverage、e2e、convert 运行输出 | `test_outputs/debug/template_eval_runs/` 或显式 `/tmp/...` | 不放 `reports/`、`out/`、`standards/` 或根级 `test_outputs/eval_runs/` |
| 绑定某个模板生成验证的 eval 运行输出 | `test_outputs/debug/template_generation/<验证名>/eval_runs/` | 不散放到其他 run 目录 |
| 单阶段临时调试输出 | `test_outputs/debug/<stage_name>/`，模板生成用 `test_outputs/debug/template_generation/<验证名>/` | 不放 `tests/` |
| 人工整理包、review packet、可丢弃草稿 | `test_outputs/workbench/` | 不放 `standards/` |
| pytest 测试代码 | `tests/unit/`、`tests/contract/`、`tests/e2e/`、`tests/regression/` | 不承载运行输出 |

## 顶层目录

```text
docfit_v3/
  README.md
  SPEC.md
  STATUS.md
  DIRECTORY_STRUCTURE.md  # 根目录短入口，完整正文在 docs/current/project-directory-structure.md

  docs/
    current/       # 长期维护的当前文档
    plans/         # 计划和历史方案
    human/         # 审查、讨论、历史过程
    agents/        # agent 操作手册

  src/docfit/      # 产品代码
  standards/       # 已签收标准和 expected/golden
  test_inputs/     # 可复现输入
  test_outputs/    # 可再生成运行输出
  tests/           # pytest 测试代码
  scripts/         # 可复用维护脚本
```

## `docs/` 目录边界

| 目录 | 做什么 | 不做什么 |
| --- | --- | --- |
| `docs/current/` | 当前有效、长期维护、需要持续对齐实现的文档 | 不放一次性计划和历史审查 |
| `docs/plans/` | 计划、拆解、阶段方案、历史执行方案 | 不作为当前实现的默认真相 |
| `docs/human/` | 人工 review、讨论材料、过程记录、迁移指针 | 不继续维护长期正文 |
| `docs/agents/` | agent runbook、工具说明、长流程操作 | 不替代产品文档 |

## 运行输出边界

`test_outputs/` 表示系统跑出来的东西。它可以被删除后重新生成；如果某个输出被人工签收为标准，必须迁入 `standards/` 并补签收记录。

| 子目录 | 放什么 |
| --- | --- |
| `test_outputs/debug/template_eval_runs/` | 不绑定具体模板生成验证的 eval / coverage / e2e run 输出 |
| `test_outputs/debug/template_generation/<验证名>/` | 模板生成逐步证据和该验证自己的 `eval_runs/` |
| `test_outputs/workbench/` | 人工整理包和可丢弃草稿 |

`test_outputs/debug/` 已预建这些输出目录：

```text
test_outputs/debug/
  template_eval_runs/             # 不绑定具体模板生成验证的 eval / coverage / e2e / convert run
  template_generation/
    <验证名>/
      eval_runs/                  # 绑定这个模板生成验证的 eval run
  template_parsing/
  content_extraction/
  content_placement/
  docx_rendering/
```

新增或输出调试内容时，按阶段或验证对象放进对应目录。目录和 `.gitkeep` 可以提交；目录里的
JSON、DOCX、截图、manifest、临时报告等运行产物默认可再生成，不能作为
`PASS` / `FAIL` / `UNKNOWN` 的人工改写依据。

## 评测输出归属规则

`test_outputs/debug/template_eval_runs/` 只放不属于某一个模板生成验证的评测运行结果。例如：

- `docfit eval e2e --school demo-school ... --out test_outputs/debug/template_eval_runs/bootstrap_pass`
- `docfit eval coverage --profile real-core-v0 --out test_outputs/debug/template_eval_runs/real-core-v0`
- `docfit convert ... --report test_outputs/debug/template_eval_runs/run_convert_001`

如果一次评测是围绕某个模板生成验证展开的，就放进这个验证自己的目录：

```text
test_outputs/debug/template_generation/<验证名>/
  <时间戳>/                    # 模板生成支撑流程 debug 快照，例如 00-10 步文件
  eval_runs/
    template_generate/          # 生成出来的 generated_template.docx 和报告
    template_gap_<学校或场景>/   # 同一份 generated_template 的 gap 检查报告
```

例如 `unit_copy_test_01.docx` 的模板生成验证应该放在：

```text
test_outputs/debug/template_generation/unit_copy_test_01/
  <时间戳>/
  eval_runs/template_generate/
```

不要再新建或使用 `test_outputs/debug/eval_runs/`；根级 `test_outputs/eval_runs/` 也不是新的默认输出入口。

## 标准边界

`standards/` 是“应该怎么判”的来源，不是输入目录，也不是输出目录。

规则：

- 不能因为当前输出变化自动更新 standards。
- `UNKNOWN` 或 `FAIL` 不能通过改 standards 被消掉，除非有人工签收证据和变更记录。
- `template_artifact.json`、`template_generation_manifest.json`、`template_gap_report.json` 都不是标准。

## 当前边界

旧 `inputs/`、`reports/`、`out/` 和 `tests/template/` 不再是默认入口。看到这些名字时，
先检查是不是旧文档说明或 CLI 参数名；不要把新文件放回这些旧目录。

签收标准只属于 `standards/`。如果某个 `test_outputs/` 里的产物要升级成标准，必须先有人工签收证据、
变更原因和对应测试，不能直接拿当前输出覆盖 expected 或 golden。
