from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from docfit.core.io import now_iso, sha256_file
from docfit.template_gap.inspector import (
    inspect_generated_template_docx,
    iter_visible_text_entries,
)

from .artifacts import source_tree_from_document_facts
from .refs import _part_name


def inspect_source_template_docx(source_template_docx: Path) -> dict[str, Any]:
    return source_tree_from_document_facts(inspect_document_facts_docx(source_template_docx))


def inspect_document_facts_docx(source_template_docx: Path) -> dict[str, Any]:
    inspected = inspect_generated_template_docx(source_template_docx)
    run_index = _runs_from_inspection(inspected)
    body_flow = _body_flow_from_inspection(inspected, run_index)
    data = inspected.get("data", {})
    return {
        "artifact_type": "document_facts",
        "artifact_version": "1.1",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "metadata": {
            "source_template_docx": str(source_template_docx),
            "source_template_hash": sha256_file(source_template_docx),
            "input_exists": inspected.get("input_exists"),
            "input_valid_docx": inspected.get("input_valid_docx"),
        },
        "body_flow": body_flow,
        "runs": run_index["runs"],
        "unknown_objects": data.get("unknown_visible_objects", []),
        "indexes": {
            "by_source_ref": {
                item.get("source_ref"): item.get("node_id")
                for item in body_flow
                if item.get("source_ref")
            },
            "by_source_seq": {
                str(item.get("source_seq")): {
                    "node_id": item.get("node_id"),
                    "source_ref": item.get("source_ref"),
                    "text_preview": str(item.get("text") or "")[:80],
                    "structure_layer": item.get("structure_layer"),
                }
                for item in body_flow
                if item.get("source_seq") is not None
            },
            "body_order": [item.get("node_id") for item in body_flow],
            "runs_by_paragraph_id": run_index["runs_by_paragraph_id"],
            "runs_by_source_ref": run_index["runs_by_source_ref"],
            "runs_by_raw_run_id": run_index["runs_by_raw_run_id"],
        },
        "warnings": _source_tree_warnings(inspected),
        "data": data,
    }


def _body_flow_from_inspection(
    tree: dict[str, Any],
    run_index: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in iter_visible_text_entries(tree):
        order = entry.get("order") or 0
        node_id = f"body_{len(items) + 1:04d}"
        ids = _stable_ids_for_entry(entry)
        raw_run_ids = _raw_run_ids_for_entry(entry, run_index)
        items.append(
            {
                "node_id": node_id,
                "structure_layer": "header_footer"
                if entry.get("kind") in {"header", "footer"}
                else "body_flow",
                "flow_item_type": entry.get("kind"),
                "kind": entry.get("kind"),
                "source_ref": entry.get("source_ref"),
                "part_name": _part_name(entry.get("source_ref")),
                "order": order,
                **ids,
                "python_docx_index": entry.get("python_docx_index"),
                "parent_ref": None,
                "container_ref": entry.get("table_source_ref"),
                "visible": bool(entry.get("text")),
                "text": entry.get("text", ""),
                "style": entry.get("style", ""),
                "style_details": entry.get("style_details", {}),
                "text_facts": _text_facts_for_entry(entry),
                "raw_run_ids": raw_run_ids,
                "logical_run_ids": _logical_run_ids_for_raw_ids(
                    raw_run_ids,
                    run_index,
                ),
                **_container_trace_fields(entry, raw_run_ids),
            }
        )
    sorted_items = sorted(
        items,
        key=lambda item: (float(item.get("order") or 0), item["node_id"]),
    )
    for index, item in enumerate(sorted_items, start=1):
        item["source_seq"] = index
        item["source_seq_label"] = f"源模板元素 {index:03d}"
    return sorted_items


def _runs_from_inspection(tree: dict[str, Any]) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    runs_by_paragraph_id: dict[str, list[str]] = {}
    runs_by_source_ref: dict[str, list[str]] = {}
    runs_by_raw_run_id: dict[str, dict[str, Any]] = {}
    logical_by_raw: dict[str, str] = {}
    for paragraph in _run_paragraphs_from_inspection(tree):
        paragraph_index = paragraph.get("xml_index") or paragraph.get("index")
        if paragraph_index is None:
            continue
        source_ref = str(paragraph.get("source_ref") or f"word/document.xml:p[{paragraph_index}]")
        part_name = str(paragraph.get("part_name") or _part_name(source_ref))
        paragraph_id = _paragraph_id_for_run_paragraph(part_name, int(paragraph_index))
        style_details = paragraph.get("style_details") or {}
        paragraph_runs = paragraph.get("runs") or []
        current_group: dict[str, Any] | None = None
        logical_run_index = 0

        def flush_current_group() -> None:
            nonlocal current_group
            if current_group is None:
                return
            run_facts = _logical_run_facts(
                current_group,
                paragraph=paragraph,
                paragraph_id=paragraph_id,
                style_details=style_details,
            )
            runs.append(run_facts)
            for raw_run_id, raw_source_ref in zip(
                run_facts["merged_from"],
                run_facts["source_refs"],
                strict=True,
            ):
                runs_by_raw_run_id[raw_run_id] = {
                    **run_facts,
                    "raw_run_id": raw_run_id,
                    "source_ref": raw_source_ref,
                }
            current_group = None

        for raw_index, run in enumerate(paragraph_runs, start=1):
            raw_run_id = f"{paragraph_id}.r_{raw_index:03d}"
            effective_style = _effective_style(run)
            raw_source_ref = str(run.get("source_ref") or f"{source_ref}/r[{raw_index}]")
            if (
                current_group is None
                or current_group["effective_style"] != effective_style
            ):
                flush_current_group()
                logical_run_index += 1
                current_group = {
                    "logical_run_id": f"{paragraph_id}.lr_{logical_run_index:03d}",
                    "paragraph_id": paragraph_id,
                    "source_ref": raw_source_ref,
                    "source_refs": [],
                    "container_refs": [],
                    "merged_from": [],
                    "texts": [],
                    "effective_style": effective_style,
                }
            current_group["merged_from"].append(raw_run_id)
            current_group["source_refs"].append(raw_source_ref)
            for container_ref in run.get("container_refs", []):
                if container_ref not in current_group["container_refs"]:
                    current_group["container_refs"].append(container_ref)
            current_group["texts"].append(str(run.get("text") or ""))
            logical_run_id = str(current_group["logical_run_id"])
            logical_by_raw[raw_run_id] = logical_run_id
            runs_by_paragraph_id.setdefault(paragraph_id, []).append(raw_run_id)
            runs_by_source_ref.setdefault(source_ref, []).append(raw_run_id)
        flush_current_group()
    return {
        "runs": runs,
        "runs_by_paragraph_id": runs_by_paragraph_id,
        "runs_by_source_ref": runs_by_source_ref,
        "runs_by_raw_run_id": runs_by_raw_run_id,
        "logical_by_raw": logical_by_raw,
    }


def _paragraph_id_for_run_paragraph(part_name: str, paragraph_index: int) -> str:
    if part_name in {"", "word/document.xml"}:
        return f"p_{paragraph_index:04d}"
    return f"{_safe_part_id(part_name)}.p_{paragraph_index:04d}"


def _safe_part_id(part_name: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", part_name).strip("_").lower()


def _run_paragraphs_from_inspection(tree: dict[str, Any]) -> list[dict[str, Any]]:
    paragraphs: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append(paragraph: dict[str, Any]) -> None:
        source_ref = str(paragraph.get("source_ref") or "")
        if source_ref and source_ref in seen:
            return
        if source_ref:
            seen.add(source_ref)
        paragraphs.append(paragraph)

    for paragraph in tree.get("data", {}).get("paragraphs", []):
        append(paragraph)
    for table in tree.get("data", {}).get("tables", []):
        for cell in table.get("cells", []):
            for paragraph in cell.get("paragraphs", []):
                append(paragraph)
    for part in tree.get("data", {}).get("headers_footers", []):
        for paragraph in part.get("paragraphs", []):
            append(paragraph)
    return paragraphs


def _logical_run_facts(
    group: dict[str, Any],
    *,
    paragraph: dict[str, Any],
    paragraph_id: str,
    style_details: dict[str, Any],
) -> dict[str, Any]:
    merged_from = list(group["merged_from"])
    return {
        "raw_run_id": merged_from[0],
        "logical_run_id": group["logical_run_id"],
        "merged_from": merged_from,
        "paragraph_id": paragraph_id,
        "source_ref": group["source_ref"],
        "source_refs": list(group["source_refs"]),
        "container_refs": list(group.get("container_refs", [])),
        "text": "".join(group["texts"]),
        "kind": "text",
        "effective_style": group["effective_style"],
        "style_provenance": {
            "paragraph_style": paragraph.get("style"),
            "style_inheritance": style_details.get("style_inheritance", {}),
            "layers": [
                "docDefaults",
                "basedOn",
                "paragraph_style",
                "paragraph_direct",
                "run_direct",
            ],
        },
    }


def _effective_style(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "font_names": run.get("font_names", []),
        "font_size_pt": run.get("font_size_pt"),
        "bold": run.get("bold"),
        "italic": run.get("italic"),
        "underline": run.get("underline"),
        "color": run.get("color"),
    }


def _logical_run_ids_for_raw_ids(
    raw_run_ids: list[str],
    run_index: dict[str, Any],
) -> list[str]:
    logical_run_ids: list[str] = []
    seen: set[str] = set()
    for raw_run_id in raw_run_ids:
        logical_run_id = run_index["logical_by_raw"].get(raw_run_id)
        if not logical_run_id or logical_run_id in seen:
            continue
        logical_run_ids.append(logical_run_id)
        seen.add(logical_run_id)
    return logical_run_ids


def _stable_ids_for_entry(entry: dict[str, Any]) -> dict[str, Any]:
    source_ref = str(entry.get("source_ref") or "")
    ids: dict[str, Any] = {}
    paragraph_index = entry.get("paragraph_index")
    if paragraph_index is None:
        match = _match_index(source_ref, r"p\[(\d+)\]")
        paragraph_index = int(match) if match is not None else None
    if paragraph_index is not None:
        ids["paragraph_id"] = f"p_{int(paragraph_index):04d}"
    table_index = entry.get("table_index")
    if table_index is None:
        match = _match_index(source_ref, r"tbl\[(\d+)\]")
        table_index = int(match) if match is not None else None
    if table_index is not None:
        ids["table_id"] = f"tbl_{int(table_index):04d}"
    row_index = _match_index(source_ref, r"tr\[(\d+)\]")
    cell_index = _match_index(source_ref, r"tc\[(\d+)\]")
    if table_index is not None and row_index is not None and cell_index is not None:
        ids["cell_id"] = (
            f"tbl_{int(table_index):04d}.r_{int(row_index):03d}.c_{int(cell_index):03d}"
        )
    return ids


def _raw_run_ids_for_entry(entry: dict[str, Any], run_index: dict[str, Any]) -> list[str]:
    if entry.get("kind") == "paragraph":
        paragraph_index = entry.get("paragraph_index")
        if paragraph_index is None:
            paragraph_index = _match_index(str(entry.get("source_ref") or ""), r"p\[(\d+)\]")
        if paragraph_index is None:
            return []
        paragraph_id = f"p_{int(paragraph_index):04d}"
        return list(run_index["runs_by_paragraph_id"].get(paragraph_id, []))
    if entry.get("kind") in {"header", "footer"}:
        refs: list[str] = []
        for source_ref in entry.get("part_paragraph_refs", []):
            refs.extend(run_index["runs_by_source_ref"].get(str(source_ref), []))
        return list(dict.fromkeys(refs))
    paragraph_indices = []
    for paragraph_index in entry.get("paragraph_indices") or []:
        paragraph_indices.append(int(paragraph_index))
    if entry.get("paragraph_index") is not None:
        paragraph_indices.append(int(entry["paragraph_index"]))
    if entry.get("end_paragraph_index") is not None:
        start = paragraph_indices[0] if paragraph_indices else int(entry["end_paragraph_index"])
        end = int(entry["end_paragraph_index"])
        paragraph_indices = list(range(start, end + 1))
    refs: list[str] = []
    for paragraph_index in paragraph_indices:
        paragraph_id = f"p_{paragraph_index:04d}"
        refs.extend(run_index["runs_by_paragraph_id"].get(paragraph_id, []))
    return list(dict.fromkeys(refs))


def _container_trace_fields(
    entry: dict[str, Any],
    raw_run_ids: list[str],
) -> dict[str, Any]:
    if entry.get("kind") != "table_cell":
        if entry.get("kind") in {"header", "footer"}:
            return {
                "part_paragraph_refs": list(entry.get("part_paragraph_refs", [])),
                "part_run_refs": list(raw_run_ids),
            }
        return {}
    return {
        "cell_paragraph_refs": list(entry.get("cell_paragraph_refs", [])),
        "cell_run_refs": list(raw_run_ids),
    }


def _text_facts_for_entry(entry: dict[str, Any]) -> dict[str, Any]:
    text = str(entry.get("text") or "")
    style_details = entry.get("style_details") or {}
    paragraph_style = style_details.get("paragraph") or {}
    dominant = style_details.get("dominant_run") or {}
    return {
        "raw_text": text,
        "normalized_text": re.sub(r"\s+", " ", text.strip()),
        "char_count": len(text),
        "has_tab": "\t" in text,
        "has_line_break": "\n" in text,
        "parenthesized_segments": _parenthesized_segments(text),
        "trailing_token": _trailing_token(text),
        "leader_char_run": _leader_char_run(text),
        "style_id": paragraph_style.get("style_id"),
        "style_name": (
            entry.get("style")
            or paragraph_style.get("style_name")
            or paragraph_style.get("style_id")
            or ""
        ),
        "alignment": paragraph_style.get("alignment"),
        "dominant_font_size_pt": dominant.get("font_size_pt"),
        "dominant_bold": dominant.get("bold"),
    }


def _parenthesized_segments(text: str) -> list[str]:
    return [
        match.group(1) or match.group(2) or ""
        for match in re.finditer(r"（([^）]*)）|\(([^)]*)\)", text)
    ]


def _trailing_token(text: str) -> str | None:
    match = re.search(r"(\S+)\s*$", text)
    return match.group(1) if match else None


def _leader_char_run(text: str) -> str | None:
    match = re.search(r"([…\.．·•]{2,})\s*\S+\s*$", text)
    return match.group(1) if match else None


def _match_index(text: str, pattern: str) -> str | None:
    import re

    match = re.search(pattern, text)
    return match.group(1) if match else None


def _source_tree_warnings(inspected: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for item in inspected.get("data", {}).get("unknown_visible_objects", []):
        warnings.append(
            {
                "code": "unknown_visible_object",
                "message": item.get("reason", "unknown visible object"),
                "source_ref": item.get("source_ref"),
                "severity": "review",
            }
        )
    return warnings
