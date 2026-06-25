from __future__ import annotations

from typing import Any

from docfit.template_generation.structure_candidates import (
    _structural_signals,
    _toc_entry_like,
    build_template_structure_candidates,
    canonical_title,
)


def _units_by_id(candidates: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {unit["unit_id"]: unit for unit in candidates["units"]}


def _unit_at_seq(candidates: dict[str, Any], seq: int) -> dict[str, Any]:
    for unit in candidates["units"]:
        if seq in (unit.get("source_seq_refs") or []):
            return unit
    raise AssertionError(f"no unit owns source_seq {seq}")


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


def test_t2_ignores_legacy_t1_structural_signals_when_deriving_toc() -> None:
    toc_entry = _entry(3, "摘要\tⅠ", style="toc 1")
    toc_entry["structural_signals"] = {"is_toc_entry": False}
    candidates = build_template_structure_candidates(
        _source_tree(
            [
                _entry(1, "封面"),
                _entry(2, "目录"),
                toc_entry,
                _entry(4, "摘要", style="Heading 1"),
                _entry(5, "正文", style="Heading 1"),
            ]
        )
    )

    toc = next(unit for unit in candidates["units"] if unit["unit_id"] == "toc")

    assert "word/document.xml:p[3]" in toc["source_refs"]


def test_t2_text_properties_only_is_candidate_not_unit_boundary() -> None:
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

    # text_properties alone must not open a top-level unit (plan §6.5).
    assert not [
        unit
        for unit in candidates["units"]
        if unit["source_range"].get("start_source_ref") == "word/document.xml:p[2]"
    ]

    candidate_questions = [
        question
        for question in candidates["open_questions"]
        if question["kind"] == "boundary_candidate"
        and question["interval"].get("start_source_ref") == "word/document.xml:p[2]"
    ]
    assert len(candidate_questions) == 1
    assert candidate_questions[0]["candidate_reason"] == "text_properties_only"
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


def test_t2_toc_block_claims_all_toc_entries() -> None:
    # TOC entries whose text contains body/reference keywords must stay in `toc`
    # and must not let the body_main fallback anchor inside the TOC block.
    candidates = build_template_structure_candidates(
        _source_tree(
            [
                _entry(1, "封面"),
                _entry(2, "目  录", style="Heading 1", alignment="center"),
                _entry(3, "摘要…………………1", style="toc 1"),
                _entry(4, "第一章 文献综述…………2", style="toc 1"),
                _entry(5, "参考文献…………………9", style="toc 1"),
                _entry(6, "正文", style="Heading 1"),
                _entry(7, "参考文献", style="Heading 1"),
            ]
        )
    )

    units = _units_by_id(candidates)
    assert units["toc"]["source_refs"] == [
        "word/document.xml:p[2]",
        "word/document.xml:p[3]",
        "word/document.xml:p[4]",
        "word/document.xml:p[5]",
    ]
    # body_main must start at the real heading, not the TOC entry "第一章 …".
    assert units["body_main"]["source_range"]["start_source_ref"] == "word/document.xml:p[6]"
    assert _unit_at_seq(candidates, 4)["unit_id"] == "toc"


def test_t2_subheading_alone_is_not_top_level_unit() -> None:
    candidates = build_template_structure_candidates(
        _source_tree(
            [
                _entry(1, "封面"),
                _entry(2, "正文", style="Heading 1"),
                _entry(3, "二级小节标题", style="Heading 2"),
                _entry(4, "正文段落内容"),
            ]
        )
    )

    # The level-2 heading must not open its own unit; it stays inside body_main.
    assert _unit_at_seq(candidates, 3)["unit_id"] == "body_main"
    candidate_questions = [
        question
        for question in candidates["open_questions"]
        if question["kind"] == "boundary_candidate"
        and question["interval"].get("start_source_ref") == "word/document.xml:p[3]"
    ]
    assert candidate_questions and candidate_questions[0]["candidate_reason"] == "subheading_only"


def test_t2_custom_unit_not_other_for_high_confidence_unknown_heading() -> None:
    candidates = build_template_structure_candidates(
        _source_tree(
            [
                _entry(1, "封面"),
                _entry(2, "研究方案设计", style="Heading 1"),
                _entry(3, "方案内容段落"),
                _entry(4, "正文", style="Heading 1"),
            ]
        )
    )

    unknown = _unit_at_seq(candidates, 2)
    assert unknown is not None
    assert unknown["unit_id"].startswith("custom:template:")
    assert unknown["label_status"] == "custom_detected"
    assert unknown["canonical_label_id"] is None
    assert unknown["display_name"] == "研究方案设计"
    assert not [unit for unit in candidates["units"] if unit["unit_id"] == "other"]
    assert any(
        entry["normalized_title"] == "研究方案设计"
        for entry in candidates["taxonomy_review_queue"]
    )


def test_t2_repeated_core_section_becomes_custom_not_other() -> None:
    candidates = build_template_structure_candidates(
        _source_tree(
            [
                _entry(1, "封面"),
                _entry(2, "参考文献", style="Heading 1"),
                _entry(3, "致谢", style="Heading 1"),
                _entry(4, "参考文献", style="Heading 1"),
            ]
        )
    )

    second = _unit_at_seq(candidates, 4)
    assert second["unit_id"].startswith("custom:template:")
    assert second["label_status"] == "custom_detected"
    assert any(flag["type"] == "unit_label_repeated_custom" for flag in second["flags"])
    assert not [unit for unit in candidates["units"] if unit["unit_id"] == "other"]


def test_t2_table_cell_is_not_a_unit_boundary() -> None:
    cell = _entry(2, "Stage 1", alignment="center", font_size_pt=18.0, bold=True)
    cell["kind"] = "table_cell"
    cell["source_ref"] = "word/document.xml:tbl[1]/tr[1]/tc[1]"
    candidates = build_template_structure_candidates(
        _source_tree(
            [
                _entry(1, "封面"),
                cell,
                _entry(3, "正文", style="Heading 1"),
            ]
        )
    )

    assert _unit_at_seq(candidates, 2)["unit_id"] != "other"
    assert _unit_at_seq(candidates, 2)["unit_id"] in {"cover", "body_main"}


def test_t2_canonical_title_strips_format_annotations_and_placeholders() -> None:
    assert canonical_title("摘□要（三号黑体）") == "摘要"
    assert canonical_title("目□□录   (二号黑体，居中)") == "目录"
    assert canonical_title("□□Abstract(小四号Times New Roman, 加粗)") == "abstract"


def test_t2_derives_toc_entry_like_from_atomic_facts() -> None:
    # leader + page number, Normal style — derived purely from atomic text facts.
    assert _toc_entry_like(_entry(1, "□□摘要……………………1"))
    # tab + roman page number
    assert _toc_entry_like(_entry(2, "摘  要\tⅠ", style="toc 1"))
    # a plain centered title is not a TOC entry
    assert not _toc_entry_like(_entry(3, "目录", alignment="center"))


def _toc_coverage_for_real_template(school: str) -> tuple[int, int]:
    """Return (toc_entries_in_toc, toc_entries_leaked_to_other_units)."""
    import pathlib

    import pytest

    from docfit.template_generation.artifacts import source_tree_from_document_facts
    from docfit.template_generation.source_tree import inspect_document_facts_docx

    docx = pathlib.Path("inputs/targets") / school / "raw/source_template.docx"
    if not docx.exists():
        pytest.skip(f"{docx} not available")

    source_tree = source_tree_from_document_facts(inspect_document_facts_docx(docx))
    candidates = build_template_structure_candidates(source_tree)
    seq_to_unit: dict[int, str] = {}
    for unit in candidates["units"]:
        for ref in unit.get("source_seq_refs", []) or []:
            seq_to_unit[int(ref)] = str(unit["unit_id"])

    toc_seqs = [
        int(entry["source_seq"])
        for entry in source_tree["layers"]["body_flow"]
        if entry.get("structure_layer") == "body_flow"
        and entry.get("text")
        and entry.get("source_seq") is not None
        and _toc_entry_like(entry)
    ]
    in_toc = sum(1 for seq in toc_seqs if seq_to_unit.get(seq) == "toc")
    leaked = sum(1 for seq in toc_seqs if seq_to_unit.get(seq) not in (None, "toc"))
    return in_toc, leaked


def test_t2_hunan_toc_20_of_20_without_ai() -> None:
    in_toc, leaked = _toc_coverage_for_real_template("hunannongye")
    assert in_toc == 20
    assert leaked == 0


def test_t2_nannong_toc_25_of_25_without_ai() -> None:
    in_toc, leaked = _toc_coverage_for_real_template("nannong-undergraduate")
    assert in_toc == 25
    assert leaked == 0


def test_t2_pku_toc_17_of_17_without_ai() -> None:
    in_toc, leaked = _toc_coverage_for_real_template("pku-graduate")
    assert in_toc == 17
    assert leaked == 0
