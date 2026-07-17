# DocFit v3

一句话结论：DocFit v3 的长期目标是把学生论文 Word 转成目标学校要求的 Word；**当前工程和标准制作只推进模板阶段**。

## 这个项目做什么

长期产品会接收两类业务输入：

- 目标学校的 Word 模板或模板要求；
- 学生已经写好的 Word 论文。

但当前阶段只处理第一类：目标学校模板。学生内容提取、内容放置和最终论文渲染还没有清晰实现流程，因此对应标准也暂不制作，不能用当前仓库里的历史学生/case 材料冒充已定义标准。

## 当前启用范围

| 范围 | 当前状态 | 说明 |
| --- | --- | --- |
| 模板解析 / 模板生成 | active | 从学校原始模板 Word 产出 `01_document_facts.json`、`02_unit_map.yaml`、`03_element_spec.yaml`、`04_global_spec.yaml`、`05_template_spec.yaml`、`06.1_fillable_template.docx` |
| 模板质量检查 | active | 用 `template-gap` 和后续标准裁判对照模板阶段标准 |
| 学生内容提取 | deferred | 流程和阶段边界未实现清楚，暂不制作签收标准 |
| 内容放置 | deferred | 依赖学生内容提取和模板 slot 语义，暂不制作签收标准 |
| DOCX 渲染 | deferred | 依赖内容放置计划，暂不制作签收标准 |

长期仍可以扩展为“模板解析、内容提取、内容放置、DOCX 渲染”四段产品链路；只是当前不要把后三段当成正在验收的工程主线。

## 评测是什么

评测驱动开发是这个项目的开发和验收方式，不是业务流程本身。

Eval Harness 负责检查已启用范围的产物，输出 `PASS` / `FAIL` / `UNKNOWN`：

- `PASS`：证据足够，并且产物满足标准；
- `FAIL`：标准明确，产物违反标准；
- `UNKNOWN`：缺标准、缺检查器、缺证据或输入不可支持。

AI 只能读报告、解释问题、建议下一步，不能裁定通过或失败。

## 当前真实状态

当前真实主线是模板阶段：

- 模板生成支撑流程能从学校原始模板 Word 产出阶段产物和 `06.1_fillable_template.docx`。
- 三校模板生成 T1-T5 阶段标准已经准备好，但标准裁判代码还在规划/接入中。
- 学生内容、放置和渲染相关历史 fixture 可以保留为背景材料，但当前不作为标准制作对象。

## 常用命令

安装依赖：

```bash
uv sync
```

运行测试：

```bash
uv run pytest
```

运行模板生成：

```bash
RUN_ROOT=test_outputs/debug/template_generation/manual_hunannongye
uv run docfit template generate \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --out "$RUN_ROOT/eval_runs/template_generate"
```

模板生成和全流程默认 `--ai off`；需要时显式用 `--ai live`。单独调试
T2/T3/T4 AI 观察时，使用默认 live 且优先复用已有 run 的阶段入口：

```bash
uv run docfit template stage t2 \
  --run "$RUN_ROOT/eval_runs/template_generate" \
  --out /private/tmp/docfit_observe_t2
```

具体的 T3 上游复用和 T4 视觉 API 要求见 `docs/current/template-generation.md`。

运行模板差距检查：

```bash
RUN_ROOT=test_outputs/debug/template_generation/manual_hunannongye
uv run docfit eval template-gap \
  --school hunannongye \
  --generated-template "$RUN_ROOT/eval_runs/template_generate/06.1_fillable_template.docx" \
  --out "$RUN_ROOT/eval_runs/template_gap"
```

## 继续读哪里

| 你要了解什么 | 入口 |
| --- | --- |
| 当前主线和流程图 | `docs/current/README.md` |
| 当前状态、下一步和阻塞项 | `STATUS.md` |
| 当前启用范围、门禁和 AI 边界 | `docs/current/contracts-and-gates.md` |
| 模板生成支撑流程 | `docs/current/template-generation.md` |
| 模板生成各阶段的职责、依赖和输入输出契约 | `docs/current/template-generation-stage-contracts.md` |
| 新增文件放哪里 | `DIRECTORY_STRUCTURE.md` |

目录规则只是新增文件时的参考，不是项目主线。
