# 模板生成阶段优化总览

Last updated: 2026-06-25

> 迁移提示：本文保留 2026-06-22 以前的 00-05 优化地图，当前主线已经切换为
> `document_facts -> unit_map -> element_spec -> global_spec -> template_spec ->
> fillable_template + build_manifest`。当前字段、命令和门禁以
> `docs/current/template-generation.md` 为准；本文只作为旧优化背景和兼容视图排查参考。

一句话结论：这份文档把分散在模板生成主文档和计划文档里的内容收成一张当前可执行地图；它说明每个阶段当前代码已经做到什么、下一步应该改哪里、出了问题先看哪个产物。

## 文档定位

模板生成相关内容现在分在几类文档里：

| 文档 | 当前用途 | 什么时候读 |
| --- | --- | --- |
| `docs/current/template-generation.md` | 当前模板生成支撑流程的主说明，说明命令、产物、字段规则和 `template-gap` 边界 | 改模板生成字段、产物、manifest、gap 报告前先读 |
| `docs/current/template-generation-stage-optimization.md` | 本文；把阶段优化计划归纳成一份当前执行地图 | 讨论“各阶段代码下一步怎么改”时读 |
| `docs/current/template-generation-evaluation.md` | 模板生成评测与测试架构，说明最终 gap、阶段检查骨架和测试边界 | 讨论“怎么验、哪些阶段先登记、哪些检查器还没配置”时读 |
| `docs/plans/template-generation-flow-optimization.md` | 历史方案和执行记录，保留旧产物、阶段评测设想和细节推演 | 需要查设计背景、旧方案为什么改掉时读；不要采用其中“学校标准或学生内容台账作为生成输入”的旧设想 |
| `docs/plans/template-generate-runner-split.md` | runner 拆分后的模块地图和历史剩余工作清单 | 查当前模块职责或拆分证据时读；剩余工作以本文和待核实差距清单为准 |

本文只写当前应该相信的主线，不把历史旧产物当成当前实现。历史旧产物名只在说明迁移背景时出现。

## 当前真实链路

模板生成是模板侧支撑流程，不是 DocFit 四个业务阶段之外的新业务阶段。它的职责是把学校原始模板 Word 变成可填写模板和过程证据；学校格式是否合格仍由 `template-gap` 判断。

当前代码链路：

```text
00 输入和请求
  -> 01 source_template_tree
  -> 02 template_structure_candidates
  -> 03 template_generation_model
  -> 04 template_generation_plan
  -> 05 执行 Word action 和 manifest
  -> 06 template-gap 检查生成模板是否符合学校标准
```

当前 runner 调用链：

```python
request = build_template_generation_request(...)
source_tree = inspect_source_template_docx(source_template_docx)
structure_candidates = build_template_structure_candidates(source_tree)
generation_model = build_template_generation_model(
    request,
    structure_candidates=structure_candidates,
)
plan = build_template_generation_plan(
    request,
    generation_model=generation_model,
)
manifest = build_template_generation_manifest(
    request=request,
    source_tree=source_tree,
    structure_candidates=structure_candidates,
    generation_model=generation_model,
    plan=plan,
    ...
)
```

注意：这里的 `template_generation_model.json` 只属于 `template_generate` 支撑流程。业务四阶段里的模板解析产物 `template_artifact.json` 仍然属于 `template_parse`，不是这次改名范围。

## 阶段产物和文件编号

| 编号 | 产物 | 当前生产者 | 主要消费者 | 能证明什么 |
| --- | --- | --- | --- | --- |
| `00` | `template_generation_request.json`、`00_input_source_template.docx` | `request.py`、`outputs.py` | 后续所有阶段、debug | 本次运行用的是哪份源模板和哪些输入 |
| `01` | `source_template_tree.json` | `source_tree.py` | `structure_candidates.py` | 源 Word 里实际观察到了什么 |
| `02` | `template_structure_candidates.json` | `structure_candidates.py` | `generation_model.py` | 候选 unit、logical element、`role_hint`、证据和来源序号 |
| `03` | `template_generation_model.json` | `generation_model.py` | `plan.py` | 最终模板业务模型、单元策略、slots、protected zones、cleanup |
| `04` | `template_generation_plan.json` | `plan.py` | `executor.py`、manifest | 要执行哪些 Word action，每个 action 影响哪些源元素 |
| `05.0` | `05.0_copy_source_docx.docx` | `executor.py` | 人工 diff、debug | 只做整包复制后的停点 |
| `05.1` | `generated_template.docx`、`05.1_generated_template.docx` | `executor.py` | `template-gap`、后续流程 | 执行 action 后的生成模板 Word |
| `05.2` | `template_generation_manifest.json` | `manifest.py` | 报告、审计、debug | 实际执行了什么、输出 hash 是什么 |
| `99` | `99_template_generation_debug_index.json` | `outputs.py` | 人工排查 | 调试目录索引 |

编号规则：整数部分对应阶段；点后面是阶段内子产物；`00` 给输入和请求；`99` 给索引和非阶段性说明。小数点不是数学小数，也不是旧流水编号兼容。

## 全流程来源序号

当前全流程必须保留源模板元素序号：

| 字段 | 谁生产 | 谁消费 | 用途 |
| --- | --- | --- | --- |
| `source_seq` | 阶段一 | 后续所有阶段 | 给源模板每个可见元素一个稳定编号 |
| `source_seq_label` | 阶段一 | debug、报告、人工沟通 | 人读标签，例如 `源模板元素 003` |
| `source_seq_refs[]` | 阶段二起 | 阶段三、阶段四、manifest | 说明一个对象来自哪些阶段一元素 |
| `affected_source_seq_refs[]` | 阶段四 | 阶段五、manifest、人工复核 | 说明一个 action 影响或记录了哪些源元素 |

这条规则解决的是定位问题：如果人工说“源模板元素 12 不该删除”，排查时先用 `indexes.by_source_seq["12"]` 找到阶段一原始节点，再查阶段二哪个 logical element 引用了 12，阶段三是否把它转成 cleanup，阶段四哪个 action 影响了它。

## 各阶段代码优化计划

### 阶段一：源 Word 事实

当前真实实现：

| 项 | 当前情况 |
| --- | --- |
| 模块 | `src/docfit/template_generation/source_tree.py` |
| 产物 | `source_template_tree.json` |
| 已完成 | 解析段落、表格、页眉页脚、section、编号、unknown objects；给 `body_flow[]` 分配连续 `source_seq`；写 `indexes.by_source_seq` |
| 不负责 | 不判断 unit，不决定 copy-only，不生成 slot，不判断学校标准 |

下一步优化：

| 要改什么 | 为什么 | 验收重点 |
| --- | --- | --- |
| 更完整表达文本框、drawing、复杂可见对象 | 当前 unknown objects 会让下游证据不足 | unknown 可见对象不能静默丢失，必须进入 `UNKNOWN` 或待复核证据 |
| 改善表格单元格和段落的结构坐标 | 阶段二要合并 label/value 和定位误删 | 每个表格片段能稳定回到 table、row、cell 和 `source_seq` |
| 保持 `source_seq` 只在阶段一分配 | 后续合并、删除、保留都要引用原序号 | 后续阶段不能重编号或补造序号 |

### 阶段二：候选结构识别

当前真实实现：

| 项 | 当前情况 |
| --- | --- |
| 模块 | `src/docfit/template_generation/structure_candidates.py` |
| 产物 | `template_structure_candidates.json` |
| 已完成 | 识别候选 unit；生成 logical element；连续说明文字、表格同一行 label/value、跨段落业务句 continuation 可以合并；输出 `candidate_policy`、`role_hint`、`evidence[]`、`source_seq_refs[]`、`source_context` |
| 不负责 | 不决定最终 `generation_mode`，不生成 slot，不生成 Word action |

下一步优化：

| 要改什么 | 应该改哪里 | 验收重点 |
| --- | --- | --- |
| 固定枚举化 `role_hint` | element policy 规则 | 阶段三不消费自由文本猜测 |
| 补 `conflicts[]` 和 `open_questions[]` | structure candidates 顶层和 unit/element 层 | 证据不足不伪装成确定策略 |
| 更明确的 copy-only 内部候选边界 | `_copy_only_unit_elements` | 说明文字可进入 cleanup，填写痕迹只作为证据，不能在阶段二变 slot |

### 阶段三：生成模板模型与策略

当前真实实现：

| 项 | 当前情况 |
| --- | --- |
| 模块 | `src/docfit/template_generation/generation_model.py` |
| 产物 | `template_generation_model.json` |
| 已完成 | 消费阶段二 `template_structure_candidates`；输出 `unit_strategies[]`、`slots[]`、`required_fields[]`、`protected_zones[]`、`cleanup[]`、`unsupported[]`、`unresolved_questions[]` |
| 不负责 | 不直接改 Word，不重新解析源 DOCX，不替代 `template-gap` 判定学校合格性 |

当前策略仍以全局 copy-only 基线为起点。默认 copy-only 单元使用正向白名单；未命中白名单的单元（尤其是 `custom:template:*` / `other`）默认走 `copy_then_patch`，不再因未知而整单元冻结。

下一步优化：

| 要改什么 | 应该改哪里 | 验收重点 |
| --- | --- | --- |
| 强化源模板责任推断 | `generation_model.py` 和阶段二候选证据 | 不把 `standards/targets/**` 当成生成输入；只根据源模板里的结构、文字、样式、占位符、表格、字段和通用规则决定 copy-only / patch |
| 明确模板内容责任 | generation model 输入 | 致谢、附录等条件单元先按源模板自身证据识别为固定保留、用户填写、系统生成或需要人工确认；模板生成阶段不读取某一次学生源内容台账，也不读取学校签收标准 |
| 强化 `unresolved_questions[]` | `_unresolved_questions_from_candidates` 和策略构建 | 强填写信号、源模板证据不足、unknown visible objects 都要集中表达 |
| 把策略理由写成人能读懂的证据 | `unit_strategies[]`、cleanup、protected zones | 人工能看懂为什么元素 3、4、5 被合并并删除，或为什么元素 12 被保护 |

### 阶段四：动作计划

当前真实实现：

| 项 | 当前情况 |
| --- | --- |
| 模块 | `src/docfit/template_generation/plan.py` |
| 产物 | `template_generation_plan.json` |
| 已完成 | 只消费 `template_generation_model`；把 unit 策略、slots、cleanup、page/section 规则转成 action；action 带 `affected_source_seq_refs[]` |
| 不负责 | 不重新判断 unit 语义，不反推阶段二/三策略 |

下一步优化：

| 要改什么 | 为什么 | 验收重点 |
| --- | --- | --- |
| 为修改型 action 补完整影响范围 | 误删定位必须从 action 回到源元素 | `remove_instruction_text`、slot、generated field、manual placeholder 都能说明影响哪些 `source_seq` |
| 增强 action 之间的冲突检查 | 同一源元素不能同时被删除又被保护 | 冲突进入 `needs_review` 或 `UNKNOWN` |
| 把页面/section action 的来源说清楚 | 当前页面规则容易被误认为最终视觉证明 | action 只说明执行计划，视觉合格仍由 gap / inspector 判断 |

### 阶段五：执行与 manifest

当前真实实现：

| 项 | 当前情况 |
| --- | --- |
| 模块 | `executor.py`、`manifest.py`、`outputs.py` |
| 产物 | `generated_template.docx`、`template_generation_manifest.json`、debug 快照 |
| 已完成 | 先整包复制，再执行 action；manifest 记录执行动作、slot、generated field、输出 hash；debug 文件按阶段编号写出 |
| 不负责 | 不决定内容应该放哪里，不证明学校格式通过 |

下一步优化：

| 要改什么 | 为什么 | 验收重点 |
| --- | --- | --- |
| manifest 强化 `source_seq` 可读性 | 方便人工说“12 不该删”后直接定位 | `actions_executed[]`、`slots[]`、`generated_fields[]` 都保留来源序号 |
| 输出执行前后 diff 摘要 | 只看 Word 不容易知道 action 改了哪里 | `05.0` 到 `05.1` 的变化能对应到 action id 和 `source_seq` |
| 待复核动作集中展示 | 不能把 unsupported 或冲突藏在 manifest 深处 | `actions_requiring_review[]` 能进报告 |

## first_bad_stage 快速定位

| 现象 | 先看什么 | first_bad_stage | 应该改哪里 |
| --- | --- | --- | --- |
| 输入文件不对 | `00_input_source_template.docx`、request | `00_input_request` | 调用命令或 profile 绑定 |
| 源 Word 内容没解析出来 | `01_source_template_tree.json` | `01_source_parse` | `source_tree.py` 或底层 inspector |
| unit 没识别或边界错 | `02_template_structure_candidates.json` | `02_structure_discovery` | `structure_candidates.py` |
| logical element 合并错 | `02` 的 `entry_refs[]`、`source_seq_refs[]`、`merge` | `02_structure_discovery` | `_logical_entry_groups` |
| 源模板元素 12 不该删除 | 先查 `by_source_seq["12"]`，再查阶段二/三/四引用链 | `02_structure_discovery` / `03_generation_model` / `04_plan_build` | 找到第一次把 12 判错的阶段再改 |
| 应 copy-only 的单元生成了 slot | `03_template_generation_model.json` 的 `unit_strategies[]` 和 `slots[]` | `03_generation_model` | copy-only 基线、源模板责任推断规则或不确定性表达 |
| plan 对但 Word 没变 | `04_template_generation_plan.json`、`05.0`、`05.1` | `05_action_execution` | `executor.py` |
| Word 看起来不合格 | `generated_template_tree.json`、`template_gap_report.*` | `06_final_template_gap` 或更早阶段 | 先看 gap 指向的源证据，再回查 01-05 |

## 当前验证记录

| 日期 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- |
| 2026-06-22 | `uv run python -m py_compile src/docfit/template_generation/*.py` | `PASS` | 模板生成阶段模块语法检查通过 |
| 2026-06-22 | `uv run pytest tests/contract/test_template_generate.py -q` | `PASS`，9 passed | 覆盖新阶段产物、debug 编号、`source_seq`、action 来源追踪 |
| 2026-06-22 | `uv run pytest tests/contract -q` | `PASS`，71 passed | 合同测试矩阵通过，真实 real-core 链路没有说明文字泄漏回归 |
| 2026-06-22 | `uv run pytest tests/contract/test_template_generate.py -q` | `PASS`，11 passed | 覆盖阶段二表格 label/value 合并、跨段落业务句 continuation 合并和来源序号保留 |
| 2026-06-22 | `uv run pytest tests/contract -q` | `PASS`，73 passed | 合同测试矩阵通过，阶段二合并增强没有破坏现有消费者 |
| 2026-06-22 | `uv run docfit eval template-generate --template inputs/targets/hunannongye/raw/source_template.docx --out runs/template_generation/school-hunannongye-requirement/eval_runs/template_generate_stage2_merge_check` | `PASS` | 真实湖南农业大学模板生成命令仍能写出生成模板和阶段产物 |

这些验证只证明模板生成支撑流程按当前合同工作；不证明任何真实学校生成模板已经满足最终学校格式标准。真实学校合格性仍必须看 `template-gap` 的 `PASS / FAIL / UNKNOWN`。

## 工作包状态

| 优先级 | 工作包 | 目标文件 | 状态 |
| --- | --- | --- | --- |
| 1 | 补阶段二更深 logical element 合并 | `structure_candidates.py`、`tests/contract/test_template_generate.py` | 已完成；表格 label/value、跨段落 continuation 能合并并保留全部来源序号 |
| 2 | 阶段三强化源模板责任推断和模板内容责任 | `generation_model.py`、`structure_candidates.py` | copy-only / patch 不只靠全局 unit_id 基线，也不依赖某一次学生源内容台账或学校签收标准 |
| 3 | 阶段检查归因落地 | harness/report 层 | 能表达 `input_check`、`output_check`、`first_bad_phase`、下游症状 |
| 4 | 报告可读性增强 | manifest、pm report、debug index | 人工能从报告直接定位到源模板元素序号和 action |

当前待核实差距清单见：

- `docs/current/template-generation-open-gaps.md`

每做一个工作包，至少运行：

```bash
uv run pytest tests/contract/test_template_generate.py -q
```

如果改到消费者、报告或 e2e 引用，再补：

```bash
uv run pytest tests/contract -q
```
