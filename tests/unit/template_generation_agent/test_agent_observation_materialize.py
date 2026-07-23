from __future__ import annotations

from typing import Any

from docfit.template_generation.agent.observation_materialize import (
    materialize_layout_observation,
    materialize_unit_observation,
)
from docfit.template_generation.agent.packet import (
    build_template_agent_render_packet,
    packet_source_seq_set,
)

from .helpers import document_facts


def clean_packet() -> dict[str, Any]:
    return build_template_agent_render_packet(
        document_facts=document_facts(),
        structure_candidates={},
    )


def demotion_checks(observation: dict[str, Any]) -> set[str]:
    return {d["check_id"] for d in observation["quality_report"]["demotions"]}


def test_unit_label_closure_demotes_unknown_taxonomy() -> None:
    packet = clean_packet()
    obs = materialize_unit_observation(
        [{"unit_id": "not_a_real_unit", "source_seq_refs": [1]}],
        packet=packet,
    )
    assert obs["items"] == []
    assert "C-LABEL-CLOSURE" in demotion_checks(obs)
    # 降级后 source_seq 落入 unknown，不 silent gap。
    assert 1 in obs["coverage"]["unknown_source_seq"]


def test_unit_evidence_binding_demotes_unbound_refs() -> None:
    packet = clean_packet()
    obs = materialize_unit_observation(
        [{"unit_id": "cover", "source_seq_refs": [9999]}],
        packet=packet,
    )
    assert obs["items"] == []
    assert "C-EVIDENCE-BIND" in demotion_checks(obs)


def test_unit_coverage_invariant_holds_after_materialize() -> None:
    packet = clean_packet()
    all_seq = packet_source_seq_set(packet)
    obs = materialize_unit_observation(
        [{"unit_id": "cover", "source_seq_refs": sorted(all_seq), "confidence": "high"}],
        packet=packet,
    )
    owned = set(obs["coverage"]["owned_source_seq"])
    unknown = set(obs["coverage"]["unknown_source_seq"])
    assert owned | unknown == all_seq
    assert owned & unknown == set()


def test_unit_materialize_does_not_revive_legacy_page_policy_fields() -> None:
    packet = clean_packet()
    seq = sorted(packet_source_seq_set(packet))[0]
    obs = materialize_unit_observation(
        [
            {
                "unit_id": "cover",
                "source_seq_refs": [seq],
                "confidence": "high",
                "page_break": "document_start",
                "page_isolation": True,
                "allow_multi_page": False,
                "keep_together": True,
                "evidence_refs": ["page:1"],
            }
        ],
        packet=packet,
    )

    assert obs["items"][0]["page_policy"] == {
        "start": "unknown",
        "scope": "unknown",
    }
    assert "page" not in obs["items"][0]
    assert "page_break" not in obs["items"][0]


def test_unit_materialize_preserves_unit_page_policy_without_legacy_page() -> None:
    packet = clean_packet()
    seq = sorted(packet_source_seq_set(packet))[0]
    obs = materialize_unit_observation(
        [
            {
                "unit_id": "cover",
                "source_seq_refs": [seq],
                "confidence": "high",
                "page_policy": {
                    "start": "document_start",
                    "scope": "single_page_exclusive",
                },
            }
        ],
        packet=packet,
    )

    assert obs["items"][0]["page_policy"] == {
        "start": "document_start",
        "scope": "single_page_exclusive",
    }
    assert "page" not in obs["items"][0]
    assert "page_break" not in obs["items"][0]


def test_unit_materialize_orders_units_by_source_seq_not_ai_order() -> None:
    packet = clean_packet()
    seqs = sorted(packet_source_seq_set(packet))
    obs = materialize_unit_observation(
        [
            {
                "unit_id": "body_main",
                "source_seq_refs": [seqs[1]],
                "confidence": "high",
                "order": 99,
            },
            {
                "unit_id": "cover",
                "source_seq_refs": [seqs[0]],
                "confidence": "high",
                "order": 99,
            },
        ],
        packet=packet,
    )

    assert [item["unit_id"] for item in obs["items"]] == ["cover", "body_main"]
    assert [item["order"] for item in obs["items"]] == [0, 1]


def test_unit_overlap_higher_confidence_wins() -> None:
    packet = clean_packet()
    seqs = sorted(packet_source_seq_set(packet))
    obs = materialize_unit_observation(
        [
            {"unit_id": "cover", "source_seq_refs": seqs[:1], "confidence": "high"},
            {"unit_id": "body_main", "source_seq_refs": seqs[:1], "confidence": "low"},
        ],
        packet=packet,
    )
    winners = {item["unit_id"] for item in obs["items"]}
    assert "cover" in winners
    assert "body_main" not in winners
    assert "C-COVERAGE-OVERLAP" in demotion_checks(obs)


def test_layout_visual_abstains_without_facts_or_images() -> None:
    # 无分节事实(helpers sections=[]) 且无页图 → 无确定性 profile → 仍整体弃权。
    packet = clean_packet()
    obs = materialize_layout_observation(
        {"section_profiles": [{"section_profile_id": "s1"}]},
        packet=packet,
        render_available=False,
    )
    assert obs["abstain"] is True
    assert obs["visual_abstained"] is True
    assert "C-LAYOUT-VISUAL-ABSTAIN" in demotion_checks(obs)


def test_layout_track_a_deterministic_profile_from_facts() -> None:
    # 有分节事实 + 无页图 → Track A 确定性全局 profile；不整体 abstain，仅视觉子项弃权。
    packet = clean_packet()
    packet["global_layout_facts"] = {
        "sections": [
            {
                "index": 1,
                "page_margins": {"top_pt": 56.7, "left_pt": 73.7},
                "page_size": {"width_pt": 595.3, "height_pt": 841.9, "orientation": "portrait"},
                "page_numbering": {"format": "decimal", "start": None},
                "references": [{"kind": "header", "type": "default", "part_name": "word/header1.xml"}],
            }
        ],
        "header_footer": [{"kind": "header", "part_name": "word/header1.xml", "has_content": False}],
        "numbering_definition_count": 0,
    }
    obs = materialize_layout_observation({"section_profiles": []}, packet=packet, render_available=False)
    assert obs["abstain"] is False  # 有确定性 profile
    assert obs["visual_abstained"] is True  # 视觉子项仍弃权
    assert obs["page_structure_source"] == "unavailable_no_render"
    assert len(obs["items"]) == 1
    profile = obs["items"][0]
    assert profile["source"] == "deterministic_facts"
    assert profile["page_setup"]["page_size"]["orientation"] == "portrait"
    assert profile["page_numbering"]["format"] == "decimal"


def test_layout_track_b_deterministic_page_facts_when_rendered() -> None:
    # 有真实页图渲染 → page_layout_index 带 per-seq page_no → 确定性页结构，无模型。
    packet = clean_packet()
    packet["global_layout_facts"] = {
        "sections": [{"index": 1, "page_margins": {"top_pt": 56.7}, "page_size": {"orientation": "portrait"}}],
        "header_footer": [],
        "numbering_definition_count": 0,
    }
    # 模拟渲染产出的 per-seq 真实页码（helpers packet 有 source_seq 1..4）
    packet["page_layout_index"] = [
        {"source_seq": 1, "page_no": 1},
        {"source_seq": 2, "page_no": 1},
        {"source_seq": 3, "page_no": 2},
        {"source_seq": 4, "page_no": 3},
    ]
    obs = materialize_layout_observation({"section_profiles": []}, packet=packet, render_available=True)
    assert obs["visual_abstained"] is False
    assert obs["page_structure_source"] == "deterministic_pdf_layout"
    assert obs["page_count"] == 3
    assert obs["page_map"] == {"1": 1, "2": 1, "3": 2, "4": 3}
    assert obs["items"][0]["pages"] == [1, 2, 3]


def test_layout_aggregates_vision_page_observations() -> None:
    packet = clean_packet()
    packet["global_layout_facts"] = {"sections": [{"index": 1, "page_size": {}}], "header_footer": []}
    packet["page_layout_index"] = [{"source_seq": 1, "page_no": 1}, {"source_seq": 2, "page_no": 2}]
    page_obs = [
        {"page_no": 1, "has_header": False, "has_footer": False, "page_number_visible": False, "page_number_text": ""},
        {"page_no": 2, "has_header": True, "has_footer": True, "page_number_visible": True, "page_number_text": "1"},
    ]
    obs = materialize_layout_observation(
        {"section_profiles": []}, packet=packet, render_available=True, page_observations=page_obs
    )
    assert obs["vision_source"] == "minimax_m3"
    assert len(obs["page_observations"]) == 2
    assert obs["header_footer_policy"]["pages_with_header"] == [2]
    assert obs["header_footer_policy"]["pages_with_footer"] == [2]
    assert obs["page_numbering_display"]["pages_with_visible_number"] == [2]
    assert obs["page_numbering_display"]["samples"] == [{"page_no": 2, "text": "1"}]
