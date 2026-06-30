---
status: draft
owner: template-generation
stage: run-bundle
topic: template-generation-run-bundle-contract
doc_type: implementation_plan
plan_id: RUN-BUNDLE-PLAN-01
created: 2026-06-28
last_updated: 2026-06-28
related_issue:
  id: RUN-BUNDLE-ISSUE-01
  doc: docs/plans/template-parse-refactor-run-bundle-template-generation-contract-issue-01-co-located-outputs.md
previous_issue:
  id: RUN-BUNDLE-ISSUE-01
  doc: docs/plans/template-parse-refactor-run-bundle-template-generation-contract-issue-01-co-located-outputs.md
previous_optimization:
  doc: none
  summary: none
related_code:
  - src/docfit/convert/orchestrator.py
  - src/docfit/template_generation/outputs.py
  - src/docfit/harness/template_generation_run_bundle.py
  - src/docfit/harness/template_generation_judge_reports.py
  - tests/contract/test_template_generate.py
  - tests/contract/test_template_generation_standard_judge.py
---

# Run Bundle Plan 01：模板生成运行包契约分阶段执行

## 0. 总目标

把一次 `template-generate` 运行产生的所有材料收束成一个可复制、可审计、可被后续评测读取的 run bundle。

目标目录形态：

```text
test_outputs/debug/template_generation/<run_id>/
  eval_runs/
    template_generate/
    template_gap/
    template_generation_judge/
  human/
    <timestamp>/
  run_bundle_manifest.json optional
```

这里的 `<run_id>` 是一次模板生成工作的归档根。`eval_runs/` 放机器可读、可重跑的阶段输出和评测输出；`human/` 放本次运行伴随产生的人读/debug 快照。两者必须在同一个 run root 下，不能散到 `runs/template_generation/**`。

## 1. 阶段拆解总览

| 阶段 | 名称 | 目标 | 主要交付 |
| --- | --- | --- | --- |
| P0 | 契约定名与边界 | 明确这件事叫“模板生成运行包契约”，区别于 AI 集成和标准裁判 | issue / plan / 索引命名统一 |
| P1 | Run root 推导 | 从 `--out` 稳定反推出同一个 bundle root | `_bundle_root_from_output_dir()`、合同测试 |
| P2 | 产物落盘布局 | `template_generate` 公开产物进 `eval_runs/`，debug/human 伴随产物进 `human/` | 输出路径调整、debug index |
| P3 | 后续 eval 共址 | `template-gap`、`template-generation-judge` 等后续报告进入同一 run root 的 `eval_runs/` | 文档命令、裁判输出目录规则 |
| P4 | 报告命名对齐 | 阶段报告文件名与阶段产物编号对齐 | `*_standard_quality_report.{json,md}` 命名矩阵 |
| P5 | Run bundle 证据绑定 | 后续 standard judge 能证明自己读取的是同一次 run 的产物 | run bundle binder / manifest / hash check |
| P6 | 文档与目录策略同步 | README/current/plan 不再推荐旧散落路径 | README、current docs、issue index |
| P7 | 验收门禁 | 用自动测试和三校手动命令锁住不回退 | contract tests + real run checklist |

## 2. P0：契约定名与边界

目标：

```text
把当前工作明确归入“模板生成运行包契约”
英文/slug：template-generation-run-bundle-contract
```

不属于本阶段的内容：

| 不属于 | 去哪里 |
| --- | --- |
| AI 怎么加入模板生成管线 | `T2T3T4 agent-proposal` / AI 集成 |
| 阶段产物和标准怎么比较 | `standard-judge` |
| mismatch 谁负责 | `stage-diff-root-cause` |
| 具体 T2/T3 识别错误 | T2/T3 对应阶段 issue |

执行计划：

1. 文档 frontmatter 使用：

```yaml
stage: run-bundle
topic: template-generation-run-bundle-contract
```

2. issue id 使用：

```text
RUN-BUNDLE-ISSUE-xx
RUN-BUNDLE-PLAN-xx
```

3. issue index 增加独立分组：

```text
Run bundle contract
```

验收：

```bash
rg -n "stage: output-layout|template-generation-output-bundle|OUTPUT-LAYOUT" \
  docs/plans \
  --glob '!template-parse-refactor-run-bundle-template-generation-contract-plan-01-phased-execution.md'
```

应没有旧分类残留。

## 3. P1：Run root 推导

目标：

给定任意 `template-generate --out`，代码能推导“这次 run 的 bundle root”。

规则：

| 输入 `--out` | bundle root | debug/human root |
| --- | --- | --- |
| `.../<run_id>/eval_runs/template_generate` | `.../<run_id>` | `.../<run_id>/human` |
| `.../<run_id>/eval_runs/template_gap` | `.../<run_id>` | `.../<run_id>/human` |
| `.../<run_id>/human/<timestamp>` | `.../<run_id>` | `.../<run_id>/human` |
| 不含 `eval_runs` / `human` 的普通路径 | `--out` 自身 | `--out/human` |

执行计划：

1. 在 `src/docfit/convert/orchestrator.py` 保留小而纯的路径函数：

```python
_bundle_root_from_output_dir(out_dir: Path) -> Path
_template_generation_project_dir(root: Path, template_docx: Path | None, out_dir: Path | None) -> Path
```

2. 不再从 `template_docx.stem` 推导 `runs/template_generation/<stem>` 作为默认写入位置。
3. `out_dir` 存在时，以 `out_dir` 为唯一可信来源。

验收：

```bash
uv run pytest tests/contract/test_template_generate.py::test_template_generate_writes_full_stage_artifact_chain -q
```

额外断言：

```text
summary.artifacts.template_generation_debug_dir 位于 <run_id>/human/<timestamp>
不会创建 runs/template_generation/**
```

## 4. P2：产物落盘布局

目标：

同一次模板生成的两类产物按职责分开放，但同根打包。

`eval_runs/template_generate/` 放机器可读产物：

```text
00_input_source_template.docx
00_template_generation_request.json
01_document_facts.json
02_unit_map.yaml
02.1_t2_input.json
03_element_spec.yaml
04_global_spec.yaml
05_template_spec.yaml
06.0_copy_source_docx.docx
06.1_fillable_template.docx
06.2_build_manifest.json
07_verification_report.json
99_template_generation_debug_index.json
artifacts/
summary.json
findings.json
issue_clusters.json
pm_report.md
```

`human/<timestamp>/` 放人读/debug 快照：

```text
00_input_source_template.docx
00_template_generation_request.json
01_document_facts.json
02_unit_map.yaml
...
07_verification_report.json
08_agent_render_packet.json optional
09_agent_transcript.json optional
10_agent_decisions.json optional
11_agent_t2_overlay.json optional
12_agent_t3_overlay.json optional
13_agent_t4_hints.json optional
14_agent_attribution.json optional
99_template_generation_debug_index.json
```

执行计划：

1. 保持 `write_template_generation_outputs(out_dir, result)` 写 `eval_runs/template_generate/`。
2. 保持 `write_template_generation_debug_snapshot(debug_dir, ...)` 写 `human/<timestamp>/`。
3. `build_manifest.debug_snapshot.dir` 指向 `human/<timestamp>`。
4. `summary.artifacts.template_generation_debug_dir` 指向同一路径。

验收：

```bash
uv run pytest tests/contract/test_template_generate.py -q
```

## 5. P3：后续 eval 共址

目标：

同一个模板生成 run 触发的后续检查进入同一个 run root。

推荐命令：

```bash
RUN_ROOT=test_outputs/debug/template_generation/manual_hunannongye

uv run docfit eval template-generate \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --out "$RUN_ROOT/eval_runs/template_generate"

uv run docfit eval template-gap \
  --school hunannongye \
  --generated-template "$RUN_ROOT/eval_runs/template_generate/fillable_template.docx" \
  --out "$RUN_ROOT/eval_runs/template_gap"

uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run "$RUN_ROOT/eval_runs/template_generate" \
  --out "$RUN_ROOT/eval_runs/template_generation_judge"
```

执行计划：

1. README 和 `docs/current/template-generation.md` 使用 `RUN_ROOT` 示例。
2. standard judge issue/plan 的 `--run`、`--out` 示例使用同一个 `RUN_ROOT`。
3. 不再推荐 `runs/eval/template_generation_judge/<target>/<run>/` 作为某次模板生成 run 的伴随输出。

验收：

```bash
rg -n "runs/eval/template_generation_judge|runs/template_generation/hunannongye|--out runs/template_generation|--run runs/template_generation" README.md docs/current docs/plans
```

命中的内容只能是历史说明或反例，不能是当前推荐命令。

## 6. P4：报告命名对齐

目标：

阶段报告文件名和模板生成阶段产物一一对齐。人看到报告名就知道对应哪个阶段产物。

命名规则：

```text
<阶段产物编号和名称>_standard_quality_report.{json,md}
```

映射：

| 阶段产物 | 阶段报告 |
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

执行计划：

1. standard judge 报告 writer 输出上述 per-stage report。
2. `template_generation_judge_report.{json,md}` 只做聚合。
3. `template_generation_stage_checks.json` 保留机器列表，但不替代 per-stage report。

验收：

```bash
uv run pytest tests/contract/test_template_generation_standard_judge.py -q
```

后续实现阶段需要把合同测试从旧的单个 `template_generation_stage_standard_quality_report` 改成编号化文件清单。

## 7. P5：Run bundle 证据绑定

目标：

standard judge 能证明自己读取的是同一次 `template-generate` run 的产物。

执行计划：

1. `template_generation_run_bundle.json` 记录：

```text
source_run_id
source_run_dir
source_run_dir_name
manifest_source
artifacts.<key>.path
artifacts.<key>.sha256
artifacts.<key>.declared_sha256 optional
artifacts.<key>.hash_match
```

2. 优先读取 `eval_runs/template_generate/99_template_generation_debug_index.json`。
3. 缺 index 时 fallback 到 filesystem scan，但状态不能假装强绑定。
4. 对比 `build_manifest`、`fillable_template.docx`、阶段产物 hash。

验收：

```bash
uv run pytest tests/unit/test_template_generation_run_bundle.py \
  tests/contract/test_template_generation_standard_judge.py -q
```

## 8. P6：文档与目录策略同步

目标：

所有当前入口都讲同一套目录规则。

要同步的文档：

```text
README.md
docs/current/template-generation.md
docs/current/project-directory-structure.md
docs/plans/template-parse-refactor-run-bundle-template-generation-contract-*.md
docs/plans/template-parse-refactor-standard-judge-*.md
```

执行计划：

1. 常用命令统一使用 `RUN_ROOT=test_outputs/debug/template_generation/<run_id>`。
2. 目录结构文档写清：

```text
eval_runs/ = 机器可读 eval / run 输出
human/ = 人读/debug 伴随材料
runs/eval/ = 非某次模板生成 run bundle 的长期评测报告
```

3. issue index 保留 `Run bundle contract` 分组。

验收：

```bash
rg -n "test_outputs/debug/template_generation/<run_id>|RUN_ROOT|Run bundle contract" README.md docs/current docs/plans
```

## 9. P7：验收门禁

目标：

把路径契约变成不容易倒退的自动测试和人工命令。

自动测试：

```bash
uv run pytest tests/contract/test_template_generate.py \
  tests/contract/test_template_generation_standard_judge.py -q
```

人工三校验证：

```bash
for school in hunannongye nannong-undergraduate pku-graduate; do
  RUN_ROOT="test_outputs/debug/template_generation/manual_${school}"

  uv run docfit eval template-generate \
    --template "inputs/targets/$school/raw/source_template.docx" \
    --out "$RUN_ROOT/eval_runs/template_generate"

  uv run docfit eval template-gap \
    --school "$school" \
    --generated-template "$RUN_ROOT/eval_runs/template_generate/fillable_template.docx" \
    --out "$RUN_ROOT/eval_runs/template_gap"
done
```

验收点：

```text
1. 每个 RUN_ROOT 下只有 eval_runs/ 和 human/ 承载本次材料。
2. human/<timestamp>/ 有 99_template_generation_debug_index.json。
3. eval_runs/template_generate/summary.json 里的 template_generation_debug_dir 指向同一 RUN_ROOT/human/<timestamp>。
4. 不因为这轮命令额外生成 runs/template_generation/**。
5. 后续 template-gap/template-generation-judge 能直接消费同一 RUN_ROOT/eval_runs/template_generate。
```

## 10. 推荐执行顺序

下一步建议按这个顺序执行：

```text
1. P1/P2：先锁住 template-generate 自身输出布局。
2. P3/P6：同步 gap/judge 和 current docs 的推荐命令。
3. P4：实现 standard judge 编号化阶段报告。
4. P5：增强 run bundle hash 绑定。
5. P7：三校真实运行验收。
```

原因很简单：先把“东西放哪儿”稳定住，再让 standard judge 和 AI attribution 接这个稳定包。不然报告再聪明，也可能是在翻错抽屉。
