from __future__ import annotations

import re
from typing import Any

from docx import Document
from docx.oxml.ns import qn
from docx.table import _Cell
from docx.text.paragraph import Paragraph


def _first_source_ref(item: dict[str, Any]) -> str | None:
    refs = item.get("source_refs")
    if isinstance(refs, list) and refs:
        return str(refs[0])
    ref = item.get("source_ref")
    return str(ref) if ref else None


def _source_seq_refs(item: dict[str, Any]) -> list[int]:
    refs = item.get("source_seq_refs")
    if isinstance(refs, list):
        return [int(ref) for ref in refs if ref is not None]
    seq = item.get("source_seq")
    return [int(seq)] if seq is not None else []


def _paragraph_index(source_ref: str | None) -> int | None:
    if not source_ref:
        return None
    match = re.search(r"word/document\.xml:p\[(\d+)\]", source_ref)
    return int(match.group(1)) if match else None


def _paragraph_for_ref(
    paragraph_map: dict[int, Paragraph],
    source_ref: str | None,
) -> Paragraph | None:
    index = _paragraph_index(source_ref)
    if index is None:
        return None
    return paragraph_map.get(index)


def _paragraph_map_by_ooxml_index(doc: Document) -> dict[int, Paragraph]:
    top_level_by_element_id = {id(paragraph._p): paragraph for paragraph in doc.paragraphs}
    paragraph_map: dict[int, Paragraph] = {}
    for index, paragraph_element in enumerate(
        doc.element.body.iter(qn("w:p")),
        start=1,
    ):
        paragraph = top_level_by_element_id.get(id(paragraph_element))
        if paragraph is not None:
            paragraph_map[index] = paragraph
    return paragraph_map


def _cell_for_ref(doc: Document, source_ref: str | None) -> _Cell | None:
    if not source_ref:
        return None
    match = re.search(
        r"word/document\.xml:tbl\[(\d+)\]/tr\[(\d+)\]/tc\[(\d+)\]",
        source_ref,
    )
    if not match:
        return None
    table_index, row_index, cell_index = (int(value) - 1 for value in match.groups())
    try:
        return doc.tables[table_index].rows[row_index].cells[cell_index]
    except IndexError:
        return None


def _part_name(source_ref: str | None) -> str:
    if not source_ref:
        return ""
    return source_ref.split(":", 1)[0]
