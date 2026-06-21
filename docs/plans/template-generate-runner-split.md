# template_generate/runner.py 拆分任务

Last updated: 2026-06-21

一句话结论：`src/docfit/stages/template_generate/runner.py` 应按模板生成五步证据链拆分成多个小模块；第一轮只做机械拆分并保持行为不变，第二轮再把阶段二、阶段三的语义边界收拢到新流程。

## 这个文件做什么

这个文件只记录 `template_generate/runner.py` 的代码拆分任务。流程语义以
`docs/plans/template-generation-flow-optimization.md` 为准。

拆分目标不是马上改变模板生成结果，而是让后续排查能按产物定位代码：

| 如果先坏在 | 应该看 |
| --- | --- |
| `source_template_tree.json` | 源 Word 事实解析模块 |
| `discovered_template_rules.json` | 候选结构识别模块 |
| `template_artifact.json` / `template_unit_decisions.json` | 生成模板模型与策略模块 |
| `template_generation_plan.json` | 动作计划模块 |
| `generated_template.docx` / `template_generation_manifest.json` | 执行和记录模块 |

## 当前真实情况

当前 `runner.py` 约 1900 行，把这些职责放在同一个文件里：

| 职责 | 当前状态 |
| --- | --- |
| 输入检查和主流程编排 | 已在 `generate_template()` 中实现 |
| 源 Word 事实解析 | 已实现，产物是 `source_template_tree.json` |
| 候选单元和元素识别 | 已实现第一版，产物是 `discovered_template_rules.json` |
| 模板模型和策略 | 已实现第一版，但分散在 `template_artifact` 和 `template_unit_decisions` |
| 动作计划 | 已实现第一版，产物是 `template_generation_plan.json` |
| Word action 执行 | 已实现，产物是 `generated_template.docx` 和执行结果 |
| manifest / debug / artifacts 写出 | 已实现 |

当前还存在一个语义偏差：候选结构识别阶段已经直接写 `policy = fill / fixed / generated / remove_instruction`，但目标流程里阶段二应该只给 `role_hint` 和证据，阶段三才统一决定 slot、protected zone、cleanup 和 `generation_mode`。

## 目标模块结构

建议先拆成下面这些文件：

| 目标文件 | 职责 |
| --- | --- |
| `runner.py` | 只保留 `generate_template()` 主流程、输入失败状态和必要兼容导出 |
| `constants.py` | 默认策略、slot marker、unit 定义、marker 列表 |
| `request.py` | 构建 `template_generation_request.json` |
| `source_tree.py` | 阶段一：解析源 Word 事实 |
| `structure_candidates.py` | 阶段二：识别候选 unit / element / source_ref / role hint / evidence |
| `generation_model.py` | 阶段三：生成模板业务地图和处理策略 |
| `plan.py` | 阶段四：把业务地图翻译成 action plan |
| `executor.py` | 阶段五：执行 action，返回执行结果 |
| `manifest.py` | 生成 `template_generation_manifest.json` |
| `outputs.py` | 写 public artifacts 和 00-10 debug 快照 |
| `refs.py` | `source_ref`、段落序号、part name 等定位工具 |
| `text_utils.py` | 文本规范化、格式注释清理、去重等纯文本工具 |
| `word_ops.py` | python-docx 底层插入、删除、清空 cell、分页和分节操作 |

## 当前函数归属

第一轮机械拆分时，函数可以先这样移动：

| 目标文件 | 当前函数 |
| --- | --- |
| `runner.py` | `generate_template()`、`_coverage()` |
| `request.py` | `build_template_generation_request()` |
| `outputs.py` | `_new_template_generation_debug_dir()`、`write_template_generation_debug_snapshot()`、`write_template_generation_outputs()` |
| `source_tree.py` | `inspect_source_template_docx()`、`_body_flow_from_inspection()`、`_source_tree_warnings()`、`_structural_signals()` |
| `structure_candidates.py` | `infer_template_rules()`、`_body_entries()`、`_infer_units()`、`_unit_anchors()`、`_infer_elements()`、`_copy_only_unit_elements()`、`_rule_unknowns()` |
| `generation_model.py` | `build_template_artifact()`、`build_template_unit_decisions()`、`_unit_generation_mode()`、`_instruction_paragraphs_from_units()`、`_instruction_paragraphs_from_source_tree()`、`_style_inventory()` |
| `plan.py` | `build_template_generation_plan()`、`_synthetic_unit_title_actions()`、`_generated_unit_title_text()`、`_previous_unit_source_ref()`、`_next_unit_source_ref()`、`_decision_reason()`、`_action_type_for_decision()`、`_target_ref_for_decision()`、`_page_break_rule_requires_break()` |
| `executor.py` | `execute_template_generation_plan()`、`_slot_marker()`、`_generated_marker()`、`_slot_from_action()`、`_executed()`、`_needs_review()` |
| `manifest.py` | `build_template_generation_manifest()` |
| `refs.py` | `_first_source_ref()`、`_paragraph_index()`、`_paragraph_for_ref()`、`_cell_for_ref()`、`_part_name()` |
| `text_utils.py` | `_normalize_text()`、`_normalize_for_match()`、`_strip_format_annotations()`、`_dedupe()`、`_dedupe_by_key()` |
| `word_ops.py` | `_clear_cell()`、`_insert_marker()`、`_insert_page_break_before()`、`_insert_section_break_before()`、`_insert_styled_paragraph_before()`、`_next_page_section_properties()`、`_insert_paragraph_before()`、`_insert_paragraph_after()`、`_append_marker()`、`_find_marker_ref()`、`_remove_paragraph()` |

`_unit_for_text()`、`_unit_policy()`、`_element_policy()`、`_looks_like_instruction()`、`_looks_like_heading()`、`_element_name()`、`_element_type()`、`_style_summary()` 等函数第一轮可以留在 `structure_candidates.py`，保持行为不变。第二轮语义收敛时，再把“最终处理策略”迁到 `generation_model.py`。

## 实施顺序

### 第一轮：机械拆分，不改行为

目标：代码位置变清楚，产物和测试结果不变。

1. 新建目标模块文件。
2. 按“当前函数归属”移动函数。
3. `runner.py` 只保留主流程，并从新模块导入函数。
4. 如有外部测试或模块仍从 `runner.py` import 常量或函数，先在 `runner.py` 保留兼容导出。
5. 不新增字段，不改 JSON 形状，不改 copy-only 行为。

验收：

```bash
uv run pytest tests/contract/test_template_generate.py -q
```

如果涉及 e2e 或真实模板样例，再补：

```bash
uv run docfit eval template-generate \
  --template test_inputs/template_generation/school-hunannongye-requirement.docx \
  --out test_outputs/debug/template_generation/school-hunannongye-requirement/eval_runs/template_generate_split_check
```

### 第二轮：语义收敛

目标：让代码真正符合五步流程。

1. `structure_candidates.py` 输出候选结构、`role_hint` 和 evidence，不再把候选信号当最终处理策略。
2. `generation_model.py` 统一决定 `generation_mode`、slots、protected zones、cleanup 清单和 unresolved questions。
3. `plan.py` 只消费阶段三模型，不重新判断 unit 语义。
4. 修复 copy-only 单元内部说明文字漏清理的问题：copy-only 仍不自动生成学生内容 slot，但允许内部说明文字进入 cleanup。
5. 继续兼容写出旧产物名，直到消费者完成迁移。

验收：

```bash
uv run pytest tests/contract/test_template_generate.py -q
```

还应新增或调整聚焦测试，证明：

| 用例 | 证明什么 |
| --- | --- |
| copy-only 单元仍是 `whole_unit_copy` | 生成策略没有退回误插 slot |
| copy-only 内部说明文字进入 cleanup | `whole_unit_copy` 不等于跳过说明文字处理 |
| copy-only 内部填写痕迹不生成 slot | 封面 `论文题目：____` 不自动变成学生内容入口 |
| 非 copy-only 单元仍生成 slot / generated marker | 摘要、正文、参考文献等继续可填写或可生成 |
| plan 只来自阶段三模型 | 动作计划不重新做业务判断 |

## 不在本拆分任务里做

| 不做什么 | 原因 |
| --- | --- |
| 不更改学校标准输入参数 | `template-generate` 当前仍只接收 `--template` 和 `--out` |
| 不自动新增或更新 golden / expected | 这会改变验收基线 |
| 不把 `template-gap` 判定合并进生成器 | 生成器只产出模板和证据，学校合格性仍由 `template-gap` 检查 |
| 不把 `template_generation_manifest` 当作最终 Word 合格证明 | manifest 只证明执行记录和 hash，不证明学校格式通过 |

## 完成标准

第一轮完成标准：

| 标准 | 结果 |
| --- | --- |
| `runner.py` 只保留主流程和兼容导出 | 待做 |
| 每个模块职责能对应五步流程 | 待做 |
| `tests/contract/test_template_generate.py` 通过 | 待做 |
| 公开产物名和 JSON 形状不变 | 待做 |

第二轮完成标准：

| 标准 | 结果 |
| --- | --- |
| 阶段二只输出候选结构和证据 | 待做 |
| 阶段三统一输出模板业务地图和处理策略 | 待做 |
| 阶段四只翻译 action，不重新判断业务语义 | 待做 |
| copy-only 内部说明文字清理有测试证明 | 待做 |
