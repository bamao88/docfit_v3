from __future__ import annotations

from docfit.core.io import write_json
from docfit.template_generation.agent.config import AgentConfig
from docfit.template_generation.agent.loop import run_template_agent

from .helpers import layered_submission, round0_artifacts


def test_pass_scope_rejects_disallowed_t4_layer(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t4": {
                "section_profile_hints": [
                    {
                        "proposal_id": "t4_out_of_scope",
                        "kind": "section_profile_hint",
                        "source_seq_refs": [3],
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
        {
            "rounds": [
                {
                    "round_id": "round_001",
                    "pass_id": "t2_unit_scan",
                    "pass_kind": "t2_unit_scan",
                    "window_id": "full_document",
                    "allowed_layers": ["t2"],
                    "submission": submission,
                }
            ]
        },
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

    assert result.pass_plan["passes"][0]["pass_id"] == "t2_unit_scan"
    assert result.decisions["rejected_proposal_ids"] == ["t4_out_of_scope"]
    decision = result.decisions["decisions"][0]
    assert decision["checks"][0]["check_id"] == "C-PASS-SCOPE"


def test_t4_pass_builds_post_t2_checkpoint_without_t3_side_input(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    t2_submission = layered_submission(
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
                    }
                ]
            }
        },
    )
    t4_submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={},
    )
    transcript_path = tmp_path / "transcript.json"
    packet_path = tmp_path / "packet.json"
    write_json(packet_path, artifacts["packet"])
    write_json(
        transcript_path,
        {
            "rounds": [
                {
                    "round_id": "round_001",
                    "pass_kind": "t2_unit_scan",
                    "allowed_layers": ["t2"],
                    "submission": t2_submission,
                },
                {
                    "round_id": "round_002",
                    "pass_kind": "t4_global_layout",
                    "allowed_layers": ["t4"],
                    "submission": t4_submission,
                },
            ]
        },
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

    assert result.post_t2_checkpoint is not None
    assert result.decisions["accepted_proposal_ids"] == ["t2_add_001"]
