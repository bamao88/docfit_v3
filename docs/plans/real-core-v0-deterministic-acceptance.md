# real-core-v0 Deterministic Acceptance Plan

Status: Implemented for acceptance-gate slice
Last reviewed: 2026-06-16

## Goal

Upgrade `real-core-v0` from source-fact and Word-evidence binding to deterministic, fine-grained business acceptance before further eval-driven rendering work.

## Approved Preflight Contract

Task source: mixed conversation and repo state.

Route: durable `$intuitive-flow`, executed in the main session for this first bounded standards/verifier slice.

Scope:

- Split the existing source-fact baseline into executable template, content, placement, and render business checks.
- Treat school template reviews as the source for structured template unit contracts.
- Treat student content reviews as the source for structured student content trees.
- Treat shared alignment plus the 3 x 3 case matrix as the source for case-level placement expectations.
- Treat rendered DOCX plus Microsoft Word evidence as necessary but not sufficient render evidence.
- Ensure current bad product-quality output cannot pass merely because evidence is bound.

Non-goals:

- Do not optimize the real-core renderer before the acceptance gates can fail the current bad output.
- Do not ask for new external review material.
- Do not auto-update signed standards, goldens, or expected baselines from current output.
- Do not use AI or runtime human judgement as the pass/fail authority.
- Do not accept LibreOffice or script pagination as Microsoft Word evidence.

## Current Repo Reality

`STATUS.md` now records that the nine `reports/real-core-v0/**/final.docx` files and Word image evidence packages exist, but evidence binding is no longer sufficient for `PASS`.

The product review in `docs/human/real-core-v0-product-quality-review.md` records that those same outputs are not business-acceptable: template instructions leak into the final DOCX, student content is appended after copied templates, and content is not placed in target school positions.

Therefore this implementation slice does not improve rendering. It makes the deterministic gate report those known product failures.

## Acceptance

- `run_e2e_eval` for real-core applies the product-quality gate after render and returns `FAIL` or `UNKNOWN` when template/content/placement/render quality findings exist.
- `docfit eval coverage --profile real-core-v0` checks existing reports with the same product-quality gate and no longer reports full `PASS` for the current bad generated outputs.
- Focused tests prove all four business stages are represented by blocking findings.
- Bootstrap behavior remains unchanged.

## Verification

Required deterministic gates:

```bash
uv run pytest tests/unit/test_baseline_comparison.py tests/unit/test_word_evidence.py tests/contract/test_contract_gates.py tests/contract/test_real_core_baseline_harness.py tests/contract/test_real_core_four_stage_problem_checks.py
```

Required integration gate:

```bash
uv run pytest tests/e2e/test_bootstrap_cli.py
```

Required product-run gate:

```bash
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
```

Local/live gate, still required before claiming final render-format acceptance:

```bash
uv run python scripts/export_real_core_word_evidence.py
```

This local/live gate depends on nine freshly generated `final.docx` files and local Microsoft Word. It is not required to prove this acceptance-gate slice.

## Verification Result

Run on 2026-06-16:

- `uv run pytest tests/unit/test_baseline_comparison.py tests/unit/test_word_evidence.py tests/contract/test_contract_gates.py tests/contract/test_real_core_baseline_harness.py tests/contract/test_real_core_four_stage_problem_checks.py`: 30 passed.
- `uv run pytest tests/e2e/test_bootstrap_cli.py`: 5 passed.
- `uv run pytest`: 47 passed.
- `uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage`: `status = FAIL`, `blocked_at = template`, with all 9 e2e cases checked by product-quality gate and all four business acceptance flags false.

## Remaining Work After This Slice

- Replace the failing product-quality gate by fixing template parsing, content extraction, placement, and rendering in that order.
- Expand structured baseline dimensions until every accepted content node has a target unit/element/sub-element disposition.
- Regenerate the nine real-core final DOCX files and Microsoft Word evidence only after P0/P1 business failures are removed.
