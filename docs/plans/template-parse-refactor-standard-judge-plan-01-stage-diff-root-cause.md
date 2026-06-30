---
status: draft
owner: template-generation
stage: standard-judge
topic: template-generation-standard-judge
doc_type: implementation_plan
plan_id: STANDARD-JUDGE-PLAN-01
created: 2026-06-28
last_updated: 2026-06-28
related_issue:
  id: STANDARD-JUDGE-ISSUE-01
  doc: docs/plans/template-parse-refactor-standard-judge-issue-01-run-bundle-stage-verifiers.md
previous_issue:
  id: STANDARD-JUDGE-ISSUE-01
  doc: docs/plans/template-parse-refactor-standard-judge-issue-01-run-bundle-stage-verifiers.md
previous_optimization:
  doc: none
  summary: none
target_outputs:
  - verify_report
  - stage_standard_diff_report
  - root_cause_report
related_code:
  - src/docfit/harness/template_generation_standard_judge.py
  - src/docfit/harness/template_generation_run_bundle.py
  - src/docfit/harness/template_generation_stage_verifiers.py
  - src/docfit/harness/template_generation_judge_reports.py
  - src/docfit/template_generation/agent/attribution.py
---

# Standard Judge Plan 01：阶段 diff 与责任归因闭环

## 0. 阶段目标

目标不是让 `template-generate` 直接变成 PASS，而是让一次模板生成跑完后，系统能稳定回答三个问题：

```text
1. 这次 run 本身是否可靠？
2. 每个阶段产物与对应阶段标准有哪些具体不一致？
3. 每个不一致的原因是什么，应该由代码、标准、verifier 还是 AI/prompt 解决？
```

最终交付三个报告：

| 报告 | 回答的问题 | 状态权威 |
| --- | --- | --- |
| `verify_report` | run 内部产物链、hash、T1 边界、DOCX 输出是否可靠 | deterministic code |
| `stage_standard_diff_report` | T1-T5 产物和最终 Word 分别与标准哪里不一致 | deterministic stage verifier |
| `root_cause_report` | 不一致来自代码、标准、verifier 缺口还是 AI proposal | deterministic classifier + agent attribution join |

AI 只能提供建议和被归因，不能裁定 PASS/FAIL。`standards/targets/**` 只能作为裁判输入，不能作为模板生成算法输入。

## 1. 当前真实状态

截至 2026-06-28，本地最终复核结果：

```text
real-core 三校：
  T1 audit=PASS, status=PASS
  T2 audit=PASS, status=PASS
  T3 audit=PASS, status=PASS
  T4 audit=PASS, status=PASS
  T5 audit=PASS, status=PASS

template-generation-judge:
  standard_acceptance_status=PASS
  signoff_status=SIGNABLE
  owner_summary.code=0
  owner_summary.verifier=0
```

本阶段已经从“骨架和局部 audit”推进到“可执行 diff + root cause + owner + 可签收 gate”。`template-generation-judge` 对 real-core T1-T5 读取 signed standard、绑定同一次 run bundle，并输出编号化阶段报告。

2026-06-28 纠偏记录：

上一轮 run-bundle 验收只能说明输出路径、编号化报告和 run bundle hash 绑定跑通；它不能代表“阶段产物 vs 阶段标准”已经可签收。后续修复完成前，曾出现如下真实状态：

```text
status: UNKNOWN
standard_acceptance_status: FAIL / UNKNOWN
signoff_status: NOT_SIGNABLE
owner_summary:
  code: >0
  verifier: 5
  standard: 0
  ai_prompt: 0
  unknown: 0
```

当时含义：

1. `status=UNKNOWN` 来自 T1-T5 标准文件仍声明 `verifier_state=not_configured`、`gate_enabled=false`。
2. `standard_acceptance_status=FAIL` 来自 T2/T3/T5 已有确定性 audit 发现产物与 signed standard 不一致。
3. `signoff_status=NOT_SIGNABLE` 是当时唯一可以对外签收的结论：那份 run 的标准验收报告不能被当成 PASS。
4. 明确产物 mismatch 默认归 `owner=code`；只有标准文件缺失、无效或 registry 错误才归 `owner=standard`。

现在这些 code/verifier 阻断已清零；如果未来报告再次出现 `NOT_SIGNABLE`，必须按同样口径暴露 blocker，不能假装通过。

## 2. 成功标准

### 2.1 人读结果

对任意三校 run，执行：

```bash
RUN_ROOT=test_outputs/debug/template_generation/manual_hunannongye
uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run "$RUN_ROOT/eval_runs/template_generate" \
  --out "$RUN_ROOT/eval_runs/template_generation_judge"
```

报告必须直接给出：

```text
status: FAIL | UNKNOWN | PASS
first_bad_stage: T1 | T2 | T3 | T4 | T5 | final_template | none
owner_summary:
  code: N
  verifier: N
  standard: N
  ai_prompt: N
  unknown: N
top_blockers:
  - stage, unit/element, expected, observed, root_cause, owner, next_action
```

### 2.2 机器可读结果

`template_generation_judge_report.json` 至少包含：

```text
verify_report_ref
run_bundle
standard_quality
stage_standard_quality_reports[]
stage_checks[]
stage_standard_diffs[]
root_causes[]
owner_summary
first_bad_stage
final_gap_ref optional
agent_attribution_ref optional
```

每条 `stage_standard_diffs[]` 必须能被后续自动 issue 化。

### 2.3 判定规则

```text
标准文件缺失 / run 证据缺失 / hash 不一致 -> UNKNOWN
阶段 verifier 未实现 -> UNKNOWN, owner=verifier
阶段产物与 signed standard 明确不一致 -> FAIL
最终 Word 与 final_template.expected.yaml 明确不一致 -> FAIL
所有 enabled checks 通过且没有 UNKNOWN -> PASS
```

## 3. 输出契约

### 3.1 阶段报告命名

标准裁判输出目录必须保留聚合报告，同时为每个阶段写独立报告。独立报告的文件名要和 `template-generate` 的阶段产物名对齐：保留编号、保留核心 artifact 名称，并追加 `_standard_quality_report`。

示例输出目录：

```text
test_outputs/debug/template_generation/manual_hunannongye/eval_runs/template_generation_judge/
  summary.json
  findings.json

  00_template_generation_request_standard_quality_report.json
  00_template_generation_request_standard_quality_report.md

  01_document_facts_standard_quality_report.json
  01_document_facts_standard_quality_report.md

  02_unit_map_standard_quality_report.json
  02_unit_map_standard_quality_report.md

  03_element_spec_standard_quality_report.json
  03_element_spec_standard_quality_report.md

  04_global_spec_standard_quality_report.json
  04_global_spec_standard_quality_report.md

  05_template_spec_standard_quality_report.json
  05_template_spec_standard_quality_report.md

  06.1_fillable_template_standard_quality_report.json
  06.1_fillable_template_standard_quality_report.md

  06.2_build_manifest_standard_quality_report.json
  06.2_build_manifest_standard_quality_report.md

  07_verification_report_standard_quality_report.json
  07_verification_report_standard_quality_report.md

  template_generation_run_bundle.json
  template_generation_stage_checks.json
  template_generation_judge_report.json
  template_generation_judge_report.md
```

命名映射：

| run 产物 | 阶段报告 |
| --- | --- |
| `00_template_generation_request.json` | `00_template_generation_request_standard_quality_report.{json,md}` |
| `01_document_facts.json` | `01_document_facts_standard_quality_report.{json,md}` |
| `02_unit_map.yaml` | `02_unit_map_standard_quality_report.{json,md}` |
| `03_element_spec.yaml` | `03_element_spec_standard_quality_report.{json,md}` |
| `04_global_spec.yaml` | `04_global_spec_standard_quality_report.{json,md}` |
| `05_template_spec.yaml` | `05_template_spec_standard_quality_report.{json,md}` |
| `06.1_fillable_template.docx` | `06.1_fillable_template_standard_quality_report.{json,md}` |
| `06.2_build_manifest.json` | `06.2_build_manifest_standard_quality_report.{json,md}` |
| `07_verification_report.json` | `07_verification_report_standard_quality_report.{json,md}` |

说明：

```text
1. 每个阶段报告只负责一个 artifact 与其对应标准/契约的质量判断。
2. `template_generation_judge_report.{json,md}` 只做聚合、first_bad_stage、owner_summary 和 top blockers。
3. `template_generation_stage_checks.json` 可以继续作为机器读取的阶段列表，但不能替代编号化阶段报告。
4. 如果某阶段没有学校阶段标准，例如 00/06.2/07，则报告仍保留同名文件，status 可为 PASS/UNKNOWN，标准来源写成 run contract 或 verifier contract。
```

每个编号化阶段报告 JSON 至少包含：

```text
report_id
report_kind: standard_quality_report
stage_id
stage_key
artifact_under_test
artifact_path
artifact_sha256
standard_path optional
standard_sha256 optional
contract_source: stage_standard | final_template_expected | run_contract | verifier_contract
status
checks[]
stage_standard_diffs[]
root_causes[]
owner_summary
next_actions[]
```

### 3.2 StageStandardDiff

每个阶段不一致统一落成 `stage_standard_diffs[]`：

```yaml
mismatch_id: diff_T2_0001
status: FAIL | UNKNOWN
severity: blocking | warning
stage_id: T2
stage_key: t2_unit_pagination
check_id: t2_unit_order
standard:
  path: standards/targets/hunannongye/v1/template_generation/t2_unit_pagination.standard.yaml
  sha256: sha256:...
artifact:
  path: runs/.../02_unit_map.yaml
  sha256: sha256:...
field_path: $.units[*].unit_id
expected: [cover, integrity_statement, toc, ...]
observed: [cover, integrity_statement, toc, references, ...]
affected_unit_ids: [references, body_main]
affected_element_ids: []
source_seq_refs: [244, 245]
evidence_refs:
  - runs/.../02_unit_map.yaml
  - standards/.../t2_unit_pagination.standard.yaml
message: T2 unit order does not match signed standard
report_ref: 02_unit_map_standard_quality_report.json
```

### 3.3 RootCause

每个 diff 追加一条 `root_causes[]`：

```yaml
mismatch_id: diff_T2_0001
root_cause_bucket: code:t2_unit_detector
owner: code
owner_detail: template-generation deterministic T2 logic
confidence: high
reason: round0 unit_map already disagrees with signed T2 standard and no accepted AI proposal touched this path
introduced_by:
  source: round0 | agent | verifier | standard | unknown
  round_id: null
  proposal_ids: []
next_action: fix T2 unit ordering / boundary state machine, then rerun template-generation-judge
report_ref: 02_unit_map_standard_quality_report.json
```

Owner 闭集：

| owner | 含义 |
| --- | --- |
| `code` | 生成器、inspector、verifier 或 reconciler 的确定性代码要修 |
| `standard` | 阶段标准或 final expected 本身缺锚点、冲突或错误 |
| `verifier` | 标准存在但检查器缺失或证据读取能力不足 |
| `ai_prompt` | AI proposal 本身无效或 accepted proposal 引入错误 |
| `human_review` | 需要人工决定标准口径或产品取舍 |
| `unknown` | 证据不足，不能可靠归因 |

### 3.4 Agent attribution join

如果 run 里存在：

```text
artifacts/agent_attribution.json
artifacts/template_agent_decisions.json
artifacts/agent_t2_overlay.json
artifacts/agent_t3_overlay.json
artifacts/agent_t4_hints.json
```

root cause classifier 必须用 `field_path` / `source_seq_refs` / `proposal_id` 做 join：

| 情况 | 归因 |
| --- | --- |
| mismatch path 没有被 agent touch，round0 已错 | `owner=code` |
| proposal rejected，所以产物未变化 | `owner=ai_prompt`，但不算生成 regression |
| proposal accepted 后对应 path 从 PASS 变 FAIL | `owner=ai_prompt` 或 `code:reconciler_too_permissive` |
| proposal accepted，但 deterministic verifier 仍 UNKNOWN 因检查器缺失 | `owner=verifier` |
| T4 hint 只落 attribution，不改变 T4/T5/T6 | 只能归因为 hint，不能改变 status |

第一版不要求自然语言 RCA 很聪明，但必须可追踪、可复现。

## 4. 执行计划

### Phase 0：锁定报告 schema 和 fixture

目标：先把报告形状固定，避免后续 verifier 各写各的字段。

改动：

```text
src/docfit/harness/template_generation_judge_reports.py
src/docfit/harness/template_generation_stage_verifiers.py
tests/fixtures/template_generation_judge/
tests/unit/test_template_generation_judge_reports.py
```

任务：

1. 定义 `StageStandardDiff` 和 `RootCause` dataclass 或 typed dict。
2. 定义编号化阶段报告 schema，文件名使用 `<stage_artifact_stem>_standard_quality_report.{json,md}`。
3. `TemplateGenerationJudgeReport.to_dict()` 增加 `stage_standard_quality_reports`、`stage_standard_diffs`、`root_causes`、`owner_summary`。
4. Markdown 报告新增三段：Summary、Stage Reports、Root Cause / Owner。
5. 增加最小 fixture，覆盖 1 条 T2 FAIL、1 条 verifier UNKNOWN、1 条 AI attribution join。

验收：

```bash
uv run pytest tests/unit/test_template_generation_judge_reports.py -q
```

### Phase 1：完善 run bundle 与 verify report 引用

目标：证明裁判消费的是同一次 `template-generate` run，而不是临时拼出来的文件。

改动：

```text
src/docfit/harness/template_generation_run_bundle.py
src/docfit/harness/template_generation_standard_judge.py
tests/unit/test_template_generation_run_bundle.py
```

任务：

1. 绑定顶层编号文件和 `artifacts/` 兼容文件。
2. 记录每个 artifact 的实际 path、sha256、manifest source。
3. 检查 request source hash、debug index hash、build manifest output hash。
4. 在 judge report 里引用 `07_verification_report.json`，并把内置 UNKNOWN findings 保留为 verify 层信息。

验收：

```bash
uv run pytest tests/unit/test_template_generation_run_bundle.py \
  tests/contract/test_template_generation_standard_judge.py -q
```

### Phase 2：T1 verifier 先变成可判定

目标：T1 是事实层边界，必须先可判定，否则 `first_bad_stage` 永远被 verifier_missing 抢占。

改动：

```text
src/docfit/harness/template_generation_stage_verifiers.py
tests/unit/test_template_generation_stage_verifiers.py
```

检查项：

1. `artifact_type`、source template hash、必需 top-level/data groups。
2. `body_flow` / `runs` source_seq 连续性、source_ref 可回查。
3. 表格、页眉页脚、sections、fields、numbering、images/unknown objects 的事实组存在性。
4. 禁止 T1 输出语义判断字段：`unit_id`、`policy`、`confidence`、`is_toc_entry` 等。

输出：

```text
T1 PASS: 事实完整且无语义字段
T1 FAIL: 明确违反 fact-only 或 source_seq 错
T1 UNKNOWN: 标准缺必需项、artifact 缺失、证据不足
```

验收：

```bash
uv run pytest tests/unit/test_template_generation_stage_verifiers.py -q
uv run docfit eval template-generation-judge --school hunannongye --run <run> --out <out>
```

### Phase 3：T2/T3/T5 diff 产品化

目标：把当前 T2/T3/T5 audit 从 summary 变成具体 diff。

改动：

```text
src/docfit/template_generation/t2_standard.py
src/docfit/harness/template_generation_stage_verifiers.py
tests/unit/test_template_generation_stage_verifiers.py
```

T2 diff：

```text
unit_order mismatch
missing_units / unexpected_units
source_seq owner mismatch
boundary range mismatch
pagination ownership UNKNOWN
```

T3 diff：

```text
unit_order mismatch
policy group conflict
fill_source missing / unexpected
manual_semantics missing
generated.field_type mismatch
instruction_remove / fixed / fill policy mismatch
source trace missing
```

T5 diff：

```text
template_spec unit order mismatch
element policy not preserved from T3
section_profile refs missing
input hash mismatch
review flags not propagated
```

验收：

```bash
uv run pytest tests/unit/test_template_generation_stage_verifiers.py \
  tests/contract/test_template_generation_standard_judge.py -q
```

三校 judge report 至少能列出阻断项的 `expected`、`observed`、`field_path`、`affected_unit_ids`。

### Phase 4：T4 verifier 与最终 gap 引用

目标：T4 不一定一次做完所有版式检查，但不能只显示 not_configured。

改动：

```text
src/docfit/harness/template_generation_stage_verifiers.py
src/docfit/template_gap/gap.py optional
```

T4 第一版检查：

```text
section profile count / id
section boundary source_ref
page numbering display/status
header/footer part references
default font/page setup presence
```

最终 gap：

1. judge 命令第一版不自动跑 `template-gap`。
2. 如果 `--final-gap-report` 后续加入，允许把 final gap report join 到 root cause。
3. 当前 plan 只要求输出中预留 `final_gap_ref` 字段。

验收：

```bash
uv run pytest tests/unit/test_template_generation_stage_verifiers.py -q
```

### Phase 5：Root cause classifier

目标：把 diff 转成 owner 和 next action。

新增或扩展：

```text
src/docfit/harness/template_generation_root_cause.py
tests/unit/test_template_generation_root_cause.py
```

规则优先级：

1. artifact 缺失、hash mismatch -> `owner=code` 或 `owner=unknown`，bucket=`run_bundle_invalid`。
2. verifier_state not_configured -> `owner=verifier`。
3. standard 自身缺 required expected 字段 -> `owner=standard`。
4. T1 fact-only 违反 -> `owner=code`。
5. T2/T3/T4/T5 round0 diff -> `owner=code`。
6. accepted AI proposal touch 了同 path 且引入 diff -> `owner=ai_prompt` 或 `code:reconciler_too_permissive`。
7. rejected AI proposal -> `owner=ai_prompt`，但不改变主产物 status。
8. 证据不足 -> `owner=unknown`，要求人工 review。

验收：

```bash
uv run pytest tests/unit/test_template_generation_root_cause.py \
  tests/contract/test_template_generation_standard_judge.py -q
```

### Phase 6：三校真实 run 验收

目标：不是要求三校 PASS，而是要求失败可解释、可分派。

命令：

```bash
for school in hunannongye nannong-undergraduate pku-graduate; do
  uv run docfit eval template-generate \
    --template inputs/targets/$school/raw/source_template.docx \
    --out /private/tmp/docfit_standard_judge_plan01/$school/template_generate

  uv run docfit eval template-generation-judge \
    --school $school \
    --run /private/tmp/docfit_standard_judge_plan01/$school/template_generate \
    --out /private/tmp/docfit_standard_judge_plan01/$school/template_generation_judge
done
```

验收口径：

```text
1. standard quality PASS。
2. run bundle PASS。
3. T1/T4 不再因为 verifier_missing 抢占 first_bad_stage。
4. T2/T3/T5 FAIL 时有具体 diff。
5. root cause owner_summary 非空。
6. Markdown 报告中 top blockers 可直接转 issue。
```

## 5. 文件与测试清单

预计代码改动：

```text
src/docfit/harness/template_generation_judge_reports.py
src/docfit/harness/template_generation_run_bundle.py
src/docfit/harness/template_generation_stage_verifiers.py
src/docfit/harness/template_generation_standard_judge.py
src/docfit/harness/template_generation_root_cause.py
src/docfit/template_generation/t2_standard.py
```

预计测试：

```text
tests/unit/test_template_generation_judge_reports.py
tests/unit/test_template_generation_run_bundle.py
tests/unit/test_template_generation_stage_verifiers.py
tests/unit/test_template_generation_root_cause.py
tests/contract/test_template_generation_standard_judge.py
```

回归命令：

```bash
uv run pytest tests/unit/test_template_generation_stage_verifiers.py \
  tests/unit/test_template_generation_run_bundle.py \
  tests/contract/test_template_generation_standard_judge.py -q

uv run pytest tests/contract/test_template_generate.py \
  tests/contract/test_template_generate_agent_default_off.py \
  tests/contract/test_template_generate_agent_replay.py -q
```

## 6. 非目标

本 plan 不做：

```text
1. 不让 template-generate 读取 standards 后再生成。
2. 不自动修标准，不自动更新 expected。
3. 不让 AI 裁定 PASS/FAIL。
4. 不要求三校最终 Word 立即 PASS。
5. 不把 T4 hints 升级成 T4 overlay。
6. 不引入 LangChain / LangGraph / CrewAI。
```

## 7. 实施顺序建议

优先顺序：

```text
P0 schema/report -> P1 run bundle -> P2 T1 verifier -> P3 T2/T3/T5 diff
-> P5 root cause -> P4 T4/final gap ref -> P6 三校验收
```

原因：

```text
1. schema 先行，避免阶段 verifier 输出无法聚合。
2. run bundle 先行，避免 diff 指向不同 run。
3. T1 verifier 先行，避免 first_bad_stage 永远停在 verifier_missing。
4. T2/T3/T5 是当前真实阻断面，优先产出可分派 diff。
5. root cause 在 diff 稳定后接入，避免归因基于不稳定字段。
```

## 8. 完成定义

本阶段完成时，一轮运行后应该能得到类似结论：

```text
Status: FAIL
First bad stage: T2

Top blockers:
1. T2 unit_order mismatch
   expected: [...]
   observed: [...]
   owner: code
   next_action: fix T2 unit detector ordering/state-machine

2. T3 policy group conflict
   expected: manual_only [...]
   observed: fill [...]
   owner: code
   next_action: fix T3 policy derivation or T2 unit ownership

3. T4 page numbering evidence UNKNOWN
   owner: verifier
   next_action: add OOXML page numbering verifier support
```

这时即使最终模板仍 FAIL，工程上也已经进入可执行状态：每个问题都有证据、字段路径、阶段归属、根因类别和责任方。
