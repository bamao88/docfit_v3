# T1 原始事实与 L1 统一身份、客观结构（讨论稿）

> Status: discussion draft  
> Created: 2026-07-24  
> Scope: 模板生成 T1 原始解析事实与 L1 新增统一身份、索引、定位及视觉绑定字段的责任边界  
> Related: [`t3-stage-input-hierarchical-structure-discussion.md`](./t3-stage-input-hierarchical-structure-discussion.md)  
> Canonical target: 讨论定稿后迁入 [`template-generation-architecture.md`](../current/template-generation-architecture.md) 的共享身份、T1 和 L1 章节  
> Non-goal: 本文不修改正式架构契约、代码、artifact schema、T2/T3 语义输出或实施计划。

> **Current scope override — T4 暂缓：本轮不讨论、不设计、不修改也不验收 T4。涉及页面、全局事实和 visual binding 的定义只用于完善 T1/L1 中立事实底座，并保证现有 T4 consumer 不被破坏；不据此派生新的 T4 字段或任务。**

> 本文只用于讨论。第 2 节和第 5.1 节记录目前已经形成的共识；第 5.2 节及之后仍有待决项，不能据此宣称系统已经完成迁移。

## 0. 现行事实基线与迁移顺序

本稿提出的是 T1/L1 目标身份模型。判断“当前字段是什么”时，事实优先级为：

1. 当前 producer、final publisher、consumer，以及由当前版本可复现生成并通过契约检查的真实 artifact；
2. 与实现一致的 [`docs/current/template-generation-architecture.md`](../current/template-generation-architecture.md) 和测试契约；
3. active status；
4. 已批准且仍在执行的 plan；
5. human discussion 和未来架构设想。

当前实现的身份面不能被目标名词遮盖：

- T1 `01_document_facts.json` 当前生产 `body_flow` 中的 `source_seq`/`source_ref`，并保存 raw/logical Run、unknown objects、indexes 和其他原始 `data`；
- L1 `01.5_l1_input_contract.json` 当前生产 `source_text_index`、`run_index`、`source_object_index`、`source_structure_index`、`layout_fact_index`、`visual_page_index`、`coverage` 和 `input_hashes`；
- T2–T6 当前仍消费 `source_seq`、`source_ref`、raw/logical Run ID、span、object、page/render binding 等组合引用；
- 当前 L1 尚未生产本文目标中的 `source_atom_seq`、统一 source selection 或统一 locator schema。

长期架构文档仍是现行 T2–T7 核心字段的有效基线，但其 L1 必备内容表漏列了当前实现已有的 `source_structure_index`；完整 stage view shape 也仍须以 builder、schema、契约测试和当次 artifact 为准。历史运行目录中的旧 artifact 不能覆盖当前实现。

因此，本轮顺序固定为：先冻结现行阶段输入输出，再完成 T1/L1 目标 schema 与兼容投影，然后只切换 T2/T3 stage-input projector 的事实来源并验证 T2–T7 行为不变，最后才迁移 gold。下游改用新 identity/locator 另行立项；尚未实现的 T2-B、多 T3 模式、T5 slots/effects 等未来设计不参与本轮现行字段判定。

## 1. 这次讨论要解决什么

源 Word 中所有后续可能被保留、替换、删除、校验或用于排版的内容都不能在解析过程中丢失。系统还需要让后续阶段和人工审查能够使用一个简单、统一的编号找到这些内容。

目前需要分开讨论两个问题：

1. **身份问题**：源 Word 中最底层、可独立追踪的内容，怎样获得唯一且有顺序的编号；
2. **事实表达问题**：表格行列、单元格合并、对象归属、格式和 OOXML 位置等事实，怎样在不制造多套身份的前提下完整保存。

本稿已经锁定原子边界、物理顺序原则、客观结构表达和属性保存策略；剩余讨论集中在完整 OOXML 类型枚举、精确 schema 与迁移验收。

## 2. 已形成共识：统一的源内容身份

### 2.1 一份源 Word 只使用一套由 L1 新增的底层顺序编号

T1 忠实解析源 Word 对象但不新增统一业务字段。L1 基于 T1 对象和确定性源顺序，把所有需要独立追踪的最底层内容纳入同一条有序序列；每个成员只获得一个权威编号。

新增的统一原子编号固定命名为 `source_atom_seq`。“atom”表示源内容原子。当前 `source_seq` 已被下游广泛使用，而且它目前指向较高层的可见正文流条目；本轮不改名、不删除，也不把它偷偷改成另一种粒度。L1 新增 `source_atom_seq`，并保存 `source_seq ↔ source_atom_seq[]` 的兼容映射，待下游逐步迁移。

```text
source_atom_seq = 1, 2, 3, 4, ...
```

这套编号必须满足：

- 在同一份冻结的源 Word 和同一次事实版本中唯一；
- 按确定性的源文档顺序连续生成；
- 同一份源 Word 重复解析时结果可复现；
- 只由 L1 确定性生成，T1 不创建，T2、T3 以及更后阶段不得重编号或补造编号；
- 编号本身不表达内容类型、结构层级、语义动作或格式；
- 后续阶段只使用该编号回答“这是哪个源原子”；表达一组原子、原子内部字符范围或执行位置时，使用引用该编号的选择关系和 locator。

编号的稳定范围是“同一份源文档快照”。源 Word 内容发生插入、删除或重排后，序号可以变化；系统应通过源文件 hash 区分不同快照，不能把两个版本中相同的数字当成同一个内容。

### 2.2 编号与对象类型无关

文字片段、图片、公式、控制节点、最深空占位及其他源叶子 occurrence 使用同一种编号。编号的数字只表达该成员在统一源序列中的身份和顺序，不表达“它是什么”。

概念示例：

| `source_atom_seq` | `kind` | 内容或事实 |
| ---: | --- | --- |
| 10 | `text` | “学生姓名” |
| 11 | `inline_object` | 校徽图片 occurrence |
| 12 | `empty_placeholder` | 一个没有任何叶子内容但必须保留的空段落占位 |
| 13 | `text` | “指导教师” |
| 14 | `control` | 页码 field instruction/control occurrence |

上表中的 `kind` 是内容事实，不是第二套身份。

### 2.3 “统一身份”不等于“只解析 Run”

当前 Word 文字的较低层级是 raw Run，但 Run 不能覆盖所有需要追踪的源内容，例如：

- 图片和绘图对象；
- 没有文字的单元格或段落；
- 公式、文本框、内容控件；
- 字段、分页符和分节符；
- 只通过结构或版式产生作用的对象。

因此，目标不是把现有 Run ID 当作全局编号，而是定义一个能够容纳不同 `kind` 的统一源内容原子序列。raw Run 继续作为物理容器和兼容 locator；它的连续文字、控制符和对象 child 才是原子。一个只含连续文字的 raw Run 会对应一个 `text` 原子，一个混合 Run 可以对应多个原子。

### 2.4 只保留一套权威身份，不等于只保留一个引用字段

后续阶段和人工讨论应以统一顺序编号作为源内容的权威引用，不应同时把以下编号都暴露成并列的业务身份：

- 第 3 张表；
- 第 5 个单元格；
- 第 12 个段落；
- `body_0010`；
- 第 7 张图片；
- raw Run 编号；
- 另一套对象编号。

这些信息如果仍由程序内部使用，只能是对象属性、数组位置、派生标签或执行定位信息，不能与统一编号竞争“源内容到底是谁”的解释权。

例如，一张表由源原子 10 至 12 组成时，可以使用一个范围选择：

```json
{
  "source_selection": {
    "kind": "atom_interval",
    "start": {"source_atom_seq": 10},
    "end": {"source_atom_seq": 12}
  }
}
```

这里的 `source_selection` 回答“选中了哪些原子”，不是“这个对象的身份是什么”。如果最终 schema 继续使用 `source_range` 这个名字，也必须把它定义成选择表达式，而不是与 `source_atom_seq` 并列的身份。

因此需要同时保留但严格分层：

- `source_atom_seq`：源原子的唯一业务身份；
- source selection：选择一个原子、连续原子区间或非连续成员；
- character selection：选择某个文字原子内部的字符区间；
- locator：把已选目标定位到 OOXML/package 中的可执行地址；
- visual binding：把源原子绑定到渲染页、bbox 或裁剪图。

“只有一种身份”不能被解释成取消范围选择、字符范围、结构位置或执行地址。它只表示这些字段都不能与 `source_atom_seq` 竞争“源内容是谁”的解释权。

### 2.5 所有源内容必须被覆盖

统一编号成立的前提不是“给已经解析出来的可见文字重新编号”，而是 T1 先忠实解析并显式记录未知节点，L1 再证明统一身份覆盖了需要追踪的源内容。

至少必须覆盖：

- 正文、表格、页眉、页脚和脚注中的文字；
- 所有 raw Run；有叶子内容的 Run 映射到一个或多个原子，空的 formatting-only Run 作为 Run/格式事实保留但不单独获得原子身份；
- 图片、公式、文本框、内容控件及其他可见对象；
- 空段落、空单元格和合并单元格中的占位事实；只给最深空容器创建一个 `empty_placeholder`；
- 字段、分页、分节及其他影响最终 Word 的源节点；
- 嵌套表格和浮动对象；
- 当前解析器尚不能识别但确实存在的对象。

哪些项目本身成为原子已经由第 5.1 节固定。coverage 必须同时证明原子叶子没有遗漏、非原子的容器/属性/资源事实也没有静默丢失。

### 2.6 页面图片是视觉真值，不是第二套源内容身份

独立 render 过程还应把同一份冻结源 Word 渲染成页面图片。L1 负责把 T1 facts 与 render facts 合并并封存。结构化事实回答“源 package 里有什么、对象怎样组成”，页面图片回答“这份 Word 实际呈现成什么样”。两者是同一源快照下相互校验的两种权威证据面。

需要区分：

- Word 中嵌入的图片、绘图或对象本身，若需要独立追踪，应作为 source atom 获得 `source_atom_seq`；
- 整页渲染图片是源文档的视觉证据，不是新增的 source atom，也不获得另一套内容身份；
- clean page image 是下游进行视觉判断的主输入；带编号、bbox 或标记的 annotated image 只用于定位和诊断，不能替代 clean image；
- 某一张源页面图的稳定归属至少由 `source hash + source_render_hash + page number` 确定，图片文件 hash 用于校验具体文件内容；
- 页面图片通过 source hash、render hash、page number、bbox 和 atom/object binding 与结构化事实绑定；
- T3 使用的 unit page subset 或 crop 只是从 sealed clean page image 派生的 Stage View，不成为新的源真值；它必须保留原 page number、crop bbox 和父 image hash；
- T2、T3、T4 可以按任务查看整页图或裁剪图，但不能在各自阶段重新渲染出另一套未封存的视觉事实。

还要区分两个不同时间点的渲染快照：

- T1/L1 基础阶段渲染的是原始学校模板，使用 `source_render_hash`，供 T2/T3/T4 判断；
- T7 渲染的是 T6 修改后的最终 DOCX，使用独立的 final/output render hash，供成品验证。

这两个 hash 都是对某次渲染快照的版本证明，不是源内容 identity。最终 Word 中新增的内容也不能因为出现在 T7 页面图中而获得原模板的 `source_atom_seq`。

### 2.7 L1 的边界：保存能力，不预做下游问题

> **L1 负责让原始内容不丢失、可查询、可定位；不负责替下游把问题提前做完。**

因此，T1 提供原始解析对象、原始内容、原始关系和原始 locator；L1 为其新增统一 atom identity、字符地址、查询索引、统一 locator map 和视觉绑定。但 L1 不需要提前枚举 T2 unit、T3 span 或 T4 layout 会使用的所有 selection。下游形成 selection 后，L1 必须能够解释、查询和定位它。

### 2.8 正文域与全局域分离，但不形成两套身份

T1 应把 body paragraph/table/run 等正文事实，与 section、header/footer、page field、break、numbering、document defaults 等全局事实分域保存。这样 T4 可以直接读取全局事实，而不需要从正文流中重新识别。

事实分域不改变统一身份原则：

- 两个事实域中需要独立追踪的源对象都由 L1 分配同一套 `source_atom_seq`；
- 正文 atom 可以通过显式关系引用 section、numbering、field 或 header/footer；
- 全局对象不能因为单独存放而再获得一套 `global_id` 业务身份；
- page geometry、margin 等如果只是属性，可以绑定其源 section/locator，不必强行成为独立 atom。

## 3. 身份、选择、执行地址和视觉位置是四个不同问题

统一编号直接回答三个问题：

1. 这是源 Word 中哪一个最底层内容；
2. 它在统一源序列中的前后顺序是什么；
3. 后续结果引用的最底层对象是谁。

它不能单独回答：

- 一次判断或动作选中了哪些原子；
- 只选择某个文字原子的哪些字符；
- 被选内容在 OOXML 中怎样定位和修改；
- 被选内容实际渲染在哪一页、哪个区域。

因此建议把引用模型分成以下层次。字段名仍需在正式 schema 中裁定。

### 3.1 单个原子身份

```json
{
  "source_atom_seq": 12
}
```

### 3.2 连续或非连续的原子选择

连续选择可以紧凑表达为：

```json
{
  "source_selection": {
    "kind": "atom_interval",
    "start": {"source_atom_seq": 10},
    "end": {"source_atom_seq": 12}
  }
}
```

非连续选择可以明确列出成员：

```json
{
  "source_selection": {
    "kind": "ordered_members",
    "members": [
      {"source_atom_seq": 10},
      {"source_atom_seq": 12},
      {"source_atom_seq": 18}
    ]
  }
}
```

两种形状都只是对 `source_atom_seq` 的组合引用。区间端点必须可展开成确定的 atom members；不能另外获得一个 range identity。

### 3.3 原子内部的字符选择

当一个 Run 原子内部需要执行不同动作时，下游必须能够形成稳定的字符范围：

```json
{
  "source_selection": {
    "kind": "character_span",
    "atom": {"source_atom_seq": 12},
    "char_start": 0,
    "char_end": 4
  }
}
```

L1 必须保存 raw text，并固定字符 offset 的坐标系、开闭区间、Unicode 单位和源文本 hash；它不需要预先切好 character span。字符范围由需要它的下游阶段形成，不是新的内容身份，而是对一个源原子的局部选择。

### 3.4 OOXML 执行地址

T6 不能只靠顺序编号修改 Word。L1 必须能够把 atom 或 selection 解析为可验证 locator，例如 part、XML path、父容器、run/character 位置和 source hash。

locator 可以作为 L1 索引保存，也可以在执行输入中物化；无论怎样，它回答的是“去哪里执行”，不是“源内容是谁”。

### 3.5 视觉位置

page、bbox、render target 和 crop 回答“源内容呈现在哪里”。它们必须绑定 `source_atom_seq` 或 source selection，并绑定 source/render hash，但不承担源对象身份。

## 4. T1 客观成员关系与下游语义组合必须分开

多个 atom 被一起引用不必然是语义判断。需要区分两类组合。

### 4.1 T1 可以输出的客观成员关系

源 Word 已经明确存在的物理包含关系属于客观事实，例如：

- 某个段落包含哪些源原子；
- 某个单元格包含哪些源原子；
- 某张表格覆盖哪些源原子；
- 某个页眉或页脚包含哪些源原子。

T1 应保留源 OOXML 中已有的物理成员关系；L1 可以为这些关系增加统一 identity 引用和查询索引。下游 view 可以把成员关系表达成 `source_selection`；选择的端点或 member 仍只用 `source_atom_seq` 指向源内容。

### 4.2 T1 不能输出的语义组合

需要理解内容含义后才能形成的组合不属于 T1，例如：

- 哪些内容共同构成“中文摘要”单元；
- 哪段是固定模板说明，哪段应该删除；
- 哪些文字应该 Fill、Keep 或 Delete；
- 一个 Run 中哪几个字符形成可替换的语义 span。

这些组合由 T2/T3 或后续阶段判断，但必须引用 L1 已经生成的统一源编号。

T1 保存 raw Run 原始文字和原始 locator；L1 可以确定性增加统一字符坐标和 source text hash。两者都不能提前创建带有 Fill/Delete 等含义的语义 span。

## 5. 已固定的原子边界与剩余待决项

### 5.1 什么才是最底层“源内容原子”

本讨论固定以下定义：

> **源内容原子，是源 OOXML 中最小的、可以被独立引用、选择、校验或执行的叶子 occurrence。**

“最小”不是指单个字符，也不是指每一个 XML 标签。判断标准是：拆得更小以后，是否仍存在独立的追踪、校验或执行意义。原子必须来自源 package 中真实存在的 occurrence；L1 只能分配身份，不能创造源内容。

#### 5.1.1 哪些内容获得 `source_atom_seq`

| `kind` | 原子边界 | 说明 |
| --- | --- | --- |
| `text` | raw Run 内一段连续的文字叶子内容 | 字符不是新原子；字符级目标用本原子内的 offset range 表达 |
| `inline_object` | 每一次图片、drawing、公式或嵌入对象 occurrence | 图片锚点、尺寸、relationship 和媒体 hash 是该 occurrence 的事实；媒体二进制本身不是第二个原子 |
| `control` | 每一个会独立影响内容流或执行的显式控制 occurrence | 包括 tab、换行/分页、字段 begin/separate/end 或 instruction、显式分节控制；显示结果文字仍是 `text` 原子 |
| `empty_placeholder` | 没有任何叶子内容但必须保留和定位的最深空容器占位 | 普通空段落产生一个占位；空 cell 若已有空段落，只使用该空段落占位，不再为 cell 重复建原子 |
| `opaque_unknown` | 当前解析器不能展开、但源 package 中真实存在的未知叶子或不透明子树 occurrence | 保存原始 locator、节点类型、可见性和 raw hash；不得静默丢弃 |

同一个 raw Run 可能只形成一个 `text` 原子，也可能形成多个原子。例如一个 Run 内依次出现“标题”、换行和图片时，形成 `text + control + inline_object` 三个原子；三者都保留相同的 `raw_run_id` 和各自的 child locator。这样既不把整个 Run 粗暴地当成不可拆整体，也不把每个字符变成身份。

#### 5.1.2 哪些内容不是原子

| 内容 | 表达方式 |
| --- | --- |
| 单个字符或文字子串 | `source_atom_seq + char_start + char_end` |
| logical Run | raw Run/原子之上的无损派生视图，保留现有 `logical_run_id` 供兼容，不获得新的原子身份 |
| paragraph、table、row、cell | 客观结构容器；通过有序成员关系引用原子 |
| header/footer、text box、content control | 结构或 part 容器；内部叶子各自成为原子；完全为空时只建一个最深空占位 |
| field 整体 | 一个物理关系对象，引用 field control、instruction 和 result atoms；不与这些叶子重复占用身份 |
| section、style、numbering definition、document defaults | 全局事实或共享定义，由 occurrence/容器引用 |
| 页面图、crop、bbox | 同一源快照的视觉证据和 binding，不是源内容身份 |
| 图片媒体二进制 | `inline_object` 的 payload/resource，使用 relationship、path、hash 回查 |
| T2 unit、T3 element、T6 action | 下游语义对象或动作，通过 source selection 引用原子 |

#### 5.1.3 T1 与 L1 在原子形成过程中的分工

T1 只输出可以成为原子的原始叶子事实，不分配 `source_atom_seq`。每个叶子至少保存：

- 现有 `source_ref`、`part_name`、`order`、`raw_run_id`/object ref；
- `kind`、`text` 或 object/control/empty/unknown 的原始事实；
- `parent_ref`、`container_refs` 和 OOXML locator；
- 原始 style/properties、可见性、supported/unknown 状态；
- 同一 source snapshot 的 hash 归属。

L1 按确定性源顺序为这些叶子分配 `source_atom_seq`，并增加字符地址、成员索引、locator map 和视觉绑定。当前 `source_seq` 继续表示现有正文流条目；一个 `source_seq` 可以映射一个或多个 `source_atom_seq`，一个跨容器原子不得反向挂到多个互相冲突的 `source_seq`。

#### 5.1.4 原子顺序

身份顺序采用 OOXML 物理顺序，不采用视觉坐标顺序：

1. 主文档 part 按 OOXML 深度优先顺序遍历；表格按 row → cell → paragraph → raw Run → Run child；inline object/control 位于其 Run child 的真实位置；
2. 主文档引用的 header/footer、footnote/endnote 等附属 part，按首次引用顺序进入；同一引用点按规范化 part kind 和 part name 稳定排序；
3. 每个附属 part 内继续按 OOXML 物理顺序遍历；
4. 浮动对象按其 anchor occurrence 排序，视觉 page/bbox 只保存为 binding，不参与身份重排；
5. 相同 source snapshot 和 schema version 必须得到相同顺序；无法排序的 unknown 必须显式 `not_available`，不能静默插入任意位置。

这一定义已经足以锁定原子粒度。后续仍需在正式 schema 中确定 locator 的精确序列化和跨 part 排序的完整枚举，但不能再改变“叶子 occurrence 是原子、容器不是原子、字符使用区间”这一边界。

### 5.2 “文档呈现顺序”到底采用哪一种顺序

第 5.1.4 节已经固定：原子身份采用 OOXML 物理顺序，视觉 page/bbox 不参与重排。普通正文、表格行和单元格按物理遍历直接确定；以下内容仍需在正式 schema 中补完整枚举：

- 页眉与页脚；
- 脚注和尾注；
- 浮动图片和文本框；
- 同一页面上通过坐标摆放的多个对象；
- 锚定位置与视觉位置不同的对象。

完整枚举必须遵守：

1. main document 先按物理顺序；
2. 附属 part 按首次引用顺序、part kind、part name 形成稳定序；
3. 浮动对象按 anchor occurrence，不按页面视觉位置；
4. 无法排序的 unknown 显式失败或 `not_available`，不能使用运行时遍历偶然顺序。

### 5.3 客观结构怎样表达

结构采用“规范化节点表 + 有序成员关系”，不把整棵嵌套树复制进每个下游 artifact：

```text
T1 body_structure/global_structure
  nodes[]
    - structure_ref
    - kind
    - part_name
    - source_ref
    - parent_ref
    - ordered child_refs[]
    - order
    - raw_locator
    - raw_properties
    - completeness

L1 source_membership_index
  container_ref
    → ordered child_refs[]
    → ordered source_atom_seq_refs[]
    → merge/nested/empty/children_complete

Stage View
  → 按任务把上述关系投影成树
```

paragraph、table、row、cell、header/footer、text box 和 content control 使用 `structure_ref` 做结构寻址；`structure_ref` 不是源内容业务身份。叶子内容只使用 `source_atom_seq`。这样既能表达空容器、合并单元格和嵌套表格，又不会让 T3 重新发现物理关系。

### 5.4 结构和格式属性保留到什么程度

身份编号不能代替以下事实：

- 行列关系；
- 横向和纵向合并；
- 表格网格、列宽、行高；
- 边框、底纹、对齐和单元格边距；
- 图片尺寸、锚点和环绕；
- 段落和 Run 的原始格式；
- 字段、分页和分节属性。

保存策略固定为“原始事实 + 常用规范化投影”：

- `raw_locator` / `raw_properties` 保存可回查的源 OOXML 地址和原始属性/hash；
- `normalized_properties` 保存下游已确认需要查询的稳定字段，例如 merge、grid、尺寸、alignment、font、spacing、break 和 anchor；
- `style_provenance` 说明 direct formatting、style definition、inheritance 和 effective value 的来源；
- 新增规范化字段必须能从 raw facts 确定性计算，并经过 schema version 管理；
- 未规范化的属性仍可从 raw facts 回查，不能因为当前下游没使用就静默丢失。

这些属性不获得 `source_atom_seq`；它们绑定到原子、结构容器或全局 occurrence。

### 5.5 范围选择怎样引用统一身份

普通段落、单元格和表格的物理成员通常连续；下游形成的选择也可能连续。但以下对象或任务选择可能包含不连续成员：

- 嵌套表格；
- 浮动对象；
- 跨 part 的页眉页脚；
- 合并单元格；
- 同一个逻辑对象包含多个不连续源节点；
- T2/T3 根据语义形成的组合对象。

公开契约固定支持四类选择：

```yaml
# 单个原子
kind: atom
source_atom_seq: 10

# 连续原子区间，包含首尾
kind: atom_interval
start_source_atom_seq: 10
end_source_atom_seq: 14

# 有序、非连续成员
kind: atom_members
source_atom_seq_refs: [10, 12, 20]

# 单个文字原子内部的半开字符区间 [start, end)
kind: text_range
source_atom_seq: 10
char_start: 0
char_end: 4
offset_unit: unicode_code_point
text_sha256: "..."
```

区间不得跨 source snapshot；`atom_interval` 按 L1 原子顺序确定性展开；`atom_members` 保留给定顺序并拒绝重复；`text_range` 必须校验 atom kind、offset unit、边界和 text hash。空选择非法。复杂下游对象可以持有多个 selection，但不能创建新源身份。

### 5.6 定位映射以什么形式存在

后续执行最终仍需回到 DOCX/OOXML 中找到具体节点，因此 locator/resolver 能力是必需的。承载形式固定为：

- `source_atom_index.atoms[]` 只携带 `locator_ref`，不复制完整执行地址；
- L1 `locator_index` 保存 `locator_ref → locator` 和 `source_atom_seq → locator_ref`；
- locator 至少包含 `source_template_hash`、`part_name`、`ooxml_path`、`node_kind`、`parent_ref`，以及适用的 `raw_run_id`、`run_child_index`、object/control address 和 precondition hash；
- T2/T3/T5 artifact 只传 source identity/selection，不需要展开完整 locator；
- T6 resolver 从 sealed L1 读取 locator，校验 source hash、节点类型、父容器和前置内容后执行；
- T7 可以读取 locator 做 trace/owner 归因，但不能用 locator 重新推断业务语义。

无论采用哪一种方案，都必须遵守：

> locator 是执行地址，不是第二套对外业务身份。

### 5.7 后续新生成内容的身份边界

L1 为模板源生成的统一编号只能覆盖 T1 从源 Word 中解析出的内容。

如果后续排版新增了源 Word 中不存在的内容，例如学生论文正文、自动生成目录或程序插入字段，它们不能伪造一个 L1 `source_atom_seq`。它们应保存：

- 来自哪个源内容编号、学生内容节点或生成动作；
- 在输出 Word 中获得什么输出身份；
- 与哪些模板源原子是什么关系。

是否需要跨模板源内容、学生源内容和最终输出内容建立一套更高层的统一追踪模型，需要另行讨论；不能通过扩大 L1 模板源编号的含义解决。

## 6. 当前实现与目标定义的差距

当前实现不是全部错误，但还不符合第 2 节定义的统一底层身份。

### 6.1 当前做对的部分

- 当前已经存在连续 `source_seq`，证明统一顺序引用对边界、追踪、报告和人工沟通有价值；
- raw/logical Run、表格、单元格和 OOXML `source_ref` 已保存了部分可回查事实；
- 表格单元格当前已有 `row`、`column`、文字、段落和 `source_ref` 等事实。
- 当前 render pipeline 已能从同一源 Word 生成 PDF、clean page PNG、annotated SVG、page layout 和部分 source binding；L1 `visual_page_index` 也已经封存 render hash 与这些产物。

### 6.2 当前不符合目标的部分

- 当前 `source_seq` 在 T1 内生成且只覆盖较高层正文流；它可以继续作为兼容字段，但 L1 尚未新增叶子级 `source_atom_seq` 和两者映射；
- 当前 `source_seq` 的对象通常是段落或有文字的表格单元格，不是全部底层原子；
- 空单元格因为没有文字，不一定进入可见 `body_flow`；
- 图片、未知对象、字段、分页和其他非文字事实没有全部进入同一套连续编号；
- raw Run 仍使用独立 Run ID，未进入统一源原子序列；
- `node_id`、`source_seq`、`source_ref`、`paragraph_id`、`table_id`、`cell_id`、raw/logical Run ID 等容易被下游理解成多套并列身份；
- 当前若干字段同时承担身份、范围选择和执行定位，缺少 `identity → selection → locator` 的明确转换契约；
- 表格当前记录了行列位置，但合并关系尚未形成明确、统一的规范化事实。
- 当前视觉链路仍需补齐显式 source hash、逐页 hash/完整性和 atom/object binding coverage；crop 与 T7 final render 的派生关系也需要进入正式契约。

因此，之前引入 `source_seq` 的目的和使用场景是正确的；需要补充的是由 L1 生成叶子级 `source_atom_seq`，同时解决覆盖层级偏高、覆盖对象不完整和多套身份关系不清。现有 `source_seq` 不改变名称、数值或粒度。

### 6.3 这不是废弃现有身份链路

当前 `source_seq` 已有大量生产消费关系，不应先删掉再重建。更稳妥的优化路径是：

1. 保留 T1 当前生成的 `source_seq` 数值、粒度和下游引用，由 L1 做一致性校验并建立 atom 映射；
2. 扩大 L1 identity coverage，使 Run、对象、空结构和未知节点进入统一模型；
3. 在 L1 增加 `identity → selection → locator/visual binding` 查询能力；
4. 新增 `source_atom_seq` 和 `source_seq ↔ source_atom_seq[]` 映射，不复用或改写现有 `source_seq` 的语义；
5. 只有新的 T1/L1 事实能力已经被真实运行、当前阶段输入、T2–T7 输出契约和代表性 replay 证明后，才删除重复的上游事实 producer；本轮不删除下游兼容身份；
6. 在上述迁移闭环以前冻结现有 gold，只把它作为回归裁判和差异证据；
7. T1/L1 与现有阶段输入兼容验证完成后，再用可审计的旧字段→新字段映射迁移 gold 和 gold projector。

gold 不得作为 T1/L1 的生成输入，也不能反向定义新的事实 schema；否则事实层与预期答案会在同一轮一起漂移，失去发现回归的能力。

因此，本讨论的目标是把现有能力归位并补齐，不是重新设计所有 artifact 或一次性改完全部消费者。

## 7. 下一轮讨论建议

建议按以下顺序逐项定稿，避免同时讨论所有字段：

1. **现行接口冻结**：逐项登记 T1/L1 producer、T2–T7 consumer、artifact 字段和兼容依赖；
2. **原子类型枚举**：把第 5.1 节的五类原子映射到全部受支持 OOXML 节点，并为未知类型保留显式扩展位；
3. **顺序规则细化**：补齐附属 part、浮动对象和 unknown 的确定性排序枚举，但不改变第 5.1 节的物理顺序原则；
4. **结构 schema**：把已确定的规范化节点表和有序成员关系写成正式字段约束；
5. **属性枚举**：列出第一版 `normalized_properties` 白名单和 raw-fact completeness 规则；
6. **执行映射 schema**：把已确定的 `locator_ref`/`locator_index` 方式补成精确字段、precondition 和 resolver 错误契约；
7. **选择规则验证**：用表格、单元格、T2 unit 和特殊对象验证四类 selection 的展开与完整性规则；
8. **集中与兼容验收**：规划兼容投影、T2/T3 projector 切换、下游不变回归、真实样本、replay、契约测试和残留扫描；下游 identity/locator 切换另行立项；
9. **gold 迁移**：只在 T1/L1 与现有阶段输入兼容闭环后执行，不与事实 schema 同步修改。

在前七项定稿以前，不建议直接修改正式身份契约或开始代码迁移；在第八项闭环以前，不修改 gold。

## 8. 当前讨论结论

截至本稿创建时，只确认以下结论：

> T1 忠实提供原始解析对象，不新增统一业务身份。L1 基于 T1/render 原始事实，为所有需要独立追踪的最底层内容确定性增加同一套、按源顺序排列的唯一编号，并增加索引、统一 locator、字符地址和视觉绑定。`source_atom_seq` 只负责身份；连续/非连续范围、字符区间、OOXML locator 和视觉绑定继续承担各自职责，但不能成为第二套业务身份。

以下事项尚未确认：

- 五类原子与全部受支持 OOXML 节点的完整映射表；
- 附属 part 和复杂浮动对象的完整排序枚举；
- 规范化结构节点表和成员关系的精确 schema；
- 第一版 normalized properties 白名单；
- locator 字段、precondition 和 resolver 错误的精确 schema；
- 复杂成员关系和后续新生成内容的身份规则。
