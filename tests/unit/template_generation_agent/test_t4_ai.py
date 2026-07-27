from __future__ import annotations

from typing import Any

from docfit.template_generation.t4_ai import publish_t4_ai_final


def _packet() -> dict[str, Any]:
    return {
        "input_contract_hash": "sha256:l1",
        "source_render_hash": "sha256:render",
        "page_text_index": [
            {"source_seq": 1},
            {"source_seq": 2},
        ],
    }


def _observation() -> dict[str, Any]:
    return {
        "artifact_type": "ai_layout_observation",
        "source_render_hash": "sha256:render",
        "input_contract_hash": "sha256:l1",
        "abstain": False,
        "items": [
            {
                "section_profile_id": "section_001",
                "source_ref": "word/document.xml:body/sectPr",
                "boundary": {
                    "start_source_seq": 1,
                    "end_source_seq": 2,
                    "confidence": "high",
                },
                "source_seq_refs": [1, 2],
                "page_setup": {"orientation": "portrait"},
                "header_footer": [],
                "page_numbering": {"format": "decimal"},
                "evidence_refs": [
                    {"page_no": 1, "render_target_id": "page:1"}
                ],
            }
        ],
        "coverage": {
            "total": 2,
            "owned_source_seq": [1, 2],
            "unknown_source_seq": [],
        },
        "default_font": {"name": "宋体"},
        "page_numbering": {"status": "single"},
        "header_footer": [],
        "numbering_rules": [],
    }


def test_t4_ai_observation_is_the_only_final_source() -> None:
    result = publish_t4_ai_final(_observation(), packet=_packet())

    assert result.availability == "AVAILABLE"
    assert result.payload["lineage"]["producer_mode"] == "ai"
    assert result.payload["lineage"]["selected_from"][0]["artifact"] == (
        "04.1_t4_ai_layout_observation.yaml"
    )
    assert result.payload["section_profiles"][0]["origin"] == (
        "ai_layout_observation"
    )


def test_t4_ai_abstention_has_no_code_fallback() -> None:
    observation = {**_observation(), "abstain": True, "items": []}

    result = publish_t4_ai_final(observation, packet=_packet())

    assert result.availability == "NOT_AVAILABLE"
    assert result.payload["section_profiles"] == []
    assert result.payload["lineage"]["producer_mode"] == "ai"


def test_t4_ai_rejects_cross_run_observation() -> None:
    observation = {**_observation(), "source_render_hash": "sha256:other"}

    result = publish_t4_ai_final(observation, packet=_packet())

    assert result.availability == "NOT_AVAILABLE"
    assert "source render" in str(result.reason)
    assert result.payload["section_profiles"] == []
