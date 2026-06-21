# real-core-v0 下一步开发材料责任分工

日期：2026-06-15

## 结论

目前不需要用户再准备新的外部材料。

此前开发已经把 `real-core-v0` 的已审材料转成 9 个真实渲染输出：

```text
test_outputs/debug/template_eval_runs/real-core-v0/<case_id>/final.docx
```

这些 `final.docx` 由 DocFit real-core 渲染链路产生，并已通过 Word evidence exporter 生成：

```text
test_outputs/debug/template_eval_runs/real-core-v0/<case_id>/evidence/word_image_evidence.json
test_outputs/debug/template_eval_runs/real-core-v0/<case_id>/evidence/page-*.png
```

这些输出和 Word evidence 证明旧的证据闭环曾经跑通，但它们不再代表当前
`real-core-v0` 已通过。当前 deterministic coverage 结果：

```bash
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
# status = FAIL
```

产品质量验收已开始，结论见：

```text
docs/human/real-core-v0-product-quality-review.md
```

当前 9 个输出还不能视为产品质量合格成品；主要问题是生成模板 Word 差距检查
已经阻断 template 阶段，后续内容抽取、内容放置、Word 生成仍有具体问题。
后续工程仍可继续推进，不需要用户补充新材料。

生成物索引见：

```text
docs/human/real-core-v0-generated-evidence-index.md
```

## 用户已准备完成

| 材料 | 路径/状态 | 当前状态 |
| --- | --- | --- |
| 3 所学校模板源文件 | `test_inputs/template_generation/school-*.docx` | 已存在 |
| 3 所学校模板人工审查源 | `test_inputs/template_generation/school-*-template-review.txt` | 已存在 |
| 3 份学生源 DOCX | `test_inputs/content_extraction/real-student-*-source.docx` | 已存在 |
| 3 份学生内容人工审查源 | `test_inputs/content_extraction/real-student-*-content-review.md` | 已存在 |
| 共享模板识别/对齐审查 | `test_inputs/template_generation/shared-template-recognition-alignment-review.txt` | 已存在 |
| 最终人工 review 包 | `docs/human/real-core-v0-review-packet.md` | 已审，可作为测试标准 |
| 本机 Microsoft Word | 本机应用 | 可用，已验证可导出 PDF |

用户当前不需要补学校模板、不需要补学生文档、不需要再整理 review 包，也不需要手工导图。

## Codex 已准备完成

| 材料/能力 | 路径/状态 | 当前状态 |
| --- | --- | --- |
| 签名 source-fact 学校标准 | `standards/schools/*/v1/` | 已生成 |
| real-core profile expected baselines | `standards/eval_profiles/real-core-v0/expected/` | 已生成 |
| coverage gate | `docfit eval coverage --profile real-core-v0` | 可运行 |
| 生成模板差距检查 | `docfit eval template-gap --school ... --generated-template ...` | 已实现，当前会阻断坏模板 |
| Word image evidence verifier | `src/docfit/harness/word_evidence.py` | 已实现 |
| Word evidence exporter | `scripts/export_real_core_word_evidence.py` | 已实现 |
| Word 本机导出链路 | Microsoft Word SaveAs PDF + `pdftoppm` | 已验证 |
| 9 个 real-core final.docx | `test_outputs/debug/template_eval_runs/real-core-v0/<case_id>/final.docx` | 已生成 |
| 9 组 Word page image evidence | `test_outputs/debug/template_eval_runs/real-core-v0/<case_id>/evidence/` | 已生成 |
| 产品质量 review 结论 | `docs/human/real-core-v0-product-quality-review.md` | 已生成，当前未验收通过 |

## Codex 已完成的工程输出

这些不是用户材料，是工程输出；此前已完成并仍可复用的部分：

1. real-core template stage：从已审模板基线生成/验证真实学校的 template artifact，不能再依赖 bootstrap 的 `[[DOCFIT_SLOT:body]]`。
2. real-core content stage：建模学生 DOCX 中的可见图片，避免 `unsupported_visible_object:image` 阻断后续链路。
3. real-core placement stage：按已审 render plan/source facts 给每个学生内容节点明确 disposition，保证 no silent drop。
4. real-core render stage：为 9 个 school/student 组合生成真实 `test_outputs/debug/template_eval_runs/real-core-v0/<case_id>/final.docx`。
5. Word evidence stage：对 9 个 `final.docx` 运行 `scripts/export_real_core_word_evidence.py`，生成 page PNG 和 manifest。
6. verification：Word evidence 不再是唯一阻断；当前 coverage 会继续检查生成模板差距和业务质量，坏输出返回 `FAIL`。

## 之后可能需要用户 review 的内容

Codex 已经生成 9 个真实 `final.docx` 和 Word page images。当前产品 QA
已经确认这些输出不是最终可验收质量。下一次需要用户 review 的对象应是
P0/P1 修复并重新生成后的 9 个输出：

| 内容 | 需要用户现在准备吗 | 触发条件 |
| --- | --- | --- |
| 9 个 final.docx 的人工验收 | 否 | 可直接审查当前 `test_outputs/debug/template_eval_runs/real-core-v0/**/final.docx` |
| 9 组 Word page images 的视觉验收 | 否 | 可直接审查当前 `test_outputs/debug/template_eval_runs/real-core-v0/**/evidence/page-*.png` |
| 新增学校例外/规则签署 | 否 | 发现已审标准不足或冲突时 |

## 不应接受的替代物

- 复制学校模板或学生原稿冒充 `final.docx`。
- 手工改 `final.docx` 后再导图。
- 只有 PNG，没有绑定 `final.docx_sha256` 的 manifest。
- 用 LibreOffice 或脚本分页结果冒充 Microsoft Word evidence。
- 用人工视觉判断覆盖 deterministic `FAIL` 或 `UNKNOWN`。
