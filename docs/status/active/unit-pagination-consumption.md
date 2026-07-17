# Unit Pagination Consumption

status: PARKED

source_plan: `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-11-unit-pagination-alignment.md`

latest_user_intent: Implement Plan 11 after approval.

current_slice: Code implementation is in `implemented_in_part`; parked on broader real-sample/live verification.

completed_slice_batch:

- Added canonical `units[].page` helpers and T2 production of explicit unknown page policy.
- Added T2 standard page mismatch audit, T2/T5/T6 verifier checks, T6 page policy results, and manifest provenance.
- Routed T2 AI page-only decisions through `page_policy_candidates` into overlay/regenerate.
- Switched T6 pagination planning to `template_spec.units[].page` for page break, page isolation, and keep-together best-effort actions.
- Added route-eval page policy accuracy for T2 AI observation while keeping T4 out of unit pagination ownership.

last_proven_evidence:

- `uv run pytest -q tests/unit/template_generation_agent/test_agent_observation_eval.py tests/unit/test_t2_unit_map.py tests/unit/test_t2_standard.py tests/unit/test_template_generation_artifacts.py tests/unit/template_generation_agent/test_agent_observation_materialize.py tests/unit/template_generation_agent/test_agent_observation_bridge.py tests/unit/template_generation_agent/test_agent_t2_overlay.py tests/unit/template_generation_agent/test_agent_observation_pipeline.py tests/contract/test_template_generate.py tests/contract/test_template_generation_standard_judge.py` -> 116 passed.
- `uv run pytest -q tests/unit/template_generation_agent/test_agent_observation_eval.py tests/unit/test_t2_unit_map.py tests/unit/test_t2_standard.py tests/unit/test_template_generation_artifacts.py tests/unit/template_generation_agent/test_agent_observation_materialize.py tests/unit/template_generation_agent/test_agent_observation_bridge.py` -> 77 passed.
- `uv run pytest -q tests/unit/template_generation_agent/test_agent_t2_overlay.py tests/unit/template_generation_agent/test_agent_observation_pipeline.py tests/contract/test_template_generate.py tests/contract/test_template_generation_standard_judge.py` -> 39 passed.
- `uv run python -m compileall -q src/docfit/template_generation src/docfit/harness/template_generation_judge_reports.py` -> passed.
- `/tmp/docfit-t2-pagination-impl-20260717-hunannongye`: 16 T2 units, zero empty page objects, 16 manifest `page_policy_results`.
- `/tmp/docfit-t2-pagination-impl-20260717-hunannongye-judge-r2`: `t2_unit_pagination=FAIL` with `t2_page_policy_mismatch`, replacing the prior false PASS.

next_action: Run remaining real samples (`nannong-undergraduate`, `pku-graduate`) and final Word OOXML/render checks, then update Plan 11 from `implemented_in_part` only if all completion signals pass.

next_proof: Three-school `template-generate` + `template-generation-judge`, final Word page/keep OOXML checks, and live T2 API route only with explicit authorization.

stop_condition: Stop before live API proof unless credentials/cost authorization is explicitly provided.

no_touch_scope: Do not revert or format unrelated dirty worktree changes; do not migrate non-pagination `generation_model` dependencies.

parked_work:

- Live T2 API proof requires explicit credentials/cost authorization.
- Full removal of T6 non-pagination `generation_model` dependencies remains in the full-chain plan.
- Current offline path still yields page unknowns where neither mechanical nor AI evidence proves school-specific policy.
