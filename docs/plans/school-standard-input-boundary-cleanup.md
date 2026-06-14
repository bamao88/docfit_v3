# School Standard And Input Boundary Cleanup

Date: 2026-06-14
Owner: Product + Engineering
Status: Proposed

## Purpose

Before adding more conversion capability, clean the migrated repository shape so
the prototype has one obvious main path:

```text
raw school/student inputs -> signed runnable standard -> stage verifiers ->
evidence report -> PASS / FAIL / UNKNOWN
```

This plan intentionally does not preserve backward compatibility unless a later
task explicitly asks for a temporary bridge. The current prototype contract at
`HEAD` is the target.

## Product Direction

Do not delete the real schools. The cleanup target is the boundary between
source evidence and runnable standards:

- `demo-school` remains a synthetic bootstrap harness, not product proof.
- Hunan Agricultural, Nanjing Agricultural Undergraduate, and PKU Graduate
  remain real school source evidence.
- Only directories with `signed_standard.yaml` and reviewed contracts should
  live under runnable `standards/schools/**`.
- Raw DOCX/DOC files, student documents, and human review evidence stay under
  the input asset surface.
- Expected placement plans, feature snapshots, and generated reports are not
  raw inputs.

Default first real-school promotion candidate: `hunannongye`, because it has a
converted `.docx`, original legacy `.doc`, and human template review evidence.
This is a recommendation for the next product slice, not part of this cleanup
unless explicitly selected.

## Accepted Decisions

These decisions were accepted in the docs grilling pass on 2026-06-14:

1. `SPEC.md` must be updated during this cleanup so it no longer presents
   bootstrap expected JSON files as members of `inputs/`.
2. Non-runnable real-school directories under `standards/schools/**` should be
   removed. Their raw files and human review status stay cataloged in
   `inputs/README.md`.
3. Bootstrap expected artifacts should move to the eval profile surface:
   `standards/eval_profiles/bootstrap-core/expected/`.
4. This cleanup does not select, sign, or make any real-school standard pass.
   It only makes real-school source evidence clearly discoverable for the next
   product slice.

## Zoom-Out Map

Control plane:

- `src/docfit/cli/main.py`: public `docfit eval ...`, `docfit convert`, and
  diagnostic commands.
- `src/docfit/convert/orchestrator.py`: stage orchestration, stage status
  aggregation, artifact copying.
- `src/docfit/harness/**`: standards loading, coverage requirements, reports,
  issue clusters, and audit helpers.

Stage plane:

- `src/docfit/stages/template_parse/runner.py`
- `src/docfit/stages/content_extract/runner.py`
- `src/docfit/stages/placement/runner.py`
- `src/docfit/stages/render/runner.py`

Evidence and contract plane:

- `inputs/**`: raw school/student files and human review evidence.
- `standards/schools/**`: runnable signed standards only after cleanup.
- `standards/eval_profiles/**`: eval profile registry and expected harness
  evidence.
- `tests/**`: deterministic behavioral proof and private failure injection.
- `scripts/create_bootstrap_fixtures.py`: current bootstrap asset generator.

Human/agent surface:

- `README.md`: short current orientation.
- `SPEC.md`: canonical product semantics.
- `AGENTS.md` / `CLAUDE.md`: agent operational guidance.
- `docs/agents/**`: long runbooks.
- `docs/plans/**`: execution plans and completed cleanup history.

## Eng-Review Recommendation

Interactive `$plan-eng-review` questioning is unavailable in this Codex default
mode, so this applies the engineering review frame in prose.

Architecture fit:

- The strongest seam is an explicit eval profile/case registry plus a clear
  asset boundary. That makes later real-school work local instead of scattering
  paths and capability names across CLI, coverage, tests, scripts, and docs.
- Do not start by adding formatting capability. The next capability work should
  happen after school inputs, signed standards, gate status, and public commands
  have clean semantics.
- Do not keep compatibility wrappers for old file paths, duplicate specs, or
  public simulation switches. Update known in-repo consumers to the new shape.

Data flow after cleanup:

```text
inputs catalog
  -> eval profile / case registry
  -> standards loader
  -> template/content/placement/render runners
  -> report bundle
  -> deterministic gate status
```

Rejected alternatives:

- Delete real school packages: rejected, because product proof cannot depend
  only on `demo-school`.
- Leave future school README files inside `standards/schools/**`: rejected,
  because that makes evidence packages look runnable.
- Keep expected JSON in `inputs/`: rejected, because it mixes raw user/school
  inputs with harness-generated proof artifacts.
- Move bootstrap expected artifacts to `tests/fixtures`: rejected, because
  coverage eval is a product harness command, not only a pytest concern.
- Keep public `--simulate-*` switches for convenience: rejected, because they
  are test-only failure injection, not product surface.

## Discovery Rounds

### Round 0: Orientation And High-Noise Budget

Read:

- `README.md`
- `AGENTS.md`
- `SPEC.md`

Ran:

```bash
node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs" --examples 8
```

Findings:

- `docs/plans/**` has one completed bootstrap plan.
- `reports/**`, `out/**`, `.pytest_cache`, `.venv`, and `__pycache__` are
  ignored local/generated surfaces.
- `tests/**` is small enough to inspect around candidate seams.

### Round 1: Code And Public Contract Surface

Sampled:

- `src/docfit/cli/main.py`
- `src/docfit/convert/orchestrator.py`
- `src/docfit/harness/coverage.py`
- `src/docfit/harness/standards.py`
- `src/docfit/core/status.py`

Candidate evidence:

- Bootstrap paths, case ids, and capability names are repeated in CLI,
  coverage, tests, scripts, standards, and docs.
- Public CLI exposes failure simulation switches.
- `Status.NOT_RUN` is mixed into the same enum as public gate statuses.

### Round 2: Input, Standard, Golden, And Generator Boundary

Sampled:

- `inputs/README.md`
- `standards/schools/*/v1/README.md`
- `standards/schools/demo-school/v1/**`
- `scripts/create_bootstrap_fixtures.py`
- `docs/agents/bootstrap-eval-runbook.md`
- `docs/plans/bootstrap-verification-entropy-fixes.md`

Candidate evidence:

- Real school evidence packages are under `standards/schools/**` but are not
  runnable signed standards.
- `inputs/` contains expected fixture JSON, not only raw inputs and review
  evidence.
- The bootstrap generator can rewrite signed standards, contracts, goldens, and
  expected fixture JSON.

### Round 3: Saturation Sweep

Sampled:

```bash
rg -n "if .*school|school_id ==|demo-school|bootstrap-core|simulate_|NOT_RUN|golden|signed_standard|inputs/bootstrap-demo-(placement-plan|feature-snapshot)" \
  src tests scripts docs README.md AGENTS.md inputs standards SPEC.md
```

Result:

- No new P0/P1 direction appeared beyond the selected packet.
- Core stage runners do not currently contain broad school-specific branches.
- Local ignored residue is real but lower priority than the public contract and
  asset-boundary work.

## Recommended Packet

Candidate 1: Canonical eval profile/case registry

- Severity: P1
- Entropy source: repo surface layout, workflow drift
- Materiality: live source drift, recurring rediscovery
- Why now: bootstrap paths, capability vocabulary, and case ids are duplicated
  across CLI, coverage, tests, scripts, standards, and docs.
- Impact radius: repo-wide
- Maintainer test: a maintainer changing one bootstrap asset should not need to
  rediscover every hard-coded path and capability list.
- Affected paths: `src/docfit/harness/coverage.py`,
  `src/docfit/cli/main.py`, `scripts/create_bootstrap_fixtures.py`,
  `tests/**`, `standards/schools/demo-school/v1/**`, `docs/**`
- Owner skill: `$intuitive-refactor`
- Zen hint: one obvious source of truth.
- Pattern hint: small registry/factory; avoid broader framework ceremony.
- Suggested proof: stale hard-coded path search plus bootstrap eval matrix.
- Execution risk: needs approval because it touches public commands and tests.

Candidate 2: School standard boundary without deleting real schools

- Severity: P1
- Entropy source: repo surface layout, human docs
- Materiality: real workflow friction, false confidence
- Why now: real school directories under `standards/schools/**` are explicitly
  not runnable, while the loader treats missing `signed_standard.yaml` as
  `UNKNOWN`.
- Impact radius: workflow
- Maintainer test: a future agent must be able to tell which schools are source
  evidence and which are verified runnable standards.
- Affected paths: `inputs/README.md`, `standards/schools/hunannongye/v1`,
  `standards/schools/nannong-undergraduate/v1`,
  `standards/schools/pku-graduate/v1`, `src/docfit/harness/standards.py`,
  `SPEC.md`
- Owner skill: this skill + `$intuitive-doc`
- Zen hint: explicit current truth over directory implication.
- Pattern hint: no pattern; direct layout and catalog cleanup is clearer.
- Suggested proof: standards package listing, `docfit eval standards` behavior,
  and stale path search.
- Execution risk: needs approval because it moves/deletes directory surfaces.

Candidate 3: Bootstrap expected artifact boundary

- Severity: P1
- Entropy source: repo surface layout, tests
- Materiality: live source drift, real workflow friction, false confidence
- Why now: `inputs/` contains expected placement and feature snapshot JSON even
  though inputs should be raw documents and human evidence.
- Impact radius: workflow
- Maintainer test: reviewers should not confuse user-provided source documents
  with harness-generated expected artifacts.
- Affected paths: `inputs/bootstrap-demo-placement-plan.json`,
  `inputs/bootstrap-demo-feature-snapshot.json`,
  `standards/eval_profiles/bootstrap-core/expected/**`,
  `src/docfit/harness/coverage.py`, `tests/contract/test_contract_gates.py`,
  `scripts/create_bootstrap_fixtures.py`,
  `standards/schools/demo-school/v1/golden/feature_snapshot.json`,
  `SPEC.md`
- Owner skill: `$intuitive-tests` + `$intuitive-refactor`
- Zen hint: raw inputs are raw; expected evidence has its own home.
- Pattern hint: no pattern; direct fixture relocation and policy is clearer.
- Suggested proof: `rg` for old expected JSON paths, pytest, coverage eval.
- Execution risk: needs approval because it moves tracked fixture assets.

Candidate 4: Gate status versus run state

- Severity: P1
- Entropy source: architecture discovery
- Materiality: live source drift, false confidence
- Why now: repo invariants say gate states are only `PASS`, `FAIL`, and
  `UNKNOWN`, but `Status.NOT_RUN` is part of the shared status model.
- Impact radius: repo-wide
- Maintainer test: public reports should not expose internal lifecycle state as
  a possible gate result.
- Affected paths: `src/docfit/core/status.py`,
  `src/docfit/convert/orchestrator.py`, `tests/unit/test_status_and_audit.py`,
  `SPEC.md`
- Owner skill: `$intuitive-refactor`
- Zen hint: separate domain concepts instead of overloading one enum.
- Pattern hint: explicit state model; `GateStatus` plus `StageRunState`.
- Suggested proof: unit tests for status merge and report schema checks.
- Execution risk: needs approval because it changes public report semantics.

Candidate 5: Private failure simulation harness

- Severity: P1
- Entropy source: stale surface, tests
- Materiality: stale surface, false confidence
- Why now: `docfit eval` exposes `--simulate-*` switches that exist only to
  manufacture test failures.
- Impact radius: workflow
- Maintainer test: user-facing CLI help should describe product behavior, not
  test-only mutation hooks.
- Affected paths: `src/docfit/cli/main.py`,
  `src/docfit/convert/orchestrator.py`, stage runners with `simulate_*`,
  `tests/**`, `docs/agents/bootstrap-eval-runbook.md`
- Owner skill: `$intuitive-refactor` + `$intuitive-tests`
- Zen hint: public surface should be smaller than private test harness.
- Pattern hint: no pattern; test helpers or fixture builders are enough.
- Suggested proof: CLI help grep for `simulate`, pytest failure-path tests.
- Execution risk: needs approval because it removes public CLI options.

Candidate 6: Guard bootstrap generator

- Severity: P1
- Entropy source: workflow drift
- Materiality: false confidence, real workflow friction
- Why now: `scripts/create_bootstrap_fixtures.py` writes signed standard,
  contracts, goldens, and expected fixture JSON, while project invariants forbid
  automatic standard/golden updates.
- Impact radius: workflow
- Maintainer test: running a helper script should not silently rewrite reviewed
  evidence.
- Affected paths: `scripts/create_bootstrap_fixtures.py`,
  `standards/schools/demo-school/v1/**`, `inputs/**`
- Owner skill: `$intuitive-refactor`
- Zen hint: dangerous writes should be explicit.
- Pattern hint: builder with dry-run/output-dir default; no compatibility shim.
- Suggested proof: generator writes only to temp by default; overwrite path
  requires explicit flag and tests.
- Execution risk: safe if default behavior becomes non-mutating; otherwise needs
  approval before overwriting signed assets.

Candidate 7: Single canonical spec

- Severity: P1
- Entropy source: human docs
- Materiality: live source drift, recurring rediscovery
- Why now: `SPEC.md` and `DOCFIT_EVAL_HARNESS_FIRST_SPEC_CN.md` are identical
  2008-line files, and AGENTS tells future agents to treat `SPEC.md` as
  canonical.
- Impact radius: repo-wide
- Maintainer test: a product semantics update should have one canonical edit
  path.
- Affected paths: `SPEC.md`, `DOCFIT_EVAL_HARNESS_FIRST_SPEC_CN.md`,
  `AGENTS.md`, references in docs/tests if any.
- Owner skill: `$intuitive-doc`
- Zen hint: one canonical source.
- Pattern hint: no pattern; delete or replace duplicate with a short pointer.
- Suggested proof: `cmp`, stale filename search, doc command verification.
- Execution risk: needs approval because it deletes or replaces a large tracked
  doc.

Candidate 8: Dead/local surface pruning

- Severity: P2
- Entropy source: repo surface layout
- Materiality: stale surface, real workflow friction
- Why now: `src/docfit/contracts/__init__.py` is an empty unused package, while
  ignored local reports/out/pycache/.venv residue can dominate file listings.
- Impact radius: module
- Maintainer test: a future agent should not inspect empty packages or local
  generated residue while searching for live contract logic.
- Affected paths: `src/docfit/contracts/__init__.py`, ignored local outputs.
- Owner skill: this skill
- Zen hint: fewer dead doors.
- Pattern hint: no pattern; direct deletion/cleanup is clearer.
- Suggested proof: `rg docfit.contracts`, `git ls-files`, `git check-ignore`.
- Execution risk: safe for unused package after import search; local residue
  cleanup should avoid deleting tracked files.

## Suggested Execution Order

1. Asset and registry foundation: Candidates 1, 2, and 3.
2. Public contract cleanup: Candidates 4 and 5.
3. Standard/golden write safety: Candidate 6.
4. Human source-of-truth cleanup: Candidate 7.
5. Small dead-surface cleanup: Candidate 8, bundled with a nearby cleanup
   commit or done last.

This order makes later code changes less noisy: first define where facts live,
then simplify the public API and lifecycle model, then protect scripts and docs.

## Verification Ladder

Focused searches:

```bash
rg -n "bootstrap-demo-placement-plan|bootstrap-demo-feature-snapshot" .
rg -n "standards/schools/(hunannongye|nannong-undergraduate|pku-graduate)" .
test -d standards/eval_profiles/bootstrap-core/expected
rg -n "simulate-|simulate_" src tests docs
rg -n "NOT_RUN" src tests docs SPEC.md
rg -n "DOCFIT_EVAL_HARNESS_FIRST_SPEC_CN" .
rg -n "docfit\\.contracts|from docfit\\.contracts|import docfit\\.contracts" .
```

Baseline tests:

```bash
uv run pytest -q
```

Eval gates:

```bash
uv run docfit eval standards --school demo-school --out /tmp/docfit_standards
uv run docfit eval coverage --profile bootstrap-core --out /tmp/docfit_coverage
uv run docfit eval e2e --school demo-school \
  --student inputs/bootstrap-demo-student-pass.docx \
  --out /tmp/docfit_bootstrap_pass
uv run docfit eval content \
  --student inputs/bootstrap-demo-student-unsupported-textbox.docx \
  --out /tmp/docfit_bootstrap_unknown
```

After public simulation switches are removed, bootstrap FAIL proof should live
in pytest or private test helpers instead of CLI docs.

Real-school sanity checks:

```bash
uv run docfit eval standards --school hunannongye --out /tmp/docfit_hunannongye_standards
uv run docfit eval content --student inputs/real-student-001-source.docx --out /tmp/docfit_real_student_001_content
```

Expected near-term result: real-school standards remain `UNKNOWN` until one
real school is promoted to signed standard; real student content may remain
`UNKNOWN` for unsupported visible objects, but must not silently pass.

## Completion Standard

This plan is complete only when the repo can answer these questions from the
current file structure and deterministic commands, without tribal knowledge:

1. What files are raw school/student inputs?
2. What files are human review evidence?
3. What schools are runnable signed standards today?
4. What real schools exist only as source evidence for future standards?
5. What bootstrap cases and capability requirements define the current eval
   profile?
6. Which artifacts are signed/golden evidence versus generated/intermediate
   output?
7. Which statuses are public gate results versus internal stage lifecycle
   states?

The expected completed state:

- `inputs/` is a raw-input and human-evidence catalog, not a home for expected
  intermediate JSON.
- Bootstrap expected artifacts live under
  `standards/eval_profiles/bootstrap-core/expected/`, with all code, tests, and
  docs using that path.
- Runnable school standards have a signed standard and contracts. Real schools
  without signed standards remain discoverable in `inputs/README.md`, but do
  not have placeholder directories under `standards/schools/**`.
- Bootstrap profile facts have one code source of truth: profile id, required
  capabilities, case ids, and fixture paths.
- `SPEC.md` reflects the new asset boundary and no longer documents expected
  bootstrap JSON files under `inputs/`.
- Public CLI commands expose only product/eval behavior. Failure injection is
  private test infrastructure.
- Gate status is exactly `PASS`, `FAIL`, or `UNKNOWN`; internal not-run state
  cannot leak into public gate semantics.
- The bootstrap generator cannot rewrite signed standards or goldens by
  default.
- `SPEC.md` is the only long canonical product spec.

What we get after completion:

- A repo where future agents can see the main path in minutes instead of
  rediscovering which files are real inputs, fixtures, goldens, or generated
  outputs.
- A trustworthy answer to "which schools can we evaluate today?" and "which
  real schools are only waiting to be promoted into signed standards?"
- A smaller public CLI surface that matches the prototype product instead of
  exposing test-only switches.
- A safer standards/golden workflow where scripts do not silently mutate
  reviewed evidence.
- A clean runway for the next product slice: promote one real school, likely
  `hunannongye`, into the first real signed standard.

Non-goals for this plan:

- It does not make real-school conversion pass.
- It does not add image, formula, footnote, text box, or visual formatting
  capability.
- It does not update goldens to make failing output pass.
- It does not preserve old paths, duplicate docs, or public simulation switches
  for compatibility.

## Preflight Contract

Preflight status: DRAFT

Task source: plan path + docs grilling decisions.

Canonical source:
`docs/plans/school-standard-input-boundary-cleanup.md`

Route: durable `$intuitive-flow`

Goal: execute the school-standard/input-boundary cleanup so the repo has one
clear eval-harness path before feature work resumes.

Scope:

- Implement all accepted decisions in this plan.
- Move bootstrap expected JSON out of `inputs/` into
  `standards/eval_profiles/bootstrap-core/expected/`.
- Remove non-runnable real-school placeholder directories from
  `standards/schools/**`; keep real-school source status in `inputs/README.md`.
- Add one canonical bootstrap profile/case/capability registry and update CLI,
  coverage, tests, scripts, and docs.
- Split public gate status from internal not-run state.
- Remove public `--simulate-*` switches; keep failure injection private to
  tests/helpers.
- Guard bootstrap generator from rewriting signed standards/goldens by default.
- Collapse duplicate long spec so `SPEC.md` is canonical.
- Delete confirmed dead local/code surfaces such as unused `docfit.contracts`.

Non-goals:

- Making real-school conversion pass.
- Signing a real-school standard.
- Adding Word feature support.
- Preserving old paths or public simulation options.
- Updating goldens to make failures pass.

Context:

- Must read: this plan, `SPEC.md`, `AGENTS.md`, `README.md`,
  `inputs/README.md`, `src/docfit/cli/main.py`,
  `src/docfit/harness/coverage.py`, `src/docfit/harness/standards.py`,
  `src/docfit/core/status.py`, `src/docfit/convert/orchestrator.py`,
  `scripts/create_bootstrap_fixtures.py`, and `tests/**`.
- Useful: `docs/agents/bootstrap-eval-runbook.md` and
  `docs/plans/bootstrap-verification-entropy-fixes.md`.
- Avoid unless needed: `reports/**`, `out/**`, `.venv/**`,
  `.pytest_cache/**`, and `__pycache__/**`.

Acceptance:

- SUCCESS: repo structure/docs answer which files are raw inputs, human
  evidence, runnable standards, real-school source evidence, eval profile
  expected artifacts, and public gate statuses.
- SUCCESS: `inputs/` contains no expected intermediate JSON.
- SUCCESS: `standards/schools/**` contains only runnable signed standards.
- SUCCESS: `standards/eval_profiles/bootstrap-core/expected/` owns bootstrap
  expected artifacts.
- SUCCESS: public CLI help/search has no `simulate` switches.
- SUCCESS: public gate status is only `PASS` / `FAIL` / `UNKNOWN`; not-run is
  internal state.
- SUCCESS: `SPEC.md` matches the new asset boundary and duplicate long spec is
  removed or reduced to a pointer.
- BLOCKED_NEEDS_DECISION: none expected.
- BLOCKED_NEEDS_LOCAL_VALIDATION: none; all required gates are local
  deterministic CLI/test gates.
- INTERMEDIATE_ONLY: none unless explicitly requested.
- No regressions: bootstrap PASS/UNKNOWN behavior remains deterministic;
  real-school standards remain honestly `UNKNOWN` until signed.

Verification:

- Deterministic: `git diff --check`, `uv run pytest -q`, and focused tests
  around status, coverage, CLI, standards, and generator behavior.
- Integration:
  - `rg -n "bootstrap-demo-placement-plan|bootstrap-demo-feature-snapshot" .`
  - `rg -n "standards/schools/(hunannongye|nannong-undergraduate|pku-graduate)" .`
  - `test -d standards/eval_profiles/bootstrap-core/expected`
  - `rg -n "simulate-|simulate_" src tests docs`
  - `rg -n "NOT_RUN" src tests docs SPEC.md`
  - `rg -n "DOCFIT_EVAL_HARNESS_FIRST_SPEC_CN" .`
  - `rg -n "docfit\\.contracts|from docfit\\.contracts|import docfit\\.contracts" .`
- Product run:
  - `uv run docfit eval standards --school demo-school --out /tmp/docfit_standards`
  - `uv run docfit eval coverage --profile bootstrap-core --out /tmp/docfit_coverage`
  - `uv run docfit eval e2e --school demo-school --student inputs/bootstrap-demo-student-pass.docx --out /tmp/docfit_bootstrap_pass`
  - `uv run docfit eval content --student inputs/bootstrap-demo-student-unsupported-textbox.docx --out /tmp/docfit_bootstrap_unknown`
  - `uv run docfit eval standards --school hunannongye --out /tmp/docfit_hunannongye_standards`
- Local/live/manual: none.
- Optional:
  - `uv run docfit eval content --student inputs/real-student-001-source.docx --out /tmp/docfit_real_student_001_content`

Execution:

- Main: root supervisor owns sequencing, edits, verification, and final
  judgment.
- Worker: none by default.
- Worker goal: none.

To execute:

```text
/goal execute docs/plans/school-standard-input-boundary-cleanup.md with intuitive-flow
```

Approval: `LGTM`, `approve`, or `go ahead` approves; edits request revision.

## Stop Condition

The cleanup is complete when all of these are true:

- `inputs/` contains only raw school/student documents and human review
  evidence, not expected intermediate JSON.
- `standards/schools/**` contains only runnable signed standards; real-school
  source evidence is cataloged without pretending to be runnable.
- `standards/eval_profiles/bootstrap-core/expected/` owns bootstrap expected
  artifacts.
- Bootstrap profile/case/capability facts have one canonical registry.
- Public gate statuses are only `PASS`, `FAIL`, and `UNKNOWN`; internal
  not-run state is separate.
- Public CLI help no longer exposes failure simulation switches.
- Bootstrap generator cannot rewrite signed standards or goldens by default.
- `SPEC.md` is the only canonical long product spec.
- `SPEC.md` agrees with the new input/standard/expected artifact boundary.
- Baseline tests and eval gates in the verification ladder pass.
- Stale-path searches for moved/removed surfaces are empty or intentionally
  documented.

## Parked Items

- Ignored local residue (`reports/**`, `out/**`, `.pytest_cache`, `.venv`,
  `__pycache__`) can be cleaned locally, but it is not the main architecture
  work because `.gitignore` already excludes it.
- Existing completed plan `docs/plans/bootstrap-verification-entropy-fixes.md`
  has old fixture names in completion evidence. Update only if it remains a
  live runbook after the canonical docs cleanup.
- Advanced real-school conversion support is parked until one real-school
  signed standard is promoted.

## Materiality Gate

The candidate set passed the deterministic materiality gate:

```text
eligible_count: 8
rejected_count: 0
stop_recommended: false
```

The saturation sweep found no additional P0/P1 cleanup direction, so this plan
is a reasonable development direction for the next refactor batch.
