---
status: draft
owner: template-generation
stage: T2
topic: unit-recognition
plan_id: T2-UNIT-PLAN-03
plan_sequence: 3
created: 2026-06-26
last_updated: 2026-06-26
version: 1
source_issue:
  id: T2-UNIT-ISSUE-03
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-issue-03-state-machine-standard-gates.md
previous_issue:
  id: T2-UNIT-ISSUE-02
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md
previous_plan:
  id: T2-UNIT-PLAN-02
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-plan-02-post-phase2-residual-fix.md
data_contract:
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-data-contract.md
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/verifier.py
  - src/docfit/harness/standards.py
  - scripts/t2_metrics.py
  - tests/unit/test_t2_unit_map.py
---

# T2 单元识别 Plan 03：标准门禁与状态机

## 0. 一句话结论

本轮 T2 不再把“补边界规则、扩 taxonomy、状态机、standard 校验”写成几条平行任务。

执行主线是：

```text
先接上三校 T2 standard 的 audit/gate，
再让 T2 deterministic path 产出 standard 要求的 unit_id，
然后用 front/body/back 状态机解决正文内部标题过切，
最后用 standard-backed range ownership 收口。
```

## 1. 本轮要解决什么

| 问题 | 解决方式 | 完成信号 |
| --- | --- | --- |
| standard 文件存在但没闭环 | 新增 T2 standard loader + standard audit/gate | expected/actual unit_order mismatch 能变成 T2 finding |
| unit_id 与 standard 不一致 | 扩 taxonomy + alias registry + list-like block type | 三校 expected unit_id 不再退化为 custom/旧泛化 unit |
| 核心标题被格式说明干扰 | canonical_label_hint 前移 + instruction_class | 摘□要、附 录、致 谢等能打开正确 boundary |
| 正文 Heading 1 过切 | front/body/back 状态机 | 北大/南农正文内部章标题归入 body_main |
| 后置 references/declaration 错位 | duplicate core contextual rule + back_matter state | 真后置 references/声明页保留 standard unit_id |
| source_seq owner 没门禁 | unit_range_audit 消费 standard anchors | critical owner mismatch 进入 unit_map.flags 和 verifier |

## 2. 不做什么

本轮不做：

```text
1. 不接入 live AI。
2. 不做 visual page policy。
3. 不把 standards/targets/** 当成 T2 inference 输入。
4. 不自动更新 signed standard 或 expected snapshot。
5. 不做 T3 正文内部章节解析。
6. 不恢复 T1 semantic fields。
```

核心原则：

```text
T2 算法只从源 DOCX 事实推断。
standard 只作为测试、metrics、verifier 的裁判。
```

## 3. standard 本次如何引入

### 3.1 输入位置

现有三校标准文件：

```text
standards/targets/hunannongye/v1/template_generation/t2_unit_pagination.standard.yaml
standards/targets/nannong-undergraduate/v1/template_generation/t2_unit_pagination.standard.yaml
standards/targets/pku-graduate/v1/template_generation/t2_unit_pagination.standard.yaml
```

本轮不新建孤立 `tests/fixtures/t2_expected_units/*.yaml` 作为主标准。

唯一权威来源是上面的 signed stage standard。测试可构造小 fixture，但三校回归必须读 `standards/targets/**/t2_unit_pagination.standard.yaml`。

### 3.2 接入层次

| 层次 | 引入方式 | 是否阻断 |
| --- | --- | --- |
| loader | 读取 stage standard，提取 `expected.unit_order`、`expected.units`、anchors、page policy | loader 失败为 UNKNOWN |
| metrics | `scripts/t2_metrics.py --standard-gate` 打印 expected vs actual | 初期 audit-only，仍明确 FAIL/UNKNOWN |
| unit tests | 用标准 loader 对三校 expected metadata 做 schema/一致性测试 | 阻断 |
| verifier | `verify_template_parse_build(..., t2_standard=...)` 或 harness wrapper 消费 standard diff | 阻断或 audit 取决于 `gate_enabled` |
| standards metadata | 代码闭环后再把 `verifier_state` / `gate_enabled` 作为单独 review change | 不自动改 |

### 3.3 gate_enabled 的处理

当前三校 standard 都是：

```text
verifier_state: not_configured
gate_enabled: false
```

本轮分两步：

```text
Step A：实现 audit。
即使 gate_enabled=false，也必须输出 standard diff report，不能显示为 PASS。

Step B：实现 gate。
当 T2 actual 通过 standard audit 后，再提交人工可 review 的 standard metadata 变更：
verifier_state: configured
gate_enabled: true
```

在 Step A 期间，报告状态建议：

```text
standard missing / invalid -> UNKNOWN
standard present but gate disabled -> audit-only，不覆盖已有结果，但显示 mismatch
gate enabled and mismatch -> FAIL
```

## 4. 状态机方案

### 4.1 状态定义

```text
front_matter:
  封面、声明、摘要、目录、图目录、表目录等正文前单元。

body_main:
  正文主体。进入后，章标题、节标题、说明性 heading 默认是 body_main 内部结构。

back_matter:
  参考文献、附录、成果、致谢、原创/授权声明等正文后单元。

post_forms:
  学校后置表单集合。仅用于不能稳定拆成 standard unit_id 的过渡状态，不能替代已签收 standard unit。

unknown:
  证据不足，需要 open_question 或 standard audit finding。
```

### 4.2 输入

状态机输入不是 raw paragraph，而是 preliminary anchors：

```text
entry + derived signals
canonical_label_hint
instruction_class
preliminary unit_id
taxonomy_scope
anchor evidence
list_block range
```

这样状态机只负责裁决“顶层单元边界是否成立”，不重复做标题识别。

### 4.3 转移规则

| 当前状态 | 触发 | 动作 |
| --- | --- | --- |
| `front_matter` | 命中 front unit | 保留顶层 unit |
| `front_matter` | 命中 `body_main` start 或正文章标题 | 进入 `body_main` |
| `body_main` | 命中 chapter/section heading，但不是 back label | 吸收到 `body_main` |
| `body_main` | 命中 `references` / `appendix` / `academic_achievements` / `acknowledgement` / declaration | 进入 `back_matter`，保留顶层 unit |
| `body_main` | 命中 duplicate `references`，但后续仍有正文式 heading/paragraph | 留在 `body_main`，记录 duplicate trace |
| `back_matter` | 命中后置 unit | 保留顶层 unit |
| `back_matter` | 命中正文式 heading | 生成 open_question，不直接重返 `body_main` |

### 4.4 输出

状态机输出：

```text
final_anchors
state_machine_trace
absorbed_anchor_refs
open_questions for ambiguous transitions
```

`state_machine_trace` 最小字段：

```yaml
- source_seq: 92
  raw_title: 插图、公式与表格
  from_state: body_main
  to_state: body_main
  preliminary_unit_id: custom:template:插图公式与表格:92
  final_unit_id: body_main
  decision: absorb_into_body_main
  reason: heading_inside_body_before_back_matter
```

### 4.5 关键门禁

```text
pku seq 50 / 92 / 221 / 302 -> body_main
pku seq 306 -> references
nannong seq 83 -> body_main
nannong seq 109 -> appendix
nannong seq 113 -> acknowledgement
```

## 5. 实施顺序

### Phase 0：标准 audit 先行

新增或修改：

```text
src/docfit/template_generation/t2_standard.py
tests/unit/test_t2_standard_loader.py
scripts/t2_metrics.py --standard-gate
```

要求：

```text
1. loader 从 standards/targets/<school>/v1/template_generation/t2_unit_pagination.standard.yaml 读取。
2. 校验 expected.unit_order == [unit.unit_id for unit in expected.units]。
3. 输出 expected ids、actual ids、missing、unexpected、custom_count。
4. 不把 standard 输入 build_template_structure_candidates()。
```

### Phase 1：taxonomy 对齐 standard

修改：

```text
src/docfit/template_generation/constants.py
src/docfit/template_generation/structure_candidates.py
```

新增或稳定这些 unit_id：

```text
body_title_block
figure_list
table_list
academic_achievements
copyright_notice
originality_statement
authorization_statement
originality_authorization_statement
design_task
proposal
proposal_record
defense_record
topic_change_approval
grade_form
```

要求：

```text
taxonomy_scope 区分 global_core / global_extended / school_expected / template_form。
custom 仍允许，但 custom 不能覆盖 standard expected unit_id。
```

### Phase 2：boundary canonical hint + instruction class

修改：

```text
canonical_title()
_structural_signals()
_boundary_decision()
_boundary_vetoes()
_label_boundaries()
```

新增概念：

```text
canonical_label_hint:
  boundary 阶段可见的 unit_id hint。

instruction_class:
  not_instruction
  pure_instruction
  title_with_format_annotation
  ambiguous_instruction_title
```

要求：

```text
title_with_format_annotation 不能硬 veto。
pure_instruction 仍可 veto 顶层 boundary。
canonical_label_hint + heading/style/break 任一强证据可打开 boundary。
```

### Phase 3：list-like block 拆分

修改：

```text
_segment_toc_blocks() -> _segment_list_like_blocks()
_toc_block_anchor() -> _list_block_anchor()
scripts/t2_metrics.py
```

要求：

```text
主目录 -> toc
图目录 -> figure_list
表目录 -> table_list
三者都复用 toc-entry-like coverage 逻辑，但最终 unit_id 必须不同。
```

### Phase 4：front/body/back 状态机

新增：

```text
reconcile_document_zones(preliminary_anchors, entries, list_blocks) -> final_anchors, trace
```

接线位置：

```text
_boundary_anchors()
  -> _label_boundaries()
  -> reconcile_document_zones()
  -> _infer_units()
```

要求：

```text
状态机只裁决顶层 unit 边界。
正文内部 heading 不丢失，仍通过 source_seq_refs 留在 body_main。
所有 absorb 决策写 trace。
歧义转移写 open_questions。
```

### Phase 5：range ownership audit

新增：

```text
unit_range_audit
expected_anchor_owner_results
critical_unowned_ranges
unit_map.flags for FAIL/UNKNOWN audit items
```

要求：

```text
标准 anchors.start_title / title_aliases 命中的 source_seq 必须有 owner。
owner 的 unit_id 必须匹配 expected unit。
不可靠 anchor 匹配只能 UNKNOWN，不能静默 PASS。
```

### Phase 6：verifier 闭环

修改：

```text
src/docfit/template_generation/verifier.py
src/docfit/template_generation/runner.py 或 harness wrapper
src/docfit/convert/orchestrator.py
```

建议路径：

```text
1. 保持 generate_template(source_template_docx, ...) 的 source-only 语义。
2. 在 run_template_generate_eval / harness 层已知 school_id 时加载 StandardBundle。
3. 把 T2 standard 作为 verifier input，而不是 generator input。
4. verify_template_parse_build 支持 optional t2_standard_audit。
```

要求：

```text
gate_enabled=false:
  输出 audit report，不阻断生成结果。

gate_enabled=true:
  expected mismatch / missing unit / critical owner mismatch -> T2 FAIL。
```

### Phase 7：standard metadata 收口

前置条件：

```text
三校 standard audit PASS。
T2 metrics old gate PASS。
contract/unit tests PASS。
真实生成 verification_report 不再出现 T2 standard mismatch。
```

然后才提交人工可 review 的标准元数据变更：

```text
verifier_state: configured
gate_enabled: true
```

## 6. 验收命令

最低门禁：

```text
uv run pytest tests/unit/test_t2_unit_map.py -q
uv run pytest tests/unit/test_t2_standard_loader.py -q
uv run python scripts/t2_metrics.py
uv run python scripts/t2_metrics.py --standard-gate
```

真实生成门禁：

```text
uv run pytest tests/contract/test_template_generate.py -q
```

如果新增 harness-level standard verification：

```text
uv run pytest tests/contract/test_real_core_baseline_harness.py -q
```

## 7. 验收口径

### 湖南农大

```text
body_title_block 存在。
abstract_cn 存在，摘□要 anchor 归 abstract_cn。
references / acknowledgement / appendix / 后置表单 unit_id 与 standard 对齐。
toc 继续不包含 seq 50-64。
```

### 南京农业大学本科

```text
originality_statement / authorization_statement 与 standard 对齐。
appendix 存在。
academic_achievements 不再 custom。
acknowledgement 存在。
第X章结论与展望 归 body_main。
```

### 北京大学研究生

```text
copyright_notice 存在。
toc / figure_list / table_list 独立。
研究背景、插图公式与表格、其他注意事项、结论与讨论归 body_main。
后置参考文献 seq 306 归 references。
originality_authorization_statement 存在。
custom_count 明显下降，且剩余 custom 都有 review reason。
```

## 8. 失败处理

如果 Phase 4 状态机导致误吞后置单元：

```text
不要回退到纯 keyword patch。
先看 state_machine_trace，补 back_matter transition evidence。
```

如果 standard anchor 匹配不可靠：

```text
不要让 gate PASS。
标 UNKNOWN，写 open_question 或 audit finding。
```

如果某个 standard unit 确实需要改名：

```text
不要在实现里硬兼容两个名字。
先开 standard change review，更新 standard 后再改 taxonomy。
```
