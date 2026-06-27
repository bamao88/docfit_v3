---
status: draft
owner: template-generation
stage: standard-judge
topic: template-generation-standard-judge
issue_id: STANDARD-JUDGE-ISSUE-01
issue_sequence: 1
created: 2026-06-27
last_updated: 2026-06-27
version: 1
previous_issue:
  id: none
  doc: none
previous_optimization:
  doc: none
  summary: none
next_plan:
  id: TBD
  doc: TBD
  summary: 基于本文档拆出标准质量、run bundle、阶段 verifier 和聚合报告的实施计划。
related_docs:
  - docs/current/template-generation-stage-standards.md
  - docs/current/template-generation-stage-standard-quality.md
  - docs/current/template-generation-evaluation.md
  - docs/current/project-directory-structure.md
related_code:
  - src/docfit/harness/standards.py
  - src/docfit/harness/baselines.py
  - src/docfit/template_generation/runner.py
  - src/docfit/template_generation/verifier.py
  - src/docfit/template_generation/outputs.py
  - src/docfit/template_generation/t2_standard.py
---

# 模板生成标准裁判 Issue 01：Run Bundle + 阶段标准 Verifier + 聚合闭环

## 0. 一句话结论

标准裁判模块是一个独立 harness 能力：

```text
已签收阶段标准 + 某一次 template-generate 运行产物
  -> T1-T5 阶段裁判
  -> PASS / FAIL / UNKNOWN
  -> findings + first_bad_stage + 可追踪输出报告
```

它不是模板生成器的一部分，不把 `standards/targets/**` 当作生成输入，也不自动更新标准。

## 1. 真实运行口径

本模块只消费两类稳定包。

### 1.1 标准包

入口：

```text
standards/targets/<target_id>/v1/target.standard.yaml
```

阶段标准：

```text
standards/targets/<target_id>/v1/template_generation/
  t1_document_facts.standard.yaml
  t2_unit_pagination.standard.yaml
  t3_element_policy.standard.yaml
  t4_global_layout.standard.yaml
  t5_template_spec.standard.yaml
```

最终质量标准：

```text
standards/targets/<target_id>/v1/template_quality/final_template.expected.yaml
```

### 1.2 运行包

输入是一整个已有 `template-generate` run 目录，不能从零散文件自动拼装。

推荐命令形态：

```bash
uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run runs/template_generation/hunannongye/eval_runs/template_generate \
  --out runs/eval/template_generation_judge/hunannongye/template_generate
```

运行包至少包含：

```text
<run>/
  00_template_generation_request.json
  01_document_facts.json
  02_unit_map.yaml
  03_element_spec.yaml
  04_global_spec.yaml
  05_template_spec.yaml
  06.1_fillable_template.docx
  06.2_build_manifest.json
  07_verification_report.json
  artifacts/
    document_facts.json
    unit_map.yaml
    element_spec.yaml
    global_spec.yaml
    template_spec.yaml
    build_manifest.json
    verification_report.json
```

优先读取顶层阶段编号文件；缺顶层文件时可读 `artifacts/` 兼容路径，但报告必须记录实际读取路径和 hash。

## 2. Expected vs Observed

| 项 | Expected | Observed |
| --- | --- | --- |
| 标准准备 | 三校 T1-T5 标准可被统一加载、校验和引用 | 标准文件已存在，`target.standard.yaml` 已登记，合同测试覆盖基本结构 |
| 标准质量 | 有独立质量报告证明标准本身可作为裁判 | 只有静态 baseline 校验和合同测试，没有产品化报告 |
| run 绑定 | 裁判读取同一次 `template-generate` run 产物并记录 hash | 目前没有 run bundle binder |
| 阶段裁判 | T1-T5 分别消费对应标准和产物，输出阶段 check | 内置 `verification_report` 只做结构检查，不读学校标准 |
| T2 裁判 | T2 standard audit 可进入聚合报告 | 已有 `t2_standard.py` 初步 audit，但未接入主报告 |
| T1/T3/T4/T5 | 均有标准 verifier | 尚未实现 |
| 聚合闭环 | 报告能定位 first_bad_stage 并转成 issue 的 expected/observed | 目前最终 gap 失败后仍主要靠人工回查 |

## 3. 疑似根因

```text
1. 生成器、标准文件、最终 gap 已经各自存在，但中间缺一个稳定 harness 层。
2. 当前 verification_report 是 run 内置自检，不是学校阶段标准裁判。
3. 标准质量、run 证据绑定、阶段 verifier、聚合报告四件事还没有分层实现。
4. T2 的脚手架证明方向可行，但如果只沿 T2 局部继续补，会遮住整个标准裁判模块的边界。
```

## 4. 上一轮已解决 / 未解决对照

| 类别 | 已解决 | 未解决 |
| --- | --- | --- |
| 标准落位 | 三校 T1-T5 标准文件已按新命名落在 `standards/targets/<target>/v1/template_generation/` | 标准质量报告未产品化 |
| 标准登记 | `target.standard.yaml#/evidence_baselines/template_generation_stages` 已登记新入口 | 缺 profile/school 级统一报告 |
| 产物链 | `template-generate` 已能输出 `document_facts` 到 `template_spec`、`fillable_template`、`build_manifest`、`verification_report` | 缺 run bundle hash 绑定和“同一次 run”证明 |
| verifier | T1-T6 内置三态自检已存在 | 学校阶段标准 verifier 未接入 |
| T2 | 已有 T2 standard loader/audit 单测 | 不作为整体模块核心；仍需统一接口接入 |
| 文档 | 已说明阶段标准不是生成输入 | 缺标准裁判完整模块计划、目录树、输出位置和命名规范 |

## 5. 模块目录与文件命名

建议新增 harness 模块：

```text
src/docfit/harness/
  template_generation_standard_judge.py
  template_generation_standard_quality.py
  template_generation_run_bundle.py
  template_generation_stage_verifiers.py
  template_generation_judge_reports.py
```

职责：

| 文件 | 职责 |
| --- | --- |
| `template_generation_standard_judge.py` | 主入口，串联标准加载、质量检查、run 绑定、阶段裁判、报告输出 |
| `template_generation_standard_quality.py` | 检查标准文件本身：登记、存在、metadata、hash、旧入口、unit order |
| `template_generation_run_bundle.py` | 绑定某次 run 的产物路径、hash、artifact source 和缺失项 |
| `template_generation_stage_verifiers.py` | T1-T5 阶段 verifier，输入标准 + 产物，输出 stage check |
| `template_generation_judge_reports.py` | 聚合报告、Markdown 报告、summary/findings 输出 |

测试：

```text
tests/unit/test_template_generation_standard_quality.py
tests/unit/test_template_generation_run_bundle.py
tests/unit/test_template_generation_stage_verifiers.py
tests/contract/test_template_generation_standard_judge.py
```

CLI：

```text
docfit eval template-generation-judge
docfit eval template-generation-standard-quality
```

## 6. 输出位置

### 6.1 标准质量检查输出

标准质量检查不读取某次 run，只检查标准本身。

Profile 级：

```bash
uv run docfit eval template-generation-standard-quality \
  --profile real-core-v0 \
  --out runs/eval/template_generation_standard_quality/real-core-v0
```

单校：

```bash
uv run docfit eval template-generation-standard-quality \
  --school hunannongye \
  --out runs/eval/template_generation_standard_quality/hunannongye
```

输出：

```text
runs/eval/template_generation_standard_quality/<scope>/
  summary.json
  findings.json
  template_generation_stage_standard_quality_report.json
  template_generation_stage_standard_quality_report.md
```

### 6.2 标准裁判输出

标准裁判读取某次 `template-generate` run。

推荐输出目录：

```text
runs/eval/template_generation_judge/<target_id>/<source_run_id>/
```

示例：

```bash
uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run runs/template_generation/hunannongye/eval_runs/template_generate \
  --out runs/eval/template_generation_judge/hunannongye/template_generate
```

输出：

```text
runs/eval/template_generation_judge/hunannongye/template_generate/
  summary.json
  findings.json
  template_generation_run_bundle.json
  template_generation_stage_checks.json
  template_generation_standard_quality_report.json
  template_generation_judge_report.json
  template_generation_judge_report.md
```

命名规则：

| 产物 | 命名 |
| --- | --- |
| 标准质量报告 | `template_generation_stage_standard_quality_report.{json,md}` |
| run 绑定报告 | `template_generation_run_bundle.json` |
| 阶段裁判列表 | `template_generation_stage_checks.json` |
| 聚合裁判报告 | `template_generation_judge_report.{json,md}` |
| CLI 输出目录 | `runs/eval/template_generation_judge/<target_id>/<source_run_id>/` |

## 7. 整体流程

```text
load_standard_set
  target.standard.yaml
  -> T1-T5 StageStandard paths

evaluate_standard_quality
  StageStandard files + final_template.expected.yaml
  -> template_generation_stage_standard_quality_report

bind_run_bundle
  existing template-generate run dir
  -> BoundArtifact paths + hashes + missing evidence

run_stage_judges
  StageStandard + BoundArtifact + context
  -> StageCheck[T1..T5]

aggregate_judgement
  standard_quality + run_bundle + stage_checks
  -> judge_report + summary + findings + first_bad_stage
```

## 8. 数据转换模型

核心转换链：

```text
StageStandard YAML
  -> StageStandardSpec
  -> StageExpectation

Run artifact file
  -> BoundArtifact
  -> ActualObservation

StageExpectation + ActualObservation
  -> StageFinding[]
  -> StageCheck

StageCheck[]
  -> JudgeReport
```

建议内部结构：

```python
@dataclass
class StageStandardSpec:
    stage_key: str
    stage_id: str
    path: Path
    sha256: str
    verifier_state: str
    gate_enabled: bool
    artifact_under_test: str
    expected: dict[str, Any]


@dataclass
class BoundArtifact:
    artifact_key: str
    stage_id: str
    path: Path | None
    sha256: str | None
    status: Status
    payload: dict[str, Any] | None


@dataclass
class StageCheck:
    stage_key: str
    stage_id: str
    verifier_state: str
    gate_enabled: bool
    standard_path: Path | None
    artifact_path: Path | None
    status: Status
    audit_status: str | None
    findings: list[Finding]
```

## 9. 阶段输入输出

| 阶段 | 标准输入 | 运行输入 | 上下文输入 | 裁判输出 |
| --- | --- | --- | --- | --- |
| T1 | `t1_document_facts.standard.yaml` | `document_facts.json` | 源模板 hash、request | artifact type、事实覆盖、禁用语义字段、trace/hash findings |
| T2 | `t2_unit_pagination.standard.yaml` | `unit_map.yaml` | `document_facts.json`、source tree | unit order、missing/unexpected units、boundary、page policy、anchor owner |
| T3 | `t3_element_policy.standard.yaml` | `element_spec.yaml` | `unit_map.yaml` | policy、fill_source、manual_semantics、generated.field_type、source trace |
| T4 | `t4_global_layout.standard.yaml` | `global_spec.yaml` | `document_facts.json` | section profile、page numbering、header/footer、numbering、page evidence |
| T5 | `t5_template_spec.standard.yaml` | `template_spec.yaml` | T2/T3/T4 artifacts | unit/element/global 合并、unit-section 绑定、review flags 保留 |

## 10. 核心代码形状

主入口：

```python
def judge_template_generation_run(
    root: Path,
    school_id: str,
    run_dir: Path,
    out_dir: Path,
    template_version: str = "v1",
) -> StageResult:
    standard_set = load_template_generation_standard_set(
        root,
        school_id,
        template_version,
    )
    standard_quality = evaluate_template_generation_standard_quality(standard_set)
    run_bundle = bind_template_generation_run_bundle(run_dir)

    stage_checks = [
        judge_stage(
            stage_key=stage_key,
            standard=standard_set.stages.get(stage_key),
            artifact=run_bundle.artifacts.get(stage_key),
            context=run_bundle,
            standard_quality=standard_quality,
        )
        for stage_key in [
            "t1_document_facts",
            "t2_unit_pagination",
            "t3_element_policy",
            "t4_global_layout",
            "t5_template_spec",
        ]
    ]

    report = aggregate_template_generation_judgement(
        standard_set=standard_set,
        standard_quality=standard_quality,
        run_bundle=run_bundle,
        stage_checks=stage_checks,
    )
    write_template_generation_judge_outputs(out_dir, report)
    return report.to_stage_result()
```

阶段分派：

```python
def judge_stage(...) -> StageCheck:
    if standard is None:
        return missing_standard_check(...)
    if artifact is None or artifact.payload is None:
        return missing_artifact_check(...)
    if standard.verifier_state == "not_configured":
        return not_configured_check_or_audit(...)

    return {
        "t1_document_facts": judge_t1_document_facts,
        "t2_unit_pagination": judge_t2_unit_pagination,
        "t3_element_policy": judge_t3_element_policy,
        "t4_global_layout": judge_t4_global_layout,
        "t5_template_spec": judge_t5_template_spec,
    }[stage_key](standard, artifact, context)
```

聚合：

```python
def aggregate_template_generation_judgement(...) -> JudgeReport:
    stage_statuses = [check.status for check in stage_checks]
    first_bad_stage = first_stage_with_status(stage_checks, {FAIL, UNKNOWN})
    status = merge_statuses(stage_statuses)
    return JudgeReport(...)
```

## 11. 状态规则

| 情况 | 阶段状态 |
| --- | --- |
| 阶段标准缺失 | `UNKNOWN` |
| 阶段标准 YAML 无效 | `UNKNOWN` |
| 标准质量不是 `PASS` | `UNKNOWN` |
| run 产物缺失 | `UNKNOWN` |
| run 产物不是同一次运行或 hash 绑定失败 | `UNKNOWN` |
| `verifier_state=not_configured` | `UNKNOWN`；可附带 `audit_status`，不能 `PASS` |
| `gate_enabled=false` 且 audit mismatch | `audit_status=FAIL`，聚合报告展示，但不写成 enabled gate PASS |
| verifier enabled 且 mismatch | `FAIL` |
| verifier enabled 且全部满足 | `PASS` |

聚合规则：

```text
任一 enabled stage FAIL -> judge FAIL
任一 stage UNKNOWN -> judge UNKNOWN，除非调用方明确只请求 audit summary
没有 configured verifier 的阶段不能让总报告宣称全链路 PASS
```

## 12. 后续验收门禁

最小闭环门禁：

```text
1. 标准质量命令能输出三校 stage standard quality report。
2. 标准裁判命令能绑定已有 template-generate run，缺产物时输出 UNKNOWN。
3. T1-T5 都有 StageCheck，占位阶段也必须显示 not_configured，不可消失。
4. T2 现有 audit 通过统一 StageCheck 出现在 judge report。
5. 报告能写出 first_bad_stage、标准路径、产物路径、hash 和 findings。
6. 所有输出进入 runs/eval/template_generation_judge/**，不写 standards/ 或 inputs/。
7. 不修改 `standards/targets/**`，不自动重跑 template-generate。
```

代码验证建议：

```bash
uv run pytest tests/unit/test_template_generation_standard_quality.py -q
uv run pytest tests/unit/test_template_generation_run_bundle.py -q
uv run pytest tests/unit/test_template_generation_stage_verifiers.py -q
uv run pytest tests/contract/test_template_generation_standard_judge.py -q
```

人工验收建议：

```bash
uv run docfit eval template-generate \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --out runs/template_generation/hunannongye/eval_runs/template_generate

uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run runs/template_generation/hunannongye/eval_runs/template_generate \
  --out runs/eval/template_generation_judge/hunannongye/template_generate
```

验收时应能在输出目录看到：

```text
summary.json
findings.json
template_generation_run_bundle.json
template_generation_stage_checks.json
template_generation_judge_report.json
template_generation_judge_report.md
```
