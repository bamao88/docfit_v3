from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file
from docfit.harness.generated_template_inspector import (
    inspect_generated_template_docx,
    iter_visible_text_entries,
)

from .refs import _part_name
from .structure_candidates import _structural_signals


def inspect_source_template_docx(source_template_docx: Path) -> dict[str, Any]:
    inspected = inspect_generated_template_docx(source_template_docx)
    body_flow = _body_flow_from_inspection(inspected)
    return {
        "artifact_type": "source_template_tree",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.2.0"},
        "created_at": now_iso(),
        "metadata": {
            "source_template_docx": str(source_template_docx),
            "source_template_hash": sha256_file(source_template_docx),
            "input_exists": inspected.get("input_exists"),
            "input_valid_docx": inspected.get("input_valid_docx"),
        },
        "layers": {
            "package_global": {
                "numbering_definitions": inspected.get("data", {}).get(
                    "numbering_definitions", []
                ),
            },
            "section_rules": inspected.get("data", {}).get("sections", []),
            "header_footer": inspected.get("data", {}).get("headers_footers", []),
            "body_flow": body_flow,
            "embedded_resources": [],
            "unknown_objects": inspected.get("data", {}).get(
                "unknown_visible_objects", []
            ),
        },
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
        },
        "warnings": _source_tree_warnings(inspected),
        "data": inspected.get("data", {}),
    }


def _body_flow_from_inspection(tree: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in iter_visible_text_entries(tree):
        order = entry.get("order") or 0
        node_id = f"body_{len(items) + 1:04d}"
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
                "parent_ref": None,
                "container_ref": entry.get("table_source_ref"),
                "visible": bool(entry.get("text")),
                "text": entry.get("text", ""),
                "style": entry.get("style", ""),
                "style_details": entry.get("style_details", {}),
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
