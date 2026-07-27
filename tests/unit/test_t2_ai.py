from __future__ import annotations

from pathlib import Path

import pytest

from docfit.core.io import sha256_file
from docfit.template_generation.agent.evidence import build_t2_evidence
from docfit.template_generation.agent.observation_multimodal import (
    anthropic_user_content,
)
from docfit.template_generation.t2_ai import (
    T2AIContractError,
    materialize_t2_ai_observation,
    materialize_t2_final_unit_map,
)
from docfit.template_generation.agent.t3_ai_materialize import (
    build_t3_source_structure,
)


def _packet(tmp_path: Path) -> dict:
    images = []
    for page_no in (1, 2, 3):
        path = tmp_path / f"page-{page_no}.png"
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        images.append(
            {
                "page_no": page_no,
                "path": str(path),
                "sha256": sha256_file(path),
                "width_px": 100,
                "height_px": 200,
            }
        )
    return {
        "input_contract_hash": "sha256:l1",
        "source_render_hash": "sha256:render",
        "render_status": "real_render",
        "render_artifacts": {
            "page_count": 3,
            "clean_page_images": images,
        },
        "page_text_index": [
            {
                "source_seq": 1,
                "source_ref": "word/document.xml:p[1]",
                "node_id": "p1",
                "page_no": 1,
                "render_binding_status": "exact",
                "text": "封面",
                "kind": "paragraph",
                "raw_run_ids": ["p1.r1"],
                "logical_run_ids": ["p1.lr1"],
            },
            {
                "source_seq": 2,
                "source_ref": "word/document.xml:p[2]",
                "node_id": "p2",
                "page_no": 2,
                "render_binding_status": "exact",
                "text": "目录",
                "kind": "paragraph",
                "raw_run_ids": ["p2.r1"],
                "logical_run_ids": ["p2.lr1"],
            },
            {
                "source_seq": 3,
                "source_ref": "word/document.xml:p[3]",
                "node_id": "p3",
                "page_no": 3,
                "render_binding_status": "exact",
                "text": "目录续页",
                "kind": "paragraph",
                "raw_run_ids": ["p3.r1"],
                "logical_run_ids": ["p3.lr1"],
            },
        ],
        "page_layout_index": [],
        "global_layout_facts": {"breaks": []},
    }


def _ai_payload() -> dict:
    return {
        "units": [
            {
                "unit_id": "cover",
                "unit_name": "封面",
                "boundary": {"start_page": 1, "end_page": 1},
            },
            {
                "unit_id": "toc",
                "unit_name": "目录",
                "boundary": {"start_page": 2, "end_page": 3},
            },
        ]
    }


def test_t2_ai_materializes_page_ranges_and_fixed_page_policy(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    observation = materialize_t2_ai_observation(
        _ai_payload(),
        packet=packet,
        model="MiniMax-M2.7",
    )
    unit_map = materialize_t2_final_unit_map(observation, packet=packet)

    assert observation["units"] == _ai_payload()["units"]
    assert unit_map["page_count"] == 3
    assert unit_map["units"][0] == {
        "unit_id": "cover",
        "unit_name": "封面",
        "order": 1,
        "boundary": {"start_page": 1, "end_page": 1},
        "page_refs": ["page:1"],
        "source_seq_refs": [1],
        "source_refs": ["word/document.xml:p[1]"],
        "source_seq_range": {"start": 1, "end": 1},
        "page_policy": {
            "start": "document_start",
            "scope": "page_range_exclusive",
        },
    }
    assert unit_map["units"][1]["source_seq_refs"] == [2, 3]
    assert unit_map["units"][1]["page_policy"] == {
        "start": "new_page",
        "scope": "page_range_exclusive",
    }


@pytest.mark.parametrize(
    "payload, message",
    [
        (
            {
                "units": [
                    {
                        "unit_id": "cover",
                        "unit_name": "封面",
                        "boundary": {"start_page": 1, "end_page": 1},
                    },
                    {
                        "unit_id": "body_main",
                        "unit_name": "正文",
                        "boundary": {"start_page": 3, "end_page": 3},
                    },
                ]
            },
            "without gap",
        ),
        (
            {
                "units": [
                    {
                        "unit_id": "cover",
                        "unit_name": "封面",
                        "boundary": {"start_page": 1, "end_page": 3},
                        "page_policy": {"start": "document_start"},
                    }
                ]
            },
            "page_policy",
        ),
        (
            {
                "units": [
                    {
                        "unit_id": "Cover",
                        "unit_name": "封面",
                        "boundary": {"start_page": 1, "end_page": 3},
                    }
                ]
            },
            "lower snake_case",
        ),
    ],
)
def test_t2_ai_rejects_contract_violations(
    tmp_path: Path,
    payload: dict,
    message: str,
) -> None:
    with pytest.raises(T2AIContractError, match=message):
        materialize_t2_ai_observation(payload, packet=_packet(tmp_path))


def test_t2_ai_rejects_one_source_node_crossing_unit_boundaries(
    tmp_path: Path,
) -> None:
    packet = _packet(tmp_path)
    packet["page_text_index"].append(
        {
            **packet["page_text_index"][0],
            "page_no": 2,
        }
    )
    observation = materialize_t2_ai_observation(
        _ai_payload(),
        packet=packet,
    )

    with pytest.raises(T2AIContractError, match="spans multiple T2 page groups"):
        materialize_t2_final_unit_map(observation, packet=packet)


def test_t2_ai_rejects_unresolved_page_binding(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    packet["page_text_index"][1]["render_binding_status"] = "ambiguous"

    with pytest.raises(T2AIContractError, match="page binding is unresolved"):
        materialize_t2_ai_observation(_ai_payload(), packet=packet)


def test_t2_ai_rejects_duplicate_page_images(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    packet["render_artifacts"]["clean_page_images"].append(
        dict(packet["render_artifacts"]["clean_page_images"][0])
    )

    with pytest.raises(T2AIContractError, match="duplicate page entries"):
        materialize_t2_ai_observation(_ai_payload(), packet=packet)


def test_t2_ai_rejects_page_image_hash_mismatch(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    packet["render_artifacts"]["clean_page_images"][0]["sha256"] = (
        "sha256:not-the-file-hash"
    )

    with pytest.raises(T2AIContractError, match="image hashes are invalid"):
        materialize_t2_ai_observation(_ai_payload(), packet=packet)


def test_t2_ignores_unbound_repeating_header_footer_rows(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    packet["page_text_index"].append(
        {
            "source_seq": 4,
            "source_ref": "word/header1.xml",
            "structure_layer": "header_footer",
            "page_no": None,
            "render_binding_status": "unbound",
            "text": "动态页眉",
        }
    )

    observation = materialize_t2_ai_observation(_ai_payload(), packet=packet)
    unit_map = materialize_t2_final_unit_map(observation, packet=packet)
    evidence = build_t2_evidence(packet)

    assert observation["validation"]["complete_page_coverage"] is True
    assert 4 not in {
        source_seq
        for unit in unit_map["units"]
        for source_seq in unit["source_seq_refs"]
    }
    assert all(
        row.get("source_seq") != 4
        for page in evidence["page_packets"]
        for row in page["content"]
    )


def test_t2_ignores_nonvisual_generated_slot_controls(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    packet["page_text_index"].append(
        {
            "source_seq": 4,
            "source_ref": "word/document.xml:sdt[1]",
            "structure_layer": "body_flow",
            "kind": "content_control",
            "page_no": 1,
            "render_binding_status": "ambiguous",
            "bbox": None,
            "text": "sdt:slot_body_start",
        }
    )

    observation = materialize_t2_ai_observation(_ai_payload(), packet=packet)
    unit_map = materialize_t2_final_unit_map(observation, packet=packet)
    evidence = build_t2_evidence(packet)

    assert observation["validation"]["complete_page_coverage"] is True
    assert 4 not in {
        source_seq
        for unit in unit_map["units"]
        for source_seq in unit["source_seq_refs"]
    }
    assert all(
        row.get("source_seq") != 4
        for page in evidence["page_packets"]
        for row in page["content"]
    )


def test_t2_evidence_and_multimodal_message_are_page_first(tmp_path: Path) -> None:
    evidence = build_t2_evidence(_packet(tmp_path))
    assert [page["page_no"] for page in evidence["page_packets"]] == [1, 2, 3]
    assert evidence["page_packets"][0]["content"][0]["text"] == "封面"

    content = anthropic_user_content("unused", evidence)
    assert isinstance(content, list)
    page_1_label = next(
        index
        for index, item in enumerate(content)
        if item.get("type") == "text" and item.get("text") == "page:1 图片"
    )
    assert content[page_1_label + 1]["type"] == "image"
    assert content[page_1_label + 2]["type"] == "text"
    assert "本页客观事实" in content[page_1_label + 2]["text"]


def test_t3_source_structure_uses_ai_units_without_code_inference(
    tmp_path: Path,
) -> None:
    packet = _packet(tmp_path)
    observation = materialize_t2_ai_observation(_ai_payload(), packet=packet)
    unit_map = materialize_t2_final_unit_map(observation, packet=packet)
    source_tree = {
        "layers": {
            "package_global": {"numbering_definitions": []},
            "section_rules": [],
            "header_footer": [],
            "body_flow": packet["page_text_index"],
            "unknown_objects": [],
        },
        "indexes": {
            "body_order": [1, 2, 3],
            "by_source_ref": {},
            "by_source_seq": {},
            "runs_by_raw_run_id": {},
            "runs_by_source_ref": {},
        },
        "data": {"paragraphs": []},
        "input_hashes": {"l1": "sha256:l1"},
    }

    shell = build_t3_source_structure(source_tree, unit_map)

    assert shell["source_method"] == (
        "ai_page_groups_with_deterministic_l1_binding"
    )
    assert [unit["unit_id"] for unit in shell["units"]] == ["cover", "toc"]
    assert shell["units"][1]["elements"][0]["content"] == "目录"
