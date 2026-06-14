# DocFit v3

Eval-harness-first prototype for verifiable DOCX conversion.

The first implementation target is the Bootstrap Profile from `SPEC.md`:

- four independent stages,
- `PASS` / `FAIL` / `UNKNOWN` gate semantics,
- visible content ledger,
- no silent drop verifier,
- signed standards and anti-drift checks,
- PM reports, issue clusters, and AI diagnosis packets.

Run the bootstrap checks with:

```bash
uv run pytest
uv run docfit eval e2e --school demo-school --student fixtures/bootstrap/students/demo-thesis.docx --out reports/bootstrap_pass
```
