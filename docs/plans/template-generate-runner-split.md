# template_generate 模块拆分现状

Status: Implemented
Last updated: 2026-06-22

一句话结论：`src/docfit/stages/template_generate/runner.py` 的机械拆分已经完成；当前剩余工作不是继续拆文件，而是把阶段二/三产物名、debug 编号、`source_seq` 追踪字段和消费者连接一次性切到目标契约。

## 这个文件做什么

这个文件记录模板生成模块拆分后的当前状态、已经完成的证据、仍然使用旧产物名的地方，以及下一轮代码优化要改哪里。

它不再作为“待拆模块清单”。模板生成五阶段目标方案以
`docs/plans/template-generation-flow-optimization.md` 为准；当前长期流程说明以
`docs/current/template-generation.md` 为准。

## 当前真实模块地图

当前 `runner.py` 只保留 `generate_template()` 主流程、输入失败状态、覆盖率和必要模块调用。模板生成职责已经拆到 `src/docfit/stages/template_generate/` 下的专项模块：

| 职责 | 当前模块 | 当前产物 |
| --- | --- | --- |
| 输入检查和主流程编排 | `runner.py` | 汇总各阶段结果 |
| 常量和默认规则 | `constants.py` | 被阶段模块复用 |
| 请求记录 | `request.py` | `template_generation_request.json` |
| 阶段一：源 Word 事实解析 | `source_tree.py` | `source_template_tree.json` |
| 阶段二：候选单元和元素识别 | `structure_candidates.py` | `discovered_template_rules.json` |
| 阶段三：模板模型和策略 | `generation_model.py` | `template_artifact.json`、`template_unit_decisions.json` |
| 阶段四：动作计划 | `plan.py` | `template_generation_plan.json` |
| 阶段五：Word action 执行 | `executor.py` | `generated_template.docx` 和执行结果 |
| manifest 生成 | `manifest.py` | `template_generation_manifest.json` |
| public artifacts 和 debug 快照写出 | `outputs.py` | `--out/artifacts/` 和 debug 目录文件 |
| source reference 定位工具 | `refs.py` | 被阶段模块复用 |
| 文本规范化工具 | `text_utils.py` | 被阶段模块复用 |
| python-docx 底层操作 | `word_ops.py` | 被执行阶段复用 |

当前语义边界已经比最初 runner 单文件更清楚：`discovered_template_rules` 里的元素带 `role_hint` 和 `evidence`；`generation_model.py` 会把候选 `policy` materialize 成阶段三最终 `policy`。copy-only 单元内部的 `fill` / `generated` 候选会保留为证据但最终变成 `fixed`，不会生成 slot；`remove_instruction` 候选会进入 cleanup。

## 当前真实输出

当前代码仍写出旧的公开产物名和旧的 debug 编号。排查现有运行结果时，应按这张表定位：

| 编号 | 当前文件 | 说明 |
| --- | --- | --- |
| `00` | `00_input_source_template.docx` | 输入学校原始模板 Word |
| `01` | `01_template_generation_request.json` | 本次生成请求 |
| `02` | `02_source_template_tree.json` | 阶段一：源 Word 事实 |
| `03` | `03_discovered_template_rules.json` | 阶段二：候选结构识别，当前旧产物名 |
| `04` | `04_template_artifact.json` | 阶段三的一部分：模板业务地图，当前旧产物名 |
| `05` | `05_template_unit_decisions.json` | 阶段三的一部分：处理策略，当前旧产物名 |
| `06` | `06_template_generation_plan.json` | 阶段四：动作计划 |
| `07` | `07_copy_source_docx.docx` | 阶段五：只执行整包复制后的 Word 停点 |
| `08` | `08_generated_template.docx` | 阶段五：执行全部 action 后的生成模板 Word |
| `09` | `09_template_generation_manifest.json` | 阶段五：执行记录和输出 hash |
| `10` | `10_template_generation_debug_index.json` | 本 debug 目录的文件索引 |

这些旧名字是当前真实实现，不是下一轮目标。下一轮改名时，应同步更新生产者、消费者、测试和报告引用，不为旧产物名额外保留兼容输出。

## 下一轮目标输出

下一轮目标是让文件编号按阶段命名：整数部分对应阶段，点后面对应该阶段内的子产物；`00` 留给输入、请求和运行上下文，`99` 留给索引、汇总和非阶段性说明。

| 编号 | 目标文件 | 说明 |
| --- | --- | --- |
| `00` | `00_input_source_template.docx` | 运行输入：学校原始模板 Word，不属于阶段一 |
| `00` | `00_template_generation_request.json` | 运行请求：记录源文件、输出目录和策略，不属于阶段一 |
| `01` | `01_source_template_tree.json` | 阶段一：源 Word 事实 |
| `02` | `02_template_structure_candidates.json` | 阶段二：候选结构识别的目标主产物 |
| `03` | `03_template_generation_model.json` | 阶段三：生成模板模型与策略的目标主产物 |
| `04` | `04_template_generation_plan.json` | 阶段四：动作计划 |
| `05.0` | `05.0_copy_source_docx.docx` | 阶段五：只执行整包复制后的停点 |
| `05.1` | `05.1_generated_template.docx` | 阶段五：执行全部 action 后的 Word |
| `05.2` | `05.2_template_generation_manifest.json` | 阶段五：执行记录和输出 hash |
| `99` | `99_template_generation_debug_index.json` | 非阶段文件：本 debug 目录索引 |

小数点不是数学小数，而是 `阶段.子步骤` 标号。后续如果某阶段内子产物超过 9 个，可以改用 `02.01`、`02.02` 这种两位子步骤，避免文件排序混乱。

## 已完成

| 已完成事项 | 证据 |
| --- | --- |
| `runner.py` 拆成阶段模块 | 提交 `0db2f4d refactor(template-generate): split runner modules` |
| copy-only 内部说明文字可以清理 | 提交 `304d613 feat(template-generate): clean copy-only instructions` |
| 阶段三 materialize 最终策略 | 提交 `526196f refactor(template-generate): materialize candidate policies in model` |
| 聚焦合同测试通过 | `uv run pytest tests/contract/test_template_generate.py -q` -> `9 passed` |
| 合同测试通过 | `uv run pytest tests/contract -q` -> `71 passed` |
| 真实模板生成通过 | `uv run docfit eval template-generate --template test_inputs/template_generation/school-hunannongye-requirement.docx --out test_outputs/debug/template_generation/school-hunannongye-requirement/eval_runs/template_generate_split_check` -> `status = PASS` |
| 当前 debug 快照仍写出旧编号 | 真实运行写出 `00_input_source_template.docx` 到 `10_template_generation_debug_index.json` |

## 仍需补齐

| 剩余工作 | 应该改哪里 | 验收重点 |
| --- | --- | --- |
| 阶段一新增 `source_seq` | `source_tree.py`、相关 schema 和测试 | 每个可追踪元素都有稳定序号，后续合并、删除、保留都能引用原始序号 |
| 阶段二目标产物改名 | `structure_candidates.py`、`outputs.py`、消费者和测试 | `discovered_template_rules` 切到 `template_structure_candidates`，不双写旧名 |
| 阶段三目标产物合并 | `generation_model.py`、`outputs.py`、消费者和测试 | `template_artifact` 与 `template_unit_decisions` 收敛为 `template_generation_model`，合并对象保留来源序号 |
| debug 编号按阶段重命名 | `outputs.py` 和 debug index | 新文件名按 `00 / 01 / 02 / 03 / 04 / 05.x / 99` 写出 |
| 报告和测试引用同步更新 | summary、template-gap、e2e 或合同测试中读取旧名的代码 | 没有残留旧产物名依赖 |
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
  --template test_inputs/template_generation/school-hunannongye-requirement.docx \
  --out test_outputs/debug/template_generation/school-hunannongye-requirement/eval_runs/template_generate_target_contract
```

如果新增 `source_seq`，还需要补聚焦测试证明：

| 用例 | 证明什么 |
| --- | --- |
| 单个元素保留 | 输出对象能引用原始 `source_seq` |
| 多个元素合并 | 合并后对象能列出全部来源序号，例如 `3,4,5` |
| 元素删除 | cleanup / report 能说明删除了哪个 `source_seq` |
| AI 自检或人工沟通 | finding / evidence 能用 `source_seq` 定位问题来源 |
