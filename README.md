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
The reviewed baselines and nine Microsoft Word page-image evidence packages are
bound under `reports/real-core-v0/**`, but evidence binding is no longer a
sufficient pass condition.
The real-school template contracts now include executable `expected.units`
standards, so template parsing is checked at the unit, element, policy, and
style-field level before later stages can claim acceptance.
The real-school template gate also treats `generated_template.docx` as a tested
Word input: it writes `generated_template_tree.json` from OOXML and
`template_gap_report.json` / `.md` / `.docx` before e2e can claim template
acceptance. `docfit eval template-generate` now runs the template-generation
stage: it parses the source Word into `source_template_tree.json`, infers
`discovered_template_rules.json`, builds `template_artifact.json`,
`template_unit_decisions.json`, `template_generation_plan.json`, writes
`generated_template.docx`, and records `template_generation_manifest.json`.
When `--school <school_id>` is supplied, the generator also loads that school's
signed `expected.units` standard and uses it to align fillable/generated
markers to the source Word.
For `real-core-v0`, template and e2e runs now generate
`template_generation/generated_template.docx` during the run and gap-check that
file. The checked-in simulated business-template inputs under
`inputs/simulated-generated-templates/**` remain explicit template-gap fixtures;
they are not accepted generator output.

The current `real-core-v0` coverage gate returns `FAIL` for the existing
generated outputs because generated-template gap checks and deterministic
product-quality checks find template, content, placement, and render problems.
Product-level layout review is tracked in
`docs/human/real-core-v0-product-quality-review.md`; the four-stage gate is
tracked in `docs/human/real-core-v0-four-stage-problem-checks.md`.

Run the bootstrap checks with:

```bash
uv run pytest
uv run docfit eval e2e --school demo-school --student inputs/bootstrap-demo-student-pass.docx --out reports/bootstrap_pass
```

Check the real-school baseline gate with:

```bash
uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
```

Run one generated-template gap check with:

```bash
uv run docfit eval template-gap --school hunannongye --generated-template inputs/simulated-generated-templates/real-core-v0/hunannongye/generated_template.docx --out /tmp/docfit_template_gap_hunannongye
```

Run the template-generation stage with:

```bash
uv run docfit eval template-generate --school hunannongye --template inputs/school-hunannongye-requirement.docx --out /tmp/docfit_template_generate_hunannongye
```

Check that generated output against the signed template standard with:

```bash
uv run docfit eval template-gap --school hunannongye --generated-template /tmp/docfit_template_generate_hunannongye/generated_template.docx --out /tmp/docfit_template_gap_hunannongye_generated
```
