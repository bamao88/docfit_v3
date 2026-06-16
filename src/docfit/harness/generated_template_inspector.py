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
    tree["data"]["paragraphs"] = _paragraphs(doc)
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


def _paragraphs(doc: Document) -> list[dict[str, Any]]:
    paragraphs: list[dict[str, Any]] = []
    for index, paragraph in enumerate(doc.paragraphs, start=1):
        text = paragraph.text.strip()
        if not text:
            continue
        paragraphs.append(
            {
                "index": index,
                "text": text,
                "style": paragraph.style.name if paragraph.style is not None else "",
                "runs": [
                    {
                        "text": run.text,
                        "bold": run.bold,
                        "italic": run.italic,
                        "font_name": run.font.name,
                        "font_size_pt": (
                            run.font.size.pt if run.font.size is not None else None
                        ),
                    }
                    for run in paragraph.runs
                    if run.text
                ],
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
