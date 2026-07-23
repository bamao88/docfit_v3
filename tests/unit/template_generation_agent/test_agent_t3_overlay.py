from __future__ import annotations

from docfit.core.io import write_json
from docfit.template_generation.agent.config import AgentConfig
from docfit.template_generation.agent.loop import run_template_agent
from docfit.template_generation.agent.overlay import apply_t3_proposal, bind_t3_target
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


def test_t3_policy_overlay_splits_exact_raw_run_before_applying_policy(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    candidates = artifacts["structure_candidates"]
    body = next(unit for unit in candidates["units"] if unit["unit_id"] == "body_main")
    element = next(item for item in body["elements"] if item["source_seq_refs"] == [3])
    element.update(
        {
            "content": "学号：20XX（填写说明）",
            "candidate_policy": "fixed",
            "raw_run_ids": ["p_0003.r_001", "p_0003.r_002", "p_0003.r_003"],
            "logical_run_ids": ["p_0003.lr_001", "p_0003.lr_002", "p_0003.lr_003"],
        }
    )
    candidates["source_context"]["runs_by_raw_run_id"] = {
        "p_0003.r_001": {"text": "学号：", "logical_run_id": "p_0003.lr_001"},
        "p_0003.r_002": {"text": "20XX", "logical_run_id": "p_0003.lr_002"},
        "p_0003.r_003": {"text": "（填写说明）", "logical_run_id": "p_0003.lr_003"},
    }
    proposal = {
        "proposal_id": "t3_exact_fill",
        "policy": "fill",
        "unit_id": "body_main",
        "source_seq_refs": [3],
        "raw_run_ids": ["p_0003.r_002"],
        "logical_run_ids": ["p_0003.lr_002"],
        "decision_ref": "decision:fill",
        "decision_target_ref": "run:p_0003.r_002",
        "decision_status": "accepted",
        "resolution": "direct",
        "member_ref": "run:p_0003.r_002",
        "fill_source": "student_content",
        "fill_field": "STUDENT_ID",
    }

    bound = bind_t3_target(candidates, proposal)
    assert bound is not None and bound[1]["element_id"] == element["element_id"]
    patched, operation, reason = apply_t3_proposal(candidates, proposal)

    assert reason == ""
    assert patched is not None and operation is not None
    patched_body = next(unit for unit in patched["units"] if unit["unit_id"] == "body_main")
    split = [item for item in patched_body["elements"] if item.get("source_seq_refs") == [3]]
    assert [item["content"] for item in split] == ["学号：", "20XX", "（填写说明）"]
    assert [item["candidate_policy"] for item in split] == ["fixed", "fill", "fixed"]
    target = next(item for item in split if item["raw_run_ids"] == ["p_0003.r_002"])
    assert target["candidate_policy"] == "fill"
    assert target["fill_field"] == "STUDENT_ID"
    assert target["agent_traces"][0]["decision_ref"] == "decision:fill"
    assert operation["raw_run_ids"] == ["p_0003.r_002"]


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


def test_t3_policy_overlay_rejects_fill_for_fixed_unit(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    candidates = artifacts["structure_candidates"]
    manual_entry = candidates["source_context"]["body_flow"][1]
    manual_unit = candidates["units"][1]
    manual_unit["unit_id"] = "proposal"
    manual_unit["name"] = "开题报告"
    manual_unit["candidate_policy"] = "fixed"
    manual_unit["source_refs"] = [manual_entry["source_ref"]]
    manual_unit["source_seq_refs"] = [manual_entry["source_seq"]]
    manual_unit["source_range"]["source_refs"] = [manual_entry["source_ref"]]
    manual_unit["source_seq_range"]["source_seq_refs"] = [manual_entry["source_seq"]]
    manual_unit["elements"] = [
        {
            "element_id": "e_001",
            "name": "开题报告",
            "order": 1,
            "candidate_policy": "fixed",
            "role_hint": "fixed_text_candidate",
            "relationship": "source_paragraph",
            "content": manual_entry["text"],
            "style": "Normal",
            "source_refs": [manual_entry["source_ref"]],
            "source_seq_refs": [manual_entry["source_seq"]],
            "entry_refs": [manual_entry["node_id"]],
            "evidence": [],
        }
    ]
    unit_map = build_unit_map(artifacts["document_facts"], candidates)
    generation_model = build_template_generation_model(artifacts["request"], candidates)
    element_spec = build_element_spec(generation_model)
    submission = layered_submission(
        artifacts["packet"]["source_render_hash"],
        layers={
            "t3": {
                "element_policy_candidates": [
                    {
                        "proposal_id": "t3_fill_manual_001",
                        "kind": "element_policy_candidate",
                        "policy": "fill",
                        "target_candidate_id": "proposal.e_001",
                        "source_seq_refs": [manual_entry["source_seq"]],
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

    assert result.changed is False
    assert result.decisions is not None
    assert result.decisions["rejected_proposal_ids"] == ["t3_fill_manual_001"]
    assert result.decisions["decisions"][0]["checks"][0]["check_id"] == "C-POLICY-DOWNGRADE"


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


def test_t3_explicit_unknown_executes_as_keep_even_over_fill(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    candidates = artifacts["structure_candidates"]
    target = next(
        element
        for unit in candidates["units"]
        for element in unit.get("elements", [])
        if element.get("source_seq_refs") == [3]
    )
    target["candidate_policy"] = "fill"

    patched, operation, error = apply_t3_proposal(
        candidates,
        {
            "proposal_id": "t3_unknown_001",
            "kind": "element_policy_candidate",
            "policy": "unknown",
            "source_seq_refs": [3],
        },
    )

    assert error == ""
    assert patched is not None
    assert operation is not None
    patched_target = next(
        element
        for unit in patched["units"]
        for element in unit.get("elements", [])
        if element.get("source_seq_refs") == [3]
    )
    assert patched_target["candidate_policy"] == "fixed"
    assert operation["observed_policy"] == "unknown"
    assert operation["execution_fallback_action"] == "keep"
