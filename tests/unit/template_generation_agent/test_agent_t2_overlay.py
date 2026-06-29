from __future__ import annotations

from docfit.core.io import write_json
from docfit.template_generation.agent.config import AgentConfig
from docfit.template_generation.agent.loop import run_template_agent

from .helpers import layered_submission, round0_artifacts


def test_t2_add_unit_overlay_regenerates_unit_map(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t2": {
                "unit_candidates": [
                    {
                        "proposal_id": "t2_add_001",
                        "kind": "unit_candidate",
                        "operation": "add_unit",
                        "unit_id": "integrity_statement",
                        "display_name": "承诺书",
                        "source_seq_refs": [2],
                        "evidence": [{"source_seq": 2}],
                    }
                ]
            }
        },
    )
    transcript_path = tmp_path / "transcript.json"
    packet_path = tmp_path / "packet.json"
    write_json(packet_path, artifacts["packet"])
    write_json(
        transcript_path,
        {"artifact_type": "template_agent_transcript", "rounds": [{"submission": submission}]},
    )

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

    assert result.changed is True
    assert any(unit["unit_id"] == "integrity_statement" for unit in result.unit_map["units"])
    assert result.t2_overlay is not None
    assert result.t2_overlay["operations"][0]["operation"] == "add_unit"
    assert result.decisions is not None
    assert result.decisions["accepted_proposal_ids"] == ["t2_add_001"]


def test_t2_overlay_rejects_invalid_source_seq(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t2": {
                "unit_candidates": [
                    {
                        "proposal_id": "t2_bad_001",
                        "kind": "unit_candidate",
                        "operation": "add_unit",
                        "unit_id": "integrity_statement",
                        "source_seq_refs": [999],
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
    assert result.decisions["rejected_proposal_ids"] == ["t2_bad_001"]


def test_t2_overlay_can_claim_round0_unassigned_source_seq(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    for unit in artifacts["structure_candidates"]["units"]:
        if unit["unit_id"] == "body_main":
            unit["source_seq_refs"] = [2, 3]
            unit["source_refs"] = unit["source_refs"][:2]
            unit["source_range"]["source_refs"] = unit["source_refs"]
            unit["source_seq_range"]["source_seq_refs"] = [2, 3]
            unit["elements"] = unit["elements"][:2]
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t2": {
                "unit_candidates": [
                    {
                        "proposal_id": "t2_claim_gap_001",
                        "kind": "unit_candidate",
                        "operation": "add_unit",
                        "unit_id": "appendix_gap",
                        "display_name": "未归属附录",
                        "source_seq_refs": [4],
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

    assert result.changed is True
    assert result.decisions is not None
    assert result.decisions["accepted_proposal_ids"] == ["t2_claim_gap_001"]
    assert result.t2_overlay is not None
    operation = result.t2_overlay["operations"][0]
    assert operation["round0_unassigned_source_seq_refs"] == [4]
    assert operation["round0_reassigned_source_seq_refs"] == []
    assert result.post_t2_input is not None
    assert result.post_t2_input["source_seq_ownership"]["4"] == "appendix_gap"


def test_t2_overlay_rejects_claim_spanning_multiple_existing_units(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t2": {
                "unit_candidates": [
                    {
                        "proposal_id": "t2_steal_many_001",
                        "kind": "unit_candidate",
                        "operation": "add_unit",
                        "unit_id": "bad_cross_unit",
                        "display_name": "跨单元抢占",
                        "source_seq_refs": [1, 2],
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
    assert result.decisions["rejected_proposal_ids"] == ["t2_steal_many_001"]
    assert "multiple existing units" in result.decisions["decisions"][0]["reason"]
