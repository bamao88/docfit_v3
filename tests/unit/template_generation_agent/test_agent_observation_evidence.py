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
        structure_candidates={},
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
    assert view["rows"], "expected non-empty evidence rows"
    allowed = set(EVIDENCE_FIELD_WHITELIST["t2"])
    for row in view["rows"]:
        assert set(row).issubset(allowed)


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
        structure_candidates={},
    )

    view = build_t4_evidence(packet)
    facts_view = view["global_layout_facts"]
    assert facts_view["header_footer"][0]["text"] == "第 1 页"
    assert facts_view["fields"][0]["field_type"] == "PAGE"
    assert facts_view["breaks"][0]["type"] == "page"
