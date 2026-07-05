from __future__ import annotations

from docfit.core.io import write_json
from docfit.template_generation.agent.config import AgentConfig
from docfit.template_generation.agent.loop import run_template_agent
from docfit.template_generation.artifacts import build_element_spec, build_unit_map
from docfit.template_generation.generation_model import build_template_generation_model

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


def test_t3_policy_overlay_preserves_source_backed_spans(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    candidates = artifacts["structure_candidates"]
    body_entry = candidates["source_context"]["body_flow"][2]
    body_entry["text"] = "□□□□□□学□□号：20××××××××××（四号Times New Roman）"
    body_entry["raw_run_ids"] = ["p_0003.r_001", "p_0003.r_002", "p_0003.r_003"]
    body_entry["logical_run_ids"] = ["p_0003.lr_001", "p_0003.lr_002", "p_0003.lr_003"]
    candidates["source_context"]["runs_by_raw_run_id"] = {
        "p_0003.r_001": {"text": "□□□□□□"},
        "p_0003.r_002": {"text": "学□□号："},
        "p_0003.r_003": {"text": "20××××××××××（四号Times New Roman）"},
    }
    for unit in candidates["units"]:
        for element in unit.get("elements", []):
            if element.get("source_seq_refs") == [3]:
                element["content"] = body_entry["text"]
    unit_map = build_unit_map(artifacts["document_facts"], candidates)
    generation_model = build_template_generation_model(artifacts["request"], candidates)
    element_spec = build_element_spec(generation_model)
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
        structure_candidates=candidates,
        unit_map=unit_map,
        generation_model=generation_model,
        element_spec=element_spec,
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
    span_types = {span["span_type"] for span in target["spans"]}
    assert {"layout_spacer", "label", "sample_value", "inline_instruction"}.issubset(
        span_types
    )
    assert target["policy"] == "fill"


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
