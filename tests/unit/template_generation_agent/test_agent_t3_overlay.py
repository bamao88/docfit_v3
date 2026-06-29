from __future__ import annotations

from docfit.core.io import write_json
from docfit.template_generation.agent.config import AgentConfig
from docfit.template_generation.agent.loop import run_template_agent

from .helpers import layered_submission, round0_artifacts


def test_t3_policy_overlay_regenerates_element_spec(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t3": {
                "element_policy_candidates": [
                    {
                        "proposal_id": "t3_fill_001",
                        "kind": "element_policy_candidate",
                        "policy": "fill",
                        "source_seq_refs": [3],
                    }
                ]
            }
        },
    )
    transcript_path = tmp_path / "transcript.json"
    packet_path = tmp_path / "packet.json"
    write_json(packet_path, artifacts["packet"])
    write_json(transcript_path, {"rounds": [{"submission": submission}]})

    result = run_template_agent(
        source_template_docx=tmp_path / "template.docx",
        request=artifacts["request"],
        document_facts=artifacts["document_facts"],
        structure_candidates=artifacts["structure_candidates"],
        unit_map=artifacts["unit_map"],
        generation_model=artifacts["generation_model"],
        element_spec=artifacts["element_spec"],
        agent_config=AgentConfig(
            enabled=True,
            transcript_path=transcript_path,
            render_packet_path=packet_path,
        ),
    )

    target = next(
        element
        for element in result.element_spec["elements"]
        if element["source_seq_refs"] == [3]
    )
    assert target["policy"] == "fill"
    assert result.t3_overlay is not None
    assert result.t3_overlay["operations"][0]["target_candidate_id"] == "body_main.e_002"


def test_t3_unknown_policy_is_rejected_before_canonical_fallback(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t3": {
                "element_policy_candidates": [
                    {
                        "proposal_id": "t3_remove_001",
                        "kind": "element_policy_candidate",
                        "policy": "remove",
                        "source_seq_refs": [3],
                    }
                ]
            }
        },
    )
    transcript_path = tmp_path / "transcript.json"
    packet_path = tmp_path / "packet.json"
    write_json(packet_path, artifacts["packet"])
    write_json(transcript_path, {"rounds": [{"submission": submission}]})

    result = run_template_agent(
        source_template_docx=tmp_path / "template.docx",
        request=artifacts["request"],
        document_facts=artifacts["document_facts"],
        structure_candidates=artifacts["structure_candidates"],
        unit_map=artifacts["unit_map"],
        generation_model=artifacts["generation_model"],
        element_spec=artifacts["element_spec"],
        agent_config=AgentConfig(
            enabled=True,
            transcript_path=transcript_path,
            render_packet_path=packet_path,
        ),
    )

    assert result.changed is False
    assert result.decisions is not None
    assert result.decisions["rejected_proposal_ids"] == ["t3_remove_001"]
    assert result.decisions["decisions"][0]["checks"][0]["check_id"] == "C-EXECUTABLE-ENUM"
