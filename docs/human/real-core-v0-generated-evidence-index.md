# real-core-v0 Generated Evidence Index

日期：2026-06-15

本机已生成 `real-core-v0` 的 9 个 school/student 组合输出。生成物位于
`reports/real-core-v0/**`，该目录按仓库规则属于本地 generated evidence，不随代码提交。

Coverage proof:

```bash
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage_final_pass_check
# status = PASS
```

## Evidence Matrix

| Case | Final DOCX | Word page images | Page count |
| --- | --- | --- | ---: |
| `real_core_v0_hunannongye_real-student-001` | `reports/real-core-v0/real_core_v0_hunannongye_real-student-001/final.docx` | `reports/real-core-v0/real_core_v0_hunannongye_real-student-001/evidence/page-*.png` | 40 |
| `real_core_v0_hunannongye_real-student-002` | `reports/real-core-v0/real_core_v0_hunannongye_real-student-002/final.docx` | `reports/real-core-v0/real_core_v0_hunannongye_real-student-002/evidence/page-*.png` | 36 |
| `real_core_v0_hunannongye_real-student-003` | `reports/real-core-v0/real_core_v0_hunannongye_real-student-003/final.docx` | `reports/real-core-v0/real_core_v0_hunannongye_real-student-003/evidence/page-*.png` | 25 |
| `real_core_v0_nannong-undergraduate_real-student-001` | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-001/final.docx` | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-001/evidence/page-*.png` | 31 |
| `real_core_v0_nannong-undergraduate_real-student-002` | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-002/final.docx` | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-002/evidence/page-*.png` | 27 |
| `real_core_v0_nannong-undergraduate_real-student-003` | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-003/final.docx` | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-003/evidence/page-*.png` | 18 |
| `real_core_v0_pku-graduate_real-student-001` | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-001/final.docx` | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-001/evidence/page-*.png` | 76 |
| `real_core_v0_pku-graduate_real-student-002` | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-002/final.docx` | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-002/evidence/page-*.png` | 67 |
| `real_core_v0_pku-graduate_real-student-003` | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-003/final.docx` | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-003/evidence/page-*.png` | 46 |

Each evidence directory also contains `word_image_evidence.json`, binding the
page images to the corresponding `final.docx` SHA-256 and Microsoft Word
version `16.109.3`.

## Review Boundary

This evidence proves the deterministic source-fact coverage and Microsoft
Word-open/page-image export gate. It does not replace product review of final
layout quality. The next review surface is the generated `final.docx` and page
images listed above.
