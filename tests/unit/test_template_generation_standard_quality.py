from __future__ import annotations

from pathlib import Path

from docfit.harness.template_generation_standard_quality import (
    TEMPLATE_GENERATION_STAGE_KEYS,
    evaluate_template_generation_standard_quality,
    evaluate_template_generation_standard_quality_for_profile,
    load_template_generation_standard_set,
)


ROOT = Path(__file__).resolve().parents[2]

EXPECTED_T3_CORE_ACTION_MAP = {
    "fixed": "keep",
    "template_default": "keep",
    "template_default_optional": "keep",
    "fill": "fill",
    "generated": "fill",
    "instruction_remove": "delete",
    "remove_instruction": "delete",
}

EXPECTED_T3_DELEGATED_REVIEW_COUNTS = {
    "hunannongye": {
        "candidate_runs": 76,
        "reviewed_rows": 121,
        "mixed_runs": 12,
        "span_rows": 52,
    },
    "nannong-undergraduate": {
        "candidate_runs": 50,
        "reviewed_rows": 75,
        "mixed_runs": 3,
        "span_rows": 28,
    },
    "pku-graduate": {
        "candidate_runs": 37,
        "reviewed_rows": 41,
        "mixed_runs": 3,
        "span_rows": 7,
    },
}


def test_standard_quality_loads_three_school_stage_standards() -> None:
    for school_id in ["hunannongye", "nannong-undergraduate", "pku-graduate"]:
        standard_set = load_template_generation_standard_set(ROOT, school_id)
        report = evaluate_template_generation_standard_quality(standard_set)

        assert report.status.value == "UNKNOWN"
        assert set(standard_set.stages) == set(TEMPLATE_GENERATION_STAGE_KEYS)
        assert {finding.type for finding in report.findings} == {
            "t3_gold_not_verified",
            "t3_gold_review_metadata_incomplete",
        }
        assert report.stage_statuses["t3_element_policy"] == "UNKNOWN"
        assert all(
            status == "PASS"
            for stage, status in report.stage_statuses.items()
            if stage != "t3_element_policy"
        )
        final_element_count = sum(
            len(unit.get("elements", []))
            for unit in standard_set.final_template["expected"]["units"]
        )
        t3_expected = standard_set.stages["t3_element_policy"].expected
        t3_standard = standard_set.stages["t3_element_policy"].raw
        assert t3_standard["gold_status"] == "PARTIAL"
        assert (
            t3_standard["gold_contract_version"]
            == "t3-adaptive-run-span-gold-1.0"
        )
        core_action_contract = t3_expected["core_action_contract"]
        assert core_action_contract == {
            "primary_metric": "exact_action_accuracy",
            "scored_ledger": "run_span_ledger",
            "gold_granularity": "adaptive_run_or_span",
            "gold_source_field": "expected_action",
            "owned_structure_layers": ["body_flow"],
            "allowed_actions": ["keep", "fill", "delete"],
            "policy_to_action": EXPECTED_T3_CORE_ACTION_MAP,
            "grouping_invariant": True,
            "subtype_policy_accuracy": "out_of_scope",
            "unknown_action": "unknown",
            "unknown_scoring": "excluded_from_primary",
            "unknown_execution_fallback": "keep",
            "uncertain_delete_forbidden": True,
        }
        assert len(t3_expected["element_expectations"]) == final_element_count
        assert len(t3_expected["run_span_ledger"]) >= final_element_count
        assert {
            item["expected_action"] for item in t3_expected["run_span_ledger"]
        } == {"keep", "fill", "delete"}
        assert "pending_span_review" not in t3_expected
        delegated_review = t3_standard["delegated_review_metadata"]
        review_counts = EXPECTED_T3_DELEGATED_REVIEW_COUNTS[school_id]
        assert (
            delegated_review["reviewed_candidate_run_count"]
            == review_counts["candidate_runs"]
        )
        assert delegated_review["human_confirmation_state"] == "pending"
        assert delegated_review["verified_promotion_allowed"] is False
        reviewed_rows = [
            item
            for item in t3_expected["run_span_ledger"]
            if item.get("delegated_review_state")
        ]
        assert len(reviewed_rows) == review_counts["reviewed_rows"]
        assert all(
            item["target_kind"] in {"run", "span"}
            and isinstance(item["text"], str)
            for item in t3_expected["run_span_ledger"]
        )
        span_rows = [
            item
            for item in t3_expected["run_span_ledger"]
            if item["target_kind"] == "span"
        ]
        assert len(span_rows) == review_counts["span_rows"]
        assert len({item["raw_run_id"] for item in span_rows}) == review_counts[
            "mixed_runs"
        ]
        assert all(
            isinstance(item["start"], int)
            and isinstance(item["end"], int)
            and item["start"] < item["end"]
            for item in span_rows
        )
        assert standard_set.source_template_docx_sha256
        assert all(
            str(stage.path).endswith(f"template_generation/{stage.stage_key}.standard.yaml")
            for stage in standard_set.stages.values()
        )


def test_standard_quality_profile_aggregates_real_core_targets() -> None:
    report = evaluate_template_generation_standard_quality_for_profile(
        ROOT,
        "real-core-v0",
    )

    target_ids = {target["school_id"] for target in report.target_reports}
    assert {"hunannongye", "nannong-undergraduate", "pku-graduate"} <= target_ids
    assert report.status.value == "UNKNOWN"
    assert {finding.type for finding in report.findings} == {
        "t3_gold_not_verified",
        "t3_gold_review_metadata_incomplete",
    }
