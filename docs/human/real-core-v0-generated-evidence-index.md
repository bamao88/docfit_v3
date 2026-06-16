# real-core-v0 Generated Evidence Index

日期：2026-06-15

本机已生成 `real-core-v0` 的 9 个 school/student 组合输出。生成物位于
`reports/real-core-v0/**`，该目录按仓库规则属于本地 generated evidence，不随代码提交。

Coverage proof:

```bash
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage_after_reconcile
# status = PASS
```

Per-case report reconciliation:

```bash
uv run python scripts/export_real_core_word_evidence.py --reconcile-existing
# all 9 case reports reconciled
```

## Evidence Matrix

| Case | Report | Final DOCX | Word page images | Page count |
| --- | --- | --- | --- | ---: |
| `real_core_v0_hunannongye_real-student-001` | `PASS`, 0 findings | `reports/real-core-v0/real_core_v0_hunannongye_real-student-001/final.docx` | `reports/real-core-v0/real_core_v0_hunannongye_real-student-001/evidence/page-*.png` | 40 |
| `real_core_v0_hunannongye_real-student-002` | `PASS`, 0 findings | `reports/real-core-v0/real_core_v0_hunannongye_real-student-002/final.docx` | `reports/real-core-v0/real_core_v0_hunannongye_real-student-002/evidence/page-*.png` | 36 |
| `real_core_v0_hunannongye_real-student-003` | `PASS`, 0 findings | `reports/real-core-v0/real_core_v0_hunannongye_real-student-003/final.docx` | `reports/real-core-v0/real_core_v0_hunannongye_real-student-003/evidence/page-*.png` | 25 |
| `real_core_v0_nannong-undergraduate_real-student-001` | `PASS`, 0 findings | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-001/final.docx` | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-001/evidence/page-*.png` | 31 |
| `real_core_v0_nannong-undergraduate_real-student-002` | `PASS`, 0 findings | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-002/final.docx` | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-002/evidence/page-*.png` | 27 |
| `real_core_v0_nannong-undergraduate_real-student-003` | `PASS`, 0 findings | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-003/final.docx` | `reports/real-core-v0/real_core_v0_nannong-undergraduate_real-student-003/evidence/page-*.png` | 18 |
| `real_core_v0_pku-graduate_real-student-001` | `PASS`, 0 findings | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-001/final.docx` | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-001/evidence/page-*.png` | 76 |
| `real_core_v0_pku-graduate_real-student-002` | `PASS`, 0 findings | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-002/final.docx` | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-002/evidence/page-*.png` | 67 |
| `real_core_v0_pku-graduate_real-student-003` | `PASS`, 0 findings | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-003/final.docx` | `reports/real-core-v0/real_core_v0_pku-graduate_real-student-003/evidence/page-*.png` | 46 |

Each evidence directory also contains `word_image_evidence.json`, binding the
page images to the corresponding `final.docx` SHA-256 and Microsoft Word
version `16.109.3`.

Each case directory also contains `summary.json`, `findings.json`,
`issue_clusters.json`, and `pm_report.md`. After reconciliation, every
`summary.json` has `status: PASS`, `blocked_at: null`, and
`coverage.render.word_image_evidence: true`.

## Review Boundary

This evidence proves the deterministic source-fact coverage and Microsoft
Word-open/page-image export gate. It does not replace product review of final
layout quality. The next review surface is the generated `final.docx` and page
images listed above.

Product QA review has started here:

```text
docs/human/real-core-v0-product-quality-review.md
```

Current product QA result: the nine generated outputs are not yet product
accepted. They prove the evidence loop, but still retain template
instructions/examples and use append-only student-content rendering.
