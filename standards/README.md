# Standards 目录说明

一句话结论：`standards/` 只放“如何判定正确”的已签收标准和通用检查契约；**当前 active 范围只有模板阶段**。学生内容、放置和渲染标准目录保留为未来结构，暂不新增签收标准。

## 当前启用范围

| 范围 | 状态 | 说明 |
| --- | --- | --- |
| `targets/<target>/v1/template_generation/*.standard.yaml` | active | 当前正在制作和接入的 T1-T5 模板生成阶段标准 |
| `targets/<target>/v1/template_quality/final_template.expected.yaml` | active | 当前模板最终质量检查标准 |
| `students/<student>/...` | reserved | 学生内容提取流程和产物模型未定义清楚前，不新增或改判标准 |
| `cases/<target>__<student>/.../placement` | reserved | 内容放置依赖学生内容提取，暂不制作标准 |
| `cases/<target>__<student>/.../render` | reserved | 最终渲染依赖放置计划，暂不制作标准 |

reserved 目录里的历史文件只能作为后续设计参考，不能说明当前学生链路已经可验收。

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
      template_generation/t1_document_facts.standard.yaml
      template_generation/t2_unit_pagination.standard.yaml
      template_generation/t3_element_policy.standard.yaml
      template_generation/t4_global_layout.standard.yaml
      template_generation/t5_template_spec.standard.yaml
      template_quality/final_template.expected.yaml
      golden/
      exceptions.yaml
  students/
    <student_id>/v1/content_extract/          # reserved until content extraction flow is defined
      student_content_artifact.expected.yaml
  cases/
    <target_id>__<student_id>/v1/             # reserved until placement/render flows are defined
      placement/placement_plan.expected.yaml
      render/feature_snapshot.expected.json
```

## 文件职责

| 位置 | 做什么 | 不做什么 |
| --- | --- | --- |
| `contracts/` | 保存跨学校复用的阶段检查契约 | 不保存学校原始 Word 或某次运行输出 |
| `targets/<target>/v1/target.standard.yaml` | 目标模板标准入口，登记来源、contract、基线和覆盖要求 | 不证明生成模板已经通过 |
| `targets/<target>/v1/template_generation/t1_document_facts.standard.yaml` | T1 源 DOCX 事实解析标准 | 不承载单元、元素策略、全局版式或 `template_spec` 合并标准 |
| `targets/<target>/v1/template_generation/t2_unit_pagination.standard.yaml` | T2 单元识别、单元顺序、边界范围和分页归属标准 | 不兼容旧结构发现标准入口 |
| `targets/<target>/v1/template_generation/t3_element_policy.standard.yaml` | T3 `keep/fill/delete` 一级动作 gold 和 source/run trace；细粒度 policy 只作输出兼容与诊断 | 不签收 fill/manual/generated 子类型准确率，不负责全局页面规则或 Word 构建执行 |
| `targets/<target>/v1/template_generation/t4_global_layout.standard.yaml` | T4 页面、分节、页眉页脚、页码和编号规则标准 | 不负责元素策略或 Word 构建执行 |
| `targets/<target>/v1/template_generation/t5_template_spec.standard.yaml` | T5 `template_spec` 合并、unit-element 绑定和 unit-section 绑定标准 | 不执行 Word 修改，不替代 T6 构建或最终 gap |
| `targets/<target>/v1/template_quality/final_template.expected.yaml` | 最终生成模板的质量期望 | 不等于 `generated_template.docx` 的真实内容证明 |
| `students/<student>/v1/content_extract/*.expected.yaml` | 未来学生内容提取标准位置 | 当前流程未定义清楚前，不新增或改判签收标准 |
| `cases/<target>__<student>/v1/placement/*.expected.yaml` | 未来内容放置标准位置 | 当前流程未定义清楚前，不新增或改判签收标准 |
| `cases/<target>__<student>/v1/render/*.expected.json` | 未来渲染标准位置 | 当前流程未定义清楚前，不新增或改判签收标准 |

## 门禁规则

- 缺标准、缺输入、缺输出或缺 verifier 都不能通过；结果应为 `UNKNOWN`。
- `*.expected.yaml` / `*.expected.json` / `*.standard.yaml` 是人工签收后的期望或标准，不允许为了让测试变绿自动更新。
- `target.standard.yaml` 可以登记 `evidence_baselines.template_generation_stages` 字段；T1/T2/T3/T4/T5 使用 `t1_document_facts`、`t2_unit_pagination`、`t3_element_policy`、`t4_global_layout`、`t5_template_spec` 五个专用标准入口，不再登记旧数字阶段标准。
- 当前不要为学生内容、placement 或 render 新增签收标准；等对应流程和产物模型明确后，再启用 `standards/students` 或 `standards/cases`。
- `eval_profiles/` 只定义要跑哪些学校、学生和 case；expected 本体必须放在对应 `standards/` 子目录。当前 active profile 重点仍应围绕模板阶段。
