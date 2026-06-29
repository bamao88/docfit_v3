from __future__ import annotations

from docfit.core.io import write_json
from docfit.template_generation.agent.config import AgentConfig
from docfit.template_generation.agent.loop import run_template_agent

from .helpers import layered_submission, round0_artifacts


def test_t4_hints_are_artifacts_only(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    artifacts["packet"]["render_status"] = "real_render"
    artifacts["packet"]["render_artifacts"]["render_status"] = "real_render"
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t4": {
                "page_policy_hints": [
                    {
                        "proposal_id": "t4_page_001",
                        "kind": "page_policy_hint",
                        "page_no": 1,
                        "hint": "visual_new_page",
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
    assert result.unit_map == artifacts["unit_map"]
    assert result.element_spec == artifacts["element_spec"]
    assert result.t4_hints is not None
    assert result.t4_hints["page_policy_hints"][0]["proposal_id"] == "t4_page_001"


def test_t4_hints_are_rejected_without_real_render_packet(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t4": {
                "page_policy_hints": [
                    {
                        "proposal_id": "t4_page_001",
                        "kind": "page_policy_hint",
                        "page_no": 1,
                        "hint": "visual_new_page",
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
    assert result.t4_hints is not None
    assert result.t4_hints["page_policy_hints"] == []
    assert result.decisions is not None
    assert result.decisions["rejected_proposal_ids"] == ["t4_page_001"]
    assert result.decisions["decisions"][0]["checks"][0]["check_id"] == "C-RENDER-REQUIRED"
