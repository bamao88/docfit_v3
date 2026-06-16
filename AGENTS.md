本仓库的讨论、计划、总结和最终回复默认使用中文；除非用户明确要求其他语言。

# AGENTS.md

DocFit v3 is an eval-harness-first DOCX conversion prototype. The product is
not "make a DOCX"; it is proving, with deterministic evidence, that conversion
satisfies signed contracts.

## Read First

- `README.md` for the short orientation and bootstrap command.
- `SPEC.md` for product semantics, stage boundaries, and gate rules.
- `docs/agents/**` for agent-only runbooks that are too long for this file.
- Relevant standards under `standards/schools/**` and tests under `tests/**`.

`SPEC.md` is the canonical long product spec.
`DOCFIT_EVAL_HARNESS_FIRST_SPEC_CN.md` is a short compatibility pointer only.

## Project Map

- `src/docfit/cli/`: Typer CLI and `docfit eval ...` entry points.
- `src/docfit/convert/`: orchestration across verified stages.
- `src/docfit/stages/`: template parse, content extract, placement, and render.
- `src/docfit/harness/`: status, standards, coverage, reports, issue clusters,
  and audit helpers.
- `standards/schools/**`: runnable signed standards, contracts, goldens, and
  exceptions only.
- `standards/eval_profiles/**`: eval profile expected artifacts.
- `inputs/**`: original DOCX/DOC inputs, student examples, and human review
  evidence.
- `reports/**` and `out/**`: generated evidence/output unless a task explicitly
  asks to preserve them.

## Core Invariants

- Gate states are only `PASS`, `FAIL`, and `UNKNOWN`; `UNKNOWN` is blocking.
- Preserve the visible content ledger from extraction through render.
- Silent drop of visible user content is always a blocking failure.
- `docfit convert` must not bypass stage verifiers.
- AI may help diagnose structured reports but must not decide pass/fail.
- Never auto-update goldens, signed standards, expected snapshots, or convert
  `FAIL`/`UNKNOWN` into success.
- Prefer generic capability fixes. School-specific behavior needs signed
  evidence, registry/config, and tests.
- Do not optimize architecture recommendations or refactors for backward
  compatibility unless a task explicitly asks for it. Prefer a clean current
  prototype contract over preserving migrated legacy surfaces.

## Commands

Install/sync:

```bash
uv sync
```

Baseline verification:

```bash
uv run pytest
uv run docfit eval e2e --school demo-school --student inputs/bootstrap-demo-student-pass.docx --out reports/bootstrap_pass
```

When changing contracts, verifiers, stages, standards, input assets, or CLI eval
behavior, run focused tests plus the relevant `docfit eval ...` command. Use
`docs/agents/bootstrap-eval-runbook.md` for the longer bootstrap matrix.

## Agent Workflow

- Keep root guidance small. Put long agent-only procedures in `docs/agents/**`;
  keep reusable mechanics in scripts or skills.
- Development autonomy rule: if a task can be completed by the agent with
  available repo context, local tools, or generated evidence, continue through
  implementation, verification, documentation alignment, and commit before
  stopping. Stop for the user only when the next action genuinely requires
  user-owned review, product judgment, credentials, external materials, or
  unavailable local capability. When stopping, state exactly what the user must
  do, why it is user-owned, and what it unblocks.
- Before broad or vague work, use `$intuitive-preflight`; for ordinary scoped
  build/change work, use `$intuitive-flow`.
- Use `$intuitive-doc` for human-facing documentation drift, `$intuitive-tests`
  for test-suite structure, `$intuitive-refactor` before broad refactors, and
  `$intuitive-reduce-entropy` for periodic cleanup.
- Target-repo LSP config lives in `pyrightconfig.json`; agent-facing Serena/MCP
  setup is documented in `docs/agents/lsp-and-mcp.md`.
