from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file
from docfit.template_gap.inspector import (
    inspect_generated_template_docx,
    iter_visible_text_entries,
)

from .artifacts import source_tree_from_document_facts
from .refs import _part_name
from .structure_candidates import _structural_signals


def inspect_source_template_docx(source_template_docx: Path) -> dict[str, Any]:
    return source_tree_from_document_facts(inspect_document_facts_docx(source_template_docx))


def inspect_document_facts_docx(source_template_docx: Path) -> dict[str, Any]:
    inspected = inspect_generated_template_docx(source_template_docx)
    run_index = _runs_from_inspection(inspected)
    body_flow = _body_flow_from_inspection(inspected, run_index)
    data = inspected.get("data", {})
    return {
        "artifact_type": "document_facts",
        "artifact_version": "1.0",
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
            "runs_by_raw_run_id": {
                run["raw_run_id"]: run for run in run_index["runs"]
            },
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
                "parent_ref": None,
                "container_ref": entry.get("table_source_ref"),
                "visible": bool(entry.get("text")),
                "text": entry.get("text", ""),
                "style": entry.get("style", ""),
                "style_details": entry.get("style_details", {}),
                "raw_run_ids": raw_run_ids,
                "logical_run_ids": [
                    run_index["logical_by_raw"][raw_run_id]
                    for raw_run_id in raw_run_ids
                    if raw_run_id in run_index["logical_by_raw"]
                ],
                "structural_signals": _structural_signals(entry),
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
    logical_by_raw: dict[str, str] = {}
    for paragraph in tree.get("data", {}).get("paragraphs", []):
        paragraph_index = paragraph.get("xml_index") or paragraph.get("index")
        if paragraph_index is None:
            continue
        paragraph_id = f"p_{int(paragraph_index):04d}"
        source_ref = str(paragraph.get("source_ref") or f"word/document.xml:p[{paragraph_index}]")
        style_details = paragraph.get("style_details") or {}
        paragraph_runs = paragraph.get("runs") or []
        for run_index, run in enumerate(paragraph_runs, start=1):
            raw_run_id = f"{paragraph_id}.r_{run_index:03d}"
            logical_run_id = f"{paragraph_id}.lr_{run_index:03d}"
            logical_by_raw[raw_run_id] = logical_run_id
            run_facts = {
                "raw_run_id": raw_run_id,
                "logical_run_id": logical_run_id,
                "merged_from": [raw_run_id],
                "paragraph_id": paragraph_id,
                "source_ref": f"{source_ref}/r[{run_index}]",
                "text": run.get("text", ""),
                "kind": "text",
                "effective_style": _effective_style(run),
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
            runs.append(run_facts)
            runs_by_paragraph_id.setdefault(paragraph_id, []).append(raw_run_id)
            runs_by_source_ref.setdefault(source_ref, []).append(raw_run_id)
    return {
        "runs": runs,
        "runs_by_paragraph_id": runs_by_paragraph_id,
        "runs_by_source_ref": runs_by_source_ref,
        "logical_by_raw": logical_by_raw,
    }


def _effective_style(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "font_names": run.get("font_names", []),
        "font_size_pt": run.get("font_size_pt"),
        "bold": run.get("bold"),
        "italic": run.get("italic"),
    }


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
    source_ref = str(entry.get("source_ref") or "")
    if entry.get("kind") == "paragraph":
        return list(run_index["runs_by_source_ref"].get(source_ref, []))
    paragraph_indices = []
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
    return refs


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
