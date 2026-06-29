from __future__ import annotations

from pathlib import Path

from docfit.template_generation.agent.replay import (
    load_agent_transcript,
    pass_plan_from_steps,
    transcript_submissions,
    transcript_steps,
)


FIXTURES = Path("tests/fixtures/template_generation_agent")


def test_single_round_fixture_can_be_replayed() -> None:
    transcript = load_agent_transcript(FIXTURES / "transcript_single_round.json")

    submissions = transcript_submissions(transcript, max_rounds=4)

    assert len(submissions) == 1
    assert submissions[0]["round_id"] == "round_001"


def test_multi_round_fixture_can_be_limited() -> None:
    transcript = load_agent_transcript(FIXTURES / "transcript_multi_round.json")

    submissions = transcript_submissions(transcript, max_rounds=1)

    assert len(submissions) == 1
    assert submissions[0]["round_id"] == "round_001"


def test_staged_transcript_preserves_pass_metadata() -> None:
    transcript = {
        "artifact_type": "template_agent_transcript",
        "rounds": [
            {
                "round_id": "round_001",
                "pass_id": "t2_unit_scan",
                "pass_kind": "t2_unit_scan",
                "window_id": "full_document",
                "allowed_layers": ["t2"],
                "submission": {"round_id": "round_001", "layers": {}},
            }
        ],
    }

    steps = transcript_steps(transcript, max_rounds=4)
    pass_plan = pass_plan_from_steps(steps, provider="replay")

    assert steps[0]["pass_id"] == "t2_unit_scan"
    assert steps[0]["allowed_layers"] == ["t2"]
    assert pass_plan["passes"][0]["pass_kind"] == "t2_unit_scan"
