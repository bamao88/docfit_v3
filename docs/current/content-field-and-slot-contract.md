# 内容字段与模板槽位匹配契约

Status: Draft for review  

本文是学生内容、模板填写槽位和放置阶段共同使用的跨阶段语义契约。它定义内容是什么、模板位置接受什么内容，以及两者如何通过稳定字段完成标识与匹配。

Last updated: 2026-07-22

一句话结论：学生内容以递归 `ContentNode` 表示，模板中的可填写位置以 `TemplateSlot` 表示；`ContentNode.field_key` 与 `TemplateSlot.accepts_field_keys` 使用同一套标准字段完成匹配，槽位再声明写入目标 Word 时使用的样式或格式契约。

本文定义跨阶段共享字段、内容节点结构和模板槽位匹配边界；不定义内容提取算法、具体放置决策、Word 写入实现或验收方案。

## 1. 统一模型

```text
StudentContentArtifact
└── nodes[]: ContentNode
    ├── 公共字段
    │   ├── node_id
    │   ├── field_key
    │   ├── node_type
    │   ├── order
    │   ├── parent_node_id
    │   ├── payload
    │   ├── children[]
    │   ├── source_refs[]
    │   └── content_hash
    └── node_type 分支
        ├── text
        ├── person_name
        ├── section
        ├── paragraph
        ├── keyword
        ├── heading
        ├── figure
        ├── table
        ├── table_row
        ├── table_cell
        ├── caption
        ├── note
        ├── asset
        ├── reference_entry
        ├── appendix
        └── unmapped
```

两条核心规则：

```text
field_key 决定“这项内容在论文中是什么”
node_type 决定“这项内容使用什么结构保存”
```

`field_key` 和 `node_type` 是两个不同维度。例如，中英文标题使用不同 `field_key`，但都使用 `text` 节点；中英文摘要使用不同 `field_key`，但都使用 `section` 容器和 `paragraph` 子节点。

## 2. 顶层产物 `StudentContentArtifact`

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `artifact_type` | string | 是 | 固定为 `student_content_artifact` |
| `artifact_version` | string | 是 | 字段契约版本 |
| `student_id` | string/null | 是 | 学生样本或业务输入标识；未知时为 null |
| `source_document` | object | 是 | 源 DOCX 路径、hash 和 OOXML 主 part |
| `nodes` | ContentNode[] | 是 | 顶层内容节点，按源文档语义顺序排列 |
| `indexes` | object | 是 | 按节点、字段和来源建立的反查索引 |

### 2.1 `source_document`

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `path` | string | 是 | 源 DOCX 路径或业务对象引用 |
| `sha256` | string | 是 | 源 DOCX 内容 hash |
| `document_part` | string | 是 | 正文 XML part，通常为 `word/document.xml` |

## 3. 统一节点 `ContentNode`

所有内容节点都必须使用以下公共字段。某个分支不得另造一套身份、顺序或来源字段。

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `node_id` | string | 是 | 节点稳定且唯一的身份 |
| `field_key` | string/null | 是 | 标准语义字段；结构子节点不单独映射时为 null |
| `node_type` | enum | 是 | 决定 `payload` 结构的类型辨别字段 |
| `order` | integer | 是 | 当前父节点下的顺序，从 1 开始 |
| `parent_node_id` | string/null | 是 | 父节点 ID；顶层节点为 null |
| `payload` | object | 是 | 当前类型自己的值；结构由 `node_type` 决定 |
| `children` | ContentNode[] | 是 | 子节点；没有子节点时为空数组 |
| `source_refs` | SourceRef[] | 是 | 当前节点来自哪些源 Word 对象 |
| `content_hash` | string | 是 | 规范化 `payload + children` 的内容 hash |

统一示例：

```yaml
node_id: abstract-zh
field_key: abstract.zh.body
node_type: section
order: 4
parent_node_id: null
payload:
  language: zh
children:
  - node_id: abstract-zh-p-001
    field_key: null
    node_type: paragraph
    order: 1
    parent_node_id: abstract-zh
    payload:
      text: "……"
      raw_text: "……"
    children: []
    source_refs: []
    content_hash: sha256:...
source_refs: []
content_hash: sha256:...
```

### 3.1 `SourceRef`

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `part_name` | string | 是 | OOXML part，例如 `word/document.xml` |
| `object_type` | string | 是 | `paragraph`、`table`、`drawing`、`textbox`、`other` |
| `object_index` | integer/string | 是 | part 内对象位置 |
| `paragraph_id` | string/null | 否 | 源文档存在稳定段落 ID 时记录 |
| `run_ids` | string[] | 否 | 仅使用部分 run 时记录 |

## 4. 标准 `field_key` 注册表

| 内容 | `field_key` | 根节点 `node_type` | 主要子节点 |
| --- | --- | --- | --- |
| 中文论文标题 | `metadata.title.zh` | `text` | 无 |
| 英文论文标题 | `metadata.title.en` | `text` | 无 |
| 学生姓名 | `metadata.student.name` | `person_name` | 无 |
| 学号 | `metadata.student.number` | `text` | 无 |
| 学院 | `metadata.academy.name` | `text` | 无 |
| 专业 | `metadata.major.name` | `text` | 无 |
| 导师姓名 | `metadata.advisor.name` | `person_name` | 无 |
| 中文摘要正文 | `abstract.zh.body` | `section` | `paragraph[]` |
| 中文关键词 | `abstract.zh.keywords` | `section` | `keyword[]` |
| 英文摘要正文 | `abstract.en.body` | `section` | `paragraph[]` |
| 英文关键词 | `abstract.en.keywords` | `section` | `keyword[]` |
| 正文 | `body.content` | `section` | `heading/paragraph/figure/table/...` |
| 参考文献 | `references` | `section` | `heading? + reference_entry[]` |
| 附录 | `appendices` | `section` | `heading? + appendix[]` |
| 致谢 | `acknowledgements` | `section` | `heading? + paragraph[]` |
| 暂无标准字段的内容 | `unmapped` | `unmapped` | 按观察到的结构保留 |

标准字段只出现在需要跨阶段匹配的语义根节点上。表题、表格行和正文段落等内部节点通常使用 `field_key: null`，通过父子关系确定语义，避免为每个内部结构制造全局字段。

## 5. `node_type` 分支定义

每个分支只定义 `payload` 字段和允许的 `children`。第 3 节的公共字段始终存在。

### 5.1 文本 `text`

适用于论文标题、学号、学院和专业等单值内容。

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `text` | string | 是 | 去除“论文题目”“学号”等标签后的正文 |
| `raw_text` | string | 是 | 源文档完整原文 |
| `language` | enum | 是 | `zh`、`en`、`mixed`、`unknown` |

允许的 `children`：空数组。

### 5.2 姓名 `person_name`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `display_name` | string | 是 | 去除“学生姓名”“导师”等标签后的姓名原文 |
| `raw_text` | string | 是 | 源文档完整原文 |
| `language` | enum | 是 | `zh`、`en`、`mixed`、`unknown` |

允许的 `children`：空数组。默认不拆分姓和名，也不自动翻译。

### 5.3 内容域容器 `section`

适用于摘要、关键词、正文、参考文献、附录和致谢的语义根节点。

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `language` | enum/null | 是 | `zh`、`en`、`mixed`、`unknown`；不适用时为 null |
| `label_raw_text` | string/null | 是 | 源区域标签，例如“摘要”“关键词”“参考文献” |

允许的 `children` 由 `field_key` 决定，见第 4 节。

### 5.4 段落 `paragraph`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `text` | string | 是 | 去除区域标签后的段落正文 |
| `raw_text` | string | 是 | 源段落完整原文 |
| `paragraph_role` | enum | 是 | `body_text`、`list_item`、`quote`、`other` |

允许的 `children`：通常为空；行内公式等需要结构化时可以增加专用子节点。

### 5.5 关键词 `keyword`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `text` | string | 是 | 去除两侧空白后的关键词正文 |
| `raw_text` | string | 是 | 源关键词文本片段 |
| `source_delimiter` | string/null | 是 | 该关键词之后的源分隔符 |

允许的 `children`：空数组。

### 5.6 标题 `heading`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `heading_text` | string | 是 | 去除源编号后的标题正文 |
| `heading_level` | integer | 是 | 标题结构层级 |
| `source_numbering_text` | string/null | 是 | 原稿编号，例如 `1.2.1` 或 `第一章` |
| `raw_text` | string | 是 | 源标题完整文字 |

允许的 `children`：空数组。标题管辖的后续正文通过内容顺序或独立结构索引表达，不把全文机械嵌套进标题节点。

### 5.7 图 `figure`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `source_numbering_text` | string/null | 是 | 原稿图号 |
| `layout_hint` | object/null | 否 | 组合图等无法只靠子节点表达的源事实 |

允许的 `children`：

```text
asset[]
caption[language=zh]?
caption[language=en]?
note[]
figure[]（组合图子图）
```

图资源、图题和图注归入同一个 `figure` 节点后，不再作为正文同级节点重复出现。

### 5.8 表 `table`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `source_numbering_text` | string/null | 是 | 原稿表号 |
| `row_count` | integer | 是 | 逻辑行数 |
| `column_count` | integer | 是 | 逻辑列数 |
| `merge_map` | object[] | 是 | 横向和纵向合并信息 |

允许的 `children`：

```text
caption[language=zh]?
caption[language=en]?
table_row[]
note[]
```

表题、表格主体和表注共同构成一个 `table` 节点。

### 5.9 表格行 `table_row`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `row_index` | integer | 是 | 从 1 开始的逻辑行号 |

允许的 `children`：`table_cell[]`。

### 5.10 表格单元格 `table_cell`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `column_index` | integer | 是 | 从 1 开始的逻辑列号 |
| `row_span` | integer | 是 | 纵向跨度 |
| `column_span` | integer | 是 | 横向跨度 |
| `raw_text` | string | 是 | 单元格调试文本视图 |

允许的 `children`：`paragraph/figure/formula/list/unmapped[]`。

### 5.11 图表题名 `caption`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `language` | enum | 是 | `zh`、`en`、`mixed`、`unknown` |
| `label` | string/null | 是 | `表`、`Table`、`图`、`Figure` 等 |
| `source_number` | string/null | 是 | 去除 label 后的源编号 |
| `title` | string | 是 | 去除 label 和编号后的题名正文 |
| `raw_text` | string | 是 | 源题名完整文字 |

允许的 `children`：空数组。

如果中文和英文题名位于同一个源段落，仍可建立两个 `caption` 子节点，并共同引用该源段落的不同 run；确实无法拆分时使用一个 `language: mixed` 节点。

### 5.12 图注和表注 `note`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `marker` | string/null | 是 | 例如 `注：`、`Note:`、`*` |
| `language` | enum | 是 | `zh`、`en`、`mixed`、`unknown` |
| `text` | string | 是 | 去除 marker 后的注释正文 |
| `raw_text` | string | 是 | 源注释完整文字 |

允许的 `children`：空数组。

### 5.13 图片资源 `asset`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `media_type` | string | 是 | 例如 `image/png`、`image/jpeg` |
| `source_part` | string | 是 | OOXML media part 路径 |
| `sha256` | string | 是 | 原始二进制 hash |
| `width` | number/null | 否 | 源显示宽度 |
| `height` | number/null | 否 | 源显示高度 |
| `alt_text` | string/null | 是 | 源替代文字 |

允许的 `children`：空数组。

### 5.14 参考文献条目 `reference_entry`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `source_label` | string/null | 是 | 原稿编号，例如 `[1]` |
| `text` | string | 是 | 去除源编号后的完整条目正文 |
| `raw_text` | string | 是 | 源条目完整文字 |

允许的 `children`：跨段条目可以包含 `paragraph[]`。作者、题名、期刊和年份属于可选增强，不能替代完整 `text`。

### 5.15 附录 `appendix`

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `source_label` | string/null | 是 | 例如 `附录 A` |
| `title` | string/null | 是 | 附录标题正文 |
| `raw_heading_text` | string/null | 是 | 源附录标题完整文字 |

允许的 `children`：与 `body.content` 相同的 `heading/paragraph/figure/table/...` 内容节点。

## 6. 没有对应标准字段的内容 `unmapped`

当提取器取得一项真实内容，但字段注册表中没有合适的 `field_key` 时，仍然使用统一 `ContentNode`，只是：

```yaml
field_key: unmapped
node_type: unmapped
```

`payload`：

| 字段 | 类型 | 必需 | 定义 |
| --- | --- | --- | --- |
| `observed_type` | string | 是 | 当前能描述的内容类型，例如 `ethics_statement`、`funding_info`、`author_bio`、`unknown` |
| `proposed_field_key` | string/null | 是 | 建议新增的标准字段；只作为候选 |
| `raw_content` | string/object | 是 | 完整原始内容，不截断 |
| `reason` | enum | 是 | `no_registered_field`、`ambiguous_field_mapping`、`multiple_possible_fields` |
| `candidate_field_keys` | string[] | 是 | 存在多个可能映射时全部记录 |

允许的 `children`：如果已经能识别其内部结构，可以继续使用统一 `ContentNode[]` 保存；完全无法结构化时为空数组。

处理规则：

1. `unmapped` 是正式内容节点，不是日志。
2. 它和其他节点使用相同的身份、顺序、来源和 hash 字段。
3. 不得为了消除 `unmapped` 而将内容塞进语义不准确的现有字段。
4. `proposed_field_key` 不能直接作为正式字段使用。
5. 确认新语义后，应先更新第 4 节字段注册表，再将节点映射到正式 `field_key`。

## 7. 字段树示例

```text
nodes[]
├── ContentNode(field_key=metadata.title.zh, node_type=text)
├── ContentNode(field_key=metadata.student.name, node_type=person_name)
├── ContentNode(field_key=abstract.zh.body, node_type=section)
│   ├── ContentNode(node_type=paragraph)
│   └── ContentNode(node_type=paragraph)
├── ContentNode(field_key=abstract.zh.keywords, node_type=section)
│   ├── ContentNode(node_type=keyword)
│   └── ContentNode(node_type=keyword)
├── ContentNode(field_key=body.content, node_type=section)
│   ├── ContentNode(node_type=heading)
│   ├── ContentNode(node_type=paragraph)
│   ├── ContentNode(node_type=figure)
│   │   ├── ContentNode(node_type=asset)
│   │   ├── ContentNode(node_type=caption, language=zh)
│   │   ├── ContentNode(node_type=caption, language=en)
│   │   └── ContentNode(node_type=note)
│   └── ContentNode(node_type=table)
│       ├── ContentNode(node_type=caption, language=zh)
│       ├── ContentNode(node_type=caption, language=en)
│       ├── ContentNode(node_type=table_row)
│       │   └── ContentNode(node_type=table_cell)
│       └── ContentNode(node_type=note)
├── ContentNode(field_key=references, node_type=section)
│   └── ContentNode(node_type=reference_entry)
├── ContentNode(field_key=appendices, node_type=section)
│   └── ContentNode(node_type=appendix)
└── ContentNode(field_key=unmapped, node_type=unmapped)
```

## 8. 与模板字段的对应

模板生成阶段如果识别出可填写位置，应让该槽位声明接受的标准字段，并关联写入该位置时使用的目标样式或格式引用：

```yaml
slot_id: target-slot-abstract-zh
accepts_field_keys:
  - abstract.zh.body
target_style_ref: abstract-body
```

跨阶段只通过以下关系匹配：

```text
ContentNode.field_key <-> TemplateSlot.accepts_field_keys
```

职责边界：

- `field_key` 标识“内容是什么”，由内容节点和模板槽位共享；
- `accepts_field_keys` 标识“这个槽位允许接收什么内容”；
- `target_style_ref` 或等价格式契约标识“内容写入该槽位后应呈现什么样式”；
- 放置阶段基于字段匹配选择槽位，渲染阶段执行槽位已经确定的样式；
- 样式不能改变内容语义，字段也不直接编码某所学校的具体 Word 样式。

内部结构节点通过父节点整体传递，不需要逐个建立全局模板字段。例如 `body.content` 下的图题和表注保留为子节点，由正文内容树共同传递。`unmapped` 节点在登记正式 `field_key` 前不能匹配普通模板槽位。

## 9. 索引

顶层 `indexes` 至少包含：

| 字段 | 类型 | 定义 |
| --- | --- | --- |
| `by_node_id` | object | `node_id -> 节点位置` |
| `by_field_key` | object | `field_key -> node_id[]` |
| `by_source_ref` | object | `SourceRef -> node_id[]` |

索引只用于反查，不是字段树的第二事实源。
