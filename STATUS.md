# DocFit Status

Last updated: 2026-06-16

Current focus:

- `real-core-v0` 已从“证据绑定通过”推进到“业务验收 gate 会阻塞当前坏输出”；
  模板 source-fact 解析已经升级为结构化标准逐项验收，但新的生成模板 Word
  差距检查会把当前 template 阶段判为 `FAIL`，因为它能确定性指出
  `generated_template.docx` 和学校模板标准之间的差距。
- 新的 `PASS` 语义必须同时满足四层业务验收：模板解析、内容抽取、内容放置、
  Word 生成。只有 source-fact baseline 和 Word 页面图像证据不再足够。
- 接下来重点不是继续准备材料，而是按 gate 暴露的问题修真实工程链路。

Current state:

- `real-core-v0` 已注册三所学校、三份学生文档、九个学校/学生组合。
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
  当前缺少 checked-in 的模板差距证据，并且历史 `reports/real-core-v0/**`
  成品仍显示模板、内容、放置、渲染问题。
- 9 个成品的产品审查记录在
  `docs/human/real-core-v0-product-quality-review.md`。当前结论是：
  这些 Word 文件还不能算学校格式转换合格，因为它们仍保留目标模板说明/示例，
  并且大多是在复制模板后把学生内容追加到末尾。
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
  `template_gap_report`。报告保留 `known_status`、`display_status`、
  `passed_count`、`failed_count`、`unknown_count` 和 `blocking_status`。
  字段和编号现在也有显式检查：Word complex field / fldSimple 会合并成完整
  指令并绑定到单元范围；缺 Word 生成字段会报
  `template_generation_field_missing`，字段在错误单元会报
  `template_generation_field_out_of_unit`，编号规则未绑定到单元/元素会报
  `template_generation_numbering_unverified`。
  样式检查现在会读取 OOXML 字体、字号、加粗、对齐和行距，并合并
  `word/styles.xml` 段落样式继承链；能确定不一致时会报
  `template_generation_style_mismatch`，样式表或单元绑定证据仍不足时保持
  `UNKNOWN`。
  分页检查现在会绑定单元位置和 OOXML page break / section；缺少应有分页或
  分节证据时会报 `template_generation_page_rule_mismatch`。
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

- 下一步先修生成模板差距报告暴露的 template 阶段问题：补齐生成模板实际输出、
  样式/分页/页眉页脚/字段解析，或修模板生成逻辑，直到模板差距报告不再阻断。
- 然后继续修内容抽取：识别摘要、关键词、参考文献、附录、致谢这类章节角色，
  以及旧封面、旧目录这类不该进目标正文的源文档格式内容。
- 再修内容放置：确认每段学生内容进入目标学校模板的具体位置，不能全部放到
  `slot_body_start`。
- 最后修 Word 生成：确认最终文件没有模板说明文字，并且学生内容不是追加到
  整份模板后面。

Known blockers:

- 目前没有需要用户提供的新材料阻塞工程继续。
- 等内容抽取、内容放置和渲染修复后，需要用户或产品 owner review 新生成的
  9 个 Word 成品，判断固定表单、缺失内容占位、北大空白页/版权页/原创性声明页
  等最终成品策略。
