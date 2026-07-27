# T1 原始解析、L1 技术合并与下游阶段输入视图（讨论稿）

> Status: discussion draft  
> Created: 2026-07-24  
> Scope: 明确模板生成 T1 原始解析、L1 技术字段合并、T2/T3 阶段输入与判断之间的责任边界，以及 T5/T6/T7 的输入关系；T4 本轮只保留兼容边界  
> Related identity discussion: [`t1-l1-source-identity-and-structure-discussion.md`](./t1-l1-source-identity-and-structure-discussion.md)  
> Related T3 discussion: [`t3-stage-input-hierarchical-structure-discussion.md`](./t3-stage-input-hierarchical-structure-discussion.md)  
> Canonical target: 讨论定稿后迁入 [`template-generation-architecture.md`](../current/template-generation-architecture.md) 的 T1、L1、阶段依赖和各阶段输入章节  
> Non-goal: 本文不修改正式架构契约、artifact schema、代码、标准、测试或实施计划。

> **Current scope override — T4 暂缓：本轮不讨论、不设计、不修改也不验收 T4。文中保留的 T4 内容只用于说明现有兼容边界，确保 T1/L1 改动不破坏当前 T4 consumer；它不构成本轮字段方案、实施任务或完成门禁。后续恢复 T4 时另行讨论和立项。**

> 本文只用于讨论。它记录用户本轮已经明确的总体原则，并提出 T1 原始解析、L1 技术合并与下游视图方案。源原子边界已经按相关身份讨论稿第 5.1 节固定：叶子 occurrence 是原子、容器不是原子、字符使用原子内区间；后续 Plan 15 Phase 1 只冻结完整 OOXML 类型映射和精确序列化 schema，不重新打开原子粒度。

## 0. 现行事实基线与优先级

本文讨论的是 T1/L1 的目标优化，但迁移约束必须以当前各阶段真正生产和消费的输入输出为准。发生冲突时，按以下顺序判定事实：

1. 当前代码中的 producer、final publisher、consumer，以及由当前版本可复现生成并通过契约检查的真实 artifact；
2. [`docs/current/template-generation-architecture.md`](../current/template-generation-architecture.md) 与 [`docs/current/template-generation-testing.md`](../current/template-generation-testing.md) 中和实现一致的现行契约；
3. `docs/status/active/` 中记录的已实现、部分完成和未闭环状态；
4. 已批准且仍在执行的 plan；
5. `docs/human/` 中的讨论稿和未来方案。

历史运行目录中的旧 artifact 只能证明当时的行为，不能因为文件真实存在就覆盖当前 producer/schema。`docs/human/` 中提出但尚未进入代码、测试和 canonical 文档的 T2-A/T2-B、多种 T3 处理模式、统一 T3 target spec、T5 declarative slots/effects 和 T6 transaction/slot catalog，也都不是本轮现行字段。

截至 2026-07-26，长期架构文档对 T2–T7 的阶段关系和核心输出字段与当前实现一致，可以作为本轮迁移基线；但有两点必须以实现为准：

- 当前 L1 实际还输出 `source_structure_index`，长期架构文档的 L1 必备内容表漏列了该字段；
- 长期架构文档只列阶段核心字段，没有穷举 T2/T4 stage view 的完整序列化形状；完整 shape 仍由当前 builder、schema、契约测试和当次 artifact 共同确定。

因此，本文后续出现的 `source_atom_seq`、统一 selection/locator 和正文域/全局域完全分离，均是 T1/L1 的**目标状态**；当前 `source_seq`、`source_ref`、raw/logical Run、span、object 和 page/render 引用则是迁移期间必须继续兼容的**现行接口**。

## 1. 这次讨论要解决什么

模板生成的 T2、T3、T4 以及后续执行和验证，本质上都在使用同一份学校源 Word。但只有 T2、T3、T4 需要面向模型或判断任务的“筛选视图”；T5 是合并阶段，T6 是依据 T5 修改原始 Word 的执行阶段，T7 是不可跳过的成品验证阶段。

当前需要明确四个问题：

1. T1 原始解析和 L1 技术合并分别负责什么；
2. L1 可以新增哪些技术字段、必须停在哪里；
3. 哪些内容属于源事实，哪些内容必须留给后续语义阶段；
4. T2、T3、T4 分别应该看到哪些筛选事实，以及 T5、T6 应读取什么。

如果这些问题没有先定稿，后续很容易出现：

- T2、T3、T4 分别重新投影甚至重新推导源文档事实；
- T3 为了层级遍历重新恢复 table、cell、paragraph、run 关系；
- 同一对象在不同阶段出现不同身份或不同父子关系；
- 阶段输入只给了局部摘要，却没有说明省略和完整性；
- T6 执行时重新解释 source ref 或 run 编号；
- “输入构造”逐渐混入该阶段自己的语义判断。

## 2. 本轮已经明确的总体原则

### 2.1 T1、L1、下游判断是三个不同责任层

T1 和 L1 连续执行，但不能再被描述成职责相同的一个步骤。正确边界是：

```text
                           ┌→ T1：解析并整理原始内容 ─────────┐
源 DOCX（同一 source hash）─┤                                ├→ L1
                           └→ render：导出 PDF/页面图片与位置事实 ┘

L1：合并 T1/render facts，并新增统一技术字段
  → T2/T3/T4：构造各自阶段输入并进行判断
  → T5 → T6
                        ↓
                 T7 强制验证
```

三层可以概括为：

```text
T1：不新增，只忠实解析
L1：可以新增技术字段，但不能新增语义
T2/T3/T4：进行任务相关的组织和判断
```

T1 `document_facts` 是原始解析事实和诊断产物；sealed L1 是加入统一技术字段后的下游事实契约。T2/T3/T4 只读 L1，不直接绕回 T1 artifact 补事实。

这一阶段的最高边界原则是：

> **T1 负责忠实解析；L1 负责让这些原始内容不丢失、可查询、可定位；T2/T3/T4 负责组织问题并作出判断。**

这三个责任分别表示：

- **不丢失**：T1 忠实解析源 DOCX 的内容、结构、样式、对象、控制节点和未知项；L1 合并后不得改变或补写这些源内容；
- **可查询**：下游能够按 atom、结构容器、样式、page、bbox 等条件取回事实，不需要重新解析 DOCX；
- **可定位**：任何被下游选中的 atom 或字符范围都能解析回源 OOXML 地址和视觉位置。

L1 可以新增确定性的统一技术字段，但不负责生成 unit、element、layout policy，也不负责提前生成某个阶段专用的摘要、分组、span 方案或最终 view artifact。L1 提供的是足以完成这些工作的中立事实和查询能力。

### 2.2 L1 新增字段必须满足三个条件

L1 新增的任何字段都必须同时满足：

1. 能根据 T1 facts 和 render facts 确定性生成；
2. 不改变、不补写、不纠正源内容；
3. 不包含 unit、span、策略、角色或版式语义判断。

典型允许字段包括统一 `source_atom_seq`、统一 locator map、结构查询索引、raw text 字符坐标、source text hash、coverage/unknown/unbound/not_available，以及 schema/artifact hash。对视觉事实，L1 还可以封存 render engine/version、PDF 与页数、clean/annotated page image refs、`source_render_hash`、page layout，以及 page/bbox/atom binding。

### 2.3 一份事实，三套任务筛选视图

T2、T3、T4 不应各自建立事实源。它们各自的 view builder 应查询同一个 sealed L1，并生成按任务筛选的只读视图。

```text
                        ┌─ T2 全文分段视图
sealed L1 fact space ───├─ T3 unit 范围层级视图
                        └─ T4 全局版式视图
```

这些视图可以：

- 选择当前阶段需要的事实；
- 压缩或摘要不需要完整展开的字段；
- 调整呈现顺序；
- 附加当前阶段所需的上下文；
- 在输入过大时分窗或分页。

这些视图不能：

- 重新读取 DOCX 发现源事实；
- 重新创建源内容身份；
- 重新恢复物理父子关系；
- 修改 L1 已记录的文本、样式、顺序或对象归属；
- 把本阶段代码判断伪装成输入事实；
- 静默省略内容却仍声明输入完整。

### 2.4 依赖上游语义结果的内容必须留在后续阶段

“尽量提前准备”应拆开理解：T1 把原始事实解析完整，L1 把统一技术字段、查询索引和定位能力准备完整；二者都不把下游的筛选、组织和判断提前。

例如：

- T3 需要查询 table、cell、paragraph、run 的物理关系；T1 负责解析并保留关系，L1 负责增加统一引用和查询索引，T3 专用的层级输入仍由 T3 view builder 组织；
- 某个 paragraph 属于哪个 `unit` 依赖 T2 final，必须在 T2 后形成；
- T3 的 Keep、Fill、Delete 或 Generated 属于元素策略，不能进入 L1；
- T4 的最终 page numbering 或 layout policy 属于 T4 判断，不能进入 L1；
- T6 的 Word 修改动作依赖 T5 final，不能由 L1 提前生成。

### 2.5 结构化事实与页面图片共同构成源真值

T1 解析结构事实，独立 render 过程把同一份冻结源 Word 渲染成页面图片，L1 负责合并并封存两类事实。对下游而言：

- 结构化事实是“源 package 真值”：能精确回查文字、结构、样式和 OOXML 位置；
- 页面图片是“视觉呈现真值”：能看到 Word 实际排版后的页面、位置、留白和对象外观；
- 两者必须绑定到同一个 source hash，并用 render hash、page、bbox 和 `source_atom_seq` binding 互相连接；
- 页面图片不是另一套 source atom 身份，也不能替代可执行的结构定位。

T2、T3、T4 可以按任务选择整页图或裁剪图。图片由 render 过程生成；L1 负责版本封存和 atom/page/bbox 绑定；下游只选择和查看，不再临时建立一套图片事实。

Word 导出图片必须是正式 render facts，而不是只有调试用途的临时文件。至少包括：

| Render fact | 责任 |
| --- | --- |
| `clean_page_images` | 与源 Word 页面一致的干净页面图，是下游模型的主要视觉输入 |
| `annotated_page_images` | 带 bbox/编号等叠加信息的诊断图，只用于定位和审查，不替代 clean image |
| `pdf` / page count | Word 渲染中间产物、实际页数和页面顺序证据 |
| `source_render_hash` | 证明页面图来自哪份 source snapshot 和哪次 render |
| render engine/version | 记录 Word/PDF 渲染实现，支持复现和差异诊断 |
| `page_layout_index` | page size、page number、页面顺序和必要几何事实 |
| atom/object → page/bbox binding | 让结构化事实能定位到页面图片中的具体区域 |
| availability/error | 导出失败、缺页、无法绑定或 fallback 的显式原因 |

L1 可以在 render 失败时封存 `not_available` 以保留诊断链，但需要图片的下游阶段不能把图片缺失当成“已经完成视觉判断”。T2/T4 必须显式降级 availability 或进入复核；T3 对受影响 unit 必须记录 visual evidence 缺失。

下游消费关系是：

```text
T2：全部 clean page images，image-first 识别 unit 与边界
T3：当前 unit 涉及的页面图或 crop + atom/page/bbox binding
T4：全部页面图 + page layout index + 全局事实域
T7：对最终 DOCX 重新 render，使用新的 final render hash 做成品验证
```

Stage View 必须真正携带可供模型读取的图片内容或正式附件引用；只有本机路径字符串不构成视觉输入。

当前对 T2 的默认呈现顺序应明确为：

```text
先看页面图片形成整体视觉认识
→ 再用 page/bbox binding 找到结构化事实树中的具体 source atom
→ 最后按需展开文字、结构和样式细节
```

### 2.6 T1 原始事实必须区分正文域与全局域

T4 的输入是全局文档事实，不应从正文内容流中临时拼装。T1 解析时就应按 OOXML 的物理归属，把原始事实至少分成两个中立事实域：

```text
T1 document facts
├── body_content_facts
│   ├── body paragraph / table / row / cell / run
│   ├── body object / field occurrence
│   └── body order and physical membership
└── global_document_facts
    ├── section properties and page geometry
    ├── header/footer parts, references and inheritance
    ├── page-number fields and document-level fields
    ├── break facts and section boundaries
    ├── numbering definitions and document-level settings
    └── document defaults / shared style definitions
```

这里的“识别”是按源 part、节点类型和物理关系进行客观分类，不是判断最终 page policy 或 layout policy。

两域之间可以有明确引用，例如正文段落引用 section、numbering definition 或 field；但完整的全局对象只在全局域保存一次，不应混入 `body_flow` 后再由 T4 反向猜测。两域中需要独立追踪的源对象仍共享同一套 L1 identity。

L1 在不改变 T1 分类的前提下，为两个事实域增加统一 identity、locator、跨域引用、page/bbox binding 和查询索引。T4 view builder 默认只读取全局事实域、visual page facts 和必要的最小正文锚点。

### 2.7 现行阶段输入输出冻结基线

下表记录当前生产路径，不表示目标 T1/L1 字段已经实现。T1/L1 的优化必须兼容或显式迁移这些现行消费者，不能用未来讨论稿中的阶段形态替换它们。

| 层/阶段 | 当前主要输入 | 当前正式输出 | 当前核心业务字段 |
| --- | --- | --- | --- |
| T1 | 原始 source DOCX/OOXML | `01_document_facts.json` | `metadata`、`body_flow`、`runs`、`unknown_objects`、`indexes`、`warnings`、`data`；当前 `source_seq` 在本层生成 |
| L1 | T1 `document_facts` + 同源 render facts | `01.5_l1_input_contract.json` | `input_hashes`、`source_text_index`、`run_index`、`source_object_index`、`source_structure_index`、`layout_fact_index`、`visual_page_index`、`coverage` |
| T2 | sealed L1 派生的 T2 stage input + 全页视觉事实 | `02_unit_map.yaml` | `units[]` 的 `unit_id`、`unit_name`、boundary、order、`page_refs`、`source_seq_range`、`source_seq_refs`、`source_refs`、`page_policy` |
| T3 | sealed L1 + T2 final 派生的 unit-scoped hierarchical input | `03_element_spec.yaml` | `elements[]` 的 element/unit/stable/order identity、source/run identity、spans、content、policy、role、fill/generated、confidence、evidence、flags |
| T4 | sealed L1 的全局/布局/视觉事实；不依赖 T2/T3 final | `04_global_spec.yaml` | `section_profiles`、`default_font`、`page_numbering`、`header_footer`、`numbering_rules`、flags |
| T5 | L1 引用校验 + T2/T3/T4 final | `05_template_spec.yaml` | `l1_input_contract_ref`、`input_hashes`、`global`、`units`、`page_policy`、section refs、`elements`、`review_flags`、`review_decisions` |
| T6 | 原始 source DOCX + T5 final + L1 identity resolver | `06.1_fillable_template.docx` + `06.2_build_manifest.json` | output、slots、generated fields、page/section breaks、keep/page-policy results、actions、identity resolution、observed effects、input/output refs |
| T7 | T6 最终 DOCX、manifest、上游 refs 与验收规则 | `07_verification_report.json` | `status`、`first_bad_stage`、`stages`、`findings[]`；差异项记录 expected/observed、owner、root cause |

T2–T5 final 还统一携带 `stage_id`、`result_role=final`、`availability`、`input_refs` 和 `lineage`。T7/post-T6 verification 是六个业务生成阶段之后的强制验证阶段，不计入业务生成阶段数量，但属于完整流程且不能跳过。

本轮只允许 T1/L1 在上述基线上做受控扩展和迁移。T2-B、按 unit 类型拆分的多种 T3 模式、T5 slots/effects 新契约等未来变化，必须另立状态与 plan；它们不能成为 T1/L1 当前改造的隐含前置条件。

## 3. 与统一源身份讨论稿的关系

本文不重新定义源对象身份，直接采用身份讨论稿目前已经形成的共识：

1. T1 不创建统一身份；L1 为一份冻结源 Word 确定性增加一套底层源内容顺序编号；
2. 新增的叶子级身份固定命名为 `source_atom_seq`；现有 `source_seq` 保留原名称和现有粒度，不被重解释；
3. raw Run、图片、公式、空单元格、字段和其他需要独立追踪的源内容共享同一套编号；
4. 对象类型、表格行列、OOXML path 和内部数组位置是事实或 locator，不是并列业务身份；
5. `source_atom_seq` 只回答源原子身份；单个、连续、非连续和字符级目标由 source selection 表达；
6. locator 是执行地址，page/bbox 是视觉位置；二者都不是第二套业务身份。

这是目标身份模型，不表示当前公开字段可以立即删除。迁移期间，L1 必须为现有 `source_seq`、`source_ref`、raw/logical Run ID、span、object 和 page/render 引用提供稳定兼容投影或双写校验；只有 T2–T7 当前消费者完成迁移并通过真实运行、契约测试和残留扫描后，新的统一身份才能成为唯一输出。

因此，本文后面提到 paragraph、table、cell、run、field 或 source object 时，指的是客观结构对象或事实集合，不表示它们必须再获得一套并列业务编号。

如果阶段视图为了递归遍历需要 `target_ref` 或 `view_ref`，它应满足：

- 只在当前 view 内起寻址作用；
- 必须绑定一个明确的 `source_atom_seq` 或 source selection；
- 不能被下游当成新的源内容业务身份；
- 不能与 `source_atom_seq` 竞争“源内容到底是谁”的解释权。

以下问题继续由身份讨论稿细化，本文不提前给出完整 schema：

- 五类原子与全部 OOXML 节点的完整映射；
- 附属 part、浮动对象和 unknown 的完整排序枚举；
- 客观结构采用树、成员关系还是“原始树 + 派生视图”；
- raw Run 字符地址空间和 selection locator 的精确 schema；
- locator 的具体形状。

### 3.1 四类坐标必须分离

| 概念 | 回答的问题 | 典型形状 | 是否是身份 |
| --- | --- | --- | --- |
| source identity | 这是哪个源原子 | `source_atom_seq` | 是，唯一一套 |
| source selection | 选中了哪些原子或哪些字符 | atom interval、ordered members、character span | 否 |
| execution locator | 在 DOCX/OOXML 哪里执行 | part、XML path、父容器、run/char address | 否 |
| visual binding | 渲染后出现在哪里 | page、bbox、render target、crop | 否 |

“统一身份”只约束第一行，不能取消后三行。L1 保存物理成员关系并提供 selection/locator 能力；结构容器、T2 unit、T3 element 和 T6 action 可以在各自阶段形成 selection，T6 再把 action selection 解析为 locator。L1 不需要提前枚举下游将会产生的所有 selection。

## 4. T1 与 L1 各自的完成标准

完成信号不能只是“成功生成 JSON”，需要分别判断：

- **T1 完成**：源 DOCX/OOXML 已被忠实解析；原始内容、顺序、关系和 locator 被保留；不能解析的节点被显式记录；
- **L1 完成**：T1 facts 与 render facts 已确定性合并；统一身份、索引、定位、字符地址、视觉绑定、完整性和封存字段已生成并通过一致性校验；源内容未被修改或补写。

> T2、T3、T4 不需要重新读取或重新理解源 DOCX 来发现客观事实；它们从 L1 查询事实，自行组织本阶段输入并完成本阶段判断。T6 重新打开原始 DOCX 只为了执行 T5 动作，不是为了重新发现事实。

至少需要满足以下能力。

### 4.1 源内容完整覆盖

T1 必须记录所有后续可能被保留、替换、删除、校验或用于排版的源内容，并显式记录 unsupported/unknown 源节点；L1 再增加 coverage、unknown、unbound 和 not_available 汇总。

至少包括：

- 正文、表格、页眉、页脚、脚注和尾注中的文字；
- raw Run、空 Run、空段落和空单元格；
- 图片、公式、文本框、内容控件和绘图对象；
- 字段、分页符、分节符和编号引用；
- 嵌套表格、合并单元格和浮动对象；
- 只产生版式作用、没有普通可见文本的节点；
- 当前解析器不能识别但在源 package 中确实存在的对象。

### 4.2 客观结构可查询

后续阶段必须能够直接查询而不是猜测：

- 文档主体的确定性顺序；
- paragraph、table、row、cell、run 的物理包含关系；
- 单元格合并、网格、嵌套和空内容；
- field 的起止字符位置与显示结果；
- object 的锚点、父容器和相邻源内容；
- 页眉页脚、脚注、文本框等跨 part 关系；
- 上层结构对象包含的物理 source selection。

这里要求“可查询”，但尚不提前决定最终序列化必须是一棵树、一个关系表还是原始树加派生索引。

### 4.3 文本和格式可回查

至少应保存：

- 原始文本、空格、tab、换行和字段显示结果；
- raw Run 字符坐标；
- 段落属性、字符属性、表格属性和单元格属性；
- direct formatting、style inheritance 和 effective style；
- 样式事实来自哪个源节点或 style definition；
- 编号、列表、边框、底纹、缩进、行距和分页控制事实。

### 4.4 布局和视觉可绑定

至少应表达：

- section、break、page size、orientation 和 margin；
- header/footer references 和 page numbering field；
- 从同一份冻结源 Word 导出的 PDF、实际页数和按页排序的 clean page images；
- annotated page images 及其诊断用途，不能与 clean page images 混为模型主视觉输入；
- render engine/version、`source_render_hash`、PDF hash、每页图片 hash 或等价的可复现校验信息；
- 页面图片所对应的 source hash，并证明结构化 facts 与 render facts 来自同一份源快照；
- 源内容对应的 page、bbox 和 render target；
- 页面首尾 `source_atom_seq`；
- clean page image 数量与实际 page count 的一致性；
- 无法渲染、缺页、无法绑定或只得到 projection fallback 的原因。

“页面图文件已经生成”本身不等于视觉事实完成。至少还需要证明：

1. 页面图来自当前 sealed source snapshot，而不是旧缓存或另一份 Word；
2. 每一页都有稳定页码、顺序和可读取的 clean image；
3. 页面图能够通过 page/bbox 与结构化 source atom 或 source object 互相回查；
4. `real_render`、`projection_fallback`、`not_available` 等状态不会被下游混用；
5. Stage View 真正把图片内容或可读取附件传给模型，而不只是传本机路径字符串。

### 4.5 完整性和未知成员可证明

L1 不只要保存“找到了什么”，还要保存：

- 哪些源内容已覆盖；
- 哪些对象没有身份；
- 哪些对象有身份但没有视觉绑定；
- 哪些容器的 child 不完整；
- 哪些结构因 merge、nested、field 边界或解析能力不足无法确认；
- 哪些证据不可用，而不是默认不存在。

Stage View 因筛选而产生的 omissions 由对应 view artifact 记录，不写回 L1 coverage。

## 5. T1 与 L1 的责任边界

T1 与 L1 是连续但不同的责任层。T1 的输出是原始解析事实；L1 的输出是增加统一技术字段后的 sealed facts。

### 5.1 T1：源 package 客观提取

对外理解上，T1 基础事实阶段固定产出三份数据：正文事实、全局事实和源模板渲染事实。内部实现可以继续把 DOCX parser 和 render pipeline 并行执行，但 L1 必须在三份数据都封存后才能开始。

```text
                         ┌→ 01.1_body_content_facts.json
source DOCX → T1 parser ─┤
                         └→ 01.2_global_document_facts.json

source DOCX → render ─────→ 01.3_source_render_facts.json
                              + PDF / clean page images / annotated diagnostics

三份 component hashes
  → 01_document_facts.json（现有 T1 final/兼容入口）
  → 01.5_l1_input_contract.json
```

这些是目标稳定产物名，尚未在当前代码中完成拆分。当前实现仍只有合并的 `01_document_facts.json`、render 目录/packet 和 `01.5_l1_input_contract.json`。迁移时不删除或改名 `01_document_facts.json`：它继续作为 T1 final 与兼容 bundle，增加三份 component refs/hashes，并在下游完成迁移前保留当前 `metadata`、`body_flow`、`runs`、`unknown_objects`、`indexes`、`warnings` 和 `data`。

三份数据必须满足共同约束：

- 使用同一个 `source_template_hash`；
- 各自有 `artifact_type`、`artifact_version`、`producer`、`created_at` 和 `availability`；`01_document_facts.json` 记录三份 component ref 与 sha256，避免文件在自身内容中记录自哈希；
- 所有 path 使用 run artifact 内可搬移的相对引用，并带文件 hash；只有本机绝对路径不能成为稳定契约；
- unknown、unsupported、render failure 和 unbound 必须显式存在；
- T1 只保存源事实和原始 locator，不分配 `source_atom_seq`，也不产生 unit、element、policy 或 gold 字段。

#### 5.1.1 正文事实：`01.1_body_content_facts.json`

| 字段 | 内容与含义 | 兼容策略 |
| --- | --- | --- |
| `metadata` | source path/hash、DOCX 是否存在/有效、parser/schema version | 保留当前字段 |
| `body_flow` | 当前按正文可见流组织的条目；保留 `source_seq`、`source_ref`、`node_id`、`order`、text/style/run refs 等 | 名称、数值和粒度不改 |
| `source_leaves` | T1 解析出的叶子 occurrence：`text`、`inline_object`、`control`、`empty_placeholder`、`opaque_unknown`；只有原始 ref/order/locator，没有 `source_atom_seq` | 新增 |
| `body_structure` | document/body → paragraph/table → row/cell → raw Run/leaf 的物理 parent/child/member 关系，含 merge、nested、empty | 新增；不替换当前 `data.paragraphs/tables` |
| `runs` | 当前 raw/logical Run 事实、`raw_run_id`、`logical_run_id`、文字、样式及互相映射 | 保留当前名称 |
| `objects` | 正文中的 image、drawing、equation、text box、content control 等 occurrence、anchor、relationship、media hash | 从当前 `data` 做无损分区，保留旧投影 |
| `formatting_facts` | paragraph/Run/table/cell 的 direct style、style provenance、effective style 和原始属性 | 新增中立分区；当前 style 字段继续存在 |
| `indexes` | `by_source_ref`、`by_source_seq`、body order、run indexes，以及源结构查找入口 | 保留并增量扩展 |
| `unknown_objects` / `warnings` | 未识别叶子、opaque subtree、解析缺口和原始诊断 | 保留当前名称 |

`source_leaves` 每一项至少包含 `source_ref`、`part_name`、`order`、`kind`、`parent_ref`、`container_refs`、raw locator、可见性、supported/unknown 状态，以及适用的 `text`、`raw_run_id`、object/control facts。它描述“有哪些原子候选”，但不在 T1 建立统一业务身份。

#### 5.1.2 全局事实：`01.2_global_document_facts.json`

| 字段 | 内容与含义 |
| --- | --- |
| `metadata` | 与正文事实相同的 source snapshot、parser/schema 信息 |
| `sections` | section occurrence、顺序、边界 locator、page size、orientation、margin、columns、title-page 等原始属性 |
| `headers_footers` | header/footer part、first/default/even 类型、引用和继承、内部结构与叶子 occurrence |
| `fields` | field type、instruction、result、begin/separate/end 关系、part、locator |
| `breaks` | line/page/column/section break occurrence、类型、位置和相邻 source refs |
| `numbering_refs` / `numbering_definitions` | 正文引用与 package 定义，保持两者分离 |
| `style_definitions` / `document_defaults` | 共享样式定义、默认字体/段落/字符属性及来源 |
| `package_resources` | part inventory、relationships、media/resource refs 和 hashes；资源本身不是 source atom |
| `global_structure` | section、header/footer、field、break、numbering 与其物理 child/member/cross-ref 关系 |
| `global_leaves` | 位于 header/footer、footnote/endnote 等附属 part 的叶子 occurrence；字段与正文 `source_leaves` 相同 |
| `unknown_objects` / `warnings` | 全局域未知节点、缺失 part/ref、继承或解析问题 |

正文事实只保存对 section、numbering、field、break 等全局对象的原始引用；完整全局对象只在本文件保存一次。header/footer 等附属 part 中的文字和对象属于全局事实文件，但进入 L1 后与正文叶子共享同一套 `source_atom_seq`。

#### 5.1.3 渲染事实：`01.3_source_render_facts.json`

这份 JSON 是 PDF、页面图片和结构内容对应关系的稳定 manifest；图片和 PDF 不内嵌进 JSON，作为同一 run 下的二进制 artifact 保存。

| 字段 | 内容与含义 |
| --- | --- |
| `input_hashes` | `source_template_hash`、正文事实 hash、全局事实 hash |
| `render_status` / `render_error` | `real_render`、fallback、`not_available` 及明确错误 |
| `source_render_hash` | 由 source snapshot、render engine/version、PDF、页面图和 binding 共同确定的渲染快照身份 |
| `render_engine` / `render_version` | 实际 Word→PDF→image 工具链及版本 |
| `pdf` | 相对 artifact ref、sha256、实际 page count |
| `clean_page_images[]` | `page_no`、相对 ref、sha256、width/height、image type；供模型看真实页面 |
| `annotated_page_images[]` | 诊断图 ref/hash、对应 page；只用于定位和人工审查 |
| `page_layout_index[]` | page number、page size、按页位置、render target、必要 bbox |
| `source_bindings[]` | `source_ref`、现有 `source_seq`/raw Run/object ref → page/bbox/render target、binding status |
| `binding_summary` | bound/unbound/fallback 数量、缺页、重复绑定和不可绑定原因 |
| `completeness` | PDF 页数与 clean images 数量一致性、逐页 hash 完整性、source snapshot 一致性 |

`source_bindings` 在 T1/render 阶段只能使用现有客观 ref；L1 分配 `source_atom_seq` 后，再把这些 binding 确定性扩展到 atom 级。

T1 不负责：

- 新增统一业务字段；
- 创建 `source_atom_seq`；
- 把正文、全局和 render 三份数据交叉合并；
- 创建跨索引、完整性汇总或下游视图；
- 创建 unit、span、element、布局策略或任何语义结果。

### 5.2 L1：统一、交叉绑定和封存

L1 只生成一份稳定、sealed、可回放的 `01.5_l1_input_contract.json`。代码运行时可以把它加载成内存对象或查询索引，但内存对象不是第二事实源；所有下游必须能用该文件及其 hash 重放相同输入。

当前已有字段不改名，继续作为兼容接口：

| 当前字段 | 当前含义 | 本轮怎样扩展 |
| --- | --- | --- |
| `input_hashes` | source、T1 document facts、render facts hashes | 增加三份 T1 component hashes |
| `source_text_index` | 当前 `source_seq` 文本流、source refs、run refs、style、page/bbox | 增加 `source_atom_seq_refs` 和完整 source selection，不改变 `source_seq` |
| `run_index` | raw/logical Run 及 source 映射 | 增加 raw Run child → atom、atom → character range 映射 |
| `source_object_index` | 图片、文本框、content control、unknown 等 occurrence | 每个叶子 object 增加唯一 `source_atom_seq`；容器只增加 member refs |
| `source_structure_index` | paragraph/table/body order/source refs/unknown | 增加完整 parent/child/member、merge/nested/empty 和 atom refs |
| `layout_fact_index` | sections、headers/footers、fields、breaks、numbering | 增加全局叶子 atom refs、正文 anchor 和 cross-domain refs |
| `visual_page_index` | render 状态/hash、PDF、images、page layout 和 bindings | 增加逐页 hash/completeness、atom → page/bbox/image binding |
| `coverage` | text/run/object/layout/render 数量和缺口 | 增加 atom、locator、structure member、visual binding 的总数与 gap |

L1 另外新增四个明确字段：

| 新字段 | 形状与含义 | 主要消费者 |
| --- | --- | --- |
| `source_atom_index` | `atoms[]` + `by_source_atom_seq`；每个 atom 保存 `source_atom_seq`、kind、source/raw Run/object refs、part/order、内容或 payload ref、parent/container refs、coverage status | T2/T3 选择、T5 校验、T6 执行、T7 trace |
| `source_membership_index` | container ref → ordered child/member refs 与 `source_atom_seq_refs`，并记录 merge/nested/empty/children_complete | T2 block、T3 层级树、T6 scope 校验 |
| `text_address_index` | 文字 atom 的原文、text sha256、offset unit、length、raw Run locator 和字符范围映射 | T3 candidate/semantic span、T6 字符级动作 |
| `locator_index` | `source_atom_seq` → source hash、part、OOXML path、raw Run child/object/control address；selection 可确定性展开为 locators | T6 resolver、T7 owner/trace |

`source_atom_seq` 采用新增字段，现有 `source_seq` 不改名、不改数值、不改变粒度。L1 必须保存：

```text
source_seq
  ↔ ordered source_atom_seq[]
  ↔ raw_run_id / logical_run_id / source_ref / object_id
  ↔ locator
  ↔ page / bbox / render target
```

L1 还负责：

| 能力 | L1 责任 |
| --- | --- |
| 身份 | 为 T1 叶子 occurrence 分配 `source_atom_seq`，校验唯一、顺序、覆盖和重复 |
| 结构 | 不改变 T1 正文域/全局域及物理关系，只增加统一引用和中立查询索引 |
| 文本地址 | 基于 T1 raw Run 增加稳定字符坐标和 source text hash，不预先决定 T3 span |
| 对齐 | source atom、container、section/break/field、page/bbox/image 和当前兼容 refs 互相绑定 |
| 完整性 | coverage、coverage gap、unknown、unbound、not_available 与分母/分子 |
| 封存 | source/component/render/L1 hashes、schema version、input refs 和 lineage |

L1 新增字段必须能够由 T1/render facts 确定性生成，不得改变或补写源内容，不得包含 unit、span、策略、角色或版式语义判断。L1 可以做无损规范化、索引构建和坐标转换，但不能做阶段专用筛选、摘要、分组、span 方案或语义判断。

如果 T1 漏解析了一个源节点，L1 只能把它报告为 coverage gap 或 not_available，不能自行猜测内容并补成新的源事实。

### 5.3 客观规范化与语义判断的边界

| 信息 | T1 原始解析 | L1 可新增的技术字段 | 下游才可产生 |
| --- | --- | --- | --- |
| 段落格式 | 原始 style、字体、字号、对齐、outline | 统一 atom refs、样式查询索引 | “这是一级标题” |
| field | 原始 type、instruction、result、locator | 字符坐标、text hash、统一 locator | “这是目录 unit” |
| 页面 | section、break、page size 等源事实 | render page、bbox、首尾 atom、visual binding | `page_policy.start=new_page` |
| 表格 | row/cell/merge/nested/empty、源顺序 | 统一 atom refs、结构查询索引 | “这是封面信息表” |
| 文字 | 原文和 raw Run | `source_atom_seq`、字符坐标、text hash、locator map | candidate/semantic span、fixed/fill/delete |
| 图片 | media、anchor、原始对象关系 | page/bbox/render binding | “这是必须保留的校徽” |
| 完整性 | unknown/unsupported 原始节点 | coverage、unbound、not_available 汇总 | confidence 或质量 PASS |

## 6. L1 事实空间建议包含的能力分区

以下是第 5.2 节公开字段在概念上的能力分区，不是另一套并列字段名。实现应继续使用现有索引字段和第 5.2 节新增字段，不能照此树再造一份重复 schema。

```text
sealed L1
├── source_snapshot
│   ├── source hash
│   ├── package/part inventory
│   └── parser/schema version
├── source_atoms
│   ├── unified source sequence
│   ├── kind
│   ├── content/value
│   └── source locator
├── body_content_index
│   ├── paragraph/table/row/cell/run/object
│   ├── container membership and body order
│   └── merge/nested/empty facts
├── global_document_fact_index
│   ├── section/page geometry/columns
│   ├── header/footer refs and inheritance
│   ├── field/break/page numbering
│   └── numbering definitions/document defaults
├── cross_domain_refs
│   └── body atom → section/numbering/field/break
├── text_address_space
│   ├── raw Run text
│   ├── stable character offsets
│   └── source text hash
├── formatting_facts
│   ├── direct formatting
│   ├── style inheritance
│   └── effective formatting
├── visual_bindings
│   ├── source/render hash and render engine/version
│   ├── PDF hash and actual page count
│   ├── clean page images
│   ├── annotated diagnostic images
│   ├── page layout and bbox/render target
│   ├── atom/object → page/bbox binding
│   └── render availability/error
├── locator_map
│   └── source atom/selection → OOXML execution address
├── indexes
└── coverage_and_unknowns
```

其中 `locator_map` 只用于内部执行和回查，不成为第二套业务身份。

## 7. Stage View 的共同契约

### 7.1 View 是筛选结果，不是新事实源

Stage View 由对应阶段的 view builder 基于 L1 查询结果生成，不属于 L1 自身的事实责任。它可以物化成独立 artifact，方便 replay、缓存、审查和模型调用，但必须明确：

- `view_of` 指向 sealed L1；
- 记录 L1 hash 和 source hash；
- 每项事实能回查 L1；
- view 内没有新的源事实权威；
- view schema 变化不改变源身份；
- 相同 L1 和相同筛选条件应得到确定性相同的事实内容。

View builder 可以做与呈现有关的筛选、排序、摘要、树形投影、分页和裁剪；这些结果只在该 view 内有效。它不能通过重新解析 DOCX 来补造 L1 缺失的事实，也不能把呈现派生物写回 L1 冒充源事实。

### 7.2 建议统一输入外壳

```yaml
artifact_type: t2_fact_view
view_version: "discussion-1.0"

source:
  l1_artifact: 01.5_l1_input_contract.json
  l1_hash: "..."
  source_template_hash: "..."
  source_render_hash: "..."

scope:
  kind: full_document
  source_selection:
    kind: atom_interval
    start:
      source_atom_seq: 1
    end:
      source_atom_seq: 2

facts: {}
visual_evidence: []

coverage:
  complete: true
  included_atom_count: 0
  omitted_atom_count: 0
  unbound_atom_count: 0

omissions: []
not_available_reasons: []
```

外壳中的字段名可以在正式 schema 中细化，但 `view_of`、hash、scope、facts、visual evidence、coverage、omissions 和 not-available reason 这些责任必须保留。

### 7.3 稳定文件与运行时传递方式

阶段输入采用“稳定 artifact + 运行时加载”两层方式：

1. 每个会影响阶段判断的结构化输入先物化为 JSON/YAML 文件并记录 hash、input refs、schema version 和 coverage；
2. 代码消费者可以把文件加载成内存对象，但不得在内存中补造一套未落盘的事实；
3. 模型消费者拿到同一份结构化 artifact；页面图片由运行器依据 artifact 中的 ref/hash 作为真实多模态附件上传，不能把本机路径字符串当作图片；
4. crop、分页窗口和递归子调用可以运行时生成，但必须记录父 artifact hash、scope、selection、omissions 和附件 hashes，才能 replay；
5. 阶段 final 只引用实际消费过的 input artifact hash，不能引用一份与真实模型输入不同的“展示文件”。

各阶段的输入形状和完整性指标固定如下：

| 阶段 | 稳定输入 artifact | 取自哪类数据 | 主要内容 | 必须记录的指标/状态 |
| --- | --- | --- | --- | --- |
| T2 | 保留 `01.6_t2_l1_stage_input.json`；实际模型输入保留 `02.1_t2_input.json` | 正文 + 全页 render + 最小 section/break 全局事实 | document summary、ordered `page_packets[]`、clean image ref、页面 content blocks、显著格式、break facts、source/atom bindings、omissions | atom/block/page count、page image availability、content-binding coverage、unbound/omitted count、render status |
| T3 | `03.0_t3_hierarchical_stage_input.json` | T2 final unit scope + 正文结构/原子 + unit 页面图/crop | contract hashes、`unit_roots[]`、层级 `nodes[]`、parent/child/member refs、source selections、run/char facts、visual evidence、neighbor context | selected/included atom count、children/content/visual complete、unbound/omitted members、unit coverage、`tree_hash` |
| T4 | **本轮暂缓**；保留当前 `01.8_t4_l1_stage_input.json` 及现有 consumer，不新增、不改名 | 本轮不展开；只要求 T1/L1 兼容当前读取 | 不形成新的 T4 输入设计 | 只做“不破坏现有 consumer”的兼容检查，不进入本轮质量验收 |
| T5 | 直接读取 `02_unit_map.yaml`、`03_element_spec.yaml`、`04_global_spec.yaml` 和 L1 identity/hash lookup | 上游 final，不再读取全文 view | availability、lineage、unit-element-section refs、conflicts、review flags | final/hash/ref 一致性、缺失/冲突数、review flag count |
| T6 | 原始 source DOCX + `05_template_spec.yaml` + `01.5_l1_input_contract.json` resolver | 原文件 + 动作语义 + locator | source selections、preconditions、locators、actions、output refs | action count、identity/locator resolution success/failure、precondition failure、observed effect count |
| T7 | T6 DOCX/manifest + T1/L1 基线 + T2–T5 finals + fresh final render | 全链路证据 | expected/observed、first bad stage、owner、root cause、fresh output facts | status、finding count、stage availability、hash/ref integrity、coverage residuals |

当前实现已经稳定物化 T2、T3 的主要输入和 T4 的 L1 兼容输入。本轮不继续讨论或处理 T4 model evidence 是否单独落盘；只冻结并保护现有 `01.8_t4_l1_stage_input.json` 消费关系。

### 7.4 所有 Stage View 的不变量

1. 不重编号源原子。
2. 不修改 authoritative source content。
3. 不生成新的物理父子关系。
4. 不把 code candidate、AI observation、gold 或 judge 放进事实视图。
5. 省略必须显式记录，不能用摘要代替完整性声明。
6. Code 和 AI 候选必须读取同一份事实视图或同一 L1 hash 下等价视图。
7. 视觉输入必须真正传递图片内容；只有本机路径不算视觉证据。
8. 上下文只能帮助理解，不能让当前阶段认领 scope 之外的源内容。

## 8. T2 应获得的事实视图

### 8.1 T2 的任务

T2 根据源事实识别模板单元、顺序、边界和分页语义。

T2 需要全文视角，但通常不需要一次看到每个 raw Run 的全部属性。T2 的主入口应是页面图片；结构化事实树是与图片位置绑定、可继续展开的精确证据。

### 8.2 建议的呈现方式

```text
T2 full-document segmentation view
├── ordered page images
├── page summary and atom bindings
├── ordered physical blocks
│   ├── paragraph summary
│   ├── table summary
│   └── source object summary
├── section/break/page facts
├── significant formatting facts
└── coverage/omissions
```

### 8.3 T2 应包含

- 源文档总 atom/block/page 数；
- 物理 block 的确定性全文顺序；
- 每个 block 的物理 source selection；
- paragraph/table/object 类型；
- 完整可见文字或明确标记的摘要；
- 显著段落和字符格式；
- 真实 page、页面首尾 source atom；
- section 和 break 对应的 source atom 位置；
- 表格尺寸、是否跨页和必要结构摘要；
- source object 的类型、锚点和可见摘要；
- 所有页面图片或明确的视觉缺失；
- 全文覆盖、缺失和 unbound 成员。

### 8.4 T2 应过滤

- 不参与单元边界判断的完整 Run 属性明细；
- 字符级执行 locator；
- T3 policy、role、fill source；
- T4 最终布局策略；
- 任何 code_raw unit 结果、gold 或标准。

### 8.5 T2 输入构造允许做什么

T2 view builder 可以：

- 压缩样式字段；
- 把完整结构按阅读顺序呈现；
- 为大文档按页面分片；
- 附加页面图片；
- 生成纯展示用途的 page/block summary。

但 page membership、break/source 对齐和结构成员关系应已经存在于 L1，不应由 T2 临时恢复。T2 从图片定位到事实树的 page/bbox/atom 映射也必须来自 L1，而不是 T2 自己猜。

## 9. T3 应获得的事实视图

### 9.1 T3 的任务与额外依赖

T3 根据 T2 final 划定的 unit source selection，对 unit 内源内容判断元素策略。

因此：

```text
T3 input
= T3 view builder 从 L1 查询得到的中立事实
+ current run's T2 final unit source selection
```

T2 final 提供 unit scope。T3 view builder 再从 L1 查询该 scope 内的物理事实，组织成适合 T3 判断的层级输入。它可以投影和组织事实，但不能重新解析 DOCX 或补猜 L1 没有保存的源事实。

### 9.2 哪些内容必须提前存在于 L1

- paragraph、table、row、cell、run 和 source object 的物理关系；
- 上层结构对象的有序物理成员；
- merge、nested、empty 和 field 的物理起止位置；
- raw Run 文字、字符坐标和样式；
- source object anchor、page 和 bbox；
- 每个物理容器的 child/member 完整性；
- 页面图片和视觉可用状态；
- raw Run 的稳定字符地址空间和源文本 hash；
- 面向上述物理关系的中立查询索引；
- source atom、字符位置、物理结构节点、page/bbox 和渲染图片之间的绑定。

当前 T3 输入构造中的工作需要拆成两类：

- 读取平铺数据后重新发现 table/cell/paragraph/run 关系或 source object，说明 T1 原始解析不足；重新补完整性汇总、统一引用或视觉绑定，说明 L1 技术字段不足；
- 按 unit scope 查询、投影层级、摘要样式、选择图片裁剪和构造候选 span，属于 T3 view builder，可以保留在 T3。

判断标准不是“这段代码现在位于哪个 builder”，而是它在恢复源事实，还是在为 T3 组织问题。

### 9.3 T3 在 T2 后可以新增什么

- unit wrapper；
- unit 对应的 source selection；
- 根据 T2 unit selection 对 L1 结构和页面图片做选择、裁剪；
- 将中立物理关系投影成 T3 需要的层级 view；
- 基于稳定字符地址构造 view-local candidate span；
- previous/next unit context；
- 因 T2 边界造成的 contested、partial 或 missing membership；
- T3 决策所需的 view-local target ref；
- T3 policy、role、evidence 和 element materialization。

这里的“裁剪”和“层级投影”只改变当前输入展示，不重新解析或重建源事实。结构关系、图片和 binding 必须能从 sealed L1 查询；candidate span 可以由 T3 view builder 生成，但必须完全引用 L1 的 `source_atom_seq + char offsets`。

### 9.4 建议的呈现方式

```text
unit wrapper
├── selected page image / crop
│   └── page/bbox/source_atom_seq bindings
├── projected paragraph node
│   └── L1 raw Run / character-addressable content
├── projected table node
│   └── row → cell → paragraph → Run
└── projected source object node
```

这里的 `unit` 来自 T2；下层结构来自 L1。为了递归调用生成的 target handle 是当前 view 的寻址句柄，不是新的源业务身份。

### 9.5 span 的边界

span 需要按“是否依赖 T2 unit 或 T3 policy”分层：

- raw Run 必须由 T1 忠实解析；稳定字符地址、offset 规则和 source text hash 由 L1 确定性增加；
- policy-neutral candidate partition 可以由 T3 view builder 按当前 unit 和输入预算生成，它是 view-local 呈现，不是 L1 源事实；
- T3 可以基于语义确认或调整 split，但结果必须引用既有 `source_atom_seq + char offsets`，不能创建新的源身份；
- Fill、Delete、Keep 等带策略含义的 span 必须等待 T3，既不能进入 T1，也不能进入 L1。

因此，前移到 L1 的是字符内容、稳定坐标和可执行定位能力，不是某一套预先切好的 atomic span。L1 让 T3 能切、能查、能执行，但不替 T3 决定怎样切。

## 10. T4 应获得的事实视图

> **本节暂缓。本轮只把以下内容当作现有 consumer 边界记录，不据此新增 T4 artifact、字段、指标、测试或验收任务。**

### 10.1 T4 的任务

T4 根据客观 section、page、header/footer、numbering、field 和视觉事实形成全局版式规则。

T4 是相对独立的全局判断阶段，默认不依赖 T2 unit 或 T3 element 结果：

```text
T4 input
= L1 global_document_fact_index
+ L1 visual_page_index
+ 必要的 body boundary anchors
```

全局事实必须由 T1 在原始解析时独立归类，再由 L1 合并、绑定和索引；不能先混入正文内容流，再让 T4 从完整正文中重新识别全局对象。

### 10.2 建议的呈现方式

```text
T4 global-layout fact view
├── global document summary
├── section boundaries and source refs
├── page geometry
├── margins/orientation
├── header/footer references and content
├── field and page-number facts
├── numbering definitions
├── break/page bindings
├── page images/layout index
└── minimal source anchors
```

### 10.3 T4 应包含

- section 的物理 source selection；
- page size、orientation、margin 和 columns；
- header/footer part、引用关系和有效继承；
- header/footer、page-number 及其他全局 field 的 instruction、显示结果和源位置；
- numbering definition 和引用；
- break 位于哪个 source atom 之前或之后；
- 真实页面图、页数、page layout 和视觉绑定状态；
- 必要的短文本锚点用于定位。

### 10.4 T4 应过滤

- T2 unit 判断；
- T3 element policy；
- 完整 body flow、正文 table/cell/run 明细；
- 与全局边界无关的正文语义和内容摘要；
- 学校标准和最终合格性结论。

T1 负责解析全局对象及其原始物理关系；L1 负责 section、break、header/footer、field、numbering 与 source atom/page 的统一绑定。T4 只在此基础上形成布局语义。

## 11. T5、T6 与后置验证的输入边界

### 11.1 T5：只合并上游 Final

T5 的业务输入应是：

```text
T2 final + T3 final + T4 final
+ L1 hash/identity lookup for validation
```

T5 不需要获得另一份全文事实视图。它只能做：

- hash 和身份一致性校验；
- unit-element-section 绑定；
- 上游 availability 和 flag 保留；
- 合并冲突和 review flag。

T5 不能重新阅读 L1 文本或视觉事实补猜 unit、policy 或 layout。

### 11.2 T6：读取原始 Word 执行，不是第四套筛选视图

T6 的业务输入应是：

```text
原始 source DOCX
+ T5 final
+ L1 source atom/selection → OOXML locator/resolver
```

三者分工是：

- 原始 source DOCX 提供真正要被修改的完整内容；
- T5 final 说明需要执行什么动作、作用于哪些 `source_atom_seq`；
- L1 resolver 把这些原子准确定位回同一 source hash 下的 OOXML 节点。

L1 resolver 至少应支持：

- source atom/selection → OOXML locator；
- source selection → paragraph/table/cell/object；
- Run/character range → 可执行文字位置；
- source package hash 校验；
- action scope 和父容器校验；
- 无法精确绑定时返回结构化失败。

T6 必须打开原始 DOCX 才能修改它；它不需要一份像 T2/T3/T4 那样为判断任务裁剪的事实视图。T6 可以读取原始内容核对动作前置条件，但不能借此重新理解、重新分类或补猜 T2/T3/T4 的语义。

### 11.3 T7：强制的 post-T6 验证阶段

当前项目部分代码和 canonical 文档把 T6 后的验证产物命名为 `T7`，例如 `07_verification_report.json`。这个编号可以保留。需要区分的是：

- T1、T2、T3、T4、T5、T6 是六个业务生成阶段；L1 是 T1 与 T2 之间的技术合并层，不另算一个 T 阶段；
- T7 是强制的 post-T6 验证阶段；
- 完整流程必须经过 T7，T7 失败或不可用时不能把生成结果声明为完成。

因此，完整流程口径是：

```text
T1 原始解析 → L1 技术合并 → T2 → T3 → T4 → T5 → T6
                                                  ↓
                                     T7 / post-T6 verification（强制）
```

后置验证需要：

- sealed L1 结构与视觉事实基线；
- T2/T3/T4/T5/T6 canonical final 和 hash refs；
- T6 actions、preconditions 和 manifest；
- 最终 DOCX 的 fresh observation；
- expected vs observed、owner 和 first bad stage 规则。

它重新观察最终 Word 是验证职责，不属于重新构建上游事实输入，也不是面向业务生成判断的 Stage View。`T7` 和 `07_` 可以继续作为流程与产物编号；“六阶段”只用于描述业务生成阶段数量，不能被解释成验证可选。

### 11.4 POST_T6 质量判断

POST_T6 的质量判断主要读取最终 Word 和学校签收标准。L1 只用于 trace 和 owner 归因，不能代替最终 Word 观察，也不能把学校标准写回事实层。该步骤是 T7 的组成部分，不是 T7 之后又一个可选阶段。

## 12. 三套筛选视图何时生成

只有 T2、T3、T4 有 Stage View。需要区分两件事：

1. **L1 能力就绪**：无损源事实、物理关系、raw Run/字符地址、object、样式、完整性、图片、binding、查询索引和 locator 必须在 L1 sealed 前准备并验证；
2. **Stage View 构造**：按阶段任务查询、筛选、摘要、树形投影、候选 span、裁剪和 artifact 物化，由对应阶段的 view builder 在需要时完成。

| View | 最早生成时点 | 原因 |
| --- | --- | --- |
| L1 neutral facts/indexes | L1 sealed 前必须就绪 | 保证原始内容不丢失、可查询、可定位 |
| T2 fact view artifact | T2 开始时由 T2 view builder 生成 | image-first 组织是 T2 的输入呈现责任 |
| T4 fact view artifact | T4 开始时由 T4 view builder 生成 | 从独立全局事实域、visual facts 和最小正文锚点构造，不等待 T2/T3 |
| T3 unit-scoped view artifact | T2 final 后由 T3 view builder 生成 | unit selection 来自 T2；层级投影和 candidate span 服务于 T3 |

这里的关键区别是：

- **源事实、查询和定位能力**必须在 L1 完整；
- **怎样把问题呈现给某阶段**由该阶段负责；
- **语义判断**必须留在拥有该判断的阶段。

T5 不需要事实筛选视图；它合并 T2/T3/T4 final。T6 不需要事实筛选视图；它读取原始 DOCX、T5 final 和 L1 resolver 执行修改。T7/post-T6 verification 强制读取成品重新观察，但不属于生成阶段的 Stage View。

## 13. 当前实现与目标边界的初步差距

本节只用于支持讨论，不是正式状态或实施计划。

### 13.1 已经对齐的部分

- 主流程已经在 T1 之外调用 `build_template_agent_render_packet`，通过 LibreOffice 把 Word 转成 PDF，再通过 Poppler 生成 clean page PNG、页面布局、source binding 和 annotated SVG，之后封存进 L1；
- 当前 L1 `visual_page_index` 已包含 `render_status`、`source_render_hash`、render engine/version、PDF path/hash、page count、clean/annotated page images、page layout 和 binding summary；
- T2 最近的输入方向已经以页面图片为主，再回查结构和样式，符合 image-first 原则；
- T3 hierarchical input 已按 unit 页码选择 clean page images，并记录 `visual_complete`；
- T4 agent 路线已有独立 `build_t4_evidence`，会同时读取全局版式事实、全部 clean page images 和 page layout；没有 real render 时会对视觉子范围显式 abstain；
- T2/T4 生产路径读取 L1 派生输入；
- L1 已有独立 `layout_fact_index`，T4 stage input 也不依赖 T2/T3 final，说明全局独立路线已有实现基础；
- T3 已要求 sealed L1 + T2 final；
- T3 hierarchical builder 已负责 unit-scoped 层级投影和 atomic span，责任位置与目标边界一致；
- T5 已只合并 T2/T3/T4 final；
- T6 动作已由 T5 final 驱动并使用 L1 做身份校验；
- T7 验证器会在 T6 后重新观察最终 Word。

### 13.2 尚未对齐的部分

- T1 的可见 flow 仍偏向文字块，不等于全部底层源原子；
- 当前 `source_seq` 仍只覆盖较高层正文流；它可以继续作为 T1 兼容字段，但 L1 尚未新增叶子级 `source_atom_seq` 和两者的映射；
- L1 已有多个事实索引，但还没有按身份讨论稿形成统一源原子覆盖；
- identity、source selection、character range、locator 和 visual binding 仍分散在不同字段中，转换和一致性校验契约尚未收敛；
- 客观结构分散在 body flow、tables、paragraphs、run index 和对象索引中；
- T1 已在 `data` 中保存 sections、headers/footers、fields、breaks 和 numbering，但 header/footer 等内容仍可能进入可见 `body_flow`，全局域与正文域尚未完全分离；
- T2/T4 仍通过兼容层重建部分 document facts，而不是只查询 L1 后组织 stage view；
- 当前 `01.8_t4_l1_stage_input` 仍复用完整 document-facts-shaped view且不直接包含 `visual_page_index`；另一条 agent evidence 路线才组合全局事实与页面图。目标上应把两条输入口径收敛为正式的 `layout_fact_index + visual_page_index + minimal body anchors` T4 view；
- T2 生成 page summary 属于合理的 view 组织；但如果仍需补算 page membership、break/source 物理对齐，则说明 L1 事实或索引不足；
- 页面图片虽然已经进入流程，但 source hash 没有作为 `visual_page_index` 的显式一等字段；`source_render_hash`、PDF/image 完整性、旧缓存隔离和 page/bbox/atom 完整绑定仍未形成统一闭环；
- 当前真实 render 已记录固定的 pipeline version，但尚未记录 LibreOffice、Poppler 等实际工具版本，跨环境复现和视觉差异归因仍不足；
- clean/annotated page image 目前主要以文件 path 进入 artifact；必须继续验证每个模型调用是否把图片作为真实多模态附件传入，而不是只把路径放进文本；
- T2 已把 `real_render` 设为正式 AI 路线的前置条件，T3 已按 unit 选择图片，T4 也已有视觉子范围 abstain；仍需把三者的图片完整性、真实附件传递和统一 availability 契约收口到正式 Stage View；
- T3 从 L1 rows 组织 unit tree 本身应保留；但其中若仍需解析编码式 cell ID 或推断 merge/nested/empty 等物理事实，这部分说明上游事实表达不足；
- L1 尚未形成足以支持 T3 自主生成 candidate span 的统一字符地址和 locator 契约；
- field ownership、merge、nested、empty cell 和 object binding 尚未完整；
- T6 resolver 目前更偏身份校验，实际定位仍有执行层自行解析的部分；
- 内部仍存在允许没有 sealed L1 packet 时重新构造 L1 的兼容入口。

### 13.3 优化原则：保留现有能力，只调整 owner、缺口和重复推导

目标边界不是要求重做整个链路。当前能力应按以下方式处理：

| 当前能力 | 当前状态 | 优化方式 |
| --- | --- | --- |
| T1 DOCX/OOXML inspector | 已能解析 body flow、Run、段落、表格、对象、样式、source ref，并产生 warnings/unknown | 保留解析器；补齐遗漏对象和物理关系；把统一 identity/index 的最终 owner 收敛到 L1 |
| 现有 `source_seq` 及下游引用 | 已被 T2-T6、报告和人工沟通广泛使用 | 名称、数值和粒度保持不变；L1 新增 `source_atom_seq` 与双向映射；本轮阶段输入继续输出 `source_seq`，下游 identity 切换另行立项 |
| `01.5_l1_input_contract.json` | 已合并 source text、run、object、structure、layout、visual page 和 coverage | 保留 L1 contract/builder；在现有结构上补统一身份覆盖、字符地址、locator map 和完整 binding |
| `build_template_agent_render_packet` / render pipeline | 已实现 Word→PDF→clean PNG，并生成 annotated SVG、page layout 和 source binding | 整体保留，不另建渲染子系统；把它从 agent 辅助产物提升为 T1/L1 基础阶段的正式 render facts producer，补真实工具版本、逐页 hash、缺页校验和缓存隔离 |
| L1 `visual_page_index` | 已封存 render status/hash、engine/version、PDF path/hash、page count、clean/annotated images、page layout 和 binding summary | 保留字段和 builder；补显式 source hash、逐页完整性、atom/object binding coverage，并规定下游拿到真实图片附件 |
| T2/T4 stage input builders | 已从 L1 构造阶段输入 | T2 保留现有序列化 shape，只把事实来源收口到新 L1；T4 本轮只验证兼容，不修改 builder 目标 |
| `layout_fact_index` 与 T4 独立路线 | 已有 sections、headers/footers、fields、breaks、numbering，T4 不依赖 T2/T3 final | 保留并深化；T1 明确分离全局事实域，T4 input 改为全局索引、visual facts 和最小正文锚点 |
| T3 hierarchical input 与 atomic span | 已基于 sealed L1 + T2 final 构造层级树，并在 T3 生成 span | 保留这一层；缺失的源物理事实由 T1 补解析，统一引用、查询和 binding 由 L1 补齐 |
| `L1IdentityResolver` | 已能校验 source hash、source/run 引用和字符范围 | 本轮保持现有执行行为；L1 新 locator 先形成只读事实索引，T6 resolver 切换另立后续计划 |
| T7 verifier | 已在 T6 后重新观察最终 Word | 保留为强制验证阶段 |

推荐的改动顺序是：

1. 先标出当前字段的真实 producer、consumer 和兼容依赖；
2. 在现有 L1 contract 中补字段和校验，不先改下游接口；
3. 只改 T2/T3 stage-input projector 的事实来源，保持现有序列化 shape、模型附件和业务输出；T4 只做兼容，T5/T6/T7 不切换身份；
4. 用当前 T2–T7 输出契约、代表性真实样本和 replay 证明“上游事实归位、下游输入不变”；
5. 删除重复的上游事实 producer；不在本轮删除下游兼容字段或切换 T6 resolver；
6. 只有 T1/L1 schema、stage-input projector 切换和下游不变验证全部闭环后，才迁移 canonical gold 与 gold projector。

在前五步期间，现有 gold 只能作为冻结的回归裁判和差异证据，不能作为生成输入，也不能反向规定新的 T1/L1 事实 schema。gold 迁移必须保留旧字段到新字段的可审计映射、人工确认来源和迁移前后差异。

任何优化都应满足：已有能力继续可用、artifact 可回放、现有阶段输入保持兼容、每一步都有等价性或增量能力验证。下游 identity/locator 切换不是本轮完成条件。

## 14. 本轮核心结论与剩余待决项

以下结论已经进入本讨论稿，但尚未迁入 canonical 架构或实现。

### 14.1 本轮已经明确

1. T1、L1 和 T2/T3/T4 是三个不同责任层：原始解析、技术合并、阶段组织与判断；
2. T1 基础事实对外分成正文、全局、render 三份稳定 component；`01_document_facts.json` 作为现有 T1 final/兼容 bundle 保留；sealed L1 是增加统一技术字段后的唯一下游事实入口；
3. T1 不新增统一业务字段；L1 可以新增确定性技术字段，但不能改变源内容或新增语义；
4. T2、T3、T4 的 view builder 可以查询、筛选、摘要、投影和裁剪 L1 事实，但不能重新发现源事实；
5. T3 只等待 T2 unit scope；L1 提供物理关系、raw Run/字符地址、source object、完整性和图片绑定，T3 自己组织层级 view 和 candidate span；
6. T5 不读取 L1 做语义补猜；
7. T6 的输入是原始 DOCX、T5 final 和 L1 resolver，它可以打开 DOCX 执行动作，但不能重新判断语义；
8. T7 是六个业务生成阶段之后的强制验证阶段，可以继续使用 T7/`07_` 流程编号；
9. L1 只建立一套 `source_atom_seq`；本轮 T2/T3 Stage View 可以继续输出现有 `source_seq`/run/object 引用，是否对外切换为 atom selection 另行立项；selection、character range、locator 和 visual binding 不能成为并列身份；
10. 页面图片和结构化事实共同构成同一源快照的权威证据；render 过程生成页面图，L1 负责与 T1 facts 合并和绑定；
11. T2 默认 image-first，再沿视觉绑定回查事实树和样式；
12. T1 必须把正文事实域与全局事实域分开；L1 保持分域并增加跨域索引；T4 独立读取全局事实、visual facts 和最小正文锚点。
13. Word→PDF→clean page images 是 T1/L1 基础阶段必须准备的正式输入链路；annotated images 只用于诊断，crop 只是 Stage View 的派生视图，二者都不产生新的源身份；
14. T7 对最终 DOCX 的重新渲染属于成品验证快照，必须使用独立的 final render hash，不能与源模板的 `source_render_hash` 混用。
15. T1/L1 优化必须以第 2.7 节的现行阶段输入输出为迁移基线；尚未实施的未来阶段设计不能提前改变本轮 consumer contract；
16. gold 必须在 T1/L1、stage-input projector 切换和现行消费者不变验证完成后再修改，不能与事实层 schema 同步漂移。
17. 源内容原子固定为最小可独立引用/校验/执行的 OOXML 叶子 occurrence；字符使用原子内区间，结构容器不获得并列原子身份；
18. 现有 `source_seq` 不改名、不改粒度；L1 新增 `source_atom_seq` 和兼容映射；
19. T2/T3 的实际判断输入必须稳定物化并可 replay；模型图片由 artifact ref/hash 加载成真实附件；T4 本轮只保留现有兼容边界。

### 14.2 需要结合身份讨论稿继续裁定

1. 五类原子到全部受支持 OOXML 节点的完整映射表；
2. 附属 part、浮动对象和 unknown 的完整稳定排序枚举；
3. `body_structure`、`global_structure` 和 `source_membership_index` 的精确 schema；
4. normalized properties 第一版白名单与 raw-fact completeness 规则；
5. view-local target handle 的合法形状；
6. raw Run 字符坐标、Unicode 单位、源文本 hash 和 selection locator 的精确 schema；
7. 单点、连续区间、非连续成员和 character span 的 selection schema、展开及完整性规则；
8. locator map 的字段和可复现规则；
9. Stage View artifact 的缓存、版本和 replay 规则；
10. body/global 的完整分类表，以及 shared styles、body field occurrence 和跨域引用怎样表达。

## 15. 建议的讨论顺序

建议下一轮按以下顺序讨论，避免身份、结构、视图和实现同时混在一起：

1. 冻结第 2.7 节中的现行 producer、consumer、artifact 与核心字段，并补齐长期架构文档和实现之间的已知漂移；
2. 把第 5.1 节三份 T1 component 的字段表补成正式 schema，并确认 `01_document_facts.json` 兼容 bundle 形状；
3. 把五类原子映射到完整 OOXML 节点枚举，补齐跨 part 排序；
4. 定稿结构节点表、成员索引、normalized properties、字符地址和 locator schema；
5. 定稿 L1 新增字段、现有字段增量和逐项 producer/consumer；
6. 逐一确认 T2、T3 稳定输入 artifact 的字段、过滤、指标和真实附件传递；T4 只做现有 consumer 兼容检查；
7. 确认 T5、T6 和强制 T7/post-T6 verification 继续使用现有输入和 resolver，只做兼容回归；
8. 形成一份 T1/L1 schema、stage-input compatibility、测试与真实样本验收计划；
9. 完成 T1/L1 和现有阶段输入兼容验证后，最后再形成并执行 gold migration。

在前七项定稿以前，不建议继续通过给某个下游 builder 增加局部字段来补齐事实底座；在第八项闭环以前，不修改 gold。
