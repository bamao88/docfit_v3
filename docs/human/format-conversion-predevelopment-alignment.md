# 格式转换项目开发前对齐清单

日期：2026-06-20

## 这个文件做什么

这个文件是 DocFit 格式转换项目的开发前对齐清单。它不属于某一个阶段，也不替代阶段计划。

它回答一个问题：

```text
在开始写代码、改标准、改检查器或改报告之前，团队必须先把哪些事情说清楚？
```

DocFit 的产品目标不是“生成一个 Word 文件”，而是用确定性证据证明：

- 学校模板被正确理解；
- 学生 Word 里的可见内容没有静默丢失；
- 每个内容都有明确去向；
- 生成的 Word 来自已验证的模板、放置计划和渲染过程；
- `PASS`、`FAIL`、`UNKNOWN` 的结论有标准、有检查器、有证据。

所以，开发前对齐的重点不是提前设计所有代码细节，而是先确认每个输入、字段、产物、检查结果和人工作用的身份。

## 使用规则

以下工作开始前，应该先看这份清单：

- 新增或修改学校模板生成能力；
- 新增或修改 `template-gap`、content extract、placement、render 检查；
- 调整阶段产物字段、报告字段、manifest 字段；
- 整理 signed standard、contract、golden、expected snapshot；
- 新增真实学校、真实学生样本或 eval profile；
- 修改 `docfit convert`、`docfit eval ...` 的阶段边界或 gate 逻辑。

文档优先级：

- `SPEC.md` 定义产品总语义、阶段边界、三态门禁和防漂移规则。
- `standards/schools/**` 定义已签收的学校事实。
- 本文件定义开发前要先对齐的问题清单。
- `docs/human/**` 下的阶段主线文档定义具体方向的阶段职责。
- `docs/plans/**` 下的计划文档定义某一次执行怎么做。

如果一个阶段计划里出现了项目级通用问题，应该把通用问题放回本文件，阶段计划只保留本阶段要执行的部分。

## 项目主线先对齐

开发前先把完整转换链路放在同一张图里看：

```text
学校原始模板 Word
-> source_template_tree
-> discovered_template_rules
-> template_artifact
-> generated_template.docx + template_generation_manifest

学生论文 Word
-> student_content_artifact
-> placement_plan
-> final.docx + render_manifest

所有关键产物
-> deterministic verifiers
-> PASS / FAIL / UNKNOWN
-> reports / coverage / e2e gate
```

这里有两个重要边界：

- 模板生成解决“可填写的学校模板怎么来”。
- 学生论文转换解决“学生内容怎么被提取、放置、渲染进目标模板”。

不要把学校原始模板、生成模板、学生论文、标准文件和检查报告混成同一种输入。

## 开发前必须先对齐的事项

| 对齐事项 | 开发前要说清楚什么 | 不先对齐的风险 | 对齐后的最低产出 |
| --- | --- | --- | --- |
| 产品成功标准 | 这次工作要证明什么，什么情况下算可发布，什么情况下只能算调试通过 | 把“能生成 Word”误当成“格式转换正确” | 一句话成功标准，明确是否需要通过 gate |
| 用户输入身份 | 用户真正上传什么文件；哪些只是系统参数、开发期参照或排查产物 | 把 YAML、报告、人工样本误设计成生产输入 | 输入清单，标注 `[用户文件]`、`[系统参数]`、`[开发期参照]` |
| 被测对象身份 | 当前检查测的是学校原始模板、生成模板、学生输入、放置计划，还是最终 Word | 测错对象，但报告看起来还能跑 | 被测对象路径和 hash 绑定方式 |
| 阶段边界 | 每个阶段输入什么、输出什么、不能做什么 | 某阶段偷偷做了下游决策，导致 verifier 失效 | 阶段输入/输出表 |
| 产物字段 | 每个 JSON/YAML/manifest 字段的含义、生产者、消费者、是否参与门禁 | 字段同名不同义，或者代码和报告各说各话 | 字段对齐表 |
| 标准和事实来源 | 哪些事实来自学校原始模板、人工审查、signed standard、golden 或 generated artifact | 把当前错误输出写回标准，造成标准漂移 | 来源事实表和禁止修改清单 |
| 三态判定口径 | 什么是 `PASS`、`FAIL`、`UNKNOWN`；哪些情况必须阻断 | 为了减少红灯，把未知改成通过或失败 | 判定规则和 UNKNOWN 触发条件 |
| 可见内容去向 | 学生 Word 里的每个可见内容如何进入 ledger，后续怎么追踪 | 静默丢失正文、表格、图片、公式、脚注等内容 | visible content ledger 字段和检查方式 |
| Word 结构模型 | 正文、表格、页眉页脚、字段、编号、section、图片、未知对象如何建模 | 用扁平文本替代 Word 结构，后面无法定位错误 | Word 节点坐标和结构层定义 |
| 模板规则来源 | 生产中模板规则是否自动识别；开发期人工标准怎样参与校准 | 把 `template_unit_contract.yaml` 变成用户必须上传的文件 | 自动识别规则和开发期参照的关系说明 |
| 模板单元和元素 | 单元、元素、固定内容、可填写槽位、生成字段、说明文字分别是什么 | 把说明文字或页面规则当成目标模板元素 | 单元/元素分类规则 |
| 定位锚点 | 哪些文本或结构可以定位单元，哪些只能在单元内部检查，哪些不能参与定位 | 用页眉、页码、说明文字、页边距错误定位正文单元 | 锚点角色定义，例如 `primary/secondary/none` |
| 页面和全局规则 | 页边距、纸张、页眉页脚距离、页码体系、section 创建原则放在哪 | 全局规则混入单元元素，制造误报 | 单元规则和全局规则边界 |
| 放置计划责任 | placement 负责决定内容去哪里；render 只能执行计划 | render 阶段重新决定内容位置，绕过 placement verifier | placement_plan 和 render_manifest 的责任边界 |
| 学校特例 | 学校差异是否有签收证据、配置入口、测试覆盖 | 在核心代码里写学校硬编码分支 | 特例登记方式和测试要求 |
| unsupported 对象 | 遇到未建模但可见对象时怎么记录、怎么阻断、谁确认 | 未支持内容被静默丢弃 | unsupported/needs_review 字段和 UNKNOWN 规则 |
| 报告解释层级 | 报告要说明问题属于标准、输入、解析、定位、元素、样式、分页、页眉页脚、字段、编号还是渲染 | 报告只有 FAIL/UNKNOWN，不能指导下一步开发 | 报告分层和 next action 口径 |
| AI 使用边界 | AI 可以读报告做根因分析，但不能决定通过/失败 | AI 代替确定性检查器做裁判 | AI 只能输出建议，gate 只信 verifier |
| 文件修改边界 | 哪些文件可改、只读、禁止改；哪些产物只是临时证据 | 误改 signed standard、golden、expected snapshot 或输入 Word | 修改清单和禁止清单 |
| 验证矩阵 | 改动后跑哪些 focused tests、eval 命令、coverage gate | 只跑单测，不知道真实 profile 是否被破坏 | 验证命令和临时报告路径 |
| 人工决策点 | 哪些问题必须由产品或人工审查确认，不能由代码猜 | 把不确定学校规则硬写成标准 | open questions 和 decision owner |
| 交付文档 | 开发结束后人要看哪些文档、报告和总结 | 代码变了，但人不知道标准、失败和下一步怎么变 | 计划、字段对齐表、执行总结、验证报告 |

## 字段对齐怎么写

每次新增或修改字段，都应该至少回答下面这些问题。

```text
字段名：
所在产物：
字段含义：
字段类型或形状：
生产者：
消费者：
是否参与 PASS/FAIL/UNKNOWN：
缺失时结果是什么：
来源事实或 provenance：
是否允许自动生成：
是否允许人工编辑：
是否需要 hash / snapshot / audit：
```

字段对齐表至少包含：

| 业务概念 | 当前字段 | 生产者 | 消费者 | 是否参与判定 | 缺失或不确定时怎么办 |
| --- | --- | --- | --- | --- | --- |
| 模板单元 | `template_artifact.data.units[]`、`expected.units[]` | 模板解析或签收标准 | 模板生成、gap 检查、报告 | 是，取决于阶段 | 不确定时 `UNKNOWN` 或进入人工问题 |
| 可填写槽位 | `slots[]`、`manifest.slots[]` | 模板生成 | placement、render、gap | 是 | 缺失时 `FAIL` 或 `UNKNOWN` |
| 学生可见内容 | `student_content_artifact.items[]` | 内容提取 | placement、ledger、render | 是 | 没有去向就是阻断失败 |
| 放置动作 | `placement_plan.actions[]` | placement | render、verifier | 是 | 缺动作就是 `FAIL` 或 `UNKNOWN` |
| 渲染执行记录 | `render_manifest.actions_executed[]` | render | render verifier、e2e gate | 是 | 计划未执行就是 `FAIL` |
| 生成模板检查项 | `template_gap_report.units[]/global_checks[]` | template-gap | coverage、e2e、人工排查 | 是 | 证据不足就是 `UNKNOWN` |

如果一个字段只是记录事实、当前还没有 verifier 消费，必须写清楚：

```text
已归位，当前阶段暂不判定。
```

不能因为检查器暂时不会查，就把字段塞进另一个会被检查的字段里制造 `PASS` 或 `FAIL`。

## 输入和产物身份清单

开发前要把文件身份先标清楚。

| 身份 | 含义 | 例子 | 能否作为生产输入 | 能否作为门禁证据 |
| --- | --- | --- | --- | --- |
| `[用户文件]` | 用户上传或用户明确选择的真实文件 | 学校原始模板 Word、学生论文 Word | 是 | 可以，但必须解析成结构化证据 |
| `[系统参数]` | 命令、任务或环境提供的参数 | `school_id`、`out_dir`、策略开关 | 是 | 只能解释运行条件 |
| `[开发期参照]` | 当前为了校准实现而人工整理的样本或标准 | `template_unit_contract.yaml` 在模板生成自动识别前的用法 | 否 | 可以作为签收标准的一部分时参与 |
| `[内存对象]` | 阶段间传递的数据结构 | `source_template_tree`、`template_artifact`、`placement_plan` | 否 | 落盘后可作为证据 |
| `[磁盘产物·核心]` | 用户或后续阶段真正需要的输出 | `generated_template.docx`、`final.docx`、manifest | 否，通常由系统生成 | 是 |
| `[磁盘产物·可选]` | 调试、检查、解释用输出 | tree、gap report、coverage report | 否 | 可以作为排查证据 |
| `[签收标准]` | 人工签收、版本化、可审计的标准 | signed standard、golden、expected snapshot | 否 | 是，不能自动更新 |

## 阶段边界要先对齐

| 阶段 | 输入 | 输出 | 不能做什么 |
| --- | --- | --- | --- |
| 学校模板解析/生成 | 学校原始模板 Word、必要的运行参数、开发期签收标准 | `source_template_tree`、`discovered_template_rules`、`template_artifact`、`generated_template.docx`、`template_generation_manifest` | 不能宣称最终转换通过 |
| 生成模板差距检查 | `generated_template.docx`、已签收或已确认的规则 | `generated_template_tree.json`、`template_gap_report.*` | 不能用 `template_artifact` 替代被测 Word 证据 |
| 学生内容提取 | 学生论文 Word | `student_content_artifact`、visible content ledger | 不能静默丢弃可见内容 |
| 内容放置规划 | 学生内容、模板 artifact、学校标准 | `placement_plan` | 不能渲染 Word，也不能让 render 再决定位置 |
| DOCX 渲染 | `generated_template.docx`、`placement_plan`、学生内容 | `final.docx`、`render_manifest` | 不能重新判断内容应该放哪里 |
| eval / coverage / gate | 各阶段产物、标准、报告 | `PASS/FAIL/UNKNOWN`、issue clusters、PM 报告 | 不能让 AI 或人工感觉替代 verifier |

## 开发前最低输出标准

进入实现前，至少要有下面这些内容。可以写在阶段计划里，也可以写在单独的执行前对齐记录里。

- 这次改动属于哪个阶段，以及不属于哪个阶段。
- 输入身份表：用户文件、系统参数、开发期参照、签收标准、被测对象。
- 输出产物表：核心产物、检查产物、临时证据、最终报告。
- 字段对齐表：业务概念、字段、生产者、消费者、是否参与判定。
- 判定口径：哪些情况是 `PASS`、`FAIL`、`UNKNOWN`。
- 文件修改边界：必须改、只读参考、禁止改。
- 验证矩阵：focused tests、eval 命令、coverage 命令、报告路径。
- 人工问题清单：哪些学校事实、产品规则或质量口径需要人确认。
- 开发结束后要交付的文档和报告。

如果这些内容缺失，不应该直接进入实现。应该先补齐对齐记录，再写代码。

## 当前阶段一如何使用本文件

`docs/plans/template-gap-phase-1-school-standard-cleanup.md` 是一次具体执行计划。它应该只保留阶段一要做的事情：

- 整理三校 `template_unit_contract.yaml`；
- 区分单元内容、单元规则、跨单元规则、冲突和待确认项；
- 为定位锚点补 `anchor_role`；
- 小改 `template-gap` 的定位逻辑；
- 用 focused tests 和三校 gap 报告验证。

项目级的开发前对齐事项放在本文件，不放在阶段一计划里。阶段一计划只需要引用本文件，并把本阶段实际用到的字段对齐表写清楚。
