# real-core-v0 Product Quality Review

日期：2026-06-16

## 结论

`real-core-v0` 的 9 个 `final.docx` 都已经通过 deterministic evidence gate：
报告为 `PASS`，并且都有 Microsoft Word 导出的页面图像证据。

但从产品验收视角看，当前 9 个成品不能视为学校格式转换质量合格。当前
PASS 只证明 source-fact baseline、render manifest、Word 打开/分页图像证据
闭环成立；它不证明版式和语义已经达到可交付论文成品质量。

## 审查范围

审查对象：

- `reports/real-core-v0/<case_id>/final.docx`
- `reports/real-core-v0/<case_id>/evidence/page-*.png`
- 对应 `summary.json`、`placement_plan.json`、`render_manifest.json`
  和 `student_content_artifact.json`

9 个 case 覆盖：

| 学校 | 学生 001 | 学生 002 | 学生 003 |
| --- | ---: | ---: | ---: |
| 湖南农业大学 | 40 页 | 36 页 | 25 页 |
| 南京农业大学本科 | 31 页 | 27 页 | 18 页 |
| 北京大学研究生 | 76 页 | 67 页 | 46 页 |

## 主要产品问题

### P0：目标模板说明/示例内容泄漏到成品

当前 renderer 复制目标学校模板后追加学生内容，没有清理源模板中的说明、示例
和占位内容。

观察到的典型表现：

- 湖南农业输出前几页保留了“附件1 封面基本格式”“（一号华文行楷空一行）”
  “毕业论文（设计）中文题目”等格式说明和示例占位。
- 南京农业输出保留了红/蓝色模板说明页，例如“论文题目（三号黑体）”
  “摘要（四号黑体）”等示范文字。
- 北京大学输出保留了模板说明文本、示例标题和模板项目说明，例如
  “研究生院网站上的毕业论文模板功能有严重欠缺”等非学生论文内容。

影响：成品看起来像“模板说明 + 学生内容附件”，不是目标学校论文成品。

### P0：学生内容被追加到文档尾部，而不是填入目标学校单元流

当前 9 个 case 的 placement action 基本都指向虚拟 `slot_body_start`，render
阶段使用 `doc.add_paragraph()` / `doc.add_table()` 追加内容。结果是学生正文、
参考文献、附录、致谢等没有进入目标学校要求的单元顺序。

观察到的典型表现：

- 湖南农业 case 中，学生正文内容出现在后置固定表单之后。
- 南京农业 case 中，前部仍是目标模板示例/说明页，学生内容从后部才开始出现。
- 北京大学 case 中，模板示例页占据大量篇幅，学生参考文献和致谢集中在尾部。

影响：目录、摘要、正文、参考文献、致谢、附录和固定表单的目标顺序不成立。

### P0：封面、题名、摘要、关键词等填充语义未落地

当前输出没有把学生题名、英文题名、作者/导师信息、中文摘要、英文摘要、
关键词等填到目标学校对应位置。封面和摘要页多处仍保留模板占位或示例文本。

影响：即使全部学生可见内容没有 silent drop，最终文档也不满足“转换成目标学校
论文格式”的核心用户预期。

### P1：旧目录和 donor/source-format 内容处置不足

学生 001 的源文档包含旧目录。产品语义要求旧目录应作为源格式噪音处理，由目标
学校流程重新生成目录。当前已生成的 9 个成品仍可能包含旧目录/源格式内容。

本轮已完成的通用开发修复：

- content extract 将 `toc 1` / `toc 2` / `toc 3` 样式段落识别为
  `source_format`，保留在 visible content ledger。
- placement 对这类内容生成 `discard_as_source_format` disposition，而不是
  当作正文放置。
- render manifest 记录该 action 已执行，但不把旧目录文本写入输出 DOCX。

注意：这个修复影响后续重新生成的输出。当前 `reports/real-core-v0/**` 下的
已导出 Word image evidence 仍绑定旧 `final.docx`，未在本轮自动替换。

### P1：正文标题层级和目录重建基础仍弱

真实学生文档中大量标题使用普通样式、字号、编号和对齐表达，而不是 Word
内置 Heading 样式。当前抽取阶段仍有大量标题被归类为普通 paragraph。

影响：

- 目标学校目录无法可靠重建。
- 正文章节样式无法稳定套用。
- 图表、参考文献、附录、致谢等区域边界仍主要依赖粗粒度顺序，而不是明确语义树。

### P1：图、表、题注关系没有成为 render 质量门禁

虽然图片和表格已经进入 ledger 并能被渲染，但当前产品验收还没有确定性检查：

- 图题/表题是否与对象保持相邻关系；
- 图表编号是否符合目标学校规则；
- 跨页表格、宽表和大图是否排版合理；
- 中英文题注缺失时的处置是否符合 signed policy。

## 已完成开发切片

本轮完成了一个通用 source-format 处置修复：

```text
source TOC style -> visible ledger source_format
source_format -> placement discard_as_source_format
discard_as_source_format -> render manifest executed, no visible DOCX write
```

验证：

```bash
uv run pytest tests/contract/test_contract_gates.py::test_source_toc_entry_is_discarded_as_source_format -q
uv run pytest -q
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage_product_qa
```

结果：

- focused source-format regression：PASS
- full test suite：46 passed
- real-core-v0 coverage：PASS

## 下一步开发任务

### P0：把 renderer 从 append-only 改成 unit/slot-based render

目标：

- 不再复制整份模板后追加学生内容。
- 按 signed template unit tree 保留固定/手工单元。
- 清理模板说明、示例、占位正文。
- 在目标学校的题名、摘要、正文、参考文献、致谢、附录等单元中写入对应学生内容。

验收：

- render manifest 能证明每个 content node 写入目标 unit/sub-element，或被明确
  `discard_as_source_format` / `manual_only` / `ask_user`。
- 产品质量 snapshot 能证明不存在模板说明泄漏和 append-only insertion。

### P0：把 placement plan 从单一虚拟 body slot 升级为目标单元映射

目标：

- placement action 不再全部指向 `slot_body_start`。
- 每个学生内容节点映射到目标学校 unit/sub-element。
- donor front matter、旧目录、源模板说明进入 source-format discard，而不是正文。

验收：

- render plan baseline 不只比较 source fact hash，还能比较 content-node disposition。
- no silent drop 继续通过。

### P1：增强真实论文语义抽取

目标：

- 识别标题编号、居中标题、摘要/关键词、参考文献、附录、致谢等区域。
- 区分正文标题、旧目录条目、封面元数据、摘要标签和普通段落。
- 对普通样式但有编号结构的标题生成 heading candidates。

验收：

- 三份真实学生文档的 semantic tree 与人工 content review 对齐。
- 旧目录不会进入正文 render。

### P1：增加产品质量 snapshot/verifier

目标：

- 在 render output 中结构化记录：
  - template instruction leakage markers；
  - unfilled placeholder markers；
  - first student content position；
  - discarded source-format action count；
  - image/table/caption adjacency；
  - blank/near-blank page candidates。
- 该 verifier 初期可以作为产品 QA 报告，不直接改写已签收 baseline。

验收：

- 当前 9 个旧成品应被产品质量报告明确标为 `not product-accepted`。
- 后续修复后的输出能逐项消除这些 finding。

### P2：重新生成 9 个成品和 Word evidence

触发条件：

- P0/P1 renderer 和 placement 修复完成。

要求：

- 重新生成 `reports/real-core-v0/<case_id>/final.docx`。
- 重新导出 Word page images 和 `word_image_evidence.json`。
- 重新运行 coverage。
- 再做一轮产品视觉/语义 review。

## 需要用户判断的点

当前没有新的外部材料阻塞工程继续。

后续在 P0 renderer 修复完成后，需要用户或产品 owner review 新一轮 9 个 Word
成品是否达到产品验收线，尤其是：

- 各学校固定/手工表单是否应该完整保留；
- 缺学生内容的默认模块应该保留占位、评论，还是省略；
- 北大模板中的空白页/版权页/原创性声明页哪些属于必须保留的最终成品页。

