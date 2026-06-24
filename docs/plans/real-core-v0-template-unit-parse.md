# real-core-v0 Template Unit Parse Plan

Status: Implemented for strict template parser/verifier slice
Last reviewed: 2026-06-16

## Goal

Implement the template-only `real-core-v0` slice: real school templates must
produce deterministic template units, elements, output policies, and writable
targets instead of falling back to a single virtual `slot_body_start`.

## Approved Preflight Contract

Task source: mixed conversation and repo state.

Route: durable `$intuitive-flow`, executed in the main session because this is a
bounded single-stage parser/verifier slice.

Scope:

- Add structured `data.units` to real-core template artifacts for all three
  school templates.
- Derive units, elements, sub-elements, and policies from existing reviewed
  school template baselines under `standards/targets/*/v1/`.
- Classify template instruction/example paragraphs so the template acceptance
  gate can tell whether they are fixed, fillable, generated, manual-only, or
  stripped from final output.
- Produce real writable slots from fillable/generated template elements instead
  of relying only on the virtual body slot.
- Update focused tests and product-quality audit so template acceptance clears
  while content, placement, and render remain blocking.
- Add executable `expected.units` to each real-school `template_unit_contract.yaml`
  and compare actual template artifacts against it at unit, element, policy,
  content, style, and relationship granularity.

Non-goals:

- Do not change student content extraction, placement mapping, or render output
  behavior in this slice.
- Do not regenerate the nine real-core `final.docx` files or Word page-image
  evidence packages.
- Do not auto-update signed standards, expected baselines, goldens, or Word
  evidence.
- Do not claim full `real-core-v0` acceptance; later stages should still fail.

## Acceptance

- Each real-core template artifact contains a non-empty `data.units` list with
  school unit ids, element ids, order, policies, and source evidence.
- Each real-school `template_unit_contract.yaml` contains `expected.units`; if
  that structured standard is missing, template acceptance returns `UNKNOWN`.
- The verifier compares every expected unit and element against
  `template_artifact.data.units`, including style strings. A style mismatch
  returns a path-specific finding such as `template_element_style_mismatch` on
  `cover.e_001.style`.
- Each real-core template artifact contains non-virtual writable slots derived
  from fillable/generated elements.
- Template instruction/example paragraphs are classified and no longer trigger
  `template_instruction_paragraph_unclassified`.
- The four-stage e2e probe no longer reports `template_unit_tree_missing` or
  `template_instruction_paragraph_unclassified`; `blocked_at` advances to the
  next failing business stage.
- Full profile coverage remains non-PASS until content, placement, render, and
  freshly regenerated report artifacts are fixed. Because this slice does not
  regenerate `runs/eval/real-core-v0/**`, profile coverage may still show
  template findings from stale report artifacts; the current parser proof is the
  temporary e2e product run below.

## Verification

Required deterministic gates:

```bash
uv run pytest tests/contract/test_real_core_four_stage_problem_checks.py tests/contract/test_real_core_baseline_harness.py tests/contract/test_contract_gates.py tests/unit/test_baseline_comparison.py
```

Required integration gate:

```bash
uv run pytest tests/e2e/test_bootstrap_cli.py
```

Required product-run gates:

```bash
uv run docfit eval e2e --school hunannongye --student test_inputs/students/real-student-003/raw/source_document.docx --out /tmp/docfit_real_core_template_probe
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
```

Optional:

```bash
uv run pytest
```

## Verification Result

Run on 2026-06-16:

- Strict template verifier update:
  `uv run pytest tests/contract/test_real_core_baseline_harness.py tests/contract/test_real_core_four_stage_problem_checks.py -q`: 13 passed.
- Full verification after strict verifier update: `uv run pytest`: 50 passed.
- `uv run pytest tests/contract/test_real_core_four_stage_problem_checks.py tests/contract/test_real_core_baseline_harness.py tests/contract/test_contract_gates.py tests/unit/test_baseline_comparison.py`: 25 passed.
- `uv run pytest tests/e2e/test_bootstrap_cli.py`: 5 passed.
- `uv run pytest`: 48 passed.
- `uv run docfit eval e2e --school hunannongye --student test_inputs/students/real-student-003/raw/source_document.docx --out /tmp/docfit_real_core_template_probe`: `status = FAIL`, `blocked_at = content`, `stage_statuses.template = PASS`, `business.template_acceptance = true`.
- `uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage`: `status = FAIL`; this still reads stale `runs/eval/real-core-v0/**` artifacts and remains blocked until the nine runs/eval/final DOCX files are regenerated after later slices.

## Remaining Work After This Slice

- Convert student reviews into a stronger content tree extractor/verifier.
- Map content nodes to target units/elements in placement plans.
- Rewrite render to place content into target locations instead of appending.
- Regenerate the nine final DOCX files and Word evidence only after P0/P1
  business findings are cleared.
