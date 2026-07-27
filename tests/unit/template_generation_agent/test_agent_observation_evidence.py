from __future__ import annotations

from typing import Any

import pytest

from docfit.template_generation.agent.evidence import (
    EvidenceFirewallError,
    EVIDENCE_FIELD_WHITELIST,
    assert_firewall_clean,
    build_t2_evidence,
    build_t4_evidence,
)
from docfit.template_generation.agent.packet import build_template_agent_render_packet

from .helpers import document_facts


def clean_packet() -> dict[str, Any]:
    return build_template_agent_render_packet(
        document_facts=document_facts(),
    )


def test_firewall_passes_clean_view() -> None:
    view = {"rows": [{"source_seq": 1, "text": "封面", "style": "Normal"}]}
    assert_firewall_clean(view)  # no raise


def test_firewall_blocks_code_conclusion_key() -> None:
    leaked = {"rows": [{"source_seq": 1, "unit_map": {"unit_id": "cover"}}]}
    with pytest.raises(EvidenceFirewallError):
        assert_firewall_clean(leaked)


def test_firewall_blocks_t1_policy_leak() -> None:
    # 真实 T1 产物把 template_policy/final_disposition 混进 paragraphs；必须挡住。
    leaked = {"rows": [{"source_seq": 1, "text": "封面", "template_policy": "fixed"}]}
    with pytest.raises(EvidenceFirewallError):
        assert_firewall_clean(leaked)


def test_firewall_blocks_expected_prefix() -> None:
    with pytest.raises(EvidenceFirewallError):
        assert_firewall_clean({"expected_unit_id": "cover"})


def test_firewall_ignores_string_values_like_task_lists() -> None:
    # packet 自带 forbidden_ai_tasks 的字符串值（write_unit_map 等）不应误报。
    view = {"forbidden_ai_tasks": ["write_unit_map", "write_element_spec"]}
    assert_firewall_clean(view)  # no raise


def test_t2_evidence_is_firewall_clean_and_whitelisted() -> None:
    packet = clean_packet()
    view = build_t2_evidence(packet)
    assert view["scope"] == "t2_page_groups"
    assert view["page_packets"] == []
    assert_firewall_clean(view)


def test_t2_evidence_projects_compact_page_and_break_facts_without_local_paths() -> None:
    packet = clean_packet()
    packet["render_status"] = "real_render"
    packet["render_artifacts"] = {
        "page_count": 2,
        "clean_page_images": [
            {
                "page_no": 1,
                "path": "/private/tmp/page-01.png",
                "sha256": "sha256:page-1",
                "width_px": 900,
                "height_px": 1200,
                "image_type": "png",
            }
        ],
    }
    packet["page_text_index"] = [
        {
            "source_seq": 1,
            "source_ref": "word/document.xml:p[1]",
            "order": 1,
            "page_no": 1,
            "render_target_id": "source_seq:1",
            "render_binding_status": "exact",
            "flow_item_type": "paragraph",
            "text": "封面",
            "style": "Title",
            "text_facts": {
                "alignment": "center",
                "char_count": 2,
                "dominant_bold": True,
                "has_tab": False,
                "normalized_text": "封面",
            },
        },
        {
            "source_seq": 2,
            "source_ref": "word/document.xml:p[2]",
            "order": 2,
            "page_no": 2,
            "render_target_id": "source_seq:2",
            "render_binding_status": "exact",
            "flow_item_type": "paragraph",
            "text": "摘要",
            "style": "Heading 1",
        },
    ]
    packet["page_layout_index"] = [
        {
            "source_seq": 1,
            "page_no": 1,
            "page_top_ratio": 0.2,
            "tier": 1,
            "bbox": {"y_max": 240, "page_height": 1200},
        },
        {
            "source_seq": 2,
            "page_no": 2,
            "page_top_ratio": 0.05,
            "tier": 1,
            "bbox": {"y_max": 180, "page_height": 1200},
        },
    ]
    packet["global_layout_facts"] = {
        "breaks": [
            {
                "index": 1,
                "kind": "section",
                "type": "section_properties",
                "paragraph_index": 1,
                "source_ref": "word/document.xml:p[1]/sectPr",
                "template_policy": "must_not_leak",
            }
        ]
    }

    view = build_t2_evidence(packet)

    assert view["render_available"] is True
    assert view["document_summary"] == {"source_seq_count": 2, "page_count": 2}
    assert [page["page_no"] for page in view["page_packets"]] == [1, 2]
    assert view["page_packets"][0]["content"][0]["text_facts"] == {
        "alignment": "center",
        "dominant_bold": True,
    }
    assert view["page_packets"][1]["content"][0]["page_position"] == {
        "starts_new_rendered_page": True,
        "page_top_ratio": 0.05,
    }
    assert view["page_packets"][0]["break_facts"] == [
        {
            "index": 1,
            "kind": "section",
            "type": "section_properties",
            "paragraph_index": 1,
            "after_source_seq": 1,
        }
    ]
    assert view["page_thumbnails"] == [
        {
            "page_no": 1,
            "sha256": "sha256:page-1",
            "width_px": 900,
            "height_px": 1200,
            "image_type": "png",
        }
    ]
    assert view["visual_evidence"] == [
        {
            "page_no": 1,
            "sha256": "sha256:page-1",
            "width_px": 900,
            "height_px": 1200,
            "image_type": "png",
            "visual_ref": "page:1",
            "_attachment_path": "/private/tmp/page-01.png",
        }
    ]
    assert view["_visual_attachment_limit"] == 1
    assert "/private/tmp" not in repr(view["page_thumbnails"])


def test_t2_evidence_does_not_infer_rendered_page_position_from_projection() -> None:
    view = build_t2_evidence(clean_packet())

    assert view["render_available"] is False
    assert view["page_packets"] == []
    assert view["visual_evidence"] == []


def test_t2_evidence_marks_only_page_start_and_aligns_body_section_to_last_seq() -> None:
    packet = clean_packet()
    packet["render_status"] = "real_render"
    packet["render_artifacts"] = {
        "page_count": 1,
        "clean_page_images": [{"page_no": 1, "path": "/tmp/page-1.png"}],
    }
    packet["page_text_index"] = [
        {"source_seq": 1, "order": 1, "page_no": 1, "text": "第一行"},
        {"source_seq": 2, "order": 2, "page_no": 1, "text": "第二行"},
    ]
    packet["global_layout_facts"] = {
        "breaks": [
            {
                "index": 1,
                "kind": "section",
                "type": "section_properties",
                "paragraph_index": None,
                "source_ref": "word/document.xml:body/sectPr",
            }
        ]
    }

    view = build_t2_evidence(packet)

    rows = view["page_packets"][0]["content"]
    assert rows[0]["page_position"] == {"starts_new_rendered_page": True}
    assert "page_position" not in rows[1]
    assert view["page_packets"][0]["break_facts"][0]["after_source_seq"] == 2


def test_t4_evidence_marks_render_unavailable_for_projection_fallback() -> None:
    packet = clean_packet()
    view = build_t4_evidence(packet)
    # 测试 fixture 无真实页图 → render_available False → 上层强制 abstain。
    assert view["render_available"] is False


def test_t4_evidence_includes_layout_fields_headers_and_breaks() -> None:
    facts = document_facts()
    facts["data"]["headers_footers"] = [
        {
            "kind": "footer",
            "part_name": "word/footer1.xml",
            "text": "第 1 页",
            "paragraphs": [
                {
                    "index": 1,
                    "text": "第 1 页",
                    "source_ref": "word/footer1.xml:p[1]",
                }
            ],
            "source_ref": "word/footer1.xml",
        }
    ]
    facts["data"]["fields"] = [
        {
            "index": 1,
            "kind": "fldSimple",
            "field_type": "PAGE",
            "instruction": "PAGE",
            "part_name": "word/footer1.xml",
            "source_ref": "word/footer1.xml:p[1]/field[1]",
        }
    ]
    facts["data"]["breaks"] = [
        {
            "index": 1,
            "kind": "break",
            "type": "page",
            "paragraph_index": 2,
            "source_ref": "word/document.xml:p[2]/r[1]/br[1]",
        }
    ]
    packet = build_template_agent_render_packet(
        document_facts=facts,
    )

    view = build_t4_evidence(packet)
    facts_view = view["global_layout_facts"]
    assert facts_view["header_footer"][0]["text"] == "第 1 页"
    assert facts_view["fields"][0]["field_type"] == "PAGE"
    assert facts_view["breaks"][0]["type"] == "page"
