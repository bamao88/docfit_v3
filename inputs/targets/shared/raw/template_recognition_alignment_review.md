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
