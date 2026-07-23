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


def test_observation_bridge_keeps_gold_page_policy_when_boundary_also_changes(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        units=[
            {
                "unit_id": "body_main",
                "name": "正文",
                "source_seq_refs": [2, 3],
                "confidence": "high",
                "page_policy": {
                    "start": "new_page",
                    "scope": "page_range_exclusive",
                },
            }
        ],
    )

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    t2 = bridge["transcript"]["rounds"][0]["submission"]["layers"]["t2"]
    assert len(t2["boundary_adjustments"]) == 1
    assert len(t2["page_policy_candidates"]) == 1
    assert t2["page_policy_candidates"][0]["page_policy"] == {
        "start": "new_page",
        "scope": "page_range_exclusive",
    }


def test_observation_bridge_converts_page_only_t2_difference(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    cover = next(
        unit
        for unit in artifacts["structure_candidates"]["units"]
        if unit["unit_id"] == "cover"
    )
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        units=[
            {
                "unit_id": "cover",
                "name": "封面",
                "source_seq_refs": cover["source_seq_refs"],
                "confidence": "high",
                "page_policy": {
                    "start": "document_start",
                    "scope": "single_page_exclusive",
                },
                "evidence_refs": ["page:1"],
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
    assert t2_submission["layers"]["t2"]["boundary_adjustments"] == []
    proposals = t2_submission["layers"]["t2"]["page_policy_candidates"]
    assert bridge["summary"]["t2_proposals"] == 1
    assert proposals[0]["kind"] == "page_policy_candidate"
    assert proposals[0]["operation"] == "set_page_policy"
    assert proposals[0]["page_policy"] == {
        "start": "document_start",
        "scope": "single_page_exclusive",
    }
    assert "page" not in proposals[0]


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


def test_observation_bridge_preserves_unknown_until_execution_fallback(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        elements=[
            {
                "element_id": "body_main.e_002",
                "unit_id": "body_main",
                "policy": "unknown",
                "core_action": "keep",
                "source_seq_refs": [3],
                "confidence": "low",
            }
        ],
    )

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    proposal = bridge["transcript"]["rounds"][1]["submission"]["layers"]["t3"][
        "element_policy_candidates"
    ][0]
    assert proposal["policy"] == "unknown"
    assert proposal["core_action"] == "keep"
    assert proposal["observed_policy"] == "unknown"
    assert proposal["execution_fallback_action"] == "keep"
    assert proposal["execution_fallback_policy"] == "fixed"


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


def test_observation_bridge_only_emits_accepted_sparse_mutations(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        elements=[
            {
                "element_id": "cover.run_1",
                "unit_id": "cover",
                "core_action": "keep",
                "policy": "fixed",
                "source_seq_refs": [1],
                "raw_run_ids": ["p_0001.r_001"],
                "confidence": "high",
                "decision_status": "accepted",
                "resolution": "direct",
                "merge_eligible": True,
            },
            {
                "element_id": "body.run_1",
                "unit_id": "body_main",
                "core_action": "fill",
                "policy": "fill",
                "source_seq_refs": [3],
                "raw_run_ids": ["p_0003.r_001"],
                "logical_run_ids": ["p_0003.lr_001"],
                "confidence": "medium",
                "decision_ref": "decision:fill",
                "decision_target_ref": "paragraph:p_0003",
                "decision_status": "accepted",
                "resolution": "inherited",
                "inherited_from": "paragraph:p_0003",
                "member_ref": "run:p_0003.r_001",
                "merge_eligible": True,
                "fill_source": "student_content",
                "fill_field": "STUDENT_ID",
            },
            {
                "element_id": "body.run_2",
                "unit_id": "body_main",
                "core_action": "keep",
                "policy": "fixed",
                "source_seq_refs": [3],
                "raw_run_ids": ["p_0003.r_002"],
                "confidence": "low",
                "decision_status": "failed",
                "resolution": "fallback",
                "merge_eligible": False,
            },
        ],
    )
    bundle["ai_element_observation"]["sparse_decisions"] = [{"decision_ref": "decision:fill"}]

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    proposals = bridge["transcript"]["rounds"][1]["submission"]["layers"]["t3"][
        "element_policy_candidates"
    ]
    assert len(proposals) == 1
    assert proposals[0]["target_candidate_id"] is None
    assert proposals[0]["raw_run_ids"] == ["p_0003.r_001"]
    assert proposals[0]["decision_ref"] == "decision:fill"
    assert proposals[0]["fill_field"] == "STUDENT_ID"
    assert bridge["proposal_map"][0]["status"] == "no_op"
    assert bridge["summary"]["manual_review_required"] == 1
    assert bridge["manual_review_items"][0]["reason_code"] == (
        "OBSERVATION-T3-SPARSE-NOT-MERGEABLE"
    )


def test_observation_bridge_ai_primary_emits_accepted_sparse_keep(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        elements=[
            {
                "element_id": "cover.run_1",
                "unit_id": "cover",
                "core_action": "keep",
                "policy": "fixed",
                "source_seq_refs": [1],
                "raw_run_ids": ["p_0001.r_001"],
                "confidence": "high",
                "decision_status": "accepted",
                "resolution": "direct",
                "merge_eligible": True,
            }
        ],
    )
    bundle["ai_element_observation"]["sparse_decisions"] = [
        {"decision_ref": "decision:keep"}
    ]

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
        t3_authority_mode="ai_primary",
    )

    proposals = bridge["transcript"]["rounds"][1]["submission"]["layers"]["t3"][
        "element_policy_candidates"
    ]
    assert len(proposals) == 1
    assert proposals[0]["core_action"] == "keep"
    assert proposals[0]["policy"] == "fixed"
    assert proposals[0]["raw_run_ids"] == ["p_0001.r_001"]


def test_observation_bridge_ai_primary_materializes_sparse_fallback_keep(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(
        artifacts["packet"]["source_render_hash"],
        elements=[
            {
                "element_id": "body.run_2",
                "unit_id": "body_main",
                "core_action": "keep",
                "policy": "fixed",
                "source_seq_refs": [3],
                "raw_run_ids": ["p_0003.r_002"],
                "confidence": "low",
                "decision_status": "manual_review",
                "resolution": "fallback",
                "merge_eligible": False,
            }
        ],
    )
    bundle["ai_element_observation"]["sparse_decisions"] = [
        {"decision_ref": "decision:fallback"}
    ]

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
        t3_authority_mode="ai_primary",
    )

    proposals = bridge["transcript"]["rounds"][1]["submission"]["layers"]["t3"][
        "element_policy_candidates"
    ]
    assert len(proposals) == 1
    assert proposals[0]["core_action"] == "keep"
    assert proposals[0]["policy"] == "fixed"
    assert bridge["summary"]["manual_review_required"] == 0


def test_observation_bridge_routes_sparse_source_objects_to_manual_review(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    bundle = _bundle(artifacts["packet"]["source_render_hash"])
    bundle["ai_element_observation"].update(
        {
            "sparse_decisions": [{"decision_ref": "decision:object"}],
            "object_items": [
                {
                    "element_id": "object.text_box_1",
                    "member_ref": "text_box:1",
                    "policy": "fixed",
                    "decision_status": "accepted",
                    "resolution": "direct",
                    "merge_eligible": True,
                }
            ],
        }
    )

    bridge = build_observation_bridge(
        observation_bundle=bundle,
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )

    assert bridge["summary"]["t3_proposals"] == 0
    assert bridge["manual_review_items"][0]["reason_code"] == (
        "OBSERVATION-T3-OBJECT-NOT-MATERIALIZABLE"
    )


def test_run_template_agent_materializes_accepted_sparse_raw_run_decision(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    candidates = artifacts["structure_candidates"]
    body = next(unit for unit in candidates["units"] if unit["unit_id"] == "body_main")
    element = next(item for item in body["elements"] if item["source_seq_refs"] == [3])
    element.update(
        {
            "candidate_policy": "fixed",
            "content": "学号：20XX（填写说明）",
            "raw_run_ids": ["p_0003.r_001", "p_0003.r_002", "p_0003.r_003"],
            "logical_run_ids": ["p_0003.lr_001", "p_0003.lr_002", "p_0003.lr_003"],
        }
    )
    candidates["source_context"]["runs_by_raw_run_id"] = {
        "p_0003.r_001": {"text": "学号：", "logical_run_id": "p_0003.lr_001"},
        "p_0003.r_002": {"text": "20XX", "logical_run_id": "p_0003.lr_002"},
        "p_0003.r_003": {"text": "（填写说明）", "logical_run_id": "p_0003.lr_003"},
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
                "merge_eligible": True,
                "fill_source": "student_content",
                "fill_field": "STUDENT_ID",
            }
        ],
    )
    bundle["ai_element_observation"]["sparse_decisions"] = [
        {"decision_ref": "decision:fill"}
    ]
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

    assert result.changed is True
    assert result.decisions is not None
    assert result.decisions["accepted_proposal_ids"] == ["obs_t3_body_main_001"]
    target = next(
        item
        for item in result.element_spec["elements"]
        if item.get("raw_run_ids") == ["p_0003.r_002"]
    )
    assert target["policy"] == "fill"
    assert target["fill_field"] == "STUDENT_ID"
    assert target["agent_traces"][0]["decision_ref"] == "decision:fill"


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
