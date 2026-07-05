from __future__ import annotations

from copy import deepcopy
import re
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


def _clear_runs_by_raw_run_ids(
    paragraph: Paragraph,
    source_ref: str | None,
    raw_run_ids: list[str],
) -> str | None:
    source_paragraph_index = _source_ref_paragraph_index(source_ref)
    run_indices: list[int] = []
    for raw_run_id in raw_run_ids:
        parsed = _parse_raw_run_id(raw_run_id)
        if parsed is None:
            return None
        paragraph_index, run_index = parsed
        if (
            source_paragraph_index is not None
            and paragraph_index != source_paragraph_index
        ):
            return None
        run_indices.append(run_index)
    runs = list(paragraph.runs)
    if not run_indices or any(index < 1 or index > len(runs) for index in run_indices):
        return None
    for run_index in sorted(set(run_indices)):
        runs[run_index - 1].text = ""
    joined = ",".join(raw_run_ids)
    return f"{source_ref}/runs[{joined}]:cleared"


def _replace_run_text_ranges(
    paragraph: Paragraph,
    source_ref: str | None,
    ranges: list[dict[str, Any]],
) -> str | None:
    source_paragraph_index = _source_ref_paragraph_index(source_ref)
    runs = list(paragraph.runs)
    grouped: dict[int, list[dict[str, Any]]] = {}
    for item in ranges:
        raw_run_id = str(item.get("raw_run_id") or "")
        parsed = _parse_raw_run_id(raw_run_id)
        if parsed is None:
            return None
        paragraph_index, run_index = parsed
        if (
            source_paragraph_index is not None
            and paragraph_index != source_paragraph_index
        ):
            return None
        if run_index < 1 or run_index > len(runs):
            return None
        grouped.setdefault(run_index, []).append(item)
    if not grouped:
        return None
    for run_index, replacements in grouped.items():
        run = runs[run_index - 1]
        text = run.text
        for item in sorted(replacements, key=lambda value: int(value.get("start") or 0), reverse=True):
            start = int(item.get("start") or 0)
            end = int(item.get("end") or start)
            if start < 0 or end < start or end > len(text):
                return None
            replacement = str(item.get("replacement") or "")
            text = f"{text[:start]}{replacement}{text[end:]}"
        run.text = text
    joined = ",".join(
        f"{item.get('raw_run_id')}:{item.get('start')}-{item.get('end')}"
        for item in ranges
    )
    return f"{source_ref}/char_ranges[{joined}]:replaced"


def _source_ref_paragraph_index(source_ref: str | None) -> int | None:
    if not source_ref:
        return None
    match = re.search(r"word/document\.xml:p\[(\d+)\]", source_ref)
    return int(match.group(1)) if match else None


def _parse_raw_run_id(raw_run_id: str) -> tuple[int, int] | None:
    match = re.search(r"(?:^|\.)p_(\d{4})\.r_(\d{3})$", raw_run_id)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


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


def _insert_sdt(
    doc: Document,
    paragraph_map: dict[int, Paragraph],
    source_ref: str | None,
    tag: str,
    *,
    alias: str | None = None,
    placeholder: str = "",
) -> str:
    target = _paragraph_for_ref(paragraph_map, source_ref)
    if target is not None:
        _insert_sdt_after(target, tag, alias=alias, placeholder=placeholder)
        return f"{source_ref}/after:sdt[{tag}]"
    target_cell = _cell_for_ref(doc, source_ref)
    if target_cell is not None:
        _append_sdt_to_parent(target_cell._tc, tag, alias=alias, placeholder=placeholder)
        return f"{source_ref}/sdt[{tag}]"
    return _append_sdt(doc, tag, alias=alias, placeholder=placeholder)


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


def _insert_sdt_after(
    paragraph: Paragraph,
    tag: str,
    *,
    alias: str | None = None,
    placeholder: str = "",
) -> None:
    paragraph._p.addnext(_sdt_block(tag, alias=alias, placeholder=placeholder))


def _append_sdt(doc: Document, tag: str, *, alias: str | None = None, placeholder: str = "") -> str:
    block = _sdt_block(tag, alias=alias, placeholder=placeholder)
    section_properties = doc.element.body.sectPr
    if section_properties is not None:
        section_properties.addprevious(block)
    else:
        doc.element.body.append(block)
    return f"word/document.xml:sdt[{tag}]"


def _append_sdt_to_parent(
    parent: Any,
    tag: str,
    *,
    alias: str | None = None,
    placeholder: str = "",
) -> None:
    parent.append(_sdt_block(tag, alias=alias, placeholder=placeholder))


def _sdt_block(tag: str, *, alias: str | None = None, placeholder: str = "") -> Any:
    sdt = OxmlElement("w:sdt")
    sdt_pr = OxmlElement("w:sdtPr")
    alias_node = OxmlElement("w:alias")
    alias_node.set(qn("w:val"), alias or tag)
    tag_node = OxmlElement("w:tag")
    tag_node.set(qn("w:val"), tag)
    sdt_pr.append(alias_node)
    sdt_pr.append(tag_node)
    sdt_content = OxmlElement("w:sdtContent")
    paragraph = OxmlElement("w:p")
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    if placeholder:
        text.text = placeholder
    run.append(text)
    paragraph.append(run)
    sdt_content.append(paragraph)
    sdt.append(sdt_pr)
    sdt.append(sdt_content)
    return sdt


def _append_marker(doc: Document, marker: str) -> str:
    doc.add_paragraph(marker)
    return f"word/document.xml:p[{_body_paragraph_count(doc)}]"


def _find_marker_ref(doc: Document, marker: str) -> str | None:
    paragraph_index_by_element_id = {
        id(paragraph_element): index
        for index, paragraph_element in enumerate(doc.element.body.iter(qn("w:p")), start=1)
    }
    for index, paragraph in enumerate(doc.paragraphs, start=1):
        if marker in paragraph.text:
            paragraph_index = paragraph_index_by_element_id.get(id(paragraph._p), index)
            return f"word/document.xml:p[{paragraph_index}]"
    return None


def _body_paragraph_count(doc: Document) -> int:
    return sum(1 for _ in doc.element.body.iter(qn("w:p")))


def _find_sdt_tag_ref(doc: Document, tag: str) -> str | None:
    for index, sdt in enumerate(doc.element.body.iter(qn("w:sdt")), start=1):
        tag_node = next(iter(sdt.iter(qn("w:tag"))), None)
        if tag_node is not None and tag_node.get(qn("w:val")) == tag:
            return f"word/document.xml:sdt[{index}:{tag}]"
    return None


def _remove_paragraph(paragraph: Paragraph) -> None:
    element = paragraph._element
    parent = element.getparent()
    if parent is not None:
        parent.remove(element)
