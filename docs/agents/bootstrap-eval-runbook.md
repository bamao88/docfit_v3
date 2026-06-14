# Bootstrap Eval Runbook

Use this when changes touch contracts, verifiers, stage runners, standards,
fixtures, report generation, or CLI eval behavior.

## Fast Loop

```bash
uv run pytest -q
```

Run focused tests first when the target is obvious, then run the relevant CLI
eval command before handing off.

## Bootstrap PASS

```bash
uv run docfit eval standards --school demo-school --out /tmp/docfit_standards
uv run docfit eval coverage --profile bootstrap-core --out /tmp/docfit_coverage
uv run docfit eval e2e --school demo-school \
  --student fixtures/bootstrap/students/demo-thesis.docx \
  --out /tmp/docfit_bootstrap_pass
```

Expected status is `PASS`.

## Bootstrap UNKNOWN

```bash
uv run docfit eval content \
  --student fixtures/bootstrap/students/with-unsupported-textbox.docx \
  --out /tmp/docfit_bootstrap_unknown
```

Expected status is `UNKNOWN`. Unsupported visible content must not be silently
dropped or treated as success.

## Bootstrap FAIL

Generate the PASS artifacts first, then simulate a placement drop:

```bash
uv run docfit eval placement --school demo-school \
  --template-artifact /tmp/docfit_bootstrap_pass/artifacts/template_artifact.json \
  --content-artifact /tmp/docfit_bootstrap_pass/artifacts/student_content_artifact.json \
  --simulate-drop c_002 \
  --out /tmp/docfit_bootstrap_fail
```

Expected status is `FAIL`.

## Evidence Rules

- Treat `reports/**`, `out/**`, and `/tmp/docfit_*` as generated evidence.
- Do not update goldens, signed standards, expected snapshots, or fixture output
  just to make a failing run pass.
- If a change intentionally updates a standard, contract, or golden, include the
  matching provenance, signed evidence, and regression coverage in the same
  change.
