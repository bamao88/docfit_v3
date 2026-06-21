# 项目目录结构约定

Last updated: 2026-06-21

一句话结论：DocFit 的目录应该按“产品代码、签收标准、评测输入、评测输出、测试代码、文档”分工；仓库内样例材料统一进入 `test_inputs/`，所有可再生成的运行证据统一进入 `test_outputs/`。

## 当前真实实现

当前代码、标准路径、测试路径和 CLI 默认输出已经迁到目标结构：

| 当前目录 | 当前真实用途 | 当前处理 |
| --- | --- | --- |
| `test_inputs/template_generation/` | 学校源模板、学校格式要求、人工模板 review、模板生成单页调试输入 | 作为模板生成和模板理解输入来源 |
| `test_inputs/content_extraction/` | 学生源文档、人工内容 review、内容提取回归输入 | 作为内容提取和 e2e 输入来源 |
| `test_inputs/template_gap/` | 已生成模板 fixture，只用于单独测试 generated-template gap | 不作为 signed standard、golden 或真实生成器验收结果 |
| `test_outputs/eval_runs/` | eval run 报告、artifacts、AI 诊断包、Word 页面证据和历史 run 结果 | 默认可再生成；提交时只保留占位 |
| `test_outputs/debug/template_generation/` | 模板生成调试快照；当前模板生成 CLI 默认会写这里 | 默认可再生成；不放在 `tests/` |
| `test_outputs/debug/template_parsing/` | 模板解析/模板理解调试快照占位 | 默认可再生成；后续模板解析调试输出写这里 |
| `test_outputs/debug/content_extraction/` | 用户内容提取调试快照占位 | 默认可再生成；后续内容提取调试输出写这里 |
| `test_outputs/debug/content_placement/` | 内容放置调试快照占位 | 默认可再生成；后续放置调试输出写这里 |
| `test_outputs/debug/docx_rendering/` | DOCX 渲染调试快照占位 | 默认可再生成；后续渲染调试输出写这里 |
| `test_outputs/workbench/` | 人工整理草稿、临时最终 DOCX、历史 workbench 输出 | 默认可再生成；不作为验收标准 |

旧 `inputs/`、`reports/`、`out/` 和 `tests/template/` 不再是当前代码、标准或测试的默认入口；
如果本地还残留空目录或系统元数据，它们不代表产品目录职责。

## 和 `SPEC.md` 的关系

`SPEC.md` 是产品规范主来源。本文件继承 `SPEC.md` 第 5 节的 Harness-first 目录原则：

- 产品代码、harness、stage runner 在 `src/docfit/`；
- 可执行标准和 expected/golden 在 `standards/`；
- 阶段 artifacts、报告和 AI 诊断包必须作为一等公民保存；
- 测试代码在 `tests/`；
- 不能只保存最终 `.docx`，必须保存阶段证据和 verifier report。

本文件对旧 SPEC 目录命名做了一个收紧：旧的 `inputs/` 改名为 `test_inputs/`，
旧的 `reports/` / `out/` 归并为 `test_outputs/`。原因是 `inputs/` 容易被误解为
线上用户上传入口，`reports/` 容易被误解成只放人读报告；实际业务需要表达的是
“仓库内评测输入”和“评测/调试输出”。

## 目标结构

```text
docfit_v3/                         # 项目根目录；只放入口文件和一等公民目录
  README.md                        # 人类快速入口：项目是什么、当前怎么跑、重要指针
  SPEC.md                          # 产品规范主来源：阶段边界、门禁语义、目录原则
  STATUS.md                        # 当前真实状态：现在做到哪、下一步是什么、还卡什么
  pyproject.toml                   # Python 包、依赖、测试和命令行入口配置

  src/                             # 产品代码根目录；按业务层和阶段放可运行实现
    docfit/                        # Python 包根；`uv run docfit ...` 会进入这里
      cli/                         # 产品命令入口：`docfit eval ...`、`docfit convert ...`
      eval_harness/                # 评测/门禁产品层；当前代码名是 `harness/`，不是 pytest 测试
      stages/                      # 业务阶段实现；每个阶段独立产出 artifact 和状态
        template_generation/       # 模板生成：学校源模板 -> generated_template.docx 和生成过程证据
        template_parsing/          # 模板解析：模板/生成模板 -> template_artifact.json
        content_extraction/        # 内容提取：用户论文 -> student_content_artifact.json
        content_placement/         # 内容放置：模板理解 + 用户内容 -> placement_plan.json
        docx_rendering/            # Word 渲染：placement_plan -> final.docx 和 render_manifest.json
      conversion/                  # 转换编排：按门禁串起阶段；当前代码名是 `convert/`
      ooxml/                       # Word/OOXML 底层读取、包结构、字段、编号、样式工具
      core/                        # 通用模型、状态、读写、hash、时间等基础能力
      ai_diagnosis/                # AI 诊断包构造；只辅助分析，不决定 PASS/FAIL/UNKNOWN

  standards/                       # 已签收标准和 profile expected；决定“应该怎么判”
    schools/                       # 学校级签收标准、contracts、exceptions、golden
    eval_profiles/                 # 评测 profile、case 绑定、profile expected 产物

  test_inputs/                     # 仓库随附的可复现评测输入，不是线上用户上传目录
    template_generation/           # 学校源模板、学校要求、人工模板 review、模板生成小输入
    content_extraction/            # 用户/学生源论文、人工内容 review、内容提取回归输入
    template_gap/                  # 已生成模板 fixture；单独测试 template-gap 的被测 Word

  test_outputs/                    # eval、调试和本地验证跑出来的文件，默认可再生成
    eval_runs/                     # `docfit eval ...`、coverage、e2e、convert 的 run 目录
    debug/                         # 单阶段调试快照，例如模板生成逐步产物
      template_generation/         # 模板生成调试输出：生成计划、manifest、debug index
      template_parsing/            # 模板解析调试输出：template artifact、样式和单元识别快照
      content_extraction/          # 内容提取调试输出：可见内容台账和提取 artifact
      content_placement/           # 内容放置调试输出：placement plan 和去向检查
      docx_rendering/              # DOCX 渲染调试输出：render manifest、feature snapshot、打开检查证据
    workbench/                     # 人工整理包、临时 review packet、可丢弃草稿

  tests/                           # pytest 测试代码和极小必要 fixture
    unit/                          # 小范围函数、模型和纯逻辑测试
    contract/                      # 阶段合同、gate、报告形状、业务不变量测试
    e2e/                           # CLI 和端到端行为测试
    regression/                    # 已修复问题的回归测试

  docs/                            # 文档根目录；按读者和时效分层
    human/                         # 人类可读当前事实、流程主线、验收规则、目录约定
    agents/                        # 面向 coding agent 的长流程、工具和运行手册
    plans/                         # 阶段计划、历史方案、待执行方案，不冒充当前实现

  scripts/                         # 可复用维护脚本；批量生成、证据导出、基线绑定等
```

## 根目录职责

| 目录 | 做什么 | 不做什么 |
| --- | --- | --- |
| `src/docfit/` | 产品实现代码：CLI、评测门禁、阶段 runner、DOCX/OOXML 处理、转换编排 | 不放评测样例、标准、运行输出 |
| `standards/` | 已签收标准、contracts、exceptions、golden、profile expected | 不放用户源文件、学校源模板、调试输出 |
| `test_inputs/` | 仓库内可复现的评测/调试输入材料 | 不放 signed standard、expected、golden、运行报告 |
| `test_outputs/` | 本地或产品评测 run 产生的报告、artifacts、debug 快照、最终 DOCX、页面图像证据 | 不放源材料、签收标准、测试代码 |
| `tests/` | pytest 测试代码和极小必要 fixture | 不放成批运行输出、不放模板生成调试快照 |
| `docs/human/` | 人类可读的当前产品说明、流程主线、验收规则、目录约定 | 不放自动生成的大体量运行证据 |
| `docs/agents/` | 面向 coding agent 的长流程、工具、运行手册 | 不作为产品真相的默认入口 |
| `docs/plans/` | 阶段计划、历史方案、待执行计划 | 不冒充当前实现 |
| `scripts/` | 可复用脚本，例如导出证据、批量生成或迁移辅助 | 不放一次性手工输出 |

## `src/docfit/`

`src/docfit/` 放真正会被产品命令调用的代码。目录应该按业务层次命名，而不是按“这是测试还是调试”命名。

当前真实代码和目标命名的关系：

| 当前目录 | 当前真实职责 | 目标命名建议 |
| --- | --- | --- |
| `src/docfit/cli/` | Typer 命令入口，接收 `docfit eval ...` 和 `docfit convert ...` | 保持 `cli/` |
| `src/docfit/harness/` | 产品评测层：加载标准、跑 coverage、生成报告、做 template-gap、聚合 findings | 改名或文档命名为 `eval_harness/`，继续留在 `src/docfit/` |
| `src/docfit/stages/template_generate/` | 模板生成流程：学校源模板生成可填写模板和 manifest | `stages/template_generation/` |
| `src/docfit/stages/template_parse/` | 模板解析/理解：产出 `template_artifact.json` | `stages/template_parsing/` |
| `src/docfit/stages/content_extract/` | 用户内容提取：产出 `student_content_artifact.json` | `stages/content_extraction/` |
| `src/docfit/stages/placement/` | 内容放置规划：产出 `placement_plan.json` | `stages/content_placement/` |
| `src/docfit/stages/render/` | Word 渲染：产出 `final.docx`、`render_manifest.json`、feature snapshot | `stages/docx_rendering/` |
| `src/docfit/convert/` | 转换/e2e 编排，把阶段和门禁串起来 | `conversion/` |
| `src/docfit/ooxml/` | DOCX/OOXML 底层能力 | 保持 `ooxml/` |
| `src/docfit/core/` | 通用状态、模型、IO、hash | 保持 `core/` |
| `src/docfit/ai_rca/` | AI 诊断包 | `ai_diagnosis/` |

四个验收主阶段仍然是：

| 阶段 | 当前代码 | 产物 | 失败说明什么 |
| --- | --- | --- | --- |
| 模板理解/模板侧阶段 | `template_generate` + `template_parse` | `generated_template.docx`、`template_artifact.json`、模板生成 manifest、template-gap report | 系统还不能证明学校模板被正确理解或生成模板满足学校标准 |
| 用户内容提取 | `content_extract` | `student_content_artifact.json` | 系统还不能证明用户可见内容被完整提取 |
| 内容放置 | `placement` | `placement_plan.json` | 系统还不能证明每份用户内容都有正确去向 |
| DOCX 渲染 | `render` | `final.docx`、`render_manifest.json`、feature snapshot | 系统还不能证明最终 Word 按已验证计划生成 |

### Harness 和 tests 的区别

| 项 | `src/docfit/harness/` | `tests/` |
| --- | --- | --- |
| 它是什么 | 产品里的评测/门禁执行层 | pytest 测试代码 |
| 谁调用它 | `docfit eval ...`、`docfit convert ...`、coverage 和报告流程 | 开发者或 CI 运行 `uv run pytest` |
| 运行时是否需要 | 需要；没有它就没有 eval harness、报告和 gate | 不需要；线上或产品命令不依赖 pytest 测试文件 |
| 输出什么 | `summary.json`、`pm_report.md`、findings、coverage、template-gap report、AI diagnosis packet | 测试通过/失败结果 |
| 应不应该放一起 | 不应该混放；harness 是被测产品能力，tests 是验证 harness 和 stages 的测试 | 不应该承载产品运行输出 |

所以 `harness` 不应该搬到 `tests/`。更准确的做法是：把 `src/docfit/harness/` 在目标结构里明确命名为 `src/docfit/eval_harness/`，让它看起来不像“测试目录”，但仍保留在产品代码里。

## `scripts/`

`scripts/` 放可重复运行的维护脚本。它们不是产品 CLI 的公开入口，也不是测试代码；
如果脚本会写 standards 或 expected，必须在脚本说明和运行结果里明确它是基于什么人工签收证据写入的。

当前脚本：

| 脚本 | 做什么 | 主要输入 | 主要输出 | 风险边界 |
| --- | --- | --- | --- | --- |
| `create_bootstrap_fixtures.py` | 生成 Bootstrap demo 的学校模板、学生样例和相关 bootstrap fixture | 代码内的 Bootstrap profile 配置 | 默认写 `test_outputs/workbench/bootstrap-fixtures`；显式允许时可写 repo 内 `test_inputs/` 和 standards 相关文件 | 会影响基础 fixture；不能用它自动更新真实学校标准 |
| `create_real_core_baseline_review_packet.py` | 从 real-core 三校三学生配置生成待人工 review 的 baseline 草稿包 | `REAL_CORE_SCHOOLS`、`REAL_CORE_STUDENTS`、当前源材料路径 | 默认写 `test_outputs/workbench/real-core-v0-baseline-review` | 产物是待 review 草稿，不是已签收标准 |
| `create_real_core_reviewed_baselines.py` | 把已人工 review 的 source-fact packet 绑定进 real-core standards 和 profile expected | 默认读取 `docs/human/real-core-v0-review-packet.md` | 写 `standards/schools/**` 和 `standards/eval_profiles/real-core-v0/expected/**` | 会改签收相关材料；只能在人工 review 已完成且变更理由明确时运行 |
| `export_real_core_word_evidence.py` | 用 Microsoft Word 导出 real-core 成品页面图像证据，或校验已有证据并刷新报告 | 默认读取 `test_outputs/eval_runs/real-core-v0/<case_id>/final.docx`；目标应迁到 `test_outputs/eval_runs/**` | 页面 PNG、`word_image_evidence.json`、刷新后的 case 报告 | 依赖本机 Microsoft Word；生成的是 evidence，不是自动 PASS 依据 |

脚本目录规则：

- 脚本本身可以保留在 `scripts/`，脚本输出必须写到 `test_outputs/`、`standards/` 或显式传入的目标目录。
- 写 `standards/` 的脚本必须要求明确人工签收输入，不能从当前失败输出自动生成标准。
- 只生成调试或 review 草稿的脚本默认写 `test_outputs/workbench/`。
- 导出页面图像、PDF、截图、manifest 这类运行证据的脚本默认写 `test_outputs/eval_runs/` 对应 case 目录。
- `scripts/__pycache__/` 是 Python 缓存，不属于项目源文件。

## `test_inputs/`

`test_inputs/` 表示“仓库随附的评测输入”，不是线上用户上传目录。这里的文件可以来自真实学校、真实学生、人工 review 或专门构造的调试样例，但它们进入仓库后都服务于可复现评测。

只保留两层：

```text
test_inputs/<阶段用途>/<文件名>
```

目标子目录：

| 子目录 | 放什么 | 文件命名建议 |
| --- | --- | --- |
| `template_generation/` | 学校原始模板、学校格式要求、人工模板 review、模板生成单页调试输入 | `<school>-source-template.docx`、`<school>-template-review.txt`、`unit-copy-01.docx` |
| `content_extraction/` | 用户/学生原始论文、人工内容 review、内容提取回归输入 | `<student-id>-source.docx`、`<student-id>-content-review.md` |
| `template_gap/` | 已经生成好的 `generated_template.docx` fixture，用来单独测试生成模板差距检查 | `<profile>-<school>-generated-template.docx` |

边界：

- 学校原始模板属于 `template_generation/`，不能直接拿来冒充生成结果。
- 用户论文属于 `content_extraction/`，不能混进模板生成输入。
- 被测生成模板 fixture 属于 `template_gap/`，它不是 signed standard，也不是 golden。
- expected、golden、signed standard 仍然只放 `standards/`。

## `test_outputs/`

`test_outputs/` 表示“系统跑出来的东西”。它可以被删除后重新生成；如果某个输出被人工签收为标准，必须复制或迁移到 `standards/` 并补齐签收记录，不能继续留在 `test_outputs/` 里当标准。

目标子目录：

| 子目录 | 放什么 | 示例 |
| --- | --- | --- |
| `eval_runs/` | 正式 eval / coverage / e2e run 输出 | `eval_runs/e2e-real-core-v0-hunannongye-student-003/` |
| `debug/` | 单阶段调试快照；下面按阶段分目录 | `debug/template_generation/20260621T123000/` |
| `workbench/` | 人工整理包、临时 review packet、可丢弃草稿 | `workbench/real-core-v0-baseline-review/` |

`debug/` 阶段目录：

| 子目录 | 放什么 | 当前状态 |
| --- | --- | --- |
| `debug/template_generation/` | 模板生成逐步证据，例如 source tree、规则发现、生成计划、generated_template 和 manifest | 已使用；`template-generate` 默认写这里 |
| `debug/template_parsing/` | 模板解析/模板理解临时 artifact、字段识别和单元识别快照 | 已预建占位 |
| `debug/content_extraction/` | 用户可见内容台账、unsupported 内容和提取 artifact 调试快照 | 已预建占位 |
| `debug/content_placement/` | placement plan、内容去向和放置失败定位调试快照 | 已预建占位 |
| `debug/docx_rendering/` | render manifest、feature snapshot、最终 DOCX 打开检查和渲染证据 | 已预建占位 |

新增阶段调试输出时，沿用 `debug/<stage_name>/` 的结构：目录占位和 `.gitkeep`
可以提交，具体运行产物默认可删除、可再生成，不能当作 signed standard、expected 或 golden。

每个 eval run 目录内部可以继续按报告类型分层：

```text
test_outputs/eval_runs/<run_id>/
  summary.json
  pm_report.md
  findings.json
  issue_clusters.json
  artifacts/
  evidence/
  ai/
  preview/
  final.docx
```

边界：

- `artifacts/` 是本次 run 的机器证据，不是全局标准。
- `evidence/` 是本次 run 的页面图像、diff、截图等证据，不是输入。
- `ai/` 是辅助诊断材料，不能改变 `PASS` / `FAIL` / `UNKNOWN`。
- `debug/` 里的 step 文件帮助定位问题，不参与正式 gate，除非 run 报告显式引用。

## `standards/`

`standards/` 是“应该怎么判”的来源。它不是输入目录，也不是输出目录。

| 子目录 | 放什么 |
| --- | --- |
| `standards/schools/<school_id>/<version>/` | 学校签收标准、合同、例外、golden |
| `standards/eval_profiles/<profile_id>/` | profile 级 case、expected、覆盖要求 |

规则：

- 不能因为当前输出变化自动更新 standards。
- `UNKNOWN` 或 `FAIL` 不能通过改 standards 被消掉，除非有人工签收证据和变更记录。
- `template_artifact.json`、`template_generation_manifest.json`、`template_gap_report.json` 都不是标准。

## `tests/`

`tests/` 只表达“检查代码怎么跑”，不承载产品运行输出。

| 子目录 | 用途 |
| --- | --- |
| `tests/unit/` | 小范围函数或模型测试 |
| `tests/contract/` | 阶段合同、gate、报告形状和业务不变量测试 |
| `tests/e2e/` | CLI 和端到端行为测试 |
| `tests/regression/` | 已修复问题的回归测试 |

规则：

- 测试需要的小型 fixture 可以放在 `tests/fixtures/`，但大输入应放 `test_inputs/`。
- 测试运行产生的输出必须写到 pytest `tmp_path` 或 `test_outputs/debug/`，不能写回 `tests/`。
- 模板生成调试快照默认写 `test_outputs/debug/template_generation/`，不能写回 `tests/`。

## 迁移顺序

| 顺序 | 做什么 | 成功证明 |
| --- | --- | --- |
| 1 | 新建 `test_inputs/`、`test_outputs/` | 已完成：README 和 `.gitignore` 说明新边界 |
| 2 | 把 `inputs/**` 按身份迁到 `test_inputs/<阶段用途>/` | 已完成：`src/docfit/harness/profiles.py`、`standards/**`、README 和测试路径同步更新 |
| 3 | 把 CLI 默认输出和调试输出改到 `test_outputs/` | 已完成：`template-generate` 不再写 `tests/template/`，默认写 `test_outputs/debug/template_generation/`；其他阶段 debug 目录已预建 |
| 4 | 迁移或删除旧 `reports/**`、`out/**` 中可再生成内容 | 已完成：旧运行证据迁到 `test_outputs/eval_runs/` 和 `test_outputs/workbench/` |
| 5 | 清理旧目录入口 | 验证中：旧路径不能再被代码、标准或当前文档当成默认入口引用 |

## 迁移时不能做的事

- 不能把路径迁移当成 standards 语义变更。
- 不能自动更新 golden、expected 或 signed standard。
- 不能把 `template_gap` fixture 当作真实 template-generation 输出验收。
- 不能把运行输出移进 `tests/` 或 `standards/`。
- 不能只改 README，不改代码路径和测试断言就声称迁移完成。
