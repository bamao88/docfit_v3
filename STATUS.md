# DocFit Status

Last updated: 2026-06-16

Current focus:

- `real-core-v0` 已从“证据绑定通过”推进到“业务验收 gate 会阻塞当前坏输出”；
  模板解析切片已经完成，新的临时 e2e 输出会把 template 阶段判为 `PASS`。
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
  并把当前模板说明泄漏、追加写入、内容未定位等业务问题作为阻塞 findings。
- 最新 product-run 输出到 `/tmp/docfit_real_core_coverage`，结果为 `FAIL`：
  该 run 仍读取历史 `reports/real-core-v0/**` 成品和 artifacts，所以 9/9 个 e2e
  case 仍显示 `business.template_acceptance`、`business.content_acceptance`、
  `business.placement_acceptance`、`business.render_acceptance` 都是 `false`。
- 9 个成品的产品审查记录在
  `docs/human/real-core-v0-product-quality-review.md`。当前结论是：
  这些 Word 文件还不能算学校格式转换合格，因为它们仍保留目标模板说明/示例，
  并且大多是在复制模板后把学生内容追加到末尾。
- 四个环节的问题检查已经成为 real-core 验收 gate：
  `tests/contract/test_real_core_four_stage_problem_checks.py` 会用湖南农业大学模板
  和学生 003 源文档跑一次转换，并确认模板解析已经通过，内容抽取、内容放置、
  Word 生成仍能给出具体问题说明；当前坏输出会返回 `FAIL`，不能再因为证据绑定
  存在而通过。
  最新临时 probe `/tmp/docfit_real_core_template_probe` 的结果是
  `template: PASS`、`blocked_at: content`、`business.template_acceptance: true`。
  详细说明见
  `docs/human/real-core-v0-four-stage-problem-checks.md`。
- 学生源文档中的旧目录已经有一个通用修复：`toc 1` / `toc 2` / `toc 3`
  样式段落会被识别为源文档格式内容，内容放置时标为不写入成品，Word 生成记录
  会说明该动作已处理但不会把旧目录文字写进后续新输出。
- 已有通用的基线比较基础：可以验证签收信息、比较输出维度，并合并成
  `PASS` / `FAIL` / `UNKNOWN`。
- Word 页面图像证据清单可以生成和校验；缺少证据时 coverage 会保持
  `UNKNOWN`。即使 Word evidence 存在，缺少可审计业务 artifacts 或业务审计失败，
  coverage 也会保持 `UNKNOWN` 或 `FAIL`。
- `scripts/export_real_core_word_evidence.py --reconcile-existing` 可以校验
  已有页面图像证据，并刷新每个 case 的报告，不需要重新打开 Word。
- AI 诊断包只用于辅助分析，不能改变最终通过或失败状态。

Next action:

- 下一步修内容抽取：识别标题、摘要、关键词、参考文献、致谢，以及旧封面、
  旧目录这类不该进目标正文的源文档格式内容。
- 然后修内容放置：确认每段学生内容进入目标学校模板的具体位置，不能全部放到
  `slot_body_start`。
- 最后修 Word 生成：确认最终文件没有模板说明文字，并且学生内容不是追加到
  整份模板后面。

Known blockers:

- 目前没有需要用户提供的新材料阻塞工程继续。
- 等内容抽取、内容放置和渲染修复后，需要用户或产品 owner review 新生成的
  9 个 Word 成品，判断固定表单、缺失内容占位、北大空白页/版权页/原创性声明页
  等最终成品策略。
