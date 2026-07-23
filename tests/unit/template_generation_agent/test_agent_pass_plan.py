from __future__ import annotations

from docfit.core.io import write_json
from docfit.template_generation.agent.config import AgentConfig
from docfit.template_generation.agent.loop import run_template_agent

from .helpers import layered_submission, round0_artifacts


def test_pass_scope_rejects_disallowed_layer(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t3": {
                "element_policy_candidates": [
                    {
                        "proposal_id": "t3_out_of_scope",
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

    assert result.changed is False
    assert result.pass_plan is not None
    assert result.pass_plan["passes"][0]["pass_id"] == "t2_unit_scan"
    assert result.decisions is not None
    assert result.decisions["rejected_proposal_ids"] == ["t3_out_of_scope"]
    decision = result.decisions["decisions"][0]
    assert decision["checks"][0]["check_id"] == "C-PASS-SCOPE"
    assert decision["pass_id"] == "t2_unit_scan"


def test_legacy_t3_layered_proposal_is_rejected_after_t2_pass(tmp_path) -> None:
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
    t3_submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t3": {
                "element_policy_candidates": [
                    {
                        "proposal_id": "t3_outside_window",
                        "kind": "element_policy_candidate",
                        "policy": "fill",
                        "source_seq_refs": [2],
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
                    "submission": t2_submission,
                },
                {
                    "round_id": "round_002",
                    "pass_id": "t3_unit_elements_body_main",
                    "pass_kind": "t3_unit_elements",
                    "window_id": "unit:body_main",
                    "unit_id": "body_main",
                    "allowed_layers": ["t3"],
                    "submission": t3_submission,
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
    assert result.unit_windows is not None
    body_main = next(
        window
        for window in result.unit_windows["windows"]
        if window["unit_id"] == "body_main"
    )
    assert 2 not in body_main["source_seq_refs"]
    assert result.decisions is not None
    assert result.decisions["accepted_proposal_ids"] == ["t2_add_001"]
    assert result.decisions["rejected_proposal_ids"] == ["t3_outside_window"]
    rejected = result.decisions["decisions"][1]
    assert "legacy T3 layered proposals are removed" in rejected["reason"]
    assert rejected["pass_unit_id"] == "body_main"
