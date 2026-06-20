# DocFit Status

Last updated: 2026-06-20

Current focus:

- `real-core-v0` 已从“证据绑定通过”推进到“业务验收 gate 会阻塞当前坏输出”；
  模板 source-fact 解析已经升级为结构化标准逐项验收，生成模板 Word 差距检查
  现在检查本次 `template-generate` 生成的 `generated_template.docx`，或 CLI
  显式传入的 `generated_template.docx`，不再把学校源模板路径混成被测生成物。
- 新的 `PASS` 语义必须同时满足四层业务验收：模板解析、内容抽取、内容放置、
  Word 生成。只有 source-fact baseline 和 Word 页面图像证据不再足够。
- 接下来重点不是继续准备材料，而是按 gate 暴露的问题修真实工程链路。

Current state:

- `real-core-v0` 已注册三所学校、三份学生文档、九个学校/学生组合。
- `docfit eval template-generate --template ... --out ...` 已经跑完整模板生成阶段：
  它会写出 `source_template_tree.json`、`discovered_template_rules.json`、
  `template_artifact.json`、`template_unit_decisions.json`、
  `template_generation_plan.json`、顶层 `generated_template.docx` 和
  `template_generation_manifest.json`。这证明生成阶段证据链已经存在；
  学校格式质量仍要交给 `template-gap` 和 real-core gate 判定。
  如果传入 `--school <school_id>`，当前开发链路会读取该学校签名标准里的
  `expected.units`，把可填写项和自动生成项对齐到源 Word，并在输出 Word 中写入
  `[[DOCFIT_SLOT:...]]` / `[[DOCFIT_GENERATED:...]]` 标记。
- real-core 的 template/e2e 编排已经接入模板生成阶段：每次 run 会先写出
  `template_generation/generated_template.docx`，再把这份 Word 交给
  `template-gap` 检查，并让后续 render 以它作为底稿。已签入的
  `inputs/simulated-generated-templates/**` 仍保留为显式 `template-gap` fixture，
  但不再是 template/e2e run 的被测生成结果。
- 用户验收所需的真实输入材料、基线和 Word 页面图像证据要求记录在
  `docs/human/real-core-v0-acceptance.md`。
- 用户已 review 的 `docs/human/real-core-v0-review-packet.md` 作为
  `real-core-v0` 的已接受源材料事实。
- 九个 Microsoft Word 页面图像证据包已经绑定到 `reports/real-core-v0/**`。
  这些证据仍然必要，但现在只是 render-format evidence 的一部分，不足以单独
  证明业务正确。
- 历史生成的九个 case 报告文件仍可能记录旧口径的 `PASS`、`blocked_at: null`。
  新的 `docfit eval coverage --profile real-core-v0` 会重新读取这些报告和 artifacts，
  并把当前生成模板差距、模板说明泄漏、追加写入、内容未定位等业务问题作为
  阻塞 findings。
- 最新 product-run 输出到 `/tmp/docfit_real_core_coverage`，结果为 `FAIL`：
  该 run 不再把 source-fact binding 或 Word 页面证据当成模板正确性证明。
  生成模板差距报告已经改为 v2 分层树并包含 `summary.per_unit`；当前阻断来自
  真实模板差距、检查能力不足和历史 `reports/real-core-v0/**` 成品中的模板、
  内容、放置、渲染问题。
- 9 个成品的产品审查记录在
  `docs/human/real-core-v0-product-quality-review.md`。当前结论是：
  历史 Word 文件还不能算学校格式转换合格；新编排已经能清理一批目标模板
  说明/示例文字，但仍主要是在复制生成模板后把学生内容追加到末尾。
- 四个环节的问题检查已经成为 real-core 验收 gate：
  `tests/contract/test_real_core_four_stage_problem_checks.py` 会用湖南农业大学模板
  和学生 003 源文档跑一次转换，并确认生成模板差距、内容抽取、内容放置、
  Word 生成都能给出具体问题说明；当前坏输出会返回 `FAIL`，不能再因为证据绑定
  存在而通过。
  最新临时 probe `/tmp/docfit_real_core_template_probe` 的结果是
  `template: FAIL`、`content: UNKNOWN`、`placement: UNKNOWN`、`render: FAIL`、
  `blocked_at: template`。probe 同时写出
  `artifacts/generated_template.docx`、`generated_template_tree.json` 和
  `template_gap_report.json/.md/.docx`；模板差距报告展示为 `FAIL + UNKNOWN`。
  详细说明见
  `docs/human/real-core-v0-four-stage-problem-checks.md`。
- 三所学校的 `standards/schools/*/v1/template_unit_contract.yaml` 现在包含
  `expected.units`：每个 unit、element、policy、type/fill、content、style、
  position/relationship 都是可执行标准。模板 stage 和 product-quality gate 会把
  `template_artifact.data.units` 与这些结构化标准逐项比对；例如元素样式不一致会
  报 `template_element_style_mismatch`，并指出 `cover.e_001.style` 这类具体路径。
- real-core 模板合同现在还要求生成模板差距检查：`docfit eval template-gap`
  明确接收 `--generated-template`，把被测 Word 复制为 `generated_template.docx`，
  从 OOXML 解析 `generated_template_tree.json`，再输出三种
  `template_gap_report`。JSON 报告现在以 `input`、`units`、
  `unmodeled_objects` 和 `summary.per_unit` 为主结构，不再公开平铺
  `check_items`。
  字段和 Word 自动编号现在也有显式检查：Word complex field / fldSimple 会合并成
  完整指令并绑定到单元范围；如果单元不能可靠定位，下级字段、编号和元素会保持
  `UNKNOWN`，不会靠全文搜索冒充 PASS。缺 Word 生成字段会报
  `template_generation_field_missing`，字段在错误单元会报
  `template_generation_field_out_of_unit`。自动编号会解析 `word/numbering.xml`、
  样式 `numPr`、段落直接 `numPr` 和段落样式引用；北大正文标题这类要求可以报
  `template_generation_numbering_match`，缺失或格式不一致会报
  `template_generation_numbering_missing` / `template_generation_numbering_mismatch`。
  北大图名、表名和公式编号这类题注/公式序号也能按 `SEQ 图`、`SEQ 表`、
  `SEQ 公式` 字段绑定到具体标准条目。等价生成机制、脚注编号和更细题注规则
  仍需要后续检查。
  样式检查现在会读取 OOXML 字体、字号、加粗、对齐和行距，并合并
  `word/styles.xml` 段落样式继承链；能确定不一致时会报
  `template_generation_style_mismatch`，样式表或单元绑定证据仍不足时保持
  `UNKNOWN`。
  页眉页脚检查现在会解析 `document.xml.rels` 和 section 的 header/footer 引用，
  并按单元位置检查对应 section；确定冲突时会报页眉或页码规则 mismatch。
  分页检查现在会绑定单元位置和 OOXML page break / section；缺少应有分页或
  分节证据时会报 `template_generation_page_rule_mismatch`。同页约束会检查
  `keepNext` / `keepLines`、表格真实段落范围和表格行 `cantSplit`；南农封面这类
  固定表格可以报 `template_generation_page_rule_match`。页面溢出和签名区掉页
  仍需要 Word evidence 或更细页面级检查。
  生成模板 gap 的区域定位也已收敛一层：页眉页脚不再参与正文单元定位；首单元从
  正文第一个可见块开始；显式 DocFit 标记可以作为元素存在证据；合并表格单元格
  继承所在行坐标；单元顺序错误会作为单独 FAIL 报告，而不会级联成大量元素误报。
  生成器现在还会在签名标准要求单元标题、但源 Word 只有短标题时，合成缺失的
  可见标题文本；湖南 probe 中已合成 5 个这类标题。
  生成器现在会按签名标准为需要另起页的单元写入 `pageBreakBefore`，并为需要
  分节隔离的单元写入 `nextPage` section break；manifest 会记录 `page_breaks`
  和 `section_breaks`。生成模板解析器也会记录顶层段落对应的 XML 段落位置，
  分页检查优先使用已定位的单元锚点，并允许单元标题前少量空行/占位段落内的
  page/section 边界作为证据。
  最新三校 probe 写在 `/tmp/docfit_stage_realcore_audit31`，仍全部为 `FAIL`：
  湖南农业大学 PASS/FAIL/UNKNOWN 为 `161/6/127`，南农为 `94/20/92`，
  北大为 `109/13/32`。本轮主要修了源锚点和检查定位：南农正文不再跳到
  “第X章 结论与展望”，北大图目录/表目录/正文/参考文献/致谢能定位到实际标题或
  正文开头，正文中的图表公式字段和编号规则也能归到正文单元。北大源模板没有真实目录
  标题时，生成器会在图目录前合成可见“目录”标题并设置分页，不再误把图目录或表目录
  当目录。主要阻断仍集中在样式、页眉页脚、页码、未建模可见对象，以及页面/样式/
  生成机制类要求的证据不足。
- 学生源文档中的旧目录已经有一个通用修复：`toc 1` / `toc 2` / `toc 3`
  样式段落会被识别为源文档格式内容，内容放置时标为不写入成品，Word 生成记录
  会说明该动作已处理但不会把旧目录文字写进后续新输出。
- 学生正文中的常见编号标题已经有通用语义候选：例如 `3 PGP6...` 会标为
  `arabic_numbered_heading`，`5.1本研究...` 会标为
  `arabic_dotted_numbered_heading`，后续报告不再把这类正文标题当作完全未识别。
- 已有通用的基线比较基础：可以验证签收信息、比较输出维度，并合并成
  `PASS` / `FAIL` / `UNKNOWN`。
- Word 页面图像证据清单可以生成和校验；缺少证据时 coverage 会保持
  `UNKNOWN`。即使 Word evidence 存在，缺少可审计业务 artifacts 或业务审计失败，
  coverage 也会保持 `UNKNOWN` 或 `FAIL`。
- `scripts/export_real_core_word_evidence.py --reconcile-existing` 可以校验
  已有页面图像证据，并刷新每个 case 的报告，不需要重新打开 Word。
- AI 诊断包只用于辅助分析，不能改变最终通过或失败状态。

Next action:

- 下一步先把 `template-generate` 产物推进到真实模板生成质量：按签名标准顺序重组
  可填写模板，保留固定表单和真实可见固定内容，补齐等价生成机制、复杂
  样式/section/页码规则和页面级版面证据，直到模板差距报告不再阻断。
- 然后继续修内容抽取：识别摘要、关键词、参考文献、附录、致谢这类章节角色，
  以及旧封面、旧目录这类不该进目标正文的源文档格式内容。
- 再修内容放置：确认每段学生内容进入目标学校模板的具体位置，不能全部放到
  `slot_body_start`。
- 最后修 Word 生成：确认最终文件没有模板说明文字，并且学生内容不是追加到
  生成模板后面。

Known blockers:

- 目前没有需要用户提供的新材料阻塞工程继续。
- 等内容抽取、内容放置和渲染修复后，需要用户或产品 owner review 新生成的
  9 个 Word 成品，判断固定表单、缺失内容占位、北大空白页/版权页/原创性声明页
  等最终成品策略。
