# DocFit v3

一句话结论：DocFit v3 的业务是把学生论文 Word 转成目标学校要求的 Word；业务流程只有四个阶段：模板解析、内容提取、内容放置、DOCX 渲染。

## 这个项目做什么

DocFit 接收两类业务输入：

- 目标学校的 Word 模板或模板要求；
- 学生已经写好的 Word 论文。

它要输出一份目标学校格式的 Word。正确性不是“文件能打开”或“看起来差不多”，而是四个业务阶段都能说明自己做了什么、产出了什么、有没有丢内容、有没有证据不足。

## 业务四阶段

| 阶段 | 输入 | 输出 | 失败说明什么 |
| --- | --- | --- | --- |
| 1. 模板解析 | 学校 Word 模板 | `template_artifact.json` | 系统还没有正确理解目标学校模板结构、样式、区域和可填写位置 |
| 2. 内容提取 | 学生源 Word | `student_content_artifact.json` | 系统还不能证明学生可见内容被完整识别，没有静默丢弃 |
| 3. 内容放置 | 模板理解结果 + 学生内容 | `placement_plan.json` | 系统还不知道每段学生内容应该进入模板里的哪个位置 |
| 4. DOCX 渲染 | 放置计划 + 模板底稿 | `final.docx`、`render_manifest.json` | 系统还不能证明最终 Word 是按放置计划生成的 |

`docfit convert` 只是把这四个阶段串起来。任一阶段 `FAIL` 或 `UNKNOWN`，都不能宣称转换成功。

## 评测是什么

评测驱动开发是这个项目的开发和验收方式，不是业务流程本身。

Eval Harness 负责检查四个业务阶段的产物，输出 `PASS` / `FAIL` / `UNKNOWN`：

- `PASS`：证据足够，并且产物满足标准；
- `FAIL`：标准明确，产物违反标准；
- `UNKNOWN`：缺标准、缺检查器、缺证据或输入不可支持。

AI 只能读报告、解释问题、建议下一步，不能裁定通过或失败。

## 当前真实状态

Bootstrap demo 链路能跑通。`real-core-v0` 真实学校链路现在能生成 Word 和报告，但完整业务验收仍会返回 `FAIL` / `UNKNOWN`。

当前开发重点不是继续整理目录，也不是只产出一个 Word 文件，而是修真实工程链路：

1. 内容提取：识别摘要、关键词、参考文献、附录、致谢等章节角色，并排除旧封面、旧目录这类源文档格式内容。
2. 内容放置：把每段学生内容放到目标学校模板的具体位置，不能全部放到 `slot_body_start` 或追加到末尾。
3. DOCX 渲染：最终 Word 不能带模板说明文字，学生内容也不能只是追加在生成模板后面。

模板生成和 `template-gap` 是当前模板侧的支撑流程：它们帮助准备和检查可填写模板，但不改变“业务只有四阶段”这个边界。

## 常用命令

安装依赖：

```bash
uv sync
```

运行测试：

```bash
uv run pytest
```

运行 Bootstrap e2e：

```bash
uv run docfit eval e2e \
  --school demo-school \
  --student inputs/students/bootstrap-demo-pass/raw/source_document.docx \
  --out runs/eval/bootstrap_pass
```

运行 real-core-v0 coverage gate：

```bash
uv run docfit eval coverage \
  --profile real-core-v0 \
  --out /tmp/docfit_real_core_coverage
```

## 继续读哪里

| 你要了解什么 | 入口 |
| --- | --- |
| 当前主线和流程图 | `docs/current/README.md` |
| 当前状态、下一步和阻塞项 | `STATUS.md` |
| 四阶段产物、门禁和 AI 边界 | `docs/current/contracts-and-gates.md` |
| 模板生成支撑流程 | `docs/current/template-generation.md` |
| docx4j 旁路诊断 | `docs/current/docx4j-diagnostics.md` |
| 新增文件放哪里 | `DIRECTORY_STRUCTURE.md` |

目录规则只是新增文件时的参考，不是项目主线。
