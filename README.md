# DocFit v3

一句话结论：DocFit v3 是一个评测框架优先的 DOCX 转换原型；它要证明转换结果满足已签收标准，而不是只生成一个看起来能打开的 Word 文件。

## 当前项目边界

当前真实实现已经有可运行的 `docfit eval ...` CLI、四阶段评测骨架、模板生成阶段、generated-template gap 检查、Bootstrap profile 和 real-core-v0 基线 gate。

当前没有证明 real-core-v0 已经转换合格。真实学校链路会生成 Word 和报告，但完整 gate 仍会因为模板、内容、放置、渲染问题返回 `FAIL` 或 `UNKNOWN`。

整个项目流程图见 `docs/current/README.md` 的“整体流程图”。

`docfit eval template-generate` 只负责：

```text
学校原始模板 Word -> generated_template.docx + 模板生成过程证据
```

它不读取学校签收标准，也不接受 `--school`。学校标准检查由 `docfit eval template-gap`、`docfit eval template` 和 real-core/e2e gate 负责。

当前模板生成默认先整包复制源 Word，但“仅复制单元”不能简单定义成“除几个单元外都复制”。判断口径是内容责任：普通目录、图目录、表目录、中文摘要、英文摘要、正文、参考文献，以及学生源文档中实际有内容的致谢或附录，都属于机器可能需要生成、填写或放置学生内容的区域；签名、日期、教师意见、成绩评定、声明固定正文等只需要学生或老师线下手写/确认的区域，可以作为仅复制单元保留。这个规则只是生成策略，不是验收结论；生成后的 Word 是否符合学校要求仍由 `template-gap` 判定。

## 文档怎么读

| 你要了解什么 | 入口 | 说明 |
| --- | --- | --- |
| 项目是什么、边界是什么、整体流程图 | `docs/current/README.md` | 当前长期维护文档入口 |
| 当前真实状态、下一步、阻塞项 | `STATUS.md` | 当前状态，不等于长期规范 |
| 阶段、字段、产物、判定必须怎么对齐 | `docs/current/contracts-and-gates.md` | 契约级入口，完整规范仍以 `SPEC.md` 为主 |
| 模板生成阶段怎么跑、怎么验收 | `docs/current/template-generation.md` | 流程、字段、执行、证据、gap 合并入口 |
| 模板生成流程怎么优化 | `docs/plans/template-generation-flow-optimization.md` | 生成策略选择、仅复制单元、填写/生成/人工区域的对齐计划 |
| 新增输入、输出、标准、测试、文档该放哪 | `DIRECTORY_STRUCTURE.md` | 根目录短入口，完整规则见 `docs/current/project-directory-structure.md` |

## 常用命令

安装或同步依赖：

```bash
uv sync
```

运行基础测试：

```bash
uv run pytest
```

运行 Bootstrap e2e：

```bash
uv run docfit eval e2e \
  --school demo-school \
  --student test_inputs/content_extraction/bootstrap-demo-student-pass.docx \
  --out test_outputs/debug/template_eval_runs/bootstrap_pass
```

运行 real-core-v0 coverage gate：

```bash
uv run docfit eval coverage \
  --profile real-core-v0 \
  --out /tmp/docfit_real_core_coverage
```

运行模板生成阶段：

```bash
uv run docfit eval template-generate \
  --template test_inputs/template_generation/school-hunannongye-requirement.docx \
  --out test_outputs/debug/template_generation/school-hunannongye-requirement/eval_runs/template_generate
```

检查生成模板是否满足学校签收标准：

```bash
uv run docfit eval template-gap \
  --school hunannongye \
  --generated-template test_outputs/debug/template_generation/school-hunannongye-requirement/eval_runs/template_generate/generated_template.docx \
  --out test_outputs/debug/template_generation/school-hunannongye-requirement/eval_runs/template_gap_hunannongye
```

## 目录速记

| 目录 | 用途 |
| --- | --- |
| `src/docfit/cli/` | Typer CLI 和 `docfit eval ...` / `docfit convert` 入口 |
| `src/docfit/convert/` | e2e、convert 和阶段编排 |
| `src/docfit/stages/` | 模板生成、模板解析、内容提取、内容放置、DOCX 渲染 |
| `src/docfit/harness/` | 评测、标准、coverage、报告、template-gap、AI 诊断包 |
| `standards/` | 已签收标准、contracts、expected、golden、profile case |
| `test_inputs/` | 仓库随附的可复现输入 |
| `test_outputs/` | 本地 eval、debug、workbench 输出；默认可再生成 |
| `docs/current/` | 长期维护的当前项目文档 |
| `docs/human/` | 讨论、审查、历史过程和迁移指针 |
| `docs/agents/` | 面向 coding agent 的长流程手册 |

完整目录约定只维护在 `docs/current/project-directory-structure.md`；根目录 `DIRECTORY_STRUCTURE.md` 是短入口。
