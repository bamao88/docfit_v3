# DocFit Inputs

本目录是 DocFit 的唯一输入资产入口。这里放原始 DOCX/DOC、学生样例、
人工 review 证据，以及 bootstrap eval 需要的 expected fixture JSON。

机器可执行标准仍然放在 `standards/schools/**`：signed standard、contracts、
goldens 和 exceptions 不属于原始输入。

## Bootstrap 输入

| 文件 | 类型 | 用途 | 对应标准 |
| --- | --- | --- | --- |
| `bootstrap-demo-school-template.docx` | 原始学校模板 | Bootstrap Stage 1 模板解析输入 | `standards/schools/demo-school/v1/signed_standard.yaml` |
| `bootstrap-demo-student-pass.docx` | 学生示例输入 | Bootstrap e2e `PASS` case | `standards/schools/demo-school/v1/*_contract.json` |
| `bootstrap-demo-student-unsupported-textbox.docx` | 学生示例输入 | Unsupported visible object -> `UNKNOWN` case | `standards/schools/demo-school/v1/student_content_contract.json` |
| `bootstrap-demo-student-silent-drop.docx` | 学生示例输入 | Silent-drop / placement regression case | `standards/schools/demo-school/v1/placement_contract.json` |
| `bootstrap-demo-placement-plan.json` | Expected fixture | Bootstrap coverage gate input | `standards/schools/demo-school/v1/placement_contract.json` |
| `bootstrap-demo-feature-snapshot.json` | Expected fixture | Bootstrap coverage/render hash gate input | `standards/schools/demo-school/v1/render_contract.json` |

## 真实学生输入

这些是真实学生 DOCX 和人工内容识别记录。它们还不是 Bootstrap `PASS`
fixture，因为当前 bootstrap profile 会把图片、文本框、脚注等未支持可见对象阻断为
`UNKNOWN`。

| 文件 | 类型 | 用途 | 对应标准 |
| --- | --- | --- | --- |
| `real-student-001-source.docx` | 原始学生论文 | 未来内容提取回归输入 | 尚未绑定 signed standard |
| `real-student-001-content-review.md` | 人工 review | `001` 的内容识别参考 | 尚未绑定 signed standard |
| `real-student-002-source.docx` | 原始学生论文 | 未来内容提取回归输入 | 尚未绑定 signed standard |
| `real-student-002-content-review.md` | 人工 review | `002` 的内容识别参考 | 尚未绑定 signed standard |
| `real-student-003-source.docx` | 原始学生论文 | 未来内容提取回归输入 | 尚未绑定 signed standard |
| `real-student-003-content-review.md` | 人工 review | `003` 的内容识别参考 | 尚未绑定 signed standard |

## 真实学校模板输入

这些是真实学校模板/要求和人工模板 review 证据。它们是未来 MVP 学校标准的来源，
目前对应的 school package 还不是 runnable signed standard。

| 文件 | 类型 | 用途 | 对应标准包 |
| --- | --- | --- | --- |
| `school-hunannongye-requirement.docx` | 原始学校模板 | 湖南农业未来 Stage 1 输入 | `standards/schools/hunannongye/v1/` |
| `school-hunannongye-requirement-legacy.doc` | 原始 legacy 文件 | 湖南农业 provenance | `standards/schools/hunannongye/v1/` |
| `school-hunannongye-template-review.txt` | 人工 review | 湖南农业模板识别证据 | `standards/schools/hunannongye/v1/` |
| `school-nannong-undergraduate-template.docx` | 原始学校模板 | 南京农业本科未来 Stage 1 输入 | `standards/schools/nannong-undergraduate/v1/` |
| `school-nannong-undergraduate-template-review.txt` | 人工 review | 南京农业本科模板识别证据 | `standards/schools/nannong-undergraduate/v1/` |
| `school-pku-graduate-template.docx` | 原始学校模板 | 北大研究生未来 Stage 1 输入 | `standards/schools/pku-graduate/v1/` |
| `school-pku-graduate-template-review.txt` | 人工 review | 北大研究生模板识别证据 | `standards/schools/pku-graduate/v1/` |
| `shared-template-recognition-alignment-review.txt` | 人工 review | 跨学校模板识别对齐证据 | 多学校未来标准参考 |
