# Bootstrap Eval Runbook

Use this when changes touch contracts, verifiers, stage runners, standards,
input assets, report generation, or CLI eval behavior.

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
  --student inputs/students/bootstrap-demo-pass/raw/source_document.docx \
  --out /tmp/docfit_bootstrap_pass
```

Expected status is `PASS`.

## Bootstrap UNKNOWN

```bash
uv run docfit eval content \
  --student inputs/students/bootstrap-demo-unsupported-textbox/raw/source_document.docx \
  --out /tmp/docfit_bootstrap_unknown
```

Expected status is `UNKNOWN`. Unsupported visible content must not be silently
dropped or treated as success.

## Bootstrap FAIL

Failure injection is private test infrastructure, not a public CLI option. Use
the focused pytest proof when you need to verify that the renderer catches a
skipped placement action:

```bash
uv run pytest tests/e2e/test_bootstrap_cli.py::test_fail_when_renderer_skips_action -q
```

Expected status is `FAIL`.

## Evidence Rules

- Treat `runs/eval/**`,
  `runs/template_generation/*/eval_runs/**`,
  `runs/workbench/**`, and
  `/tmp/docfit_*` as generated evidence.
- Do not update goldens, signed standards, expected snapshots, or fixture output
  just to make a failing run pass.
- If a change intentionally updates a standard, contract, or golden, include the
  matching provenance, signed evidence, and regression coverage in the same
  change.
