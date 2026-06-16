from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from docx import Document

from docfit.core.io import now_iso, sha256_file
from docfit.ooxml.package import detect_unsupported_visible_objects, is_valid_docx


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def inspect_generated_template_docx(generated_template: Path) -> dict[str, Any]:
    tree: dict[str, Any] = {
        "artifact_type": "generated_template_tree",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-generated-template-inspector", "version": "0.1.0"},
        "created_at": now_iso(),
        "input_docx": str(generated_template),
        "input_exists": generated_template.exists(),
        "input_valid_docx": is_valid_docx(generated_template),
        "input_hashes": {},
        "source_kind": "generated_template_docx",
        "data": {
            "paragraphs": [],
            "tables": [],
            "headers_footers": [],
            "fields": [],
            "breaks": [],
            "numbering_refs": [],
            "unknown_visible_objects": [],
        },
    }
    if not tree["input_exists"] or not tree["input_valid_docx"]:
        return tree

    tree["input_hashes"]["generated_template_docx"] = sha256_file(generated_template)
    doc = Document(generated_template)
    paragraph_styles = _paragraph_style_details_by_index(generated_template)
    tree["data"]["paragraphs"] = _paragraphs(doc, paragraph_styles)
    tree["data"]["tables"] = _tables(doc)
    tree["data"].update(_inspect_ooxml_parts(generated_template))
    tree["data"]["unknown_visible_objects"] = detect_unsupported_visible_objects(
        generated_template
    )
    return tree


def iter_visible_text_entries(tree: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    data = tree.get("data", {})
    for paragraph in data.get("paragraphs", []):
        if paragraph.get("text"):
            entries.append(
                {
                    "kind": "paragraph",
                    "text": paragraph.get("text", ""),
                    "style": paragraph.get("style", ""),
                    "style_details": paragraph.get("style_details", {}),
                    "runs": paragraph.get("runs", []),
                    "source_ref": paragraph.get("source_ref", ""),
                    "order": paragraph.get("index", 0),
                }
            )
    for table in data.get("tables", []):
        for cell in table.get("cells", []):
            if cell.get("text"):
                entries.append(
                    {
                        "kind": "table_cell",
                        "text": cell.get("text", ""),
                        "style": table.get("style", ""),
                        "source_ref": cell.get("source_ref", ""),
                        "order": 10_000 + cell.get("global_index", 0),
                    }
                )
    for part in data.get("headers_footers", []):
        if part.get("text"):
            entries.append(
                {
                    "kind": part.get("kind", "header_footer"),
                    "text": part.get("text", ""),
                    "style": "",
                    "source_ref": part.get("source_ref", ""),
                    "order": 20_000 + part.get("index", 0),
                }
            )
    return entries


def _paragraphs(
    doc: Document,
    paragraph_styles: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    paragraphs: list[dict[str, Any]] = []
    for index, paragraph in enumerate(doc.paragraphs, start=1):
        text = paragraph.text.strip()
        if not text:
            continue
        style_details = paragraph_styles.get(index, {})
        runs = style_details.get("runs") or [
            {
                "text": run.text,
                "bold": run.bold,
                "italic": run.italic,
                "font_names": [run.font.name] if run.font.name else [],
                "font_size_pt": (
                    run.font.size.pt if run.font.size is not None else None
                ),
            }
            for run in paragraph.runs
            if run.text
        ]
        paragraphs.append(
            {
                "index": index,
                "text": text,
                "style": paragraph.style.name if paragraph.style is not None else "",
                "style_details": style_details,
                "runs": runs,
                "source_ref": f"word/document.xml:p[{index}]",
            }
        )
    return paragraphs


def _tables(doc: Document) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    global_cell_index = 0
    for table_index, table in enumerate(doc.tables, start=1):
        cells: list[dict[str, Any]] = []
        for row_index, row in enumerate(table.rows, start=1):
            for cell_index, cell in enumerate(row.cells, start=1):
                global_cell_index += 1
                text = "\n".join(
                    paragraph.text.strip()
                    for paragraph in cell.paragraphs
                    if paragraph.text.strip()
                )
                cells.append(
                    {
                        "row": row_index,
                        "column": cell_index,
                        "global_index": global_cell_index,
                        "text": text,
                        "source_ref": (
                            f"word/document.xml:tbl[{table_index}]"
                            f"/tr[{row_index}]/tc[{cell_index}]"
                        ),
                    }
                )
        tables.append(
            {
                "index": table_index,
                "style": table.style.name if table.style is not None else "",
                "row_count": len(table.rows),
                "column_count": max((len(row.cells) for row in table.rows), default=0),
                "cells": cells,
                "source_ref": f"word/document.xml:tbl[{table_index}]",
            }
        )
    return tables


def _paragraph_style_details_by_index(path: Path) -> dict[int, dict[str, Any]]:
    try:
        with ZipFile(path) as package:
            root = ET.fromstring(package.read("word/document.xml"))
    except (KeyError, ET.ParseError):
        return {}

    details: dict[int, dict[str, Any]] = {}
    for index, paragraph in enumerate(root.iter(f"{W_NS}p"), start=1):
        text = _visible_text(paragraph)
        if not text:
            continue
        paragraph_properties = paragraph.find(f"{W_NS}pPr")
        runs = [
            _run_style(run)
            for run in paragraph.findall(f"{W_NS}r")
            if _visible_text(run)
        ]
        details[index] = {
            "paragraph": _paragraph_style(paragraph_properties),
            "paragraph_run_properties": _run_properties(
                paragraph_properties.find(f"{W_NS}rPr")
                if paragraph_properties is not None
                else None
            ),
            "runs": runs,
            "dominant_run": _dominant_run_style(runs),
        }
    return details


def _paragraph_style(properties: ET.Element | None) -> dict[str, Any]:
    if properties is None:
        return {}
    style = properties.find(f"{W_NS}pStyle")
    alignment = properties.find(f"{W_NS}jc")
    spacing = properties.find(f"{W_NS}spacing")
    indent = properties.find(f"{W_NS}ind")
    return {
        "style_id": _attr(style, "val"),
        "alignment": _attr(alignment, "val"),
        "spacing": _spacing_style(spacing),
        "indent": _indent_style(indent),
        "page_break_before": properties.find(f"{W_NS}pageBreakBefore") is not None,
        "keep_next": properties.find(f"{W_NS}keepNext") is not None,
        "keep_lines": properties.find(f"{W_NS}keepLines") is not None,
    }


def _run_style(run: ET.Element) -> dict[str, Any]:
    properties = run.find(f"{W_NS}rPr")
    return {
        "text": _visible_text(run),
        **_run_properties(properties),
    }


def _run_properties(properties: ET.Element | None) -> dict[str, Any]:
    if properties is None:
        return {
            "font_names": [],
            "font_size_pt": None,
            "bold": None,
            "italic": None,
        }
    fonts = properties.find(f"{W_NS}rFonts")
    size = properties.find(f"{W_NS}sz")
    return {
        "font_names": _font_names(fonts),
        "font_size_pt": _half_points_to_points(_attr(size, "val")),
        "bold": _toggle_value(properties.find(f"{W_NS}b")),
        "italic": _toggle_value(properties.find(f"{W_NS}i")),
    }


def _dominant_run_style(runs: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        run
        for run in runs
        if _run_visible_for_style(str(run.get("text", "")))
    ]
    if not candidates:
        candidates = runs
    if not candidates:
        return {}
    return max(candidates, key=lambda run: len(str(run.get("text", "")).strip()))


def _run_visible_for_style(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and not (
        stripped.startswith("（") and stripped.endswith("）")
    )


def _spacing_style(spacing: ET.Element | None) -> dict[str, Any]:
    if spacing is None:
        return {}
    line = _attr(spacing, "line")
    line_rule = _attr(spacing, "lineRule")
    return {
        "before_pt": _twips_to_points(_attr(spacing, "before")),
        "after_pt": _twips_to_points(_attr(spacing, "after")),
        "line": line,
        "line_rule": line_rule,
        "line_spacing": _line_spacing(line, line_rule),
    }


def _indent_style(indent: ET.Element | None) -> dict[str, Any]:
    if indent is None:
        return {}
    return {
        "first_line_twips": _int_or_none(_attr(indent, "firstLine")),
        "left_twips": _int_or_none(_attr(indent, "left")),
        "right_twips": _int_or_none(_attr(indent, "right")),
    }


def _font_names(fonts: ET.Element | None) -> list[str]:
    if fonts is None:
        return []
    names = [
        _attr(fonts, "eastAsia"),
        _attr(fonts, "ascii"),
        _attr(fonts, "hAnsi"),
        _attr(fonts, "cs"),
    ]
    return [name for name in dict.fromkeys(names) if name]


def _toggle_value(element: ET.Element | None) -> bool | None:
    if element is None:
        return None
    value = _attr(element, "val")
    if value in {"0", "false", "False", "off"}:
        return False
    return True


def _attr(element: ET.Element | None, name: str) -> str | None:
    if element is None:
        return None
    return element.attrib.get(f"{W_NS}{name}")


def _half_points_to_points(value: str | None) -> float | None:
    number = _int_or_none(value)
    return number / 2 if number is not None else None


def _twips_to_points(value: str | None) -> float | None:
    number = _int_or_none(value)
    return number / 20 if number is not None else None


def _line_spacing(line: str | None, line_rule: str | None) -> str | None:
    number = _int_or_none(line)
    if number is None:
        return None
    if line_rule in {None, "auto"}:
        if number == 240:
            return "single"
        if number == 360:
            return "1.5"
        if number == 480:
            return "double"
    if line_rule == "exact":
        return f"exact:{number / 20:g}pt"
    return str(number)


def _int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _inspect_ooxml_parts(generated_template: Path) -> dict[str, list[dict[str, Any]]]:
    headers_footers: list[dict[str, Any]] = []
    fields: list[dict[str, Any]] = []
    breaks: list[dict[str, Any]] = []
    numbering_refs: list[dict[str, Any]] = []

    with ZipFile(generated_template) as package:
        part_names = [
            name
            for name in package.namelist()
            if name == "word/document.xml"
            or name.startswith("word/header")
            or name.startswith("word/footer")
        ]
        for part_index, part_name in enumerate(sorted(part_names), start=1):
            try:
                root = ET.fromstring(package.read(part_name))
            except ET.ParseError:
                continue
            if part_name.startswith("word/header") or part_name.startswith("word/footer"):
                headers_footers.append(
                    {
                        "index": part_index,
                        "kind": (
                            "header" if part_name.startswith("word/header") else "footer"
                        ),
                        "part_name": part_name,
                        "text": _visible_text(root),
                        "source_ref": part_name,
                    }
                )
            fields.extend(_fields(root, part_name))
            breaks.extend(_breaks(root, part_name))
            if part_name == "word/document.xml":
                numbering_refs.extend(_numbering_refs(root))

    return {
        "headers_footers": headers_footers,
        "fields": fields,
        "breaks": breaks,
        "numbering_refs": numbering_refs,
    }


def _visible_text(root: ET.Element) -> str:
    return "".join(node.text or "" for node in root.iter(f"{W_NS}t")).strip()


def _fields(root: ET.Element, part_name: str) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for index, node in enumerate(root.iter(f"{W_NS}instrText"), start=1):
        text = (node.text or "").strip()
        if not text:
            continue
        fields.append(
            {
                "index": index,
                "kind": "instrText",
                "instruction": text,
                "source_ref": f"{part_name}:instrText[{index}]",
            }
        )
    for index, node in enumerate(root.iter(f"{W_NS}fldSimple"), start=1):
        instruction = node.attrib.get(f"{W_NS}instr", "").strip()
        fields.append(
            {
                "index": index,
                "kind": "fldSimple",
                "instruction": instruction,
                "source_ref": f"{part_name}:fldSimple[{index}]",
            }
        )
    return fields


def _breaks(root: ET.Element, part_name: str) -> list[dict[str, Any]]:
    breaks: list[dict[str, Any]] = []
    for index, node in enumerate(root.iter(f"{W_NS}br"), start=1):
        breaks.append(
            {
                "index": index,
                "kind": "break",
                "type": node.attrib.get(f"{W_NS}type", "line"),
                "source_ref": f"{part_name}:br[{index}]",
            }
        )
    for index, _node in enumerate(root.iter(f"{W_NS}sectPr"), start=1):
        breaks.append(
            {
                "index": index,
                "kind": "section",
                "type": "section_properties",
                "source_ref": f"{part_name}:sectPr[{index}]",
            }
        )
    return breaks


def _numbering_refs(root: ET.Element) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    paragraph_index = 0
    for paragraph in root.iter(f"{W_NS}p"):
        paragraph_index += 1
        num_pr = paragraph.find(f".//{W_NS}numPr")
        if num_pr is None:
            continue
        refs.append(
            {
                "paragraph_index": paragraph_index,
                "source_ref": f"word/document.xml:p[{paragraph_index}]/numPr",
            }
        )
    return refs
