from __future__ import annotations

import json

from docfit.core.io import sha256_json
from docfit.template_generation.input_contract import build_l1_input_contract
from docfit.template_generation.stage_inputs import (
    build_agent_stage_packet,
    l1_artifact_hash,
)


def test_l1_input_contract_projects_text_objects_layout_and_visual_facts() -> None:
    facts = {
        "artifact_type": "document_facts",
        "metadata": {"source_template_hash": "sha256:source"},
        "body_flow": [
            {
                "source_seq": 1,
                "source_ref": "word/document.xml:p[1]",
                "node_id": "p_0001",
                "kind": "paragraph",
                "text": "封面",
                "style": "Title",
                "style_details": {
                    "font": "黑体",
                    "runs": [
                        {
                            "source_ref": "word/document.xml:p[1]/r[1]",
                            "text": "封面",
                            "font_names": ["黑体"],
                            "font_size_pt": 16.0,
                            "bold": True,
                        }
                    ],
                },
                "text_facts": {"char_count": 2},
                "raw_run_ids": ["p_0001.r_001"],
                "logical_run_ids": ["p_0001.lr_001"],
            }
        ],
        "runs": [
            {
                "logical_run_id": "p_0001.lr_001",
                "merged_from": ["p_0001.r_001"],
                "paragraph_id": "p_0001",
                "source_refs": ["word/document.xml:p[1]/r[1]"],
                "text": "封面",
                "effective_style": {
                    "font_names": ["黑体"],
                    "font_size_pt": 16.0,
                    "bold": True,
                },
            }
        ],
        "indexes": {
            "runs_by_raw_run_id": {
                "p_0001.r_001": {
                    "logical_run_id": "p_0001.lr_001",
                    "paragraph_id": "p_0001",
                    "source_ref": "word/document.xml:p[1]/r[1]",
                    "effective_style": {
                        "font_names": ["黑体"],
                        "font_size_pt": 16.0,
                        "bold": True,
                    },
                }
            }
        },
        "data": {
            "sections": [{"index": 1, "page_size": {"width_twips": 11906}}],
            "headers_footers": [{"kind": "header", "part_name": "word/header1.xml", "text": "页眉"}],
            "fields": [{"index": 1, "field_type": "PAGE", "source_ref": "word/header1.xml:p[1]"}],
            "breaks": [{"index": 1, "type": "page", "source_ref": "word/document.xml:p[1]"}],
            "numbering_refs": [],
            "numbering_definitions": [],
            "images": [
                {
                    "index": 1,
                    "relationship_id": "rId5",
                    "target": "media/image1.png",
                    "sha256": "sha256:image",
                    "byte_count": 10,
                    "source_ref": "word/document.xml:p[1]/drawing[1]",
                }
            ],
        },
    }
    packet = {
        "source_render_hash": "sha256:render",
        "render_status": "real_render",
        "page_text_index": [
            {
                "source_seq": 1,
                "source_ref": "word/document.xml:p[1]",
                "page_no": 1,
                "bbox": [1, 2, 3, 4],
                "render_target_id": "source_seq:1",
                "render_binding_status": "bound_exact_text",
            }
        ],
        "page_layout_index": [{"page_no": 1, "source_seq": 1}],
        "render_artifacts": {
            "render_engine": "fixture",
            "clean_page_images": [{"page_no": 1, "path": "page.png"}],
            "annotated_page_images": [{"page_no": 1, "path": "page.svg"}],
            "page_count": 1,
        },
    }

    contract = build_l1_input_contract(document_facts=facts, render_packet=packet)

    assert contract["artifact_type"] == "template_generation_l1_input_contract"
    assert contract["artifact_version"] == "2.0"
    assert contract["source_text_index"][0]["style_details"]["font"] == "黑体"
    assert contract["source_text_index"][0]["binding_status"] == "bound_exact_text"
    assert contract["source_object_index"][0]["binding_status"] == "via_text_anchor:bound_exact_text"
    assert contract["source_object_index"][0]["page_no"] == 1
    assert contract["layout_fact_index"]["fields"][0]["field_type"] == "PAGE"
    assert contract["visual_page_index"]["render_status"] == "real_render"
    assert contract["coverage"]["source_object_unbound_count"] == 0
    assert contract["run_index"]["raw_runs"][0]["text"] == "封面"
    assert contract["run_index"]["raw_runs"][0]["parent_source_seq"] == 1
    assert contract["run_index"]["logical_runs"][0]["raw_run_ids"] == [
        "p_0001.r_001"
    ]
    assert contract["coverage"]["raw_run_count"] == 1
    assert contract["coverage"]["logical_run_count"] == 1
    persisted = json.loads(json.dumps(contract, ensure_ascii=False, sort_keys=True))
    assert l1_artifact_hash(contract) == sha256_json(persisted)
    assert l1_artifact_hash(contract) == l1_artifact_hash(persisted)

    agent_packet = build_agent_stage_packet(contract)
    agent_row = agent_packet["page_text_index"][0]
    assert agent_row["kind"] == "paragraph"
    assert agent_row["paragraph_id"] == "p_0001"
    assert agent_row["style_details"].get("paragraph", {}) == {}
    assert agent_row["style_details"]["runs"] == [
        {
            "raw_run_id": "p_0001.r_001",
            "logical_run_id": "p_0001.lr_001",
            "text": "封面",
            "source_ref": "word/document.xml:p[1]/r[1]",
            "effective_style": {
                "font_names": ["黑体"],
                "font_size_pt": 16.0,
                "bold": True,
            },
        }
    ]
    field_object = next(
        item
        for item in agent_packet["object_fact_index"]
        if item.get("object_type") == "field"
    )
    assert field_object == {
        "object_id": "field:word/header1.xml:p[1]",
        "object_type": "field",
        "source_ref": "word/header1.xml:p[1]",
        "field_type": "PAGE",
    }


def test_l1_input_contract_marks_missing_render_and_unbound_objects() -> None:
    facts = {
        "artifact_type": "document_facts",
        "body_flow": [{"source_seq": 1, "source_ref": "word/document.xml:p[1]", "text": "正文"}],
        "data": {
            "sections": [],
            "headers_footers": [],
            "fields": [],
            "breaks": [],
            "images": [{"index": 1, "source_ref": "word/document.xml:p[9]/drawing[1]"}],
        },
    }

    contract = build_l1_input_contract(document_facts=facts)

    assert contract["visual_page_index"]["render_status"] == "not_available"
    assert contract["source_text_index"][0]["binding_status"] == "no_render_packet"
    assert contract["source_object_index"][0]["binding_status"] == "unbound_no_source_seq_anchor"
    assert contract["coverage"]["source_object_unbound_count"] == 1


def test_l1_input_contract_excludes_ai_and_quality_semantics() -> None:
    facts = {
        "artifact_type": "document_facts",
        "body_flow": [{"source_seq": 1, "source_ref": "word/document.xml:p[1]", "text": "封面"}],
        "data": {"sections": [], "headers_footers": [], "fields": [], "breaks": []},
    }
    packet = {
        "source_render_hash": "sha256:render",
        "render_status": "projection_fallback",
        "page_text_index": [{"source_seq": 1, "source_ref": "word/document.xml:p[1]"}],
        "page_layout_index": [],
        "render_artifacts": {},
    }
    contract = build_l1_input_contract(document_facts=facts, render_packet=packet)

    assert "bundle_gate_view" not in contract
    assert "ai_observation_bundle" not in contract["input_hashes"]
    assert "bundle_present" not in contract["coverage"]
    serialized = repr(contract)
    for forbidden in (
        "ai_unit_observation",
        "candidate_policy",
        "accepted_decision",
        "judge_status",
    ):
        assert forbidden not in serialized
