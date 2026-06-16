# real-core-v0 四阶段测试暴露能力

日期：2026-06-16

## 结论

当前最重要的测试目标不是让 9 个 Word 成品继续保持 deterministic `PASS`，
而是确认测试能不能把当前代码生成内容的问题按四个阶段暴露出来，并且每个
问题都有具体说明。

本轮新增了一个产品质量审计测试面：

```text
src/docfit/harness/product_quality.py
tests/contract/test_real_core_product_quality_exposure.py
```

它不会改变现有 deterministic gate，也不会自动更新 signed baselines。它读取
一次真实 real-core e2e 输出的四阶段 artifact 和 `final.docx`，生成专门用于
产品质量验收的 finding。

验证命令：

```bash
uv run pytest tests/contract/test_real_core_product_quality_exposure.py -q
```

当前结果：测试通过，并证明四个阶段的问题都能被暴露。

## 为什么需要这层测试

`real-core-v0` 当前 coverage `PASS` 证明的是：

- source-fact baseline 已签收；
- placement/render manifest 覆盖已验证；
- Word 能打开并导出页面图像；
- AI 不参与最终判定。

它没有证明：

- 模板说明/示例文本没有进成品；
- 学生内容被写入正确目标学校单元；
- 摘要、关键词、正文标题、参考文献、致谢等语义被正确识别；
- renderer 不是复制整模板后 append-only 追加内容。

因此产品质量测试必须以“四阶段各自暴露问题”为目标，而不是只看最终 DOCX
是否存在。

## 当前四阶段暴露矩阵

测试 case：

```text
school = hunannongye
student = inputs/real-student-003-source.docx
out = /tmp/real_core_product_quality_case
```

选择这个 case 是因为它能同时暴露模板说明泄漏、donor/front-matter 识别、
正文标题语义、单槽 placement 和 append-only render。

### Stage 1：Template Parse

暴露问题 1：

```text
type = template_unit_tree_missing
stage = template
status = UNKNOWN
```

具体说明：

- 期望：模板 artifact 应拆出 cover、声明、目录、题名、摘要、正文、参考文献、
  附录/致谢、manual-only 表单等目标学校单元，并区分 fixed、fillable、
  generated、manual-only、source-format note。
- 实际：湖南农业模板 artifact 有 145 个非空模板段落，但只有 1 个
  `slot_body_start`，没有 protected zone，也没有 required field。
- 证据：first paragraph 是 `附件1 封面基本格式...`，说明 parser 只把说明文字
  放进段落 inventory，没有形成可执行的 unit tree。

暴露问题 2：

```text
type = template_instruction_paragraph_unclassified
stage = template
status = UNKNOWN
```

具体说明：

- 期望：模板说明/示例段落要被标为 non-output template note、固定证据或可剥离
  说明，不能作为最终可渲染内容混入输出。
- 实际：`p[1]: 附件1 封面基本格式...`、`p[2]: （一号华文行楷空一行）`、
  `p[5]: （一号黑体空一行）` 仍只是普通 template paragraph。

Stage 1 测试结论：现在能够具体暴露“模板解析没有建 unit tree，也没有给模板
说明文字 non-output policy”的问题。

### Stage 2：Content Extract

暴露问题 1：

```text
type = content_heading_semantics_unclassified
stage = content
status = UNKNOWN
```

具体说明：

- 期望：正文标题、摘要、关键词、参考文献、致谢、附录等应作为 semantic
  candidate 输出，至少带 content_id、level/region 候选和 evidence。
- 实际：这些章节标题仍是普通 paragraph。例如：
  - `c_029: 1 前言`
  - `c_030: 1.1 研究背景与意义`
  - `c_032: 1.2 国内外研究进展`
  - `c_033: 1.2.1 磷肥应用现状`
  - `c_035: 1.2.2 磷肥施用对产量性状的影响`
- 证据中包含 style、alignment、font_size，便于定位为什么当前 heuristic 没识别。

暴露问题 2：

```text
type = content_donor_front_matter_not_disposed
stage = content
status = UNKNOWN
```

具体说明：

- 期望：学生源文档中的 donor-school 封面和源模板前置页应标为 `source_format`
  或按人工 review policy 忽略。
- 实际：这些前置页仍作为学生内容进入 ledger。例如：
  - `c_001: 湖 南 农 业 大 学`
  - `c_002: 全日制普通本科生毕业论文`
  - `c_005: 学生姓名：袁一文`
  - `c_006: 学    号：202240490218`
  - `c_007: 年级专业及班级：2022级种子（2）班`

Stage 2 测试结论：现在能够具体暴露“内容抽取没有把源格式/前置页和正文语义
区分开”的问题。

### Stage 3：Placement

暴露问题：

```text
type = placement_actions_collapsed_to_virtual_body_slot
stage = placement
status = UNKNOWN
```

具体说明：

- 期望：每个内容节点应映射到目标学校的具体 unit/sub-element，比如 title
  block、abstract、body heading、reference entry、appendix、acknowledgement。
- 实际：`124/124` 个 `place` action 全部指向 `slot_body_start`。
- 具体例子：
  - `a_001 ['c_001'] -> slot_body_start text=湖 南 农 业 大 学`
  - `a_002 ['c_002'] -> slot_body_start text=全日制普通本科生毕业论文`
  - `a_003 ['c_003'] -> slot_body_start text=磷肥不同施肥量对米粉稻产量性状的影响研究`
  - `a_005 ['c_005'] -> slot_body_start text=学生姓名：袁一文`

Stage 3 测试结论：现在能够具体暴露“placement 不是目标学校单元映射，而是
单一虚拟 body slot 塌缩”的问题。

### Stage 4：Render

暴露问题 1：

```text
type = render_template_instruction_text_leaked
stage = render
status = FAIL
```

具体说明：

- 期望：最终 DOCX 只包含固定学校内容、生成字段和已接受的学生内容；模板说明
  和示例文字不能出现在成品里。
- 实际：最终 DOCX 仍包含：
  - `docx paragraph 1: 附件1 封面基本格式...`
  - `docx paragraph 2: （一号华文行楷空一行）`
  - `docx paragraph 5: （一号黑体空一行）`

暴露问题 2：

```text
type = render_append_only_insertion
stage = render
status = FAIL
```

具体说明：

- 期望：第一个写入学生内容的 placement action 应进入目标 unit/slot，而不是
  复制完整模板正文后追加。
- 实际：第一个写入 action 的 OOXML ref 是 `word/document.xml:p[230]`；
  template artifact 只有 145 个非空模板段落，最终输出第一个非空段落仍是
  `附件1 封面基本格式...`。

Stage 4 测试结论：现在能够具体暴露“renderer 复制模板说明并 append-only 写入
学生内容”的问题。

## 当前边界

这层产品质量审计现在是 contract/regression 测试面，不是 `docfit eval e2e`
的最终 pass/fail gate。原因是：

- real-core deterministic gate 仍负责签收事实、hash、manifest、Word evidence；
- 产品质量 finding 需要逐步转成 signed contract / verifier / expected
  dimension，不能绕过 review 自动改变现有 PASS；
- 当前目标是先让测试能稳定暴露问题，再决定哪些 finding 升级成 blocking gate。

## 下一步

建议下一步按这个顺序推进：

1. 把 `template_unit_tree_missing` 转成 Stage 1 的真实 contract/verifier：
   模板必须输出 unit tree 和 non-output instruction policy。
2. 把 `content_heading_semantics_unclassified` 和
   `content_donor_front_matter_not_disposed` 转成 Stage 2 的 content semantic
   contract。
3. 把 `placement_actions_collapsed_to_virtual_body_slot` 转成 Stage 3 的
   target-unit disposition verifier。
4. 把 `render_template_instruction_text_leaked` 和
   `render_append_only_insertion` 转成 Stage 4 的 product-quality render
   verifier。

这四步完成后，四阶段测试就不只是“能描述当前问题”，而是能在 eval gate 中
阻断同类错误。
