---
status: draft
owner: template-generation
stage: standard-judge
topic: route-eval
doc_type: issue
issue_id: STANDARD-JUDGE-ISSUE-03
issue_sequence: 03
previous_issue:
  id: STANDARD-JUDGE-ISSUE-02
  doc: docs/plans/template-parse-refactor-standard-judge-issue-02-stage-standard-diff-diagnosis-priority.md
previous_optimization:
  doc: docs/plans/template-parse-refactor-standard-judge-plan-01-stage-diff-root-cause.md
  summary: 已建立 run bundle、T1-T5 阶段 verifier、stage standard diff、root cause、owner 和 fix plan 四层诊断；但评测仍围绕最终阶段产物，尚未统一比较 code_raw、ai_raw、merged 三条路线，也未把 T6 执行和 template-gap 纳入同一诊断闭环。
next_plan: docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-plan-03-full-chain-three-route-evaluator.md
created: 2026-07-01
last_updated: 2026-07-01
---

# Standard Judge Issue 03：模板生成全链路三路线评测缺口

## 真实运行口径

当前模板生成主链路按阶段产出：

```text
T1 document_facts
  -> T2 unit_map
  -> T3 element_spec
  -> T4 global_spec
  -> T5 template_spec
  -> T6 fillable_template.docx / build_manifest
  -> verification_report
```

`template-generation-judge` 读取同一次 `template-generate` run bundle，并对照三校 `standards/targets/<school>/v1/template_generation/` 下的 T1-T5 阶段标准输出质量报告、阶段检查、stage standard diff 和四层诊断。

当前 AI/code/merged 三条路线的真实身份是：

```text
code_raw:
  deterministic code 在 agent 合并前的 T2/T3/T4 中间产物。

ai_raw:
  Module 1 的 ai_unit_observation / ai_element_observation / ai_layout_observation。

merged:
  agent bridge / comparison / reconciler 后写回主链路的最终 T2/T3/T4/T5/T6 产物。
```

## Expected vs observed

Expected：

```text
1. 同一套评测入口能统一评测整个模板生成模块，而不是只评 T2/T3。
2. T1 作为共享事实底座被单独检查；T2/T3/T4 对 code_raw、ai_raw、merged 三条路线分别对照标准。
3. T5/T6 通过三路隔离重放评测下游合并和执行，避免只知道最终 merged 是否失败却不知道哪条路线引入问题。
4. T2 报告到单元准确率、单元顺序、source_seq 区间和分页/边界证据。
5. T3 报告到逐元素 presence、policy、fill/manual/generated、source evidence 和行内 instruction span。
6. T4 报告到 section profile、section boundary、page numbering、header/footer、numbering rule 和 unit page policy binding。
7. T5 报告到 template_spec merge、input hash、unit-element binding、unit-section binding、source trace 和 review flag preservation。
8. T6 报告到 DOCX/build_manifest/verification_report 执行证据，并接入 template-gap 或等价最终模板差距报告。
9. 报告能横向比较 code_raw、ai_raw、merged，把 mismatch 分类为 code_only_wrong、ai_only_wrong、both_wrong、merge_regression、merge_fixed_ai、execution_failure、gold_missing 或 evidence_missing。
10. 准确率不能替代 stage standard diff diagnosis；仍必须输出 mismatches[]、root_causes[]、owner_assignments[]、fix_plan[]。
```

Observed：

```text
1. T1-T5 阶段标准和 verifier 已存在，但主要面向当前 run 的最终阶段产物。
2. template_agent_bridge_standard_acceptance 只能说明 bridge 后的 merged 输出摘要，不能同时解释 AI 原始观察、代码原始输出和合并输出谁更接近标准。
3. observation_eval 是 AI observation 的浅层评估，独立于 standard judge 报告体系。
4. code_raw 的完整 T2/T3/T4 产物没有作为可评测 artifact 固化在 run bundle 中。
5. T3 standard 目前只有 policy groups / contract，没有逐元素 expected.elements，也缺少行内 instruction span gold。
6. 人工 review packet 已包含三校单元、元素、顺序、关系、policy、样式和页面事实，但还没有被整理成 T3 元素级诊断草案。
7. T6/T7 当前更多是 run bundle 证据和 verification/template-gap 输出，尚未进入三路线统一评测报告。
8. 当前报告缺少 cross-route failure classification，无法稳定回答“AI 错、代码错、合并错、还是执行器错”。
```

## 疑似根因

```text
1. Standard judge 的第一轮目标是阶段标准和当前 run 产物对齐，因此先落地了 T1-T5 final artifact verifier。
2. T2T3T4 agent bridge 先解决 AI observation 如何进入代码生成桥接，没有把 code_raw/ai_raw/merged 的横向准确率比较作为同一模块的核心接口。
3. T3 元素级 gold 曾被识别为缺口，但 review packet -> element expected 的可审计反推流程尚未建立。
4. T6 被视为 Word 执行结果和 manifest 证据，没有与上游路线隔离重放绑定，因此无法区分上游规格错误和执行器错误。
5. template-gap 属于最终模板质量检查，尚未被 standard judge 当作 T6 后的统一差异证据层消费。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. 三校 T1-T5 阶段标准已拆分并登记。
2. template-generation-judge 已能读取 run bundle，输出阶段检查、standard quality、stage standard diff 和四层诊断。
3. Module 1 AI observation bundle 和 Module 2 observation bridge 已有独立 artifacts。
4. bridge 后 merged 输出已有 template_agent_bridge_standard_acceptance 摘要。
5. 人工 review packet 已明确是三校 source facts 的权威来源，且包含元素、关系、policy 和布局事实。
```

未解决：

```text
1. 缺少整个模板生成模块的 T1-T6 三路线统一评测报告。
2. 缺少 code_raw 完整 artifact 持久化和 route candidate 绑定。
3. 缺少 ai_raw observation 到标准评测 shape 的统一归一化。
4. 缺少基于人工 review packet 和当前输出 scaffold 的三校 T3 draft expected.elements。
5. 缺少 T5/T6 三路线隔离重放，无法定位 merge 或 execution regression。
6. 缺少 template-gap 与 route eval 的统一证据绑定。
7. 缺少 cross-route mismatch 分类和 owner 归因口径。
```

## 后续验收门禁

```text
1. template-generation-judge 能输出 template_generation_route_eval_report.json/md。
2. 报告覆盖 T1-T6，并把 verification_report/template-gap 作为 T6 后执行证据层。
3. T2/T3/T4 至少能分别展示 code_raw、ai_raw、merged 的 availability、source hash、stage metrics 和 item-level mismatches。
4. T5/T6 通过隔离重放评测 code_raw、ai_raw、merged，不覆盖原始 run 产物。
5. T3 三校元素级 expected 第一版只能是 draft_diagnostic，不参与 gate 放行。
6. 没有 AI bundle、缺 code_raw、缺标准或缺执行证据时输出 NOT_AVAILABLE / NOT_EVALUABLE / UNKNOWN，不伪造 PASS。
7. 现有 standard quality、stage diff、root cause、bridge acceptance 报告保持兼容。
8. 报告能稳定回答：问题属于 AI 原始观察、代码原始输出、合并桥接、T5 merge、T6 执行器、标准缺口还是证据缺口。
```
