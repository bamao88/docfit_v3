from __future__ import annotations

from docfit.core.io import write_json
from docfit.template_generation.agent.config import AgentConfig
from docfit.template_generation.agent.loop import run_template_agent
from docfit.template_generation.agent.observation_bridge import build_observation_bridge

from .helpers import round0_artifacts


def test_observation_bridge_converts_high_confidence_t2_unit(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        units=[
            {
                "unit_id": "integrity_statement",
                "name": "承诺书",
                "source_seq_refs": [2],
                "confidence": "high",
                "ai_rationale": "source text is a commitment statement",
            }
        ],
    )

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    t2_submission = bridge["transcript"]["rounds"][0]["submission"]
    proposals = t2_submission["layers"]["t2"]["unit_candidates"]
    assert bridge["summary"]["t2_proposals"] == 1
    assert bridge["summary"]["manual_review_required"] == 0
    assert proposals[0]["origin"] == "ai_observation"
    assert proposals[0]["operation"] == "add_unit"
    assert proposals[0]["source_seq_refs"] == [2]


def test_observation_bridge_routes_t2_boundary_adjustment_to_boundary_collection(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        units=[
            {
                "unit_id": "body_main",
                "name": "正文",
                "source_seq_refs": [2, 3],
                "confidence": "high",
                "ai_rationale": "AI boundary excludes trailing instruction paragraph",
            }
        ],
    )

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    t2_submission = bridge["transcript"]["rounds"][0]["submission"]
    assert t2_submission["layers"]["t2"]["unit_candidates"] == []
    proposals = t2_submission["layers"]["t2"]["boundary_adjustments"]
    assert bridge["summary"]["t2_proposals"] == 1
    assert proposals[0]["kind"] == "boundary_adjustment"
    assert proposals[0]["operation"] == "adjust_unit_range"
    assert proposals[0]["target_unit_id"] == "body_main"


def test_observation_bridge_maps_instruction_remove_policy(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        elements=[
            {
                "element_id": "body_main.e_001",
                "unit_id": "body_main",
                "policy": "instruction_remove",
                "source_seq_refs": [2],
                "confidence": "medium",
            }
        ],
    )

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    t3_submission = bridge["transcript"]["rounds"][1]["submission"]
    proposals = t3_submission["layers"]["t3"]["element_policy_candidates"]
    assert proposals[0]["policy"] == "remove_instruction"
    assert proposals[0]["target_candidate_id"] == "body_main.e_001"


def test_observation_bridge_maps_template_default_policy_to_fixed(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        elements=[
            {
                "element_id": "cover.e_001",
                "unit_id": "cover",
                "policy": "template_default",
                "source_seq_refs": [1],
                "confidence": "high",
            }
        ],
    )

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    t3_submission = bridge["transcript"]["rounds"][1]["submission"]
    proposals = t3_submission["layers"]["t3"]["element_policy_candidates"]
    assert proposals[0]["policy"] == "fixed"


def test_observation_bridge_keeps_low_confidence_t3_as_bound_proposal(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        elements=[
            {
                "element_id": "cover.e_001",
                "unit_id": "cover",
                "policy": "fixed",
                "source_seq_refs": [1],
                "confidence": "low",
            }
        ],
    )

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    t3_submission = bridge["transcript"]["rounds"][1]["submission"]
    proposals = t3_submission["layers"]["t3"]["element_policy_candidates"]
    assert bridge["summary"]["t3_proposals"] == 1
    assert bridge["summary"]["manual_review_required"] == 0
    assert proposals[0]["policy"] == "fixed"
    assert proposals[0]["observation_confidence"] == "low"


def test_observation_bridge_low_confidence_goes_to_manual_review(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        units=[
            {
                "unit_id": "integrity_statement",
                "source_seq_refs": [2],
                "confidence": "low",
            }
        ],
    )

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    assert bridge["summary"]["total_proposals"] == 0
    assert bridge["manual_review_items"][0]["reason_code"] == "OBSERVATION-LOW-CONFIDENCE"


def test_observation_bridge_does_not_convert_vision_page_observation_to_t4_policy(
    tmp_path,
) -> None:
    artifacts = round0_artifacts(tmp_path)
    artifacts["packet"]["render_status"] = "real_render"
    artifacts["packet"]["page_layout_index"] = [
        {"source_seq": 1, "page_no": 1, "render_target_id": "source_seq:1"},
        {"source_seq": 2, "page_no": 2, "render_target_id": "source_seq:2"},
        {"source_seq": 3, "page_no": 2, "render_target_id": "source_seq:3"},
        {"source_seq": 4, "page_no": 3, "render_target_id": "source_seq:4"},
    ]
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        layout_items=[],
    )
    bundle["ai_layout_observation"]["page_observations"] = [
        {
            "page_no": 2,
            "page_number_visible": True,
            "page_number_text": "1",
        }
    ]

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    t4_submission = bridge["transcript"]["rounds"][2]["submission"]
    assert "page_policy_hints" not in t4_submission["layers"]["t4"]
    assert bridge["summary"]["t4_proposals"] == 0


def test_run_template_agent_consumes_observation_bundle(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    packet_path = tmp_path / "packet.json"
    bundle_path = tmp_path / "observation_bundle.json"
    write_json(packet_path, artifacts["packet"])
    write_json(
        bundle_path,
        _bundle(
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
            render_packet_path=packet_path,
            observation_bundle_path=bundle_path,
        ),
    )

    assert result.changed is True
    assert result.observation_bridge is not None
    assert result.t2_overlay["operations"][0]["proposal_id"].startswith("obs_t2_")
    assert "integrity_statement" in [unit["unit_id"] for unit in result.unit_map["units"]]
    assert result.manual_review_items["summary"]["total"] == 0


def test_run_template_agent_batches_t2_boundary_adjustments(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    packet_path = tmp_path / "packet.json"
    bundle_path = tmp_path / "observation_bundle.json"
    write_json(packet_path, artifacts["packet"])
    write_json(
        bundle_path,
        _bundle(
            artifacts["packet"]["source_render_hash"],
            units=[
                {
                    "unit_id": "body_main",
                    "name": "正文",
                    "source_seq_refs": [3, 4],
                    "confidence": "high",
                },
                {
                    "unit_id": "cover",
                    "name": "封面",
                    "source_seq_refs": [1, 2],
                    "confidence": "high",
                },
            ],
        ),
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
            render_packet_path=packet_path,
            observation_bundle_path=bundle_path,
        ),
    )

    units = {unit["unit_id"]: unit for unit in result.unit_map["units"]}
    assert result.changed is True
    assert len(result.t2_overlay["operations"]) == 2
    assert len(result.decisions["accepted_proposal_ids"]) == 2
    assert units["cover"]["source_seq_refs"] == [1, 2]
    assert units["body_main"]["source_seq_refs"] == [3, 4]


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
