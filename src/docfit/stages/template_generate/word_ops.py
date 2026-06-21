from __future__ import annotations

from copy import deepcopy
from typing import Any

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import _Cell
from docx.text.paragraph import Paragraph

from .refs import _cell_for_ref, _paragraph_for_ref


def _clear_cell(cell: _Cell) -> None:
    for paragraph in list(cell.paragraphs):
        _remove_paragraph(paragraph)
    if not cell.paragraphs:
        cell.add_paragraph("")


def _insert_marker(
    doc: Document,
    paragraph_map: dict[int, Paragraph],
    source_ref: str | None,
    marker: str,
) -> str:
    target = _paragraph_for_ref(paragraph_map, source_ref)
    if target is not None:
        _insert_paragraph_after(target, marker)
        return f"{source_ref}/after:{marker}"
    target_cell = _cell_for_ref(doc, source_ref)
    if target_cell is not None:
        target_cell.add_paragraph(marker)
        return f"{source_ref}/p[last]:{marker}"
    return _append_marker(doc, marker)


def _insert_page_break_before(
    doc: Document,
    paragraph_map: dict[int, Paragraph],
    source_ref: str | None,
) -> str | None:
    target = _paragraph_for_ref(paragraph_map, source_ref)
    if target is not None:
        target.paragraph_format.page_break_before = True
        return f"{source_ref}/pageBreakBefore"
    target_cell = _cell_for_ref(doc, source_ref)
    if target_cell is not None and target_cell.paragraphs:
        target_cell.paragraphs[0].paragraph_format.page_break_before = True
        return f"{source_ref}/p[1]/pageBreakBefore"
    return None


def _insert_section_break_before(
    doc: Document,
    paragraph_map: dict[int, Paragraph],
    source_ref: str | None,
) -> str | None:
    target = _paragraph_for_ref(paragraph_map, source_ref)
    if target is None:
        return None
    boundary = _insert_paragraph_before(target, "")
    paragraph_properties = boundary._p.get_or_add_pPr()
    paragraph_properties.append(_next_page_section_properties(doc))
    return f"{source_ref}/before:sectPr"


def _insert_styled_paragraph_before(
    paragraph_map: dict[int, Paragraph],
    source_ref: str | None,
    text: str,
    *,
    page_break_before: bool = False,
) -> str | None:
    target = _paragraph_for_ref(paragraph_map, source_ref)
    if target is None:
        return None
    inserted = _insert_paragraph_before(target, text)
    inserted.style = target.style
    inserted.alignment = target.alignment
    inserted.paragraph_format.page_break_before = page_break_before
    return f"{source_ref}/before:{text}"


def _next_page_section_properties(doc: Document) -> Any:
    section_properties = deepcopy(doc.sections[0]._sectPr)
    for child in list(section_properties):
        if child.tag == qn("w:type"):
            section_properties.remove(child)
    section_type = OxmlElement("w:type")
    section_type.set(qn("w:val"), "nextPage")
    section_properties.insert(0, section_type)
    return section_properties


def _insert_paragraph_before(paragraph: Paragraph, text: str) -> Paragraph:
    new_element = OxmlElement("w:p")
    paragraph._p.addprevious(new_element)
    new_paragraph = Paragraph(new_element, paragraph._parent)
    if text:
        new_paragraph.add_run(text)
    return new_paragraph


def _insert_paragraph_after(paragraph: Paragraph, text: str) -> Paragraph:
    new_element = OxmlElement("w:p")
    paragraph._p.addnext(new_element)
    new_paragraph = Paragraph(new_element, paragraph._parent)
    new_paragraph.add_run(text)
    return new_paragraph


def _append_marker(doc: Document, marker: str) -> str:
    doc.add_paragraph(marker)
    return f"word/document.xml:p[{len(doc.paragraphs)}]"


def _find_marker_ref(doc: Document, marker: str) -> str | None:
    for index, paragraph in enumerate(doc.paragraphs, start=1):
        if marker in paragraph.text:
            return f"word/document.xml:p[{index}]"
    return None


def _remove_paragraph(paragraph: Paragraph) -> None:
    element = paragraph._element
    parent = element.getparent()
    if parent is not None:
        parent.remove(element)
