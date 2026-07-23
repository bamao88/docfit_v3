from __future__ import annotations

from docfit.core.io import write_json
from docfit.template_generation.agent.config import AgentConfig
from docfit.template_generation.agent.loop import run_template_agent
from docfit.template_generation.agent.observation_bridge import (
    build_observation_bridge,
)

from .helpers import round0_artifacts


def test_observation_bridge_converts_high_confidence_t2_unit(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bridge = build_observation_bridge(
        observation_bundle=_bundle(
            artifacts["packet"]["source_render_hash"],
            units=[
                {
                    "unit_id": "integrity_statement",
                    "name": "承诺书",
                    "source_seq_refs": [2],
                    "confidence": "high",
                }
            ],
        ),
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    rounds = bridge["transcript"]["rounds"]
    proposals = rounds[0]["submission"]["layers"]["t2"]["unit_candidates"]
    assert [round_item["allowed_layers"] for round_item in rounds] == [
        ["t2"],
        ["t4"],
    ]
    assert bridge["summary"]["t2_proposals"] == 1
    assert "t3_proposals" not in bridge["summary"]
    assert proposals[0]["operation"] == "add_unit"


def test_observation_bridge_never_converts_t3_to_layered_proposals(
    tmp_path,
) -> None:
    artifacts = round0_artifacts(tmp_path)
    bridge = build_observation_bridge(
        observation_bundle=_bundle(
            artifacts["packet"]["source_render_hash"],
            elements=[
                {
                    "element_id": "body.run_1",
                    "unit_id": "body_main",
                    "policy": "fill",
                    "source_seq_refs": [3],
                    "raw_run_ids": ["p_0003.r_001"],
                    "decision_status": "accepted",
                    "resolution": "direct",
                    "execution_eligible": True,
                }
            ],
        ),
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    assert all(
        "t3" not in round_item["submission"]["layers"]
        for round_item in bridge["transcript"]["rounds"]
    )
    assert all(
        item.get("layer") != "t3"
        for item in bridge["proposal_map"]
    )


def test_run_template_agent_materializes_t3_without_proposal_pipeline(
    tmp_path,
) -> None:
    artifacts = round0_artifacts(tmp_path)
    candidates = artifacts["structure_candidates"]
    body = next(
        unit for unit in candidates["units"] if unit["unit_id"] == "body_main"
    )
    element = next(
        item for item in body["elements"] if item["source_seq_refs"] == [3]
    )
    element.update(
        {
            "candidate_policy": "fixed",
            "content": "学号：20XX（填写说明）",
            "raw_run_ids": [
                "p_0003.r_001",
                "p_0003.r_002",
                "p_0003.r_003",
            ],
            "logical_run_ids": [
                "p_0003.lr_001",
                "p_0003.lr_002",
                "p_0003.lr_003",
            ],
        }
    )
    candidates["source_context"]["runs_by_raw_run_id"] = {
        "p_0003.r_001": {
            "text": "学号：",
            "logical_run_id": "p_0003.lr_001",
        },
        "p_0003.r_002": {
            "text": "20XX",
            "logical_run_id": "p_0003.lr_002",
        },
        "p_0003.r_003": {
            "text": "（填写说明）",
            "logical_run_id": "p_0003.lr_003",
        },
    }
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        elements=[
            {
                "element_id": "sparse.body.run_2",
                "unit_id": "body_main",
                "core_action": "fill",
                "policy": "fill",
                "source_seq_refs": [3],
                "raw_run_ids": ["p_0003.r_002"],
                "logical_run_ids": ["p_0003.lr_002"],
                "confidence": "high",
                "decision_ref": "decision:fill",
                "decision_target_ref": "run:p_0003.r_002",
                "decision_status": "accepted",
                "resolution": "direct",
                "member_ref": "run:p_0003.r_002",
                "execution_eligible": True,
                "fill_source": "student_content",
                "fill_field": "STUDENT_ID",
            }
        ],
    )
    packet_path = tmp_path / "packet.json"
    bundle_path = tmp_path / "observation_bundle.json"
    write_json(packet_path, artifacts["packet"])
    write_json(bundle_path, bundle)

    result = run_template_agent(
        source_template_docx=tmp_path / "template.docx",
        request=artifacts["request"],
        document_facts=artifacts["document_facts"],
        structure_candidates=candidates,
        unit_map=artifacts["unit_map"],
        generation_model=artifacts["generation_model"],
        element_spec=artifacts["element_spec"],
        agent_config=AgentConfig(
            enabled=True,
            render_packet_path=packet_path,
            observation_bundle_path=bundle_path,
        ),
    )

    assert result.decisions["accepted_proposal_ids"] == []
    assert result.decisions["rejected_proposal_ids"] == []
    trace = result.t3_materialization_trace
    assert trace["artifact_type"] == "t3_materialization_trace"
    assert trace["materialization"]["accepted_observation_item_count"] == 1
    target = next(
        item
        for item in result.element_spec["elements"]
        if item.get("raw_run_ids") == ["p_0003.r_002"]
    )
    assert target["policy"] == "fill"
    assert target["fill_field"] == "STUDENT_ID"


def test_observation_bridge_keeps_t4_as_second_round(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bridge = build_observation_bridge(
        observation_bundle=_bundle(
            artifacts["packet"]["source_render_hash"],
            layout_items=[],
        ),
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    t4_submission = bridge["transcript"]["rounds"][1]["submission"]
    assert t4_submission["allowed_layers"] == ["t4"]
    assert "t3" not in t4_submission["layers"]


def _bundle(
    source_render_hash: str,
    *,
    units: list[dict] | None = None,
    elements: list[dict] | None = None,
    layout_items: list[dict] | None = None,
) -> dict:
    return {
        "artifact_type": "ai_observation_bundle",
        "source_render_hash": source_render_hash,
        "model": "fixture",
        "ai_unit_observation": {
            "artifact_type": "ai_unit_observation",
            "items": units or [],
            "quality_report": {"demotions": []},
        },
        "ai_element_observation": {
            "artifact_type": "ai_element_observation",
            "items": elements or [],
            "quality_report": {"demotions": []},
        },
        "ai_layout_observation": {
            "artifact_type": "ai_layout_observation",
            "items": layout_items or [],
            "abstain": False,
            "quality_report": {"demotions": []},
        },
    }
