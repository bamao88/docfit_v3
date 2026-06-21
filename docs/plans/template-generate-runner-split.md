# template_generate/runner.py 拆分任务

Status: Implemented
Last updated: 2026-06-21

一句话结论：`src/docfit/stages/template_generate/runner.py` 已按模板生成五步证据链拆分成多个小模块；copy-only 单元现在会做受限内部识别，说明文字可以进入 cleanup，填写痕迹不会自动生成学生内容 slot。

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

当前 `runner.py` 只保留 `generate_template()` 主流程、输入失败状态、覆盖率和兼容导入。模板生成职责已经拆到 `src/docfit/stages/template_generate/` 下的专项模块：

| 职责 | 当前状态 |
| --- | --- |
| 输入检查和主流程编排 | `runner.py` |
| 源 Word 事实解析 | `source_tree.py`，产物是 `source_template_tree.json` |
| 候选单元和元素识别 | `structure_candidates.py`，产物是 `discovered_template_rules.json` |
| 模板模型和策略 | `generation_model.py`，产物是 `template_artifact.json` 和 `template_unit_decisions.json` |
| 动作计划 | `plan.py`，产物是 `template_generation_plan.json` |
| Word action 执行 | `executor.py`，产物是 `generated_template.docx` 和执行结果 |
| manifest / debug / artifacts 写出 | `manifest.py` 和 `outputs.py` |

语义边界也已收敛一层：`discovered_template_rules` 里的元素带 `role_hint` 和 `evidence`，`generation_model.py` 会把候选 `policy` materialize 成 `template_artifact` 的最终 `policy`。copy-only 内部的 `fill` / `generated` 候选会保留为证据但最终变成 `fixed`，不会生成 slot；`remove_instruction` 候选会进入 cleanup。

## 过程文件输出兼容要求

拆分后必须继续输出当前 Runner 已经输出的过程文件。代码可以拆成多个 Python 文件，但对调用方和排查者来说，过程证据的位置、文件名和阶段编号必须保持兼容。

当前有两类输出都要保留：

| 输出位置 | 用途 | 拆分后要求 |
| --- | --- | --- |
| `--out/artifacts/*.json` | 公开机器可读阶段产物，供 summary、报告、后续 e2e 和人工排查引用 | 文件名和 JSON 形状第一轮不变 |
| `test_outputs/debug/template_generation/<验证名或运行目录>/<timestamp>/00-10_*` | 按阶段编号保存的调试快照，方便从输入到 manifest 逐步定位 first_bad_stage | 目录层级、编号前缀和文件名第一轮不变 |

以当前真实输出目录
`test_outputs/debug/template_generation/20260621T160704467333+0800/` 为例，拆分后仍应生成同名文件：

| 编号 | 文件 | 含义 |
| --- | --- | --- |
| `00` | `00_input_source_template.docx` | 输入学校原始模板 Word |
| `01` | `01_template_generation_request.json` | 本次生成请求 |
| `02` | `02_source_template_tree.json` | 阶段一：源 Word 事实 |
| `03` | `03_discovered_template_rules.json` | 阶段二：候选结构识别，当前兼容产物名 |
| `04` | `04_template_artifact.json` | 阶段三的一部分：模板业务地图，当前兼容产物名 |
| `05` | `05_template_unit_decisions.json` | 阶段三的一部分：处理策略，当前兼容产物名 |
| `06` | `06_template_generation_plan.json` | 阶段四：动作计划 |
| `07` | `07_copy_source_docx.docx` | 只执行整包复制后的 Word 停点 |
| `08` | `08_generated_template.docx` | 执行全部 action 后的生成模板 Word |
| `09` | `09_template_generation_manifest.json` | 阶段五：执行记录和输出 hash |
| `10` | `10_template_generation_debug_index.json` | 本 debug 目录的文件索引 |

重要边界：

| 边界 | 说明 |
| --- | --- |
| 拆模块不等于改输出契约 | 第一轮机械拆分不能改文件位置、编号、名字或 JSON 形状 |
| 阶段三目标产物可以叫 `template_generation_model` | 但迁移期仍要写出 `template_artifact.json` 和 `template_unit_decisions.json` |
| `outputs.py` 负责保持输出兼容 | 其他模块只返回数据，不直接决定 debug 文件命名 |
| manifest 仍只证明执行记录 | 不能因为拆分后 manifest 更完整，就把它当成模板质量通过证明 |

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
6. 保留 `--out/artifacts/` 和 debug snapshot 的现有输出位置、编号前缀和文件名。

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
| `runner.py` 只保留主流程和兼容导出 | 已完成；提交 `0db2f4d` |
| 每个模块职责能对应五步流程 | 已完成；新增 `source_tree.py`、`structure_candidates.py`、`generation_model.py`、`plan.py`、`executor.py`、`manifest.py`、`outputs.py` 等 |
| `tests/contract/test_template_generate.py` 通过 | 已完成；`9 passed` |
| 公开产物名和 JSON 形状不变 | 已完成；第一轮机械拆分未改 artifacts 文件名 |
| 00-10 debug 快照位置和文件名不变 | 已完成；真实命令验证写出 `00_input_source_template.docx` 到 `10_template_generation_debug_index.json` |

第二轮完成标准：

| 标准 | 结果 |
| --- | --- |
| 阶段二只输出候选结构和证据 | 已完成到兼容层；`role_hint` 和 `evidence` 已进入 `discovered_template_rules`，旧 `policy` 字段保留为候选 policy 兼容字段 |
| 阶段三统一输出模板业务地图和处理策略 | 已完成；`generation_model.py` materialize 最终 `policy`，并保留 `candidate_policy` 解释候选来源 |
| 阶段四只翻译 action，不重新判断业务语义 | 已完成；`plan.py` 消费 `template_artifact` 和 `template_unit_decisions`，不重新决定 copy-only / fill / generated 语义 |
| copy-only 内部说明文字清理有测试证明 | 已完成；`tests/contract/test_template_generate.py` 证明 copy-only 内部说明文字删除、填写痕迹不生成 cover slot |

## 执行证据

| 类型 | 证据 |
| --- | --- |
| 提交 | `0db2f4d refactor(template-generate): split runner modules` |
| 提交 | `304d613 feat(template-generate): clean copy-only instructions` |
| 提交 | `526196f refactor(template-generate): materialize candidate policies in model` |
| 聚焦测试 | `uv run pytest tests/contract/test_template_generate.py -q` -> `9 passed` |
| 合同测试 | `uv run pytest tests/contract -q` -> `71 passed` |
| 真实模板生成 | `uv run docfit eval template-generate --template test_inputs/template_generation/school-hunannongye-requirement.docx --out test_outputs/debug/template_generation/school-hunannongye-requirement/eval_runs/template_generate_split_check` -> `status = PASS` |
| 输出兼容 | 真实运行写出 7 个 public JSON artifact，以及 `00_input_source_template.docx` 到 `10_template_generation_debug_index.json` 的 debug 快照 |
| 行为变化 | manifest 记录 43 个 copy-only 内部 cleanup action；copy-only 填写候选不生成 cover slot |
