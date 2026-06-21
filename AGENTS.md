本仓库的讨论、计划、总结和最终回复默认使用中文；除非用户明确要求其他语言。

# AGENTS.md

DocFit v3 is an eval-harness-first DOCX conversion prototype. The product is
not "make a DOCX"; it is proving, with deterministic evidence, that conversion
satisfies signed contracts.

## 写作约定

- 回消息、写计划、写总结和写文档时，优先使用普通产品语言，
  直接说明“这个文件做什么、在检查什么、失败说明什么、下一步要改哪类问题”。
- 默认先给一句人能看懂的结论，再给证据、文件、命令、验证结果和剩余未知。
  不要只说“已修改”“已优化”“已修复”；必须说明改了什么、行为变化是什么、
  用什么证明、还有什么没有证明。
- 解释系统、bug、流程或改动时，明确区分“当前真实实现”“已有设计意图”
  “建议方案”“当前假设”和 `UNKNOWN`。不能把设计、猜测或计划当成当前实现来讲。
- 先判断用户要的是只读审计、开发前对齐、实施计划、实际执行、调试还是 review。
  用户明确说“做、修、合并、整理、执行”时直接推进；用户是在问“现在到底是什么、
  有没有真的做、问题在哪、我看不懂”时，先只读审计并列证据，不要直接重构。
- 排查多步骤流程时，优先找问题第一次出现在哪一步，说明 `first_bad_stage`、
  应该改哪里、不应该改哪里，以及最小下一步。不要看到最终输出不对就直接改最终输出。
- 比较状态、字段、流程、文件、风险、验证结果时，优先用表格。用户说看不懂时，
  切换成 PM 可读格式：一句话结论、当前真实情况、问题第一次出现在哪一步、证据、
  下一步应该改哪里、不应该改哪里、还不知道什么。
- 交付任何执行结果时，给出 change proof：修改文件、行为变化、验证命令和结果、
  剩余 `UNKNOWN`。如果没有运行验证，必须说明原因和风险，不能说成已经通过。
- 新增或修改字段、JSON 形状、报告字段、阶段产物前，先说明字段含义、生产者、
  消费者、是否影响 `PASS` / `FAIL` / `UNKNOWN`、缺失时怎么办，以及是否允许 AI 编辑。
- 不要用名词堆叠代替解释。避免把 `exposure`、`finding`、`contract`、
  `verifier`、`strategy contract`、`stage contract` 这类词当成默认表达。
- 标题、文件名、状态页和下一步目标也要说清楚具体用途，不要只写专有名词。
- 如果这些词是代码、文件名、命令输出或既有产品概念的一部分，可以保留原名，
  但必须先用中文说明它的实际用途和对应的具体检查。

## Read First

- `README.md` for the short orientation and bootstrap command.
- `SPEC.md` for product semantics, stage boundaries, and gate rules.
- `docs/human/template-generation-artifact-field-dictionary.md` before changing
  template-generation artifact fields, JSON shapes, manifests, gap reports, or
  producer/consumer wiring. First define the field meaning, producer, consumer,
  gate effect, missing-field result, default rule, and AI edit boundary. Do not
  add undocumented fields, guess defaults for signed meaning, or use
  `template_artifact` / `template_generation_manifest` as proof of what
  `generated_template.docx` actually contains.
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
