from __future__ import annotations

import pytest

from docfit.template_generation.source_tree import (
    _body_flow_from_inspection,
    _runs_from_inspection,
)
from docfit.template_generation.structure_candidates import _structural_signals


def _run(
    text: str,
    *,
    font_names: list[str] | None = None,
    font_size_pt: float | None = 18.0,
    bold: bool | None = True,
    italic: bool | None = False,
    underline: str | bool | None = None,
    color: str | None = None,
) -> dict[str, object]:
    return {
        "text": text,
        "font_names": font_names or ["SimHei"],
        "font_size_pt": font_size_pt,
        "bold": bold,
        "italic": italic,
        "underline": underline,
        "color": color,
    }


def _paragraph(index: int, runs: list[dict[str, object]]) -> dict[str, object]:
    text = "".join(str(run["text"]) for run in runs)
    return {
        "index": index,
        "xml_index": index,
        "text": text,
        "style": "Normal",
        "style_details": {"style_inheritance": {}},
        "runs": runs,
        "source_ref": f"word/document.xml:p[{index}]",
    }


def _tree(paragraphs: list[dict[str, object]]) -> dict[str, object]:
    return {"data": {"paragraphs": paragraphs}}


def _logical_runs_for_paragraph(
    run_index: dict[str, object],
    paragraph_id: str,
) -> list[dict[str, object]]:
    return [
        run
        for run in run_index["runs"]
        if run["paragraph_id"] == paragraph_id
    ]


def test_runs_from_inspection_merges_adjacent_runs_with_same_effective_style() -> None:
    paragraphs = [
        _paragraph(1, [_run("目"), _run("录")]),
        _paragraph(
            2,
            [
                _run("南京农业"),
                _run("大学"),
                _run("本科"),
                _run("生"),
                _run("毕业"),
                _run("论文"),
                _run("（设计）原"),
                _run("创性声明"),
            ],
        ),
        _paragraph(3, [_run("摘要"), _run("（三号"), _run("黑体）")]),
        _paragraph(
            4,
            [
                _run("A", bold=True),
                _run("B", bold=False),
                _run("C", bold=True),
            ],
        ),
        _paragraph(
            5,
            [
                _run("U", underline="single"),
                _run("V", underline="single"),
                _run("W", underline=False),
                _run("X", color="ff0000"),
                _run("Y", color="ff0000"),
            ],
        ),
    ]

    run_index = _runs_from_inspection(_tree(paragraphs))

    toc_runs = _logical_runs_for_paragraph(run_index, "p_0001")
    assert [run["text"] for run in toc_runs] == ["目录"]
    assert toc_runs[0]["merged_from"] == ["p_0001.r_001", "p_0001.r_002"]

    title_runs = _logical_runs_for_paragraph(run_index, "p_0002")
    assert [run["text"] for run in title_runs] == [
        "南京农业大学本科生毕业论文（设计）原创性声明"
    ]
    assert len(title_runs[0]["merged_from"]) == 8

    abstract_runs = _logical_runs_for_paragraph(run_index, "p_0003")
    assert [run["text"] for run in abstract_runs] == ["摘要（三号黑体）"]
    assert len(abstract_runs[0]["merged_from"]) == 3

    separated_runs = _logical_runs_for_paragraph(run_index, "p_0004")
    assert [run["text"] for run in separated_runs] == ["A", "B", "C"]

    styled_runs = _logical_runs_for_paragraph(run_index, "p_0005")
    assert [run["text"] for run in styled_runs] == ["UV", "W", "XY"]

    raw_text = "".join(
        str(run["text"])
        for paragraph in paragraphs
        for run in paragraph["runs"]
    )
    logical_text = "".join(str(run["text"]) for run in run_index["runs"])
    assert logical_text == raw_text

    raw_run_count = sum(len(paragraph["runs"]) for paragraph in paragraphs)
    merged_raw_ids = [
        raw_run_id
        for run in run_index["runs"]
        for raw_run_id in run["merged_from"]
    ]
    assert len(merged_raw_ids) == raw_run_count
    assert len(set(merged_raw_ids)) == raw_run_count
    assert set(run_index["logical_by_raw"]) == set(merged_raw_ids)
    assert set(run_index["runs_by_raw_run_id"]) == set(merged_raw_ids)
    for raw_run_id in merged_raw_ids:
        assert run_index["runs_by_raw_run_id"][raw_run_id]["raw_run_id"] == raw_run_id


def test_body_flow_deduplicates_logical_run_ids_but_preserves_raw_run_ids() -> None:
    paragraph = _paragraph(1, [_run("摘"), _run("要")])
    tree = _tree([paragraph])
    run_index = _runs_from_inspection(tree)

    body_flow = _body_flow_from_inspection(tree, run_index)

    assert body_flow[0]["text"] == "摘要"
    assert body_flow[0]["raw_run_ids"] == ["p_0001.r_001", "p_0001.r_002"]
    assert body_flow[0]["logical_run_ids"] == ["p_0001.lr_001"]


@pytest.mark.parametrize(
    ("text", "style"),
    [
        ("□□摘要……………………1", ""),
        ("摘 要\tⅠ", ""),
        ("1 绪论\t23", ""),
        ("摘要", "TOC 1"),
    ],
)
def test_structural_signals_identify_toc_entries(text: str, style: str) -> None:
    signals = _structural_signals({"text": text, "style": style})

    assert signals["is_toc_entry"] is True


@pytest.mark.parametrize(
    ("text", "style"),
    [("目录", "TOC 1"), ("目  录", "TOC 1"), ("摘要1", ""), ("摘要", "")],
)
def test_structural_signals_do_not_treat_titles_as_toc_entries(
    text: str,
    style: str,
) -> None:
    signals = _structural_signals({"text": text, "style": style})

    assert signals["is_toc_entry"] is False


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "（空三行）",
        "（五号字空一行）",
        "（根据题目长短四号字空二或三行）",
        "(空2格)",
    ],
)
def test_structural_signals_identify_spacing_lines(text: str) -> None:
    signals = _structural_signals({"text": text})

    assert signals["is_spacing_line"] is True


@pytest.mark.parametrize("text", ["（一号黑体加粗）", "摘要（三号黑体）", "空三行"])
def test_structural_signals_do_not_treat_format_notes_as_spacing_lines(
    text: str,
) -> None:
    signals = _structural_signals({"text": text})

    assert signals["is_spacing_line"] is False
