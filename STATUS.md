# DocFit Status

Last updated: 2026-06-27

一句话结论：当前工程主线只做模板阶段。学生内容提取、内容放置和最终 DOCX 渲染流程还没有定义清楚，因此对应标准暂不制作，也不作为当前 gate 目标。

## Current Focus

当前 active 范围：

```text
学校原始模板 Word
  -> template-generate
  -> document_facts.json
  -> unit_map.yaml
  -> element_spec.yaml
  -> global_spec.yaml
  -> template_spec.yaml
  -> fillable_template.docx + build_manifest.json
  -> verification_report.json
  -> template-gap / template-generation standard judge
```

当前不做：

```text
学生内容提取标准
内容放置标准
最终 DOCX 渲染标准
完整学生论文转换 gate
```

原因：学生内容提取的流程、阶段边界、产物模型和验收口径尚未实现清楚。现在制作学生或 case 标准会把历史 fixture 当成事实来源，风险太高。

## Current State

- 三校模板生成阶段标准已按 T1-T5 拆分并落在 `standards/targets/<target_id>/v1/template_generation/`。
- `template-generate` 正常只读取学校原始模板 Word，不读取学校签收标准。
- `template-generate` 已能输出 `document_facts.json`、`unit_map.yaml`、`element_spec.yaml`、`global_spec.yaml`、`template_spec.yaml`、`fillable_template.docx`、`build_manifest.json` 和 `verification_report.json`。
- `template-gap` 继续用于检查被测生成模板和 `template_quality/final_template.expected.yaml` 的差距。
- 模板生成标准裁判模块已完成文档规划，位置见 `docs/plans/template-parse-refactor-standard-judge-issue-01-run-bundle-stage-verifiers.md`。
- 目录结构约定已收敛到 `docs/current/project-directory-structure.md`；历史文档中的旧路径只作历史上下文。

## Next Action

1. 实现模板生成标准质量报告：
   `docfit eval template-generation-standard-quality`

2. 实现模板生成标准裁判：
   `docfit eval template-generation-judge`

3. 先让标准裁判读取已有 `template-generate` run bundle，输出：

   ```text
   template_generation_run_bundle.json
   template_generation_stage_checks.json
   template_generation_judge_report.json
   template_generation_judge_report.md
   ```

4. 按 T1-T5 补阶段 verifier。T2 现有 audit 可以复用，但不要让 T2 脚手架主导整个标准裁判模块设计。

5. 标准裁判闭环后，再继续修模板 gap 中仍暴露的样式、页码、section、页面和生成机制问题。

## Deferred

这些目录和历史材料可以保留，但当前不作为标准制作入口：

- `standards/students/**`
- `standards/cases/**/placement/**`
- `standards/cases/**/render/**`
- `inputs/students/**`
- 历史 real-core 学生/case fixture

启用这些范围前，必须先明确：

- 学生内容提取阶段的输入、输出和字段语义；
- 内容 ledger 的最小标准；
- 放置计划如何表达每段学生内容的去向；
- 渲染 manifest 如何证明最终 Word 忠实执行放置计划；
- 哪些内容属于学校模板，哪些内容属于学生源文档。

## Verification

当前模板阶段常用命令：

```bash
uv run docfit eval template-generate \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --out runs/template_generation/hunannongye/eval_runs/template_generate
```

```bash
uv run docfit eval template-gap \
  --school hunannongye \
  --generated-template runs/template_generation/hunannongye/eval_runs/template_generate/fillable_template.docx \
  --out runs/eval/template_gap/hunannongye/template_generate
```

标准裁判实现后，期望命令：

```bash
uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run runs/template_generation/hunannongye/eval_runs/template_generate \
  --out runs/eval/template_generation_judge/hunannongye/template_generate
```
