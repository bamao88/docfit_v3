# real-core-v0 Full Source-Fact Review Packet

Last generated: deterministic local script output
Status: source-fact review packet, not a signed baseline

This packet is intended to be the human review surface for the real-core-v0
acceptance chain. It is not a direction-only draft. The full school template
review sources and full student content review sources are embedded below so
unit elements, element order, relationships, fill policy, layout constraints,
and style dimensions are not lost in summary tables.

## Gate Boundary

- Runtime human review is not allowed as a pass/fail gate.
- AI may diagnose and organize evidence but may not decide final status.
- `auto_update_allowed` must remain false.
- This packet can approve source facts; deterministic verifiers still decide
  `PASS`, `FAIL`, or `UNKNOWN` during eval runs.

## How This Packet Is Used

| Stage | Reviewer checks in this packet | Later runnable artifact |
| --- | --- | --- |
| template parse | Full embedded school review source: unit order, unit elements, sub-elements, relationships, fixed/manual/generated/content policy, style dimensions, page/header/footer rules, keep-together constraints. | `standards/schools/<school_id>/v1/template_unit_contract.yaml` and `signed_standard.yaml` |
| content extract | Full embedded student review source: ignored donor content, title metadata, abstracts, keywords, ordered body flow, figures, tables, references, appendix, acknowledgement. | `standards/eval_profiles/real-core-v0/expected/student_content_trees/<student_id>.yaml` |
| placement | Shared alignment rules plus every render case matrix row; every accepted student content node must receive a disposition against the accepted target-school unit tree. | `standards/eval_profiles/real-core-v0/expected/render_plans/<case_id>.yaml` |
| render | Accepted template/content/placement facts plus later DOCX feature snapshots and Word image evidence. | `render_feature_snapshots/<case_id>.json` and `reports/real-core-v0/<case_id>/evidence/word_image_evidence.json` |

## Generated Draft Inventory

- Template draft files: 3
- Student content draft files: 3
- Render plan draft files: 9
- Draft YAML files remain unsigned until the full source facts below are accepted
  and converted into runnable baseline artifacts.

## Fixed Source Evidence

### School Templates

| school_id | template_docx | template_sha256 | review_source | review_sha256 |
| --- | --- | --- | --- | --- |
| `hunannongye` | `inputs/school-hunannongye-requirement.docx` | `sha256:6d66a2926ff170055840730f9273fccccfeb45df31cc877afc013d551b12d989` | `inputs/school-hunannongye-template-review.txt` | `sha256:65bb89715ad40cc8e2948f65441312d3da7efb56b5973d8f2c4c507c177c9794` |
| `nannong-undergraduate` | `inputs/school-nannong-undergraduate-template.docx` | `sha256:1c387b1991720ab2452284b02d9388ed6ab94ffce143468f43ac60e812331536` | `inputs/school-nannong-undergraduate-template-review.txt` | `sha256:d6dc0d49dac3e2b83fa63ee92e76965c1cec995d56eb3e27b3ea4d5f45acdb87` |
| `pku-graduate` | `inputs/school-pku-graduate-template.docx` | `sha256:720372f4e70b75ade60a302e95abc870e47d47ac7e6cbf0e5a16ceef4d619e14` | `inputs/school-pku-graduate-template-review.txt` | `sha256:631c7a839a1745af605fa1d5ddcffbc60b9325d506a9f8098b1a0d01ff6ad923` |

### Student Documents

| student_id | source_docx | source_sha256 | review_source | review_sha256 |
| --- | --- | --- | --- | --- |
| `real-student-001` | `inputs/real-student-001-source.docx` | `sha256:2e3d6310611cbe2fafddbda18e7b83387b5f3ea3d1f0f3163154d6ec129a6f60` | `inputs/real-student-001-content-review.md` | `sha256:fae06e0474920b7258ce7d5e7358ff665d599d09880e8b6761bbfd75248c7078` |
| `real-student-002` | `inputs/real-student-002-source.docx` | `sha256:fc39ac02efd152ddf609199615256393e3077b49629e1cca48e1f437b2e44a9b` | `inputs/real-student-002-content-review.md` | `sha256:2f54077297d25d77a65ba41d571c001d9dc47db83c26f3947fee5a7cb2f6d0db` |
| `real-student-003` | `inputs/real-student-003-source.docx` | `sha256:cf49d90832c44d2f28e7fe6940217f4afe7c637f179b3610c75801b900e7d290` | `inputs/real-student-003-content-review.md` | `sha256:a444c2826368c75c10e7e6df780fdc496e7ab139ee5ae55de0100f9b79c6583c` |

### Shared Alignment Review

- Source: `inputs/shared-template-recognition-alignment-review.txt`
- SHA-256: `sha256:8efd4bb76da5ac7f5aa0806b7fb97055146095c13a5673e991285ea6ba0d0069`

## Render Case Matrix

Every row below inherits the complete target-school template contract from
the embedded school review source and the complete student content tree from
the embedded student review source. The later render plan baseline must not
collapse this to a unit-only summary; it must preserve content-node
dispositions against target unit elements and sub-elements.

| case_id | target_school | student_content | acceptance focus |
| --- | --- | --- | --- |
| `real_core_v0_hunannongye_real-student-001` | `hunannongye` | `real-student-001` | target keeps Hunan fixed cover, integrity statement, TOC, title block, abstract units, body, references, default acknowledgement/appendix policy, and manual-only rear forms; ignore donor-school front matter and old TOC; preserve title metadata, abstracts, keywords, ordered body flow, 2 figures, 2 content tables, references, and acknowledgement; empty appendix title is not student content |
| `real_core_v0_hunannongye_real-student-002` | `hunannongye` | `real-student-002` | target keeps Hunan fixed cover, integrity statement, TOC, title block, abstract units, body, references, default acknowledgement/appendix policy, and manual-only rear forms; preserve title metadata, abstracts, keywords, ordered body flow, 1 figure, 1 table, and references; no appendix or acknowledgement found |
| `real_core_v0_hunannongye_real-student-003` | `hunannongye` | `real-student-003` | target keeps Hunan fixed cover, integrity statement, TOC, title block, abstract units, body, references, default acknowledgement/appendix policy, and manual-only rear forms; ignore Hunan Agriculture donor front matter and template lead-ins; preserve title metadata, abstracts, keywords, ordered body flow, 2 figures, 1 table, and references; second figure lacks independent English caption |
| `real_core_v0_nannong-undergraduate_real-student-001` | `nannong-undergraduate` | `real-student-001` | target keeps Nanjing cover, originality/authorization statements, TOC before abstracts, abstract units, body with conclusion/outlook type, references, appendix, achievements, and acknowledgement policy; ignore donor-school front matter and old TOC; preserve title metadata, abstracts, keywords, ordered body flow, 2 figures, 2 content tables, references, and acknowledgement; empty appendix title is not student content |
| `real_core_v0_nannong-undergraduate_real-student-002` | `nannong-undergraduate` | `real-student-002` | target keeps Nanjing cover, originality/authorization statements, TOC before abstracts, abstract units, body with conclusion/outlook type, references, appendix, achievements, and acknowledgement policy; preserve title metadata, abstracts, keywords, ordered body flow, 1 figure, 1 table, and references; no appendix or acknowledgement found |
| `real_core_v0_nannong-undergraduate_real-student-003` | `nannong-undergraduate` | `real-student-003` | target keeps Nanjing cover, originality/authorization statements, TOC before abstracts, abstract units, body with conclusion/outlook type, references, appendix, achievements, and acknowledgement policy; ignore Hunan Agriculture donor front matter and template lead-ins; preserve title metadata, abstracts, keywords, ordered body flow, 2 figures, 1 table, and references; second figure lacks independent English caption |
| `real_core_v0_pku-graduate_real-student-001` | `pku-graduate` | `real-student-001` | target keeps PKU cover, copyright, abstract units, TOC, figure/table lists, body with conclusion/discussion ending, references, achievements, acknowledgement, and originality/authorization page; ignore donor-school front matter and old TOC; preserve title metadata, abstracts, keywords, ordered body flow, 2 figures, 2 content tables, references, and acknowledgement; empty appendix title is not student content |
| `real_core_v0_pku-graduate_real-student-002` | `pku-graduate` | `real-student-002` | target keeps PKU cover, copyright, abstract units, TOC, figure/table lists, body with conclusion/discussion ending, references, achievements, acknowledgement, and originality/authorization page; preserve title metadata, abstracts, keywords, ordered body flow, 1 figure, 1 table, and references; no appendix or acknowledgement found |
| `real_core_v0_pku-graduate_real-student-003` | `pku-graduate` | `real-student-003` | target keeps PKU cover, copyright, abstract units, TOC, figure/table lists, body with conclusion/discussion ending, references, achievements, acknowledgement, and originality/authorization page; ignore Hunan Agriculture donor front matter and template lead-ins; preserve title metadata, abstracts, keywords, ordered body flow, 2 figures, 1 table, and references; second figure lacks independent English caption |

## Full School Template Review Sources

The following sections are embedded verbatim from the human school review
sources. They are the review facts for unit contents, element order,
relationships, policies, styles, page rules, and unresolved decisions.

### Source: `hunannongye`

- Path: `inputs/school-hunannongye-template-review.txt`
- SHA-256: `sha256:65bb89715ad40cc8e2948f65441312d3da7efb56b5973d8f2c4c507c177c9794`

~~~~text
湖南农业大学本科生毕业论文（设计）格式包审查稿 V2
日期：2026-06-09

依据：优先使用学校源格式说明与固定表单包
/Users/fl/ws/gogo/docfit/schools/hunannongye/sources/requirement.docx

辅助证据：
- /Users/fl/ws/gogo/docfit/schools/hunannongye/sources/requirement.doc
- /Users/fl/ws/gogo/docfit/schools/hunannongye/sources/_visual_reference/requirement_docx.source.pdf
- /Users/fl/ws/gogo/docfit/schools/hunannongye/README.md
- /Users/fl/ws/gogo/docfit/schools/hunannongye/page_contract.yaml
- /Users/fl/ws/gogo/docfit/schools/hunannongye/school.yaml
- /Users/fl/ws/gogo/docfit/schools/hunannongye/template_manifest.yaml

阅读方式
================================================================================
1. 先核对“单元顺序”：整篇文档有哪些单元，顺序是否对。
2. 再核对“单元内容与顺序”：每个单元有什么元素、元素顺序如何、哪些独立成段、哪些同段连接、哪些是固定模板内容、哪些需要填学生内容。
3. 最后核对“全局规则”：只放真正跨单元共用的页面、页码、标题、目录、正文、参考文献、图表、固定表单规则。

写法约定
- 类型=固定：学校源文件自带文字、表单、标题或固定页，不从学生正文填充。
- 类型=填充：从学生论文或元数据填入。
- 类型=生成：由 Word 字段或系统生成。
- 湖南农业源文件是“格式说明 + 示例 + 固定表单包”，不是一份干净的最终论文模板；括号里的“几号字/空几行/居中”等说明通常作为审查证据，不作为最终论文正文保留。
- 固定模板块：封面、诚信声明、后置固定表单等可以优先从源 DOCX 复制对应模板块，再清空或替换可变字段；Markdown 元素清单负责记录语义锚点、可删说明文字和验收口径，不要求逐段重建版式。
- 说明文字剥离：附件标题、括号中的字号/空行/居中说明、“以下农理工科类用”等格式说明是证据，不进入最终论文；封面这类“说明 + 示例”混合块复制时，只保留最终成品可见内容、固定标签和可填写空位。
- 固定内容必须显式写出“内容”；固定签名/日期/勾选框等表单项也要保留学校模板文字，只是不自动填写空白项或勾选项。
- 模板默认模块应默认保留，不因学生原文暂时缺少对应内容而省略；学生后续删除模块比重新补齐模块更容易。
- 缺失处理：学生内容没有识别到时，模板中应保留示例占位，并添加人工评论。
- 元素顺序：单元内元素按列出顺序输出；如果该单元用于测试，需显式写出“元素顺序”。
- 位置/排版关系：独立成段、同一段、同行、表格内部、页眉页脚等关系都属于审查项；未写同段关系时，默认该元素相对上一个元素换行并独立成段。
- 同页约束：如果一个单元或一组元素必须作为视觉整体留在同一页，应显式写出“同页约束”。封面、诚信声明这类单页固定模板块通常推定整页完整；跨页固定表单按源模板跨页结构保留，重点检查表格结构、意见区、签名日期区等局部组约束；参考文献、附录正文、致谢正文这类学生内容页不要求整个单元同页，只检查标题与首段等局部组约束。
- 样式只写核对需要的内容：字体、字号、加粗、对齐、缩进、段前、段后、行距、关键段落设置。
- 标题编号、目录页码、参考文献序号后的空格/制表符、勾选框属于模板内容；不应作为普通正文随意手打。
- 页眉/页码分层记录：页眉/页脚距离、页码字体字号、页码格式和连续编号规则放到第三层全局规则；每个单元只写本单元页眉显示文字，以及本单元使用哪一种页码规则。
- Word 实现提醒：页眉、页脚、页码格式、页边距、横竖版最终都落在 Word section 上；单元负责声明需要什么，渲染层只在这些 section 级属性变化时新开 section，并断开上一节页眉页脚继承。
- 学校模板未说明的样式、结构和规则，不写入本校专属测试标准；后续如需中国论文通用默认规则，应放到共享默认规则中统一补充，并明确不是本校源模板证据。

湖南农业本校先验判断
================================================================================
- 源文件由“论文格式说明”和“学校固定表单”组成。封面、诚信声明、目录、正文题名信息、中英文摘要、正文、参考文献、致谢、附录以及后置固定表单都出现在同一源文件中。
- 源文件可见顺序是：封面 -> 诚信声明 -> 目录 -> 正文题名信息 -> 中文摘要 -> 英文摘要 -> 正文 -> 参考文献 -> 致谢 -> 附录 -> 毕业设计任务书 -> 开题报告 -> 开题论证记录表 -> 答辩记录表 -> 题目变更审批表 -> 成绩评定表。
- 封面、诚信声明、毕业设计任务书、开题报告、开题论证记录表、答辩记录表、题目变更审批表、成绩评定表属于学校固定模板/固定表单内容，当前阶段不自动填写签名、日期、意见、成绩、勾选项。
- 正文题名信息、中英文摘要在源文件中不是独立的摘要页，而是正文首页前的题名/作者/导师/学院信息和内嵌摘要标签。
- 目录明确要求标明一级、二级、三级标题；源模板同时给出两套正文标题体系：农理工类使用 1 / 2.1 / 2.1.1，文法经管类使用 一、 / （一） / 1、。生成测试标准时应拆成“湖南农业大学-农理工类模板”和“湖南农业大学-文法经管类模板”两个变体；同一份目标输出不得混用两套编号体系。
- 源文件没有独立“图目录”“表目录”页，也没有完整图题/表题规范；只说明“如有图、表可做适当调整”。本审查不把图目录/表目录列为湖南农业官方模板单元。

================================================================================
1. 单元顺序（第一层级）
================================================================================

1.1 封面（cover）
  顺序=10；状态=required；来源=学校模板格式说明 + 封面示例；另起页=文档首页
  处理：按固定模板块处理，可从源模板封面示例复制最终可见版面；不填任何封面字段；附件标题、括号格式说明和条件说明文字不进入最终输出。
  同页约束：封面整体模块必须完整落在同一页；学校名称、论文类型、题名、英文题名、学生信息和提交日期不得溢出到下一页。
  依据：源模板 p0-p20；visual page 001。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：把封面改为固定模板块策略，可直接复制源模板最终可见封面版面；同时明确附件标题、括号格式说明和条件说明文字只作证据，不进入成品。

1.2 诚信声明（integrity_statement）
  顺序=20；状态=manual_only；来源=学校模板固定声明；另起页=是；分页隔离=是；不要求新 section，除非页眉/页脚/页码/页边距/横竖版变化
  处理：按固定模板块处理，可直接复制源模板诚信声明页；保留声明标题、正文、作者签名和日期空位，不自动填写签名和日期。
  同页约束：诚信声明标题、声明正文、作者签名和日期应作为同一固定页整体保留；签名/日期不得单独掉到下一页。
  依据：源模板 p23-p32；visual page 002。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：诚信声明改为固定模板块策略，可直接复制源模板声明页；保留签名/日期空位且不自动填写，同时维持 `另起页=是；分页隔离=是`。

1.3 目录（toc）
  顺序=30；状态=required；来源=学校目录格式说明 + 手写目录示例；另起页=是；分页隔离=是；允许跨页=是；不要求新 section，除非页眉/页脚/页码/页边距/横竖版变化
  处理：源模板目录是手写示例；目标输出可用 Word TOC 字段或等价目录生成机制生成目录；目录层级到 3 级。目录可跨多页；目录结束后，正文题名信息必须从下一页开始，不能接在目录最后一页空白处。
  依据：源模板 p51-p80；school.yaml toc.max_level=3。
  注意：目录示例中合法出现“摘要”“关键词”“1前言”“参考文献”“致谢”“附录”等条目，不能误判为正文内容泄漏。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：把 `来源=Word 自动目录` 改成“学校目录格式说明 + 手写目录示例”；处理方式改为“目标输出可用 Word TOC 字段或等价目录生成机制”；并补充 `分页隔离=是、允许跨页=是`，目录末页空白处不得放下一单元。

1.4 正文题名信息（body_title_block）
  顺序=40；状态=required；来源=学校模板 + 元数据；另起页=随正文首页
  处理：保留中文题名、学生、指导老师、学院/学校地址等可见信息段落；当前阶段不自动填这些字段；不要求源模板存在 content controls。
  依据：源模板 p81-p87；page_contract body_title_block。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：把“信息槽位”改成“可见信息段落”，并明确不要求源模板存在 content controls。

1.5 中文摘要（abstract_cn）
  顺序=50；状态=required；来源=学生内容；另起页=否；允许同页=是
  处理：使用内嵌“摘  要：”标签和“关键词：”标签；填学生中文摘要和中文关键词；剥离源模板中的括号格式说明文字。
  依据：源模板 p88-p89。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：在处理规则中补充“剥离源模板中的括号格式说明文字”，避免把 `（小四黑体）` 等说明输出到成品正文。

1.6 英文摘要（abstract_en）
  顺序=60；状态=required；来源=学生内容 + 元数据；另起页=否；允许同页=是
  处理：保留英文题名、Student、Tutor、英文学院/学校地址、Abstract 和 Key words 标签；填学生英文摘要和英文关键词；剥离源模板中的括号格式说明文字。
  依据：源模板 p91-p97。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：在处理规则中补充“剥离源模板中的括号格式说明文字”，并保留规范化后的 Abstract / Key words 标签。

1.7 正文主体（body_main）
  顺序=70；状态=required；来源=学生内容；另起页=否；允许同页=是
  处理：按农理工类或文法经管类标题体系进入正文内容流；正文段落和标题按源模板规则处理；本校专属标准不定义图、表、公式的题名、编号、结构或样式。
  依据：源模板 p99-p119；school.yaml heading_numbering.scheme=chapter_prefixed。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：删除图、表、公式的通用默认处理，只保留“本校专属标准不定义这些规则”；默认规则后续放共享默认规则中统一补充。

1.8 参考文献（references）
  顺序=80；状态=required；来源=学生参考文献；另起页=否/未要求
  处理：保留标题“参考文献”；填参考文献条目。
  依据：源模板 p121-p123；HNAU-REQ-0006。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将 `另起页=是` 改为 `另起页=否/未要求`；原始 DOCX 中参考文献标题前无显式 OOXML 分页符、分节符或 `pageBreakBefore`。

1.9 致谢（acknowledgement）
  顺序=90；状态=template_default_optional；来源=学校模板 + 学生内容；另起页=否/未要求
  处理：草稿/审阅输出默认保留；填学生致谢；无内容时保留标题、占位和评论。
  依据：源模板 p126-p127；目录示例 p66/p79。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将 `另起页=是` 改为 `另起页=否/未要求`；原始 DOCX 中致谢标题前无显式 OOXML 分页符、分节符或 `pageBreakBefore`。

1.10 附录（appendix）
  顺序=100；状态=template_default_optional；来源=学校模板 + 学生内容；另起页=否/未要求；具体附录条目可另起页
  处理：源模板说明“没有附录的不标注”，但草稿/审阅输出可默认保留并提示学生确认；正式输出是否删除需人工确认。
  依据：源模板 p130-p136；目录示例 p67。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将附录总单元 `另起页=是` 改为 `另起页=否/未要求`，并单独保留“具体附录条目可另起页”；原始 DOCX 中“附录1（另起一页）”只约束附录条目。

1.11 毕业设计任务书（design_task）
  顺序=110；状态=manual_only；来源=学校模板固定表单；另起页=是；分页隔离=是；允许跨页=是；不要求新 section，除非页眉/页脚/页码/页边距/横竖版变化
  处理：保留固定表单和填写说明；不自动填学生信息、课题来源勾选、进度安排、签名日期。
  同页约束：固定表单内的标题、学生信息表、选题表、参考资料/进度表、填写说明分别作为固定版面块保留；表格行和签名日期区不得被拆成普通正文。
  依据：源模板 p146-p197；tables 0-2；HNAU-REQ-0007。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将本表单改为 `另起页=是；分页隔离=是；允许跨页=是`，并只声明“不要求新 section”。表单可自然跨页，但下一单元不能接在本表单最后一页空白处。

1.12 开题报告（proposal）
  顺序=120；状态=manual_only；来源=学校模板固定表单；另起页=是；分页隔离=是；允许跨页=是；不要求新 section，除非页眉/页脚/页码/页边距/横竖版变化
  处理：保留固定表单；不自动填文献综述、研究方案、论证小组意见、签名日期。
  同页约束：开题报告表格结构和意见/签名区作为固定表单块保留，不按普通正文分页拆散。
  依据：源模板 p201-p207；tables 3-4。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将本表单改为 `另起页=是；分页隔离=是；允许跨页=是`，并只声明“不要求新 section”。表单可自然跨页，但下一单元不能接在本表单最后一页空白处。

1.13 开题论证记录表（proposal_record）
  顺序=130；状态=manual_only；来源=学校模板固定表单；另起页=是；分页隔离=是；允许跨页=是；不要求新 section，除非页眉/页脚/页码/页边距/横竖版变化
  处理：保留固定记录表；不自动填写记录人、论证质疑、学生回答、签名日期。
  同页约束：记录表表格结构作为固定表单块；签名和论证地点/日期不得单独掉页。
  依据：源模板 p209-p212；table 5。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将本表单改为 `另起页=是；分页隔离=是；允许跨页=是`，并只声明“不要求新 section”；同页约束仍落在表格结构、签名和地点日期这些局部关系上。

1.14 答辩记录表（defense_record）
  顺序=140；状态=manual_only；来源=学校模板固定表单；另起页=是；分页隔离=是；允许跨页=是；不要求新 section，除非页眉/页脚/页码/页边距/横竖版变化
  处理：保留固定记录表；不自动填写答辩质疑、学生答辩记录、成员签名、日期。
  同页约束：答辩记录表表格结构作为固定表单块；签名区不得单独掉页。
  依据：源模板 p214-p217；table 6。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将本表单改为 `另起页=是；分页隔离=是；允许跨页=是`，并只声明“不要求新 section”；同页约束仍落在表格结构和签名区这些局部关系上。

1.15 题目变更审批表（topic_change_approval）
  顺序=150；状态=manual_only；来源=学校模板固定表单；另起页=是；分页隔离=是；允许跨页=是；不要求新 section，除非页眉/页脚/页码/页边距/横竖版变化
  处理：保留固定审批表；不自动填写变更前/后题目、变更原因、意见、签名日期。
  同页约束：审批表表格结构作为固定表单块；意见和签名区不得单独掉页。
  依据：源模板 p218-p223；table 7。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将本表单改为 `另起页=是；分页隔离=是；允许跨页=是`，并只声明“不要求新 section”；同页约束仍落在表格结构、意见和签名区这些局部关系上。

1.16 成绩评定表（grade_form）
  顺序=160；状态=manual_only；来源=学校模板固定表单；另起页=是；分页隔离=是；允许跨页=是；不要求新 section，除非页眉/页脚/页码/页边距/横竖版变化
  处理：保留固定成绩评定表；不自动填写摘要、评语、成绩、委员会意见、签名日期。
  同页约束：成绩评定表表格结构作为固定表单块；成绩、评语、签名日期区不得拆成普通正文。
  依据：源模板 p224-p227；table 8。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将本表单改为 `另起页=是；分页隔离=是；允许跨页=是`，并只声明“不要求新 section”；同页约束仍落在表格结构和评定/签名区这些局部关系上。

================================================================================
2. 单元内容、顺序与样式（第二层级）
================================================================================

2.1 封面（cover）
  页眉：无
  页码：无
  同页约束：封面整体模块必须保持在一个页面内；若学生题目过长导致溢出，应标记为版面问题或人工调整项。
  模板块策略：可直接使用源 DOCX 封面成品块作为版面基准；“附件1 封面基本格式”、括号字号/空行说明、“所做的为论文/设计”等说明文字只作为证据，复制时应删除或转为内部规则，不进入最终论文。
  元素顺序：1 学校名称；2 论文类型标题；3 中文题名；4 英文题名；5 学生基本信息；6 地点；7 提交日期。
  元素：
    - 学校名称
      类型：固定；是否填充：否
      内容：湖 南 农 业 大 学
      样式：华文行楷；26pt（一号）；加粗；居中；单倍行距。
    - 论文类型标题
      类型：固定+条件；是否填充：否
      内容：全日制普通本科生毕业论文(设计)
      条件：所做为论文，则标题中“设计”不要；所做为设计，则标题中“论文”不要。
      样式：黑体；26pt（一号）；加粗；居中；单倍行距。
    - 中文题名
      类型：填充；是否填充：当前阶段否
      内容：毕业论文（设计）中文题目
      样式：黑体；18pt（小二）；加粗；居中。
    - 英文题名
      类型：填充；是否填充：当前阶段否
      内容：TITLE OF GRADUATION PAPER
      样式：Times New Roman；14pt（四号）；加粗；大写；居中。
    - 学生基本信息
      类型：固定标签 + 手工填写；是否填充：否
      内容：学生姓名：；学□□号：；年级专业及班级：；指导老师及职称：；学□□院：。
      排版关系：源模板说明除这 5 行基本信息外，其余内容均居中；基本信息行左侧有 6 个中文字符宽空白。
      样式：标签黑体；16pt（三号）；加粗；填写值楷体；16pt（三号）；加粗。
    - 地点
      类型：固定；是否填充：否
      内容：湖南·长沙
      样式：黑体；15pt（小三）；不加粗；首行缩进约 11 字符；单倍行距；视觉上位于封面下方中部。
    - 提交日期
      类型：固定标签 + 手工填写；是否填充：否
      内容：提交日期：20××年××月
      样式：黑体；15pt（小三）；不加粗；首行缩进约 9 字符；单倍行距。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：补充封面“固定模板块”策略，说明可复制源 DOCX 封面成品块，但附件标题、括号格式说明和条件说明文字不得进入成品；学生基本信息标签也已补齐冒号和源模板空格形态。

2.2 诚信声明（integrity_statement）
  页眉：无
  页码：无
  同页约束：本单元是固定模板页；标题、声明正文、签名和日期应保持同页。
  模板块策略：可直接复制源 DOCX 诚信声明页的最终可见内容；作者签名和日期保留为空白手填项，不从学生正文填充，也不改写声明正文。
  元素顺序：1 学校/论文类型行；2 诚 信 声 明；3 声明正文；4 作者签名；5 日期。
  元素：
    - 学校/论文类型行
      类型：固定；是否填充：否
      内容：湖南农业大学全日制普通本科生毕业论文（设计）
      样式：黑体；18pt（小二）；居中；不加粗；单倍行距。
    - 诚 信 声 明
      类型：固定；是否填充：否
      内容：诚 信 声 明
      样式：黑体；18pt（小二）；居中；不加粗；单倍行距。
    - 声明正文
      类型：固定；是否填充：否
      内容：本人郑重声明：所呈交的本科毕业论文（设计）是本人在指导老师的指导下，进行研究工作所取得的成果，成果不存在知识产权争议。除文中已经注明引用的内容外，本论文不含任何其他个人或集体已经发表或撰写过的作品成果。对本文的研究做出重要贡献的个人和集体在文中均作了明确的说明并表示了谢意。本人完全意识到本声明的法律结果由本人承担。
      样式：宋体；12pt（小四）；两端对齐；首行缩进 2 字符；1.5 倍行距。
    - 作者签名
      类型：固定表单项；是否填充：否
      内容：毕业论文（设计）作者签名：
      样式：宋体；14pt（四号）；不加粗；左侧空格定位；单倍行距。
    - 日期
      类型：固定表单项；是否填充：否
      内容：年    月    日
      样式：宋体；14pt（四号）；不加粗；左侧空格定位；单倍行距。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：补充诚信声明可直接复制源 DOCX 固定声明页的策略；签名和日期保留为空白手填项，不自动填充；页顶“湖南农业大学全日制普通本科生毕业论文（设计）”仍是正文固定行，不是 Word header。

2.3 目录（toc）
  页眉：无
  页码：源模板无页码字段；目标输出如启用页码，见 3.2。
  元素顺序：1 目录标题；2 目录生成机制；3 农理工类/文科类目录条目。
  元素：
    - 目录标题
      类型：固定；是否填充：否
      内容：目  录
      样式：黑体；22pt（二号）；居中；段前=36pt；段后=24pt；1.5 倍行距。
    - 目录生成机制
      类型：生成；是否填充：系统生成
      内容：源模板是手写目录示例；目标输出可使用 Word TOC 字段或等价目录生成机制；目录必须标明一级、二级、三级标题。
      目录条目：摘要、关键词、正文标题、参考文献、致谢、附录。
    - 目录结果条目
      类型：生成结果；是否填充：系统生成
      内容：目标输出的页码由目录生成机制产生；源模板目录中的页码只是手写示例数字，不能作为固定文本保留。
      样式：宋体；12pt（小四）；1.5 倍行距；分散对齐。
      注意：源模板目录示例中“摘要”“关键词”是不带冒号的合法目录条目。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：把元素名从“自动目录字段”改为“目录生成机制”；目录结果说明改为“目标输出生成，源模板页码为手写示例数字”。

2.4 正文题名信息（body_title_block）
  页眉：默认无
  页码：源模板无页码字段；目标输出如启用页码，见 3.2。
  元素顺序：1 中文题名；2 学生；3 指导老师；4 学院/学校地址。
  排版关系：位于目录之后、中文摘要之前；各元素独立成段，按源模板说明视觉居中；学生行可用空格/缩进定位，不要求 Word `jc=center`。
  元素：
    - 中文题名
      类型：填充；是否填充：当前阶段否
      内容：毕业论文（设计）中文题目
      样式：黑体；18pt（小二）；加粗；居中；固定值 22pt 行距。
    - 学生
      类型：固定标签 + 填充；是否填充：当前阶段否
      内容：学生：×××
      样式：宋体；10.5pt（五号）；视觉居中；可用空格/缩进定位。
    - 指导老师
      类型：固定标签 + 填充；是否填充：当前阶段否
      内容：指导老师：×××
      样式：宋体；10.5pt（五号）；居中。
    - 学院/学校地址
      类型：固定格式 + 填充学院；是否填充：当前阶段否
      内容：(湖南农业大学××××学院，长沙 410128)
      样式：宋体/Times New Roman；10.5pt（五号）；居中。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：页码说明改为“源模板无页码字段；目标输出如启用见 3.2”；排版关系和学生行样式改为“视觉居中，可用空格/缩进定位”。

2.5 中文摘要（abstract_cn）
  页眉：默认无
  页码：源模板无页码字段；目标输出如启用页码，见 3.2。
  缺失处理：如果没有识别到中文摘要或关键词，保留占位并添加人工评论。
  元素顺序：1 摘  要标签；2 中文摘要正文；3 关键词标签；4 中文关键词内容。
  排版关系：“摘  要：”与摘要正文同段；“关键词：”与关键词内容同段。
  元素：
    - 摘  要标签
      类型：固定；是否填充：否
      内容：摘  要：
      样式：黑体；12pt（小四）；左对齐；固定值 22pt 行距；首行缩进 2 字符。
    - 中文摘要正文
      类型：填充；是否填充：是
      内容：学生中文摘要。
      样式：宋体；10.5pt（五号）；两端对齐；固定值 22pt 行距。
    - 关键词标签
      类型：固定；是否填充：否
      内容：关键词：
      样式：黑体；12pt（小四）；与关键词内容同段；冒号后接关键词内容。
    - 中文关键词内容
      类型：填充；是否填充：是
      内容：学生中文关键词。
      分隔符：源模板示例使用中文分号“；”。
      样式：宋体；10.5pt（五号）。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：页码说明改为“源模板无页码字段”；关键词标签样式改为具体黑体 12pt；并保留剥离括号格式说明的规则。

2.6 英文摘要（abstract_en）
  页眉：默认无
  页码：源模板无页码字段；目标输出如启用页码，见 3.2。
  缺失处理：如果没有识别到英文摘要或关键词，保留占位并添加人工评论。
  元素顺序：1 英文题名；2 Student；3 Tutor；4 英文学院/学校地址；5 Abstract 标签；6 英文摘要正文；7 Key words 标签；8 英文关键词内容。
  排版关系：英文题名、Student、Tutor、英文学院/学校地址各自独立成段；“Abstract:”与英文摘要正文同段；“Key words:”与关键词内容同段。
  元素：
    - 英文题名
      类型：填充；是否填充：是
      内容：Title of Graduation Paper
      样式：Times New Roman；14pt（四号）；加粗；居中。
    - Student
      类型：固定标签 + 填充；是否填充：是
      内容：Student: ×××
      样式：Times New Roman；10.5pt（五号）；视觉居中；可用缩进定位。
    - Tutor
      类型：固定标签 + 填充；是否填充：是
      内容：Tutor: ××××
      样式：Times New Roman；10.5pt（五号）；视觉居中；可用缩进定位。
    - 英文学院/学校地址
      类型：固定格式 + 填充学院英文名；是否填充：是
      内容：(College of ×××××××, Hunan Agricultural University, Changsha 410128, China)
      样式：Times New Roman；10.5pt（五号）；居中。
    - Abstract 标签
      类型：固定；是否填充：否
      内容：Abstract:
      样式：Times New Roman；12pt（小四）；加粗；左对齐；固定值 22pt 行距；首行缩进 2 字符。
    - 英文摘要正文
      类型：填充；是否填充：是
      内容：学生英文摘要。
      样式：Times New Roman；10.5pt（五号）；两端对齐；固定值 22pt 行距。
    - Key words 标签
      类型：固定；是否填充：否
      内容：Key words:
      样式：Times New Roman；12pt（小四）；加粗；与英文关键词内容同段。
    - 英文关键词内容
      类型：填充；是否填充：是
      内容：学生英文关键词。
      分隔符：源模板示例使用分号。
      样式：Times New Roman；10.5pt（五号）。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：页码说明改为“源模板无页码字段”；Student/Tutor 样式改为视觉居中且可缩进定位；Key words 标签补充 12pt 加粗；保留 Abstract/Key words 规范化规则。

2.7 正文主体（body_main）
  页眉：默认无或随正文 section，源文件未给出独立页眉文字
  页码：源模板无页码字段；目标输出如启用页码，见 3.2。
  缺失处理：如果没有识别到正文内容，保留正文占位并添加人工评论。
  模板变体：
    - 湖南农业大学-农理工类模板：使用 1 / 2.1 / 2.1.1 标题编号体系。
    - 湖南农业大学-文法经管类模板：使用 一、 / （一） / 1、 标题编号体系。
    - 同一份目标输出只能选择一个正文标题变体，不得在正文主体中混用两套编号体系。
  元素顺序：正文主体是内容流；按所选模板变体和学生论文顺序输出标题、正文段落、列表等本校已定义的正文内容。
  变体 A：湖南农业大学-农理工类模板
    - 一级标题
      类型：填充；是否填充：是
      内容：1 前言 / 2 标题 / 5 结论。
      样式：黑体；15pt（小三）；左对齐；段前=12pt；段后=6pt；固定值 22pt 行距；大纲级别=1。
      编号规则：顶格书写序数，空一格写标题。
    - 二级标题
      类型：填充；是否填充：是
      内容：2.1 标题。
      样式：黑体；14pt（四号）；左对齐；段前=12pt；段后=6pt；固定值 22pt 行距；大纲级别=2。
    - 三级标题
      类型：填充；是否填充：是
      内容：2.1.1 标题。
      样式：黑体；12pt（小四）；左对齐；段前=12pt；段后=6pt；固定值 22pt 行距；大纲级别=3。
  变体 B：湖南农业大学-文法经管类模板
    - 一级标题
      类型：填充；是否填充：是
      内容：一、标题。
      样式：黑体；15pt（小三）；左对齐；段前=12pt；段后=6pt；固定值 22pt 行距；大纲级别=1。
    - 二级标题
      类型：填充；是否填充：是
      内容：（一）标题。
      样式：黑体；14pt（四号）；左对齐；段前=12pt；段后=6pt；固定值 22pt 行距；大纲级别=2。
    - 三级标题
      类型：填充；是否填充：是
      内容：1、标题。
      样式：黑体；12pt（小四）；左对齐；段前=12pt；段后=6pt；固定值 22pt 行距；大纲级别=3。
    - 识别注意
      内容：后置固定表单说明项中也会出现“一、二、三、”等序号；只有位于正文主体边界内的段落才按文法经管类标题识别。
  共同内容元素：
    - 正文段落
      类型：填充；是否填充：是
      内容：学生正文。
      样式：中文宋体、英文 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0；段后=0；固定值 22pt 行距。
  本校未定义的正文对象：
    - 图、表、公式
      来源说明：源模板只写“如有图、表可做适当调整”，未给出图题位置、表题位置、双语要求、编号样例、字体、表格边框、公式编号或正斜体要求。
      处理：湖南农业本校专属测试标准不列这些对象的结构和样式；若学生正文出现图、表、公式，由共享默认规则或后续通用规范处理。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：正文主体拆成“湖南农业大学-农理工类模板”和“湖南农业大学-文法经管类模板”两个变体，并明确同一份目标输出不能混用两套标题编号体系；删除本校未明示的图/表/公式默认结构、默认样式和同页约束。

2.8 参考文献（references）
  页眉：默认无或随正文 section
  页码：源模板无页码字段；目标输出如启用页码，见 3.2。
  缺失处理：如果没有识别到参考文献，保留标题、占位和人工评论。
  元素顺序：1 参考文献；2 参考文献条目。
  元素：
    - 参考文献
      类型：固定；是否填充：否
      内容：参考文献
      位置：第 1 个元素；独立段落；不要求另起页。
      样式：黑体；15pt（小三）；左对齐；段前=12pt；段后=6pt；固定值 22pt 行距。
    - 参考文献条目
      类型：填充；是否填充：是
      内容：学生参考文献条目。
      编号：使用 [1] 形式，编号后接空格。
      样式：宋体/Times New Roman；10.5pt（五号）；左对齐；固定值 22pt 行距。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：页码说明改为“源模板无页码字段”；参考文献标题位置从“另起页”改成“不要求另起页”。

2.9 致谢（acknowledgement）
  页眉：默认无或随正文 section
  页码：源模板无页码字段；目标输出如启用页码，见 3.2。
  缺失处理：源文档未识别到致谢内容时，草稿/审阅输出保留本页并写入“【源文档中未识别到本页内容；如学校不要求，可删除本页。】”。
  元素顺序：1 致  谢；2 致谢正文。
  元素：
    - 致  谢
      类型：固定；是否填充：否
      内容：致  谢
      样式：黑体；15pt（小三）；居中；段前=24pt；段后=12pt；固定值 22pt 行距。
    - 致谢正文
      类型：填充；是否填充：是
      内容：学生致谢。
      样式：宋体/Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；固定值 22pt 行距。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：页码说明改为“源模板无页码字段”；本单元不再要求另起页，只保留标题、正文、缺失占位和样式规则。

2.10 附录（appendix）
  页眉：默认无或随正文 section
  页码：源模板无页码字段；目标输出如启用页码，见 3.2。
  缺失处理：源文档未识别到附录内容时，草稿/审阅输出可保留本页并写入“【源文档中未识别到本页内容；如学校不要求，可删除本页。】”；正式输出是否删除需人工确认。
  元素顺序：1 附录；2 附录条目/正文。
  元素：
    - 附录
      类型：固定；是否填充：否
      内容：附录
      样式：黑体；15pt（小三）；左对齐；固定值 22pt 行距。
    - 附录条目/正文
      类型：填充；是否填充：是
      内容：附录1、附录2 等材料；附录内容字体字号参照正文格式。
      样式：正文类内容默认使用正文样式；复杂材料按其自身结构保留。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：页码说明改为“源模板无页码字段”；附录总单元不要求另起页，仅保留具体附录条目可另起页的解释。

2.11 毕业设计任务书（design_task）
  页眉：无
  页码：无
  同页约束：本单元由多页学校固定表单组成，不要求整个任务书同页，但每个表格/签名区/填写说明块应作为固定版面块保留。
  模板块策略：直接保留源 DOCX 对应的多页固定表单块；Markdown 只记录标题、表格语义锚点、填写说明、备注和分页隔离要求，真实结构以源表格快照/OOXML 和渲染结果验收。
  元素顺序：1 标题行；2 学生信息表；3 日期；4 毕业设计题目/选题来源/选题性质/主要内容和要求表；5 参考资料与进度安排表；6 填写说明；7 备注。
  元素：
    - 标题行
      类型：固定；是否填充：否
      内容：湖南农业大学全日制普通本科生；毕业设计任务书
      样式：宋体；26pt（一号）；加粗；居中；段前约 7.8pt；段后约 7.8pt；单倍行距。
    - 学生信息表
      类型：固定表单；是否填充：否
      内容：学生姓名；学号；年级专业及班级；指导教师及职称；学院。
      表格关系：源模板 table 0；学生信息字段为空白或占位。
    - 日期
      类型：固定表单项；是否填充：否
      内容：20    年     月     日
    - 选题/要求表
      类型：固定表单；是否填充：否
      内容：毕业设计题目；选题来源；□结合科研课题；课题名称；□生产实际或社会实际；□其他；选题性质；□基础研究；□应用研究；□其他；主要内容和要求。
      表格关系：源模板 table 1。
    - 参考资料与进度安排表
      类型：固定表单；是否填充：否
      内容：主要中文参考资料与外文资料；工作进度安排；起止日期；主要工作内容。
      表格关系：源模板 table 2。
    - 填写说明
      类型：固定；是否填充：否
      内容：填写说明；一、毕业设计任务书是学校根据已经确定的毕业设计题目下达给学生的一种教学文件，是学生在指导教师指导下独立从事毕业设计工作的依据。此表由指导教师填写。二、此任务书必需针对每一位学生，不能多人共用。三、选题要恰当，任务要明确，难度要适中，份量要合理，使每个学生在规定的时限内，经过自己的努力，可以完成任务书规定的设计研究内容。四、任务书一经下达，不得随意更改。五、各栏填写基本要求。六、本表可从毕业论文管理系统填写打印或教务处网站下载中心下载填写打印，但签名栏必须相应责任人亲笔签名，且应用黑色签字笔填写。
    - 备注
      类型：固定；是否填充：否
      内容：注：此表如不够填写，可另加附页。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：补充固定模板块策略，毕业设计任务书应直接保留源 DOCX 多页表单块；Markdown 只记录语义锚点和验收口径，不作为重建版式的唯一来源。

2.12 开题报告（proposal）
  页眉：无
  页码：无
  同页约束：固定表单块和签名/意见区不得被拆成普通正文。
  模板块策略：直接保留源 DOCX 开题报告固定表单块；文献综述、研究方案、进程计划、论证小组意见等大块空位不自动填，后续如需填充也应在源表格结构内填入。
  元素顺序：1 标题；2 学院；3 学生/论文信息表；4 文献综述；5 研究方案；6 进程计划；7 论证小组意见/成员签名/地点日期；8 注释。
  元素：
    - 标题
      类型：固定；是否填充：否
      内容：湖南农业大学全日制普通本科生毕业论文；开题报告
    - 学院
      类型：固定表单项；是否填充：否
      内容：学  院：
    - 学生/论文信息表
      类型：固定表单；是否填充：否
      内容：学生姓名；学号；年级专业及班级；指导教师及职称；毕业论文题目；文献综述（选题研究意义、国内外研究现状、主要参考文献等，不少于1000字）。
      表格关系：源模板 table 3。
    - 研究方案/进程计划/论证意见表
      类型：固定表单；是否填充：否
      内容：研究方案（研究目的、内容、方法、预期成果、条件保障等）；进程计划（各研究环节的时间安排、实施进度、完成程度等）；论证小组意见；论证小组；成员签名；论证地点；论证日期。
      表格关系：源模板 table 4。
    - 注释
      类型：固定；是否填充：否
      内容：注：此表如不够填写，可另加页。注：1.此表为做毕业论文的同学填写。2.此表可用黑色签字笔填写，也可打印，但意见栏必须相应责任人亲笔填写。3.此表可从毕业论文管理系统填写打印或教务处网站下载中心下载。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：补充固定模板块策略，开题报告应直接保留源 DOCX 表单块；可填区域保留在表格内，不把表格拆成普通正文。

2.13 开题论证记录表（proposal_record）
  页眉：无
  页码：无
  同页约束：固定记录表、签名区、论证地点/日期应作为同一表单块或连续表单块保留。
  模板块策略：直接保留源 DOCX 开题论证记录表模板块；记录人、质疑、回答、签名、地点和日期均作为手填空位保留。
  元素顺序：1 标题；2 学院/记录人；3 记录表；4 注释。
  元素：
    - 标题
      类型：固定；是否填充：否
      内容：湖南农业大学全日制普通本科生毕业论文（设计）；开题论证记录表
    - 学院/记录人
      类型：固定表单项；是否填充：否
      内容：学  院：                                         记录人：
    - 记录表
      类型：固定表单；是否填充：否
      内容：学生姓名；学号；年级专业及班级；指导教师姓名；指导教师职称；论文（设计）题目；论证小组质疑；学生回答简要记录；论证小组组长签名；论证地点；论证日期。
      表格关系：源模板 table 5。
    - 注释
      类型：固定；是否填充：否
      内容：注：此表可从毕业论文管理系统或教务处网站下载中心下载。记录、签名栏必须用黑色笔手工填写。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：补充固定模板块策略，开题论证记录表应直接保留源 DOCX 模板块；记录人、质疑、回答、签名、地点和日期均不自动填。

2.14 答辩记录表（defense_record）
  页眉：无
  页码：无
  同页约束：固定记录表和签名区不得拆成普通正文。
  模板块策略：直接保留源 DOCX 答辩记录表模板块；答辩质疑、学生答辩记录、成员签名、地点和日期均作为手填空位保留。
  元素顺序：1 标题；2 学院/记录人；3 答辩记录表；4 注释。
  元素：
    - 标题
      类型：固定；是否填充：否
      内容：湖南农业大学全日制普通本科生毕业论文（设计）；答 辩 记 录 表
    - 学院/记录人
      类型：固定表单项；是否填充：否
      内容：学  院：                                        记录人：
    - 答辩记录表
      类型：固定表单；是否填充：否
      内容：学生姓名；学号；年级专业及班级；指导教师姓名；指导教师职称；论文（设计）题目；答辩小组质疑；学生答辩简要记录；答辩小组成员签名；答辩地点；答辩日期。
      表格关系：源模板 table 6。
    - 注释
      类型：固定；是否填充：否
      内容：注：此表可从毕业论文管理系统或教务处网站下载中心下载。记录、签名栏必须用黑色笔手工填写。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：补充固定模板块策略，答辩记录表应直接保留源 DOCX 模板块；答辩质疑、答辩记录、成员签名、地点和日期均不自动填。

2.15 题目变更审批表（topic_change_approval）
  页眉：无
  页码：无
  同页约束：固定审批表表格结构保留；意见和签名区不得单独掉页。
  模板块策略：直接保留源 DOCX 题目变更审批表模板块；Markdown 只记录语义锚点和 table 7 结构契约，不负责复刻复杂表格视觉结构。
  元素顺序：1 标题；2 学院；3 审批表；4 注释。
  元素：
    - 标题
      类型：固定；是否填充：否
      内容：湖南农业大学全日制普通本科生毕业论文（设计）；题目变更审批表
    - 学院
      类型：固定表单项；是否填充：否
      内容：学  院：
    - 审批表
      类型：固定表单；是否填充：否
      内容：学 生 姓 名；学号；年级专业及班级；变更前论文（设计）题目；变更后论文（设计）题目；论文（设计）题目变更原因：；指导教师意见：；签名：；教学基层组织意见：；负责人签名：。
      表格关系：源模板 table 7；7 行固定表格；存在跨列内容区和签名日期区。
      表格结构契约：Markdown 只记录语义锚点；真实验收以源 DOCX table 7 的 OOXML 表格快照为准，检查行列数、合并单元格、边框、列宽、文本锚点、签名日期区和注释是否保留。
    - 注释
      类型：固定；是否填充：否
      内容：注：1.此表可用黑色签字笔填写，也可打印，但意见栏必须相应责任人亲笔填写。2.此表可从毕业论文管理系统或教务处网站下载中心下载。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：补充固定模板块策略，题目变更审批表应直接保留源 DOCX 模板块；审批表内容补齐冒号，并新增 table 7 的表格结构契约。

2.16 成绩评定表（grade_form）
  页眉：无
  页码：无
  同页约束：固定成绩评定表表格结构保留；摘要、评语、成绩、签名日期和答辩委员会意见不得拆成普通正文。
  模板块策略：直接保留源 DOCX 成绩评定表模板块；Markdown 只记录语义锚点和 table 8 结构契约，不负责复刻复杂表格视觉结构。
  元素顺序：1 标题；2 学院；3 成绩评定表；4 注释。
  元素：
    - 标题
      类型：固定；是否填充：否
      内容：湖南农业大学全日制普通本科生毕业论文（设计）；成绩评定表
    - 学院
      类型：固定表单项；是否填充：否
      内容：学  院：
    - 成绩评定表
      类型：固定表单；是否填充：否
      内容：学生姓名；学号；年级专业及班级；指导教师及职称；毕业论文（设计）题目；毕业论文（设计）摘要：；关键词：；指导教师对该学生论文（设计）的评定意见：；指导老师签名：；答辩小组评语：；答辩小组成绩（百分制）：；折合五级记分制成绩：；组长签名：；成绩评定；答辩委员会审查意见：；答辩委员会主任签名：。
      表格关系：源模板 table 8；8 行固定表格；存在摘要/关键词区、评定意见区、答辩评语区、成绩区和委员会审查区。
      表格结构契约：Markdown 只记录语义锚点；真实验收以源 DOCX table 8 的 OOXML 表格快照为准，检查行列数、合并单元格、边框、列宽、文本锚点、签名日期区、成绩栏关系和注释是否保留。
    - 注释
      类型：固定；是否填充：否
      内容：注：1.此表可用黑色签字笔填写，也可打印，但意见栏必须相应责任人亲笔填写。2.各专业学生的整体成绩应符合正态分布，要求优秀比例控制在15%以内，良好、中等和及格的比例控制在75%左右，不及格的比例在10%以下；系（专业）答辩委员会对毕业论文（设计）的答辩小组建议成绩进行审查，对评定等级为优秀或不及格以及答辩评分中有争议的论文（设计）要进行重点审核，最终确定成绩，并向学生公布；五级记分制：优秀（90～100分）、良好（80～89分）、中等（70～79分）、及格（60～69分）和不及格（60分以下）。3. 此表可从毕业论文管理系统或教务处网站下载中心下载。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：补充固定模板块策略，成绩评定表应直接保留源 DOCX 模板块；成绩评定表内容补齐冒号，并新增 table 8 的表格结构契约。

================================================================================
3. 全局规则（第三层级）
================================================================================

3.1 页面、页眉、页脚与 Word section
  页面：
    - 纸张：A4。
    - 正文/目录等常规页边距：上=25.4mm；下=25.4mm；左=26mm；右=26mm。
    - 装订线：0mm。
  证据冲突：
    - 源文档可见说明写上下页边距 2.54cm、左右页边距 2.6cm。
    - 转换后的 DOCX section defaults 显示上下约 20mm、左右 26mm。
    - 审查口径：可见说明优先于转换后的 section defaults。
  页眉/页脚距离：
    - 当前 school.yaml：页眉 15mm；页脚 17.5mm。
    - 源文件未给出明确页眉文字要求。
  Word section 规则：
    - 原始 Hunan DOCX 只有 1 个 section，且 header/footer 文件为空。
    - “另起页/分页隔离”是输出版面要求：本单元从新页开始，下一单元也必须从新页开始，不能接在本单元最后一页空白处。
    - “另起页/分页隔离”不等于源模板已有 OOXML page break，也不等于必须新建 Word section。
    - 目标输出只有在页眉、页脚、页码格式、页边距或横竖版确实变化时才创建或切换 section。
    - 后置固定表单默认不显示页码；如果目标输出启用了正文页码，应通过渲染结果确认页码没有串入表单页。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：补充硬分页定义：`另起页/分页隔离` 是输出版面要求，不等于必须新建 Word section；section 只在页眉/页脚/页码/页边距/横竖版变化时创建。

3.2 页码
  归属：
    - 页码格式、字体字号、起始编号和连续规则属于全局规则。
    - 每个单元只声明使用哪一种页码规则。
  当前证据：
    - 原始 DOCX 没有页码字段，footer 为空。
    - 源文件目录示例中的页码是手写示例数字，不是 Word 更新字段结果。
    - school.yaml 当前将 toc、main_body、references、acknowledgement、appendix 设置为阿拉伯数字页码；cover、integrity_statement、design_task、proposal、defense_record、grade_form 不显示页码。
  审查口径：
    - 封面：不显示页码。
    - 诚信声明：不显示页码。
    - 目录：源模板不提供可更新页码字段；目标输出如按 school.yaml 启用阿拉伯数字页码，需由生成机制产生，不得手打固定数字。
    - 正文、参考文献、致谢、附录：源模板不提供可更新页码字段；目标输出如按 school.yaml 启用阿拉伯数字页码，需由生成机制产生。
    - 后置固定表单：不显示页码。
  不确定项：
    - 源文件未明确说明目录页码和正文页码是否各自从 1 开始；当前 school.yaml 中 toc 和 main_body 都有 page_number_start=1。需要人工确认最终学校要求。
  页码样式：
    - 仅作为目标输出规则待确认：Times New Roman；10.5pt（五号）；居中。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：重写页码规则，明确“原始 DOCX 无页码字段、footer 为空、目录页码为手写示例数字”；阿拉伯数字页码和起始编号只作为 school.yaml/目标输出规则，需人工确认。

3.3 正文基础样式（Normal / Body）
  样式：中文宋体、英文 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0；段后=0；行距=固定值 22pt。
  依据：源模板 p81、p101、p110；HNAU-REQ-0001/0002。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。正文基础样式记录为中文宋体、英文 Times New Roman、小四、两端对齐、首行缩进 2 字符、固定 22pt 行距，与源模板证据一致。

3.4 标题样式、编号与目录层级
  目录层级：
    - 必须标明一级、二级、三级标题。
    - 目录样式：宋体；12pt（小四）；1.5 倍行距；分散对齐。
  农理工类：
    - 一级标题：1 标题；小三号黑体；顶格书写序数；空一格写标题。
    - 二级标题：2.1 标题；四号黑体；顶格书写序数；空一格写标题。
    - 三级标题：2.1.1 标题；小四号黑体；顶格书写序数；空一格写标题。
    - 四级标题：一般不设；如确需，第四层次不单独占行书写。
  文法经管类：
    - 一级标题：一、标题；小三号黑体；顶格书写。
    - 二级标题：（一）标题；四号黑体；顶格书写。
    - 三级标题：1、标题；小四号黑体。
    - 四级标题：不单独占行书写。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。一级到三级目录要求、农理工类 1/2.1/2.1.1 和文法经管类 一、/（一）/1、编号体系均记录完整。

3.5 摘要与关键词全局规则
  中文摘要：
    - 标签为内嵌“摘  要：”，不是独立摘要标题页。
    - 摘要标签小四黑体；摘要正文五号宋体。
    - 关键词标签与关键词内容同段。
  英文摘要：
    - 英文题名四号 Times New Roman 加粗居中。
    - Student / Tutor / 英文学院地址五号 Times New Roman 居中。
    - Abstract 标签小四 Times New Roman 加粗；正文五号 Times New Roman。
    - Key words 标签与英文关键词内容同段。
  段内混排：
    - 摘要/Abstract 标签与正文同段但样式不同，必须以 run 级元素处理，不能整段统一样式后丢失标签样式。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：第一层和第二层已补充“剥离括号格式说明文字、输出规范化标签”；本条保留 run 级混排要求。

3.6 图、表、公式专属规则覆盖范围
  源模板证据：
    - 只明确写“如有图、表可做适当调整”。
    - 未提供图题/表题位置、编号、字体、是否中英文双题名、公式编号等细则。
  本校专属审查口径：
    - 不在湖南农业本校专属测试标准中定义图、表、公式的结构、题名、编号、字体、边框或同页规则。
    - 后续共享默认规则如要求图题、表题、公式编号等，应在共享规则层补充，不能写成本校源模板事实。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：删除目标默认结构、默认同页约束和待确认图表样式清单；本条只记录本校源模板未提供这些细则，默认规则后续放共享层。

3.7 参考文献全局规则
  参考文献标题：黑体；15pt（小三）；左对齐；段前=12pt；段后=6pt；固定值 22pt。
  参考文献条目：宋体/Times New Roman；10.5pt（五号）；左对齐；固定值 22pt。
  编号：使用 [1] 形式，编号后保留空格。
  依据：源模板 p121-p123；HNAU-REQ-0006。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。参考文献标题、条目字体字号、固定 22pt 行距和 [1] 编号后空格规则均有源模板依据。

3.8 模板默认页、固定模板块与固定表单保留策略
  固定模板块：
    - 封面、诚信声明和后置固定表单都属于学校模板拥有的固定块，不应当按普通正文重新排版。
    - 可直接从源 DOCX 复制对应模板块；封面需剥离附件标题、括号格式说明等证据文字；诚信声明需保留固定声明正文和签名/日期空位；后置固定表单需保留源表格结构。
    - Markdown 元素清单用于记录最终可见内容、语义锚点、可填空位、说明文字剥离规则和验收口径，不作为复杂版面的唯一结构来源。
  致谢：
    - 源模板列出致谢；school.yaml required=false。
    - 草稿/审阅输出默认保留标题和占位；正式输出是否删除由学生/学校要求确认。
  附录：
    - 源模板写“没有附录的不标注”。
    - 草稿/审阅输出可保留占位提示；正式输出可按学校要求和学生确认删除。
  后置固定表单：
    - 毕业设计任务书、开题报告、开题论证记录表、答辩记录表、题目变更审批表、成绩评定表属于学校固定表单。
    - 当前 school.yaml 多数标 required=false，page_contract 将其视为 manual_only / conditional-on-presence。
    - 审阅稿应优先保留固定表单页；如最终学校流程不需要某页，应由人工确认后删除。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将保留策略从“后置固定表单”扩展为“固定模板块”，明确封面、诚信声明和后置固定表单都可直接复制源 DOCX 模板块；封面需剥离说明文字，表单需保留源表格结构。

3.9 同页约束与分页完整性
  适用对象：
    - 封面整体模块。
    - 诚信声明整体固定页及签名/日期区。
    - 后置固定表单中的表格、意见区、签名日期区。
    - 标题与紧随其后的第一段或第一项内容。
  审查原则：
    - 封面、诚信声明这类单页固定模板块应保持整页完整；如果题名或签名区溢出，应标记为版面完整性问题。
    - 后置固定表单不要求整个单元同页，可按源模板自然跨页；重点检查表格结构、意见区、签名日期区、标题与首段等局部关系。
    - 学生内容页不要求整个单元同页，只检查局部组约束。
    - 如果同页约束失败，应记为版面完整性问题。
    - 不应为了通过分页而删除固定元素，也不应把同一固定表单拆成多个逻辑单元。
  Word 实现提示：
    - 普通段落可使用“与下段同页”“段中不分页”。
    - 固定模板块应优先保留为源模板版面块；固定表单应优先保留为源模板表格/模板块。
    - 如果固定表单本身超过一页，应保留其原始跨页结构并输出人工调整提示；不要为了压成一页而缩放、删行或重排。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：把封面/诚信声明与后置表单分开表述：单页固定模板块应保持整页完整，跨页表单按源模板跨页结构保留；同时明确不能为压缩分页而删行或重排。

3.10 固定模板块与高风险非样式约束
  固定模板隐藏结构：
    - 固定表格、勾选框、签名线、日期线都属于模板结构。
    - 原始 Hunan 模板未见 cover content controls 或 bookmark slots；不得把这些写成必须从源模板保留的事实。
    - 替换内容时不能只保留可见文字，把这些隐藏结构删掉。
  固定模板块验收：
    - Markdown 不负责完整复刻封面、诚信声明、后置表单的视觉结构；Markdown 负责记录最终可见内容、语义锚点、可填空位、说明文字剥离规则、分页隔离和验收口径。
    - 封面验收应检查最终输出不含“附件1”“一号华文行楷空一行”“根据题目长短四号字空二或三行”等证据说明文字，同时保留学校名称、论文类型、题名、学生信息、地点和提交日期等最终可见结构。
    - 诚信声明验收应检查源模板声明正文、作者签名和日期空位未被改写或误填；页顶固定行是正文固定行，不是 Word header。
  固定表单表格验收：
    - 对毕业设计任务书、开题报告、开题论证记录表、答辩记录表、题目变更审批表、成绩评定表，必须保留源 DOCX 对应 table 的表格结构。
    - 自动化测试应使用源 DOCX 的 table snapshot / OOXML 作为结构基准，检查行列数、gridSpan/vMerge、边框、列宽、单元格文本锚点、签名日期区、勾选框和注释。
    - 渲染测试应把生成 DOCX 转 PDF/图片，检查表格没有被拆成普通段落、签名区没有孤立掉页、分页隔离没有被破坏。
  生成字段：
    - 原始 Hunan 模板未见 Word TOC 字段；目标目录可使用 Word TOC 字段或等价机制生成。
    - 原始 Hunan 模板未见页码字段；目标输出如启用页码，应由页脚字段或等价机制生成，不能手打成普通正文。
  单元边界：
    - 参考文献必须在致谢、附录和后置固定表单之前结束。
    - 附录不得吞掉毕业设计任务书等固定表单。
    - 目录条目里的“摘要”“关键词”“1前言”等不能被误识别为正文内容。
  段内混排：
    - 摘要/关键词标签与内容同段但 run 样式不同。
    - 英文 Abstract / Key words 标签与内容同段但 run 样式不同。
  无页眉/无页码也是规则：
    - 封面、诚信声明、后置固定表单不显示页码。
    - 未显示页眉或页码不是缺失，应作为模板规则记录。
  渲染预检：
    - XML 检查只能证明结构存在，不能证明封面没溢出、签名区没掉页、固定表单没被拆散。
    - 对同页约束、溢出、页码连续性和固定表单完整性，需要渲染后页面级检查或人工 review 标记。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：把“固定表单表格验收”扩展为“固定模板块验收”，新增封面说明文字剥离、诚信声明直接保留和签名日期空位检查；复杂表格仍以源 DOCX table snapshot / OOXML 和渲染结果验收。

================================================================================
4. 实现对齐提醒
================================================================================

4.1 源文件不是最终干净模板
  源文件包含大量说明文字，如“附件1 封面基本格式”“（小二号字空两行）”“（以下农理工科类用）”。
  这些文字应作为提取证据，不应全部进入最终论文正文。实现侧可以复制源 DOCX 的最终可见模板块，但必须先识别并剥离格式说明/证据文字。

4.2 正文题名信息和摘要当前可能被 runtime 漏掉
  README 明确说 page_contract 比当前 generated effect 更严格：body title/student/tutor block 和中英文摘要标签在源文件中是正文前必需模块。
  实现侧需要确保 main body 之前有正文题名信息、中文摘要、英文摘要，而不是直接从正文标题开始。

4.3 后置固定表单的 required=false 不等于静默删除
  school.yaml 将 design_task/proposal/defense_record/grade_form 标为 required=false。
  审查口径是：这些属于学校固定表单，草稿/审阅输出应默认保留或至少可见占位；最终是否删除由人工确认。

4.4 文科类标题识别仍需谨慎
  源文件支持文科类“一、/（一）/1、”标题体系。
  但后置固定表单说明中也出现大量“一、二、三、”说明项，识别时必须结合单元边界，避免把表单说明误判为正文标题。

4.5 页码起始规则需要人工确认
  当前 school.yaml 将目录和正文都配置为阿拉伯数字起始 1。
  源文件未明确说明目录页码和正文页码是否分别起算；需要你检查源模板或学校要求后确认。

4.6 图表公式不纳入本校专属规则
  源文件没有提供具体图题、表题或公式规则。
  本校专属测试标准不定义图、表、公式的默认结构、默认样式、题名位置、编号或同页规则。
  后续如果需要默认图表公式规则，应在共享默认规则中统一补充，不写入湖南农业本校专属标准。

4.7 固定模板块不能只靠 Markdown 验收
  封面、诚信声明、题目变更审批表、成绩评定表等固定模板块包含版面、表格、签名日期区、空白占位和说明文字剥离规则；Markdown 只能表达语义锚点和测试契约，不能作为视觉结构的唯一来源。
  实现侧应为固定模板块保存源 DOCX 版面块或 table snapshot / OOXML 基准；生成后同时做 XML 结构比对和 PDF/图片渲染检查。
  验收重点是：封面不带格式说明文字、诚信声明正文和签名日期空位未改写、表格仍是表格、合并单元格关系未丢失、边框和列宽未明显破坏、签名日期区未掉页、注释和固定标签未被改写或吞掉。

================================================================================
5. 本校总评
================================================================================

5.1 当前审查口径
  湖南农业格式包适合按“单元 -> 元素 -> 子元素/嵌套单元”建模。
  封面、诚信声明和后置行政表单属于学校固定模板块/固定表单，优先保留或复制源 DOCX 对应模板块，再清空或替换可变字段；目录属于系统生成；正文题名信息、中英文摘要、正文、参考文献、致谢、附录承载学生内容或学生元数据。

5.2 需要用户确认的点
  - 正文题名信息是否当前阶段也不自动填，还是可以从元数据填入。
  - 致谢和附录在最终正式输出中，是否允许学生确认后删除。
  - 毕业设计任务书、开题报告、开题论证记录表、答辩记录表、题目变更审批表、成绩评定表是否全部默认保留在审阅稿中。
  - 目录页码和正文页码是否都从 1 开始。

5.3 可以先按本文件执行的点
  - 封面字段当前不自动填。
  - 诚信声明和后置固定表单保留固定内容，不自动填签名日期、意见、成绩或勾选项。
  - 目录收录 1-3 级标题。
  - 正文基本样式使用小四宋体/Times New Roman、固定 22pt 行距。
  - 农理工类标题使用 1 / 2.1 / 2.1.1；文科类标题使用 一、/（一）/1、，但识别需避免和固定表单说明混淆。
~~~~

### Source: `nannong-undergraduate`

- Path: `inputs/school-nannong-undergraduate-template-review.txt`
- SHA-256: `sha256:d6dc0d49dac3e2b83fa63ee92e76965c1cec995d56eb3e27b3ea4d5f45acdb87`

~~~~text
南京农业大学本科生毕业论文（设计）模板审查包 V2
日期：2026-06-09

依据：优先使用学校官方 Word 模板
/Users/fl/ws/gogo/docfit/schools/nannong-undergraduate/sources/nannong_template.docx

辅助证据：
- /Users/fl/ws/gogo/docfit/schools/nannong-undergraduate/README.md
- /Users/fl/ws/gogo/docfit/schools/nannong-undergraduate/page_contract.yaml
- /Users/fl/ws/gogo/docfit/schools/nannong-undergraduate/school.yaml
- /Users/fl/ws/gogo/docfit/schools/nannong-undergraduate/template_manifest.yaml

阅读方式
================================================================================
1. 先核对“单元顺序”：整篇文档有哪些单元，顺序是否对。
2. 再核对“单元内容与顺序”：每个单元有什么元素、元素顺序如何、哪些独立成段、哪些同段连接、哪些是固定模板内容、哪些需要填学生内容。
3. 最后核对“全局规则”：只放真正跨单元共用的页面、页眉页码、字体、目录、图表、参考文献等规则。

写法约定
- 类型=固定：学校模板自带文字、表单、标题或固定页，不从学生正文填充。
- 类型=填充：从学生论文或元数据填入。
- 类型=生成：由 Word 字段或系统生成。
- 固定内容必须显式写出“内容”；固定签名/日期等表单项也要保留学校模板文字，只是不自动填写空白项。
- 模板默认模块应默认保留，不因学生原文暂时缺少对应内容而省略；学生后续删除模块比重新补齐模块更容易。
- 缺失处理：学生内容没有识别到时，模板中应保留占位，并添加人工评论。
- 元素顺序：单元内元素按列出顺序输出；如果该单元用于测试，需显式写出“元素顺序”。
- 位置/排版关系：独立成段、同一段、同行、表格内部、页眉页脚等关系都属于审查项；未写同段关系时，默认该元素相对上一个元素换行并独立成段。
- 同页约束：如果一个单元或一组元素必须作为视觉整体留在同一页，应显式写出“同页约束”。这类约束高于普通换行关系，例如封面整体、声明签名区、图与图名、表名与表体等不能被 Word 自动分页切散。
- 样式只写核对需要的内容：字体、字号、加粗、对齐、缩进、段前、段后、行距、关键段落设置。
- 标题编号、题注编号、目录页码、参考文献序号后的空格/制表符属于模板内容；不应作为普通正文随意手打。
- 页眉/页码分层记录：页眉/页脚距离、页码字体字号、页码格式和连续编号规则放到第三层全局规则；每个单元只写本单元页眉显示文字，以及本单元使用前置页还是正文/后置页页码规则。
- Word 实现提醒：页眉、页脚、页码格式、页边距、横竖版最终都落在 Word section 上；单元负责声明需要什么，渲染层只在这些 section 级属性变化时新开 section，并断开上一节页眉页脚继承。
- 学校模板未说明的结构、样式和规则，不写入本校专属测试标准；后续如需中国论文通用默认规则，应放到共享默认规则中，并明确不是南农源模板事实。

南农本校先验判断
================================================================================
- 官方源模板的可见顺序是：封面 -> 原创性声明/使用授权声明 -> 目录 -> 中文摘要 -> 英文摘要 -> 正文 -> 参考文献 -> 附录 -> 相关的学术成果目录 -> 致谢。
- 当前审查文件以官方源模板可见顺序为准。若 runtime 的 school.yaml/template_manifest 与该顺序冲突，应按本审查口径对齐。
- 官方源模板没有独立“图目录”“表目录”页；本校审查不把它们列为学校模板单元。若后续中国通用标准要求补充图目录/表目录，应作为默认配置单独标注，不应伪装成南农官方模板内容。
- 官方源模板说明“图、表格应有中英文标题”，所以图名和表名默认必须包含中文名和英文名。
- 官方源模板把“第X章 结论与展望”作为正文的最后一章类型；它属于正文主体里的固定结尾章，不作为独立一级单元。章内文字由学生自己写。

================================================================================
1. 单元顺序（第一层级）
================================================================================

1.1 封面（cover）
  顺序=10；状态=required；来源=学校模板；另起页=是
  处理：当前阶段保留学校封面模块；不填任何封面字段；不做字段文字锚点匹配。
  同页约束：封面整体模块必须完整落在同一页；封面底部日期、选项、签名或学校要求的固定字段不得溢出到下一页。
  依据：源模板唯一表格包含“本科生毕业论文（设计）”“题目”“姓名”“学号”“学院”“专业”“指导教师”“职称”“20 年 月 日”等封面字段。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：封面源模板确为 1 个 1x1 表格固定模块；第二层已把“样式必填”占位改为从原始 DOCX 抽取的标题、字段和日期样式。

1.2 原创性声明（originality_statement）
  顺序=20；状态=manual_only；来源=学校模板；另起页=是
  处理：保留固定声明页；不自动填姓名、日期、签名。
  依据：源模板 p2-p7。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 中原创性声明独立位于封面之后，声明正文和论文作者签名/日期均为固定内容，不应自动填写。

1.3 使用授权声明（authorization_statement）
  顺序=30；状态=manual_only；来源=学校模板；另起页=否；允许与原创性声明同页=是
  处理：保留固定授权声明；不自动填作者签名、导师签名、日期。
  依据：源模板 p15-p20；官方模板中原创性声明与使用授权声明在同一页。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 中使用授权声明与原创性声明同属前置固定声明页，允许同页连续出现，签名和日期不自动填写。

1.4 目录（toc）
  顺序=40；状态=required；来源=Word 自动目录；另起页=是
  处理：使用 Word TOC 字段生成目录；目录层级到 3 级。
  依据：源模板 p24-p51；字段为 TOC \o "1-3" \h \z \u。
  注意：南农模板的目录位于中英文摘要之前，这一点与部分学校不同。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 存在 `TOC \o "1-3" \h \z \u` 字段；目录位于中英文摘要之前，层级到 3 级。

1.5 中文摘要（abstract_cn）
  顺序=50；状态=required；来源=学生内容 + 元数据；另起页=是
  处理：填中文题名、中文摘要、中文关键词；固定“摘  要”和“关键词：”标签。
  依据：源模板 p53-p61。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 在目录后进入中文摘要/规范化要求区域，包含中文题名、“摘  要”、摘要正文和“关键词：”标签；说明文字只作证据，不进最终正文。

1.6 英文摘要（abstract_en）
  顺序=60；状态=required；来源=学生内容 + 元数据；另起页=是
  处理：填英文题名、英文摘要、英文关键词；固定“ABSTRACT”和“KEY WORDS：/KEY WORDS:”标签。
  依据：源模板 p62-p69。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 在英文题名前有显式 page break；英文题名、ABSTRACT、英文摘要正文和 KEY WORDS 标签均有可见模板证据。

1.7 正文主体（body_main）
  顺序=70；状态=required；来源=学生内容 + 模板章结构；另起页=是
  处理：按学校模板保留章、节、正文、图、表、公式等规则；包含固定类型结尾章“第X章 结论与展望”。
  依据：源模板 p72-p113。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：正文主体中图/表只保留源模板明示的中英文标题、居中、按章编号和字号规则；图题位置、表题位置、题名组同页和公式样式不再写成本校事实。

1.8 参考文献（references）
  顺序=80；状态=required；来源=学生参考文献；另起页=是
  处理：保留标题“参考文献”；填参考文献条目。
  依据：源模板 p115-p134。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 明确写“参考文献表应置于正文后并另起页”，并给出 GB/T 7714-2005 说明和示例。

1.9 附录（appendix）
  顺序=90；状态=template_default_optional；来源=学校模板 + 学生内容；另起页=是
  处理：源模板标注“此项非必需项”，但草稿/审阅输出默认保留；无内容时保留标题、占位和评论。
  依据：源模板 p137-p138；目录项 p49。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 目录和正文后置页均标注“此项非必需项”，草稿保留占位、正式输出人工确认删除的口径合理。

1.10 相关的学术成果目录（academic_achievements）
  顺序=100；状态=template_default_optional；来源=学校模板 + 学生成果；另起页=是
  处理：源模板标注“此项非必需项”，但草稿/审阅输出默认保留；无内容时保留标题、占位和评论。
  依据：源模板 p141-p142；目录项 p50。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 明确有“相关的学术成果目录（此项非必需项）”，属于目标学校后置可选页，不应被参考文献或附录吞掉。

1.11 致谢（acknowledgement）
  顺序=110；状态=template_default；来源=学校模板 + 学生内容；另起页=是
  处理：默认保留学校模板中的致谢模块；填致谢正文；无内容时保留标题、占位和评论。
  依据：源模板 p145-p148；目录项 p51。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 在附录和成果目录之后列出“致  谢”，并说明学位论文正文和附录之后一般应放置致谢。

================================================================================
2. 单元内容、顺序与样式（第二层级）
================================================================================

2.1 封面（cover）
  页眉：无
  页码：无
  同页约束：封面整体模块必须保持在一个页面内；封面内部所有标题、字段、底部日期/选项属于同一版面整体，不允许拆到下一页。若学生填入内容导致溢出，审查应标记为版面问题，而不是静默分页。
  元素顺序：1 封面整体模块。
  元素：
    - 封面整体模块
      类型：固定模板模块；是否填充：否
      内容：保留学校封面本体；当前阶段不填任何封面字段。
      固定可见字段：本科生毕业论文（设计）；题目；姓名；学号；学院；专业；指导教师；职称；20 年 月 日。
      样式：源模板封面为 1 个 1x1 表格。封面标题“本科生毕业论文（设计）”为华文中宋 36pt、居中；题目/姓名/学号/学院/专业/指导教师/职称标签为黑体 16pt、首行缩进约 4 字符、固定行距约 35pt；日期为宋体 16pt、居中。
      表格关系：封面本体在源模板中是 1 个 1x1 表格，内部包含封面标题与字段行；该表格属于封面模块本身，不作为普通正文表格处理。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：将封面“样式必填/需拆分”占位改为原始 DOCX 证据：封面标题华文中宋 36pt，字段黑体 16pt，日期宋体 16pt，且封面本体是 1x1 表格固定模块。

2.2 原创性声明（originality_statement）
  页眉：无
  页码：无
  同页约束：声明标题、声明正文和论文作者签名/日期行原则上属于同一固定页；签名/日期行不得单独被挤到下一页。
  元素顺序：1 声明标题；2 声明正文；3 论文作者签名/日期行。
  元素：
    - 声明标题
      类型：固定；是否填充：否
      内容：南京农业大学本科生毕业论文（设计）原创性声明
      位置：第 1 个元素；独立段落。
      样式：黑体；18pt（小二）；居中；不加粗；单倍行距。
    - 声明正文
      类型：固定；是否填充：否
      内容：本人郑重声明：所呈交的毕业论文（设计），是本人在导师的指导下，独立进行研究工作所取得的成果。除文中已经注明引用的内容外，本论文不包含任何其他个人或集体已经发表或撰写过的作品成果。对本文的研究做出重要贡献的个人和集体，均已在文中以明确方式标明。本人完全意识到本声明的法律结果由本人承担。
      位置：第 2 个元素；独立段落。
      样式：宋体；12pt（小四）；两端对齐；首行缩进约 2 字符；固定值 20pt 行距。
    - 论文作者签名/日期行
      类型：固定表单；是否填充：否
      内容：论文作者签名：                   日期：       年     月     日
      位置：第 3 个元素；独立段落。
      样式：宋体；12pt（小四）；首行缩进约 2 字符；固定值 20pt 行距。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：声明标题、正文、签名/日期行已补成原始 DOCX 可见样式；标题黑体 18pt 居中，正文和签名日期为宋体 12pt、固定 20pt 行距。

2.3 使用授权声明（authorization_statement）
  页眉：无
  页码：无
  同页约束：授权声明标题、正文、作者/导师签名行和日期行原则上属于同一固定页；签名区不得单独被挤到下一页。南农模板允许本单元与原创性声明共页。
  元素顺序：1 授权声明标题；2 授权声明正文；3 论文作者签名/导师签名行；4 作者日期/导师日期行。
  排版关系：本单元允许与原创性声明同页，但内容仍按本单元元素顺序输出。
  元素：
    - 授权声明标题
      类型：固定；是否填充：否
      内容：南京农业大学本科生毕业论文（设计）使用授权声明
      位置：第 1 个元素；独立段落。
      样式：黑体；18pt（小二）；居中；不加粗；单倍行距。
    - 授权声明正文
      类型：固定；是否填充：否
      内容：本学位论文作者完全了解学校有关保留、使用毕业论文（设计）的规定，同意学校保留并向国家有关部门或机构送交论文的复印件和电子版，允许论文被查阅和借阅。本人授权南京农业大学教务处可以将本毕业论文（设计）的全部或部分内容编入有关数据库进行检索，可以采用影印、缩印或扫描等复制手段保存和汇编毕业论文（设计）。
      位置：第 2 个元素；独立段落。
      样式：宋体；12pt（小四）；两端对齐；首行缩进约 2 字符；固定值 20pt 行距。
    - 论文作者签名/导师签名行
      类型：固定表单；是否填充：否
      内容：论文作者签名：                       导师签名：
      位置：第 3 个元素；独立段落。
      样式：宋体；12pt（小四）；首行缩进约 2 字符；固定值 20pt 行距。
    - 作者日期/导师日期行
      类型：固定表单；是否填充：否
      内容：日期：       年      月      日      日期：     年      月      日
      位置：第 4 个元素；独立段落。
      样式：宋体；12pt（小四）；首行缩进约 2 字符；固定值 20pt 行距。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：授权声明标题、正文、签名行和日期行已补成原始 DOCX 可见样式；签名和日期仍按固定表单项保留，不自动填写。

2.4 目录（toc）
  页眉：无
  页码：前置页页码规则，见 3.2
  元素顺序：1 目  录；2 自动目录字段；3 目录结果条目。
  元素：
    - 目  录
      类型：固定；是否填充：否
      内容：目  录
      位置：第 1 个元素；独立段落。
      样式：黑体；16pt（三号）；居中；段前=24pt；段后=18pt；行距=固定值 20pt。
    - 自动目录字段
      类型：生成；是否填充：系统生成
      内容：Word TOC 字段，源模板字段为 TOC \o "1-3" \h \z \u。
      位置：第 2 个元素；位于目录标题下方。
      收录层级：1-3 级。
      收录内容：摘要、ABSTRACT、正文各章/节/小节、参考文献、附录、相关的学术成果目录、致谢。
      注意：目录条目可以出现“摘  要”“ABSTRACT”“第一章”“参考文献”等文字，不能因此误判为正文内容。
    - 目录结果条目
      类型：生成结果；是否填充：系统生成
      内容：由 Word 更新域后生成；不得保留手打目录作为最终目录。
      样式：中文宋体、英文/数字 Times New Roman；14pt（四号）；不加粗；左对齐；行距=固定值 20pt。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。目录标题、TOC 字段、1-3 级收录范围和目录结果条目均与原始 DOCX 中的目录字段和可见目录一致。

2.5 中文摘要（abstract_cn）
  页眉：无
  页码：前置页页码规则，见 3.2
  缺失处理：如果没有识别到中文题名、摘要正文或关键词，保留占位并添加人工评论。
  元素顺序：1 中文论文题目；2 摘  要；3 中文摘要正文；4 关键词：；5 中文关键词内容。
  排版关系：第 1、2、3 个元素各自独立成段；第 4、5 个元素组成同一个关键词段落，“关键词：”与关键词内容在同一段内连续排布。
  元素：
    - 中文论文题目
      类型：填充；是否填充：是
      内容：学生中文论文题目；缺失时保留题名占位并评论。
      位置：第 1 个元素；独立段落。
      样式：黑体；18pt（小二）；居中；段前=24pt；段后=18pt。
      依据：源模板 p53“论文题目（小二号黑体）”。
    - 摘  要
      类型：固定；是否填充：否
      内容：摘  要
      位置：第 2 个元素；独立段落，位于中文论文题目之后。
      样式：黑体；16pt（三号）；居中；段前=24pt；段后=18pt；行距=固定值 20pt。
    - 中文摘要正文
      类型：填充；是否填充：是
      内容：学生中文摘要；一般 400 字左右；缺失时保留占位并评论。
      位置：第 3 个元素；独立段落，位于“摘  要”之后。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0；段后=0；行距=固定值 20pt。
      内容规则：模板说明“不含图表，不加注释，具有独立性和完整性”。
    - 关键词：
      类型：固定；是否填充：否
      内容：关键词：
      位置：第 4 个元素的行首；与关键词内容同段。
      关系：与关键词内容同一行，关键词内容紧跟其后。
      样式：黑体；14pt（四号）；左对齐；行距=固定值 20pt。
    - 中文关键词内容
      类型：填充；是否填充：是
      内容：学生中文关键词；3-5 个；缺失时保留占位并评论。
      位置：第 5 个元素；紧跟“关键词：”，不另起段。
      分隔符：强制使用中文分号“；”；最后一个关键词后不打标点。
      样式：宋体；12pt（小四）；左对齐；行距=固定值 20pt。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。中文题名、摘要标题、摘要正文、关键词标签和关键词内容均有原始 DOCX 可见说明支持；关键词最后不加标点的规则也来自源模板。

2.6 英文摘要（abstract_en）
  页眉：无
  页码：前置页页码规则，见 3.2
  缺失处理：如果没有识别到英文题名、英文摘要或英文关键词，保留占位并添加人工评论。
  元素顺序：1 英文论文题目；2 ABSTRACT；3 英文摘要正文；4 KEY WORDS:；5 英文关键词内容。
  排版关系：第 1、2、3 个元素各自独立成段；第 4、5 个元素组成同一个关键词段落，“KEY WORDS:”与英文关键词内容在同一段内连续排布。
  元素：
    - 英文论文题目
      类型：填充；是否填充：是
      内容：学生英文论文题目；全部采用大写字母；缺失时保留占位并评论。
      位置：第 1 个元素；独立段落。
      样式：Times New Roman；16pt（三号）；加粗；居中；段前=24pt；段后=18pt；行距=固定值 20pt。
      依据：源模板 p62。
    - ABSTRACT
      类型：固定；是否填充：否
      内容：ABSTRACT
      位置：第 2 个元素；独立段落，位于英文题名之后。
      样式：Times New Roman；16pt（三号）；加粗；居中；段前=24pt；段后=18pt；行距=固定值 20pt。
    - 英文摘要正文
      类型：填充；是否填充：是
      内容：学生英文摘要；与中文摘要和关键词内容相一致；约 300 个实词；缺失时保留占位并评论。
      位置：第 3 个元素；独立段落，位于 ABSTRACT 之后。
      样式：Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0；段后=0；行距=固定值 20pt。
    - KEY WORDS:
      类型：固定；是否填充：否
      内容：KEY WORDS:
      位置：第 4 个元素的行首；与英文关键词内容同段。
      关系：与英文关键词内容同一行，英文关键词内容紧跟其后。
      样式：Times New Roman；14pt（四号）；加粗；左对齐；行距=固定值 20pt。
      注意：源模板可见文本用中文冒号“：”，工程输出可统一为英文冒号，但必须保持同段关系。
    - 英文关键词内容
      类型：填充；是否填充：是
      内容：学生英文关键词；小写；缺失时保留占位并评论。
      位置：第 5 个元素；紧跟“KEY WORDS:”，不另起段。
      分隔符：模板说明每个关键词之间用分号分开，最后一个关键词后不打标点。
      样式：Times New Roman；12pt（小四）；左对齐；行距=固定值 20pt。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。英文题名、ABSTRACT、英文摘要正文、KEY WORDS 标签和关键词分隔规则均有原始 DOCX 可见说明；冒号规范化需保持同段关系。

2.7 正文主体（body_main）
  页眉：南京农业大学本科毕业论文（设计）
  页码：正文及后置页阿拉伯数字页码规则，见 3.2
  缺失处理：如果没有识别到正文内容，保留正文占位并添加人工评论。
  元素顺序：1 正文章标题；2 一级节标题；3 二级节标题；4 正文段落；5 图/表（如有）；6 公式（如有）；7 固定类型结尾章“第X章 结论与展望”。
  排版关系：标题、正文段落、图、表、公式均按学生论文原有逻辑顺序进入正文流；图/表作为正文内部嵌套单元处理，不拍平成普通段落；如果源模板有实际图/表/公式示例，应以示例的相对位置和样式为准；已核对南农原始 DOCX，正文区域没有真实图、表、公式示例，因此学校未明确的图题位置、表题位置和公式样式不写成本校事实。
  元素：
    - 正文章标题
      类型：填充；是否填充：是
      内容：学生章节标题；编号形式如“第一章 文献综述”“第X章 结论与展望”。
      样式：黑体；16pt（三号）；居中；段前=24pt；段后=18pt；行距=固定值 20pt；大纲级别=1。
      编号规则：正文章标题使用“第X章 + 标题”；目录应收录。
    - 一级节标题
      类型：填充；是否填充：是
      内容：学生一级节标题；模板示例“1□材料与方法”。
      样式：黑体；14pt（四号）；左对齐；行距=固定值 20pt；大纲级别=2。
      编号规则：章内局部编号；编号后保留一个显式空格。
    - 二级节标题
      类型：填充；是否填充：是
      内容：学生二级节标题；模板示例“1.1□材料”。
      样式：宋体；12pt（小四）；左对齐；行距=固定值 20pt；大纲级别=3。
      编号规则：章内局部编号；编号后保留一个显式空格。
    - 正文段落
      类型：填充；是否填充：是
      内容：学生正文。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0；段后=0；行距=固定值 20pt。
    - 图单元（figure）
      类型：填充 + 生成编号；是否填充：是
      本校明确规则：图应有中英文标题；标题居中；图、表格按章顺序编号；图中文字说明用 5 号黑体，英文及数字用五号 Times New Roman。
      示例核对：原始 DOCX 虽包含媒体文件，但位于封面/说明框区域，不是正文图示例；正文区域没有真实图本体 + 图名示例。
      未明示规则：源模板没有提供正文图样例，未明确图题在图上还是图下、中文/英文图题的先后、图注是否必填或图题同页规则。
      处理：本校专属标准只检查上述明确规则；题名位置、题名组同页和图注结构如需默认，应放共享默认规则或人工确认。
      依据：源模板 p90“图、表格应有中英文标题，居中显示……表头及图的文字说明用5号黑体”。
    - 表单元（table）
      类型：填充 + 生成编号；是否填充：是
      本校明确规则：表格应有中英文标题；标题居中；图、表格按章顺序编号，如“表5-4”为第五章第四表；图表内容一般为 5 号及小 5 号宋体，表头用 5 号黑体，英文及数字用五号 Times New Roman。
      示例核对：原始 DOCX 只有封面 1x1 表格，没有正文表格示例。
      未明示规则：源模板没有提供正文表格样例，未明确表题在表上还是表下、中文/英文表题先后、表注是否必填、三线表边框或续表规则。
      处理：本校专属标准只检查上述明确规则；题名位置、题名组同页、表注和续表结构如需默认，应放共享默认规则或人工确认。
      依据：源模板 p90。
    - 公式
      类型：填充；是否填充：是
      内容：学生公式。
      示例核对：原始 DOCX 正文区域没有 Word 公式对象或公式示例。
      处理：源模板只说明实验部分可包含公式，未提供公式编号、对齐、字体或正斜体规则；本校专属标准不定义公式结构和样式，后续由共享默认规则或人工确认处理。
    - 固定类型结尾章“第X章 结论与展望”
      类型：模板固定章类型 + 学生内容；是否填充：章内内容需要填充
      内容：最后一章应为“结论与展望”类型，具体章号随正文实际章数变化。
      位置：正文主体最后一个章级单元，在参考文献之前。
      样式：同正文章标题；章内段落使用正文样式。
      注意：源模板 p109-p112 是写作说明，不是最终论文必须保留的固定正文。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：按原始 DOCX 重新核对图/表/公式示例；南农只有封面/说明区域媒体和封面表格，没有正文图、正文表格或公式示例，因此仍不把图题位置、表题位置、题名组同页、续表和公式样式写成本校事实。

2.8 参考文献（references）
  页眉：南京农业大学本科毕业论文（设计）
  页码：正文及后置页阿拉伯数字页码规则，见 3.2
  缺失处理：如果没有识别到参考文献，保留参考文献标题、占位和人工评论。
  元素顺序：1 参考文献；2 参考文献条目。
  元素：
    - 参考文献
      类型：固定；是否填充：否
      内容：参考文献
      位置：第 1 个元素；独立段落；另起页。
      样式：黑体；16pt（三号）；居中；段前=24pt；段后=18pt；行距=固定值 20pt。
    - 参考文献条目
      类型：填充；是否填充：是
      内容：学生参考文献条目。
      位置：第 2 个元素开始；每条独立段落。
      编号：保留或规范化为 [1] 后接空格。
      样式：中文宋体、英文/数字 Times New Roman；10.5pt（五号）；左对齐；行距=固定值 20pt。
      著录规则：模板说明遵照 GB/T 7714-2005《文后参考文献著录规则》。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。参考文献标题、条目字体字号、另起页要求和 GB/T 7714-2005 依据均与原始 DOCX 可见说明一致。

2.9 附录（appendix）
  页眉：南京农业大学本科毕业论文（设计）
  页码：正文及后置页阿拉伯数字页码规则，见 3.2
  缺失处理：源文档未识别到附录内容时，草稿/审阅输出保留本页并写入“【源文档中未识别到本页内容；如学校不要求，可删除本页。】”。
  元素顺序：1 附  录 + 附录名称；2 附录正文/材料。
  元素：
    - 附  录 + 附录名称
      类型：固定标题 + 填充标题；是否填充：附录名称可填充
      内容：附  录 附录名称
      位置：第 1 个元素；独立段落；另起页。
      样式：黑体；16pt（三号）；居中；段前=24pt；段后=18pt；行距=固定值 20pt。
    - 附录正文/材料
      类型：填充；是否填充：是
      内容：不宜放在正文中的重要支撑材料，如原始数据、数学推导、程序全文、复杂图表、设计图纸等。
      样式：正文类内容默认使用正文样式；复杂材料按其自身结构保留。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。附录标题“附  录 附录名称”和“此项非必需项”均来自原始 DOCX；保留草稿占位、正式输出人工确认的处理合理。

2.10 相关的学术成果目录（academic_achievements）
  页眉：南京农业大学本科毕业论文（设计）
  页码：正文及后置页阿拉伯数字页码规则，见 3.2
  缺失处理：源文档未识别到成果内容时，草稿/审阅输出保留本页并写入“【源文档中未识别到本页内容；如学校不要求，可删除本页。】”。
  元素顺序：1 相关的学术成果目录；2 成果条目。
  元素：
    - 相关的学术成果目录
      类型：固定；是否填充：否
      内容：相关的学术成果目录
      位置：第 1 个元素；独立段落；另起页。
      样式：黑体；16pt（三号）；居中；段前=24pt；段后=18pt；行距=固定值 20pt。
    - 成果条目
      类型：填充；是否填充：是
      内容：本科期间发表的与毕业论文（设计）相关的已发表论文或被鉴定的技术成果、发明专利等成果。
      位置：第 2 个元素开始。
      样式：正文类内容默认使用正文样式；如成果列表有固定学校格式，后续需补充。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。成果目录标题和“本科期间发表的与毕业论文相关成果”说明来自原始 DOCX；本页应作为后置可选目标页处理。

2.11 致谢（acknowledgement）
  页眉：南京农业大学本科毕业论文（设计）
  页码：正文及后置页阿拉伯数字页码规则，见 3.2
  缺失处理：源文档未识别到致谢内容时，草稿/审阅输出保留本页并写入“【源文档中未识别到本页内容；如学校不要求，可删除本页。】”。
  元素顺序：1 致  谢；2 致谢正文。
  元素：
    - 致  谢
      类型：固定；是否填充：否
      内容：致  谢
      位置：第 1 个元素；独立段落；另起页。
      样式：黑体；16pt（三号）；居中；段前=24pt；段后=18pt；行距=固定值 20pt。
    - 致谢正文
      类型：填充；是否填充：是
      内容：学生致谢正文；一般 500 字以内。
      位置：第 2 个元素；独立段落，位于“致  谢”之后。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0；段后=0；行距=固定值 20pt。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。致谢标题、字数一般 500 字以内、正文小四宋体固定 20pt 行距均由原始 DOCX 可见说明支持。

================================================================================
3. 全局规则（第三层级）
================================================================================

3.1 页面、页眉、页脚与 Word section
  页面：
    - 纸张：A4。
    - 上/下/左/右边距：20mm。
    - 装订线：5mm，居左。
  页眉/页脚距离：
    - 源模板可见说明写“页眉和页脚为 5mm”。
    - 源模板 OOXML：封面附近 section 为页眉约 5mm、页脚约 5mm；正文及后置页多数 section 为页眉约 15mm、页脚约 17.5mm。
    - 审查口径：记录为证据冲突。学校可见说明优先；如实现侧直接继承源 DOCX section，应单独标注这是模板 OOXML 实现值，不写成学校明示要求。
  页眉内容归属：
    - 全局只记录页眉机制和距离。
    - 单元记录本单元显示什么页眉。
    - 正文、参考文献、附录、成果目录、致谢页眉显示：南京农业大学本科毕业论文（设计）。
    - 封面、声明、授权、目录、中英文摘要默认无页眉。
  Word section 规则：
    - 只在页眉/页脚/页码格式/页边距/横竖版变化时创建或切换 section。
    - 新 section 需要断开 Link to Previous，避免正文页眉或页码串到封面、声明、目录、摘要。
    - 单元不是天然等于 Word section；单元只是声明需要的页面属性，渲染层再合并相邻相同属性。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：页眉/页脚距离从单纯采用 OOXML 改为“证据冲突”处理；源模板可见说明写 5mm，OOXML 部分 section 为 15mm/17.5mm，学校明示要求优先。

3.2 页码
  归属：
    - 页码格式、字体字号、起始编号和连续规则属于全局规则。
    - 每个单元只声明使用哪一种页码规则。
  页码显示：
    - 封面：不显示页码。
    - 原创性声明/使用授权声明：不显示页码。
    - 目录、中英文摘要：前置页页码规则。
    - 正文及后置页：阿拉伯数字页码规则。
  前置页页码规则：
    - 官方源模板存在罗马页码证据，页脚字段显示 I，目录示例显示 Ⅰ/Ⅱ。
    - 当前 school.yaml 使用 lowerRoman；这里需人工确认最终采用大写罗马还是小写罗马。
    - 在确认前，审查重点是“前置页使用罗马页码，且不与正文阿拉伯页码连续混用”。
  正文及后置页页码规则：
    - 从正文首页开始使用阿拉伯数字，起始页码为 1。
    - 参考文献、附录、相关的学术成果目录、致谢继续正文阿拉伯数字页码，不重新从 1 开始。
    - 页码字体：Times New Roman；10.5pt（五号）；居中。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。前置页罗马页码与正文阿拉伯页码分层正确；原始 DOCX 存在大小写/字段结果不完全一致的证据，因此保留人工确认大小写。

3.3 正文基础样式（Normal / Body）
  样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0；段后=0；行距=固定值 20pt。
  依据：源模板 p75、p89。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。正文宋体/Times New Roman、小四、首行缩进 2 字符、固定 20pt 行距与原始 DOCX 可见说明一致。

3.4 标题样式与目录层级
  章标题：
    - 编号/文本：第X章 标题。
    - 样式：黑体；16pt（三号）；居中；段前=24pt；段后=18pt；行距=固定值 20pt；大纲级别=1。
  一级节标题：
    - 编号/文本：1 标题。
    - 样式：黑体；14pt（四号）；左对齐；行距=固定值 20pt；大纲级别=2。
    - 编号后必须保留一个显式空格。
  二级节标题：
    - 编号/文本：1.1 标题。
    - 样式：宋体；12pt（小四）；左对齐；行距=固定值 20pt；大纲级别=3。
    - 编号后必须保留一个显式空格。
  目录层级：
    - 官方源模板 TOC 字段为 1-3 级。
    - 目录应收录章标题、一级节标题、二级节标题，以及前后置固定标题。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。章标题、一级节标题、二级节标题和目录 1-3 级均与原始 DOCX 示例和 TOC 字段一致。

3.5 摘要与关键词全局规则
  中文摘要：
    - 中文论文题名：黑体；18pt（小二）；居中。
    - 摘要标题：黑体；16pt（三号）；居中。
    - 摘要正文：宋体/Times New Roman；12pt；固定值 20pt；首行缩进 2 字符。
    - 关键词标签：黑体；14pt；与关键词内容同段。
    - 关键词内容：宋体；12pt；中文分号分隔；最后不加标点。
  英文摘要：
    - 英文题名：Times New Roman；16pt；加粗；居中；全部大写。
    - ABSTRACT：Times New Roman；16pt；加粗；居中。
    - 英文摘要正文：Times New Roman；12pt；固定值 20pt；首行缩进 2 字符。
    - KEY WORDS 标签：Times New Roman；14pt；加粗；与英文关键词内容同段。
    - 英文关键词内容：Times New Roman；12pt；分号分隔；最后不加标点。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。中英文摘要、关键词标签、字号、分号分隔和末尾不加标点均有原始 DOCX 可见说明。

3.6 图、表、公式全局规则覆盖范围
  图：
    - 源模板明确：图应有中英文标题；居中；按章顺序编号；图中文字说明用 5 号黑体，英文及数字为五号 Times New Roman。
    - 示例核对：原始 DOCX 的媒体对象不属于正文图示例；正文区域没有真实图本体 + 图名示例。
    - 源模板未明确：图题位置、中文/英文图题先后、图注是否必填、图题组同页规则。
  表：
    - 源模板明确：表格应有中英文标题；居中；按章顺序编号；图表内容一般为 5 号及小 5 号宋体；表头用 5 号黑体，英文及数字为五号 Times New Roman。
    - 示例核对：原始 DOCX 只有封面 1x1 表格，没有正文表格示例。
    - 源模板未明确：表题位置、中文/英文表题先后、表注是否必填、三线表边框、续表规则。
  公式：
    - 示例核对：原始 DOCX 正文区域没有 Word 公式对象或公式示例。
    - 源模板只说明实验部分可包含公式；未提供公式编号、对齐、字体、正斜体或同页规则。
  处理：
    - 本校专属测试标准只记录源模板明示项；其他图表公式默认结构和样式放共享默认规则或人工确认。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：补充“先看原始 DOCX 是否有实际示例”的核对口径；南农正文没有图、表、公式实际示例，所以只记录源模板明示的图表中英文标题、居中、按章编号和部分字号。

3.7 参考文献全局规则
  参考文献标题：黑体；16pt（三号）；居中；段前=24pt；段后=18pt；行距=固定值 20pt。
  参考文献条目：中文宋体、英文/数字 Times New Roman；10.5pt（五号）；左对齐；行距=固定值 20pt。
  编号：使用 [1] 形式，编号后保留空格。
  著录规则：源模板说明遵照 GB/T 7714-2005。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。参考文献标题、条目样式、编号示例和 GB/T 7714-2005 依据均有原始 DOCX 证据。

3.8 模板默认页保留策略
  附录：
    - 学校模板标注“此项非必需项”，但草稿/审阅输出默认保留。
    - 无学生内容时保留标题和人工确认占位。
  相关的学术成果目录：
    - 学校模板标注“此项非必需项”，但草稿/审阅输出默认保留。
    - 无学生内容时保留标题和人工确认占位。
  致谢：
    - 学校模板写“一般应放置致谢”，因此默认保留。
    - 无学生内容时保留标题和人工确认占位。
  说明文字：
    - 源模板中用于指导写作的说明段落不是最终论文固定正文。
    - 说明段落可作为审查证据，但最终输出应由学生内容或占位替换。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。附录、相关学术成果目录为“此项非必需项”，致谢为“一般应放置”；草稿保留、正式人工确认删除的策略符合源模板。

3.9 同页约束与分页完整性
  适用对象：
    - 封面整体模块。
    - 固定声明/授权页的签名区。
    - 标题与紧随其后的第一段或第一项内容。
    - 学校模板中明确要求同页呈现的表单、勾选项、底部说明或签名日期。
    - 图题/表题组同页规则：源模板未明示；如产品共享默认规则需要，可在共享层补充，不写成南农本校事实。
  审查原则：
    - 同页约束是单元/元素的布局属性，不是单纯样式属性。
    - 如果同页约束失败，应记为版面完整性问题。
    - 不应为了通过分页而删除固定元素，也不应把同一固定表单拆成多个逻辑单元。
  Word 实现提示：
    - 普通段落可使用“与下段同页”“段中不分页”。
    - 固定表单和封面可优先保留为整体表格、内容控件或模板块。
    - 图题/表题是否使用 keep-with-next，属于共享默认或渲染策略，需要单独标注来源。
    - 如果内容本身超过一页，应保留学校模板结构并输出人工调整提示。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：删除把图题/表题同页约束写成南农源模板事实的表述；同页规则保留在封面、声明签名区、标题与首段等可确认对象上，图表同页可由共享默认规则另行补充。

================================================================================
4. 实现对齐提醒
================================================================================

4.1 单元顺序对齐
  官方源模板可见顺序为“目录 -> 中文摘要 -> 英文摘要”，当前审查按此顺序。
  现有 school.yaml/template_manifest 中存在“摘要 -> 目录”的工程化顺序迹象，需要后续实现确认并对齐。

4.2 页眉页脚距离对齐
  源模板 OOXML 的正文页眉/页脚距离约为 15mm/17.5mm；当前 school.yaml 顶层 page.header_mm/footer_mm 为 5mm。
  如果最终以源模板为准，运行时 section 生成不能只使用统一 5mm。

4.3 前置页页码大小写
  源模板存在大写罗马页码证据，school.yaml 当前写 lowerRoman。
  需要人工确认学校最终要求大写罗马还是小写罗马；确认前测试只应断言“前置页为罗马页码，正文为阿拉伯数字页码”。

4.4 图目录/表目录
  南农官方模板没有独立图目录/表目录页。
  不应在本校审查里直接列为南农模板单元；若未来中国通用规范要求，可作为默认配置另行加入，并标注不是源模板证据。

4.5 图表样例不足
  源模板只有图表规则说明，没有提供真实图、表样例。
  目前可审查图表单元顺序、双语标题、编号、位置和样式；三线表边框、复杂表注、跨页续表等细节需要后续样本或人工补证。

4.6 其他高风险非样式约束
  固定模板隐藏结构：
    - 封面是整体表格/模板块，声明和授权页有固定签名日期区；合成时不能只复制可见文字而丢掉表格、字段、签名线或占位结构。
  生成字段：
    - 目录必须保留 Word TOC 字段；目录可见页码可能是旧结果，不能把旧结果当成固定文本。
    - 页码应由页脚字段或等价机制生成，不能手打成普通正文。
  单元边界：
    - 参考文献必须在“附录/相关的学术成果目录/致谢”之前结束，不能吞掉后置页。
    - 目录条目里的“第一章”“参考文献”“附录”等不能被误识别为正文标题。
  段内混排：
    - 中文“关键词：”与关键词内容同段但 run 样式不同。
    - 英文“KEY WORDS:”与英文关键词内容同段但 run 样式不同。
    - 不能只给整段一个统一样式后忽略标签与内容的差异。
  无页眉/无页码也是规则：
    - 封面、声明、授权、目录、中英文摘要默认无页眉；封面、声明、授权不显示页码。
    - 这些“空”不是缺失，应该进入验证。
  新页与分节：
    - 单元要求“另起页”时，不一定要新建 section；只有页眉页脚、页码格式、页边距等 section 级属性变化时才需要新 section。
  渲染预检：
    - 同页约束、封面溢出、签名区掉页、孤立表题/图题，必须通过渲染后页面级检查或人工 review 标记确认。

================================================================================
5. 本校总评
================================================================================

5.1 当前审查口径
  南京农业大学本科模板可以按“单元 -> 元素 -> 子元素/嵌套单元”建模。
  封面、声明、授权、目录属于学校模板/系统拥有的固定或生成单元；摘要、正文、参考文献、附录、成果目录、致谢属于学生内容填充到学校模板槽位。

5.2 需要用户确认的点
  - 目录是否最终确认为位于摘要之前。
  - 前置页页码使用大写罗马还是小写罗马。
  - 附录和相关的学术成果目录在最终正式输出中，是否允许学生确认后删除。
  - 如果后续中国通用规范要求图目录/表目录，是否要对南农这类未提供目录页的模板也默认补入。

5.3 可以先按本文件执行的点
  - 封面字段当前不自动填。
  - 原创性声明和使用授权声明保留固定内容，不自动填签名日期。
  - 图/表必须有中英文标题。
  - 图/表必须有中英文标题；源模板未明示图题/表题位置和中文/英文标题先后，相关结构由共享默认规则或人工确认补充。
  - 图表按章顺序编号；源模板未明示公式结构和样式，公式由共享默认规则或人工确认处理。
  - “第X章 结论与展望”归入正文主体的固定类型结尾章。
~~~~

### Source: `pku-graduate`

- Path: `inputs/school-pku-graduate-template-review.txt`
- SHA-256: `sha256:631c7a839a1745af605fa1d5ddcffbc60b9325d506a9f8098b1a0d01ff6ad923`

~~~~text
北京大学研究生学位论文模板审查包 V2
日期：2026-06-08

依据：只使用学校 Word 模板
/Users/fl/ws/gogo/docfit/schools/pku-graduate/sources/PKU-Graduate-Thesis-Template.docx

阅读方式
================================================================================
1. 先核对“单元顺序”：整篇文档有哪些单元，顺序是否对。
2. 再核对“单元内容与顺序”：每个单元有什么元素、元素顺序如何、哪些独立成段、哪些同段连接、哪些是固定模板内容、哪些需要填学生内容。
3. 最后核对“全局规则”：只放真正跨单元共用的页面、网格、字体和段落高级设置。

写法约定
- 类型=固定：学校模板自带文字或模块，不从学生正文填充。
- 类型=填充：从学生论文或元数据填入。
- 类型=生成：由 Word 字段或系统生成。
- 固定内容必须显式写出“内容”；固定签名/日期/勾选框等表单项也要保留学校模板文字，只是不自动填写空白项或勾选项。
- 模板默认模块应默认保留，不因学生原文暂时缺少对应内容而省略；学生后续删除模块比重新补齐模块更容易。
- 默认假设学位论文应包含图和表；图目录、表目录默认保留。
- 学校模板未说明的结构、样式和规则，不写入本校专属测试标准；后续如需中国论文通用默认规则，应放到共享默认规则中，并明确不是 PKU 源模板事实。
- 缺失处理：学生内容没有识别到时，模板中应保留示例占位，并添加人工评论。
- 元素顺序：单元内元素按列出顺序输出；如果该单元用于测试，需显式写出“元素顺序”。
- 位置/排版关系：独立成段、同一段、同行、表格内部、页眉页脚等关系都属于审查项；未写同段关系时，默认该元素相对上一个元素换行并独立成段。
- 同页约束：如果一个单元或一组元素必须作为视觉整体留在同一页，应显式写出“同页约束”。这类约束高于普通换行关系，例如封面整体、声明签名区、图与图名、表名与表体等不能被 Word 自动分页切散。
- 同页约束识别原则：如果某个单元基本都是学校模板固定内容，不随学生正文长度自由增减，通常应推定为固定版面页并检查同页约束；如果某个单元主要承载学生内容且长度可能大幅变化，例如参考文献、附录正文、致谢正文，则不要求整个单元同页，只检查标题与首段、图题/表题等局部组约束。
- 样式只写核对需要的内容：字体、字号、加粗、对齐、缩进、段前、段后、行距、关键段落设置。
- 标题编号、题注编号、目录页码、参考文献序号后的空格/制表符属于模板内容；不应作为普通正文随意手打。
- 页眉/页码分层记录：页眉/页脚距离、页码字体字号、页码格式和连续编号规则放到第三层全局规则；每个单元只写本单元页眉显示文字，以及本单元使用前置页还是正文/后置页页码规则。
- Word 实现提醒：页眉、页脚、页码格式、页边距、横竖版最终都落在 Word section 上；单元负责声明需要什么，渲染层只在这些 section 级属性变化时新开 section，并断开上一节页眉页脚继承。

================================================================================
1. 单元顺序（第一层级）
================================================================================

1.1 封面（cover）
  顺序=10；状态=required；来源=学校模板；另起页=是
  处理：当前阶段保留学校封面模块；不填任何封面字段；不做字段文字锚点匹配。
  注意：只保留真正属于模板的封面内容；如果学校模板里混有说明文字，应删除说明文字。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：封面样式不再停留在“必填/需拆分”占位；第二层已按原始 DOCX 样式补充封面标题、题名、字段、学位类型和日期的字号/字体。

1.2 版权声明（copyright_notice）
  顺序=20；状态=manual_only；来源=学校模板；另起页=是
  处理：保留固定页；不自动填充。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 中版权声明位于封面之后，包含固定版权正文和二维码版本替换说明，属于 manual_only 固定页。

1.3 中文摘要（abstract_cn）
  顺序=30；状态=required；来源=学生内容；另起页=是
  处理：保留标题和关键词标签；填入中文摘要、中文关键词。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 中中文摘要位于版权声明之后，包含“摘要”标题、摘要正文和“关键词：”同段标签。

1.4 英文摘要（abstract_en）
  顺序=40；状态=required；来源=学生内容 + 元数据；另起页=是
  处理：填英文题名、作者、导师、英文摘要、英文关键词；固定英文标题和标签。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。英文摘要页包含英文题名、作者英文名、导师行、ABSTRACT、正文和 KEY WORDS 标签，顺序与原始 DOCX 一致。

1.5 目录（toc）
  顺序=50；状态=required；来源=Word 自动目录；另起页=是
  处理：使用 Word 目录字段生成。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 存在主目录 TOC 字段，目录位于英文摘要之后、图目录之前，使用 Word 自动目录机制。

1.6 图目录（figure_list）
  顺序=60；状态=required；来源=Word 图目录；另起页=是
  处理：默认保留图目录页；有图题时生成条目；未识别到图题时保留空白图目录页并添加人工评论。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 明确存在“图目录”页和图目录 TOC 字段，默认保留图目录页有源模板依据。

1.7 表目录（table_list）
  顺序=65；状态=required；来源=Word 表目录；另起页=是
  处理：默认保留表目录页；有表题时生成条目；未识别到表题时保留空白表目录页并添加人工评论。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 明确存在“表目录”页和表目录 TOC 字段，默认保留表目录页有源模板依据。

1.8 正文主体（body_main）
  顺序=70；状态=required；来源=学生内容 + 模板章结构 + 固定结尾章；另起页=是
  处理：按学校模板保留章、节、正文、图、表、公式等规则；包含最后固定章“结论与讨论”。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：正文中图/表单元已删除“英文图名/英文表名必保留”的默认规则；PKU 源模板只提供单行图名/表名和域编号规则，不强制独立英文题名。

1.9 参考文献（references）
  顺序=80；状态=required；来源=学生参考文献；另起页=是
  处理：保留标题；填参考文献条目。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。参考文献位于正文后，源模板明确给出标题、说明、顺序编码制和著者-出版年制示例。

1.10 附录A  博士期间工作成果（academic_achievements）
  顺序=85；状态=template_default；来源=学校模板 + 学生成果；另起页=是
  处理：默认保留学校模板中的附录成果模块；填成果条目；无内容时保留标题、成果类别、占位和评论。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 中有“附录A  博士期间工作成果”，应作为学校模板默认后置模块保留。

1.11 致谢（acknowledgement）
  顺序=90；状态=template_default；来源=学校模板 + 学生内容；另起页=是
  处理：默认保留学校模板中的致谢模块；填致谢正文；无内容时保留标题、占位和评论。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 中致谢位于附录成果之后、原创性声明和使用授权说明之前，默认保留策略合理。

1.12 北京大学学位论文原创性声明和使用授权说明（originality_authorization_statement）
  顺序=100；状态=manual_only；来源=学校模板；另起页=是
  处理：保留固定签名/授权页；不自动填充。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原始 DOCX 末尾包含“北京大学学位论文原创性声明和使用授权说明”，签名/日期和授权勾选项均为固定手填内容。

================================================================================
2. 单元内容、顺序与样式（第二层级）
================================================================================

2.1 封面（cover）
  页眉：无
  同页约束：封面整体模块必须完整落在同一页；封面内部字段、底部说明、签名、日期或选项不允许被挤到下一页。若填充内容导致溢出，应标记为版面问题或人工调整项。
  元素顺序：1 封面整体模块。
  元素：
    - 封面整体模块
      类型：固定模板模块；是否填充：否
      内容：保留学校封面本体；当前阶段不填任何封面字段；删除不属于模板的说明文字。
      样式：封面标题“博士研究生学位论文”为黑体 36pt、居中；“题目：”为宋体 22pt、居中；论文题名为黑体 26pt、加粗、居中；姓名/学号/院系/专业/研究方向/导师姓名字段为黑体 15pt、居中；学术学位/专业学位和日期为宋体 16pt、居中。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：封面整体模块已补充源 DOCX/样式定义中的具体样式，包含黑体 36pt 封面标题、黑体 26pt 加粗论文题名、黑体 15pt 字段和宋体 16pt 学位类型/日期。

2.2 版权声明（copyright_notice）
  页眉：无
  同页约束：版权声明是学校固定模板页，标题、版权声明正文和二维码替换说明应作为同一固定版面整体保留；二维码替换说明不得被单独挤到下一页。若版面溢出，应标记为版面问题或人工调整项。
  元素顺序：1 版权声明；2 版权声明正文；3 二维码替换说明。
  元素：
    - 版权声明
      类型：固定；是否填充：否
      内容：版权声明
      样式：黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=2.5
      段落设置：大纲级别=正文文本；其余高级项默认/继承，需 Word 核对。
    - 版权声明正文
      类型：固定；是否填充：否
      内容：任何收存和保管本论文各种版本的单位和个人，未经本论文作者同意，不得将本论文转借他人，亦不得随意复制、抄录、拍照或以任何方式传播。否则，引起有碍作者著作权之问题，将可能承担法律责任。
      样式：宋体；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0 行；段后=0 行；行距选项=2 倍行距；设置值=无
    - 二维码替换说明
      类型：固定；是否填充：否
      内容：在正式提交图书馆的论文版本中，需将此页与原创性声明页替换为带有二维码的版本，带有二维码的此二页应当从个人门户→研究生院业务→打印学位审批材料页面下载。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
      段落设置：孤行控制=否；其余高级项默认/继承，需 Word 核对。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。版权声明标题、固定正文和二维码替换说明与原始 DOCX 可见内容一致；正式提交需替换带二维码版本这一点应保留为人工处理提示。

2.3 中文摘要（abstract_cn）
  页眉：摘要
  页码：前置页页码规则，见 3.2
  缺失处理：如果没有识别到摘要正文或关键词，保留示例占位并添加人工评论。
  元素顺序：1 摘要；2 摘要正文；3 关键词：；4 关键词内容。
  排版关系：第 1、2 个元素各自独立成段；第 3、4 个元素组成同一个关键词段落，“关键词：”与关键词内容在同一段内连续排布。
  元素：
    - 摘要
      类型：固定；是否填充：否
      内容：摘要
      位置：第 1 个元素；独立段落。
      样式：黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=2.5
      段落设置：大纲级别=1 级；与下段同页=是；段中不分页=是。
    - 摘要正文
      类型：填充；是否填充：是
      内容：学生中文摘要；缺失时示例占位“摘要……”并评论“原文未发现摘要正文，请补充”。
      位置：第 2 个元素；独立段落，位于“摘要”之后。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
      段落设置：孤行控制=否；其余高级项默认/继承，需 Word 核对。
    - 关键词：
      类型：固定；是否填充：否
      内容：关键词：
      位置：第 3 个元素的行首；与关键词内容同段。
      关系：与关键词内容同一行，关键词内容紧跟其后。
      样式：宋体；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
    - 关键词内容
      类型：填充；是否填充：是
      内容：学生中文关键词；缺失时示例占位“关键词 1；关键词 2；……”并评论“原文未发现关键词，请补充”。
      位置：第 4 个元素；紧跟“关键词：”，不另起段。
      关系：排在固定“关键词：”之后，不另起标签行。
      分隔符：强制使用中文分号“；”。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。摘要标题、正文、关键词标签和同段关系与原始 DOCX 一致；缺失时保留占位并评论的策略合理。

2.4 英文摘要（abstract_en）
  页眉：北京大学博士学位论文
  页码：前置页页码规则，见 3.2
  缺失处理：如果没有识别到英文摘要或英文关键词，保留示例占位并添加人工评论。
  元素顺序：1 英文题名；2 作者英文名；3 Directed by Professor + 导师英文名；4 ABSTRACT；5 英文摘要正文；6 KEY WORDS:；7 英文关键词内容。
  排版关系：除第 6、7 个元素同段连续排布外，其余元素均各自独立成段，并相对上一个元素换行。
  元素：
    - 英文题名
      类型：填充；是否填充：是
      内容：英文论文题名；缺失时保留英文题名占位并评论。
      位置：第 1 个元素；独立段落。
      样式：Arial；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=2.5
    - 作者英文名
      类型：填充；是否填充：是
      内容：作者英文名；缺失时保留占位并评论。
      位置：第 2 个元素；独立段落，位于英文题名之后。
      样式：Times New Roman；12pt（小四）；居中；段前=0 行；段后=0 行；行距选项=1.5 倍行距；设置值=无
    - Directed by Professor + 导师英文名
      类型：固定+填充；是否填充：导师英文名需要填充
      内容：Directed by Professor + 导师英文名
      位置：第 3 个元素；独立段落，位于作者英文名之后。
      样式：Times New Roman；12pt（小四）；居中；段前=0 行；段后=0 行；行距选项=1.5 倍行距；设置值=无
    - ABSTRACT
      类型：固定；是否填充：否
      内容：ABSTRACT
      位置：第 4 个元素；独立段落，位于导师行之后。
      样式：Arial；16pt（三号）；居中；段前=1 行；段后=0.5 行；行距选项=多倍行距；设置值=2.5
      段落设置：大纲级别=1 级；与下段同页=是；段中不分页=是。
    - 英文摘要正文
      类型：填充；是否填充：是
      内容：学生英文摘要；缺失时保留英文摘要占位并评论。
      位置：第 5 个元素；独立段落，位于 ABSTRACT 之后。
      样式：Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
      段落设置：孤行控制=否；其余高级项默认/继承，需 Word 核对。
    - KEY WORDS:
      类型：固定；是否填充：否
      内容：KEY WORDS:
      位置：第 6 个元素的行首；与英文关键词内容同段。
      关系：与英文关键词内容同一行，英文关键词内容紧跟其后。
      样式：Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
    - 英文关键词内容
      类型：填充；是否填充：是
      内容：学生英文关键词；缺失时保留英文关键词占位并评论。
      位置：第 7 个元素；紧跟“KEY WORDS:”，不另起段。
      关系：排在固定“KEY WORDS:”之后，不另起标签行。
      分隔符：强制使用英文分号“;”。
      样式：Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。英文题名、作者英文名、导师行、ABSTRACT、正文和 KEY WORDS 同段标签与原始 DOCX 可见模板一致。

2.5 目录（toc）
  页眉：北京大学博士学位论文
  页码：前置页页码规则，见 3.2
  收录层级：主目录收录正文一级、二级、三级标题；四级及以下标题不进入目录。源模板字段为 TOC \o "3-3" \h \z \t "标题 1,1,标题 2,2,PKU正文前标题,9,PKU正文尾标题,9"。
  页码/引导线：条目文字左侧对齐；页码通过右对齐制表位靠右；中间点引导线由 Word 自动生成，长度随条目文字变化，不能用固定数量的点或空格替代。
  元素顺序：1 目录标题；2 前后置目录条目；3 正文一级目录条目；4 正文二级目录条目；5 正文三级目录条目。
  排版关系：目录标题独立成段；目录条目按 Word 自动目录结果逐条成段，页码在同一目录条目内通过右对齐制表位呈现。
  元素：
    - 目录标题
      类型：固定/生成；是否填充：否
      内容：目录
      样式：黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=2.5
      段落设置：大纲级别=1 级；与下段同页=是；段中不分页=是。
    - 前后置目录条目
      类型：生成；是否填充：是
      内容：摘要、ABSTRACT、目录、图目录、表目录、参考文献、附录、致谢、原创性声明等。
      连接规则：标题文字 + 制表符 + 页码。
      样式：中文黑体、英文/数字 Times New Roman；12pt（小四）；左对齐；段前=0.5 行；段后=0 行；行距选项=多倍行距；设置值=1.2；右侧页码点引导。
    - 正文一级目录条目
      类型：生成；是否填充：是
      内容：一级标题文字、点引导线、页码。
      连接规则：前导制表符 + 章号 + 制表符 + 章标题 + 制表符 + 页码。
      样式：中文黑体、英文/数字 Times New Roman；12pt（小四）；左对齐；段前=0.5 行；段后=0 行；行距选项=多倍行距；设置值=1.2；右侧页码点引导。
    - 正文二级目录条目
      类型：生成；是否填充：是
      内容：二级标题文字、点引导线、页码。
      连接规则：编号 + 制表符 + 标题文字 + 制表符 + 页码。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；左对齐；段前=0 行；段后=0 行；行距选项=多倍行距；设置值=1.2；右侧页码点引导。
    - 正文三级目录条目
      类型：生成；是否填充：是
      内容：三级标题文字、点引导线、页码。
      连接规则：编号 + 1 个半角空格 + 标题文字 + 制表符 + 页码。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；左对齐；段前=0 行；段后=0 行；行距选项=多倍行距；设置值=1.2；右侧页码点引导。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。主目录字段和目录结果条目均来自原始 DOCX；目录依赖样式而非单纯大纲级别这一点记录准确。

2.6 图目录（figure_list）
  页眉：图目录
  页码：前置页页码规则，见 3.2
  缺失处理：默认保留图目录页；未识别到图题时保留标题和空白条目区域，并添加人工评论。
  页码/引导线：图编号和图题按连接规则排列；页码通过右对齐制表位靠右；中间点引导线自动伸缩，不能手动写固定长度。
  元素顺序：1 图目录标题；2 图目录条目。
  排版关系：图目录标题独立成段；每条图目录条目独立成段，图编号、图题文字、页码位于同一条目内。
  元素：
    - 图目录
      类型：固定/生成；是否填充：否
      内容：图目录
      样式：黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=2.5
      段落设置：大纲级别=1 级；与下段同页=是；段中不分页=是。
    - 图目录条目
      类型：生成；是否填充：是
      内容：生成图编号、图题文字、页码。
      连接规则：前导制表符 + 前导制表符 + “图” + 1 个半角空格 + 章号.图号 + 制表符 + 图题文字 + 制表符 + 页码。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；左对齐；段前=0 行；段后=0 行；行距选项=多倍行距；设置值=1.2；右侧页码点引导。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。图目录标题、条目连接规则、右对齐制表位和 Word 自动生成机制均有源 DOCX 图目录字段和可见结果支持。

2.7 表目录（table_list）
  页眉：北京大学博士学位论文
  页码：前置页页码规则，见 3.2
  缺失处理：默认保留表目录页；未识别到表题时保留标题和空白条目区域，并添加人工评论。
  页码/引导线：表编号和表题按连接规则排列；页码通过右对齐制表位靠右；中间点引导线自动伸缩，不能手动写固定长度。
  元素顺序：1 表目录标题；2 表目录条目。
  排版关系：表目录标题独立成段；每条表目录条目独立成段，表编号、表题文字、页码位于同一条目内。
  元素：
    - 表目录
      类型：固定/生成；是否填充：否
      内容：表目录
      样式：黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=2.5
      段落设置：大纲级别=1 级；与下段同页=是；段中不分页=是。
    - 表目录条目
      类型：生成；是否填充：是
      内容：生成表编号、表题文字、页码。
      连接规则：前导制表符 + 前导制表符 + “表” + 章号.表号 + 制表符 + 表题文字 + 制表符 + 页码；“表”和编号之间无半角空格。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；左对齐；段前=0 行；段后=0 行；行距选项=多倍行距；设置值=1.2；右侧页码点引导。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。表目录标题、条目连接规则、右对齐制表位和 Word 自动生成机制均有源 DOCX 表目录字段和可见结果支持。

2.8 正文主体（body_main）
  页眉：默认使用当前章名称作为页眉标题；模板中存在“章名称/学校名称”不完全一致的情况，按模板问题记录，不作为生成标准。
  分页：每章另起页。
  范围：包含学生正文内容流和学校模板固定结尾章“结论与讨论”；不包含参考文献、附录、致谢、声明等后置单元。
  缺失处理：必要章节缺失时保留模板页/示例占位，并添加人工评论；学生没有提供固定结尾章内容时，保留“第五章 结论与讨论”章标题、示例占位和人工评论。
  正文文字与引用规则：
    规则：中文字体=宋体；英文/数字字体=Times New Roman。
    规则：全局字符间距控制=压缩标点。
    规则：普通正文段落未在 OOXML 中单独声明“自动调整中文与西文间距 / 中文与数字间距”，按默认/继承处理，需 Word 核对。
    规则：参考文献条目明确关闭“自动调整中文与西文间距”和“自动调整中文与数字间距”。
    规则：图、表、公式引用应使用 Word 交叉引用；错误引用项会显示“未找到引用源”，需要人工排查。
    规则：不主动判断或新增“重点/强调”等写作语义；学生原文已有加粗、斜体、下划线等内联格式时，按原文保留或人工确认。
  元素顺序：正文主体是内容流，不是一次性固定清单；章节内按学生论文顺序输出章标题、节标题、正文段落、列表、图、表、公式等内容单元；固定结尾章“结论与讨论”排在学生正文内容流之后、参考文献之前，章内内容按学生原文顺序输出。
  排版关系：章标题、节标题、正文段落、列表正文、提行引、图、表、公式默认独立成段或独立结构；文内参考文献索引、超链接、脚注引用属于正文内联元素；脚注正文位于页脚脚注区域。
  元素：
    - 章标题
      类型：填充/编号生成；是否填充：是
      内容：章号由模板生成；章标题填学生内容。示例“第一章 研究背景”。
      编号：格式=第%1章；编号与标题之间的分隔属于模板内容。模板编号文本未内置半角空格，实际显示的空格/制表符需按 Word 自动编号效果核对。
      样式：黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=1.5 倍行距；设置值=无
      段落设置：大纲级别=1 级。
    - 二级标题
      类型：填充/编号生成；是否填充：是
      内容：编号由模板生成；标题填学生内容。示例“1.1 准备工作”。
      编号：格式=%1.%2 + 1 个半角空格；编号、空格和标题之间的关系由模板编号规则生成。
      样式：中文黑体、英文/数字 Times New Roman；14pt（四号）；两端对齐；段前=1 行；段后=1 行；行距选项=单倍行距；设置值=无
      段落设置：大纲级别=2 级；与下段同页=是。
    - 三级标题
      类型：填充/编号生成；是否填充：是
      编号：格式=%1.%2.%3 + 1 个半角空格；编号、空格和标题之间的关系由模板编号规则生成。
      样式：中文黑体、英文/数字 Times New Roman；13pt；两端对齐；段前=1 行；段后=1 行；行距选项=单倍行距；设置值=无
      段落设置：大纲级别=3 级；与下段同页=是。
    - 四级/五级标题
      类型：填充/编号生成；是否填充：按学生内容
      内容：学校模板存在四级、五级标题示例；四级及以下标题不进入目录。
      编号：四级格式=%1.%2.%3.%4；五级格式=%1.%2.%3.%4.%5；编号后分隔需按 Word 自动编号效果核对。
      样式：中文黑体、英文/数字 Times New Roman；12pt（小四）；两端对齐；段前=1 行；段后=1 行；行距选项=单倍行距；设置值=无
    - 正文段落
      类型：填充；是否填充：是
      内容：学生正文。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
      段落设置：孤行控制=否；中西文/中文数字自动间距=默认/继承，需 Word 核对。
    - 文内参考文献索引
      类型：生成/填充；是否填充：按学生引用
      内容：正文中的引用标记，例如顺序编码制“[1]”或著者-出版年制引用。
      关系：作为正文内联元素，不单独成段；与参考文献条目体制一致。
      规则：顺序编码制和著者-出版年制只能选择一种，不能混用；建议由参考文献管理软件生成。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；加粗=否；上标=否；下标=否；基线=普通。
      注意：源模板没有文内参考文献索引示例；模板中出现的“[1]”类标记均为普通基线文本。如果参考文献管理软件生成了不同样式，需要人工确认是否保留。
    - 超链接
      类型：填充；是否填充：按学生内容
      内容：正文中的网址或链接文本。
      关系：正文内联字符，不单独成段。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；蓝色；单下划线；加粗=否；上标=否；下标=否。
      注意：TOC 内部链接也使用超链接字符样式，但目录由 Word 自动生成，不按正文链接处理。
    - 脚注引用
      类型：生成；是否填充：按学生脚注
      内容：正文中的脚注编号标记。
      关系：正文内联字符，对应页脚脚注内容。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；加粗=否；上标=是；下标=否。
    - 脚注正文
      类型：填充；是否填充：按学生脚注
      内容：页脚中的脚注内容。
      关系：由正文脚注引用对应生成。
      样式：中文宋体、英文/数字 Times New Roman；9pt（小五）；左对齐；对齐到文档网格=否。
    - 列表正文
      类型：填充；是否填充：按学生内容
      内容：正文中的有序列表或步骤列表。
      编号：由 Word 列表编号生成；编号和文字之间的分隔属于列表规则，不应手打。
      样式：基于正文段落；中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
      段落设置：列表缩进/悬挂随 Word 编号规则变化，需 Word 核对。
    - 提行引
      类型：填充；是否填充：按学生内容
      样式：楷体；12pt（小四）；两端对齐；左缩进 2 字符；首行缩进 2 字符；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=1.3
    - 图
      类型：填充/生成；是否填充：按学生内容
      内容：正文内图单元。
      组成元素：图本体、图名、图注（如有）。
      子元素顺序：1 图本体；2 图名；3 图注（如有）。
      排版关系：源模板实际图示例为图片段落在上、图名在下；图本体独立成段或独立图片段落；图名位于图本体下方并独立成段；图注如有则跟随对应图。
      组成元素明细：
        - 图本体
          内容：学生图片内容。
          位置：第 1 个子元素；位于图单元顶部。
          样式：图片本体字体/字号=不适用；图片所在段落中文宋体、英文/数字 Times New Roman；12pt（小四）；居中；段前=0 行；段后=0 行；行距选项=单倍行距；设置值=无；与下段同页=是。
          源模板样式：实际示例使用 `PKU图` 样式，段落居中，设置与下段同页。
        - 图名
          内容：生成图编号 + 图名文字。
          位置：第 2 个子元素；位于图本体下方，独立段落。
          样式：中文宋体、英文/数字 Times New Roman；11pt；居中；段前=0 行；段后=0.5 行；行距选项=单倍行距；设置值=无；孤行控制=否；段中不分页=是。
          源模板样式：实际示例使用 `PKU图题` 样式，位于图片下方。
          连接规则：“图” + 1 个半角空格 + 章号.图号 + 制表符 + 图名文字。
          编号/引用：图号使用域代码；新增图应复制模板已有图名并更新域，不应手打编号。
        - 图注（如有）
          内容：图单元内部说明文字。
          位置：第 3 个子元素；位于图题名之后，独立段落。
          样式：中文宋体、英文/数字 Times New Roman；10.5pt（五号）；两端对齐；左缩进约 2 字符；悬挂约 1 字符；段后=0.5 行。
      说明：图本体、图名和图注共同构成一个图单元；源模板示例为单行图名，未提供独立英文图名，本校专属标准不强制英文图名。若共享默认规则要求英文图名，应另行标注为默认规则。
    - 表格
      类型：填充/生成；是否填充：按学生内容
      内容：正文内表格单元。
      组成元素：表名、表体、表注（如有）。
      子元素顺序：1 表名；2 表体；3 表注（如有）。
      排版关系：源模板实际表示例为表名在表体上方，表注在表体下方；表名独立成段，表体位于题名下方，表注如有则位于表体下方并独立成段。
      组成元素明细：
        - 表名
          内容：生成表编号 + 表名文字。
          位置：第 1 个子元素；位于表格单元顶部，独立段落。
          样式：中文宋体、英文/数字 Times New Roman；11pt；居中；段前=0.5 行；段后=0 行；行距选项=单倍行距；设置值=无；与下段同页=是。
          源模板样式：实际示例使用 `PKU表题` 样式，位于表格上方。
          连接规则：“表” + 章号.表号 + 制表符 + 表名文字；“表”和编号之间无半角空格。
          编号/引用：表号使用域代码；新增表格应复制模板已有表名并更新域，不应手打编号。
        - 表体
          内容：学生表格结构和数据。
          位置：第 2 个子元素；位于表名下方。
          表格样式：PKU三线表；表格整体居中；单元格垂直居中。
          线型：顶线/底线=粗线 1.5 磅；表头下线=细线 0.5 磅；复杂表可保留辅助线，全文风格宜一致。
          结构保留：合并单元格、行列数量、分组表头属于表体结构，按学生内容保留。
          列宽：属于排版样式，不作为学生内容保留；按目标模板表格版式核对。
          跨页：按 Word 表格自然分页处理；可设置标题行跨页重复；不主动生成“续表”文本框或额外续表标题。
          表体内部元素：
            - 表头
              内容：表头、列名、分组标题等。
              样式：中文宋体、英文/数字 Times New Roman；10.5pt（五号）；居中；加粗=是；段前=3pt；段后=3pt。
            - 表内文字
              内容：表格数据单元格文字。
              样式：中文宋体、英文/数字 Times New Roman；10.5pt（五号）；居中；段前=3pt；段后=3pt。
        - 表注（如有）
          内容：表格单元内部说明文字。
          位置：第 3 个子元素；位于表体下方，独立段落。
          样式：中文宋体、英文/数字 Times New Roman；10.5pt（五号）；两端对齐；左缩进约 2 字符；悬挂约 1 字符；段后=0.5 行。
          源模板样式：实际示例使用 `PKU图表注` 样式，位于表格下方。
      说明：表名、表体和表注共同构成一个表格单元；源模板示例为单行表名，未提供独立英文表名，本校专属标准不强制英文表名。若共享默认规则要求英文表名，应另行标注为默认规则。
    - 公式
      类型：填充/生成；是否填充：按学生内容
      内容：正文内公式单元。
      组成元素：公式本体、公式编号。
      子元素顺序：1 公式本体；2 公式编号。
      排版关系：公式本体和公式编号位于同一个公式承载表格行内；公式本体居中，公式编号在右侧单元格右对齐。
      结构：公式整体使用一行三列表格承载；公式本体在中间单元格，公式编号在右侧单元格。
      示例核对：原始 DOCX 存在公式示例，公式本体为 `PKU公式` 样式，编号为 `PKU公式编号` 样式；复制公式时必须包含最外层三列表格。
      组成元素明细：
        - 公式本体
          内容：学生公式内容。
          位置：第 1 个子元素；位于公式承载表格中间单元格。
          样式：`PKU公式`；Cambria Math；11pt；居中；孤行控制=否。
        - 公式编号
          内容：生成公式编号。
          位置：第 2 个子元素；位于公式承载表格右侧单元格。
          样式：`PKU公式编号`；Times New Roman；11pt；右对齐；段前=0 行；段后=0 行；行距选项=单倍行距；设置值=无。
          编号：形式=(章号.公式序号)，例如 (2.1)。
      连接规则：模板使用表格实现公式居中、编号右对齐；不是靠普通空格或制表符手动对齐。
    - 固定结尾章：结论与讨论
      类型：固定章标题 + 填充正文；是否填充：章标题固定保留，章内内容由学生论文填充。
      内容：正文主体最后一个固定章节。
      子元素顺序：1 第五章 结论与讨论；2 章内学生内容流。
      排版关系：固定章标题独立成段；章内学生内容位于章标题之后，按学生原文顺序独立成段或独立结构；该章整体另起页，位于学生正文内容流之后、参考文献之前。
      说明：该章不作为独立一级单元；只有“第五章 结论与讨论”章标题是固定模板内容。模板中的“结论”“展望”按示例小节处理，不作为必须固定保留的小节标题；学生原文有对应小节时，按正文二级标题样式输出。
      组成元素明细：
        - 第五章 结论与讨论
          类型：固定/编号生成；是否填充：否
          内容：第五章 结论与讨论
          位置：第 1 个子元素；固定结尾章章标题，独立段落。
          编号：格式=第%1章；编号与标题之间的分隔同章标题规则，属于模板内容。
          样式：同章标题；黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=1.5 倍行距；设置值=无
          段落设置：大纲级别=1 级。
        - 章内学生内容流
          类型：填充；是否填充：是
          内容：学生在“结论与讨论”章内提供的内容；可包含二级/三级标题、正文段落、列表、图、表、公式等正文内容单元。
          位置：第 2 个子元素；位于固定章标题之后，按学生原文顺序输出。
          样式：复用正文主体对应元素样式；普通段落同正文段落，二级标题同正文二级标题，图/表/公式同正文图/表/公式规则。
  仍需人工核对：
    核对：普通正文中“中文与英文 / 中文与数字”间距在 Word UI 中的最终显示。
    核对：全角/半角标点、中文括号/英文括号是否需要转换。
    核对：学生原文已有表格的合并单元格等结构是否完整保留。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：按原始 DOCX 实际示例补充图/表/公式相对位置和样式：图片在图名上方，表名在表体上方，表注在表体下方，公式用三列表格承载且公式本体/编号分别使用 `PKU公式` 和 `PKU公式编号` 样式；同时仍不强制英文图名/英文表名。

2.9 参考文献（references）
  页眉：北京大学博士学位论文
  元素顺序：1 参考文献标题；2 参考文献条目。
  排版关系：参考文献标题独立成段；每条参考文献条目独立成段，序号和文献正文在同一段内通过制表符连接。
  元素：
    - 参考文献
      类型：固定；是否填充：否
      内容：参考文献
      样式：黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=2.5
    - 参考文献条目
      类型：填充；是否填充：是
      内容：学生参考文献；每条独立成段。
      序号：顺序编码制示例为 [1] + 制表符 + 文献正文；著者-出版年制示例不带方括号序号。两种体制不能混用。
      连接规则：顺序编码制序号后使用制表符，不是普通空格。
      样式：中文宋体、英文/数字 Times New Roman；10.5pt（五号）；两端对齐；左缩进约 2 字符；悬挂缩进约 2 字符；段前=0 行；段后=6pt；行距选项=多倍行距；设置值=1.3
      段落设置：自动调整右缩进=否；自动调整中文与西文间距=否；自动调整中文与数字间距=否。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。参考文献标题、条目缩进、顺序编码制/著者-出版年制二选一和制表符连接规则均与源模板说明一致。

2.10 附录A  博士期间工作成果（academic_achievements）
  页眉：北京大学博士学位论文
  缺失处理：默认保留学校模板中的附录成果模块；无成果内容时保留标题、成果类别、占位并添加人工评论。
  元素顺序：1 附录A  博士期间工作成果；2 成果类别标题；3 成果条目。
  排版关系：附录标题、成果类别标题均独立成段；每条成果条目独立成段。
  元素：
    - 附录A  博士期间工作成果
      类型：固定；是否填充：否
      内容：附录A  博士期间工作成果
      连接规则：“附录” + 附录编号A + 2 个半角空格 + 标题文字。
      样式：黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=2.5
    - 成果类别标题
      类型：固定模板类别；是否填充：否
      内容：期刊论文、会议论文、参与项目、获得专利与软件著作权
      样式：黑体；14pt（四号）；两端对齐；段前=1 行；段后=1 行；行距选项=单倍行距；设置值=无
    - 成果条目
      类型：填充；是否填充：是
      内容：学生对应成果。
      连接规则：模板示例为 [1] + 制表符 + 成果正文；项目/专利类示例后面还有制表符分隔的类别字段，需 Word 核对。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。附录 A 标题和成果类别来自源模板；无成果内容时保留模板模块和人工评论的策略合理。

2.11 致谢（acknowledgement）
  页眉：北京大学博士学位论文
  缺失处理：默认保留学校模板中的致谢模块；无致谢内容时保留标题、占位并添加人工评论。
  元素顺序：1 致谢；2 致谢正文。
  排版关系：致谢标题独立成段；致谢正文位于标题之后，按学生内容分段。
  元素：
    - 致谢
      类型：固定；是否填充：否
      内容：致谢
      样式：黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=2.5
    - 致谢正文
      类型：填充；是否填充：是
      内容：学生致谢。
      样式：中文宋体、英文/数字 Times New Roman；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0.5 行；段后=0.5 行；行距选项=多倍行距；设置值=1.3
      段落设置：孤行控制=否；其余高级项默认/继承，需 Word 核对。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。致谢标题和正文样式与原始 DOCX 的后置页模板一致；无致谢内容时保留占位并评论。

2.12 原创性声明和使用授权说明（originality_authorization_statement）
  页眉：北京大学博士学位论文
  同页约束：本单元基本由学校固定表单内容组成，应按固定版面页处理；原创性声明、签名/日期、使用授权说明、授权条目、保密说明和授权签名/日期不得被拆成普通可流动正文。签名/日期区不得单独被挤到下一页；如固定内容因版面变化溢出，应标记为版面问题或人工调整项。
  元素顺序：1 北京大学学位论文原创性声明和使用授权说明；2 原创性声明；3 原创性声明正文；4 原创性声明签名/日期；5 学位论文使用授权说明；6 装订说明；7 授权说明正文；8 授权说明条目；9 保密论文说明；10 授权说明签名/日期。
  排版关系：固定标题、正文、签名/日期、授权条目均按学校模板顺序独立成段或表单项；不自动填充签名/日期。
  元素：
    - 北京大学学位论文原创性声明和使用授权说明
      类型：固定；是否填充：否
      内容：北京大学学位论文原创性声明和使用授权说明
      样式：黑体；16pt（三号）；居中；段前=1 行；段后=1 行；行距选项=多倍行距；设置值=2.5
    - 原创性声明
      类型：固定；是否填充：否
      内容：原创性声明
      样式：宋体；14pt（四号）；加粗；居中；段前=0 行；段后=0 行；行距选项=1.5 倍行距；设置值=无
    - 原创性声明正文
      类型：固定；是否填充：否
      内容：本人郑重声明：所呈交的学位论文，是本人在导师的指导下，独立进行研究工作所取得的成果。除文中已经注明引用的内容外，本论文不含任何其他个人或集体已经发表或撰写过的作品或成果。对本文的研究做出重要贡献的个人和集体，均已在文中以明确方式标明。本声明的法律结果由本人承担。
      样式：宋体；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0 行；段后=0 行；行距选项=1.5 倍行距；设置值=无
    - 原创性声明签名/日期
      类型：固定表单项；是否填充：否
      内容：论文作者签名：                    日期：      年   月   日
      样式：宋体；12pt（小四）；右对齐；段前=0 行；段后=0 行；行距选项=1.5 倍行距；设置值=无
    - 学位论文使用授权说明
      类型：固定；是否填充：否
      内容：学位论文使用授权说明
      样式：宋体；14pt（四号）；加粗；居中；段前=0 行；段后=0 行；行距选项=1.5 倍行距；设置值=无
    - 装订说明
      类型：固定；是否填充：否
      内容：（必须装订在提交学校图书馆的印刷本）
      样式：宋体；9pt（小五）；居中；段前=0 行；段后=0 行；行距选项=单倍行距；设置值=无
    - 授权说明正文
      类型：固定；是否填充：否
      内容：本人完全了解北京大学关于收集、保存、使用学位论文的规定，即：
      样式：宋体；12pt（小四）；两端对齐；首行缩进 2 字符；段前=0 行；段后=0 行；行距选项=1.5 倍行距；设置值=无
    - 授权说明条目
      类型：固定；是否填充：否
      内容：按照学校要求提交学位论文的印刷本和电子版本；学校有权保存学位论文的印刷本和电子版，并提供目录检索与阅览服务，在校园网上提供服务；学校可以采用影印、缩印、数字化或其它复制手段保存论文；因某种特殊原因需要延迟发布学位论文电子版，授权学校□一年/□两年/□三年以后，在校园网上全文发布。
      样式：宋体；12pt（小四）；两端对齐；左缩进约 3.2 字符；悬挂缩进约 1.2 字符；段前=0 行；段后=0 行；行距选项=1.5 倍行距；设置值=无
    - 保密论文说明
      类型：固定；是否填充：否
      内容：（保密论文在解密后遵守此规定）
      样式：宋体；12pt（小四）；居中；段前=0 行；段后=0 行；行距选项=1.5 倍行距；设置值=无
    - 授权说明签名/日期
      类型：固定表单项；是否填充：否
      内容：论文作者签名：                导师签名：；日期：      年   月   日
      样式：宋体；12pt（小四）；右对齐；段前=0 行；段后=0 行；行距选项=1.5 倍行距；设置值=无
      段落设置：允许西文在单词中间换行=否；其余高级项默认/继承，需 Word 核对。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。原创性声明、使用授权说明、授权条目、保密说明、签名和日期空位均与原始 DOCX 末尾固定声明页一致。

================================================================================
3. 全局规则（第三层级）
================================================================================

3.1 页面设置
  纸张：A4
  常规页边距：上=30.0mm；下=25.01mm；左=26.0mm；右=26.0mm；装订线=0.0mm
  页眉/页脚距离：页眉=15.01mm；页脚=17.5mm
  页眉内容归属：这里只记录页眉位置参数；页眉显示文字写在各单元中。
  Word section 规则：只有页眉内容、页码格式/起始、页边距、横竖版等 section 级属性发生变化时才需要新 section；新 section 应断开 Link to Previous，避免页眉页脚串联。
  横向页：上=26.0mm；下=26.0mm；左=25.01mm；右=30.0mm
  文档网格：前置页多为 lines 网格、linePitch=326；正文及后置页通常为 lines 网格、linePitch=312，后置页包括参考文献、附录、致谢、原创性声明和使用授权说明等；横向页 linePitch=326
  默认段落：默认对齐=两端对齐；默认字号=12pt（小四）；字符间距控制=压缩标点
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。常规页边距、页眉/页脚距离、横向页边距和文档网格均来自原始 DOCX section 设置；section 只在页面属性变化时切换。

3.2 页码
  归属：这里只记录跨单元共享的页码格式、字体字号和编号连续性；每个单元只标明采用前置页规则或正文/后置页规则。
  前置页：页脚居中；Times New Roman；10.5pt（五号）；大写罗马数字；中文摘要起始页为 I
  正文及所有后置页：页脚居中；Times New Roman；10.5pt（五号）；阿拉伯数字页码；从正文首页起始并连续编号。后置页包括参考文献、附录、致谢、原创性声明和使用授权说明等。
  Word section 规则：从前置页切到正文页码时新开 section，并将正文页码格式设为阿拉伯数字、起始页为 1；后置页沿用正文页码并继续编号，除非页眉或版式变化需要新 section。
  页脚段落设置：对齐到文档网格=否；其余高级项默认/继承，需 Word 核对。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 已修改：前置页页码由“小写罗马数字 i”改为“大写罗马数字 I”；原始 DOCX `pgNumType` 为 upperRoman，目录可见页码也是 I/II/III。

3.3 全局段落高级项
  需要逐元素关注：
    - 同样式段落间不加空格
    - 定义文档网格时对齐网格
    - 定义文档网格时自动调整右缩进
    - 孤行控制
    - 与下段同页
    - 段中不分页
    - 段前分页
    - 中文与西文间距
    - 中文与数字间距
    - 允许西文在单词中间换行
  规则：如果某个单元或元素有特别设置，写在对应单元；这里只记录全局需要关注的项目。
  判定（匹配 / 不匹配 / 不确定 / 不需要）：
  备注：
  👨 无异议。这里记录的是需要逐元素关注的高级项清单，具体开关仍落在各元素样式或源 DOCX 样式定义中核对。

================================================================================
4. 本校总评
================================================================================
4.1 单元顺序需要修改的点：
4.2 单元内部内容/样式需要修改的点：
4.3 全局规则需要修改的点：
4.4 需要后续决策的点：
~~~~


## Full Student Content Review Sources

The following sections are embedded verbatim from the human student content
review sources. They are the review facts for title metadata, ignored
donor content, abstracts, keywords, ordered body flow, visible objects,
references, appendix, and acknowledgement.

### Source: `real-student-001`

- Path: `inputs/real-student-001-content-review.md`
- SHA-256: `sha256:fae06e0474920b7258ce7d5e7358ff665d599d09880e8b6761bbfd75248c7078`

~~~~text
# 关②人工内容识别标准说明：001.docx

## 标题

- 中文标题：植物促生菌PGP6生长素合成基因的鉴定与功能验证
- 英文标题：Identification and Functional Characterization of Indole-3-Acetic Acid Biosynthesis-Related Genes in the Plant Growth-Promoting Rhizobacterium PGP6

## 应忽略的 donor-school 或模板自带前置页

```text
- 南京农业大学空白/未填写封面表格：忽略，不进入学生内容 IR。
- 南京农业大学原创性声明：忽略，不进入学生内容 IR。
- 南京农业大学使用授权声明：忽略，不进入学生内容 IR。
- 原稿旧目录：忽略，目标成品目录后续由目标学校流程生成。
```

## 中文摘要

存在中文摘要。标题为“摘要”。正文应由下面两段组成，顺序不变：

1. 植物根际促生菌（Plant growth-promoting rhizobacteria, PGPR）是一类能够定殖于植物根际，并通过促进养分吸收、合成植物激素、增强植物抗逆性及抑制病原菌等方式促进植物生长的有益微生物。与传统化肥和农药相比，PGPR具有环境友好、生态适应性强等特点，在绿色农业生产和污染土壤植物修复中具有重要应用潜力。其中，PGPR合成吲哚-3-乙酸（Indole-3-acetic acid, IAA）是其发挥促生作用的重要机制之一，但不同菌株中IAA合成相关基因及其功能贡献仍存在差异，需通过遗传学手段进一步验证。
2. 植物根际促生菌PGP6（Pantoea sp.）来源于南京栖霞山重金属污染农田根际土壤，具有合成IAA及促进植物生长的潜力。为解析PGP6中IAA合成相关基因的功能，本研究以trpA、trpB、patB及iaaH等候选基因为对象，首先采用Salkowski比色法测定PGP6的IAA合成能力，并通过抗生素最小抑菌浓度实验确定遗传操作筛选条件；随后基于全基因组注释结果定位IAA合成相关候选基因，设计并构建含上下游同源臂和卡那霉素抗性标记的线性打靶片段；进一步利用pKD46介导的λ-Red同源重组体系构建目标基因缺失突变株，并通过PCR和测序进行验证；最后比较野生型菌株与各突变株的IAA产量差异。结果表明，PGP6在含0.5 mg/mL色氨酸的YN培养基中可稳定产生IAA，野生型菌株IAA产量为80.81±2.95 mg/L；PGP6 ΔtrpA::kan、PGP6 ΔtrpB::kan、PGP6 Δ(trpA-trpB)::kan、PGP6 ΔpatB::kan和PGP6 ΔiaaH::kan突变株的IAA产量均低于野生型，其中ΔpatB::kan突变株平均降幅最大。上述结果说明trpA、 trpB、 patB及iaaH等基因均可能参与PGP6的IAA合成或其前体代谢过程，但单一基因缺失未完全阻断IAA产生，提示PGP6中IAA合成可能存在多基因协同或替代代谢途径。本研究为阐明PGP6的IAA合成遗传基础及促生机制提供了实验依据，也为后续植物促生菌剂开发与植物-微生物互作研究奠定基础。

## 中文关键词

按原顺序：

1. 植物根际促生菌
2. PGP6
3. 吲哚-3-乙酸
4. λ-Red同源重组
5. 基因敲除

## 英文摘要

存在英文摘要。标题为 `ABSTRACT`。正文应由下面三段组成，顺序不变：

1. Plant growth-promoting rhizobacteria (PGPR) are beneficial microorganisms that colonize the rhizosphere and promote plant growth by enhancing nutrient uptake, producing phytohormones, improving stress tolerance, and suppressing phytopathogens. Among these mechanisms, bacterial production of indole-3-acetic acid (IAA) is considered an important factor contributing to plant growth promotion. However, the genetic basis of IAA biosynthesis varies among bacterial strains and requires further functional verification.
2. In this study, the plant growth-promoting rhizobacterium PGP6 (Pantoea sp.), isolated from heavy metal-contaminated rhizosphere soil in Qixia Mountain, Nanjing, was used to investigate IAA biosynthesis-related genes. Four candidate genes, trpA, trpB, patB, and iaaH, were selected based on whole-genome annotation. The IAA-producing ability of PGP6 was first determined using the Salkowski colorimetric assay, and antibiotic minimum inhibitory concentration assays were performed to establish suitable selection conditions for genetic manipulation. Linear targeting fragments containing upstream and downstream homologous arms and a kanamycin resistance cassette were then constructed. Subsequently, trpA, trpB, trpA-trpB, patB, and iaaH deletion mutants were generated using the pKD46-mediated λ-Red homologous recombination system and verified by PCR and sequencing. Finally, IAA production in the wild-type strain and the mutants was quantitatively compared.
3. The results showed that PGP6 stably produced IAA in YN medium supplemented with 0.5 mg/mL tryptophan, with the wild-type strain producing 80.81 ± 2.95 mg/L IAA. The IAA yields of PGP6 ΔtrpA::kan, ΔtrpB::kan, Δ(trpA-trpB)::kan, ΔpatB::kan, and ΔiaaH::kan were all lower than that of the wild type, with ΔpatB::kan showing the greatest average reduction. These findings suggest that trpA, trpB, patB, and iaaH may participate in IAA biosynthesis or precursor metabolism in PGP6. Nevertheless, single-gene deletion did not completely abolish IAA production, indicating that multiple genes or alternative pathways may contribute to IAA biosynthesis in this strain. This study provides experimental evidence for understanding the genetic basis of IAA production in PGP6 and lays a foundation for further studies on plant-microbe interactions and PGPR-based biofertilizer development.

## 英文关键词

按原顺序：

1. Plant growth-promoting rhizobacteria
2. PGP6
3. Indole-3-acetic acid
4. λ-Red-mediated homologous recombination
5. Gene knockout

## 正文标题结构（不是原稿目录）

```text
level 1: 文献综述
  level 2: PGPR促进植物生长的主要机制
    level 3: PGPR促进植物生长的直接作用
    level 3: 本研究的目的和意义
    level 3: 技术路线
  level 2: 打靶片段的设计与构建
    level 3: 实验材料
    level 3: 打靶片段引物设计
    level 3: 打靶片段的扩增、检测及回收
    level 3: 生长素标准曲线的制定
    level 3: 菌株PGP6的抗生素最小抑菌浓度实验
```

## 正文段落顺序

```text
1. level 1: 文献综述
2. paragraph: 植物根际促生菌（Plant growth-promoting rhizobacteria, PGPR）是一类定殖于植物根际能够促进植物生长的有益微生物。早在1904年，Hiltner就提出了“根际”概念，将根际土壤中的微生物称为根际微生物，并指出其中2%~5%为有益微生物。这些有益菌能够促进植物生长、发育并提高其逆境抗性，被Kloepper等人在20世纪70年代定义为PGPR[1]。与传统化肥和农药相比，PGPR具有环境友好、提高养分利用率、增强植物抗逆性和抑制病害等优势，因此近年来成为研究热点。常见的PGPR包括假单胞菌属(Pseudomonas)、芽孢杆菌属(Bacillus)、肠杆菌属(Enterobacter)、伯克霍尔德菌属(Burkholderia)、农杆菌属(Agrobacterium)、泛菌属(Pantoea)、无色杆菌属(Achromobacter)、黄杆菌属(Flavobacterium)和沙雷菌属(Serratia)等。
3. level 2: PGPR促进植物生长的主要机制
4. paragraph: PGPR对植物的促生作用机制复杂多样，总体可分为直接作用和间接作用两大类。直接作用是指PGPR直接促进植物营养获取或调节植物激素水平，例如固氮、溶磷、解钾以及合成植物激素（如生长素Indole-3-acetic Acid, IAA等）和挥发性物质等。间接作用则是PGPR通过拮抗植物病原菌、诱导植物抗性或缓解非生物胁迫（干旱、盐碱、重金属等）来间接促进植物生长[19][20][21][22][23]。
5. level 3: PGPR促进植物生长的直接作用
6. paragraph: 植物根际促生细菌（PGPR）通过一系列直接机制促进植物生长发育[2]，核心体现在为植物提供必需营养元素和合成促进植物生长的活性物质两大方面。
7. level 3: 本研究的目的和意义
8. paragraph: PGP6是一株来源于重金属污染农田根际土壤的植物根际促生菌，前期研究表明其具有较强的IAA合成能力及植物促生潜力。然而，PGP6中参与IAA生物合成的关键基因及其功能贡献尚未得到系统验证，限制了对其促生机制的深入解析。基于此，本研究以PGP6为研究对象，围绕其IAA合成相关候选基因开展功能验证，旨在从遗传学层面明确trpA、trpB、patB及iaaH 等基因在PGP6合成IAA过程中的作用。
9. level 3: 技术路线
10. image 1: 本论文研究的技术路线；Experimental flowchart of the thesis
11. level 2: 打靶片段的设计与构建
12. paragraph: 为从遗传学层面验证PGP6中IAA合成相关候选基因的功能，本研究基于λ-Red同源重组技术（λ-Red homologous recombination）构建目标基因缺失突变株。该技术以外源线性DNA片段为重组底物，在同源臂介导下与宿主染色体发生同源重组，从而实现目标基因的定向替换。因此，高质量线性打靶片段的设计与构建是保证同源重组效率与准确性的关键前提。在前期全基因组注释及候选基因筛选的基础上，本章以trpA、trpB、patB及iaaH四个基因为研究对象，利用SnapGene软件设计扩增引物，通过聚合酶链式反应（Polymerase Chain Reaction, PCR）分别扩增目标基因上下游约0.8–1.2 kb的同源臂片段，并以pJOE8999质粒为模板扩增卡那霉素抗性基因（Kanamycin resistance marker, KmR）。随后采用重叠延伸PCR技术，将上游同源臂、抗性片段及下游同源臂拼接构建完整的线性打靶片段，为后续电转化及同源重组提供分子基础。
13. level 3: 实验材料
14. paragraph: （1）E.Z.N.A.®Gel Extraction Kit（OMEGA胶回收试剂盒），pJOE8999质粒。
15. level 3: 打靶片段引物设计
16. paragraph: 根据PGP6全基因组注释结果，获取目标基因trpA、trpB、patB及iaaH的核苷酸序列，并选取其上下游约0.8-1.2 kb的序列作为同源臂区域。利用SnapGene软件对目标基因的上下游同源臂区域进行分析，在此基础上设计用于扩增同源臂片段的引物。在引物设计过程中，综合考虑引物长度（通常为18-25 bp）、退火温度（Tm值控制在55-65℃且上下游引物Tm值相近）及GC含量（40%–60%）等关键参数，以保证扩增反应的特异性与稳定性。同时，通过在引物端引入适当的重叠序列，为后续重叠延伸PCR拼接提供条件。设计完成后，将引物序列提交南京擎科生物科技有限公司进行合成。
17. level 3: 打靶片段的扩增、检测及回收
18. paragraph: 以PGP6基因组DNA为模板，通过聚合酶链式反应（Polymerase Chain Reaction, PCR）分别扩增目标基因trpA、trpB、patB及iaaH的上游和下游同源臂片段，同时以pJOE8999质粒为模板扩增卡那霉素抗性基因（Kanamycin resistance marker, KmR）片段，对各片段进行1%琼脂糖凝胶电泳检测及DNA纯化。在获得各目标片段后，采用重叠延伸PCR技术将上游同源臂、抗性标记片段及下游同源臂拼接，构建完整的线性打靶片段。扩增产物经琼脂糖凝胶电泳分离，通过凝胶成像系统观察条带大小及特异性，选取与预期长度一致且条带清晰的目标片段。随后切取对应条带，使用E.Z.N.A.®Gel Extraction Kit（OMEGA）胶回收试剂盒按照说明书进行DNA纯化，获得纯化的线性打靶片用于后续电转化实验。
19. table 1: PCR反应体系；PCR Reaction System；6 行 x 2 列：第1行 组分 | 体积；第2行 2×Phanta Max Master Mix | 25μL；第3行 Primer_F | 1μL；第4行 Primer_R | 1μL；第5行 Template DNA | 2μL；第6行 ddH2O | up to 50μL。
20. level 3: 生长素标准曲线的制定
21. paragraph: 为定量评价PGP6合成IAA的能力，本研究以不同浓度IAA标准液建立Sackowki's比色检测体系。标准液在530 nm处的吸光值随IAA浓度增加而升高，线性回归方程为y=0.01505x+0.1027，R²=0.9662（图3-1），说明在检测浓度范围内A530与IAA浓度具有较好的线性关系，可用于发酵液中IAA含量的换算。为后续评价候选基因缺失对IAA合成的影响提供了野生型对照基础。
22. image 2: IAA标准曲线；Standard curve for IAA quantification
23. level 3: 菌株PGP6的抗生素最小抑菌浓度实验
24. paragraph: 为确定PGP6遗传操作中的抗性筛选条件，本研究比较了PGP6对氨苄青霉素、卡那霉素、壮观霉素、氯霉素、庆大霉素、四环素和链霉素的敏感性。结果显示，不同抗生素对PGP6的抑制作用存在明显差异（表1-1）。其中，卡那霉素和四环素在较低浓度下即可抑制PGP6野生型的可见生长，适合作为后续重组片段和pKD46辅助质粒的筛选压力；壮观霉素在50 μg/mL条件下不抑制PGP6生长，可用于不影响PGP6背景生长的联合培养条件。
25. table 2: PGP6对不同抗生素的敏感性结果；Antibiotic susceptibility of PGP6；8 行 x 3 列：第1行 抗生素 | 实验观察结果 | 后续遗传操作中的判定；第2行 氨苄青霉素（Amp） | 10-100 μg/mL后期仍可见缓慢生长；200 μg/mL未见可见生长 | 未作为本研究主要遗传筛选抗生素；第3行 卡那霉素（Km） | 0-200 μg/mL未见可见生长 | 后续以50 μg/mL作为KmR重组子的筛选压力；第4行 壮观霉素（Spc） | 30-50 μg/mL可生长，PGP6对该抗生素具有一定耐受性 | 50 μg/mL不抑制PGP6背景生长，可与其他抗性条件联合使用；第5行 氯霉素（Cm） | 30-100 μg/mL可见生长 | 未作为本研究主要遗传筛选抗生素；第6行 庆大霉素（Gm） | 20-80 μg/mL未见可见生长 | 抑菌作用明确，本研究未作为主要筛选标记；第7行 四环素（Tet） | 10-50 μg/mL未见可见生长 | 后续以50 μg/mL用于pKD46辅助质粒筛选；第8行 链霉素（Str） | 低温低浓度条件下仍可见或延迟生长，抑菌稳定性弱于Km和Tet | 未作为本研究主要遗传筛选抗生素。
26. paragraph: 本研究以植物根际促生菌PGP6为对象，围绕其IAA合成相关候选基因开展定位、敲除和功能验证。通过Salkowski比色法建立IAA标准曲线，获得线性回归方程y=0.01505x+0.1027，R²=0.9662；在后续的实验中，野生型PGP6在含0.5 mg/mL色氨酸的YN培养基中培养72 h后，IAA产量为80.81±2.95 mg/L，表明该菌株具有稳定合成IAA的能力。
27. paragraph: 抗生素MIC实验结果表明，PGP6对不同抗生素的敏感性存在差异。其中卡那霉素和四环素对PGP6野生型具有明确抑制作用，因此本研究采用Km 50 μg/mL筛选卡那霉素抗性替换重组子，采用Tet 50 μg/mL筛选或维持pKD46辅助质粒，为后续λ-Red同源重组实验建立了可靠的抗性筛选条件。
28. paragraph: 功能验证结果表明，与野生型PGP6相比，所有缺失突变株的平均IAA产量均有所降低，其中ΔtrpA::kan、ΔtrpB::kan、Δ(trpA-trpB)::kan和ΔiaaH::kan的IAA产量降幅约为8%–9%，ΔpatB::kan的平均降幅最大，达到19.29%。该结果说明trpA、trpB、patB和iaaH均可能参与PGP6的IAA合成或其前体代谢过程，但任一候选基因缺失均未完全阻断IAA产生，提示PGP6的IAA合成可能存在多基因协同调控或替代代谢途径。
```

## 图片

应识别为正文图片 2 个；位置按上面“正文流正确答案模板”的编号定位：

1. 正文流第 10 项；位于第 9 项之后、第 11 项开始之前。中文题名：本论文研究的技术路线。英文题名：Experimental flowchart of the thesis。
2. 正文流第 22 项；位于第 21 项之后、第 23 项开始之前。中文题名：IAA标准曲线。英文题名：Standard curve for IAA quantification。

## 表格

原始 DOCX 中有 3 个表格，其中第 1 个是未填写的南京农业大学封面表格，应忽略。
应作为论文内容识别的表格为 2 个：

1. PCR 反应体系表，正文流第 19 项；位于第 18 项之后、第 20 项开始之前。表格为 6 行 2 列，表头为“组分 / 体积”。中文表名：PCR反应体系。英文表名：PCR Reaction System。
2. PGP6 对不同抗生素的敏感性结果表，正文流第 25 项；位于第 24 项之后、第 26 项开始之前。表格为 8 行 3 列，表头为“抗生素 / 实验观察结果 / 后续遗传操作中的判定”。中文表名：PGP6对不同抗生素的敏感性结果。英文表名：Antibiotic susceptibility of PGP6。

## 参考文献

存在参考文献区，条目按原顺序为：

1. Kloepper J W, Schroth M N. Plant growth-promoting rhizobacteria on radishes[A]//Proceedings of the 4th International Conference on Plant Pathogenic Bacteria[C]. Angers: INRA, 1978: 879-882.
2. Lugtenberg B, Kamilova F. Plant-growth-promoting rhizobacteria[J]. Annual Review of Microbiology, 2009, 63: 541-556. DOI:10.1146/annurev.micro.62.081307.162918.

## 附录

原稿存在“附录”标题，但未见附录正文内容。按人工批注，只有空标题时不作为学生内容识别；目标学校如果需要附录页，由目标模板流程处理。

## 致谢

存在致谢标题和 1 段正文：

1. 提笔致谢，四年的本科生涯也即将结束，心中满是感慨与谢意。这段旅程，每一步探索少不了老师的教诲、同窗的扶持以及家人和朋友的默默支持。
~~~~

### Source: `real-student-002`

- Path: `inputs/real-student-002-content-review.md`
- SHA-256: `sha256:2f54077297d25d77a65ba41d571c001d9dc47db83c26f3947fee5a7cb2f6d0db`

~~~~text
# 关②人工内容识别标准说明：002.docx

## 标题

- 中文标题：多环芳烃污染土壤的微生物组协同修复工艺及技术条件研究
- 英文标题：A STUDY ON MICROBIAL CONSORTIUM-MEDIATED REMEDIATION OF POLYCYCLIC AROMATIC HYDROCARBON-CONTAMINATED SOIL AND ITS TECHNICAL PARAMETERS

## 应忽略的 donor-school 或模板自带前置页

```text
无。
```

## 中文摘要

存在中文摘要。标题为“摘要”。正文应由下面 1 段组成：

1. 多环芳烃（PAHs）是化工场地土壤中广泛检出的一类具有“致畸、致癌、致突变”效应的持久性有机污染物，其与土壤有机质的强结合作用导致残留态PAHs生物可利用性低、降解困难，且传统物理化学修复技术易破坏土壤生态-生产功能。本研究面向化工场地PAHs污染土壤的原位绿色修复需求，构建了由6株PAHs降解菌（涵盖低、中、高分子量PAHs降解菌）和3株植物促生菌组成的复合菌群，优化了菌群复配比例、施加时间及固定化载体类型，通过液体摇瓶实验、土壤培养实验和空心菜盆栽实验，系统考察了固定化菌剂对16种PAHs的去除效能、对植物生长的影响及对土壤理化性质的调控作用，并探讨了载体-微生物协同增效机制。主要结果如下：复合菌群最佳复配比例为1:20（v:v），48h内对液体中总PAHs去除率达68.67%，其中低分子量PAHs在12h内快速降解，中高分子量PAHs需更长时间；四种生物质载体中稻壳和玉米芯粉对PAHs的吸附效果最佳，将菌群固定于玉米芯粉后，对土壤中中分子量PAHs（87.55%）和高分子量PAHs（64.30%）的去除率显著高于单独载体或游离菌，45d后S-XF组对总PAHs去除率保持最高，证实了“吸附-富集-降解”级联协同效应；S-XF处理使空心菜株高较对照提高105.6%，污染物去除率与植物生长指标呈显著正相关；修复过程中土壤pH保持稳定（7.46–8.05），外源碳载体短期提升有机质和阳离子交换量，但45d后有机质基本恢复至对照水平，活性菌群的存在会削弱载体对阳离子交换量的提升作用，总体未对土壤造成不可逆的理化性质破坏。本研究提出的玉米芯粉固定化复合菌群修复工艺兼顾了污染物高效去除与土壤生态功能恢复，为化工场地PAHs污染土壤的绿色可持续原位修复提供了技术支撑和理论依据。

## 中文关键词

按原顺序：

1. 多环芳烃
2. 污染土壤
3. 微生物组协同修复
4. 固定化菌剂
5. 共代谢

## 英文摘要

存在英文摘要。英文题名位于英文摘要标题前；标题原文疑似写作 `ABSRTACT`，系统可按模板标题规范化为 `ABSTRACT`。正文应由下面 1 段组成：

- 英文题名：A STUDY ON MICROBIAL CONSORTIUM-MEDIATED REMEDIATION OF POLYCYCLIC AROMATIC HYDROCARBON-CONTAMINATED SOIL AND ITS TECHNICAL PARAMETERS

1. Polycyclic aromatic hydrocarbons (PAHs) are a class of persistent organic pollutants widely detected in the soil of chemical industrial sites that exhibit teratogenic, carcinogenic, and mutagenic effects. Their strong binding to soil organic matter results in low bioavailability and difficult degradation of residual PAHs, and traditional physicochemical remediation techniques often disrupt the soil’s ecological and productive functions. This study addressed the need for in-situ green remediation of PAH-contaminated soil at chemical sites by constructing a composite microbial consortium comprising six PAH-degrading bacteria (covering low-, medium-, and high-molecular-weight PAH-degrading strains) and three plant-promoting bacteria. The optimal ratios of the microbial consortium, application timing, and types of immobilization carriers were determined. Through liquid shake flask experiments, soil cultivation experiments, and water spinach pot experiments, the study systematically investigated the removal efficiency of the immobilized microbial agent for 16 types of PAHs, its impact on plant growth, and its regulatory effects on soil physicochemical properties, while also exploring the synergistic mechanism between the carrier and microorganisms. The main results are as follows: The optimal formulation ratio for the composite microbial consortium was 1:20 (v:v), achieving a total PAH removal rate of 68.67% in liquid within 48 hours. Among these, low-molecular-weight PAHs degraded rapidly within 12 hours, while medium- and high-molecular-weight PAHs required a longer time; Among the four biomass carriers, rice husks and corn cob powder exhibited the best adsorption performance for PAHs. When the microbial consortium was immobilized on corn cob powder, the removal rates of medium-molecular-weight PAHs (87.55%) and high-molecular-weight PAHs (64.30%) in soil were significantly higher than those of the carriers alone or free-living bacteria; After 45 days, the S-XF group maintained the highest removal rate for total PAHs, confirming the “adsorption-enrichment-degradation” cascade synergistic effect; S-XF treatment increased the plant height of water spinach by 105.6% compared to the control, and pollutant removal rates showed a significant positive correlation with plant growth indices; Soil pH remained stable (7.46–8.05) throughout the remediation process. The exogenous carbon carrier temporarily increased organic matter and cation exchange capacity, but organic matter levels largely returned to control levels after 45 days. The presence of active microbial communities attenuated the carrier’s effect on cation exchange capacity, and overall, no irreversible damage to the soil’s physicochemical properties was observed. The immobilized composite microbial community remediation process using corn cob powder proposed in this study balances the efficient removal of pollutants with the restoration of soil ecological functions, providing technical support and theoretical basis for the green and sustainable in-situ remediation of PAH-contaminated soils at chemical industrial sites.

## 英文关键词

按原顺序：

1. Polycyclic aromatic hydrocarbons
2. contaminated soil
3. microbial consortium-mediated remediation
4. immobilized microbial agents
5. co-metabolism

## 正文标题结构（不是原稿目录）

```text
level 1: 文献综述
  level 2: 化工场地土壤PAHs污染特征与生态风险
    level 3: 化工场地PAHs污染现状
    level 3: 不同分子量PAHs在土壤中的赋存行为差异
  level 2: PAHs的微生物降解途径与代谢机理
level 1: 土壤多环芳烃微生物组转化工艺技术条件
  level 2: 材料与方法
    level 3: 菌株、培养基与试剂
  level 2: 结果与分析
    level 3: 菌群复配比例和反应条件优化及固定化载体选择
level 1: 结论与展望
  level 2: 结论
  level 2: 展望
```

## 正文段落顺序

```text
1. level 1: 文献综述
2. level 2: 化工场地土壤PAHs污染特征与生态风险
3. level 3: 化工场地PAHs污染现状
4. paragraph: 近些年来，随着城市化进程加速和工业企业搬迁，遗留了大量污染场地，其中多环芳烃（PAHs）是一类广泛检出的具有“致畸、致癌、致突变”效应的有毒有机污染物。化工场地的PAHs污染具有浓度高、深度大、形态复杂等特点。对某一废弃化工厂场地土壤的垂直剖面调查发现，PAHs总残留含量在2.64m和5.76m深度处分别高达1622.13mg/kg和1665.65mg/kg，主要以有机可溶态存在，且低分子量（LMW-PAHs）和中分子量（MMW-PAHs）PAHs占主导地位。在污染场地中，超过90%的结合态LMW-PAHs和MMW-PAHs赋存于胡敏素中，而23.1%~47.2%的高分子量PAHs（HMW-PAHs）与富里酸和胡敏酸结合[1]。PAHs与土壤有机质的结合过程抑制了PAHs降解菌和降解基因在场地土壤中的丰度增加，导致深层污染土壤中PAHs残留难以被生物降解，存在较高的环境和健康风险[2]。
5. level 3: 不同分子量PAHs在土壤中的赋存行为差异
6. paragraph: 不同分子量的PAHs在土壤中的赋存行为存在显著差异，主要受其物理化学性质如辛醇-水分配系数LogKow、水溶性Sw和土壤有机质组成的影响。LMW-PAHs（如萘、菲）具有较高的水溶性和挥发性，在土壤中更易发生挥发和迁移，其挥发量与老化时间呈线性关系（R²=0.88~0.98），而MMW-PAHs和HMW-PAHs在土壤中具有更高的残留率。在土壤老化过程中，HMW-PAHs更易与土壤腐殖质结合形成结合态残留，在低有机碳含量的土壤中，结合态转化率顺序为HMW-PAHs>MMW-PAHs>LMW-PAHs。吸附实验表明，PAHs的土壤有机碳归一化分配系数LogKoc是决定其在土壤中平衡分配系数Kd的最关键因素，两者存在显著线性关系（R2=0.79~0.93）。此外，溶解性有机质（DOM）与PAHs及其衍生物的结合作用研究表明，官能团取代会抑制DOM与PAHs的结合，从而改变PAHs衍生物在土壤环境中的迁移能力。
7. level 2: PAHs的微生物降解途径与代谢机理
8. level 1: 土壤多环芳烃微生物组转化工艺技术条件
9. paragraph: 本章围绕化工场地多环芳烃污染土壤的微生物组协同修复工艺开展系统的实验研究，内容涵盖复合菌群构建、降解条件优化、固定化载体筛选及修复效能验证。以课题组前期筛选获得的PAHs降解菌与市售促生菌为材料构建复合菌群，优化其复配比例与施加时间，并筛选适宜的生物质固定化载体。采用吸附法制备固定化菌剂，通过土壤培养实验考察其对16种PAHs的去除效能，同时利用空心菜盆栽实验评估修复过程对植物生长的影响。在此基础上，系统测定修复前后土壤pH、有机质、水溶性盐及阳离子交换量等理化指标，阐明微生物修复对土壤生态功能的作用。本章研究旨在确定最佳的固定化工艺参数与固定化载体筛选，揭示载体-微生物协同增效机制，为化工场地PAHs污染土壤的绿色原位修复提供数据支撑和技术依据。
10. level 2: 材料与方法
11. level 3: 菌株、培养基与试剂
12. paragraph: 菲、苊烯降解菌IOCCSR-10010 Diaphorobactersp. Phe15和IOCCSR-10011 Mycolicibacteriumsp. Pyr9；芘、蒽、荧蒽降解菌IOCCSR-10001 Mycobacterium flavescens(ATCC®700033™)以及苯并芘降解菌IOCCSR-10013 Altererythrobacter epoxidivorans.sp和IOCCSR-10017 Meyerozyma guilliermondii.sp均为课题组前期工作筛选纯化得到；促生菌ACCC60428 Bacillusamyloliquefaciens、ACCC19468 Paenibacillus barcinonensis和ACCC19743 Bacillussubtilis购自中国农业微生物菌种保藏管理中心。
13. paragraph: 实验所用16种多环芳烃的性质如下表1所示，均购自上海阿拉丁生化科技股份有限公司；邻菲啰啉（C12H8N2·H2O，≥99%）、重铬酸钾（K2Cr2O7，≥99%）、乙酸铵(C2H7NO2,≥99%)购自国药集团化学试剂有限公司；浓硫酸（H2SO4，≥98%）、浓盐酸（HCl，≥99%）、无水硫酸钠（Na2SO4，≥99%）、甲醇（CH3OH,≥99.5%，色谱纯）、二氯甲烷（CH2Cl2，≥99.5%，色谱纯）、正己烷（CH3（CH2）4CH3,≥99.5%，色谱纯）、丙酮（CH3COCH3,≥99.5%，色谱纯）购自南京化学试剂有限公司。
14. table 1: 16种多环芳烃及其基本理化性质；16 Polycyclic Aromatic Hydrocarbons and Their Basic Physical and Chemical Properties；17 行 x 5 列：第1行 PAHs | 环数 | 分子量(g/mol) | 水溶解度(mg/L,25°C) | logKow(亲疏水性)；第2行 萘（Nap） | 2 | 128.17 | 31 | 3.37；第3行 苊烯（Any） | 3 | 152.2 | 16.1 | 4.07；第4行 苊（Ace） | 3 | 154.21 | 3.93 | 3.98；第5行 芴（Flu） | 3 | 166.22 | 1.98 | 4.18；第6行 菲（Phe） | 3 | 178.23 | 1.15 | 4.57；第7行 蒽（Ant） | 3 | 178.23 | 0.045 | 4.54；第8行 荧蒽（Fla） | 4 | 202.26 | 0.26 | 5.22；第9行 芘（Pyr） | 4 | 202.26 | 0.132 | 5.18；第10行 苯并[a]蒽（BaA） | 4 | 228.29 | 0.011 | 5.91；第11行 䓛（Chr） | 4 | 228.29 | 0.002 | 5.86；第12行 苯并[b]荧蒽（BbF） | 5 | 252.32 | 0.0015 | 6.04；第13行 苯并[k]荧蒽（BkF） | 5 | 252.32 | 0.0008 | 6.11；第14行 苯并[a]芘（BaP） | 5 | 252.32 | 0.0038 | 6.06；第15行 二苯并[a,h]蒽（DiahA） | 5 | 278.35 | 0.0006 | 6.75；第16行 茚并[1,2,3-cd]芘（InPy） | 6 | 276.34 | 0.00019 | 6.7；第17行 苯并[g,h,i]苝（BghiP） | 6 | 276.34 | 0.00026 | 6.63。
15. level 2: 结果与分析
16. level 3: 菌群复配比例和反应条件优化及固定化载体选择
17. paragraph: （1）菌群复配比例优化
18. paragraph: 菌群复配比例是影响多环芳烃降解效率的关键因素。如图2-1所示，对于LMW-PAHs和总多环芳烃（Σ-PAHs），1:10、1:20和1：25的菌群复配比例具有更高的去除率，对于中高分子量多环芳烃（MHW-PAHs），1：20的去除率显著高于1：10和1：25，综合来看1：20是最合适的菌群复配比例，在该条件下，菌群可能形成了更稳定的微生态系统，优化了降解酶的分泌及底物利用效率，提高了污染物的降解效率。这表明通过调控菌群复配比例可以有效提升生物修复效能，为后续固定化菌剂的功能验证提供了最优接种条件。
19. image 1: 5种复配比例下菌群对多环芳烃的去除率；Removal Efficiency of Microbial Communities for Polycyclic Aromatic Hydrocarbons Under 5 Different Blending Ratios
20. level 1: 结论与展望
21. level 2: 结论
22. paragraph: 本研究围绕化工场地多环芳烃污染土壤，构建了由6株PAHs降解菌与3株植物促生菌组成的复合菌群，优化了复配比例及固定化工艺，并在人工污染土壤中验证了其修复效能及对土壤生态功能的影响。主要结论如下：
23. paragraph: （1）菌群优化与降解性能：复合菌群最佳复配比例为1:20（v:v），48 h内对液体中16种PAHs的总去除率达68.67%；其中低分子量PAHs在12 h内快速降解，而中高分子量PAHs需要更长的作用时间。
24. level 2: 展望
25. paragraph: 尽管本研究在实验室尺度上证明了玉米芯粉固定化复合菌群修复PAHs污染土壤的可行性与优越性，但仍存在以下关键问题需要在未来研究中深入探讨：
```

## 图片

应识别为正文图片 1 个；位置按上面“正文流正确答案模板”的编号定位：

1. 正文流第 19 项；位于第 18 项之后、第 20 项开始之前。中文题名：5种复配比例下菌群对多环芳烃的去除率。英文题名：Removal Efficiency of Microbial Communities for Polycyclic Aromatic Hydrocarbons Under 5 Different Blending Ratios。

## 表格

应作为论文内容识别的表格为 1 个：

1. 正文流第 14 项；位于第 13 项之后、第 15 项开始之前。表格为 17 行 5 列。中文表名：16种多环芳烃及其基本理化性质。英文表名：16 Polycyclic Aromatic Hydrocarbons and Their Basic Physical and Chemical Properties。

## 参考文献

存在参考文献区，条目按原顺序为：

1. Tang L, Zhao X Q, Chen X W, et al. Distribution of bound-PAH residues and their correlations with the bacterial community at different depths of soil from an abandoned chemical plant site [J]. Journal of Hazardous Materials, 2023, 453: 131328
2. Tang L, Bao Z K, Zhao X Q, et al. Variations of different PAH fractions and bacterial communities during the biological self-purification in the soil vertical profile [J]. Journal of Hazardous Materials, 2023, 458: 131903

## 附录

未见附录区。

## 致谢

未见致谢区。
~~~~

### Source: `real-student-003`

- Path: `inputs/real-student-003-content-review.md`
- SHA-256: `sha256:a444c2826368c75c10e7e6df780fdc496e7ab139ee5ae55de0100f9b79c6583c`

~~~~text
# 关②人工内容识别标准说明：003.docx

## 标题

- 中文标题：磷肥不同施肥量对米粉稻产量性状的影响研究
- 英文标题：Study on the effect of different amount of phosphate fertilizer on the yield traits of rice flour rice

## 应忽略的 donor-school 或模板自带前置页

```text
- 湖南农业大学封面、诚信声明、作者/导师/学院/日期等固定前置页：忽略，不进入正文流。
- 封面中的真实中英文题名：只作为标题/元信息保留，不作为正文段落。
- 英文摘要前的 Title of Graduation Paper、Student、Tutor、英文单位地址：忽略，不作为英文标题或英文摘要正文。
- 摘要正文和关键词：不进入正文流；分别保留在摘要/关键词标准模板中。
```

## 中文摘要

存在中文摘要。原稿为 `摘 要：正文...` 同段格式；标准正文不包含 `摘 要：` 标签。正文应由下面 1 段组成：

1. 在保障国家粮食安全和提高农产品质量的宏观战略下，优化肥料施用技术以推动水稻生产的高效与可持续发展，已成为农业领域的重点研究方向。作为重要的加工专用稻类型，米粉稻产量性状的稳定与提升，直接影响稻米加工产业的原料供应和经济效益。然而，在实际生产中，磷肥施用量常缺乏精准的调控依据，过量或不足不仅易导致资源浪费和环境污染，还会制约作物产量与品质潜力的发挥。为此，本研究以专用米粉稻品种中嘉早17与两系杂交稻品种株两优4024为材料，在长沙和沅陵两地进行大田实验。试验采用双因素随机区组设计，设置0kg/hm²（P0）、30kg/hm²P(30)、60kg/hm²(P60)、90kg/hm²(P90)4个不同的磷肥梯度，测定不同磷肥施用量对米粉稻产量及产量性状的影响。结果表明，磷肥施用在适当范围内会提高米粉稻产量，过量磷肥则不利于产量的进一步提高甚至导致减产，但在实验中这些影响均不显著。有效穗数同穗粒数与千粒重之间呈现负相关，水稻产量的提升是协调寻找这三者的大小关系来完成的。

## 中文关键词

按原顺序：

1. 磷肥施用量
2. 米粉稻
3. 产量性状

## 英文摘要

存在英文摘要。原稿在英文摘要前有 `Title of Graduation Paper`、`Student`、`Tutor` 和英文单位地址等模板前导；这些不作为英文摘要正文。`Abstract:` 标签也不进入正文。正文应由下面 1 段组成：

1. Under the macro strategy of ensuring national food security and improving the quality of agricultural products, optimizing fertilizer application technology to promote the efficient and sustainable development of rice production has become a key research direction in the field of agriculture. As an important type of processing special rice, the stability and improvement of yield traits of rice flour rice directly affect the raw material supply and economic benefits of rice processing industry. However, in actual production, the application amount of phosphate fertilizer often lacks precise control basis. Excessive or insufficient application of phosphate fertilizer not only leads to waste of resources and environmental pollution, but also restricts the potential of crop yield and quality. In this study, a field experiment was conducted in Changsha and Yuanling with the special rice flour rice variety Zhongjiazao 17 and two-line hybrid rice variety Zhuliangyou 4024 as materials. A two-factor randomized block design was used in the experiment. Four different phosphorus fertilizer gradients of 0 kg / hm2 ( P0 ), 30 kg / hm2 P ( 30 ), 60 kg / hm2 ( P60 ) and 90 kg / hm2 ( P90 ) were set up to determine the effects of different phosphorus fertilizer application rates on the yield and yield traits of rice flour rice. The results showed that the application of phosphate fertilizer in an appropriate range would increase the yield of rice flour, and excessive phosphate fertilizer was not conducive to further increase the yield or even lead to yield reduction, but these effects were not significant in the experiment. There is a negative correlation between the number of effective panicles and the number of grains per panicle and 1000-grain weight. The improvement of rice yield is coordinated to find the relationship between the three.

## 英文关键词

按原顺序：

1. Phosphate fertilizer application amount
2. rice flour rice
3. yield traits

## 正文标题结构（不是原稿目录）

```text
level 1: 前言
  level 2: 研究背景与意义
    level 3: 试验材料
  level 2: 测定项目方法
    level 3: 产量及产量构成性状测定
    level 3: 数据统计与分析
level 1: 结果与分析
  level 2: 磷肥不同施用量对不同水稻品种的产量的影响
level 1: 讨论
level 1: 结论
```

## 正文段落顺序

```text
1. level 1: 前言
2. level 2: 研究背景与意义
3. paragraph: 水稻作为我国三大粮食作物之一，其种植面积约占粮食作物总面积的27%，稻谷产量约占粮食总产量的40%[1]，水稻不仅直接提供口粮，也是多种传统食品加工的重要原料。其中米粉稻是指稻米直链淀粉含量较高、适宜制作米粉等米制品的专用水稻。我国作为稻米消费大国，米粉等传统米制品市场需求持续增长，但长期以来，优质米粉专用稻品种相对缺乏，限制了米粉加工产业的原料升级与品质提升。近年来，育种工作取得显著进展，一系列高产且加工特性优良的米粉稻品种（如“特优269”、“湘早籼32号”等）相继育成并推广，为米粉稻产业发展奠定了品种基础[2]。水稻高产优质栽培是米粉稻产业发展的关键，而想要实现水稻高产，就要研究更好的施肥措施。大量研究表明，氮肥施用量显著影响米粉稻的产量、直链淀粉含量及加工品质[3]。然而，相较于氮肥，磷肥对米粉稻产量性状的调控效应尚不明确。磷素是水稻生长发育必需的营养元素，对根系发育、分蘖形成及籽粒灌浆具有重要作用。现有研究表明，适量施用磷肥能普遍促进水稻株高、有效分蘖数及产量增加，但过量则会降低磷肥利用效率甚至抑制产量[4][5]。在专用米粉稻生产中，磷肥的施用量如何影响其产量构成因素，从而影响水稻产量还缺乏系统性的依据。产量构成因子之间往往存在补偿机制，例如有效穗数增多可能导致每穗粒数下降，而千粒重的提高又可能伴随穗数的减少。此外，米粉稻对直链淀粉含量的特殊要求，使其产量形成过程中可能对不同磷肥施用表现出与普通水稻不同的规律。明确磷肥对米粉稻各产量形状的调控规律，有助于不牺牲稻米加工适宜性的前提下，充分发挥米粉稻的产量潜力，降低生产成本，提高种植效益，同时减少多余磷素排放，符合绿色、可持续发展的农业要求。
4. level 3: 试验材料
5. paragraph: 中嘉早17，株两优4024，其中中嘉早17是常规稻，直链淀粉含量较高，为专用于米粉加工的品种，株两优4024则是两系杂交稻，产量潜力较高。
6. level 2: 测定项目方法
7. level 3: 产量及产量构成性状测定
8. paragraph: 成熟期收获时在每小区随机从一株开始连续调查30株的有效穗数，按每穴平均有效穗数取5穴，考查每穗总粒数、每穗实粒数、千粒重、结实率，计算理论产量。
9. paragraph: 避免校区边上3行，随机收取100穴水稻，用谷物水分测定仪测定含水量，实际产量按照标准含水量13%折算。
10. level 3: 数据统计与分析
11. paragraph: 数据统计分析采用Microsoft Excel与Origin进行数据整理与图表绘制，所有试验数据的相关性分析均使用SPSS软件完成，不同磷肥处理间的差异显著性采用单因素方差分析，所有分析结果均以均值±标准差的形式呈现，显著性水平设定为α=0.05。
12. level 1: 结果与分析
13. level 2: 磷肥不同施用量对不同水稻品种的产量的影响
14. paragraph: 如图 1 在长沙地区，中嘉早17的平均实际产量为6854.31kg/hm²，株两优4024的平均实际产量为8094.29kg/hm²，在不同施磷量下两品种产量差异不显著，中嘉早17在P60处理下产量最高，较P30处理和P90处理分别增产9.16%和8.39%。株两优4024在P0处理下产量达到最高，为8442.99kg/hm²，较P90增产8.28%，而P60处理的产量也要高于P30和P90。在沅陵地区，中嘉早17的平均产量为8981.60kg/hm²，在P30处理下的实际产量最高，为9676.0733kg/hm²，较P0增产7.76%。株两优4024的平均产量为8901.84kg/hm²，以P0为对照，P30和P60分别减产3.04%和0.29%，而P90增产10.76%。各磷水平下产量差异不明显。
15. image 1: 不同水稻品种在不同施磷量下的实际产量；Actual yield of different rice varieties under different phosphorus application rates
16. image 2: 不同磷肥施用量下水稻的理论产量
17. table 1: 不同磷肥施用量下水稻的产量性状；Yield traits of rice under different phosphorus fertilizer application rates；17 行 x 6 列：第1行  | 处理 | 有效穗数(×105/hm2) | 每穗粒数 | 结实率（%） | 千粒重（g）；第2行 长沙-中嘉早17 | P0 | 25.51±3.62a | 137.68±8.39a | 75.82±4.21a | 25.73±1.15a；第3行  | P30 | 23.25±3.05a | 151.50±9.49a | 80.51±7.68a | 26.62±0.86a；第4行  | P60 | 24.54±2.86a | 136.98±4.86a | 74.56±8.61a | 24.17±1.68a；第5行  | P90 | 24.69±1.07a | 136.35±5.15a | 71.19±2.51a | 24.68±2.08a；第6行 长沙-株两优4024 | P0 | 31.07±4.67a | 92.34±8.68a | 85.82±1.59a | 30.42±3.43a；第7行  | P30 | 27.78±3.09a | 100.62±12.83a | 87.34±2.07a | 30.82±1.65a；第8行  | P60 | 27.78±4.66a | 104.84±18.07a | 88.99±0.93a | 28.60±2.92a；第9行  | P90 | 27.18±3.01a | 96.79±8.12a | 88.19±1.34a | 29.89±0.90a；第10行 沅陵-中嘉早17 | P0 | 41.00±5.68a | 144.77±25.03a | 72.38±4.46a | 26.01±1.84a；第11行  | P30 | 40.12±6.18a | 165.59±40.89a | 75.33±0.69a | 25.90±2.45a；第12行  | P60 | 38.34±10.21a | 168.43±20.00a | 76.47±4.36a | 24.95±0.99a；第13行  | P90 | 35.54±2.25a | 177.72±14.65a | 76.08±2.59a | 25.05±0.81a；第14行 沅陵-株两优4024 | P0 | 42.34±8.15a | 113.76±11.64a | 77.61±5.63a | 27.24±3.60a；第15行  | P30 | 48.76±6.14a | 142.15±16.02a | 76.66±2.05a | 24.42±3.81a；第16行  | P60 | 40.64±10.50a | 135.85±8.89a | 74.13±0.70a | 28.61±2.41a；第17行  | P90 | 42.59±3.44a | 125.14±21.44a | 73.14±2.55a | 27.04±2.02a。
18. level 1: 讨论
19. paragraph: 本研究表明，随着施磷量的增加，水稻总产量总体呈现先增加后下降的变化趋势，这与前人研究[22]得出的结论类似，反映了磷肥施用对水稻生长的有着双重调控作用。从产量结果来看，两个供试水稻品种对磷肥施用量的响应在长沙与沅陵两地表现出不同的趋势，且处理间差异均未达到显著水平。在长沙地区，中嘉早17在P60处理下产量最高，为7282.90 kg/hm²，较P0增产8.01%，而P30和P90处理产量略低于P0，降幅分别为1.05%和0.35%，总体呈现为P60＞PO＞P90＞P30；株两优4024则在P0处理下产量最高，达到8442.99 kg/hm²，所有施磷处理均表现出一定量的减产，但减产并不显著。在沅陵地区，中嘉早17在P30处理下产量最高达到9676.07 kg/hm²，较P0增产7.76%，而P60和P90处理则分别减产3.44%和4.23%；株两优4024在P90处理下产量最高，较P0增产10.76%，但P30和P60处理略有减产，另有实验表明[23]，施肥超过最佳水平时，产量反而下降，这也与本实验中产量呈现抛物线的变化趋势相吻合。而两个品种的最高产量均出现在不同的施磷水平，与闫金垚等[24]的实验结果相似，表明品种间对磷肥的吸收利用存在差异。从产量构成性状分析，有效穗数和每穗粒数对磷肥施用的反应相对敏感，磷肥施用过多（P90）会对水稻有效穗数整体呈抑制作用，在多数情况下会减少有效穗数，降幅约13-15%，磷肥施用量控制在P0-P30范围内即可维持或获得最高有效穗数，超过P30后穗数不增反降，P90为最差处理。磷肥施用量直接影响米粉稻的产量构成因子。本研究结果表明，磷肥用量过低或过高都会造成水稻的有效穗数的减少[25]，且千粒重随施磷量呈先增后减趋势[26]，这与前人研究结果一致。且有效穗数与每穗实粒数存在负相关[27]，有效穗数增多会使其他产量构成因素减少，这与前人研究相符[28]，表明产量性状构成因素之间不能全部同时增加，只有协调各产量构成因素，寻找最适施磷量，才能达到最佳产量。千粒重在本试验中受磷肥影响较小，符合前人研究结论[29]，施用磷肥后，水稻产量主要归因于单位面积有效穗数、每穗粒数的增加和结实率的提高。
20. level 1: 结论
21. paragraph: 在供试的两个地区中，长沙地区中嘉早17在P60处理下产量最高，较P0增产8.01%，而P30和P90处理产量略低于P0；株两优4024则在P0处理下产量最高，所有施磷处理均表现为减产，其中P90减产幅度最大（7.65%）。沅陵地区中嘉早17在P30处理下产量最高，较P0增产7.76%，P60和P90处理则表现为减产；株两优4024在P90处理下产量最高，较P0增产10.76%，P30和P60处理产量低于P90。两个品种对磷肥的响应特征存在明显差异，在实际生产中应根据土壤有效磷含量和品种对磷素的响应特性制定差异化的磷肥管理方案。水稻各产量性状不太可能实现同时增长，协调他们之间的关系，寻找最适施肥量是提高产量的可行步骤。
```

## 图片

应识别为正文图片 2 个；位置按上面“正文流正确答案模板”的编号定位：

1. 正文流第 15 项；位于第 14 项之后、第 16 项开始之前。中文题名：不同水稻品种在不同施磷量下的实际产量。英文题名：Actual yield of different rice varieties under different phosphorus application rates。
2. 正文流第 16 项；位于第 15 项之后、第 17 项开始之前。中文题名：不同磷肥施用量下水稻的理论产量。英文题名：未见独立英文图题。

## 表格

应作为论文内容识别的表格为 1 个：

1. 正文流第 17 项；位于第 16 项之后、第 18 项开始之前。表格为 17 行 6 列。中文表名：不同磷肥施用量下水稻的产量性状。英文表名：Yield traits of rice under different phosphorus fertilizer application rates。

## 参考文献

存在参考文献区，条目按原顺序为：

1. FAO. FAOSTAT: FAO Statistical Databases[EB/OL]. Rome: Food and Agriculture Organization of the United Nations, 2007.

## 附录

未见附录区。

## 致谢

未见致谢区。
~~~~


## Full Shared Alignment Review Source

This source defines the shared document-unit -> unit-element -> sub-element
model used to align template extraction, student content extraction,
placement, and render verification.

### Source: `shared-template-recognition-alignment`

- Path: `inputs/shared-template-recognition-alignment-review.txt`
- SHA-256: `sha256:8efd4bb76da5ac7f5aa0806b7fb97055146095c13a5673e991285ea6ba0d0069`

~~~~text
学校模板审查、学生文档识别、合成渲染对齐说明
日期：2026-06-09

依据：
- /Users/fl/ws/gogo/docfit/output/standards-workbench/gate1-template-review/approved-school-template-reviews-2026-06-09/school-template-hierarchical-review-v2-2026-06-08.txt
- /Users/fl/ws/gogo/docfit/docs/human/standard-unit-tree-synthesizer.md
- /Users/fl/ws/gogo/docfit/src/docfit/semantic/content_tree.py

================================================================================
1. 这份文件解决什么问题
================================================================================

当前学校模板审查已经从“平铺样式清单”转成了“单元 -> 元素 -> 子元素”的层级标准。

后续学生文档识别和最终合成也应该使用同一套层级模型，否则会出现三类问题：

1. 学校模板知道“表格 = 中文表名 + 英文表名 + 表体 + 表注”，但学生识别只抽出一堆段落和表格，无法可靠对齐。
2. 学生文档识别知道某段是图题、某个表是表格，但合成时又按扁平 block 流插入，容易把图题、表题、注释放散。
3. Word 最终是线性 OOXML 流，但放置决策如果直接在线性流里做，会丢失“属于哪个单元”的语义。

结论：

模板提取、学生识别、合成渲染都应该先对齐到同一个层级结构，再落到 Word 的段落、表格、图片、section。

================================================================================
2. 共同核心模型
================================================================================

共同模型分三层：

1. 文档单元（unit）
   论文里的结构块，例如封面、中文摘要、图目录、正文主体、参考文献、致谢。

2. 单元元素（element）
   单元里的具体内容，例如“摘要标题”“摘要正文”“关键词标签”“关键词内容”。

3. 复合子元素（sub-element / nested unit）
   图、表、公式这类正文内部复合对象的内部组成。

示例：

中文摘要（unit）
  1 摘要（fixed element）
  2 摘要正文（student element）
  3 关键词：（fixed element）
  4 关键词内容（student element）

图（body nested unit）
  1 图本体（student element）
  2 中文图名（student/generated element）
  3 英文图名（student/default-required element）
  4 图注（student optional element）

表格（body nested unit）
  1 中文表名（student/generated element）
  2 英文表名（student/default-required element）
  3 表体（student element）
      - 表头
      - 表内文字
      - 合并单元格/行列结构
  4 表注（student optional element）

================================================================================
3. 三套输入/输出必须对齐
================================================================================

3.1 学校模板提取输出：Template Unit Contract

学校模板提取负责回答：

- 目标学校论文有哪些单元？
- 单元顺序是什么？
- 哪些单元是固定模板内容？
- 哪些单元是模板默认保留？
- 每个单元内部有哪些元素？
- 元素顺序是什么？
- 哪些元素必须同页、同组或不能被分页切散？
- 每个元素的样式、编号、页眉、页码、缺失处理是什么？

学校模板提取不应该只输出样式列表，也不应该只输出段落列表。

它应该输出类似这样的结构：

template_unit:
  id: abstract_en
  order: 40
  required: true
  source_policy: student_source + target_school_template
  page:
    header_text: 北京大学博士学位论文
    page_number_profile: front_matter_roman
  layout_constraints:
    keep_within_page: false
    keep_together_groups:
      - [abstract_en.keyword_label, abstract_en.keyword_content]
  elements:
    - order: 10
      id: abstract_en.english_title
      fill_policy: content
      source_policy: student_metadata
    - order: 20
      id: abstract_en.author_english_name
      fill_policy: content
      source_policy: student_metadata
    - order: 30
      id: abstract_en.advisor_line
      fill_policy: fixed_plus_content
      fixed_text: Directed by Professor
      source_policy: student_metadata
    - order: 40
      id: abstract_en.title
      fill_policy: fixed
      fixed_text: ABSTRACT
    - order: 50
      id: abstract_en.body
      fill_policy: content
      source_policy: student_source
    - order: 60
      id: abstract_en.keyword_label
      fill_policy: fixed
      fixed_text: KEY WORDS:
    - order: 70
      id: abstract_en.keyword_content
      fill_policy: content
      source_policy: student_source

3.2 学生文档识别输出：Student Content Tree

学生文档识别负责回答：

- 学生文档里识别到了哪些内容？
- 每个内容属于哪个标准单元？
- 如果是正文内容，它属于哪一章、哪一节、哪个图/表/公式？
- 识别置信度如何？
- 有没有无法归属、低置信度、结构异常的内容？

学生识别不能只输出平铺段落。

它可以先从 CleanContentIR 得到对象流，但必须进一步归入标准单元树：

student_content_tree:
  abstract_cn:
    body: ...
    keywords: [...]
  abstract_en:
    english_title: ...
    author_english_name: ...
    advisor_english_name: ...
    body: ...
    keywords: [...]
  body_main:
    chapters:
      - title: ...
        sections:
          - title: ...
            flow:
              - paragraph
              - figure
              - table
              - formula
  references:
    items: [...]

正文识别尤其要避免平铺：

不推荐：
  paragraph, paragraph, table, paragraph, image, caption, paragraph

推荐：
  chapter
    section
      paragraph
      table
        caption_zh
        caption_en
        body
        note
      figure
        image
        caption_zh
        caption_en

3.3 合成渲染输入：Aligned Render Plan

合成渲染负责把学校模板合同和学生内容树对齐：

render_plan = template_unit_contract + student_content_tree + school_default_policy

render_plan 还必须包含“同页约束 / layout_constraints”：

- 单元是否必须完整留在同一页，例如封面、固定表单页。
- 某些元素是否必须同页，例如声明正文和签名区、标题和首段。
- 某些复合对象是否必须同组，例如图本体和图题、表题和表体开头。
- 如果内容溢出一页，是允许自然分页，还是必须报告人工调整。

同页约束的识别原则：

- 如果一个单元基本都是学校模板固定内容，不随学生正文长度自由增减，通常应推定为固定版面页并检查同页约束。
- 如果一个单元主要承载学生内容且长度可能大幅变化，例如参考文献、附录正文、致谢正文，则不要求整个单元同页，只检查标题与首段、图题/表题等局部组约束。
- 固定模板页被拆页时，优先视为版面完整性问题，而不是把被拆出的元素重新识别成新单元。

每个输出节点都应该能回答：

- 我要输出哪个单元？
- 这个单元来自学校模板、学生内容，还是系统生成？
- 学生内容缺失时是保留模板、生成占位、跳过，还是人工处理？
- 输出时应该使用哪个样式？
- 是否需要新 Word section？
- 是否需要 Word 字段？
- 是否有同页/同组约束，以及约束失败时如何报告？

================================================================================
4. 单元处理策略
================================================================================

每个 unit 应该至少有这些策略：

- source_policy
  - target_school_template
  - student_source
  - system
  - mixed

- fill_policy
  - fixed
  - content
  - generated
  - manual
  - fixed_plus_content

- missing_policy
  - preserve_template
  - placeholder_review
  - generate_empty_unit
  - skip
  - unsupported

- status
  - required
  - template_default
  - manual_only
  - generated

PKU 当前关键判断：

- 图目录：required；默认保留；无条目时保留空白页并评论。
- 表目录：required；默认保留；无条目时保留空白页并评论。
- 附录A 博士期间工作成果：template_default；默认保留模板模块。
- 致谢：template_default；默认保留模板模块。
- 原创性声明和使用授权说明：manual_only；保留固定页，不自动填写签名日期。
- 封面：required/manual；当前阶段不填任何封面字段。
- 结论与讨论：属于 body_main 内固定结尾章；固定的是“第五章 结论与讨论”章标题，章内内容来自学生。

================================================================================
5. 元素处理策略
================================================================================

每个 element 应该至少有这些信息：

- id
- order
- title
- source_policy
- fill_policy
- required/default/optional
- style binding
- position relation
- missing behavior

位置关系必须显式写出：

- 独立成段
- 同一段连续排布
- 行内元素
- 表格内部
- 页眉/页脚区域
- Word 字段生成

示例：

中文关键词标签和内容：
  关键词： 是固定元素
  关键词内容 是学生元素
  两者在同一段连续排布

英文摘要：
  KEY WORDS: 是固定元素
  英文关键词内容 是学生元素
  两者在同一段连续排布

表格：
  中文表名、英文表名、表体、表注不是平级正文段落
  它们共同构成一个 table_block

================================================================================
6. Word section 对齐原则
================================================================================

逻辑层：

- 单元声明页眉显示文字。
- 单元声明使用前置页页码规则还是正文/后置页页码规则。
- 全局规则声明页眉/页脚距离、页码字体字号、页码格式和连续编号。

Word 实现层：

- 页眉、页脚、页码格式、页边距、横竖版最终落在 section 上。
- 单元不是 Word section 的同义词。
- 只有 section 级属性变化时才新开 section。
- 新 section 必须处理 Link to Previous，避免页眉页脚串联。
- 从前置页罗马数字切到正文阿拉伯数字时必须新开 section。
- 正文章节如果页眉显示当前章名，第一版可每章一个 section；后续可评估 STYLEREF 字段减少 section 数。

因此：

审查文档写“单元页眉是什么”，不是说页眉是普通正文内容。
渲染器根据单元页眉和页码规则决定 section。

6.1 高风险非样式约束清单

这些规则和“同页约束”类似：它们不一定表现为某个字体字号，但如果遗漏，最终 Word 会明显不符合学校模板，甚至后续无法更新目录、页码或交付。

1. 固定模板隐藏结构
   - content control、bookmark、field、drawing anchor、签名线、复选框、表单边框、关系文件都可能是模板的一部分。
   - 替换内容时不能只保留可见文字，把这些隐藏结构删掉。
   - 示例：封面表单、声明签名区、授权勾选项、目录字段、页码字段。

2. 生成字段和可见结果的双重身份
   - 目录、图目录、表目录、页码、交叉引用可能同时有 field code 和旧的可见结果。
   - 审查应记录“字段规则”和“显示样式”；合成应保留字段，不能只复制模板里旧的可见文字。
   - 字段更新前后的页码差异应进入报告，不能把过期页码当作固定内容。

3. 单元边界和停止标题
   - 识别一个单元时必须知道它在哪里结束。
   - 参考文献不能吞掉附录、成果目录、致谢；摘要不能吞掉关键词后的目录或正文；目录条目不能被误认为正文标题。
   - 每个单元应记录 start anchors、stop anchors 和允许包含的子元素类型。

4. 直接格式和有效样式
   - 学校模板常常用同一个 Word style，再用 run/paragraph direct formatting 改出真正样式。
   - 提取时不能只看 styleId；应记录可见有效样式，以及 raw style 与 visible formatting 的冲突。
   - 示例：TOC 条目、摘要标题、英文标题、关键词标签。

5. 段内混排和 run 级样式
   - 一个段落里可能有多个元素和多种样式。
   - 关键词标签与关键词内容同段但字体不同；参考文献编号和正文可能样式不同；公式里的变量/函数/单位可能正斜体不同。
   - render_plan 不能只给整段一个段落样式就结束。

6. 空白页、无页眉页码和奇偶页
   - 空白页或无页眉/无页码有时本身就是模板要求。
   - “不显示页码”“不显示页眉”也是可验证规则，不是缺失。
   - 如果学校要求章首页、奇偶页或指定空白页，应作为页面布局约束记录。

7. 浮动对象和锚定关系
   - 图片、文本框、公式对象可能是 inline，也可能是 floating/anchored。
   - 图本体不能因为浮动锚点跑到图题之外；封面徽标或签名线不能因锚点丢失而移位。
   - 合成应记录对象和题注/表单的绑定关系。

8. 编号身份和重置范围
   - 标题编号、图表编号、公式编号、参考文献编号不是普通文本。
   - 需要记录编号是否按章重置、是否自动生成、是否允许保留学生原编号、编号后空格/制表符是什么。
   - 编号规则变化时，应重建编号而不是简单复制旧文本。

9. 新页、分页符和分节符的区别
   - “另起页”不一定等于新建 Word section。
   - 只有页眉/页脚/页码格式/页边距/横竖版等 section 级属性变化时才需要新 section。
   - 需要记录该单元要求的是 page break、section break，还是 paragraph pageBreakBefore。

10. 渲染后的版面预检
   - XML 检查只能证明结构存在，不能证明封面没溢出、签名区没掉页、图题没孤立。
   - 对同页约束、溢出、空白页、页码连续性等，需要渲染后页面级检查或人工 review 标记。

================================================================================
7. 识别与合成的对齐流程
================================================================================

建议流程：

1. 读取学校模板审查合同
   - 得到 template_unit_tree
   - 得到 global_page_rules
   - 得到 section_decision_rules

2. 识别学生 DOCX
   - 提取 CleanContentIR
   - 分类摘要、关键词、正文标题、正文段落、图、表、公式、参考文献、致谢等
   - 将平铺对象归入 student_content_tree

3. 对齐
   - 按 template_unit_tree 顺序遍历
   - 每个 template unit 查找对应 student unit/content
   - 固定内容直接保留
   - 生成内容使用 Word 字段或系统生成
   - 学生内容填入对应 element
   - 缺失内容按 missing_policy 处理

4. 生成 render_plan
   - 单元顺序
   - 元素顺序
   - 样式绑定
   - section 计划
   - 字段生成计划
   - 同页/同组布局约束
   - 占位/评论计划

5. 渲染 DOCX
   - 将 render_plan 线性化为 Word 段落、表格、图片、字段、section
   - 只在必要位置开 section
   - 写入页眉/页码
   - 更新目录/图目录/表目录字段
   - 按同页/同组约束设置与下段同页、段中不分页、表格整体保留、模板块保留或人工调整提示

6. 输出报告
   - rendered
   - preserved
   - generated
   - placeholder
   - manual_only
   - unsupported
   - unconsumed_source

================================================================================
8. 不应该做的事
================================================================================

不要把学校模板提取成一张平铺样式表。

问题：
  样式表知道“PKU表题”是什么，但不知道它属于“表格单元”的第 1/2 个题名元素。

不要把学生文档识别成一串无归属段落。

问题：
  图题、表题、注释、表体会和普通正文混在一起，后续合成只能靠邻近猜测。

不要让渲染器直接从学生对象流边读边写。

问题：
  固定模板模块、默认保留模块、缺失占位、目录字段、section 页眉页码都需要先有全局放置计划。

不要把 Word section 当成单元本身。

问题：
  一个单元可能不需要新 section；多个单元也可能共享 section。section 是 Word 实现细节，不是文档语义结构。

================================================================================
9. 当前代码与目标模型的潜在不一致
================================================================================

这些不是本文件的代码修改，只是后续实现对齐时需要检查的点：

1. 当前标准树代码里 `conclusion_discussion` 可能仍是独立 unit。
   PKU 审查结论是：它应归入 body_main 的固定结尾章。

2. 当前图/表英文题名元素可能仍标为 optional。
   PKU 审查结论是：学校未说明时，按中国论文通用规范默认配置要求保留英文图名/英文表名。

3. 当前 caption list 可能仍是 required=False / missing_policy=skip。
   PKU 审查结论是：图目录、表目录 required，未识别条目也保留空白页并评论。

4. 当前 academic_achievements / acknowledgement 可能仍是 optional/skip。
   PKU 审查结论是：它们是 template_default，默认保留学校模板模块。

5. 当前 table header / table cell text 可能作为 table_block 的平级 element。
   PKU 审查结论是：表头、表内文字属于表体内部元素，不应和表名、表体、表注同一层表达。

6. 当前渲染逻辑如果按线性 object 流直接输出，需要改为先生成 render_plan。

7. 页眉页码不能只按全局一次性设置，也不能每页硬写；应由单元声明驱动 section 计划。

================================================================================
10. 后续验证建议
================================================================================

最小可验证目标：

1. 给 PKU 模板生成 template_unit_tree。
2. 给一个学生样本文档生成 student_content_tree。
3. 输出一份 alignment report：
   - 每个 template unit 是否找到学生内容
   - 固定内容是否保留
   - 生成内容是否生成
   - 缺失内容是否 placeholder_review
   - 未消费的学生内容有哪些
4. 从 alignment report 生成 render_plan。
5. 渲染后检查：
   - 单元顺序正确
   - 元素顺序正确
   - 同页/同组约束没有被分页切散
   - 图/表没有被拆散
   - 图目录/表目录保留
   - 结论与讨论在正文内作为固定结尾章
   - 页眉/页码 section 没有串联

================================================================================
11. 一句话原则
================================================================================

学校模板提取定义“目标结构”。
学生文档识别定义“来源内容”。
合成渲染负责把来源内容按目标结构放进去。

三者都必须以“单元 -> 元素 -> 子元素”的层级模型为中心，Word 的线性段落流只是最后一步的实现形式。
~~~~


## Reviewer Response Template

```text
real-core-v0 source-fact review

Reviewer:
- reviewed_by: <name or role>
- review_source: this acceptance note

Accepted fact groups:
- fixed evidence set: accepted
- school template full facts: accepted / changes requested
- student content full facts: accepted / changes requested
- render-case placement expectations: accepted / changes requested

Required changes:
- <school_id, student_id, case_id, unit, element, or line reference>: <change>

Approval boundary:
- auto_update_allowed must remain false
- runtime human review is not allowed as a pass/fail gate
- AI may diagnose but may not decide final status
```
