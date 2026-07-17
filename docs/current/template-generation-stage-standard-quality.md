# 模板生成阶段标准质量衡量

Last updated: 2026-06-28

一句话结论：阶段标准质量衡量不是让 AI 自己看标准，也不是 `template-generate` 运行时自动产生的 verify 报告。当前已有两类确定性输出：`template-generation-standard-quality` 输出标准集聚合质量报告；`template-generation-judge` 针对某次 run bundle 输出和阶段产物编号对齐的 `*_standard_quality_report.{json,md}`。real-core 三校 T1-T5 阶段 verifier 已配置并开启 gate；如果 audit 发现 signed standard mismatch，报告必须写出 `standard_acceptance_status=FAIL`、`signoff_status=NOT_SIGNABLE`、`owner_summary` 和 `top_blockers`，不能被 AI 改写成通过。

## 文档范围

本文只讲 T1-T5 模板生成阶段标准本身的质量衡量：

```text
standards/targets/<target_id>/v1/template_generation/t1_document_facts.standard.yaml
standards/targets/<target_id>/v1/template_generation/t2_unit_pagination.standard.yaml
standards/targets/<target_id>/v1/template_generation/t3_element_policy.standard.yaml
standards/targets/<target_id>/v1/template_generation/t4_global_layout.standard.yaml
standards/targets/<target_id>/v1/template_generation/t5_template_spec.standard.yaml
```

不包含这两类运行报告：

| 不属于本文 | 为什么 |
| --- | --- |
| `07_verification_report.json` | 这是 `template-generate` 伴随某次运行产生的产物检查结果 |
| `template_gap_report.*` | 这是 `template-gap` 对最终 Word 的学校格式差距检查 |

## 现在已经有的

当前已有的是“标准静态质量底座”，不是完整的产品化质量衡量。

| 已有内容 | 位置 | 已经能证明什么 |
| --- | --- | --- |
| baseline 文件通用静态校验 | `src/docfit/harness/baselines.py::validate_baseline_document` | 标准有 `review_metadata`、禁止自动更新、source hash 格式正确、声明了 `dimensions[]`、comparator mode 可识别 |
| target 标准和 contract 审计入口 | `docfit eval standards` | `target.standard.yaml`、contracts 和 coverage requirements 可加载；当前不深入审 T1-T5 阶段标准内容 |
| 三校阶段标准登记合同测试 | `tests/contract/test_real_core_baseline_harness.py` | 三校只登记 `t1_document_facts` 到 `t5_template_spec`，旧 01-05 expected 文件不存在，baseline type、stage id、artifact under test、legacy flag、`verifier_state=configured`、`gate_enabled=true` 正确 |
| 标准集聚合质量命令 | `docfit eval template-generation-standard-quality` | 读取 profile 或单校标准集，输出 `template_generation_stage_standard_quality_report.{json,md}` |
| 某次 run 的标准裁判命令 | `docfit eval template-generation-judge` | 读取同一个 run bundle，输出 `template_generation_stage_checks.json` 和编号化 `*_standard_quality_report.{json,md}` |
| T1 特殊边界测试 | `tests/contract/test_real_core_baseline_harness.py` | T1 标准声明 `artifact_type: document_facts`，且禁用 `unit_id`、`policy`、`confidence` 等语义判断字段 |
| T2-T5 单元顺序一致性测试 | `tests/contract/test_real_core_baseline_harness.py` | T2-T5 的 `expected.unit_order` 与 `template_quality/final_template.expected.yaml#/expected/units` 一致 |
| T3 固定块局部填空边界 | `tests/unit/test_template_generation_stage_verifiers.py` | `fixed_units` 默认不能出现 fill；只有标准显式写入 `fixed_units_allow_fill_elements` 的单元，才允许固定模板块内部存在局部 fill 元素 |
| 标准文件落位规范 | `docs/current/template-generation-stage-standards.md`、`standards/README.md` | 人知道文件应该放哪里、叫什么、给哪个阶段用 |

现在能用的命令是这些：

```bash
uv run pytest tests/contract/test_real_core_baseline_harness.py -q
```

这条命令可以证明 real-core 三校阶段标准登记和基本结构没有跑偏。

```bash
uv run docfit eval standards --school hunannongye --out runs/eval/standards_audit
```

这条命令可以审学校 `target.standard.yaml` 和 contracts，但目前还不是 T1-T5 阶段标准质量衡量命令。

## 现在还没有的

当前缺少的是“更深的阶段标准质量产品化能力”。正式入口已经能读取三校 T1-T5 标准、对某次 run 输出阶段裁判报告，并且 real-core T1-T5 已进入 gate；但标准文件自身的深层 hash/引用审计和 T6/T7 阶段标准仍未补齐。

| 缺口 | 说明 |
| --- | --- |
| 阶段类型深校验仍有限 | 例如 T1 必须有 `forbidden_semantic_fields`，T3 必须有 `element_policy_contract`，T4 必须有 `global_layout_contract`，T5 必须有 `template_spec_contract`，这些还需要继续扩展确定性检查 |
| 没有 hash 反查审计 | 标准里写的源模板、review packet、final template 引用和 sha256，还没有在阶段标准质量检查里逐项重新计算验证 |
| 阶段质量深校验仍需扩展 | real-core T1-T5 gate 已开启，但标准质量检查仍需继续补 source/review/final template hash 反查 |
| T6/T7 还没有阶段标准 | `06.1_fillable_template.docx`、`06.2_build_manifest.json`、`07_verification_report.json` 当前只能做 run bundle 证据绑定，不能伪装成已有阶段标准比较 |

所以，目前不能说“阶段标准质量衡量已经产品化”。更准确的状态是：

```text
已有静态校验函数、CLI、聚合质量报告、编号化 run 报告、合同测试和 real-core T1-T5 gate；
缺少更深的标准文件 hash 反查审计和 T6/T7 阶段标准。
```

## 不由 AI 裁判

阶段标准质量衡量后续应该由代码执行，不应该靠 AI 自己看。

AI 可以做这些事：

- 解释质量报告。
- 帮人定位标准文件里的疑似问题。
- 帮人写修复建议。
- 帮人补文档或测试。

AI 不可以做这些事：

- 不可以把缺标准判成通过。
- 不可以补造 hash、review 来源或状态。
- 不可以绕过未配置或关闭的 gate；real-core T1-T5 当前应读取 `configured/true`。
- 不可以把当前运行产物反写成标准。
- 不可以代替阶段 verifier 输出 `PASS`。

换句话说，AI 是读报告的人，不是产生裁判结果的裁判。

T3 的 `fixed_units` 语义需要特别小心：它表示单元整体版面或固定结构属于学校模板块，不等于内部每个元素都必须是 `fixed`。例如三校封面都仍属于 `fixed_units`，但标准显式声明 `fixed_units_allow_fill_elements: [cover]`，所以题名、学生信息等明确填空位可以生成 `fill` 元素；诚信声明、授权声明、后置人工表单仍由 `manual_only_units` 约束，不能因为封面例外而放宽。

## 补全后的逻辑

建议补一个确定性模块，负责“标准本身是否合格”：

```text
target.standard.yaml
  -> template_generation_stages refs
  -> T1-T5 standard yaml
  -> final_template.expected.yaml
  -> source/review/hash references
  -> template_generation_stage_standard_quality_report.json
```

它不读取本次 `template-generate` 的 `01_document_facts.json`、`02_unit_map.yaml`、`05_template_spec.yaml`。这些是阶段 verifier 的输入，不是标准质量衡量的输入。

建议检查顺序：

| 顺序 | 检查 | 失败或缺失时 |
| --- | --- | --- |
| 1 | 读取 `target.standard.yaml` 的 `evidence_baselines.template_generation_stages` | 缺登记为 `UNKNOWN` |
| 2 | 确认只登记 `t1_document_facts` 到 `t5_template_spec` | 登记旧入口为 `FAIL` 或阻断 |
| 3 | 确认每个登记文件存在、可解析 YAML | 缺文件或 YAML 无效为 `UNKNOWN` |
| 4 | 运行 `validate_baseline_document` | 静态 baseline 结构不合格为 `UNKNOWN` |
| 5 | 检查 `baseline_type`、`stage_id`、`artifact_under_test` 与登记键一致 | 不一致为 `FAIL` |
| 6 | 检查 `legacy_compatibility: false` 和旧文件不存在 | 旧路径存在或声明兼容为 `FAIL` |
| 7 | 检查每阶段专属 contract | 缺少本阶段关键 contract 为 `UNKNOWN` |
| 8 | 检查 source/review/final template 引用和 hash | 文件缺失或 hash 不一致为 `UNKNOWN` |
| 9 | 检查 T2-T5 unit order 与 final template 一致 | 不一致为 `FAIL` |
| 10 | 检查 T1 禁用语义字段清单 | 缺禁用字段为 `FAIL` |

状态建议：

| 状态 | 含义 |
| --- | --- |
| `PASS` | 标准文件作为裁判口径是完整、可追溯、登记一致的 |
| `FAIL` | 标准文件和阶段边界或登记规则明确冲突 |
| `UNKNOWN` | 缺文件、缺 hash、缺 metadata、缺 contract、缺 verifier 能读的维度 |

## 和其他环节如何耦合

阶段标准质量衡量应该是阶段 verifier 的前置条件，而不是模板生成业务流程的一部分。

```text
标准质量衡量
  -> 证明“裁判口径能不能用”

阶段 verifier
  -> 读取“可用的标准” + “某次运行产物”
  -> 输出某阶段 PASS/FAIL/UNKNOWN

template-generate
  -> 只生产产物，不读取学校标准

template-gap
  -> 读取最终 Word + final_template.expected.yaml
  -> 输出最终模板差距
```

耦合关系：

| 环节 | 如何耦合 |
| --- | --- |
| `standards/targets/<target>/v1/target.standard.yaml` | 标准质量衡量从这里找 T1-T5 标准入口 |
| `template_quality/final_template.expected.yaml` | T2-T5 的 unit order 必须和这里一致 |
| `inputs/targets/<target>/raw/source_template.docx` | 标准里的源 DOCX hash 应能回查到这里 |
| `docs/human/real-core-v0-review-packet.md` | 标准里的人工 review 来源应能回查到这里 |
| T1-T5 阶段 verifier | 先检查标准质量；标准质量不是 `PASS` 时，该阶段不能输出 `PASS` |
| `coverage.py` 或后续聚合报告 | profile 级报告应该能展示哪些学校标准可用，哪些标准缺失或不合格 |
| AI RCA | 只能消费质量报告和 verifier 报告做解释，不写裁判结果 |

## 如何调用

### 当前调用

当前已有专用产品命令，也可以用合同测试覆盖基础结构：

```bash
uv run pytest tests/contract/test_real_core_baseline_harness.py -q
```

用途：检查三校阶段标准登记、基本结构和 gate 元数据。

```bash
uv run docfit eval standards \
  --school hunannongye \
  --out runs/eval/standards_audit
```

用途：检查学校标准 bundle 和 contracts。注意，它不替代 `template-generation-standard-quality` 的 T1-T5 阶段标准质量报告。

### 当前标准集质量调用

标准集聚合质量命令用于审标准文件本身，不绑定某一次 `template-generate` run：

```bash
uv run docfit eval template-generation-standard-quality \
  --profile real-core-v0 \
  --out runs/eval/template_generation_standard_quality/real-core-v0
```

也支持单校：

```bash
uv run docfit eval template-generation-standard-quality \
  --school hunannongye \
  --out runs/eval/template_generation_standard_quality/hunannongye
```

输出：

```text
runs/eval/.../
  summary.json
  findings.json
  template_generation_stage_standard_quality_report.json
  template_generation_stage_standard_quality_report.md
```

报告至少包含：

| 字段 | 含义 |
| --- | --- |
| `profile_id` | 例如 `real-core-v0` |
| `targets[]` | 每所学校的标准质量结果 |
| `stage_standards[]` | T1-T5 每份标准路径、hash、状态和 findings |
| `legacy_files` | 旧入口是否仍存在 |
| `source_bindings` | 源模板、review packet、final template 的引用和 hash 检查 |
| `cross_file_checks` | target 登记、stage metadata、unit order 等跨文件一致性 |
| `status` | 聚合后的 `PASS`、`FAIL`、`UNKNOWN` |

### 当前 run bundle 裁判输出

某一次 `template-generate` run 的裁判命令必须和 run bundle 共址：

```bash
RUN_ROOT=test_outputs/debug/template_generation/manual_hunannongye

uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run "$RUN_ROOT/eval_runs/template_generate" \
  --out "$RUN_ROOT/eval_runs/template_generation_judge"
```

输出目录除聚合文件外，还必须包含和阶段产物编号对齐的报告：

```text
test_outputs/debug/template_generation/<run_id>/eval_runs/template_generation_judge/
  template_generation_judge_report.json
  template_generation_stage_checks.json
  template_generation_run_bundle.json
  template_generation_stage_standard_quality_report.json
  00_template_generation_request_standard_quality_report.json
  01_document_facts_standard_quality_report.json
  02_unit_map_standard_quality_report.json
  03_element_spec_standard_quality_report.json
  04_global_spec_standard_quality_report.json
  05_template_spec_standard_quality_report.json
  06.1_fillable_template_standard_quality_report.json
  06.2_build_manifest_standard_quality_report.json
  07_verification_report_standard_quality_report.json
```

## 名称规范

### 标准文件

标准文件统一命名：

```text
t<stage_number>_<stage_topic>.standard.yaml
```

当前固定清单：

| stage key | 文件名 | baseline_type | stage_id | artifact_under_test |
| --- | --- | --- | --- | --- |
| `t1_document_facts` | `t1_document_facts.standard.yaml` | `template_generation_t1_document_facts` | `T1` | `document_facts` |
| `t2_unit_pagination` | `t2_unit_pagination.standard.yaml` | `template_generation_t2_unit_pagination` | `T2` | `unit_map` |
| `t3_element_policy` | `t3_element_policy.standard.yaml` | `template_generation_t3_element_policy` | `T3` | `element_spec` |
| `t4_global_layout` | `t4_global_layout.standard.yaml` | `template_generation_t4_global_layout` | `T4` | `global_spec` |
| `t5_template_spec` | `t5_template_spec.standard.yaml` | `template_generation_t5_template_spec` | `T5` | `template_spec` |

旧数字 expected 文件不得恢复：

```text
01_source_parse.expected.yaml
02_structure_discovery.expected.yaml
03_generation_model.expected.yaml
04_plan_build.expected.yaml
05_action_execution.expected.yaml
```

### 标准质量报告

标准集聚合质量报告使用：

```text
template_generation_stage_standard_quality_report.json
template_generation_stage_standard_quality_report.md
```

某次 run bundle 的阶段产物质量报告使用：

```text
<阶段产物编号和名称>_standard_quality_report.{json,md}
```

例如：

```text
02_unit_map_standard_quality_report.json
06.1_fillable_template_standard_quality_report.json
```

不要叫：

```text
07_verification_report.json
template_gap_report.json
```

这两个名字已经属于运行产物检查和最终 gap 检查。

### finding 类型

建议 finding type 使用这个前缀：

```text
template_generation_stage_standard_quality_*
```

示例：

| finding type | 含义 |
| --- | --- |
| `template_generation_stage_standard_quality_missing_ref` | `target.standard.yaml` 缺阶段标准登记 |
| `template_generation_stage_standard_quality_legacy_file_present` | 旧 expected 文件仍存在 |
| `template_generation_stage_standard_quality_type_mismatch` | `baseline_type`、`stage_id` 或 `artifact_under_test` 不匹配 |
| `template_generation_stage_standard_quality_missing_contract` | 阶段专属 contract 缺失 |
| `template_generation_stage_standard_quality_hash_mismatch` | source/review/final template hash 不一致 |
| `template_generation_stage_standard_quality_unit_order_mismatch` | T2-T5 unit order 与 final template 不一致 |
| `template_generation_stage_standard_quality_t1_semantic_boundary_gap` | T1 禁用语义字段清单不完整 |

### 代码位置

当前模块：

```text
src/docfit/harness/template_generation_standard_quality.py
```

当前主要函数：

```python
evaluate_template_generation_standard_quality(standard_set: TemplateGenerationStandardSet) -> TemplateGenerationStandardQualityReport
evaluate_template_generation_standard_quality_for_profile(root: Path, profile_id: str, template_version: str) -> TemplateGenerationStandardQualityReport
```

CLI 只负责参数解析和写报告，不拥有检查语义。

## 补全顺序

1. 已完成：新增 `template_generation_standard_quality.py`，实现读取登记、文件存在、旧入口不存在和 `validate_baseline_document`。
2. 已完成：增加 `docfit eval template-generation-standard-quality` CLI，并支持 profile / 单校输出聚合质量报告。
3. 已完成：`template-generation-judge` 读取标准质量结果；不是 `PASS` 时，阶段结果最多只能是 `UNKNOWN`。
4. 已完成：real-core T1-T5 阶段 verifier 接入 `template-generation-judge`，并在标准元数据中开启 `gate_enabled=true`。
5. 待扩展：增加 source/review/final template hash 反查审计。
6. 待扩展：把 `template-gap` 的最终 Word 检查作为 `06_final_template_gap` 合并进同一聚合视图。

当前 real-core T1-T5 已经从“有产品报告”推进到“阶段质量 gate”；完整产品化还需要补最终 Word 聚合和更深 hash 反查审计。
