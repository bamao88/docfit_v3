# Bootstrap Verification Entropy Fixes

Date: 2026-06-14
Owner: Product + Engineering
Status: Complete

## Purpose

This plan closes the first batch of verification risks found while comparing
`SPEC.md` with the current Bootstrap Profile implementation.

The product goal is not prettier conversion output. The goal is that DocFit only
claims `PASS` when it has deterministic evidence for the bootstrap contract.

## Scope

In scope:

- Make coverage requirements blocking instead of report-only.
- Align the signed standard with the canonical bootstrap capability names.
- Prove rendered content from the output DOCX, not only from the placement plan.
- Verify that each downstream stage consumed the artifact it claims to have
  consumed.

Out of scope:

- MVP real-school support.
- Better visual formatting.
- Image, formula, footnote, or advanced Word feature support beyond returning
  `UNKNOWN`.
- AI making gate decisions.

## Fix Batch

### 1. Coverage Gate Is Blocking

Product risk: A run could say `PASS` even when a required bootstrap capability
was not covered.

Expected behavior:

- If a required capability is missing or false, the relevant stage returns
  `UNKNOWN`.
- The finding type is `coverage_insufficient`.
- E2E stops at the first stage whose coverage is insufficient.

Acceptance:

- A student fixture with paragraphs but no table must not pass content eval.
- Coverage requirements remain visible in `summary.json`.

Status: complete.

### 2. Signed Standard Capability Names Do Not Drift

Product risk: Product, standards, and implementation can use different names for
the same capability, making standards audit look green while the team is not
testing the same promise.

Expected behavior:

- `signed_standard.yaml` uses the same bootstrap capability vocabulary as the
  contracts and coverage engine.
- Standards audit returns `UNKNOWN` if the signed standard references an
  unknown or incomplete bootstrap capability profile.

Acceptance:

- Replacing `content.visible_tables` with the old
  `content.visible_text_blocks` name causes a standards finding of
  `coverage_requirements_drift`.

Status: complete.

### 3. Rendered Content Is Proven From The Output

Product risk: Render verification could prove that the placement plan contained
content hashes, while not proving that the final DOCX actually contains those
contents.

Expected behavior:

- Render verification extracts visible text/table content from the output DOCX.
- Required content hashes are matched against output-derived hashes.
- If a renderer action is marked executed but writes the wrong content, render
  returns `FAIL`.

Acceptance:

- A regression test mutates rendered output evidence and fails with a blocking
  render content finding.

Status: complete.

### 4. Stage Artifact Hash Chain Is Verified

Product risk: A stage could consume stale or tampered intermediate artifacts
while reports still look coherent.

Expected behavior:

- Placement plan provenance binds to the exact template and student content
  artifacts it consumed.
- Render manifest provenance binds to the exact template artifact and placement
  plan it consumed.
- Downstream eval fails if an artifact hash does not match the claimed upstream
  input.

Acceptance:

- Tampering with an intermediate artifact before render produces a deterministic
  blocking finding instead of a misleading `PASS`.

Status: complete.

## Verification Commands

```bash
uv run pytest -q
uv run docfit eval standards --school demo-school --out /tmp/docfit_standards
uv run docfit eval e2e --school demo-school \
  --student test_inputs/students/bootstrap-demo-pass/raw/source_document.docx \
  --out /tmp/docfit_bootstrap_pass
uv run docfit eval content \
  --student test_inputs/students/bootstrap-demo-unsupported-textbox/raw/source_document.docx \
  --out /tmp/docfit_bootstrap_unknown
uv run docfit eval placement --school demo-school \
  --template-artifact /tmp/docfit_bootstrap_pass/artifacts/template_artifact.json \
  --content-artifact /tmp/docfit_bootstrap_pass/artifacts/student_content_artifact.json \
  --simulate-drop c_002 \
  --out /tmp/docfit_bootstrap_fail
```

## Stop Condition

This batch is done when all four fixes have tests, the bootstrap PASS /
UNKNOWN / FAIL CLI checks still behave as expected, and the plan status is
updated to `Complete`.

## Completion Evidence

Verified on 2026-06-14:

- `uv run pytest -q`: 17 passed.
- `docfit eval standards --school demo-school`: `PASS`.
- `docfit eval coverage --profile bootstrap-core`: `PASS`.
- `docfit eval e2e` with `demo-thesis.docx`: `PASS`.
- `docfit eval content` with `with-unsupported-textbox.docx`: `UNKNOWN`.
- `docfit eval placement --simulate-drop c_002`: `FAIL`.
- A no-table student document now returns `UNKNOWN` with `coverage_gap`.
- Bootstrap render snapshot now includes output-derived content hashes and the
  expected student content hashes are a subset of those rendered hashes.
