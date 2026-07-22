# T3 Stage Input 分层结构重构（讨论稿）

> Status: discussion draft  
> Scope: 模板生成 T3 Stage Input 的结构、身份、父子关系、完整性和迁移边界  
> Related output discussion: [`t3-ai-hierarchical-output-principles-discussion.md`](./t3-ai-hierarchical-output-principles-discussion.md)  
> Canonical target: 讨论定稿后迁入 `docs/current/template-generation-architecture.md` 的 T3 输入章节  
> Non-goal: 本文不确定 T3 AI 的最终输出枚举，不规定 prompt 文案、类名、函数名或实施步骤。

> Discussion state: 本文用于结合新的 T3 AI 分层输出原则重新讨论 Stage Input。当前内容不是正式契约，也不表示现有生产输入已经完成迁移。

## 1. 为什么需要单独讨论输入

T3 AI 输出准备采用稀疏递归决策：在能够统一判断的最粗节点停止，只在 `split` 时沿稳定子节点继续下钻。这个输出契约要求输入不再只是“单元摘要 + source_seq 窗口 + run 列表”，而要提供一棵可校验、可递归引用的结构树。

输入讨论与输出讨论需要分开：

- 输出文档回答 AI 输出 Keep/Fill/Delete/Split 的含义、何时停止以及如何继承；
- 本文回答 AI 能看到哪些节点、节点如何引用、父子关系从哪里来、证据是否完整以及当前输入怎样迁移；
- 输出契约不能要求输入不存在的层级；输入也不能提前写入 T3 的 Keep/Fill/Delete 判断。

## 2. 当前生产输入概况

当前 T3 输入分为两层：

```text
T2 unit window
  → unit overview + table/text-flow object summaries
  → conditional local windows
  → source_seq/paragraph/cell rows
  → raw/logical run facts
```

当前已经存在的主要信息包括：

- T2 提供的 unit id、source 范围、页面和相邻单元；
- table/text-flow 对象任务与对象摘要；
- 表格行摘要、cell id、文字、样式和候选区域；
- source_seq、source_ref、paragraph id、table id、cell id；
- raw/logical run id、文字和有效样式；
- source object facts 与页面图片引用。

当前主要缺口是：这些信息尚未组织成统一的节点树；部分 row/cell 只是摘要字段，未必是可递归引用的正式节点；大对象可能只展示代表性内容；也没有统一表达节点成员是否完整、是否截断和是否存在未绑定成员。

## 3. 目标能力

T3 Stage Input 应当允许编排器和 AI：

1. 从每个 T2 unit 的根节点开始判断；
2. 引用系统已经提供的稳定节点，不能自造身份；
3. 读取节点的直接子节点，并且只沿直接子节点继续下钻；
4. 在 table/paragraph 等粗节点完整可见时进行整体判断；
5. 在节点包含混合动作时继续到 row/cell/paragraph/run，必要时才到 span；
6. 判断当前证据是否完整，避免用局部摘要覆盖整个对象；
7. 让程序确定性展开完整 atomic coverage；
8. 保持 L1 是事实与身份底座，T3 Stage Input 只是针对当前 route 的派生视图，不成为第二事实源。

## 4. 候选节点树

首版候选结构是：

```text
unit
├── paragraph
│   └── run
│       └── span（仅系统可稳定表达时）
├── table
│   └── row
│       └── cell
│           └── paragraph
│               └── run
│                   └── span（仅系统可稳定表达时）
└── source_object
    └── 系统能够可靠表达的子节点
```

这不是已经批准的最终层级。需要继续讨论：

- table 的直接子节点固定为 row，还是允许稳定的语义 row-group；
- cell 下是否始终保留 paragraph 层，还是简单 cell 可直接到 run；
- header/footer、脚注、文本框、内容控件、公式、图片和嵌套表格如何进入树；
- span 是输入预生成节点，还是只在 run split 后按坐标临时构造。

## 5. 每一层到底给模型什么

分层输入不应把整棵 Word 树和全部 run 一次性塞给模型。候选原则是“当前节点完整信息 + 直接子节点足够做路由的摘要 + 必要邻近上下文 + 真实视觉证据”：

```text
当前节点
├── 自身身份、范围、完整性和客观事实
├── 直接子节点列表及摘要
├── 当前节点和必要邻近上下文的文字/样式/结构
└── 当前范围的页面图、对象 crop 或局部 crop
```

模型在当前层只决定终局动作或 `split + inspect_child_refs`。只有被选中的直接子节点进入下一次调用；下一层再提供更细信息。

### 5.1 所有层共有的输入外壳

每次调用都应包含 contract、target、completeness、facts、children、context 和 visual_evidence：

```jsonc
{
  "contract": {
    "l1_hash": "...",
    "t2_route": "ai_raw",
    "t2_hash": "...",
    "stage_input_version": "...",
    "prompt_contract_version": "..."
  },
  "target": {
    "ref": "...",
    "source_kind": "...",
    "parent_ref": "...",
    "ancestor_refs": ["..."],
    "source_refs": ["..."],
    "page_nos": [1],
    "bbox_refs": ["..."]
  },
  "completeness": {},
  "facts": {},
  "children": [],
  "context": {},
  "visual_evidence": []
}
```

共同约束：

- `facts` 只放客观事实，不放 Keep/Fill/Delete 预判；
- `children` 只列直接子节点，且每个 child 都有稳定 `ref`；
- `context` 只帮助理解，不允许模型跨范围认领；
- `visual_evidence` 必须能对应当前 target 或 child，不能只给无法定位的文件路径；
- 输入发生裁剪、摘要或图片缺失时必须写入 `completeness`。

### 5.2 Unit 层

Unit 层要回答：整个单元是否能统一结束；如果不能，哪些直接对象需要继续检查。

| 输入类别 | Unit 层提供什么 |
| --- | --- |
| 身份与范围 | unit ref/id、T2 route、source/page 范围、前后相邻 unit 摘要 |
| 完整文字 | 单元内按 Word 顺序排列的全文或完整文本 outline；若只能摘要，必须标记截断 |
| 直接子节点 | paragraph、table、source_object 的 ref、类型、顺序、页码、bbox、文字摘要和完整性 |
| 样式摘要 | 每个直接子节点的段落样式、主字体/字号、粗体、对齐、缩进、表格样式等显著差异；不发送全部 run 样式明细 |
| 结构摘要 | 对象数量、表格尺寸、段落数量、对象顺序、跨页关系和非正文对象存在事实 |
| 视觉 | 覆盖整个 unit 的真实页面图；必要时附 unit crop 或跨页分片 |
| 上下文 | 前后 unit 的 id、类型和短文本摘要，只作理解证据 |

Unit 层不默认发送每个 run 的完整样式和字符范围。它应足以判断整个 unit 是否都是 Keep、是否包含多种对象语义，以及哪些 table/paragraph/source_object 需要继续检查。

如果 unit 跨多页，不能因为图片数量限制只发送代表页却仍宣称 `visual_complete=true`。候选做法是发送所有页、分页观察后聚合，或明确视觉不完整并禁止依赖缺失页面做整体终局判断。

### 5.3 Table 层

Table 层要回答：整张表格的全部内容是否能统一处理；如果不能，哪些 row/cell 需要继续检查。

| 输入类别 | Table 层提供什么 |
| --- | --- |
| 身份与范围 | table ref、所属 unit、source refs、页码和跨页范围 |
| 完整文字 | 按 row/cell 顺序排列的表格全部可见文字；不是只给若干代表性行 |
| 直接子节点 | 首选 row refs；每个 row 摘要包含 cell refs、文字、空白情况、合并关系和页码 |
| 样式摘要 | table style、边框、底纹、列宽、行高，以及 row/cell 内显著文字样式差异 |
| 结构事实 | 行列数、合并单元格、嵌套表格、多段落 cell、重复表头和跨页断点 |
| 视觉 | 整张表格 crop；跨页表格提供每页 table crop，并保留同一 table ref |
| 上下文 | 表格前后标题/说明的短文本和位置，只作理解证据 |

如果整张表是打印后人工填写或签署的工作区，可以终局 Keep。如果表格结构保留但某些字段需要系统 Fill，table 必须 Split，不能因为“表格要保留”而终局 Keep。

大表不能只给代表性行后允许整体终局判断。可讨论两种方案：完整 row 摘要进入一次调用；或者先做分片事实摘要，再用覆盖全部 row 的只读聚合输入判断，并明确摘要完整性和来源。

### 5.4 Row 层

Row 层候选输入包括：

- row ref、所属 table、行号、页码和 bbox；
- 当前行完整文字；
- 直接 cell refs，以及每个 cell 的完整文字、空白状态、合并/跨列关系；
- 行高、边框、底纹和显著文字样式；
- 当前 row crop；
- 相邻前后 row 的短摘要，标记为 context only。

Row 可以整体 Keep；只有整行构成一个明确、可整体替换的字段时才考虑整体 Fill。标签和值分布在不同 cell 时通常应 Split 到 cell。

### 5.5 Cell 层

Cell 层候选输入包括：

- cell ref、table/row 祖先、行列坐标和合并关系；
- cell 内完整文字和空白状态；
- 直接 paragraph refs、顺序及完整文字摘要；
- cell 边框、底纹、垂直对齐和宽度等结构事实；
- paragraph 的段落样式和显著 run 样式摘要；
- cell crop，必要时附所在 row crop 帮助理解标签和值关系。

Cell 可以在“整个 cell 就是一个学生值/系统值且边界明确”时整体 Fill。如果 cell 同时包含固定标签、说明和待填内容，应 Split 到 paragraph 或 run。

### 5.6 Paragraph 层

Paragraph 层候选输入包括：

- paragraph ref、所属 unit/table/cell、source_seq/source_ref；
- 完整 paragraph text；
- paragraph style、对齐、缩进、行距、段前段后、列表/编号和分页事实；
- 直接 raw/logical run refs；
- 每个 run 的完整文字和有效样式摘要；
- paragraph crop 或页面中带 bbox 的局部 crop；
- 前后 paragraph 的短文本和样式摘要，标记为 context only。

如果整段都是固定条款、标题或完整字段值，可以终局 Keep/Fill。段内存在固定标签、示例值和格式批注等不同动作时，才 Split 到 run。

### 5.7 Run 层

Run 层候选输入包括：

- raw run ref、logical run ref、所属 paragraph/cell；
- 完整、未改写的 run text；
- effective style：字体、字号、粗体、斜体、下划线、颜色、语言和字符级属性；
- OOXML/source ref、字符长度和可执行边界；
- run bbox 或可校验的视觉绑定；
- 同 paragraph 相邻 run 的文字和样式，标记为 context only；
- 系统已提供的可下钻 atomic span/字符范围（如果存在）。

Run 是精细判断层，不是默认层。只有 run 内仍包含不同动作且系统支持可验证字符范围时才 Split 到 span；否则混合 run 保守 Keep 或进入人工复核。

### 5.8 Span 层

如果首版支持 span，输入必须提供系统可校验的 `run_ref + start/end + text`，同时提供所属 run 的完整文字、左右上下文、有效样式和局部视觉证据。AI 不能自己创造没有输入坐标的 span。

### 5.9 Source Object 层

source_object 用于普通段落/表格树无法覆盖的对象。不同对象需要不同事实：

- 图片：图片内容本身、尺寸、页码、bbox、alt text 和周围文字关系；
- 文本框：完整文字、内部段落/run、位置、尺寸、环绕方式和真实 crop；
- 内容控件：控件类型、tag/title、当前内容、锁定状态和内部节点；
- 公式：对象引用、可见渲染图、可提取文本/MathML（若存在）和上下文；
- 页眉页脚/脚注：所属 section/page 范围、完整内容、字段和对象关系。

AI 只能沿系统已经稳定表达的子节点下钻；没有可靠子结构时只能整体判断或进入安全回退。

## 6. 图片和视觉证据如何进入输入

图片不是 JSON 里的一个本机路径。正式多模态输入应分成两部分：

```text
JSON evidence
  → visual_ref、page_no、target_ref、bbox、crop 类型、hash、完整性

model message attachments
  → 与 visual_ref 对应的真实 PNG/JPEG bytes
```

候选视觉对象：

```jsonc
{
  "visual_ref": "visual:table_01:page_02",
  "target_ref": "table:01",
  "kind": "object_crop",
  "page_no": 2,
  "bbox": [72, 180, 520, 680],
  "sha256": "...",
  "coverage": "full|partial",
  "reason": "完整表格第二页 crop"
}
```

| 判断层 | 主要图片 | 辅助图片 |
| --- | --- | --- |
| unit | 覆盖全部 unit 的页面图或 unit 分页 crop | 前后页缩略上下文 |
| table | 完整 table crop；跨页时每页一个 crop | 所在页面图 |
| row | row crop | table crop |
| cell | cell crop | row/table crop |
| paragraph | paragraph crop | 所在 cell 或页面 crop |
| run/span | 精确 bbox crop（如果可靠） | paragraph crop |
| source_object | 对象自身渲染图 | 所在页面或邻近文字 crop |

视觉输入必须满足：

- visual_ref 与 target/child ref 可追踪；
- 图片真实作为模型附件发送，不能只在 JSON 中提供路径；
- crop 不能裁掉判断所需标签、单位或邻接关系；
- 跨页对象必须说明哪些页已覆盖；
- 图片缺失、模糊、bbox 不可靠或只覆盖局部时，写入 completeness；
- text-only route 必须显式声明没有使用视觉，不能假装与 multimodal route 等价。

### 6.1 文字、样式和图片的职责

- 文字回答“写了什么”，用于固定内容、示例值、说明和字段语义判断；
- 样式回答“这些文字在 Word 中如何组织和强调”，用于识别标题、独立 run、格式说明边界和相邻内容关系；
- 图片回答“页面上看起来是什么结构”，用于表格整体、空白区、合并单元格、签字区、相对位置和跨页视觉关系。

候选原则是：每个层级默认提供完整文字和必要结构/样式事实；只要视觉会影响整体判断，就同时提供与当前范围对应的真实图片。不能把“有文字输入”当成不需要图片，也不能只靠图片替代稳定 Word 身份。

## 7. 节点最小能力

每个可递归判断节点至少需要表达：

```jsonc
{
  "ref": "table:student_info/row:02/cell:02",
  "source_kind": "cell",
  "parent_ref": "table:student_info/row:02",
  "child_refs": ["paragraph:p_0018"],
  "source_refs": ["word/document.xml:tbl[1]/tr[2]/tc[2]"],
  "member_leaf_refs": ["run:p_0018.r_001"],
  "facts": {},
  "completeness": {}
}
```

这里需要区分：

- `ref`：当前 Stage Input 中的稳定节点引用；
- `source_refs`：回查 L1/源 DOCX 的事实引用；
- `child_refs`：允许继续递归的直接子节点；
- `member_leaf_refs`：用于确定性 coverage 展开的叶成员摘要；
- `facts`：文字、样式、位置、表格关系和视觉绑定等客观事实；
- `completeness`：当前节点能否安全做覆盖全部后代的判断。

AI 不产生这些身份和关系，只能消费并引用。

## 8. 完整性与截断

节点整体 Keep 或其他终局动作会覆盖全部后代，因此输入必须说明当前节点是否完整。候选完整性字段包括：

```jsonc
{
  "children_complete": true,
  "content_complete": true,
  "visual_complete": true,
  "truncated": false,
  "unbound_member_count": 0,
  "omitted_child_count": 0,
  "completeness_reasons": []
}
```

需要继续确定：

- 哪些字段是 Stage Input builder 的确定性结论；
- 视觉不完整是否阻止文本上明确的整体 Keep；
- 大表 token 裁剪后能否提供摘要并保持 `children_complete=true`；
- 摘要可用于路由还是也可用于终局动作；
- 未绑定对象或缺失 run 身份时允许下钻到哪一级。

## 9. 事实边界

Stage Input 只提供客观事实和结构，不提前写入 T3 语义：

允许提供：

- 节点类型、父子关系和稳定引用；
- 文字、样式、表格坐标、页面、bbox；
- raw/logical run 与可验证字符范围；
- 字段、内容控件、图片、公式等对象事实；
- 图片/crop 引用及其可用性；
- 完整性、截断、未绑定和 coverage 事实。

不允许提供：

- Keep/Fill/Delete/Split 预判；
- 根据关键词生成的权威 policy；
- 用 gold 或学校标准回填当前输入；
- AI 应该在哪个节点停止的答案；
- 与 L1 并行的第二套权威 source/run/object 身份。

确定性低层信号是否允许作为非权威提示，以及如何避免它们变成隐式 policy，仍需讨论。

## 10. Route 与输入绑定

每条 T3 route 必须绑定：

```text
sealed L1
+ 对应 route 的 T2 unit_map
+ 同一份 T3 Stage Input builder contract
```

需要保证：

- code_raw、ai_raw、merged 使用同形节点树和同一 L1 身份；
- 不同 route 的 unit 范围来自各自对应的 T2 route；
- T2 route 不可用时，对应 T3 route 不借用其他 route；
- Stage Input 记录 L1 hash、T2 route/hash、builder version 和节点树 hash；
- replay/cache 在输入树或 prompt contract 改变时正确失效。

## 11. 当前输入迁移需要核实什么

迁移前需要逐项确认：

1. 当前 unit window、page_text_index、object_fact_index、run/style facts 分别从哪里产生；
2. 哪些身份已经属于 sealed L1，哪些仍是旧 render packet 的私有投影；
3. table/row/cell/paragraph/run 的父子关系是否完整、唯一且可回查；
4. 合并单元格、嵌套表格、多段落 cell 和跨页表格如何表达；
5. header/footer、脚注、文本框、内容控件、图片和公式如何挂到 unit；
6. 当前代表性行和窗口切分会遗漏哪些成员；
7. visual evidence 是否真正发送图片以及是否覆盖完整对象；
8. 当前 source_seq/raw run coverage 能否支持确定性 inheritance ledger；
9. 下游 element materialization 与 T5/T6 能消费哪些节点身份；
10. 旧输入、旧 mapper 和重复身份投影何时可以删除。

## 12. 输入验收方向

输入重构不能只以 schema 或 artifact 存在为完成。候选完成信号包括：

- 每个 T2 unit 都有唯一根节点；
- 每个非根节点只有一个父节点，树无环且引用可回查；
- table/paragraph/source object 的成员覆盖完整；
- child refs 与 leaf membership 可确定性展开且无重复/遗漏；
- AI 输出引用越界、跨层或跨单元时可以拒绝；
- 大表、合并单元格、嵌套表格、多段落 cell 和非文本对象有代表性 fixture；
- 成员不完整、视觉缺失、截断和未绑定对象有明确反例；
- code/AI/replay 使用同形输入；
- Stage Input 与 L1/T2 hash 稳定绑定；
- 旧 render packet 私有读取和第二套身份投影完成残留扫描。

## 13. 当前待讨论问题

1. 首版必须提供哪些节点类型？
2. table 的直接子节点使用 row、cell 还是稳定 row-group？
3. cell 下是否必须保留 paragraph 层？
4. span 使用预生成节点还是 `run_ref + start/end`？
5. source_object 首版覆盖哪些对象类型？
6. 节点整体终局判断需要哪些强制完整性条件？
7. 摘要、代表性行和裁剪后的节点是否只能用于路由？
8. 视觉完整性如何计算，视觉缺失阻止哪些终局判断？
9. leaf coverage 统一落在 raw run、atomic span，还是按对象类型选择叶节点？
10. 当前旧输入迁移是否必须一次完成，还是允许受版本约束的双读过渡？
11. code route 是否直接消费同一节点树，还是先由节点树生成确定性专用视图？
12. T5/T6 需要保留哪些对象/节点身份，哪些只作为 T3 trace？
13. Unit 层是否必须发送完整全文，还是允许可验证的分片摘要后再聚合？
14. 跨页 unit/table 的图片如何分批发送并证明视觉覆盖完整？
15. 每层 direct child 摘要必须包含哪些文字、样式和结构字段？
16. 图片 crop 由确定性 bbox 生成，还是允许视觉模型先定位再生成二次 crop？
17. 哪些判断在 text-only route 中禁止产生高置信终局结果？
18. 大表的完整 row 摘要如何控制 token，同时不退化成代表性抽样？

## 14. 后续定稿顺序

1. 先在本文确认首版节点树、身份、完整性和事实边界；
2. 与 T3 AI 输出讨论稿对齐可输出动作和允许停止层级；
3. 两份讨论稿结论一致后，再迁入 canonical T3 架构与测试契约；
4. 登记当前输入实现与目标契约差距；
5. 更新现有 T3 plan 或在目标/根因变化时建立下一轮 issue/plan；
6. 最后实施 Stage Input builder、schema、prompt、orchestrator、materializer 和验证。
