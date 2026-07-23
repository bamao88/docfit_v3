from __future__ import annotations

from docfit.template_generation.agent.ai_primary import (
    materialize_ai_primary_t3_structure,
)


def test_ai_primary_replaces_code_policies_and_safely_keeps_invalid_claims() -> None:
    structure = {
        "source_context": {
            "runs_by_raw_run_id": {
                "r1": {"text": "说明", "logical_run_id": "lr1", "source_ref": "p1"},
                "r2": {"text": "姓名", "logical_run_id": "lr2", "source_ref": "p1"},
                "r3": {"text": "删除", "logical_run_id": "lr3", "source_ref": "p1"},
            }
        },
        "units": [
            {
                "unit_id": "body_main",
                "elements": [
                    {
                        "element_id": "e1",
                        "order": 1,
                        "candidate_policy": "fill",
                        "fill_source": "code_value",
                        "source_seq_refs": [1],
                        "raw_run_ids": ["r1", "r2", "r3"],
                    }
                ],
            }
        ],
    }
    observation = {
        "items": [
            {
                "raw_run_ids": ["r1"],
                "policy": "fill",
                "decision_status": "manual_review",
                "resolution": "fallback",
                "ai_rationale": "invalid fill falls back to keep",
            },
            {
                "raw_run_ids": ["r2"],
                "policy": "fill",
                "fill_source": "student_content",
                "fill_field": "student_name",
                "decision_status": "accepted",
                "resolution": "direct",
            },
            {
                "raw_run_ids": ["r3"],
                "policy": "instruction_remove",
                "removal_reason": "format annotation",
                "decision_status": "accepted",
                "resolution": "direct",
            },
        ]
    }

    materialized, operation = materialize_ai_primary_t3_structure(
        structure,
        observation,
    )

    elements = materialized["units"][0]["elements"]
    assert [element["candidate_policy"] for element in elements] == [
        "fixed",
        "fill",
        "remove_instruction",
    ]
    assert elements[0].get("fill_source") is None
    assert elements[0]["agent_traces"][-1]["safe_fallback"] is True
    assert elements[1]["fill_source"] == "student_content"
    assert elements[1]["fill_field"] == "student_name"
    assert elements[2]["removal_reason"] == "format annotation"
    assert operation["merge_enabled"] is False
    assert operation["claimed_raw_run_count"] == 3
    assert operation["matched_raw_run_count"] == 3
    assert operation["missing_claim_raw_run_ids"] == []


def test_ai_primary_conflicting_claims_resolve_to_keep() -> None:
    structure = {
        "source_context": {
            "runs_by_raw_run_id": {
                "r1": {"text": "内容", "logical_run_id": "lr1", "source_ref": "p1"}
            }
        },
        "units": [
            {
                "unit_id": "body_main",
                "elements": [
                    {
                        "element_id": "e1",
                        "candidate_policy": "fill",
                        "raw_run_ids": ["r1"],
                    }
                ],
            }
        ],
    }
    observation = {
        "items": [
            {
                "raw_run_ids": ["r1"],
                "policy": "fill",
                "decision_status": "accepted",
                "resolution": "direct",
            },
            {
                "raw_run_ids": ["r1"],
                "policy": "instruction_remove",
                "decision_status": "accepted",
                "resolution": "direct",
            },
        ]
    }

    materialized, operation = materialize_ai_primary_t3_structure(
        structure,
        observation,
    )

    assert materialized["units"][0]["elements"][0]["candidate_policy"] == "fixed"
    assert operation["conflicting_raw_run_ids"] == ["r1"]
