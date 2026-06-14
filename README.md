# DocFit v3

Eval-harness-first prototype for verifiable DOCX conversion.

The first implementation target is the Bootstrap Profile from `SPEC.md`:

- four independent stages,
- `PASS` / `FAIL` / `UNKNOWN` gate semantics,
- visible content ledger,
- no silent drop verifier,
- signed standards and anti-drift checks,
- PM reports, issue clusters, and AI diagnosis packets.

Input assets are centralized in `inputs/`; see `inputs/README.md` for which
files are original inputs and which signed standards or future standard packages
they correspond to.

Run the bootstrap checks with:

```bash
uv run pytest
uv run docfit eval e2e --school demo-school --student inputs/bootstrap-demo-student-pass.docx --out reports/bootstrap_pass
```
