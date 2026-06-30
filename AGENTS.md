重要：每个对话只负责处理与本轮任务直接相关的提交。开始做任何会修改文件的工作前，先查看工作区状态；如果工作区已有无关改动，不要为了本轮任务提交、回滚或整理这些改动，只需避开它们。只有本轮任务产生或明确涉及的改动才需要提交。

本仓库的讨论、计划、总结和最终回复默认使用中文；除非用户明确要求其他语言。

阶段优化工作流：讨论或继续优化某个阶段（例如 T1/T2/T3/T4/T5/T6）前，先在 `docs/plans/` 找到或创建对应阶段的 issue 文档，记录上一轮优化后当前仍存在的问题。该文档必须先写清真实运行口径、expected vs observed、疑似根因、上一轮已解决/未解决对照、以及后续验收门禁；随后再围绕这个文档讨论解决方案和实施顺序。

阶段 issue 命名和追踪约定：

- 新建 `docs/plans/` 文档须以 `YYYY-MM-DD-` 日期前缀开头；完整约定见 `docs/plans/README.md`。
- 优先使用 `{YYYY-MM-DD-}template-parse-refactor-{stage}-{topic}-issue-{NN}-{short-name}.md`，例如 `2026-06-29-template-parse-refactor-t3-element-policy-issue-03-inline-residuals.md`。
- 每个阶段 issue frontmatter 必须包含 `issue_id`、`issue_sequence`、`previous_issue`、`previous_optimization`、`next_plan`。没有上一轮时显式写 `none`。
- 阶段 issue 链统一登记在 `docs/plans/template-parse-refactor-issue-index.md`，避免多轮迭代后混淆“上一轮 issue / 上一轮优化文档 / 当前残余 issue”。

模板生成标准裁判目标优先级记忆：讨论或开发 standard-judge / template-generation-judge 时，`stage standard diff diagnosis` 优先于 gate/signoff。首要目标是稳定回答“阶段产物和阶段标准哪里不一致、为什么不一致、该谁修、怎么修且怎么验”，并落成 `mismatches[]`、`root_causes[]`、`owner_assignments[]`、`fix_plan[]` 四层报告。`standard_acceptance_status`、`signoff_status`、`gate_enabled`、`verifier_state` 可以保留，但不能替代上述差异诊断目标；不要把 PASS/SIGNABLE 当成该目标完成的证据。

# AGENTS.md

DocFit v3 是一个讲学生论文转换成学校模板格式的产品

模板生成阶段边界硬约束：T1 `document_facts` 只能读取并输出源 DOCX 的事实，例如文本、OOXML 位置、run、样式、字段、分页/分节、表格、页眉页脚和可见对象 trace。T1 不允许输出语义判断字段或阈值判断字段，例如 `is_toc_entry`、`is_spacing_line`、`looks_like_instruction_text`、`likely_unit_heading`、`large_font`、`short_text`、`unit_id`、`policy`、`confidence`。这些判断必须在 T2/T3/T4 等下游阶段基于 T1 事实计算。
