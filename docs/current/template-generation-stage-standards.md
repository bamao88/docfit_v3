# 模板生成阶段标准准备说明

Last updated: 2026-06-28

一句话结论：当前 real-core-v0 的三校模板生成阶段标准已经拆成 T1 到 T5 的阶段专用标准文件，并已接入 `template-generation-judge` gate。它们是阶段标准裁判口径，不是某一次运行产物，也不是代码里 `07_verification_report.json` 的替代品。

## 当前版本

本页记录这一版标准：

| 项 | 当前口径 |
| --- | --- |
| profile | `real-core-v0` |
| targets | `hunannongye`、`nannong-undergraduate`、`pku-graduate` |
| template version | `v1` |
| 标准目录 | `standards/targets/<target_id>/v1/template_generation/` |
| 登记入口 | `standards/targets/<target_id>/v1/target.standard.yaml#/evidence_baselines/template_generation_stages` |
| 旧入口兼容 | 不兼容；旧 `01_source_parse.expected.yaml`、`02_structure_discovery.expected.yaml`、`03_generation_model.expected.yaml`、`04_plan_build.expected.yaml`、`05_action_execution.expected.yaml` 已移除 |
| verifier 状态 | `configured` / `gate_enabled=true`，表示 real-core T1-T5 已纳入阶段标准裁判 gate |

每所学校现在都只有这五个模板生成阶段标准：

```text
template_generation/
  t1_document_facts.standard.yaml
  t2_unit_pagination.standard.yaml
  t3_element_policy.standard.yaml
  t4_global_layout.standard.yaml
  t5_template_spec.standard.yaml
```

## 准备方式

这一版标准按下面的顺序准备。

1. 先确定阶段边界。

   T1 只保存源 DOCX 事实；T2 才识别单元和分页；T3 才判断元素策略；T4 只处理全局页面、分节、页眉页脚、页码和编号；T5 合并成 `template_spec`。T1 不允许输出 `unit_id`、`policy`、`confidence`、`likely_unit_heading` 等语义判断字段。

2. 再确定文件命名。

   标准文件使用阶段语义名，不再使用旧数字 expected 入口。这样以后看到文件名就知道它只覆盖哪个阶段：

   | 旧入口 | 新入口 |
   | --- | --- |
   | `01_source_parse.expected.yaml` | `t1_document_facts.standard.yaml` |
   | `02_structure_discovery.expected.yaml` | `t2_unit_pagination.standard.yaml` |
   | `03_generation_model.expected.yaml` | `t3_element_policy.standard.yaml` |
   | `04_plan_build.expected.yaml` | `t4_global_layout.standard.yaml` |
   | `05_action_execution.expected.yaml` | `t5_template_spec.standard.yaml` |

3. 再绑定人工来源。

   每份标准都保留 `review_metadata` 和 `accepted_source_facts`，绑定人工 review packet、学校源模板 DOCX hash、学校 review section hash，以及上游 `template_quality/final_template.expected.yaml`。这些字段证明标准从哪里来，不允许从当前运行结果自动反写。

4. 再写阶段 expected。

   每份标准只写本阶段需要裁判的内容。T2 到 T5 需要保留 `expected.unit_order`，并和 `final_template.expected.yaml#/expected/units` 的顺序一致。T1 不写 unit order，因为它还不能产生单元语义。

5. 最后更新登记和测试。

   三校 `target.standard.yaml` 只登记新入口。合同测试检查新文件存在、旧文件不存在、`legacy_compatibility: false`、`verifier_state: configured`、`gate_enabled: true`，并用 baseline validator 检查标准文件自身可解析。

## 给哪些环节用

这些标准给后续阶段 verifier、聚合报告和人工排查使用。它们不是普通模板生成流程的输入。

| 标准 | 对应产物 | 后续使用者 | 用途 |
| --- | --- | --- | --- |
| `t1_document_facts.standard.yaml` | `01_document_facts.json` | T1 verifier、T2/T4 调试、人工 first_bad_stage 排查 | 判断源 DOCX 事实是否完整、可定位，并且没有混入 T2/T3 语义判断 |
| `t2_unit_pagination.standard.yaml` | `02_unit_map.yaml` | T2 verifier、T3/T5、最终 gap 归因 | 判断单元识别、单元顺序、边界范围、source_seq 归属和分页口径 |
| `t3_element_policy.standard.yaml` | `03_element_spec.yaml` | T3 verifier、T5/T6、人工策略排查 | 判断元素 policy、fill_source、manual_semantics、generated.field_type 和 source trace |
| `t4_global_layout.standard.yaml` | `04_global_spec.yaml` | T4 verifier、T5/T6、页面规则排查 | 判断 section profile、page numbering、header/footer、numbering 和全局布局证据 |
| `t5_template_spec.standard.yaml` | `05_template_spec.yaml` | T5 verifier、T6 builder、后续 placement/render 包装视图 | 判断 unit、element、global 三类信息是否正确合并，section 绑定和 review flags 是否保留 |

当前正常的 `template-generate` 业务流程不读取这些标准。业务流程只接受学校原始模板 Word，产出 `01_document_facts.json`、`02_unit_map.yaml`、`03_element_spec.yaml`、`04_global_spec.yaml`、`05_template_spec.yaml`、`06.1_fillable_template.docx` 和 `06.2_build_manifest.json`。

阶段化评测入口读取同一次 run 里的产物，再按 `target.standard.yaml` 找到对应标准。缺产物、缺标准、hash 对不上或 verifier 未配置时，都应该输出 `UNKNOWN`，不能自动重跑生成器补证据。

## 标准质量衡量

这里的“标准质量衡量”指的是标准文件本身够不够资格当裁判。它不评价某一次运行产物是否通过。

当前已有内容、尚未实现内容、补全顺序、调用方式和命名规范，见 `docs/current/template-generation-stage-standard-quality.md`。

一份阶段标准至少要满足这些质量点：

| 质量点 | 要证明什么 | 当前检查方式 |
| --- | --- | --- |
| 来源绑定 | 标准来自已知人工 review、源模板和 final template 标准 | `review_metadata`、`accepted_source_facts`、sha256 字段 |
| 阶段边界清晰 | 只裁判本阶段，不越权判断下游内容 | `stage_id`、`artifact_under_test`、`scope`、阶段 contract |
| 旧入口不兼容 | 后续不会 fallback 到旧 expected 文件 | 文件删除、`legacy_compatibility: false`、合同测试 |
| 可执行维度存在 | 未来 verifier 能找到最小比较维度 | `dimensions[]` 和 `validate_baseline_document` |
| 三校登记一致 | 三校都能从 `target.standard.yaml` 找到同名阶段标准 | `tests/contract/test_real_core_baseline_harness.py` |
| T1 事实边界 | T1 不输出语义判断字段 | `expected.forbidden_semantic_fields` |
| T2-T5 顺序一致 | 阶段标准和 final template 的 unit order 不冲突 | 合同测试对照 `final_template.expected.yaml#/expected/units` |

所以，标准质量衡量回答的是：

```text
这把尺子是不是来源清楚、边界清楚、结构可读、能被 verifier 使用？
```

它不回答：

```text
这一次 template-generate 跑出来的产物是不是合格？
```

## Verify 报告

代码里的 verify 报告是运行结果证据。它读取某一次运行产物，输出这次运行的 `PASS`、`FAIL` 或 `UNKNOWN`。

模板生成链路里容易混淆的报告有两类：

| 报告 | 来源 | 判断对象 | 说明 |
| --- | --- | --- | --- |
| `07_verification_report.json` | `template-generate` 运行时生成 | 当前 run 的 T1-T6 产物 | 证明这次运行里哪些内置检查发现了问题；它不是学校签收标准 |
| `template_gap_report.*` | `template-gap` 生成 | 被测 `generated_template.docx` 或 `06.1_fillable_template.docx` | 对照 `final_template.expected.yaml` 判断最终 Word 和学校标准差距 |

verify 报告回答的是：

```text
这一次运行产物在当前检查器看来是什么状态？
```

它不能做这些事：

- 不能自动更新 `*.standard.yaml` 或 `*.expected.yaml`。
- 不能证明阶段标准本身质量合格。
- 不能在 verifier 未配置时把阶段写成 `PASS`。
- 不能用一次新 run 的产物证明旧 run 没问题。
- 不能替代人工签收标准。

## 两者区别

| 对比项 | 阶段标准质量衡量 | Verify 报告 |
| --- | --- | --- |
| 核心对象 | 标准文件本身 | 某一次运行产物 |
| 典型文件 | `t1_document_facts.standard.yaml` 到 `t5_template_spec.standard.yaml` | `07_verification_report.json`、`template_gap_report.json` |
| 产生方式 | 人工 review 后整理并提交到 `standards/` | 产品代码或评测代码运行后写到 `runs/` 或输出目录 |
| 状态含义 | 标准是否可作为裁判 | 当前运行是否通过、失败或证据不足 |
| 是否可自动更新 | 不可以 | 可以由运行重新生成 |
| 是否参与学校签收 | 是裁判依据 | 是被裁判后的证据 |
| 缺失时结果 | 缺标准应为 `UNKNOWN` | 缺报告说明还没有执行或证据不足 |
| 和 AI 的关系 | AI 可解释，不可擅自改判或反写 | AI 可辅助归因，不可补造状态或证据 |

最短判断口诀：

```text
标准是尺子，verify 报告是这次测量结果。
尺子要先被审过，测量结果只能说明本次被测对象。
```

## 接入状态

当前已完成：

1. 阶段标准聚合清单：读取 `target.standard.yaml`，列出 T1-T5 标准路径、产物路径、hash 和 verifier 状态。
2. T1 verifier：检查 `01_document_facts.json` 的事实完整性和禁用语义字段。
3. T2 verifier：检查 `02_unit_map.yaml` 的单元顺序、边界和分页。
4. T3/T4/T5 verifier：分别检查元素策略、全局版式和 `template_spec` 合并。
5. real-core T1-T5 标准元数据已切换为 `configured/gate_enabled=true`。

后续仍需把 `template-gap` 作为最终模板质量检查挂进同一个聚合报告。

在任何一步，`not_configured` 都不能等同于 `PASS`。real-core 当前已经开始执法；非 real-core 或 fixture 若仍未配置，仍必须保守输出 `UNKNOWN`。
