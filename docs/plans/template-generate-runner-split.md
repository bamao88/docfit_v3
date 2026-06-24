# template_generate 模块拆分现状

Status: Implemented
Last updated: 2026-06-22

当前口径提示：本文是 runner 拆分完成时的历史记录；其中“学校标准和学生内容台账接入”这个剩余工作说法已经废弃。当前正常生成输入只有学校原始模板 Word；后续目标是强化源模板自动推断和不确定性表达。当前主线见 `docs/current/template-generation.md`，待核实差距见 `docs/current/template-generation-open-gaps.md`。

一句话结论：`src/docfit/template_generation/runner.py` 的机械拆分已经完成，阶段二/三目标产物、debug 编号和 `source_seq` 追踪字段也已经切到当前契约；当前剩余工作以 `docs/current/template-generation-open-gaps.md` 为准。

## 这个文件做什么

这个文件记录模板生成模块拆分后的当前状态和已经完成的证据。下一轮代码优化要改哪里，以 current 文档和待核实差距清单为准。

它不再作为“待拆模块清单”。模板生成五阶段目标方案以
`docs/plans/template-generation-flow-optimization.md` 为准；当前长期流程说明以
`docs/current/template-generation.md` 为准。

## 当前真实模块地图

当前 `runner.py` 只保留 `generate_template()` 主流程、输入失败状态、覆盖率和必要模块调用。模板生成职责已经拆到 `src/docfit/template_generation/` 下的专项模块：

| 职责 | 当前模块 | 当前产物 |
| --- | --- | --- |
| 输入检查和主流程编排 | `runner.py` | 汇总各阶段结果 |
| 常量和默认规则 | `constants.py` | 被阶段模块复用 |
| 请求记录 | `request.py` | `template_generation_request.json` |
| 阶段一：源 Word 事实解析 | `source_tree.py` | `source_template_tree.json` |
| 阶段二：候选单元和元素识别 | `structure_candidates.py` | `template_structure_candidates.json` |
| 阶段三：模板模型和策略 | `generation_model.py` | `template_generation_model.json` |
| 阶段四：动作计划 | `plan.py` | `template_generation_plan.json` |
| 阶段五：Word action 执行 | `executor.py` | `generated_template.docx` 和执行结果 |
| manifest 生成 | `manifest.py` | `template_generation_manifest.json` |
| public artifacts 和 debug 快照写出 | `outputs.py` | `--out/artifacts/` 和 debug 目录文件 |
| source reference 定位工具 | `refs.py` | 被阶段模块复用 |
| 文本规范化工具 | `text_utils.py` | 被阶段模块复用 |
| python-docx 底层操作 | `word_ops.py` | 被执行阶段复用 |

当前语义边界已经比最初 runner 单文件更清楚：`template_structure_candidates` 里的元素带 `role_hint`、`evidence` 和 `source_seq_refs`；`generation_model.py` 会把候选 `candidate_policy` materialize 成阶段三最终 `policy`，并写入 `unit_strategies`、`slots`、`protected_zones` 和 `cleanup`。copy-only 单元内部的 `fill` / `generated` 候选会保留为证据但最终变成 `fixed`，不会生成 slot；`remove_instruction` 候选会进入 cleanup。

## 当前真实输出

当前代码写出阶段对齐后的公开产物名和 debug 编号。排查现有运行结果时，应按这张表定位：

| 编号 | 当前文件 | 说明 |
| --- | --- | --- |
| `00` | `00_input_source_template.docx` | 输入学校原始模板 Word |
| `00` | `00_template_generation_request.json` | 本次生成请求 |
| `01` | `01_source_template_tree.json` | 阶段一：源 Word 事实 |
| `02` | `02_template_structure_candidates.json` | 阶段二：候选结构识别 |
| `03` | `03_template_generation_model.json` | 阶段三：模板业务模型和处理策略 |
| `04` | `04_template_generation_plan.json` | 阶段四：动作计划 |
| `05.0` | `05.0_copy_source_docx.docx` | 阶段五：只执行整包复制后的 Word 停点 |
| `05.1` | `05.1_generated_template.docx` | 阶段五：执行全部 action 后的生成模板 Word |
| `05.2` | `05.2_template_generation_manifest.json` | 阶段五：执行记录和输出 hash |
| `99` | `99_template_generation_debug_index.json` | 本 debug 目录的文件索引 |

这些是当前真实实现。`template_parse` 业务四阶段里的 `template_artifact.json` 仍是另一个业务产物，不属于 `template_generate` 支撑流程这次改名范围。

## 编号规则

整数部分对应阶段，点后面对应该阶段内的子产物；`00` 留给输入、请求和运行上下文，`99` 留给索引、汇总和非阶段性说明。小数点不是数学小数，而是 `阶段.子步骤` 标号。后续如果某阶段内子产物超过 9 个，可以改用 `02.01`、`02.02` 这种两位子步骤，避免文件排序混乱。

## 已完成

| 已完成事项 | 证据 |
| --- | --- |
| `runner.py` 拆成阶段模块 | 提交 `0db2f4d refactor(template-generate): split runner modules` |
| copy-only 内部说明文字可以清理 | 提交 `304d613 feat(template-generate): clean copy-only instructions` |
| 阶段三 materialize 最终策略 | 提交 `526196f refactor(template-generate): materialize candidate policies in model` |
| 阶段一新增 `source_seq` | 当前实现；`source_template_tree.layers.body_flow[]` 和 `indexes.by_source_seq` 已写出 |
| 阶段二目标产物改名 | 当前实现；`template_structure_candidates.json` 已替代 `discovered_template_rules.json` |
| 阶段三目标产物合并 | 当前实现；`template_generation_model.json` 已承载 units、unit_strategies、slots、protected_zones、cleanup |
| debug 编号按阶段重命名 | 当前实现；debug 快照使用 `00 / 01 / 02 / 03 / 04 / 05.x / 99` |
| 聚焦合同测试通过 | `uv run pytest tests/contract/test_template_generate.py -q` -> `9 passed` |
| 合同测试通过 | `uv run pytest tests/contract -q` -> `71 passed` |
| 真实模板生成通过 | `uv run docfit eval template-generate --template inputs/targets/hunannongye/raw/source_template.docx --out runs/template_generation/school-hunannongye-requirement/eval_runs/template_generate_split_check` -> `status = PASS` |
| action 来源序号可追踪 | `template_generation_plan.actions[].affected_source_seq_refs[]` 和 manifest 执行记录已保留来源序号 |

## 仍需补齐

| 剩余工作 | 应该改哪里 | 验收重点 |
| --- | --- | --- |
| 更深的 logical element 合并 | `structure_candidates.py` | 在当前连续说明文字合并之外，继续补表格行 label+blank、句子 continuation 等规则 |
| 源模板责任推断和不确定性表达 | `generation_model.py`、`structure_candidates.py` | copy-only / copy_then_patch 不再只靠全局 unit_id 基线，也不依赖学校标准或学生内容台账作为生成输入 |
| 报告和长期文档引用同步更新 | current docs、plan docs、人工排查说明 | 人工排查入口全部使用新产物名 |
| 阶段检查结果落地 | 评测层和报告层 | 能表达 `first_bad_phase`、上游阻断和下游症状 |

## 不做

| 不做什么 | 原因 |
| --- | --- |
| 不继续重拆已经完成的模块 | 当前问题是产物契约和消费者同步，不是文件还没拆开 |
| 不为旧产物名保留兼容输出 | 这个原型优先保持当前契约干净，下一轮应同步切换生产者和消费者 |
| 不自动新增或更新 golden / expected | 这会改变验收基线，必须有明确签收 |
| 不把 `template-gap` 判定合并进生成器 | 生成器产出模板和证据，学校合格性仍由检查器判断 |
| 不把 `template_generation_manifest` 当作最终 Word 合格证明 | manifest 只证明执行记录和 hash，不证明学校格式通过 |

## 下一轮验证建议

下一轮改代码后至少运行：

```bash
uv run pytest tests/contract/test_template_generate.py -q
```

涉及消费者、报告或 e2e 引用时，再补：

```bash
uv run pytest tests/contract -q
uv run docfit eval template-generate \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --out runs/template_generation/school-hunannongye-requirement/eval_runs/template_generate_target_contract
```

如果新增 `source_seq`，还需要补聚焦测试证明：

| 用例 | 证明什么 |
| --- | --- |
| 单个元素保留 | 输出对象能引用原始 `source_seq` |
| 多个元素合并 | 合并后对象能列出全部来源序号，例如 `3,4,5` |
| 元素删除 | cleanup / report 能说明删除了哪个 `source_seq` |
| AI 自检或人工沟通 | finding / evidence 能用 `source_seq` 定位问题来源 |
