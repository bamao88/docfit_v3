# 模板差距检查阶段一：整理学校标准

Status: Draft
Created: 2026-06-20
Owner: Product + Engineering

## 这个计划解决什么

本计划用于执行 `docs/human/template-gap-process-mainline.md` 里的“阶段一：整理学校标准”。

阶段一不生成新的 Word 模板，也不试图让三校 `template-gap` 立刻变成 `PASS`。它只把三所真实学校的结构化标准整理干净，让后续检查器能分清：

- 哪些是单元里应该真实可见、可填写或可生成的内容；
- 哪些是页面、页眉、页码、section、页边距这类全局或单元维度规则；
- 哪些只是审查备注、证据冲突或需要人工确认的点；
- 哪些元素可以用于定位单元，哪些只能在单元内部验证，哪些不能参与定位。

整理完成后，`template-gap` 的报告仍然可以是 `FAIL` 或 `UNKNOWN`，但这些结论应该更像真实模板差距或真实证据不足，而不是因为标准项归属错误造成的误报。

## 输入

阶段一的输入分为三类。

### 1. 流程和产品语义输入

- `README.md`：仓库当前方向和基础命令。
- `SPEC.md`：三态门禁、阶段边界和标准防漂移规则。
- `docs/human/format-conversion-predevelopment-alignment.md`：整个格式转换项目的开发前对齐清单，用于确认输入身份、阶段边界、字段契约、判定口径和文件修改边界。
- `docs/current/project-directory-structure.md`：当前目录结构约定，用于确认 `test_inputs/`、`test_outputs/` 和旧 `inputs/`、`reports/`、`out/`、`tests/template/` 的边界。
- `docs/human/template-gap-process-mainline.md`：本方向最高优先级主线文档，阶段一的直接依据。
- `docs/human/template-generation-business-flow-current-state.md`：模板生成业务主线文档，定义学校原始模板 Word 如何进入 `source_template_tree`、`discovered_template_rules`、`template_artifact`、`template_generation_plan`、`generated_template.docx` 和 `template_generation_manifest`。

### 2. 学校来源事实输入

- `docs/human/real-core-v0-review-packet.md`
- `inputs/targets/hunannongye/raw/source_review.md`
- `inputs/targets/nannong-undergraduate/raw/source_review.md`
- `inputs/targets/pku-graduate/raw/source_review.md`

这些文件说明学校模板里实际有哪些单元、元素、页面规则、页眉页码规则和人工确认点。执行阶段一时，不能脱离这些来源事实凭空改标准。

### 目录重构并行约束

当前代码、标准路径、测试路径和 CLI 默认输出已经迁到目标目录结构：仓库内评测输入读 `test_inputs/`，运行证据写 `test_outputs/`。旧 `inputs/`、`reports/`、`out/` 和 `tests/template/` 不再是当前默认入口。阶段一执行时要遵守以下边界：

- 本阶段不负责移动、重命名或删除输入资产、报告目录和调试输出目录。
- 当前计划里的学校源模板、人工审查文本和 template-gap fixture 按 `test_inputs/` 身份读取；执行前先用 `rg "inputs/|test_inputs/|reports/|out/|test_outputs/|tests/template" standards src tests docs README.md SPEC.md` 重新确认没有把旧目录当成默认入口。
- 不能把路径迁移当成学校标准语义变更；不能为了修路径而修改 `signed_standard.yaml` 的签收含义。
- 如果 `src/docfit/harness/` 在目录重构中被改名为 `src/docfit/eval_harness/`，阶段一应修改当前真实模块，不要重新创建旧目录。
- 验证输出默认写入 `runs/eval/`；如果为了隔离本地调试临时写 `/tmp`，执行总结必须说明这是临时证明，不是目标目录结构。

### 3. 当前待整理的机器标准输入

- `standards/targets/hunannongye/v1/template_unit_contract.yaml`
- `standards/targets/nannong-undergraduate/v1/template_unit_contract.yaml`
- `standards/targets/pku-graduate/v1/template_unit_contract.yaml`

这三个文件是阶段一的主要修改对象。

验证时还会读取：

- `eval_profiles/real-core-v0/profile.yaml`
- `inputs/targets/hunannongye/fixtures/template_gap/generated_template.input.docx`
- `inputs/targets/nannong-undergraduate/fixtures/template_gap/generated_template.input.docx`
- `inputs/targets/pku-graduate/fixtures/template_gap/generated_template.input.docx`

## 先确定字段：和模板生成业务链路对齐

阶段一开始时要先确定“字段契约”。这里的字段不是 Word field code，而是三类数据之间的对应关系：

- 模板生成业务产物字段：`source_template_tree`、`discovered_template_rules`、`template_artifact`、`template_unit_decisions`、`template_generation_plan`、`template_generation_manifest`。
- 开发期参照标准字段：三校 `template_unit_contract.yaml` 里的 `expected.units`、`page`、`header_footer`、`elements`、`expected.global_rules`、`expected.source_conflicts`、`expected.open_questions`。
- 检查报告字段：`generated_template_tree.json` 和 `template_gap_report.json` 里用于说明生成模板哪里缺、哪里证据不足的字段。

`template_unit_contract.yaml` 在模板生成主线里是“开发期人工整理样本”，不是生产环境要求用户上传的输入。当前 `docfit eval template-generate` 只接收 `--template` 和 `--out`，不接收 `--school`，也不把学校签收标准作为生成输入。阶段一清理它，是为了让开发期人工参照、后续自动识别 `discovered_template_rules`、以及 `template-gap` 的正式检查使用同一套业务含义。

阶段一清理三校标准时，必须把“仅复制单元”定义为内容责任，而不是固定排除列表。普通目录、图目录、表目录、中文摘要、英文摘要、正文、参考文献，以及学生源文档中实际有内容或学校标准要求承载学生内容的致谢、附录，都不能默认仅复制。签名、日期、教师意见、成绩评定、声明固定正文等只需要学生或老师线下填写/确认的区域，可以作为仅复制单元保留。

阶段一必须先产出或在执行总结中补齐下面这张字段对齐表。没有完成对齐前，不应大规模删除或重排 `elements`。

| 业务概念 | 开发期标准字段 | 生成业务字段 | gap 检查字段 | 阶段一处理原则 |
| --- | --- | --- | --- | --- |
| 模板单元 | `expected.units[].unit_id/name` | `template_artifact.data.units[]`、`template_unit_decisions[].unit_id`、`template_generation_plan.actions[].unit_id`、`template_generation_manifest.slots[].unit_id` | `template_gap_report.units[]` | 保持 `unit_id` 稳定；只修正单元内字段归属和定位锚点 |
| 目录族 | `toc` 单元内的普通目录、图目录、表目录元素；后续如拆 unit，可用 `figure_toc`、`table_toc` 等稳定 ID | `generated` 元素、字段占位、生成动作记录 | TOC / 图目录 / 表目录字段要求检查 | 必须标注为系统生成或更新相关内容，不能归入仅复制单元 |
| 学生内容单元 | `abstract_cn`、`abstract_en`、`body_main`、`references`，以及有学生源内容或标准要求承载学生内容的 `acknowledgement`、`appendix` 等 | `template_artifact.data.slots`、`create_fillable_slot`、placement target slot | 槽位、标记、元素存在性、内容去向检查 | 需要填写/放置学生内容；不能因为模板里有占位符或默认正文就整体 copy-only |
| 人工填写/确认单元 | 签名、日期、教师意见、成绩评定、答辩记录等 `manual_only` 元素或固定表单单元 | `manual_only`、`protected_zones`、`preserve_whole_unit_copy` | 单元存在性、固定文本、保护区检查 | 可以仅复制；不为姓名日期签名线自动生成 slot，不删除内部说明文字 |
| 学校固定正文单元 | 固定声明、授权说明、学校要求保留的固定表单正文 | `fixed`、`protected_zones`、`preserve_whole_unit_copy` | 单元存在性、固定文本检查 | 可以仅复制；只保留必要定位锚点和固定文本，不把版式说明伪装成学生内容 |
| 单元标题、固定声明、固定表单标签 | `expected.units[].elements[]`，`policy: fixed/manual_only`，`anchor_role: primary/secondary` | `template_artifact.data.units[].elements[]`，`copy_fixed_block`、`protect_block` | 元素存在性、文本、样式、保护区检查 | 保留在 `elements`；稳定标题优先标 `primary` |
| 学生后续要填写的位置 | `elements[]`，`policy: fill` | `template_artifact.data.slots`、`create_fillable_slot`、`manifest.slots[]` | 槽位、标记、元素存在性检查 | 保留在 `elements`；通常不作为单元起点定位 |
| 系统后续生成的字段或目录 | `elements[]`，`policy: generated` | `create_generated_field_placeholder`、字段引用、生成动作记录 | TOC、PAGE、SEQ 等字段要求检查 | 若当前检查器需要它判断字段，继续保留在 `elements` |
| 学校模板里的说明文字 | 不应作为目标 `elements`；必要时进 `source_conflicts/open_questions` | `instruction_paragraphs`、`cleanup_policy`、`remove_instruction_text` | 不应被当成目标可见内容缺失 | 从目标元素里移出，或标 `anchor_role: none` 后再归位 |
| 纸张、页边距、装订线 | `expected.global_rules.page_setup` | `source_template_tree.layers.package_global/section_rules`、`template_artifact.data.page_setup` | 当前第一阶段通常不直接判 PASS/FAIL | 作为跨单元规则归位，不再放普通元素 |
| 单元另起页、分节隔离、同页要求 | `expected.units[].page` | `template_unit_decisions`、`template_generation_plan.actions[]`、`manifest` 里的分页/分节记录 | `_page_rule_checks()` | 放在单元 `page`，不要伪装成元素文本 |
| 页眉、页脚、页码规则 | `expected.units[].header_footer`；共享规则进 `expected.global_rules.header_footer/page_numbering` | `source_template_tree.layers.header_footer`、生成执行记录 | `_header_footer_checks()` | 单元特有规则放 `header_footer`；跨单元规则放 `global_rules` |
| 证据冲突、待人工确认 | `expected.source_conflicts/open_questions` | `template_unit_decisions.unresolved_questions`、`actions_requiring_review[]` | 只能解释 `UNKNOWN` 或后续人工动作 | 不制造 `PASS`；不能藏在普通元素里 |

因此，`expected.global_rules` 不是“全局样式”的同义词。它是跨单元共享规则的入口，可能包含页面设置、页眉页脚距离、页码体系、section 创建原则，也可以在后续扩展到共享样式规则。第一阶段只要求把这些规则归位，并标明当前是否已有检查器消费。

## 最终输出标准

阶段一完成后，三校 `template_unit_contract.yaml` 必须满足以下标准。

### 0. 字段含义已经和业务链路对齐

阶段一必须明确每类标准字段对应哪个模板生成业务字段、哪个 gap 检查字段，以及当前是否参与 `PASS/FAIL/UNKNOWN` 判定。

如果某个字段当前只是标准事实，还没有下游消费者，要在执行总结中写清楚“已归位，第一阶段暂不判定”。不能因为检查器暂时不消费，就把它塞回 `elements` 里制造可见文本检查。

### 1. `elements` 只放真实可检查的单元内容

`expected.units[].elements` 只能放 Word 里应该真实可见、可填写或由系统生成的内容，例如：

- 单元标题，如 `致  谢`、`参考文献`、`版权声明`；
- 固定声明正文；
- 固定表单标签、签名日期空位、勾选项；
- 目录、图目录、表目录、页码等 Word 字段或生成结果；
- 学生填充槽位，如中文摘要正文、英文题名、参考文献条目。

这里还要先按内容责任收敛：目录族、摘要、正文、参考文献、学生致谢、学生附录继续允许逐元素表达 `fill`、`generated`、`remove_instruction` 或固定内容；签名、日期、教师意见、成绩评定、固定声明正文等人工/固定区域可以仅复制，阶段一不能把这些区域里的填写线、签名日期、说明文字拆成机器必须处理的元素。当前不确定某个单元是否承载学生内容时，应写入 `open_questions` 或标成条件规则，不能靠元素启发式默认打开或默认关闭。

以下内容不得继续作为普通 `elements`：

- 纸张、页边距、装订线；
- 页眉/页脚距离；
- 页码格式、页码起始、页码连续性；
- Word section 创建原则；
- “源模板说明”“审查口径”“当前 school.yaml”这类备注；
- 证据冲突说明；
- “孤行控制”“与下段同页”“段中不分页”等纯 Word 段落选项，除非它们作为某个具体元素的 `style` 或后续维度规则被检查。

### 2. 单元维度规则放回单元字段

每个单元自己的页面和页眉页码规则放在已有字段中：

```yaml
page:
  page_break: 是
  section_isolation: ''
  keep_together: ''
header_footer:
  header: 无
  page_number: 前置页页码规则，见 3.2
```

字段含义：

- `page.page_break`：这个单元是否要求另起页，或是否是文档首页。
- `page.section_isolation`：这个单元是否要求被 section 或等价确定性边界隔离。
- `page.keep_together`：这个单元或固定表单块是否要求同页、表格不拆行、签名区不单独掉页。
- `header_footer.header`：这个单元所在页面应显示什么页眉；无页眉也是规则。
- `header_footer.page_number`：这个单元使用哪一类页码规则；无页码也是规则。

### 3. 跨单元共享规则放到 `expected.global_rules`

新增或整理 `expected.global_rules`，用来承载跨单元共享规则，例如：

```yaml
expected:
  global_rules:
    page_setup:
      paper: A4
      margins: 上=25.4mm；下=25.4mm；左=26mm；右=26mm
      gutter: 0mm
    header_footer:
      header_distance: 15mm
      footer_distance: 17.5mm
    page_numbering:
      front_matter: 前置页页码规则
      body_and_back_matter: 正文及后置页阿拉伯数字页码规则
    section_rules:
      - 只有页眉、页脚、页码格式、页边距或横竖版变化时才创建或切换 section。
      - 单元不是 Word section 的同义词。
```

第一阶段只要求把规则归位，不要求检查器立刻完整验证所有 `global_rules`。

### 4. 冲突和待确认项单独记录

如果来源事实之间冲突，或者学校规则需要人工确认，不允许硬改成单一答案。应写入：

```yaml
expected:
  source_conflicts:
    - conflict_id: page_margin_visible_vs_ooxml
      summary: 可见说明和 OOXML section defaults 不一致。
      decision: 可见说明优先；OOXML 值作为实现证据记录。
  open_questions:
    - question_id: hunannongye_page_number_start
      summary: 目录页码和正文页码是否都从 1 开始需要人工确认。
```

这些内容不能作为普通元素，也不能用于制造 `PASS`。

### 5. 元素可标注定位角色

元素可新增 `anchor_role`：

```yaml
elements:
  - element_id: e_001
    name: 致  谢
    policy: fixed
    content: 致  谢
    anchor_role: primary
  - element_id: e_002
    name: 致谢正文
    policy: fill
    content: 学生致谢正文
    anchor_role: secondary
```

取值含义：

- `primary`：可以用于定位单元起点，例如标题、固定表单标题、稳定的声明标题。
- `secondary`：只在单元内部验证，不单独用于定位单元起点。
- `none`：不能用于定位，例如页面规则、样式说明、审查备注。

执行阶段一时不要求给所有元素一次性补全 `anchor_role`，但必须优先处理容易误定位的单元，例如湖南农业 `acknowledgement`、后置固定表单、目录、摘要，以及北大的目录/图目录/表目录。

### 6. 检查器要尊重定位角色

`src/docfit/template_gap/gap.py` 中的单元定位逻辑必须满足：

- 优先使用 `anchor_role: primary` 的元素生成单元定位查询；
- 跳过 `anchor_role: none`；
- 如果一个单元没有任何 `anchor_role`，保持现有旧逻辑，并继续使用非可见规则识别兜底；
- 不能用页眉、页码、section、纸张、页边距、审查备注等文本定位正文单元。

### 7. 禁止通过漂移标准制造成功

阶段一不能修改：

- `signed_standard.yaml`
- golden 文件；
- expected snapshot；
- `generated_template.docx`；
- 学校原始模板 Word；
- 三态规则。

不能把 `FAIL` 或 `UNKNOWN` 改成成功来完成阶段一。

## 涉及文件

### 必须修改

- `standards/targets/hunannongye/v1/template_unit_contract.yaml`
- `standards/targets/nannong-undergraduate/v1/template_unit_contract.yaml`
- `standards/targets/pku-graduate/v1/template_unit_contract.yaml`
- `src/docfit/template_gap/gap.py`
- `tests/contract/test_real_core_generated_template_gap.py`

### 只读参考

- `README.md`
- `SPEC.md`
- `docs/human/format-conversion-predevelopment-alignment.md`
- `docs/current/project-directory-structure.md`
- `docs/human/template-gap-process-mainline.md`
- `docs/human/template-generation-business-flow-current-state.md`
- `docs/human/real-core-v0-review-packet.md`
- `inputs/targets/hunannongye/raw/source_review.md`
- `inputs/targets/nannong-undergraduate/raw/source_review.md`
- `inputs/targets/pku-graduate/raw/source_review.md`
- `eval_profiles/real-core-v0/profile.yaml`

### 不得修改

- `standards/targets/*/v1/target.standard.yaml`
- `eval_profiles/**/expected/**`
- `standards/schools/**/golden/**`
- `test_inputs/template_generation/school-*.docx`
- `test_inputs/template_gap/*generated-template.docx`
- 旧目录残留的 `inputs/**` 源文件、`reports/**` 运行输出、`out/**` 草稿或 `tests/template/**` 调试快照

## 中间实现流程

### Step 0：先确定字段契约，并和模板生成主线对齐

阶段一开始改 YAML 前，必须先用 `docs/human/template-generation-business-flow-current-state.md` 确认字段边界。确认顺序是：

1. 生产主线只要求用户输入学校原始模板 Word；`template_unit_contract.yaml` 是开发期参照样本。
2. 模板生成主线的核心业务产物是 `generated_template.docx` 和 `template_generation_manifest`。
3. `source_template_tree`、`discovered_template_rules`、`template_artifact`、`template_unit_decisions`、`template_generation_plan` 是阶段间业务对象，当前 CLI 落盘是为了调试和回归。
4. `template-gap` 的报告是检查产物，不是模板生成主线的必需输入。
5. 三校标准清理必须服务于当前开发期人工参照和 `template-gap` 检查，也要给后续自动识别 `discovered_template_rules` 留出一致字段形状；如果后续新增按 `school_id` 对齐模板生成的能力，必须单独定义 CLI 边界和验收规则。

本步骤的输出是一张字段对齐表，至少包含：

```text
业务概念 -> 开发期标准字段 -> 生成业务字段 -> gap 检查字段 -> 当前是否参与判定
```

只有字段含义清楚后，才进入 YAML 项目移动。

### Step 1：确认下游验证和生成逻辑如何消费这些字段

阶段一开始改 YAML 前，必须先确认当前下游代码如何消费 `template_unit_contract.yaml`。这是本阶段的第一步，不是可选项。

当前代码的消费方式如下：

| 下游位置 | 读取什么 | 对阶段一的影响 |
| --- | --- | --- |
| `src/docfit/template_gap/gap.py` | 只正式读取 `expected.units` 作为 gap 检查标准 | `expected.global_rules` 目前不会直接生成 PASS/FAIL/UNKNOWN，只能先作为归位后的标准事实 |
| `generated_template_gap._locate_units()` | 用 unit 名称和 `fixed/manual_only` 元素文本定位单元 | `elements` 里混入页码、页眉、section、页边距，会直接污染单元定位 |
| `generated_template_gap._compare_elements()` | 在单元范围内检查 `elements` 的存在、样式、字段标记 | 删除或改名元素会改变报告结构和元素级结论 |
| `generated_template_gap._header_footer_checks()` | 读取 `unit.header_footer.header/page_number` | 页眉页码规则应放这里，而不是普通元素里 |
| `generated_template_gap._page_rule_checks()` | 读取 `unit.page.page_break/section_isolation/keep_together` | 另起页、分页隔离、同页约束应放这里 |
| `generated_template_gap._field_requirements()` | 从 `elements` 或 unit 文本里推断 TOC、PAGE、SEQ 等字段要求 | 生成字段仍需要保留在 `elements` 或 unit 可读字段中，不能全部移到 `global_rules` |
| `generated_template_gap._numbering_requirements()` | 从 `elements` 文本里推断 Word 自动编号要求 | 标题编号、图表编号、公式编号若要被检查，仍需有元素级或后续维度级入口 |
| `template_units.verify_template_units_against_expected()` | 按 unit 和 element 的 id、顺序、字段做对比 | 直接删除/重排元素会影响模板解析阶段的契约比对 |
| `src/docfit/template_generation/runner.py` | 当前不直接读取 `template_unit_contract.yaml`；它从学校源 Word 写出 `source_template_tree.json`、`discovered_template_rules.json`、`template_artifact.json`、`template_unit_decisions.json`、`template_generation_plan.json`、`generated_template.docx`、`template_generation_manifest.json` | 阶段一不能把标准字段写成和生成器业务字段不同义，否则后续自动识别、差距报告和人工解释会对不上 |

因此阶段一不能只按“人读起来更干净”来移动字段。必须先保证每一项移动后，直接消费者仍知道它属于哪类检查，未被当前检查器消费的字段也要明确标记为“第一阶段只归位，暂不判定”。

### Step 2：建立字段消费地图和修改边界

对三校标准中的字段先做消费地图，列出：

- 哪些字段当前会被 `template-gap` 直接判定；
- 哪些字段当前只被 template parse 或 template generate 使用；
- 哪些字段当前没有下游消费者，只能作为标准事实保留；
- 哪些元素删除或改名会改变 slot 集合、元素顺序或报告路径。

本步骤的输出是一张阶段内工作表或执行总结段落，至少包含三列：

```text
原位置 -> 建议归属 -> 当前下游消费者 / 是否会改变判定
```

只有确认不会误伤下游比对后，才进入 YAML 修改。

### Step 3：审计三校标准

逐校读取 `template_unit_contract.yaml`，扫描 `expected.units[].elements`，列出疑似归属错误的元素。

重点查找：

- `content` 或 `name` 包含页眉、页脚、页码、页边距、装订线、纸张、section、school.yaml、OOXML、审查口径、全局规则；
- 只有样式或 Word 段落选项、没有实际可见文本的元素；
- 被放进某个单元但明显属于全局规则的内容；
- 可以作为标题锚点的元素和不应该作为锚点的元素。

### Step 4：给每一项归类

每个被审计项必须归到下面一类：

- 单元可见内容：保留在 `elements`。
- 单元页面/页眉规则：移动到 `page` 或 `header_footer`。
- 跨单元全局规则：移动到 `expected.global_rules`。
- 证据冲突：移动到 `expected.source_conflicts`。
- 待人工确认：移动到 `expected.open_questions`。
- 当前无法判断：先保留来源说明，并标记 `anchor_role: none`，不得用于定位。

### Step 5：分两步修改 YAML 标准

按 Step 4 的分类修改三校 `template_unit_contract.yaml`。

修改原则：

- 保留已有 `review_metadata`、`accepted_source_facts`、`dimensions`。
- 不删除来源事实，只改变机器检查字段里的归属。
- 保持 `unit_id`、`element_id` 稳定；如确实删除某个非元素项，应确认它已移动到 `global_rules`、`source_conflicts` 或 `open_questions`。
- 对关键定位元素补 `anchor_role: primary`。
- 对说明性、全局性、不可见项补 `anchor_role: none`，或移出 `elements`。

建议分两次提交或两段执行：

1. 先标注：给风险元素补 `anchor_role: none/secondary/primary`，尽量不删除元素，先让下游定位不再被污染。
2. 再归位：把确认不应作为元素的全局规则移动到 `expected.global_rules`、`source_conflicts` 或 `open_questions`。

这样做可以避免一次性删除元素导致 template parse、template generate、slot 对比和 gap 报告路径同时变化。

### Step 6：小改检查器

修改 `src/docfit/template_gap/gap.py` 中的 `_unit_anchor_queries()`。

目标行为：

```text
如果单元有 primary 锚点：
  只优先用 primary 锚点定位
否则：
  沿用旧逻辑，从 fixed/manual_only 元素中挑可搜索文本

任何 anchor_role: none：
  永远不能作为单元定位锚点
```

同时保留现有 `_looks_like_nonvisible_requirement()` 兜底，以兼容没有补 `anchor_role` 的旧标准。

本步骤只改变单元定位用什么锚点，不改变 PASS/FAIL/UNKNOWN 语义。

### Step 7：补回归测试

在 `tests/contract/test_real_core_generated_template_gap.py` 增加或调整测试，证明：

- `anchor_role: none` 不会参与单元定位；
- `anchor_role: primary` 会优先用于单元定位；
- 页眉、页码、页边距、section 规则不会把单元定位到错误正文或页眉页脚；
- 真实可见固定文本缺失仍然是 `FAIL`；
- 无可靠可搜索文本的要求仍然是 `UNKNOWN`，不能伪装成 `PASS`。

### Step 8：跑验证并检查报告

执行 focused 测试和三校 gap。检查重点不是三校是否全部 PASS，而是：

- 报告中的元素缺失是否减少了标准归属错误；
- 全局规则是否不再以普通元素缺失出现；
- 页眉页脚是否仍然独立检查，而不是污染正文单元定位；
- `FAIL` 和 `UNKNOWN` 的下一步说明是否能指向模板生成、解析能力、标准归属或人工确认。

## 验证命令

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py tests/contract/test_real_core_baseline_harness.py
```

```bash
uv run docfit eval template-gap --school hunannongye --generated-template inputs/targets/hunannongye/fixtures/template_gap/generated_template.input.docx --out runs/eval/docfit_phase1_gap_hunannongye
```

```bash
uv run docfit eval template-gap --school nannong-undergraduate --generated-template inputs/targets/nannong-undergraduate/fixtures/template_gap/generated_template.input.docx --out runs/eval/docfit_phase1_gap_nannong
```

```bash
uv run docfit eval template-gap --school pku-graduate --generated-template inputs/targets/pku-graduate/fixtures/template_gap/generated_template.input.docx --out runs/eval/docfit_phase1_gap_pku
```

```bash
uv run docfit eval coverage --profile real-core-v0 --out runs/eval/docfit_phase1_coverage
```

## 阶段一完成后的产物

### 仓库内产物

- 本计划文档：`docs/plans/template-gap-phase-1-school-standard-cleanup.md`
- 清理后的三校标准：
  - `standards/targets/hunannongye/v1/template_unit_contract.yaml`
  - `standards/targets/nannong-undergraduate/v1/template_unit_contract.yaml`
  - `standards/targets/pku-graduate/v1/template_unit_contract.yaml`
- 支持 `anchor_role` 的检查器：
  - `src/docfit/template_gap/gap.py`
- 防回退测试：
  - `tests/contract/test_real_core_generated_template_gap.py`

### 临时验证产物

- `runs/eval/docfit_phase1_gap_hunannongye/artifacts/template_gap_report.json`
- `runs/eval/docfit_phase1_gap_nannong/artifacts/template_gap_report.json`
- `runs/eval/docfit_phase1_gap_pku/artifacts/template_gap_report.json`
- `runs/eval/docfit_phase1_coverage/coverage_report.json`

这些临时产物是执行证据，不作为 signed standard、golden 或 expected snapshot。

### 最终需要交给人的文档

阶段一结束时，至少需要交付两类文档：

- 计划文档：本文件，说明输入、输出标准、涉及文件、实现流程和验收方式。
- 执行总结：可追加到本文件顶部或另写 `docs/human/real-core-v0-generated-template-gap-live-run-report.md`，说明实际改了哪些标准项、哪些仍然 `FAIL/UNKNOWN`、下一阶段应该修 Word 结构解析还是单元区域地图。

如果阶段一实际执行中发现 `template-gap-process-mainline.md` 本身有不准确之处，应先更新该主线文档，再继续改标准或检查器。

## 非目标

- 不实现真正模板生成器。
- 不修改学校原始模板 Word。
- 不让 `template_artifact.json` 替代 `generated_template_tree.json`。
- 不把页眉页脚从检查中删掉；它们仍要独立检查。
- 不自动更新 signed standard、golden 或 expected snapshot。
- 不为了减少 `UNKNOWN` 把结果改成 `PASS` 或 `FAIL`。
- 不把学校专属硬编码写进核心检查逻辑。
