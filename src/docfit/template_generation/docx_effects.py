from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from docfit.core.io import sha256_file
from docfit.ooxml.package import is_valid_docx


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def inspect_docx_layout_effects(path: Path) -> dict[str, object]:
    if not is_valid_docx(path):
        return {
            "status": "UNKNOWN",
            "output_docx_hash": sha256_file(path) if path.exists() else None,
            "reason": "invalid_docx",
        }
    try:
        with ZipFile(path) as package:
            root = ET.fromstring(package.read("word/document.xml"))
    except Exception as exc:
        return {
            "status": "UNKNOWN",
            "output_docx_hash": sha256_file(path),
            "reason": repr(exc),
        }

    paragraph_effects = _paragraph_effect_refs(root)
    table_cant_split_refs = _table_cant_split_refs(root)
    page_break_before_count = sum(
        1 for element in root.iter(f"{W_NS}pageBreakBefore") if _is_enabled(element)
    )
    explicit_page_break_count = sum(
        1
        for element in root.iter(f"{W_NS}br")
        if element.attrib.get(f"{W_NS}type") == "page"
    )
    keep_with_next_count = sum(
        1 for element in root.iter(f"{W_NS}keepNext") if _is_enabled(element)
    )
    keep_together_count = sum(
        1 for element in root.iter(f"{W_NS}keepLines") if _is_enabled(element)
    )
    paragraph_section_break_count = sum(
        len(paragraph_properties.findall(f"{W_NS}sectPr"))
        for paragraph_properties in root.iter(f"{W_NS}pPr")
    )
    body_section_properties_count = sum(
        len(body.findall(f"{W_NS}sectPr")) for body in root.iter(f"{W_NS}body")
    )
    return {
        "status": "PASS",
        "output_docx_hash": sha256_file(path),
        "page_break_before_count": page_break_before_count,
        "explicit_page_break_count": explicit_page_break_count,
        "observable_page_break_count": page_break_before_count
        + explicit_page_break_count,
        "paragraph_section_break_count": paragraph_section_break_count,
        "body_section_properties_count": body_section_properties_count,
        "keep_with_next_count": keep_with_next_count,
        "keep_together_count": keep_together_count,
        "page_break_before_refs": paragraph_effects["page_break_before_refs"],
        "explicit_page_break_refs": paragraph_effects["explicit_page_break_refs"],
        "page_break_refs": _dedupe_str(
            [
                *paragraph_effects["page_break_before_refs"],
                *paragraph_effects["explicit_page_break_refs"],
            ]
        ),
        "section_break_refs": paragraph_effects["section_break_refs"],
        "keep_with_next_refs": paragraph_effects["keep_with_next_refs"],
        "keep_lines_refs": paragraph_effects["keep_lines_refs"],
        "keep_combined_refs": paragraph_effects["keep_combined_refs"],
        "table_cant_split_refs": table_cant_split_refs,
        "keep_effect_refs": _dedupe_str(
            [
                *paragraph_effects["keep_with_next_refs"],
                *paragraph_effects["keep_lines_refs"],
                *paragraph_effects["keep_combined_refs"],
                *table_cant_split_refs,
            ]
        ),
    }


def _is_enabled(element: ET.Element) -> bool:
    value = str(element.attrib.get(f"{W_NS}val") or "true").lower()
    return value not in {"0", "false", "off", "no"}


def _paragraph_effect_refs(root: ET.Element) -> dict[str, list[str]]:
    effects = {
        "page_break_before_refs": [],
        "explicit_page_break_refs": [],
        "direct_section_break_refs": [],
        "section_break_refs": [],
        "keep_with_next_refs": [],
        "keep_lines_refs": [],
        "keep_combined_refs": [],
    }
    paragraphs = list(root.iter(f"{W_NS}p"))
    for paragraph_index, paragraph in enumerate(paragraphs, start=1):
        _collect_paragraph_effect_refs(
            paragraph,
            f"word/document.xml:p[{paragraph_index}]",
            effects,
        )
        paragraph_properties = paragraph.find(f"{W_NS}pPr")
        if paragraph_properties is None:
            continue
        section_breaks = paragraph_properties.findall(f"{W_NS}sectPr")
        if not section_breaks:
            continue
        direct_ref = f"word/document.xml:p[{paragraph_index}]/sectPr"
        effects["direct_section_break_refs"].append(direct_ref)
        effects["section_break_refs"].append(direct_ref)
        if paragraph_index < len(paragraphs):
            effects["section_break_refs"].append(
                f"word/document.xml:p[{paragraph_index + 1}]/before:sectPr"
            )

    for table_index, table in enumerate(root.iter(f"{W_NS}tbl"), start=1):
        for row_index, row in enumerate(table.findall(f"{W_NS}tr"), start=1):
            for cell_index, cell in enumerate(row.findall(f"{W_NS}tc"), start=1):
                for local_paragraph_index, paragraph in enumerate(
                    cell.findall(f"{W_NS}p"),
                    start=1,
                ):
                    _collect_paragraph_effect_refs(
                        paragraph,
                        (
                            f"word/document.xml:tbl[{table_index}]"
                            f"/tr[{row_index}]/tc[{cell_index}]"
                            f"/p[{local_paragraph_index}]"
                        ),
                        effects,
                    )

    return {key: _dedupe_str(value) for key, value in effects.items()}


def _collect_paragraph_effect_refs(
    paragraph: ET.Element,
    paragraph_ref: str,
    effects: dict[str, list[str]],
) -> None:
    paragraph_properties = paragraph.find(f"{W_NS}pPr")
    has_keep_next = False
    has_keep_lines = False
    if paragraph_properties is not None:
        page_break_before = paragraph_properties.find(f"{W_NS}pageBreakBefore")
        if page_break_before is not None and _is_enabled(page_break_before):
            effects["page_break_before_refs"].append(f"{paragraph_ref}/pageBreakBefore")
        keep_next = paragraph_properties.find(f"{W_NS}keepNext")
        if keep_next is not None and _is_enabled(keep_next):
            has_keep_next = True
            effects["keep_with_next_refs"].append(f"{paragraph_ref}/keepWithNext")
        keep_lines = paragraph_properties.find(f"{W_NS}keepLines")
        if keep_lines is not None and _is_enabled(keep_lines):
            has_keep_lines = True
            effects["keep_lines_refs"].append(f"{paragraph_ref}/keepLines")
    if has_keep_next and has_keep_lines:
        effects["keep_combined_refs"].append(f"{paragraph_ref}/keepWithNext+keepLines")

    for break_index, break_element in enumerate(
        paragraph.iter(f"{W_NS}br"),
        start=1,
    ):
        if break_element.attrib.get(f"{W_NS}type") == "page":
            effects["explicit_page_break_refs"].append(f"{paragraph_ref}/br[{break_index}]")


def _table_cant_split_refs(root: ET.Element) -> list[str]:
    refs: list[str] = []
    for table_index, table in enumerate(root.iter(f"{W_NS}tbl"), start=1):
        for row_index, row in enumerate(table.findall(f"{W_NS}tr"), start=1):
            cant_split = row.find(f"{W_NS}trPr/{W_NS}cantSplit")
            if cant_split is not None and _is_enabled(cant_split):
                refs.append(f"word/document.xml:tbl[{table_index}]/tr[{row_index}]/cantSplit")
    return refs


def _dedupe_str(values: list[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result
