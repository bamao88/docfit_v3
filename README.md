# DocFit v3

Eval-harness-first prototype for verifiable DOCX conversion.

The first implementation target is the Bootstrap Profile from `SPEC.md`:

- four independent stages,
- `PASS` / `FAIL` / `UNKNOWN` gate semantics,
- visible content ledger,
- no silent drop verifier,
- signed standards and anti-drift checks,
- PM reports, issue clusters, and AI diagnosis packets.

Raw input assets are centralized in `inputs/`; see `inputs/README.md` for
original inputs, human review evidence, runnable standards, and real-school
source evidence. Bootstrap expected artifacts live under
`standards/eval_profiles/bootstrap-core/expected/`.

Current work on the real-school baseline harness is tracked in `STATUS.md`.
`real-core-v0` is registered as a fixed three-school, three-student profile.
Its deterministic coverage gate now returns `PASS` on this machine after the
reviewed baselines and nine Microsoft Word page-image evidence packages were
bound under `reports/real-core-v0/**`.

That PASS proves the evidence loop; it is not a claim that the generated DOCX
files are product-quality school submissions. Product-level layout review is
tracked in `docs/human/real-core-v0-product-quality-review.md`; the four-stage
test exposure matrix is tracked in
`docs/human/real-core-v0-stage-test-exposure.md`.

Run the bootstrap checks with:

```bash
uv run pytest
uv run docfit eval e2e --school demo-school --student inputs/bootstrap-demo-student-pass.docx --out reports/bootstrap_pass
```

Check the real-school baseline gate with:

```bash
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
```
