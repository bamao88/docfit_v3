# 模板生成产物字段定义

Last updated: 2026-06-21

## 这个文件做什么

这个文件定义模板生成阶段各个产物里的关键字段。

它解决的不是“流程怎么讲清楚”，而是更具体的问题：

- 一个字段到底表示什么；
- 谁可以写这个字段；
- 谁会读取这个字段；
- 这个字段是否参与 `PASS` / `FAIL` / `UNKNOWN` 判定；
- 字段缺失时应该阻断、失败，还是进入待确认；
- AI 或开发代码能不能自动改这个字段。

如果后续要把模板生成文档拆成 `docs/spec/template-generation/01-artifact-field-dictionary.md`，
本文件就是那份字段字典的当前仓库版本。现在先放在 `docs/human/**`，因为这里是本仓库当前的人类可读文档面。

相关上游文档：

- `docs/human/template-generation-business-flow-current-state.md` 说明模板生成主线怎么跑。
- `docs/human/template-gap-process-mainline.md` 说明生成模板差距检查怎么判定。
- `SPEC.md` 说明整个 DocFit 的 `PASS` / `FAIL` / `UNKNOWN` 和 gate 语义。

## 总原则

### 1. 没有字段定义，不新增字段

新增、修改或删除字段前，必须先补清楚下面这张表：

| 项 | 必填说明 |
| --- | --- |
| 字段名 | 写完整路径，例如 `template_artifact.data.units[].unit_id` |
| 所在产物 | 例如 `template_artifact.json` |
| 业务含义 | 用普通话说明它代表什么，不只写英文名 |
| 类型和允许值 | string、enum、array、object；枚举值必须列出 |
| 是否必填 | 是、否、视单元而定 |
| 生产者 | 哪个阶段或代码负责写 |
| 消费者 | 哪个阶段、检查器或报告读取 |
| 是否参与判定 | 是否会影响 `PASS` / `FAIL` / `UNKNOWN` |
| 缺失时结果 | `FAIL`、`UNKNOWN`、`needs_review` 或不阻断 |
| 默认值规则 | 是否允许默认值；不允许就写“无默认” |
| 是否允许人工编辑 | 是否能由人工标准或 review 修改 |
| 是否允许 AI 自动修改 | 默认不允许改签收标准和检查结果 |
| 证据要求 | 需要 `source_ref`、hash、snapshot 或审计记录吗 |
| 测试要求 | 需要补哪个阶段或检查器测试 |

如果一个字段没有明确消费者，先不要加。
如果一个字段有消费者，就必须定义缺失后果。

### 2. 字段不能靠猜默认

这些字段不能随便默认：

```text
unit_id
unit_type / policy
element_id
element policy
anchor role
required
slot_id
source_ref
output_ref
style rule
page rule
field kind
source evidence
check status
```

除非字段定义明确允许默认值，否则缺失时只能进入 `UNKNOWN`、`needs_review` 或阻断失败。
不能为了让流程跑通，把缺字段默认成看起来合理的值。

### 3. 不同产物不能互相冒充

这条是模板生成阶段最重要的边界：

| 产物 | 它能证明什么 | 它不能证明什么 |
| --- | --- | --- |
| `source_template_tree` | 学校原始 Word 里观察到了什么 | 不能证明哪个内容一定是学校规则 |
| `discovered_template_rules` | 系统从源 Word 推断出的候选规则 | 不能当作人工签收标准 |
| `template_artifact` | 系统如何理解学校原始模板 | 不能证明生成 Word 实际长什么样 |
| `template_generation_manifest` | 生成器尝试做了什么 | 不能证明 Word 里最终真的存在对应内容 |
| `generated_template_tree` | 被测生成 Word 实际解析出了什么 | 不能替代学校标准 |
| `template_gap_report` | 检查器怎么判定差距 | 不能反过来当标准，也不能被 AI 改成通过 |

正确链路是：

```text
manifest 说明生成器尝试执行动作
generated_template_tree 说明真实 generated_template.docx 里解析到的事实
template_gap_report 根据真实 Word 事实和签收标准给出 PASS / FAIL / UNKNOWN
```

错误链路是：

```text
manifest 里说生成了标题
所以 gap 判定标题存在
```

## 产物流转

| 顺序 | 产物 | 类型 | 主要生产者 | 主要消费者 | 是否直接参与 gate |
| --- | --- | --- | --- | --- | --- |
| 1 | `source_template_tree.json` | 源 Word 观察结果 | source template inspector | rule discovery、artifact builder | 间接参与；缺失会让后续无法证明 |
| 2 | `discovered_template_rules.json` | 候选模板规则 | rule discovery | artifact builder、开发排查 | 开发期可参与；不能单独正式 PASS |
| 3 | `template_artifact.json` | 源模板理解结果 | template artifact builder | generation decisions、placement/render 上下文 | 间接参与；不能替代生成 Word 检查 |
| 4 | `template_unit_decisions.json` | 单元处理决定 | decision builder | generation plan builder | 不直接参与；缺失会让生成过程不可解释 |
| 5 | `template_generation_plan.json` | 可执行动作清单 | plan builder | generator executor | 不直接参与；manifest 会记录执行结果 |
| 6 | `generated_template.docx` | 可填写模板 Word | generator executor | template-gap、placement/render | 是，被测生成模板 |
| 7 | `template_generation_manifest.json` | 生成过程记录 | generator executor | e2e 解释、审计、debug | 间接参与；不能证明 Word 事实 |
| 8 | `generated_template_tree.json` | 生成 Word 实际结构 | generated template inspector | template-gap checker | 是，gap 的事实输入 |
| 9 | `template_gap_report.json/.md/.docx` | 差距检查报告 | template-gap checker | coverage、e2e、人工排查 | 是，阻断状态来源 |

## 公共字段

这些字段出现在多数 JSON 产物里。

| 字段 | 含义 | 类型 | 是否必填 | 生产者 | 消费者 | 参与判定 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `artifact_type` | 产物身份，例如 `template_artifact` | string enum | 是 | 产物生产阶段 | 读产物的阶段、测试 | 是 | `UNKNOWN`：不能确认文件身份 | 否 |
| `artifact_version` | 产物结构版本 | string | 是 | 产物生产阶段 | 兼容层、测试 | 是 | `UNKNOWN`：不能确认字段语义 | 受控迁移 |
| `producer.name` | 写出产物的组件 | string | 是 | 产物生产阶段 | 审计、报告 | 间接 | 报告审计不足；重要 gate 可 `UNKNOWN` | 否 |
| `producer.version` | 写出产物的组件版本 | string | 应该有 | 产物生产阶段 | 审计、报告 | 间接 | 缺审计信息，不应直接 PASS 发布 | 否 |
| `created_at` | 本次产物创建时间 | ISO string | 是 | 产物生产阶段 | 审计、排查 | 间接 | 审计不足；不单独改状态 | 否 |
| `input_hashes.*` | 输入产物或文件 hash | object | 视产物而定 | 当前阶段 | 防漂移、gate | 是 | `UNKNOWN`：不能证明输入一致 | 否 |

## `source_template_tree`

这个产物只记录“从学校原始 Word 观察到了什么”。它不能直接判断学校意图。

| 字段 | 含义 | 类型 | 是否必填 | 生产者 | 消费者 | 参与判定 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `metadata.source_template_docx` | 学校原始 Word 路径 | string path | 是 | template-generate 阶段 1 | 后续 provenance、排查 | 是 | `UNKNOWN`：不能追溯来源 | 否 |
| `metadata.source_template_hash` | 学校原始 Word hash | string | 是 | template-generate 阶段 1 | artifact builder、审计 | 是 | `UNKNOWN`：不能证明处理的是同一份源文件 | 否 |
| `metadata.input_exists` | 源文件是否存在 | boolean | 是 | inspector | runner、报告 | 是 | `UNKNOWN`：源文件不存在或无法确认 | 否 |
| `metadata.input_valid_docx` | 源文件是否有效 DOCX | boolean | 是 | inspector | runner、报告 | 是 | `FAIL`：确认不是有效 DOCX；无法读取则 `UNKNOWN` | 否 |
| `layers.package_global.numbering_definitions` | Word 编号定义 | array | 否 | OOXML inspector | rule discovery、numbering 检查 | 是，涉及编号时 | 缺失且需要编号证据时 `UNKNOWN` | 否 |
| `layers.section_rules[]` | section 级页面规则 | array | 否 | OOXML inspector | page/header/footer 识别 | 是，涉及页面规则时 | 缺失且标准要求页面规则时 `UNKNOWN` | 否 |
| `layers.header_footer[]` | 页眉页脚实际内容 | array | 否 | OOXML inspector | rule discovery、gap 上下文 | 是，涉及页眉页脚时 | 缺失且标准要求时 `UNKNOWN` | 否 |
| `layers.body_flow[]` | 正文主流里的节点序列 | array | 是 | OOXML inspector | rule discovery、unit 切分 | 是 | `UNKNOWN`：不能稳定识别单元 | 否 |
| `layers.body_flow[].node_id` | 节点稳定 ID | string | 应该有 | inspector | plan/action 引用 | 是 | `UNKNOWN`：后续动作不能稳定引用 | 否 |
| `layers.body_flow[].source_ref` | OOXML 来源位置 | string | 是 | inspector | plan、manifest、gap evidence | 是 | `UNKNOWN`：不能证明字段来源 | 否 |
| `layers.body_flow[].order` | 节点在正文流中的顺序 | number | 是 | inspector | 单元切分、区域定位 | 是 | `UNKNOWN`：不能稳定判断前后顺序 | 否 |
| `layers.body_flow[].text` | 节点可见文字 | string | 否 | inspector | rule discovery、元素识别 | 是，涉及文本时 | 无文本不等于缺失；按节点类型继续判断 | 否 |
| `layers.unknown_objects[]` | 当前不能解释的可见对象 | array | 是 | inspector | artifact、coverage、report | 是 | 可见但未建模对象必须 `UNKNOWN` 或 `FAIL`，不能静默丢弃 | 否 |
| `warnings[]` | 解析时发现的问题 | array | 否 | inspector | 报告、debug | 间接 | 视严重程度进入 `UNKNOWN` | 否 |

### `source_template_tree` 边界

- 允许说“源 Word 第 12 个段落是居中文本”。
- 不允许直接说“第 12 个段落就是目录单元”。
- 不允许把页眉页脚混进正文流当正文单元定位依据。
- 不允许忽略可见但未建模对象。

## `discovered_template_rules`

这个产物记录系统从源 Word 推断出来的候选规则。开发期可以拿它和人工整理样本对齐；正式 gate 不能只靠它自证成功。

| 字段 | 含义 | 类型 | 是否必填 | 生产者 | 消费者 | 参与判定 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `source_template_hash` | 候选规则来源的源 Word hash | string | 是 | rule discovery | artifact builder、审计 | 是 | `UNKNOWN`：规则来源不可追溯 | 否 |
| `discovery_method` | 规则识别方法 | string enum | 是 | rule discovery | 报告、审计 | 间接 | 不能解释规则来源；开发 gate 应阻断 | 否 |
| `units[]` | 识别出的模板单元 | array | 是 | rule discovery | artifact builder、generator | 是 | 缺 required 单元时 `UNKNOWN` 或 `FAIL`，取决于是否有签收标准 | 受控修改 |
| `units[].unit_id` | 单元稳定 ID | string | 是 | rule discovery 或 signed standard 对齐 | generator、gap、report | 是 | `FAIL`：不能稳定引用单元 | 否，除非迁移所有引用 |
| `units[].name` | 单元中文名或业务名 | string | 是 | rule discovery / standard | 报告、人工排查 | 间接 | 报告可读性下降；不单独 PASS | 只允许根据证据改 |
| `units[].order` | 单元顺序 | number | 是 | rule discovery / standard | generator、gap | 是 | `UNKNOWN`：不能判断顺序和范围 | 受控修改 |
| `units[].status` | 单元是否必需或默认可选 | enum | 是 | rule discovery / standard | gap、coverage | 是 | `UNKNOWN`：不能决定缺失是失败还是可选 | 受控修改 |
| `units[].policy` | 单元整体处理策略 | enum | 是 | rule discovery / standard | decision builder | 是 | `UNKNOWN`：不能选择生成策略 | 受控修改 |
| `units[].source_refs[]` | 单元来源节点 | array string | 视单元而定 | rule discovery | plan、manifest、debug | 是 | `UNKNOWN`：不能可靠复制或定位 | 否 |
| `units[].elements[]` | 单元内元素 | array | 是 | rule discovery / standard | decision builder、gap | 是 | required 元素缺失时 `UNKNOWN` 或 `FAIL` | 受控修改 |
| `elements[].element_id` | 元素稳定 ID | string | 是 | rule discovery / standard | slot、field、gap | 是 | `FAIL`：不能稳定引用元素 | 否，除非迁移引用 |
| `elements[].policy` | 元素处理方式 | enum | 是 | rule discovery / standard | decision builder、generator、gap | 是 | `UNKNOWN`：不能决定保留、填充、生成或删除 | 受控修改 |
| `elements[].content` | 元素期望可见内容或标签 | string | 视 policy 而定 | rule discovery / standard | gap、generator | 是，涉及内容时 | 必需固定内容缺失为 `FAIL`；证据不足为 `UNKNOWN` | 只允许根据证据改 |
| `unknowns[]` | 无法归类的源 Word 内容 | array | 是 | rule discovery | artifact、报告 | 是 | 不能静默丢弃；进入 `UNKNOWN` 或待 review | 否 |
| `source_discovery` | 用签收标准对齐时保留的原始自动识别结果 | object | 否 | target-unit alignment | debug、审计 | 间接 | 缺失不单独阻断，但会降低排查能力 | 否 |

推荐的 `elements[].policy` 允许值：

```text
fixed
fill
generated
manual_only
remove_instruction
```

新增 policy 前，必须先说明 generator 怎么处理、gap 怎么检查、缺失时怎么判。

## `template_artifact`

这个产物表示“系统如何理解学校原始模板”。它是生成器和后续 placement/render 的结构上下文，但不是被测生成 Word 的事实。

| 字段 | 含义 | 类型 | 是否必填 | 生产者 | 消费者 | 参与判定 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `input_hashes.template_docx` | 源 Word hash | string | 是 | artifact builder | audit、e2e | 是 | `UNKNOWN`：源模板理解不可追溯 | 否 |
| `input_hashes.source_template_tree` | 源结构树 hash | string | 是 | artifact builder | audit、tests | 是 | `UNKNOWN`：不能证明理解基于哪个结构树 | 否 |
| `input_hashes.discovered_template_rules` | 候选规则 hash | string | 是 | artifact builder | audit、tests | 是 | `UNKNOWN`：不能证明规则来源 | 否 |
| `provenance.template_docx` | 源模板路径；e2e 中可被绑定到本次生成模板路径用于下游底稿 | string path | 是 | artifact builder / orchestrator | placement、render、report | 是 | `UNKNOWN`：后续不知道以哪个 Word 为底稿 | 否 |
| `status_notes[]` | 当前 artifact 的限制说明 | array string | 应该有 | artifact builder | 人工排查 | 间接 | 缺失不改变判定，但不应掩盖能力限制 | 可补说明，不能改结果 |
| `data.source_template_tree` | 源结构树文件名引用 | string | 是 | artifact builder | debug、audit | 间接 | 缺引用会降低可追溯性 | 否 |
| `data.discovered_template_rules` | 规则文件名引用 | string | 是 | artifact builder | debug、audit | 间接 | 缺引用会降低可追溯性 | 否 |
| `data.units[]` | 模板单元主表 | array | 是 | artifact builder | decisions、plan、gap 上下文 | 是 | required 单元缺失时 `FAIL` 或 `UNKNOWN` | 受控修改 |
| `data.units[].unit_id` | 单元稳定 ID | string | 是 | artifact builder | decisions、plan、slot、gap | 是 | `FAIL`：无法稳定引用单元 | 否，除非迁移引用 |
| `data.units[].elements[]` | 单元元素 | array | 是 | artifact builder | decisions、plan、gap | 是 | required 元素缺失时按标准判 `FAIL` / `UNKNOWN` | 受控修改 |
| `data.instruction_paragraphs[]` | 应从生成模板清理的说明文字 | array | 否 | artifact builder | plan builder | 是，涉及说明文字泄漏时 | 缺失会导致说明文字可能泄漏；检查到泄漏时 `FAIL` | 只允许根据源证据改 |
| `data.regions[]` | 后续可引用的模板区域 | array | 是 | artifact builder | placement、render、debug | 是 | `UNKNOWN`：无法定位或保护区域 | 受控修改 |
| `data.slots[]` | 后续可写位置 | array | 是 | artifact builder | placement、render、gap | 是 | 必需 slot 缺失为 `FAIL`；无法确认为 `UNKNOWN` | 否，除非同步迁移 |
| `data.slots[].slot_id` | slot 稳定 ID | string | 是 | artifact builder | placement、render | 是 | `FAIL`：后续内容无稳定写入点 | 否，除非迁移引用 |
| `data.slots[].unit_id` | slot 所属单元 | string | 是 | artifact builder | placement、report | 是 | `UNKNOWN`：不能判断内容写入哪个单元 | 否 |
| `data.slots[].accepted_content_kinds` | slot 可接受的内容类型 | array enum | 应该有 | artifact builder | placement | 是 | `UNKNOWN`：不能判断内容是否能写入 | 受控修改 |
| `data.protected_zones[]` | 学生内容不能覆盖的固定区域 | array | 否 | artifact builder | placement、render | 是 | 缺失可能导致覆盖固定内容；检查到覆盖为 `FAIL` | 受控修改 |
| `data.required_fields[]` | 模板需要的生成字段或填写字段 | array | 否 | artifact builder | generator、gap | 是 | 标准要求但缺失时 `UNKNOWN` 或 `FAIL` | 受控修改 |
| `data.unsupported[]` | 源模板中未支持对象 | array | 是 | artifact builder | coverage、report | 是 | 可见 unsupported 不能静默丢弃，必须阻断或待 review | 否 |

### `template_artifact` 边界

- 可以辅助解释 e2e 中为什么某个单元应该存在。
- 不能替代 `generated_template_tree` 证明生成 Word 里确实存在该单元。
- 不能把 `template_artifact.data.units` 里的期望直接当成 gap PASS。

## `template_unit_decisions`

这个产物说明每个模板单元打算怎么处理。它是生成计划的来源。

| 字段 | 含义 | 类型 | 是否必填 | 生产者 | 消费者 | 参与判定 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `input_hashes.template_artifact` | 决策基于哪个 artifact | string | 是 | decision builder | plan builder、audit | 是 | `UNKNOWN`：不能证明决策来源 | 否 |
| `units[].unit_id` | 被处理单元 | string | 是 | decision builder | plan builder | 是 | `UNKNOWN`：动作不能稳定归属 | 否 |
| `units[].source_policy` | 源单元处理策略 | string enum | 是 | decision builder | plan builder | 是 | `UNKNOWN`：不能决定复制、保护或填充 | 受控修改 |
| `units[].decisions[]` | 单元内处理决定 | array | 是 | decision builder | plan builder | 间接 | 缺失会让生成过程不可解释；可能导致 manifest review | 受控修改 |
| `decisions[].decision_id` | 决策稳定 ID | string | 是 | decision builder | plan builder、audit | 间接 | `UNKNOWN`：不能追踪计划动作来源 | 否 |
| `decisions[].decision_type` | 处理类型 | enum | 是 | decision builder | plan builder | 是 | `UNKNOWN`：不能生成动作 | 受控修改 |
| `decisions[].source_ref` | 源 Word 节点 | string/null | 视类型而定 | decision builder | plan builder、executor | 是 | 需要源节点但缺失时 `needs_review` | 否 |
| `unresolved_questions[]` | 不能自动决定的问题 | array | 是 | decision builder | report、人工 review | 是 | 有阻断问题时不能假装完成 | 可补说明，不能删除事实 |

推荐 `decision_type`：

```text
copy_fixed_block
remove_instruction_text
create_fillable_slot
create_generated_field_placeholder
create_manual_placeholder
insert_fixed_text
protect_block
```

## `template_generation_plan`

这个产物是生成器要执行的动作清单。

| 字段 | 含义 | 类型 | 是否必填 | 生产者 | 消费者 | 参与判定 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `strategy` | 本次生成策略，例如 `source_copy_scaffold` | string enum | 是 | plan builder | executor、manifest、report | 是 | `UNKNOWN`：不能解释生成方式 | 受控修改 |
| `source_template_docx` | 源 Word 路径 | string path | 是 | plan builder | executor | 是 | `UNKNOWN`：不能生成 | 否 |
| `input_hashes.source_template_docx` | 源 Word hash | string | 是 | plan builder | audit | 是 | `UNKNOWN`：不能证明输入一致 | 否 |
| `input_hashes.template_artifact` | artifact hash | string | 是 | plan builder | audit | 是 | `UNKNOWN`：不能证明计划来源 | 否 |
| `actions[]` | 可执行动作 | array | 是 | plan builder | executor | 是 | 无动作时 `UNKNOWN` 或 `FAIL`，取决于目标 | 受控修改 |
| `actions[].action_id` | 动作稳定 ID | string | 是 | plan builder | executor、manifest | 是 | `UNKNOWN`：不能审计动作 | 否 |
| `actions[].action_type` | 动作类型 | enum | 是 | plan builder | executor | 是 | 不支持动作进入 `needs_review` | 受控修改 |
| `actions[].unit_id` | 动作所属单元 | string/null | 视动作而定 | plan builder | manifest、report | 是 | 涉及单元动作缺失时 `UNKNOWN` | 否 |
| `actions[].element_id` | 动作所属元素 | string/null | 视动作而定 | plan builder | manifest、slot/field | 是 | 涉及元素动作缺失时 `UNKNOWN` | 否 |
| `actions[].source_ref` | 动作读取或修改的源节点 | string/null | 视动作而定 | plan builder | executor | 是 | 需要源节点但找不到时 `needs_review` | 否 |
| `actions[].target_ref` | 目标内容、目标路径或标记 | string/null | 视动作而定 | plan builder | executor | 是 | 需要目标但缺失时 `needs_review` | 受控修改 |
| `actions[].status` | 计划阶段状态，通常是 `planned` | enum | 是 | plan builder | executor、manifest | 间接 | 非 planned 状态必须解释 | 否 |
| `actions[].reason` | 为什么要做这个动作 | string | 应该有 | plan builder | report、debug | 间接 | 缺失不直接阻断，但不利于排查 | 可补说明 |

## `generated_template.docx`

这是模板生成阶段的核心 Word 产物。它不是 JSON，没有内部字段表，但必须被其他产物用字段固定身份。

| 字段位置 | 含义 | 是否必填 | 生产者 | 消费者 | 参与判定 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `template_generation_manifest.output.generated_template_docx` | 生成 Word 路径 | 是 | generator executor | e2e、template-gap | 是 | `UNKNOWN`：找不到被测生成模板 | 否 |
| `template_generation_manifest.output.generated_template_docx_hash` | 生成 Word hash | 是 | generator executor | audit、coverage | 是 | `UNKNOWN`：不能证明被测文件固定 | 否 |
| `template_gap_report.generated_template.path` | gap 实际检查的 Word 副本路径 | 是 | template-gap runner | coverage、report | 是 | `UNKNOWN`：检查对象不清楚 | 否 |
| `template_gap_report.generated_template.sha256` | gap 检查对象 hash | 是 | template-gap runner | coverage、audit | 是 | `UNKNOWN`：不能证明检查的是哪份 Word | 否 |

`generated_template.docx` 必须满足：

- 能被 DOCX 解析器打开；
- 不包含学生论文正文；
- 包含后续可定位的 slot 或生成机制；
- 后续流程使用它作为底稿，而不是继续使用学校原始模板；
- 质量是否合格由 `template-gap` 和后续 gate 判断。

## `template_generation_manifest`

这个产物记录生成器实际做了什么。它可以解释过程，但不能替代生成 Word 的实际解析结果。

| 字段 | 含义 | 类型 | 是否必填 | 生产者 | 消费者 | 参与判定 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `strategy` | 本次生成策略 | string enum | 是 | generator executor | report、e2e | 是 | `UNKNOWN`：不能解释生成行为 | 否 |
| `input_hashes.source_template_docx` | 源 Word hash | string | 是 | generator executor | audit | 是 | `UNKNOWN`：不能证明输入一致 | 否 |
| `input_hashes.template_artifact` | artifact hash | string | 是 | generator executor | audit | 是 | `UNKNOWN`：不能证明基于哪个理解结果 | 否 |
| `input_hashes.template_generation_plan` | plan hash | string | 是 | generator executor | audit | 是 | `UNKNOWN`：不能证明执行哪个计划 | 否 |
| `output.generated_template_docx` | 输出 Word 路径 | string path | 是 | generator executor | template-gap、e2e | 是 | `UNKNOWN`：没有可检查生成模板 | 否 |
| `output.generated_template_docx_hash` | 输出 Word hash | string | 是 | generator executor | template-gap、audit | 是 | `UNKNOWN`：输出不可固定 | 否 |
| `slots[]` | 已写入或确认的可写位置 | array | 是 | generator executor | placement、render、report | 是 | 必需 slot 缺失为 `FAIL` 或 `UNKNOWN` | 否 |
| `slots[].slot_id` | slot 稳定 ID | string | 是 | generator executor | placement、render | 是 | `FAIL`：后续无法写入目标位置 | 否 |
| `slots[].marker` | Word 中的 slot 标记 | string | 是 | generator executor | render、gap | 是 | `UNKNOWN`：不能在 Word 中定位 slot | 否 |
| `slots[].output_ref` | slot 写入到生成 Word 的位置 | string | 是 | generator executor | debug、gap | 是 | `UNKNOWN`：不能证明 slot 在输出里的位置 | 否 |
| `generated_fields[]` | 目录、页码、题注等生成字段占位 | array | 否 | generator executor | gap、后续生成机制 | 是，涉及字段时 | 标准要求但缺失时 `FAIL` 或 `UNKNOWN` | 否 |
| `page_breaks[]` | 生成器写入的分页边界 | array | 否 | generator executor | gap 解释 | 间接 | 不能单独证明 Word 分页合格；缺真实证据时 `UNKNOWN` | 否 |
| `section_breaks[]` | 生成器写入的分节边界 | array | 否 | generator executor | gap 解释 | 间接 | 不能单独证明 Word section 合格；缺真实证据时 `UNKNOWN` | 否 |
| `synthesized_texts[]` | 生成器合成的可见文本 | array | 否 | generator executor | gap、人工排查 | 是，涉及可见标题时 | 缺来源说明时应 `UNKNOWN` 或 review | 否 |
| `actions_executed[]` | 已执行动作 | array | 是 | generator executor | audit、debug | 间接 | 缺失会让生成过程不可审计 | 否 |
| `actions_requiring_review[]` | 未能安全自动执行的动作 | array | 是 | generator executor | report、gate | 是 | 非空时不能假装完整通过；按影响进入 `UNKNOWN` | 否 |

### `manifest` 边界

- `actions_executed[].status = executed` 只说明生成器执行过动作。
- 真实 Word 是否有该内容，必须看 `generated_template_tree`。
- 如果 `actions_requiring_review[]` 非空，报告必须让人看到，不允许吞掉。

## `generated_template_tree`

这个产物是从被测 `generated_template.docx` 解析出的实际结构。`template-gap` 判定 Word 事实时优先消费它。

| 字段 | 含义 | 类型 | 是否必填 | 生产者 | 消费者 | 参与判定 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `input_docx` | 被解析 Word 路径 | string path | 是 | generated-template inspector | gap、report | 是 | `UNKNOWN`：被测对象不清 | 否 |
| `input_exists` | 被测 Word 是否存在 | boolean | 是 | inspector | gap input check | 是 | `UNKNOWN`：缺少被测 Word | 否 |
| `input_valid_docx` | 被测 Word 是否有效 DOCX | boolean | 是 | inspector | gap input check | 是 | `FAIL`：确认不是有效 DOCX | 否 |
| `input_hashes.generated_template_docx` | 被测 Word hash | string | 是，有效时 | inspector | gap、audit | 是 | `UNKNOWN`：不能固定被测文件 | 否 |
| `source_kind` | 输入身份，当前应为 `generated_template_docx` | string enum | 是 | inspector | gap、report | 是 | `UNKNOWN`：不能确认正在检查生成模板 | 否 |
| `data.paragraphs[]` | 正文段落 | array | 是 | inspector | unit locator、element/style checks | 是 | 缺失且 Word 有正文时 `UNKNOWN` | 否 |
| `data.paragraphs[].index` | python-docx 段落序号 | number | 是 | inspector | locator、debug | 是 | `UNKNOWN`：段落顺序不可证明 | 否 |
| `data.paragraphs[].xml_index` | OOXML 段落序号 | number | 应该有 | inspector | locator、section/field 绑定 | 是 | 坐标不足时相关检查 `UNKNOWN` | 否 |
| `data.paragraphs[].text` | 段落可见文字 | string | 否 | inspector | element check | 是，涉及文本时 | 无文字不等于失败；看节点类型 | 否 |
| `data.paragraphs[].style_details` | 解析后的样式细节 | object | 否 | inspector | style check | 是，涉及样式时 | 样式证据不足时 `UNKNOWN` | 否 |
| `data.paragraphs[].runs[]` | run 级文字和格式 | array | 否 | inspector | 细样式检查 | 是，涉及 run 时 | 证据不足时 `UNKNOWN` | 否 |
| `data.paragraphs[].source_ref` | 段落 OOXML 来源 | string | 是 | inspector | evidence、locator | 是 | `UNKNOWN`：不能引用证据位置 | 否 |
| `data.tables[]` | 表格结构 | array | 否 | inspector | unit locator、table/style checks | 是，涉及表格时 | 需要表格证据但缺失时 `UNKNOWN` | 否 |
| `data.tables[].cells[]` | 表格单元格 | array | 否 | inspector | table/unit/element checks | 是 | 缺表格坐标时表格相关检查 `UNKNOWN` | 否 |
| `data.headers_footers[]` | 页眉页脚内容 | array | 否 | inspector | header/footer checks | 是，涉及页眉页脚时 | 标准要求但缺证据时 `UNKNOWN` | 否 |
| `data.fields[]` | Word 字段，例如 TOC/PAGE/SEQ | array | 否 | inspector | field checks | 是，涉及字段时 | 标准要求但缺字段时 `FAIL` 或 `UNKNOWN` | 否 |
| `data.breaks[]` | 分页/换行等边界 | array | 否 | inspector | page checks | 是，涉及分页时 | 缺边界证据时 `UNKNOWN` | 否 |
| `data.sections[]` | section 和页面设置 | array | 否 | inspector | page/header/footer checks | 是，涉及页面规则时 | 缺 section 证据时 `UNKNOWN` | 否 |
| `data.numbering_refs[]` | 段落编号引用 | array | 否 | inspector | numbering checks | 是，涉及编号时 | 缺引用时可能 `FAIL` 或 `UNKNOWN` | 否 |
| `data.numbering_definitions[]` | 编号定义 | array | 否 | inspector | numbering checks | 是，涉及编号时 | 缺定义时可能 `FAIL` 或 `UNKNOWN` | 否 |
| `data.footnotes[]` | 脚注内容 | array | 否 | inspector | unknown-object checks、field checks | 是，涉及脚注时 | 不支持时不能静默丢弃 | 否 |
| `data.text_boxes[]` | 文本框内容 | array | 否 | inspector | unknown-object checks、layout checks | 是，涉及文本框时 | 不支持时不能静默丢弃 | 否 |
| `data.images[]` | 图片引用 | array | 否 | inspector | unknown-object checks、layout checks | 是，涉及图片时 | 不支持时不能静默丢弃 | 否 |
| `data.unknown_visible_objects[]` | 仍无法解释的可见对象 | array | 是 | inspector | gap、coverage | 是 | 必须 `UNKNOWN` 或 `FAIL`，不能 PASS | 否 |

### `generated_template_tree` 边界

- 它是 `template-gap` 的事实输入。
- 它不能替代 `template_unit_contract.yaml` 或已签收标准。
- 页眉页脚不能污染正文单元定位，但必须作为独立检查对象保留。

## `template_gap_report`

这个产物说明生成模板差距检查的结果。它是 gate 读取的阻断状态来源。

| 字段 | 含义 | 类型 | 是否必填 | 生产者 | 消费者 | 参与判定 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `school_id` | 学校 ID | string | 是 | gap runner | coverage、report | 是 | `UNKNOWN`：不能绑定学校标准 | 否 |
| `template_version` | 模板标准版本 | string | 是 | gap runner | coverage、audit | 是 | `UNKNOWN`：不能绑定标准版本 | 否 |
| `generated_template.path` | 被测生成 Word 副本 | string path | 是 | gap runner | report、coverage | 是 | `UNKNOWN`：检查对象不清 | 否 |
| `generated_template.source_path` | CLI 或 e2e 传入的原始被测路径 | string path | 是 | gap runner | audit、debug | 是 | `UNKNOWN`：输入来源不清 | 否 |
| `generated_template.sha256` | 被测 Word hash | string | 是，有效时 | gap runner | coverage、audit | 是 | `UNKNOWN`：不能固定检查对象 | 否 |
| `generated_template.input_role` | 输入角色，必须是 `generated_template` | string enum | 是 | gap runner | report、tests | 是 | `UNKNOWN`：可能测错对象 | 否 |
| `standard.path` | 使用的结构化标准路径 | string path | 是 | gap runner | audit、report | 是 | `UNKNOWN`：缺标准 | 否 |
| `standard.sha256` | 标准文件 hash | string | 是，标准存在时 | gap runner | audit、anti-drift | 是 | `UNKNOWN`：标准不可固定 | 否 |
| `generated_template_tree` | 生成 Word 解析结果文件名 | string | 是 | gap runner | report、debug | 是 | `UNKNOWN`：缺事实输入 | 否 |
| `input` | 被测 Word 输入检查项 | check object | 是 | gap checker | summary、findings | 是 | 缺失则整体 `UNKNOWN` | 否 |
| `units[]` | 按单元组织的检查结果 | array | 是 | gap checker | summary、PM report | 是 | 缺 required 单元结果则 `UNKNOWN` | 否 |
| `units[].located` | 单元定位证据 | object | 是 | gap checker | element/style/page checks | 是 | 未定位时下级检查不得硬 PASS；通常 `UNKNOWN` | 否 |
| `units[].presence` | 单元存在性检查 | check object | 是，required 单元 | gap checker | summary、findings | 是 | 缺失则该单元 `UNKNOWN` | 否 |
| `units[].elements[]` | 元素检查结果 | array | 是 | gap checker | summary、findings | 是 | 缺 required 元素结果则 `UNKNOWN` | 否 |
| `units[].dimensions.page[]` | 页面规则检查 | array | 否 | gap checker | summary、findings | 是，涉及页面规则时 | 缺证据时 `UNKNOWN` | 否 |
| `units[].dimensions.header_footer[]` | 页眉页脚检查 | array | 否 | gap checker | summary、findings | 是，涉及页眉页脚时 | 缺证据时 `UNKNOWN` | 否 |
| `units[].dimensions.fields[]` | Word 字段检查 | array | 否 | gap checker | summary、findings | 是，涉及字段时 | 缺字段时按规则 `FAIL` 或 `UNKNOWN` | 否 |
| `units[].dimensions.numbering[]` | 自动编号检查 | array | 否 | gap checker | summary、findings | 是，涉及编号时 | 缺编号证据时 `FAIL` 或 `UNKNOWN` | 否 |
| `units[].counts` | 单元内 PASS/FAIL/UNKNOWN 计数 | object | 是 | gap summarizer | summary、report | 是 | 缺失则 summary 不可信，整体 `UNKNOWN` | 否 |
| `units[].verdict` | 单元最终判定 | enum | 是 | gap summarizer | summary、gate | 是 | 缺失则单元 `UNKNOWN` | 否 |
| `global_checks[]` | 全局检查，例如标准缺失、单元顺序 | array | 是 | gap checker | summary、findings | 是 | 缺失可能漏报，整体不应 PASS | 否 |
| `unmodeled_objects[]` | 未建模可见对象检查 | array | 是 | gap checker | summary、findings | 是 | 有可见未建模对象不能 PASS | 否 |
| `summary.known_status` | 已知检查项的状态 | enum | 是 | summarizer | coverage、report | 是 | 缺失则整体 `UNKNOWN` | 否 |
| `summary.display_status` | 人读状态，例如 `FAIL + UNKNOWN` | string | 是 | summarizer | PM report | 是 | 缺失不影响机器状态，但报告不完整 | 否 |
| `summary.blocking_status` | gate 阻断状态 | enum | 是 | summarizer | coverage、e2e | 是 | 缺失则整体 `UNKNOWN` | 否 |
| `summary.per_unit[]` | 每个单元摘要 | array | 是 | summarizer | PM report、debug | 是 | 缺失会降低定位能力，不应隐藏阻断 | 否 |
| `coverage.*` | 本次 gap 覆盖到哪些能力 | object bool | 是 | coverage builder | coverage gate | 是 | 覆盖不足为 `UNKNOWN` | 否 |

### 检查项字段

`input`、`presence`、`style`、`dimensions.*[]`、`global_checks[]`、`unmodeled_objects[]`
里的单个检查项使用同一组字段。

| 字段 | 含义 | 类型 | 是否必填 | 缺失时怎么办 | AI 是否可改 |
| --- | --- | --- | --- | --- | --- |
| `check_id` | 检查项稳定 ID | string | 是 | `UNKNOWN`：不能定位检查来源 | 否 |
| `category` | 检查类别 | string enum | 是 | `UNKNOWN`：不能归类问题 | 否 |
| `status` | `PASS`、`FAIL`、`UNKNOWN` | enum | 是 | 缺失即 `UNKNOWN` | 否 |
| `type` | 机器可聚合的问题类型 | string | 是 | `UNKNOWN`：finding 无法聚合 | 否 |
| `message` | 人读问题说明 | string | 是 | 报告不可用；不能用空说明冒充通过 | 可补说明，不能改状态 |
| `expected` | 期望证据 | string | 是 | `UNKNOWN`：不能说明检查标准 | 否，除非标准变更已签收 |
| `actual` | 实际证据 | string | 是 | `UNKNOWN`：不能说明实际观察 | 否，除非来自重新运行检查器 |
| `path` | 报告内稳定路径 | array | 是 | `UNKNOWN`：不能定位到单元/元素/维度 | 否 |
| `evidence_refs[]` | 文件或 OOXML 证据引用 | array | 应该有 | 证据不足时不得 PASS | 否 |
| `affected_ids[]` | 受影响单元或元素 | array | 应该有 | 聚合能力下降；必要时 `UNKNOWN` | 否 |
| `next_step` | 下一步该修什么 | string | 是 | 不影响状态，但报告不可执行 | 可补说明 |
| `root_cause_bucket` | 问题归类桶 | string | 应该有 | 聚合能力下降 | 可补说明 |

检查项判定规则：

- 证据充分且符合标准，才能 `PASS`。
- 标准明确、证据明确相反，才是 `FAIL`。
- 标准缺失、证据不足、单元定位不可靠、解析能力不足，都必须是 `UNKNOWN`。

AI 可以帮助改 `message` 或 `next_step` 的措辞，但不能直接改 `status`、`expected`、`actual`、`path` 或 `evidence_refs` 来让报告通过。

## 检查器消费字段

### template-gap 单元定位

消费：

- `template_unit_contract.yaml expected.units[].unit_id`
- `template_unit_contract.yaml expected.units[].elements[]`
- `generated_template_tree.data.paragraphs[]`
- `generated_template_tree.data.tables[]`
- `generated_template_tree.data.headers_footers[]`
- `generated_template_tree.data.fields[]`
- `generated_template_tree.data.sections[]`
- `generated_template_tree.data.unknown_visible_objects[]`

不消费：

- `template_generation_manifest.actions_executed[]` 作为存在性证明；
- AI 报告解释；
- 人工备注；
- `template_artifact.data.units[]` 作为独立 `template-gap` 的替代事实。

### placement / render 后续写入

消费：

- `template_artifact.data.slots[].slot_id`
- `template_artifact.data.slots[].unit_id`
- `template_artifact.data.slots[].accepted_content_kinds`
- `template_generation_manifest.output.generated_template_docx`
- `template_generation_manifest.slots[].marker`
- `template_generation_manifest.slots[].output_ref`

不消费：

- `template_gap_report.summary.display_status` 作为写入位置；
- `generated_template_tree` 里的任意全文搜索结果作为稳定 slot ID。

### coverage / e2e gate

消费：

- `template_gap_report.summary.blocking_status`
- `template_gap_report.coverage.*`
- `template_gap_report.generated_template.sha256`
- `generated_template_tree.input_valid_docx`
- `template_generation_manifest.output.generated_template_docx_hash`

不消费：

- AI 诊断结论作为 PASS；
- 当前坏输出更新后的 expected snapshot；
- 未签收的 `discovered_template_rules` 作为正式通过标准。

## 新字段检查清单

任何代码改动想新增字段时，先回答：

1. 这个字段在哪个产物里？
2. 它表达的业务概念有没有已有字段可以表达？
3. 它的唯一生产者是谁？
4. 至少一个消费者是谁？
5. 消费者缺它时判 `FAIL`、`UNKNOWN`、`needs_review`，还是不阻断？
6. 它是否需要 `source_ref`、`output_ref`、hash 或审计记录？
7. 它是否允许默认值？
8. 它是否会影响 signed standard、golden、expected snapshot？
9. 它是否需要迁移旧产物？
10. 它是否需要契约测试或 e2e gate 测试？

如果这些问题没有答案，先不要加字段。
