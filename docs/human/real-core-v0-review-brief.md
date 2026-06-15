# real-core-v0 人工 review 简明说明

Last updated: 2026-06-15

你已经确认 `real-core-v0` 的固定证据集就是 3 所学校、3 份学生文档、9 个
学校 x 学生组合。现在需要 review 的不是空 YAML，也不是转换效果，而是：

1. 学校模板事实是否正确；
2. 学生内容事实是否正确；
3. 9 个组合的放置策略是否符合预期。

完整审阅包已经整理在：

```text
docs/human/real-core-v0-review-packet.md
```

注意：这个完整包不是过程稿。它嵌入了三份学校模板 review 源文和三份
学生内容 review 源文，保留单元内元素、元素顺序、元素关系、处理策略、
样式、页眉页码和同页/分页约束。本文只是入口说明，不能替代完整包。

## 你这次怎么审

请以完整包里的源事实为准。重点找这些问题：

- 某个学校单元是否多了、少了、顺序错了；
- 某个固定页/声明/表单是否不该保留，或应该自动填但现在标成不填；
- 某个学生标题、摘要、关键词、图表、参考文献、附录、致谢是否识别错了；
- 某个学生文档的 donor-school 前置页是否应该忽略但没有忽略；
- 某个学校 x 学生组合里，附录、致谢、成果目录、图目录、表目录的默认保留策略是否不对。

## 这次不需要你审什么

- 不需要审 `out/real-core-v0-baseline-review/drafts/**/*.yaml`，那些仍是空骨架；
  需要审的是完整包里嵌入的 school review / student review 源事实。
- 不需要审 Word 输出是否好看，9 个 Word image evidence package 还没生成。
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

当前这版 source facts 已经写成 runnable `standards/**` baseline。下一步
阻塞只剩 9 个 Word image evidence package。
