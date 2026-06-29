from __future__ import annotations

from docfit.template_generation.agent.attribution import (
    build_agent_attribution,
    build_agent_decisions,
    build_agent_t2_overlay,
    build_agent_t3_overlay,
    build_agent_t4_hints,
)
from docfit.template_generation.agent.comparison import build_submission_comparison
from docfit.template_generation.agent.manual_review import build_agent_manual_review_items

from .helpers import round0_artifacts


def test_manual_review_collects_open_questions_comparison_and_validation_failures(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    transcript = {
        "artifact_type": "template_agent_transcript",
        "rounds": [
            {
                "submission": {
                    "round_id": "round_001",
                    "layers": {
                        "t2": {
                            "open_questions": [
                                {
                                    "question_id": "oq_t2_001",
                                    "blocking_level": "blocking",
                                    "question": "需要人工确认 source_seq 2 是否承诺书。",
                                    "affected_refs": {"source_seq_refs": [2]},
                                }
                            ]
                        }
                    },
                }
            }
        ],
    }
    comparison = build_submission_comparison(
        [
            {
                "proposal_id": "t2_conflict_001",
                "round_id": "round_001",
                "layer": "t2",
                "collection": "unit_candidates",
                "status": "conflict",
                "check_id": "C-COMPARISON-CONFLICT",
                "reason": "AI and deterministic ownership conflict",
                "manual_review_required": True,
                "can_auto_execute": False,
                "affected_refs": {"source_seq_refs": [2]},
                "ai": {"unit_id": "integrity_statement"},
                "deterministic": {"source_seq_owners": {"2": "body_main"}},
            }
        ],
        packet=artifacts["packet"],
        deterministic_structure=artifacts["structure_candidates"],
    )
    decisions = build_agent_decisions(
        [
            {
                "proposal_id": "schema_error_001",
                "round_id": "round_001",
                "decision": "rejected",
                "checks": [
                    {
                        "check_id": "C-SCHEMA",
                        "status": "FAIL",
                        "reason": "proposal_id is required",
                    }
                ],
                "target_path": "$.layers.t2.unit_candidates[0].proposal_id",
                "before_hash": None,
                "after_hash": None,
                "reason": "proposal_id is required",
            }
        ]
    )

    manual = build_agent_manual_review_items(
        transcript=transcript,
        comparison=comparison,
        decisions=decisions,
    )

    assert manual["artifact_type"] == "template_agent_manual_review_items"
    assert manual["summary"]["blocking"] == 3
    assert {
        item["source"] for item in manual["items"]
    } == {"open_question", "comparison", "validation_failure"}
    assert "mr_open_question_oq_t2_001" in manual["blocking_item_ids"]


def test_attribution_includes_comparison_and_manual_review_summary(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    decisions = build_agent_decisions([])
    comparison = build_submission_comparison(
        [],
        packet=artifacts["packet"],
        deterministic_structure=artifacts["structure_candidates"],
    )
    manual = build_agent_manual_review_items(
        transcript={"rounds": []},
        comparison=comparison,
        decisions=decisions,
    )

    attribution = build_agent_attribution(
        transcript={"rounds": []},
        decisions=decisions,
        round0_unit_map=artifacts["unit_map"],
        post_agent_unit_map=artifacts["unit_map"],
        round0_element_spec=artifacts["element_spec"],
        post_agent_element_spec=artifacts["element_spec"],
        t2_overlay=build_agent_t2_overlay([]),
        t3_overlay=build_agent_t3_overlay([]),
        t4_hints=build_agent_t4_hints([]),
        submission_comparison=comparison,
        manual_review_items=manual,
    )

    assert attribution["comparison_summary"]["total"] == 0
    assert attribution["manual_review"]["required"] is False
