# Standards 目录说明

一句话结论：`standards/` 只放“如何判定正确”的已签收标准和通用检查契约；原始输入在 `inputs/`，运行输出在 `runs/`，评测组合配置在顶层 `eval_profiles/`。

## 当前结构

```text
standards/
  contracts/
    template.contract.json
    template_generation.contract.json
    template_quality.contract.json
    student_content.contract.json
    placement.contract.json
    render.contract.json
  targets/
    <target_id>/v1/
      target.standard.yaml
      template_generation/*.expected.yaml
      template_generation/t2_unit_pagination.standard.yaml
      template_quality/final_template.expected.yaml
      golden/
      exceptions.yaml
  students/
    <student_id>/v1/content_extract/
      student_content_artifact.expected.yaml
  cases/
    <target_id>__<student_id>/v1/
      placement/placement_plan.expected.yaml
      render/feature_snapshot.expected.json
```

## 文件职责

| 位置 | 做什么 | 不做什么 |
| --- | --- | --- |
| `contracts/` | 保存跨学校复用的阶段检查契约 | 不保存学校原始 Word 或某次运行输出 |
| `targets/<target>/v1/target.standard.yaml` | 目标模板标准入口，登记来源、contract、基线和覆盖要求 | 不证明生成模板已经通过 |
| `targets/<target>/v1/template_generation/*.expected.yaml` | 模板生成通用阶段的已签收期望 | 不替代阶段 verifier |
| `targets/<target>/v1/template_generation/t2_unit_pagination.standard.yaml` | T2 单元识别、单元顺序、边界范围和分页归属标准 | 不承载 T1/T3/T4/T5 标准，也不兼容旧结构发现标准入口 |
| `targets/<target>/v1/template_quality/final_template.expected.yaml` | 最终生成模板的质量期望 | 不等于 `generated_template.docx` 的真实内容证明 |
| `students/<student>/v1/content_extract/*.expected.yaml` | 学生源文档可见内容的已签收期望 | 不保存学生原始 Word |
| `cases/<target>__<student>/v1/placement/*.expected.yaml` | 组合 case 的内容放置期望 | 不保存实际 `placement_plan.json` 运行产物 |
| `cases/<target>__<student>/v1/render/*.expected.json` | 组合 case 的渲染特征期望 | 不保存实际渲染 DOCX |

## 门禁规则

- 缺标准、缺输入、缺输出或缺 verifier 都不能通过；结果应为 `UNKNOWN`。
- `*.expected.yaml` / `*.expected.json` 是人工签收后的期望，不允许为了让测试变绿自动更新。
- `target.standard.yaml` 可以登记 `evidence_baselines.template_generation_stages` 字段；T2 使用 `t2_unit_pagination: template_generation/t2_unit_pagination.standard.yaml`，不再登记旧结构发现阶段标准。
- `eval_profiles/` 只定义要跑哪些学校、学生和 case；expected 本体必须放在 `standards/targets`、`standards/students` 或 `standards/cases`。
