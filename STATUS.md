# DocFit Status

Last updated: 2026-06-15

Current focus:

- Keep `real-core-v0` deterministic evidence closed while the generated
  outputs move into product-level visual/semantic review.

Current state:

- Wave 0 harness infrastructure is implemented for the deterministic
  `real-core-v0` source-fact and Word evidence gate.
- `real-core-v0` registry exists for three template cases, three content cases,
  and nine e2e school/student cases.
- User/product acceptance requirements for the blocking real baselines and Word
  evidence are documented in `docs/human/real-core-v0-acceptance.md`.
- The user-reviewed `docs/human/real-core-v0-review-packet.md` is bound as the
  accepted source-fact standard for `real-core-v0`.
- `docfit eval coverage --profile real-core-v0` returns `PASS` on this machine
  after generating the nine local Microsoft Word image evidence packages under
  `reports/real-core-v0/**`.
- The nine generated case reports under `reports/real-core-v0/<case_id>/`
  now each report `PASS`, `blocked_at: null`, zero findings, and
  `render.word_image_evidence: true` after Word evidence reconciliation.
- A generic dimension comparator foundation exists for the signed comparator
  modes named by the real-school plan.
- Baseline-to-artifact comparison now validates signed metadata, compares
  dimensions, and returns a merged `PASS` / `FAIL` / `UNKNOWN` result.
- Word image evidence manifests can be built and verified; coverage validates
  them when present and remains `UNKNOWN` while they are missing.
- `scripts/export_real_core_word_evidence.py --reconcile-existing` verifies
  existing manifests and refreshes per-case reports without re-opening Word.
- real-core e2e runs now reach render for all nine school/student combinations
  and produce bound `final.docx` files before Word evidence export.
- AI RCA diagnosis packets are explicitly advisory-only and cannot mutate
  deterministic harness status.

Next action:

- Review the generated `reports/real-core-v0/**/final.docx` and
  `reports/real-core-v0/**/evidence/page-*.png` artifacts for product-level
  visual/semantic acceptance beyond the deterministic source-fact coverage
  gate.

Known blockers:

- No external user-prepared materials are currently blocking engineering.
- The current PASS gate proves signed source-fact coverage plus Word-open/page
  image evidence. It is not a claim that every target-school layout detail is
  visually perfect; that remains a product review step over generated outputs.
