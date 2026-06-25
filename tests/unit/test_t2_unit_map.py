from __future__ import annotations

from typing import Any

from docfit.template_generation.structure_candidates import (
    _structural_signals,
    build_template_structure_candidates,
)


def _entry(
    index: int,
    text: str,
    *,
    style: str = "Normal",
    alignment: str | None = None,
    font_size_pt: float | None = None,
    bold: bool | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "node_id": f"body_{index:04d}",
        "structure_layer": "body_flow",
        "flow_item_type": "paragraph",
        "kind": "paragraph",
        "source_ref": f"word/document.xml:p[{index}]",
        "part_name": "word/document.xml",
        "order": index,
        "paragraph_id": f"p_{index:04d}",
        "visible": True,
        "text": text,
        "style": style,
        "style_details": {
            "paragraph": {
                "style_name": style,
                "style_id": style,
                "alignment": alignment,
            },
            "dominant_run": {
                "font_size_pt": font_size_pt,
                "bold": bold,
            },
        },
        "source_seq": index,
    }
    entry["structural_signals"] = _structural_signals(entry)
    return entry


def _source_tree(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "metadata": {"source_template_hash": "sha256:test"},
        "layers": {"body_flow": entries},
        "indexes": {},
        "data": {"breaks": [], "sections": [], "paragraphs": []},
    }


def test_t2_vetoes_toc_entries_before_keyword_labeling() -> None:
    candidates = build_template_structure_candidates(
        _source_tree(
            [
                _entry(1, "封面"),
                _entry(2, "目录"),
                _entry(3, "摘要……1", style="toc 1"),
                _entry(4, "1 前言……2", style="toc 1"),
                _entry(5, "参考文献……9", style="toc 1"),
                _entry(6, "摘要", style="Heading 1"),
                _entry(7, "摘要正文"),
                _entry(8, "正文", style="Heading 1"),
                _entry(9, "参考文献", style="Heading 1"),
            ]
        )
    )

    units = {unit["unit_id"]: unit for unit in candidates["units"]}

    assert units["toc"]["source_refs"] == [
        "word/document.xml:p[2]",
        "word/document.xml:p[3]",
        "word/document.xml:p[4]",
        "word/document.xml:p[5]",
    ]
    assert units["abstract_cn"]["source_range"]["start_source_ref"] == "word/document.xml:p[6]"
    assert units["body_main"]["source_range"]["start_source_ref"] == "word/document.xml:p[8]"
    assert units["references"]["source_range"]["start_source_ref"] == "word/document.xml:p[9]"


def test_t2_text_properties_can_create_low_confidence_other_boundary() -> None:
    candidates = build_template_structure_candidates(
        _source_tree(
            [
                _entry(1, "封面"),
                _entry(
                    2,
                    "承诺书",
                    alignment="center",
                    font_size_pt=18.0,
                    bold=True,
                ),
                _entry(3, "正文", style="Heading 1"),
            ]
        )
    )

    other = next(unit for unit in candidates["units"] if unit["unit_id"] == "other")
    question_kinds = {question["kind"] for question in candidates["open_questions"]}

    assert other["source_range"]["start_source_ref"] == "word/document.xml:p[2]"
    assert other["confidence"] == "low"
    assert any(flag["type"] == "unit_label_unknown" for flag in other["flags"])
    assert {"label", "boundary"} <= question_kinds
    assert candidates["t2_input"]["artifact_type"] == "t2_input"


def test_t2_heading_style_and_keyword_agreement_is_high_confidence() -> None:
    candidates = build_template_structure_candidates(
        _source_tree(
            [
                _entry(1, "封面"),
                _entry(2, "摘要", style="Heading 1"),
                _entry(3, "摘要正文"),
                _entry(4, "正文", style="Heading 1"),
            ]
        )
    )

    abstract = next(unit for unit in candidates["units"] if unit["unit_id"] == "abstract_cn")

    assert abstract["confidence"] == "high"
    assert not [
        question
        for question in candidates["open_questions"]
        if question["interval"].get("start_source_ref") == "word/document.xml:p[2]"
    ]
