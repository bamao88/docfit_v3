from __future__ import annotations

from docfit.template_generation.agent.comparison import (
    build_submission_comparison,
    compare_proposal,
)

from .helpers import round0_artifacts


def test_comparison_t2_add_unit_from_body_main_is_missing_and_executable(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)

    item = compare_proposal(
        structure_candidates=artifacts["structure_candidates"],
        packet=artifacts["packet"],
        layer="t2",
        collection="unit_candidates",
        proposal={
            "proposal_id": "t2_add_001",
            "kind": "unit_candidate",
            "operation": "add_unit",
            "unit_id": "integrity_statement",
            "source_seq_refs": [2],
        },
    )

    assert item["status"] == "missing"
    assert item["can_auto_execute"] is True
    assert item["manual_review_required"] is False
    assert item["deterministic"]["source_seq_owners"] == {"2": "body_main"}


def test_comparison_t2_add_unit_spanning_multiple_units_requires_manual_review(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)

    item = compare_proposal(
        structure_candidates=artifacts["structure_candidates"],
        packet=artifacts["packet"],
        layer="t2",
        collection="unit_candidates",
        proposal={
            "proposal_id": "t2_cross_001",
            "kind": "unit_candidate",
            "operation": "add_unit",
            "unit_id": "bad_cross_unit",
            "source_seq_refs": [1, 2],
        },
    )

    assert item["status"] == "conflict"
    assert item["can_auto_execute"] is False
    assert item["manual_review_required"] is True
    assert item["check_id"] == "C-COMPARISON-CONFLICT"
    assert "multiple existing units" in item["reason"]


def test_comparison_rejects_removed_t3_layer(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)

    item = compare_proposal(
        structure_candidates=artifacts["structure_candidates"],
        packet=artifacts["packet"],
        layer="t3",
        collection="element_policy_candidates",
        proposal={
            "proposal_id": "t3_remove_001",
            "kind": "element_policy_candidate",
            "policy": "remove",
            "source_seq_refs": [3],
        },
    )

    assert item["status"] == "unknown"
    assert item["check_id"] == "C-SCHEMA"
    assert item["manual_review_required"] is True


def test_build_submission_comparison_counts_manual_and_auto_items(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    auto_item = compare_proposal(
        structure_candidates=artifacts["structure_candidates"],
        packet=artifacts["packet"],
        layer="t2",
        collection="unit_candidates",
        proposal={
            "proposal_id": "t2_add_001",
            "kind": "unit_candidate",
            "operation": "add_unit",
            "unit_id": "integrity_statement",
            "source_seq_refs": [2],
        },
    )
    manual_item = compare_proposal(
        structure_candidates=artifacts["structure_candidates"],
        packet=artifacts["packet"],
        layer="t2",
        collection="unit_candidates",
        proposal={
            "proposal_id": "t2_cross_001",
            "kind": "unit_candidate",
            "operation": "add_unit",
            "unit_id": "bad_cross_unit",
            "source_seq_refs": [1, 2],
        },
    )

    comparison = build_submission_comparison(
        [auto_item, manual_item],
        packet=artifacts["packet"],
        deterministic_structure=artifacts["structure_candidates"],
    )

    assert comparison["artifact_type"] == "template_agent_submission_comparison"
    assert comparison["summary"]["auto_executable"] == 1
    assert comparison["summary"]["manual_review_required"] == 1
    assert comparison["items"][0]["comparison_id"] == "cmp_t2_add_001"
