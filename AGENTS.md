重要：开始做任何会修改文件的工作前，如果工作区已经有改动，先提交一个 commit，再继续新的改动。

本仓库的讨论、计划、总结和最终回复默认使用中文；除非用户明确要求其他语言。

阶段优化工作流：讨论或继续优化某个阶段（例如 T1/T2/T3/T4/T5/T6）前，先在 `docs/plans/` 找到或创建对应阶段的 issue 文档，记录上一轮优化后当前仍存在的问题。该文档必须先写清真实运行口径、expected vs observed、疑似根因、上一轮已解决/未解决对照、以及后续验收门禁；随后再围绕这个文档讨论解决方案和实施顺序。

# AGENTS.md

DocFit v3 是一个讲学生论文转换成学校模板格式的产品

模板生成阶段边界硬约束：T1 `document_facts` 只能读取并输出源 DOCX 的事实，例如文本、OOXML 位置、run、样式、字段、分页/分节、表格、页眉页脚和可见对象 trace。T1 不允许输出语义判断字段或阈值判断字段，例如 `is_toc_entry`、`is_spacing_line`、`looks_like_instruction_text`、`likely_unit_heading`、`large_font`、`short_text`、`unit_id`、`policy`、`confidence`。这些判断必须在 T2/T3/T4 等下游阶段基于 T1 事实计算。
