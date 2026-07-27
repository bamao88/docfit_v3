# Unit Pagination Consumption

status: PARKED

source_plan: `docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-11-unit-pagination-alignment.md`

latest_user_intent: Apply the downstream T5/T6 pagination principle: preserve T2 policy, execute only non-invasive Word pagination controls, and do not compress styles to force one-page layout.

current_slice: T2 gold、T2 prompt、AI observation/materialize/bridge/overlay、structure candidates、`02_unit_map.yaml`、T5 `template_spec` 和 T6 planning 均已迁移到 `page_policy.start/scope`。旧 `page_break/page_isolation/allow_multi_page/keep_together` 只保留在源 Word 机械事实、最终 Word 质量检查和 T6 具体动作/OOXML 效果中，不再作为 T2/T5 契约字段。

completed_slice_batch:

- Removed old `expected.units[].page` blocks from the three signed T2 standards; T2 gold now uses `expected.units[].page_policy` only.
- Changed T2 standard audit to read only `page_policy.start/scope`; legacy `expected.units[].page` fallback was removed.
- Changed T2 `unit_map` public output to omit old `page` and `page_start`; `02_unit_map.yaml` now exposes `units[].page_policy` for T2 pagination semantics.
- Updated AI unit accuracy and T5 preservation checks to compare `page_policy` instead of old page fields.
- 收窄 canonical page policy 模块，只保留 `page_policy.start/scope` 的归一化、形状校验和等价比较。
- Added T2 standard page mismatch audit, T2/T5/T6 verifier checks, T6 page policy results, and manifest provenance.
- Routed T2 AI page-only decisions through `page_policy_candidates` into overlay/regenerate，全链只传递 `page_policy.start/scope`。
- Switched T6 pagination planning to `template_spec.units[].page_policy` and map semantic labels directly to page-boundary and keep-together Word actions.
- Removed legacy pagination fields from the T2 prompt, materialized observations, bridge proposals, overlays, structure candidates, T5 template spec, and T6 policy results.
- Added route-eval page policy accuracy for T2 AI observation while keeping T4 out of unit pagination ownership.
- Added an injected T2-style page policy proof that bypasses incomplete real T2 inference and verifies T5 preservation, T6 action planning/execution, manifest page results, and final DOCX OOXML effects.
- Hardened T5 document-start normalization so only the first unit is treated as `document_start`; non-first `order<=10` units are no longer promoted.
- Hardened T6 boundary planning so a next-page section break dedupes and satisfies the same unit boundary as a page break.
- Changed T6 keep-together execution to non-invasive Word controls only: `keepLines`, intra-unit `keepNext`, and table-row `cantSplit`; T6 does not change font, spacing, margins, or row heights to force one-page layout.
- Upgraded T6 DOCX effect observation/verifier from count-only checks to action `output_ref` checks for page breaks, section breaks, keep refs, and table `cantSplit`.

last_proven_evidence:

- `uv run pytest -q tests/unit/test_t2_standard.py tests/unit/test_t2_unit_map.py tests/unit/test_template_generation_artifacts.py tests/unit/test_template_generation_stage_verifiers.py tests/unit/template_generation_agent/test_agent_observation_materialize.py tests/unit/template_generation_agent/test_agent_observation_eval.py` -> 96 passed.
- `uv run pytest -q tests/contract/test_template_generation_standard_judge.py tests/contract/test_real_core_baseline_harness.py` -> 8 passed.
- `uv run pytest -q tests/unit/template_generation_agent` -> 165 passed.
- Targeted scan: signed T2 gold has no `expected.units[].page`; sample `unit_map` units contain `page_policy` and do not contain `page` or `page_start`.
- `uv run pytest -q tests/unit/template_generation_agent/test_agent_observation_eval.py tests/unit/test_t2_unit_map.py tests/unit/test_t2_standard.py tests/unit/test_template_generation_artifacts.py tests/unit/template_generation_agent/test_agent_observation_materialize.py tests/unit/template_generation_agent/test_agent_observation_bridge.py tests/unit/template_generation_agent/test_agent_t2_overlay.py tests/unit/template_generation_agent/test_agent_observation_pipeline.py tests/contract/test_template_generate.py tests/contract/test_template_generation_standard_judge.py` -> 116 passed.
- `uv run pytest -q tests/unit/template_generation_agent/test_agent_observation_eval.py tests/unit/test_t2_unit_map.py tests/unit/test_t2_standard.py tests/unit/test_template_generation_artifacts.py tests/unit/template_generation_agent/test_agent_observation_materialize.py tests/unit/template_generation_agent/test_agent_observation_bridge.py` -> 77 passed.
- `uv run pytest -q tests/unit/template_generation_agent/test_agent_t2_overlay.py tests/unit/template_generation_agent/test_agent_observation_pipeline.py tests/contract/test_template_generate.py tests/contract/test_template_generation_standard_judge.py` -> 39 passed.
- `uv run python -m compileall -q src/docfit/template_generation src/docfit/harness/template_generation_judge_reports.py` -> passed.
- `/tmp/docfit-t2-pagination-impl-20260717-hunannongye`: 16 T2 units, zero empty page objects, 16 manifest `page_policy_results`.
- `/tmp/docfit-t2-pagination-impl-20260717-hunannongye-judge-r2`: `t2_unit_pagination=FAIL` with `t2_page_policy_mismatch`, replacing the prior false PASS.
- `/tmp/docfit-t2-pagination-impl-20260718-nannong-undergraduate`: 11 T2 units, zero empty page objects, zero T5 empty page objects, 11 manifest `page_policy_results` (`6 executed`, `5 manual_review`); judge first bad stage remains T2 with `t2_page_policy_mismatch`.
- `/tmp/docfit-t2-pagination-impl-20260718-pku-graduate`: 12 T2 units, zero empty page objects, zero T5 empty page objects, 12 manifest `page_policy_results` (`10 executed`, `2 manual_review`); judge first bad stage remains T2 with `t2_page_policy_mismatch`.
- Final Word OOXML/gap checks:
  - `/tmp/docfit-t2-pagination-impl-20260718-hunannongye-template-gap`: FAIL + UNKNOWN; page-related checks include PASS/FAIL/UNKNOWN, proving final Word layer is evaluable but school policy is not satisfied.
  - `/tmp/docfit-t2-pagination-impl-20260718-nannong-undergraduate-template-gap`: FAIL + UNKNOWN; page-related checks include 35 PASS, 3 FAIL, 4 UNKNOWN.
  - `/tmp/docfit-t2-pagination-impl-20260718-pku-graduate-template-gap`: FAIL + UNKNOWN; page-related checks include 10 PASS, 18 FAIL, 3 UNKNOWN.
- `uv run pytest -q tests/unit/test_template_generation_artifacts.py::test_injected_t2_page_policy_drives_t5_t6_manifest_and_docx_effects` -> passed; injected `cover/toc/abstract_cn/body_main` page policy produced page break, section break, keep-together, manifest `page_policy_results`, and observable DOCX layout effects.
- `uv run pytest -q tests/unit/test_template_generation_artifacts.py tests/unit/test_t2_unit_map.py tests/contract/test_template_generate.py tests/contract/test_template_generation_standard_judge.py` -> 55 passed.
- `uv run pytest -q tests/unit/test_t2_unit_map.py tests/unit/test_template_generation_artifacts.py tests/unit/test_template_generation_stage_verifiers.py tests/contract/test_template_generation_standard_judge.py tests/contract/test_template_generate.py` -> 78 passed.
- `uv run python -m compileall -q src/docfit/template_generation tests/unit/test_template_generation_artifacts.py` -> passed.

next_action: Refresh the three-school offline template-generation proof and verify generated T2/T5 artifacts remain `page_policy`-only while T6 actions and final OOXML effects remain observable.

next_proof: Three-school `template-generate` + `template-generation-judge` + template-gap final Word checks showing T2 `unit_map` stays `page_policy`-only while T5/T6 still execute required page/section/keep actions through their own execution contract; live T2 API route only with explicit authorization.

stop_condition: Stop before live API proof unless credentials/cost authorization is explicitly provided.

no_touch_scope: Do not revert or format unrelated dirty worktree changes; do not migrate non-pagination `generation_model` dependencies.

parked_work:

- T6 still necessarily exposes concrete Word action/effect names such as page break, section break, and keep-together; these are execution evidence, not T2/T5 policy fields.
- Live T2 API proof requires explicit credentials/cost authorization.
- Full removal of T6 non-pagination `generation_model` dependencies remains in the full-chain plan.
- Current offline path still yields `unknown` for non-mechanical page semantics; downstream now consumes and executes supplied policy more safely, but the real T2 strategy producer remains a separate capability gap.
