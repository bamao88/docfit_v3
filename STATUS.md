# DocFit Status

Last updated: 2026-06-16

Current focus:

- `real-core-v0` 的固定证据闭环已经跑通，接下来重点转向 9 个 Word 成品的
  产品质量：版式是否像目标学校论文，内容是否进了正确位置。
- 当前 `PASS` 只表示证据齐了、Word 能打开并能导出页面图像；它不表示成品
  已经达到学校提交质量。
- 现在最重要的是让测试能分别指出四个环节的问题：模板解析、内容抽取、
  内容放置、Word 生成。每个问题都必须说明“期望是什么、实际是什么、证据在哪里”。

Current state:

- `real-core-v0` 已注册三所学校、三份学生文档、九个学校/学生组合。
- 用户验收所需的真实输入材料、基线和 Word 页面图像证据要求记录在
  `docs/human/real-core-v0-acceptance.md`。
- 用户已 review 的 `docs/human/real-core-v0-review-packet.md` 作为
  `real-core-v0` 的已接受源材料事实。
- `docfit eval coverage --profile real-core-v0` 在本机返回 `PASS`，九个
  Microsoft Word 页面图像证据包已经绑定到 `reports/real-core-v0/**`。
- 九个 case 的报告都已经生成 `final.docx`，并且记录为 `PASS`、
  `blocked_at: null`、没有阻塞问题、`render.word_image_evidence: true`。
- 9 个成品的产品审查记录在
  `docs/human/real-core-v0-product-quality-review.md`。当前结论是：
  这些 Word 文件还不能算学校格式转换合格，因为它们仍保留目标模板说明/示例，
  并且大多是在复制模板后把学生内容追加到末尾。
- 四个环节的问题检查已经能运行：
  `tests/contract/test_real_core_four_stage_problem_checks.py` 会用湖南农业大学模板
  和学生 003 源文档跑一次转换，并确认模板解析、内容抽取、内容放置、Word 生成
  都能给出具体问题说明。详细说明见
  `docs/human/real-core-v0-four-stage-problem-checks.md`。
- 学生源文档中的旧目录已经有一个通用修复：`toc 1` / `toc 2` / `toc 3`
  样式段落会被识别为源文档格式内容，内容放置时标为不写入成品，Word 生成记录
  会说明该动作已处理但不会把旧目录文字写进后续新输出。
- 已有通用的基线比较基础：可以验证签收信息、比较输出维度，并合并成
  `PASS` / `FAIL` / `UNKNOWN`。
- Word 页面图像证据清单可以生成和校验；缺少证据时 coverage 会保持
  `UNKNOWN`。
- `scripts/export_real_core_word_evidence.py --reconcile-existing` 可以校验
  已有页面图像证据，并刷新每个 case 的报告，不需要重新打开 Word。
- AI 诊断包只用于辅助分析，不能改变最终通过或失败状态。

Next action:

- 先修模板解析的检查：真实学校模板不能只解析出 `slot_body_start`；解析结果必须
  说清楚封面、声明、目录、题名、摘要、正文、参考文献、附录/致谢、手工表单等
  目标位置；模板说明和示例文字必须说明能不能进成品。
- 然后按顺序补内容抽取、内容放置、Word 生成的正式检查：
  - 内容抽取要识别标题、摘要、关键词、参考文献、致谢，以及旧封面、旧目录这类
    不该进目标正文的源文档格式内容。
  - 内容放置要确认每段学生内容进入目标学校模板的具体位置，不能全部放到
    `slot_body_start`。
  - Word 生成要确认最终文件没有模板说明文字，并且学生内容不是追加到整份模板后面。

Known blockers:

- 目前没有需要用户提供的新材料阻塞工程继续。
- 等 P0 修复后，需要用户或产品 owner review 新生成的 9 个 Word 成品，判断
  固定表单、缺失内容占位、北大空白页/版权页/原创性声明页等最终成品策略。
