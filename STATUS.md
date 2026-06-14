# DocFit Status

Last updated: 2026-06-14

Current focus:

- Execute `docs/plans/real-school-baseline-eval-harness.md` through the
  `real-core-v0` eval harness path.

Current state:

- Wave 0 harness infrastructure is partially implemented.
- `real-core-v0` registry exists for three template cases, three content cases,
  and nine e2e school/student cases.
- `docfit eval coverage --profile real-core-v0` returns structured `UNKNOWN`,
  as intended, until signed baselines and Word image evidence exist.
- Baseline review packet drafts were generated at
  `out/real-core-v0-baseline-review/`.
- A generic dimension comparator foundation exists for the signed comparator
  modes named by the real-school plan.
- Baseline-to-artifact comparison now validates signed metadata, compares
  dimensions, and returns a merged `PASS` / `FAIL` / `UNKNOWN` result.
- Word image evidence manifests can be built and verified; coverage validates
  them when present and remains `UNKNOWN` while they are missing.
- AI RCA diagnosis packets are explicitly advisory-only and cannot mutate
  deterministic harness status.

Next action:

- Review and lock the generated baseline drafts, then continue with
  stage-specific artifact normalizers/comparator adapters and Word image
  evidence production/export automation.

Known blockers:

- Full `real-core-v0` cannot be claimed complete until user/product review
  signs the real baselines.
- Local Microsoft Word image export evidence is still required for the nine
  render cases.
