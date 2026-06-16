# DocFit Status

Last updated: 2026-06-16

Current focus:

- Keep `real-core-v0` deterministic evidence closed while the generated
  outputs move into product-level visual/semantic review.
- Product QA has started for the nine generated Word outputs; deterministic
  PASS is now explicitly separated from product layout acceptance.

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
- Product review of those nine generated outputs is recorded in
  `docs/human/real-core-v0-product-quality-review.md`. The current outputs are
  not product-accepted: they still retain target-template instructions/examples
  and mostly append student content after copied template content.
- Four-stage product-quality exposure is now executable via
  `src/docfit/harness/product_quality.py` and
  `tests/contract/test_real_core_product_quality_exposure.py`; the exposure
  matrix is documented in `docs/human/real-core-v0-stage-test-exposure.md`.
  It produces specific template/content/placement/render findings for the
  current generated-output failure mode without changing deterministic gates.
- Source TOC entries are now modeled as visible `source_format` content,
  receive `discard_as_source_format` placement dispositions, and are executed
  by render without writing old TOC text into future regenerated outputs.
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

- Continue the product-quality implementation path in
  `docs/human/real-core-v0-stage-test-exposure.md`: promote the four
  product-quality exposure findings into stage contracts/verifiers, starting
  with template unit tree and non-output instruction policy.

Known blockers:

- No external user-prepared materials are currently blocking engineering.
- The current PASS gate proves signed source-fact coverage plus Word-open/page
  image evidence. It is not a claim that every target-school layout detail is
  visually perfect; that remains a product review step over generated outputs.
