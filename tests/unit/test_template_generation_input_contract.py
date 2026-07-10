from __future__ import annotations

from docfit.template_generation.input_contract import build_l1_input_contract


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
                "style_details": {"font": "黑体"},
                "text_facts": {"char_count": 2},
                "raw_run_ids": ["p_0001.r_001"],
                "logical_run_ids": ["p_0001.lr_001"],
            }
        ],
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
    assert contract["source_text_index"][0]["style_details"] == {"font": "黑体"}
    assert contract["source_text_index"][0]["binding_status"] == "bound_exact_text"
    assert contract["source_object_index"][0]["binding_status"] == "via_text_anchor:bound_exact_text"
    assert contract["source_object_index"][0]["page_no"] == 1
    assert contract["layout_fact_index"]["fields"][0]["field_type"] == "PAGE"
    assert contract["visual_page_index"]["render_status"] == "real_render"
    assert contract["coverage"]["source_object_unbound_count"] == 0


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


def test_l1_input_contract_reports_observation_bundle_gate_errors() -> None:
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
    bundle = {
        "artifact_type": "ai_observation_bundle",
        "source_render_hash": "sha256:other",
        "ai_unit_observation": {
            "artifact_type": "ai_unit_observation",
            "source_render_hash": "sha256:other",
            "coverage": {"owned_source_seq": [], "unknown_source_seq": [], "total": 0},
            "items": [],
        },
    }

    contract = build_l1_input_contract(
        document_facts=facts,
        render_packet=packet,
        ai_observation_bundle=bundle,
    )

    assert contract["bundle_gate_view"]["source_render_hash_match"] is False
    assert contract["bundle_gate_view"]["stage_gates"]["ai_unit_observation"]["valid"] is False
    assert "ai_unit_observation" in contract["coverage"]["bundle_gate_invalid_stages"]
