---
status: draft
owner: template-generation
stage: standard-judge
topic: stage-standard-diff-diagnosis
issue_id: STANDARD-JUDGE-ISSUE-02
issue_sequence: 2
created: 2026-06-28
last_updated: 2026-06-28
version: 1
previous_issue:
  id: STANDARD-JUDGE-ISSUE-01
  doc: docs/plans/template-parse-refactor-standard-judge-issue-01-run-bundle-stage-verifiers.md
previous_optimization:
  id: STANDARD-JUDGE-PLAN-01
  doc: docs/plans/template-parse-refactor-standard-judge-plan-01-stage-diff-root-cause.md
  summary: Plan 01 已实现 run bundle、阶段报告、部分 stage_standard_diffs/root_causes 和 gate/signoff 输出，但执行过程把 gate/signoff 可签收优先级放到了 stage standard diff diagnosis schema 前面，导致最初定义的“差异、原因、责任、修法”四层报告没有完成。
next_plan:
  id: STANDARD-JUDGE-PLAN-02
  doc: docs/plans/template-parse-refactor-standard-judge-issue-02-stage-standard-diff-diagnosis-priority.md
  summary: 本文同时作为 Issue 02 和 Plan 02；下一步先完成 stage standard diff diagnosis 四层 schema 与报告输出，再回头讨论 gate。
related_docs:
  - docs/current/template-generation-stage-standard-quality.md
  - docs/current/template-generation-evaluation.md
  - docs/current/template-generation-stage-standards.md
related_code:
  - src/docfit/harness/template_generation_judge_reports.py
  - src/docfit/harness/template_generation_stage_verifiers.py
  - src/docfit/harness/template_generation_standard_judge.py
  - src/docfit/harness/template_generation_run_bundle.py
---

# Standard Judge Issue 02：阶段标准差异诊断优先级纠偏

## 0. P0 目标锁定

本轮 standard judge 的首要目标不是 gate，也不是先证明三校能不能签收。

首要目标是让每个阶段报告稳定回答四个问题：

```text
1. 阶段产物和阶段标准哪里不一致？
2. 为什么不一致？
3. 这个问题该谁修？
4. 怎么修，修完怎么验？
```

这四层报告能力叫：

```text
阶段标准差异诊断
stage standard diff diagnosis
```

gate 可以做，但必须排在它后面。`standard_acceptance_status`、`signoff_status`、`gate_enabled`、`verifier_state` 都不能替代 stage standard diff diagnosis。

## 1. 为什么出现偏差

偏差不是因为最开始目标没写清楚，而是因为执行时没有把“四层 schema 是否落盘”设成验收门槛。

实际执行中出现了三件事：

```text
1. 先补了 run bundle、报告命名、阶段 verifier 和 gate/signoff 状态。
2. 看到三校 real-core T1-T5 变成 PASS/SIGNABLE 后，把“可签收”误当成了主目标完成。
3. 现有报告虽然有 stage_standard_diffs/root_causes/top_blockers，但没有固定的 mismatches/root_causes/owner_assignments/fix_plan 四层结构，也没有独立 standard_diff_report 文件。
```

根本问题：

```text
目标优先级漂移：
  把 gate/signoff 当成主线；
  把 stage standard diff diagnosis 当成附属字段。

验收门槛缺失：
  没有测试强制要求每个 mismatch 必须带 root_cause、owner_assignment 和 fix_plan；
  没有测试强制 gate 关闭或未配置时仍能输出标准差异诊断。
```

后续开发必须用本文纠偏：

```text
先诊断，后 gate。
先差异、原因、责任、修法，后 PASS/SIGNABLE。
```

## 2. 当前真实运行口径

当前可复现的命令分两类。

### 2.1 当前已通过的 real-core 正向样例

```bash
ROOT=/tmp/docfit_standard_acceptance_real_core_after_t3_fixed_fill_exception
for school in hunannongye nannong-undergraduate pku-graduate; do
  run_root="$ROOT/$school"
  uv run docfit eval template-generate \
    --template "inputs/targets/$school/raw/source_template.docx" \
    --out "$run_root/eval_runs/template_generate"
  uv run docfit eval template-generation-judge \
    --school "$school" \
    --run "$run_root/eval_runs/template_generate" \
    --out "$run_root/eval_runs/template_generation_judge"
done
```

Observed：

```text
三校 template_generation_judge_report.json:
  status: PASS
  standard_acceptance_status: PASS
  signoff_status: SIGNABLE
  first_bad_stage: null
  stage_standard_diffs: []
  root_causes: []
```

这个正向样例只能证明当前三校没有差异，不能证明“失败时的差异诊断报告”已经达标。

### 2.2 当前失败样例暴露的不足

上一轮失败样例路径：

```text
/tmp/docfit_standard_acceptance_real_core_after_fill_fix/hunannongye/eval_runs/template_generation_judge/03_element_spec_standard_quality_report.json
```

当时 T3 报告包含：

```text
stage_standard_diffs:
  - diff_id: diff_001
    stage_id: T3
    finding_type: t3_policy_group_conflict
    expected: "{'fixed_units': ['cover'], ...}"
    observed: "[{'stable_id': 'cover.e_011', ... 'actual': 'fill'}]"
    owner: code
    next_action: Fix template-generation deterministic logic for the first bad stage.

root_causes:
  - root_cause_id: rc_001
    root_cause_bucket: stage_standard_mismatch
    owner: code
    reason: The generated stage artifact does not match the signed standard evidence.
```

这说明当前报告已有雏形，但还不符合目标。

## 3. Expected vs Observed

### 3.1 每阶段标准差异报告

Expected：

```yaml
stage: T2
artifact: 02_unit_map.yaml
standard: t2_unit_pagination.standard.yaml
status: FAIL
mismatches:
  - id: T2-MISMATCH-001
    field: expected.unit_order
    expected:
      - cover
      - toc
      - body_main
    observed:
      - cover
      - body_main
      - toc
    problem: unit 顺序和标准不一致
    evidence:
      artifact_path: 02_unit_map.yaml
      standard_path: t2_unit_pagination.standard.yaml
      source_seq_refs: []
```

Observed：

```text
当前只有 stage_standard_diffs[]。
字段名不是 mismatches[]；
id 不是 T2-MISMATCH-001 这种阶段稳定编号；
缺 field/problem/evidence.artifact_path/evidence.standard_path/source_seq_refs。
```

### 3.2 Root Cause

Expected：

```yaml
root_cause:
  category: generation_code
  first_bad_stage: T2
  reason: T2 unit boundary 识别把 toc 放到了 body_main 后面
```

允许枚举：

```text
generation_code
ai_overlay
standard_issue
comparator_issue
input_issue
evidence_missing
downstream_symptom
```

Observed：

```text
当前是 root_cause_bucket + owner 的粗分类。
root_cause_bucket 常见值如 stage_standard_mismatch，不等价于可执行根因类别。
reason 是泛化句子，不解释具体错误为什么发生。
```

### 3.3 责任归因

Expected：

```yaml
owner:
  primary: template_generation_code_owner
  secondary: standard_judge_owner
  rationale: 产物中的 unit_order 与标准不一致，且标准质量为 PASS；优先修 T2 识别逻辑，对比器只需确认解释是否足够清楚。
```

允许枚举：

```text
template_generation_code_owner
ai_integration_owner
standard_owner
standard_judge_owner
input_data_owner
human_review_owner
```

Observed：

```text
当前 owner 是 code/verifier/standard/ai_prompt/unknown。
这些可以用于内部粗分类，但不是面向修复责任的 owner assignment。
```

### 3.4 修复计划

Expected：

```yaml
fix_plan:
  action: 修改 T2 unit discovery 的边界/排序规则
  likely_files:
    - src/docfit/template_generation/structure_candidates.py
    - src/docfit/template_generation/artifacts.py
  tests:
    - tests/contract/test_template_generate.py
    - tests/unit/test_t2_standard.py
  acceptance:
    - 02_unit_map_standard_quality_report.json 中该 mismatch 消失
    - T2 audit_status 从 FAIL/UNKNOWN 变为 PASS
    - 不引入新的 T3/T5 mismatch
```

Observed：

```text
当前只有 next_action，而且是模板化泛句。
没有 likely_files/tests/acceptance。
```

## 4. 上一轮已解决 / 未解决对照

| 类别 | 已解决 | 未解决 |
| --- | --- | --- |
| run bundle | 能绑定同一次 template-generate run，并记录 artifact/hash | 与 diff diagnosis schema 的证据字段尚未一一落地 |
| 报告命名 | 已有编号化 `*_standard_quality_report.{json,md}` | 还没有 `*_standard_diff_report.{json,md}` |
| stage verifier | T1-T5 已有确定性 audit，real-core 正向样例可 PASS | audit finding 还没有转成稳定 `mismatches[]` schema |
| root cause | 已有粗略 `root_causes[]` | 未使用目标枚举，未解释具体原因，未区分 comparator/input/evidence/downstream |
| owner | 已有 `owner_summary` | 未输出 `owner_assignments[]`，枚举不符合修复责任模型 |
| fix plan | 有 `next_action` | 未输出结构化 `fix_plan[]` |
| gate | 已能输出 `standard_acceptance_status/signoff_status` | gate 抢占了主目标；后续必须降级为诊断之后的补充信息 |

## 5. 下一步执行 Plan

### Phase 0：目标优先级固化

目标：

```text
把 stage standard diff diagnosis 优先于 gate 写入仓库记忆，避免后续开发继续跑偏。
```

执行：

1. 新增本文作为 Issue 02 / Plan 02。
2. 更新 `docs/plans/template-parse-refactor-issue-index.md`。
3. 更新 `AGENTS.md`，写入 standard judge 目标优先级硬约束。

验收：

```text
后续任何 standard-judge 开发前，必须先检查本文；
最终回复不能把 PASS/SIGNABLE 当成 stage standard diff diagnosis 完成证据。
```

### Phase 1：定义并实现四层 diagnosis schema

目标：

```text
新增稳定机器 schema：
  mismatches[]
  root_causes[]
  owner_assignments[]
  fix_plan[]
```

建议代码：

```text
src/docfit/harness/template_generation_judge_reports.py
  build_stage_standard_diagnosis_report()
  build_mismatches()
  build_diagnosis_root_causes()
  build_owner_assignments()
  build_fix_plans()
```

验收：

```text
每个阶段报告即使 PASS，也必须包含空数组：
  mismatches: []
  root_causes: []
  owner_assignments: []
  fix_plan: []
```

### Phase 2：T2 标准差异诊断

优先级最高。

必须覆盖 mismatch 类型：

```text
t2_unit_order_mismatch
t2_expected_unit_missing
t2_unexpected_unit_present
t2_anchor_owner_mismatch
t2_source_range_mismatch
t2_page_policy_mismatch
```

每个 mismatch 至少输出：

```text
id
field
expected
observed
problem
evidence.artifact_path
evidence.standard_path
evidence.source_seq_refs
root_cause.category
owner.primary
fix_plan.action
fix_plan.tests
fix_plan.acceptance
```

验收：

```text
构造一个 T2 unit_order 失败 fixture；
02_unit_map_standard_diff_report.json 写出 T2-MISMATCH-001；
即使 gate_enabled=false，也必须输出同样的 mismatch/root_cause/owner/fix_plan。
```

### Phase 3：T3 标准差异诊断

必须覆盖 mismatch 类型：

```text
t3_unit_order_mismatch
t3_policy_group_conflict
t3_required_policy_fields_missing
```

T3 特别规则：

```text
fixed_units 默认不允许 fill；
只有 standard 显式写 fixed_units_allow_fill_elements 的 unit 才允许固定块内部局部 fill。
```

验收：

```text
构造 T3 policy_group_conflict fixture；
03_element_spec_standard_diff_report.json 能说明是 policy group 冲突；
root_cause 不得只写“失败了”，必须说明 fixed/manual/generated/fill 哪组冲突。
```

### Phase 4：T5 标准差异诊断

必须覆盖 mismatch 类型：

```text
t5_input_hash_missing
t5_review_flags_dropped
t5_unit_order_mismatch
t5_section_profile_refs_missing
t5_upstream_trace_missing
```

验收：

```text
构造 T5 丢 review_flags 或 section_profile_refs 缺失 fixture；
05_template_spec_standard_diff_report.json 能把 T5 问题标成 downstream_symptom 或 generation_code；
如果 T5 症状来自 T2/T3，root_cause.first_bad_stage 必须指向上游。
```

### Phase 5：报告文件输出

新增或补齐这些文件：

```text
02_unit_map_standard_diff_report.json
02_unit_map_standard_diff_report.md
03_element_spec_standard_diff_report.json
03_element_spec_standard_diff_report.md
05_template_spec_standard_diff_report.json
05_template_spec_standard_diff_report.md
template_generation_root_cause_report.json
template_generation_root_cause_report.md
```

说明：

```text
已有 *_standard_quality_report 可以继续保留；
但 diff diagnosis 不要只藏在 quality report 的子字段里。
```

验收：

```text
template-generation-judge 每次运行都输出上述文件；
PASS 时 mismatches/root_causes/owner_assignments/fix_plan 为空数组；
FAIL/UNKNOWN 时四层结构完整。
```

### Phase 6：合同测试防回归

新增或扩展测试：

```text
tests/contract/test_template_generation_standard_judge.py
tests/unit/test_template_generation_stage_verifiers.py
tests/unit/test_template_generation_standard_diff_diagnosis.py
```

最低测试矩阵：

| 场景 | 必须证明 |
| --- | --- |
| T2 unit_order mismatch | 有 `T2-MISMATCH-001`、`generation_code`、`template_generation_code_owner`、T2 fix_plan |
| T3 policy conflict | 有 policy group problem、owner、fix_plan |
| T5 upstream symptom | 能标记 `downstream_symptom` 并指向 first_bad_stage |
| standard missing | `standard_issue` 或 `evidence_missing`，owner 为 `standard_owner` 或 `input_data_owner` |
| comparator missing | `comparator_issue`，owner 为 `standard_judge_owner` |
| gate disabled | 仍然输出 mismatches/root_causes/owner/fix_plan；gate 状态只作为补充字段 |

## 6. 非目标

本轮先不做：

```text
1. 不优先打开更多 gate。
2. 不以 SIGNABLE/PASS 作为主要完成指标。
3. 不把 AI 解释文本当成裁判结果。
4. 不把当前运行产物反写进标准。
5. 不为了让报告好看而吞掉 FAIL/UNKNOWN。
```

## 7. 最终验收门槛

本 issue 完成时，必须可以拿一个失败 fixture 证明报告直接回答：

```text
哪里不一致：
  mismatches[].field / expected / observed / problem / evidence

为什么不一致：
  root_causes[].category / first_bad_stage / reason

谁该修：
  owner_assignments[].primary / secondary / rationale

怎么修、怎么验：
  fix_plan[].action / likely_files / tests / acceptance
```

只有上述四层结构完成后，才继续讨论 gate/signoff 作为签收层。
