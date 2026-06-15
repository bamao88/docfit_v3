# real-core-v0 下一步开发材料责任分工

日期：2026-06-15

## 结论

目前不需要用户再准备新的外部材料。

下一步推进 `real-core-v0` 的阻塞不是“缺学校/学生/人工审查材料”，而是工程实现还没有把已审材料转成 9 个真实可验收的渲染输出：

```text
reports/real-core-v0/<case_id>/final.docx
```

这些 `final.docx` 必须由 DocFit real-core 渲染链路产生，之后才能运行 Word evidence exporter 生成：

```text
reports/real-core-v0/<case_id>/evidence/word_image_evidence.json
reports/real-core-v0/<case_id>/evidence/page-*.png
```

## 用户已准备完成

| 材料 | 路径/状态 | 当前状态 |
| --- | --- | --- |
| 3 所学校模板源文件 | `inputs/school-*.docx` | 已存在 |
| 3 所学校模板人工审查源 | `inputs/school-*-template-review.txt` | 已存在 |
| 3 份学生源 DOCX | `inputs/real-student-*-source.docx` | 已存在 |
| 3 份学生内容人工审查源 | `inputs/real-student-*-content-review.md` | 已存在 |
| 共享模板识别/对齐审查 | `inputs/shared-template-recognition-alignment-review.txt` | 已存在 |
| 最终人工 review 包 | `docs/human/real-core-v0-review-packet.md` | 已审，可作为测试标准 |
| 本机 Microsoft Word | 本机应用 | 可用，已验证可导出 PDF |

用户当前不需要补学校模板、不需要补学生文档、不需要再整理 review 包，也不需要手工导图。

## Codex 已准备完成

| 材料/能力 | 路径/状态 | 当前状态 |
| --- | --- | --- |
| 签名 source-fact 学校标准 | `standards/schools/*/v1/` | 已生成 |
| real-core profile expected baselines | `standards/eval_profiles/real-core-v0/expected/` | 已生成 |
| coverage gate | `docfit eval coverage --profile real-core-v0` | 可运行 |
| Word image evidence verifier | `src/docfit/harness/word_evidence.py` | 已实现 |
| Word evidence exporter | `scripts/export_real_core_word_evidence.py` | 已实现 |
| Word 本机导出链路 | Microsoft Word SaveAs PDF + `pdftoppm` | 已验证 |

## Codex 下一步需要准备/实现

这些不是用户材料，是工程输出。Codex 应继续开发，不应在这些点上要求用户准备：

1. real-core template stage：从已审模板基线生成/验证真实学校的 template artifact，不能再依赖 bootstrap 的 `[[DOCFIT_SLOT:body]]`。
2. real-core content stage：处理或建模学生 DOCX 中的可见图片，不能让 `unsupported_visible_object:image` 阻断后续链路。
3. real-core placement stage：按已审 render plan/source facts 给每个学生内容节点明确 disposition，保证 no silent drop。
4. real-core render stage：为 9 个 school/student 组合生成真实 `reports/real-core-v0/<case_id>/final.docx`。
5. Word evidence stage：对 9 个 `final.docx` 运行 `scripts/export_real_core_word_evidence.py`，生成 page PNG 和 manifest。
6. verification：运行 coverage、focused tests、必要的 e2e probe，确认 `real-core-v0` 不再因为 Word evidence 缺失而 UNKNOWN。

## 之后可能需要用户 review 的内容

只有当 Codex 生成了 9 个真实 `final.docx` 和 Word page images 后，才可能需要用户 review：

| 内容 | 需要用户现在准备吗 | 触发条件 |
| --- | --- | --- |
| 9 个 final.docx 的人工验收 | 否 | Codex 生成真实渲染输出后 |
| 9 组 Word page images 的视觉验收 | 否 | Word evidence exporter 跑完后 |
| 新增学校例外/规则签署 | 否 | 发现已审标准不足或冲突时 |

## 不应接受的替代物

- 复制学校模板或学生原稿冒充 `final.docx`。
- 手工改 `final.docx` 后再导图。
- 只有 PNG，没有绑定 `final.docx_sha256` 的 manifest。
- 用 LibreOffice 或脚本分页结果冒充 Microsoft Word evidence。
- 用人工视觉判断覆盖 deterministic `FAIL` 或 `UNKNOWN`。
