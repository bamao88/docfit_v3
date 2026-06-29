from __future__ import annotations

from docfit.template_generation.agent.schema import validate_layered_submission

from .helpers import layered_submission, packet


def test_schema_accepts_layered_submission() -> None:
    render_packet = packet()
    submission = layered_submission(
        render_packet["source_render_hash"],
        layers={
            "t2": {
                "unit_candidates": [
                    {
                        "proposal_id": "p1",
                        "kind": "unit_candidate",
                        "operation": "add_unit",
                        "unit_id": "integrity_statement",
                        "source_seq_refs": [2],
                    }
                ]
            }
        },
    )

    result = validate_layered_submission(
        submission,
        expected_source_render_hash=render_packet["source_render_hash"],
    )

    assert result["valid"] is True


def test_schema_rejects_missing_proposal_id() -> None:
    render_packet = packet()
    submission = layered_submission(
        render_packet["source_render_hash"],
        layers={
            "t3": {
                "element_policy_candidates": [
                    {
                        "kind": "element_policy_candidate",
                        "policy": "fill",
                        "source_seq_refs": [3],
                    }
                ]
            }
        },
    )

    result = validate_layered_submission(
        submission,
        expected_source_render_hash=render_packet["source_render_hash"],
    )

    assert result["valid"] is False
    assert any(error["path"].endswith(".proposal_id") for error in result["errors"])


def test_schema_rejects_one_shot_hash_mismatch() -> None:
    submission = layered_submission("sha256:other", layers={})

    result = validate_layered_submission(
        submission,
        expected_source_render_hash="sha256:test",
    )

    assert result["valid"] is False
    assert any(error["path"] == "$.source_render_hash" for error in result["errors"])
