# DocFit v3

Eval-harness-first prototype for verifiable DOCX conversion.

The first implementation target is the Bootstrap Profile from `SPEC.md`:

- four independent stages,
- `PASS` / `FAIL` / `UNKNOWN` result states,
- visible content ledger,
- checks that visible content is not silently dropped,
- signed standards and anti-drift checks,
- PM reports, issue clusters, and AI diagnosis packets.

Raw input assets are centralized in `inputs/`; see `inputs/README.md` for
original inputs, human review evidence, runnable standards, and real-school
source evidence. Bootstrap expected artifacts live under
`standards/eval_profiles/bootstrap-core/expected/`.

Current work on the real-school baseline harness is tracked in `STATUS.md`.
`real-core-v0` is registered as a fixed three-school, three-student profile.
On this machine, its fixed evidence check returns `PASS` after the reviewed
baselines and nine Microsoft Word page-image evidence packages were bound under
`reports/real-core-v0/**`.

That `PASS` proves the evidence loop only: the inputs, generated files, Word
open result, and page images are all accounted for. It is not a claim that the
generated DOCX files are product-quality school submissions. Product-level
layout review is tracked in
`docs/human/real-core-v0-product-quality-review.md`; the check that each of the
four conversion steps can point to a concrete current problem is tracked in
`docs/human/real-core-v0-four-stage-problem-checks.md`.

Run the bootstrap checks with:

```bash
uv run pytest
uv run docfit eval e2e --school demo-school --student inputs/bootstrap-demo-student-pass.docx --out reports/bootstrap_pass
```

Check the real-school baseline gate with:

```bash
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
```
