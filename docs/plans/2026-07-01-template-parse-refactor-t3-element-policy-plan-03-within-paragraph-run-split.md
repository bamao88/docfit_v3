---
status: implemented
owner: template-generation
stage: T3
topic: element-policy
plan_id: T3-ELEMENT-PLAN-03
created: 2026-07-01
last_updated: 2026-07-01
source_issue:
  id: T3-ELEMENT-ISSUE-03
  doc: docs/plans/2026-06-30-template-parse-refactor-t3-element-policy-issue-03-within-paragraph-run-split.md
previous_plan:
  id: none
  doc: none
related_code:
  - src/docfit/template_generation/source_tree.py
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/generation_model.py
  - src/docfit/template_generation/plan.py
  - src/docfit/template_generation/executor.py
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/agent/packet.py
  - src/docfit/template_generation/agent/evidence.py
  - src/docfit/harness/template_generation_stage_verifiers.py
  - standards/targets/hunannongye/v1/template_generation/t3_element_policy.standard.yaml
  - tests/contract/test_template_generate.py
  - tests/unit/test_t1_structural_facts.py
  - tests/unit/test_template_generation_stage_verifiers.py
---

# T3 元素策略 Plan 03：段内 run 级元素化与精确删除

## 目标

修复同一 `<w:p>` 内“学生占位/标签文字 + 括号格式说明”被 T3 合成一个段落级 element 的问题。修完后，T3 能在不改变 `source_seq` 块级地址的前提下，把可分离的 run 片段拆成多个 element，并让 `remove_instruction` 删除动作精确落到对应 run，而不是删除整段。

## 实施原则

```text
1. T1 仍只输出事实；不新增 is_instruction、policy、confidence 等语义字段。
2. source_seq 仍对齐 Word 段落/块级可见对象，不改编号规则。
3. T3 可以基于 T1 的 raw_run_ids / logical_run_ids / runs_by_raw_run_id 计算段内元素。
4. 只有存在明确 run 边界或可安全定位的格式说明片段时才拆分，不把普通正文长段落按 run 过度切碎。
5. element_spec、generation_model、plan action、build_manifest 必须保留 run 级追踪，避免只在中间产物“看起来拆了”。
```

## 实施顺序

### 1. 先补失败用例

在 `tests/contract/test_template_generate.py` 新增段内 run 拆分契约用例，构造或复用 hunannongye cover 样式：

```text
段落文本：毕业论文（设计）中文题目  （小二黑体加粗）
run 事实：标题/占位 run 与格式说明 run 分离
期望：
- T3 产出至少两个 element，二者 source_seq_refs 都是同一个 source_seq。
- 占位/标签 element 为 fill 或 fixed，带自己的 raw_run_ids / logical_run_ids。
- 格式说明 element 为 remove_instruction，带格式说明 run 的 raw_run_ids / logical_run_ids。
- element_spec 保留这些 run refs。
- template_generation_plan 对 remove_instruction_text action 写入 affected_raw_run_ids / affected_logical_run_ids。
- fillable_template.docx 保留标题/占位文字，但不保留括号格式说明。
```

同时补一个反例用例：普通正文段落即便有多个同样式或自然分裂 run，也不能被拆成大量 element。

### 2. 打通 run 事实读取

在 T3 可访问的位置暴露 run 索引：

```text
1. 从 source_tree.indexes.runs_by_raw_run_id 读取 raw run -> logical run/text/style/source_ref。
2. 必要时在 _source_context_from_source_tree() 中加入 runs / runs_by_raw_run_id / runs_by_source_ref 的只读事实视图。
3. 不在 body_flow 上新增判断类字段，只使用已有 raw_run_ids / logical_run_ids。
```

完成信号：`_infer_elements()` 或其下游 helper 可以从一条 body_flow entry 还原有序 run slices。

### 3. 实现 T3 段内元素切分

在 `structure_candidates.py` 中新增受控 splitter，建议放在 `_infer_elements()` 与 `_element_from_entries()` 之间：

```text
1. `_logical_entry_groups()` 继续负责跨段落/表格行的块级合并，不承担段内 run 拆分。
2. 新增 helper，例如 `_element_entry_slices(anchor, group, run_index)`：
   - 对单条 paragraph entry，按 raw/logical run 还原 slices。
   - 将连续业务 run 合并为一个 content slice。
   - 将纯格式说明 slice（如 `（小二黑体加粗）`、`（三号黑体）`）单独切成 instruction slice。
   - 对表格、页眉页脚、缺 run refs 或无法安全定位的片段，回退当前段级逻辑。
3. slice 继续复用 `source_ref` / `source_seq`，但写入自己的 `raw_run_ids` / `logical_run_ids`。
4. `_element_from_entries()` 支持 synthetic slice entry，落盘：
   - raw_run_ids
   - logical_run_ids
   - merge.type = within_paragraph_run_split
   - structure.kind = run_slice
```

格式说明判断应优先复用 `_has_format_annotation()` / `_looks_like_instruction()`，但必须避免整段“有实质文本 + 括号说明”时返回 False 后吞掉说明 run。

### 4. 传播 run refs 到模型、计划和报告

现有 `build_element_spec()` 已读取 element 上的 `raw_run_ids` / `logical_run_ids`，本轮需要补齐前后链路：

```text
1. `_element_from_entries()` 对所有 element 写入 raw_run_ids / logical_run_ids，不能只给新 splitter 写。
2. `generation_model._build_unit_strategies()` 在 decision 中保留 raw_run_ids / logical_run_ids。
3. `plan.build_template_generation_plan()` 将 decision refs 写入 action：
   - affected_raw_run_ids
   - affected_logical_run_ids
4. build_manifest / executed action 输出同样保留 run refs，便于最终追踪。
```

完成信号：从 `03_element_spec.yaml` 到 `template_generation_plan.json` 再到 `build_manifest.json`，同一个 instruction element 的 run refs 不丢。

### 5. 精确执行 remove_instruction_text

当前 executor 对 `remove_instruction_text` 是按 `source_ref` 删除整段或清空 cell。需要增加 run 级路径：

```text
1. action 带 affected_raw_run_ids 时，优先按 raw run id 定位并清空/删除对应 Word run。
2. action 不带 run refs 时，保留现有段落级/单元格级 fallback。
3. 若 run refs 与 source_ref 无法对应，写入 review，不静默降级为整段删除。
4. 对一个段落内多个 remove_instruction action，要保证删除顺序不影响剩余 run 定位。
```

实现位置优先放在 `executor.py` / `word_ops.py`，避免把 OOXML 细节扩散到 T3 策略层。

### 6. 更新 Module 1/T3 证据视图

T3 observation 已允许证据包含 `raw_run_ids`，但 page text 视图当前仍偏段落级。同步补齐：

```text
1. `agent/packet.py` 的 T3 page_text_index 条目带 raw_run_ids / logical_run_ids。
2. query_text 或 observation evidence 中能看到同一 source_seq 下的 run refs。
3. 暂不要求 run 级 bbox；annotated 红框仍可保持 source_seq 段级。
```

这样 AI observation 可以表达“同一 source_seq 中只有某些 run 是 instruction”，但不会破坏 T2/T4 仍按 source_seq 工作的窗口模型。

### 7. 标准和诊断补齐

完成代码后补 T3 标准/裁判覆盖：

```text
1. hunannongye 的 T3 standard expected 增加 run 级 element 断言或等价诊断规则。
2. template-generation-judge 对 “expected run-level remove_instruction, observed paragraph-level fixed” 输出 mismatch。
3. root_causes 指向 T3 deterministic element split，不归因 T1 source_seq 或 T6 删除失败。
```

## 验收命令

```bash
uv run pytest tests/contract/test_template_generate.py -q
uv run pytest tests/unit/test_t1_structural_facts.py -q
uv run docfit eval template-generate \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --out test_outputs/debug/template_generation/20260701_t3_run_split/hunannongye
uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run test_outputs/debug/template_generation/20260701_t3_run_split/hunannongye/eval_runs/template_generate \
  --out test_outputs/debug/template_generation/20260701_t3_run_split/hunannongye/eval_runs/template_generation_judge
```

如果实际 run bundle 路径与命令中的 `eval_runs/template_generate` 不一致，以本次 `template-generate` 真实输出目录为准，不能为了让 judge 通过而重跑或替换旧产物。

## 完成信号

```text
1. hunannongye cover source_seq=6 被拆为至少两个 T3 element。
2. 格式说明 element policy=remove_instruction，且 raw_run_ids / logical_run_ids 可回查 document_facts.runs[]。
3. 最终 fillable_template.docx 保留 “毕业论文（设计）中文题目”，删除 “（小二黑体加粗）”。
4. 普通正文长段落没有出现 run 级过度切碎。
5. build_manifest 中 remove_instruction_text action 记录 affected_raw_run_ids / affected_logical_run_ids。
6. template-generation-judge 能把该类问题作为 T3 标准差异诊断，而不是只给 PASS/SIGNABLE。
```

## 执行结果

```text
1. 已新增段内 run 拆分契约测试：
   tests/contract/test_template_generate.py::test_template_generate_splits_within_paragraph_format_instruction_runs
2. 已实现 T3 run-level splitter：
   - source_seq 仍保持段落级；
   - 同一 source_seq 内可拆出 run_slice element；
   - 普通正文多 run 不被过度拆分。
3. 已贯通 raw/logical run refs：
   - element_spec
   - template_generation_model decisions
   - template_generation_plan actions
   - build_manifest actions_executed
   - T3 agent packet/evidence
4. 已实现 run-level remove_instruction_text：
   - 单 source_seq paragraph action 按 affected_raw_run_ids 清空对应 Word run；
   - 多段说明和表格 cell 保持原块级删除/清空路径；
   - 单段 run 定位失败时进入 review，不静默整段删除。
5. 已扩展 T3 standard verifier：
   - 新增 expected.run_level_elements；
   - hunannongye source_seq=6 断言 fixed 标题 run 与 instruction_remove 格式说明 run；
   - 缺失时输出 t3_run_level_element_mismatch。
6. hunannongye 真实生成：
   test_outputs/debug/template_generation/20260701_t3_run_split/hunannongye
   - cover source_seq=6 -> e_011 fixed + e_012 instruction_remove；
   - e_012 raw_run_ids=['p_0007.r_004']；
   - fillable_template.docx 保留“毕业论文（设计）中文题目”，不再包含“小二黑体加粗”。
7. template-generation-judge：
   test_outputs/debug/template_generation/20260701_t3_run_split/hunannongye/eval_runs/template_generation_judge_after_run_level_standard
   - status=PASS；
   - T3 run_level_element_gaps=[]；
   - standard_acceptance_status=PASS。
```

## 验证记录

```bash
uv run pytest tests/contract/test_template_generate.py tests/unit/test_t1_structural_facts.py tests/unit/test_template_generation_stage_verifiers.py -q
# 46 passed

uv run pytest tests/unit/template_generation_agent tests/unit/test_template_generation_standard_diff_diagnosis.py tests/contract/test_template_generation_standard_judge.py -q
# 111 passed

uv run docfit eval template-generate --template inputs/targets/hunannongye/raw/source_template.docx --out test_outputs/debug/template_generation/20260701_t3_run_split/hunannongye
# status = UNKNOWN

uv run docfit eval template-generation-judge --school hunannongye --run test_outputs/debug/template_generation/20260701_t3_run_split/hunannongye --out test_outputs/debug/template_generation/20260701_t3_run_split/hunannongye/eval_runs/template_generation_judge_after_run_level_standard
# status = PASS

uv run python -m py_compile src/docfit/template_generation/structure_candidates.py src/docfit/template_generation/generation_model.py src/docfit/template_generation/plan.py src/docfit/template_generation/executor.py src/docfit/template_generation/word_ops.py src/docfit/template_generation/agent/packet.py src/docfit/template_generation/agent/evidence.py src/docfit/harness/template_generation_stage_verifiers.py
# passed
```

## 风险与回退

```text
1. 风险：run 级删除误删整段。
   控制：executor 有 run refs 时禁止静默退回整段删除；失败进入 review。
2. 风险：正文被过度元素化。
   控制：只针对纯格式说明 run 或明确 instruction run 切分，正文默认沿用段级合并。
3. 风险：标准/AI observation 仍只能按 source_seq 表达。
   控制：source_seq 继续作为窗口主键，run refs 作为同一 source_seq 内的细粒度证据。
4. 回退：若精确执行不稳定，可先保留 T3 run-level element 和 review flag，但不得把 run-level remove_instruction 执行为整段删除。
```
