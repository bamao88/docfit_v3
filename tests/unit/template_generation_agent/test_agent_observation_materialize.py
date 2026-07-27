from __future__ import annotations

from typing import Any

from docfit.template_generation.agent.observation_materialize import (
    materialize_layout_observation,
)
from docfit.template_generation.agent.packet import (
    build_template_agent_render_packet,
)

from .helpers import document_facts


def clean_packet() -> dict[str, Any]:
    return build_template_agent_render_packet(
        document_facts=document_facts(),
    )


def demotion_checks(observation: dict[str, Any]) -> set[str]:
    return {d["check_id"] for d in observation["quality_report"]["demotions"]}


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


def test_layout_does_not_fall_back_to_deterministic_section_facts() -> None:
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
    obs = materialize_layout_observation(
        {"section_profiles": []},
        packet=packet,
        render_available=False,
    )
    assert obs["abstain"] is True
    assert obs["items"] == []
    assert obs["visual_abstained"] is True
    assert obs["page_structure_source"] == "unavailable_no_render"


def test_layout_materializes_only_ai_profiles_and_binds_render_pages() -> None:
    packet = clean_packet()
    packet["page_layout_index"] = [
        {"source_seq": 1, "page_no": 1},
        {"source_seq": 2, "page_no": 1},
        {"source_seq": 3, "page_no": 2},
        {"source_seq": 4, "page_no": 3},
    ]
    obs = materialize_layout_observation(
        {
            "section_profiles": [
                {
                    "section_profile_id": "s1",
                    "boundary": {
                        "start_source_seq": 1,
                        "end_source_seq": 4,
                        "confidence": "high",
                    },
                    "page_setup": {"orientation": "portrait"},
                    "evidence_refs": [
                        {"page_no": 1, "render_target_id": "page:1"}
                    ],
                }
            ]
        },
        packet=packet,
        render_available=True,
    )
    assert obs["abstain"] is False
    assert obs["visual_abstained"] is False
    assert obs["page_structure_source"] == "sealed_render_binding"
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
        {
            "section_profiles": [
                {
                    "section_profile_id": "s1",
                    "boundary": {
                        "start_source_seq": 1,
                        "end_source_seq": 2,
                        "confidence": "high",
                    },
                    "evidence_refs": [
                        {"page_no": 1, "render_target_id": "page:1"}
                    ],
                }
            ]
        },
        packet=packet,
        render_available=True,
        page_observations=page_obs,
    )
    assert obs["vision_source"] == "minimax_m3"
    assert len(obs["page_observations"]) == 2
    assert obs["header_footer_policy"]["pages_with_header"] == [2]
    assert obs["header_footer_policy"]["pages_with_footer"] == [2]
    assert obs["page_numbering_display"]["pages_with_visible_number"] == [2]
    assert obs["page_numbering_display"]["samples"] == [{"page_no": 2, "text": "1"}]
