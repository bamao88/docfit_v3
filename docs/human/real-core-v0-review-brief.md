# real-core-v0 人工 review 简明说明

Last updated: 2026-06-16

你已经确认 `real-core-v0` 的固定证据集就是 3 所学校、3 份学生文档、9 个
学校 x 学生组合。源事实已经写入 runnable baseline，Word image evidence 也已经
绑定。当前需要继续推进的不是补材料，而是让确定性业务 gate 挡住的问题逐项消失：

1. 学校模板是否真的解析成目标单元、元素、子元素和输出策略；
2. 学生内容是否真的抽取成可放置的内容树；
3. 9 个组合的放置计划是否给每个内容节点明确去向；
4. 最终 Word 是否真的没有模板说明泄漏、没有 append-only 写入，并且有 Word evidence。

完整审阅包已经整理在：

```text
docs/human/real-core-v0-review-packet.md
```

注意：这个完整包不是过程稿。它嵌入了三份学校模板 review 源文和三份
学生内容 review 源文，保留单元内元素、元素顺序、元素关系、处理策略、
样式、页眉页码和同页/分页约束。本文只是入口说明，不能替代完整包。

## 如果继续审标准，怎么审

请以完整包里的源事实为准。重点找这些问题：

- 某个学校单元是否多了、少了、顺序错了；
- 某个固定页/声明/表单是否不该保留，或应该自动填但现在标成不填；
- 某个学生标题、摘要、关键词、图表、参考文献、附录、致谢是否识别错了；
- 某个学生文档的 donor-school 前置页是否应该忽略但没有忽略；
- 某个学校 x 学生组合里，附录、致谢、成果目录、图目录、表目录的默认保留策略是否不对。

## 现在不需要你补什么

- 不需要新增学校模板审查文档或学生内容审查文档。
- 不需要审 `test_outputs/workbench/real-core-v0-baseline-review/drafts/**/*.yaml`；当前 gate 使用
  已签入的 `standards/**` 和 `test_outputs/debug/template_eval_runs/real-core-v0/**`。
- 不需要把当前 9 个旧 Word 输出当成合格成品审；它们已经被业务 gate 判为不合格。
- 不需要决定 PASS/FAIL，AI 和人工都不能作为 runtime gate。
- 不需要自动更新 golden 或 signed standard。

## 你可以直接回复的格式

```text
real-core-v0 source-fact review

Reviewer:
- reviewed_by: <你的名字或角色>
- review_source: this acceptance note

Accepted fact groups:
- fixed evidence set: accepted
- school template facts: accepted / changes requested
- student content facts: accepted / changes requested
- 9 render-case placement expectations: accepted / changes requested

Required changes:
- <学校、学生、case_id 或章节>: <需要改什么>

Approval boundary:
- auto_update_allowed must remain false
- runtime human review is not allowed as a pass/fail gate
- AI may diagnose but may not decide final status
```

当前这版 source facts 已经写成 runnable `standards/**` baseline。下一步阻塞是工程
实现：先修模板解析，再修内容抽取、放置和 Word 渲染。修完并重新生成 9 个
`final.docx` 后，才需要重新导出 Word image evidence 并再次验收。
