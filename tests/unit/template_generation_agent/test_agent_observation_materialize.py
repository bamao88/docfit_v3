from __future__ import annotations

from typing import Any

from docfit.template_generation.agent.observation_materialize import (
    materialize_element_observation,
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


def test_element_required_field_demotes_fill_without_source() -> None:
    packet = clean_packet()
    seqs = sorted(packet_source_seq_set(packet))
    window = {"window_id": "unit:cover", "unit_id": "cover", "source_seq_refs": seqs[:1]}
    obs = materialize_element_observation(
        [{"element_id": "cover.001", "policy": "fill", "source_seq_refs": seqs[:1]}],
        packet=packet,
        window=window,
    )
    assert obs["items"] == []
    assert "C-REQUIRED-FIELD" in demotion_checks(obs)


def test_element_accepts_valid_fill_with_source() -> None:
    packet = clean_packet()
    seqs = sorted(packet_source_seq_set(packet))
    window = {"window_id": "unit:cover", "unit_id": "cover", "source_seq_refs": seqs[:1]}
    obs = materialize_element_observation(
        [
            {
                "element_id": "cover.001",
                "policy": "fill",
                "fill_source": "student_content",
                "source_seq_refs": seqs[:1],
            }
        ],
        packet=packet,
        window=window,
    )
    assert len(obs["items"]) == 1
    assert obs["items"][0]["policy"] == "fill"


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
    assert len(obs["items"]) == 1
    profile = obs["items"][0]
    assert profile["source"] == "deterministic_facts"
    assert profile["page_setup"]["page_size"]["orientation"] == "portrait"
    assert profile["page_numbering"]["format"] == "decimal"
