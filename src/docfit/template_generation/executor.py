from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from docx import Document
from docx.text.paragraph import Paragraph

from .constants import BODY_SLOT_MARKER
from .refs import _cell_for_ref, _paragraph_for_ref
from .text_utils import _dedupe_by_key
from .word_ops import (
    _append_marker,
    _clear_cell,
    _find_marker_ref,
    _insert_marker,
    _insert_page_break_before,
    _insert_section_break_before,
    _insert_styled_paragraph_before,
    _remove_paragraph,
)


def execute_template_generation_plan(
    source_template_docx: Path,
    generated_template_docx: Path,
    plan: dict[str, Any],
    *,
    copy_source_snapshot_docx: Path | None = None,
) -> dict[str, Any]:
    generated_template_docx.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_template_docx, generated_template_docx)
    if copy_source_snapshot_docx is not None:
        copy_source_snapshot_docx.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(generated_template_docx, copy_source_snapshot_docx)
    doc = Document(generated_template_docx)
    paragraph_map = {
        index: paragraph for index, paragraph in enumerate(doc.paragraphs, start=1)
    }
    executed: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    slots: list[dict[str, Any]] = []
    generated_fields: list[dict[str, Any]] = []
    paragraphs_to_remove: list[Paragraph] = []

    for action in plan.get("actions", []):
        action_type = action.get("action_type")
        if action_type == "copy_source_docx":
            executed.append(_executed(action, output_ref=str(generated_template_docx)))
        elif action_type == "insert_page_break_before_unit":
            output_ref = _insert_page_break_before(
                doc,
                paragraph_map,
                action.get("source_ref"),
            )
            if output_ref is None:
                review.append(_needs_review(action, "source node not found"))
                continue
            executed.append(_executed(action, output_ref=output_ref))
        elif action_type == "insert_section_break_before_unit":
            output_ref = _insert_section_break_before(
                doc,
                paragraph_map,
                action.get("source_ref"),
            )
            if output_ref is None:
                review.append(_needs_review(action, "source node not found"))
                continue
            executed.append(_executed(action, output_ref=output_ref))
        elif action_type == "remove_instruction_text":
            target = _paragraph_for_ref(paragraph_map, action.get("source_ref"))
            target_cell = _cell_for_ref(doc, action.get("source_ref"))
            if target is None and target_cell is None:
                review.append(_needs_review(action, "source node not found"))
                continue
            if target is not None:
                paragraphs_to_remove.append(target)
            if target_cell is not None:
                _clear_cell(target_cell)
            executed.append(_executed(action, output_ref=action.get("source_ref")))
        elif action_type == "create_fillable_slot":
            marker = _slot_marker(action)
            output_ref = _insert_marker(doc, paragraph_map, action.get("source_ref"), marker)
            slot = _slot_from_action(action, marker=marker, output_ref=output_ref)
            slots.append(slot)
            executed.append(_executed(action, output_ref=output_ref))
        elif action_type == "create_generated_field_placeholder":
            marker = _generated_marker(action)
            output_ref = _insert_marker(doc, paragraph_map, action.get("source_ref"), marker)
            generated_fields.append(
                {
                    "field_id": marker.strip("[]"),
                    "unit_id": action.get("unit_id"),
                    "element_id": action.get("element_id"),
                    "marker": marker,
                    "output_ref": output_ref,
                    "source_seq_refs": action.get("affected_source_seq_refs", []),
                }
            )
            executed.append(_executed(action, output_ref=output_ref))
        elif action_type == "create_manual_placeholder":
            executed.append(_executed(action, output_ref=action.get("source_ref")))
        elif action_type == "insert_fixed_text":
            text = str(action.get("target_ref") or "")
            output_ref = _insert_marker(
                doc,
                paragraph_map,
                action.get("source_ref"),
                text,
            )
            executed.append(_executed(action, output_ref=output_ref))
        elif action_type == "insert_synthetic_unit_title_before":
            text = str(action.get("target_ref") or "")
            output_ref = _insert_styled_paragraph_before(
                paragraph_map,
                action.get("source_ref"),
                text,
                page_break_before=True,
            )
            if output_ref is None:
                review.append(_needs_review(action, "source node not found"))
                continue
            executed.append(_executed(action, output_ref=output_ref))
        elif action_type == "preserve_whole_unit_copy":
            executed.append(_executed(action, output_ref=action.get("source_ref")))
        elif action_type == "ensure_body_slot":
            marker = BODY_SLOT_MARKER
            existing_ref = _find_marker_ref(doc, marker)
            output_ref = existing_ref or _append_marker(doc, marker)
            slots.append(
                {
                    "slot_id": "slot_body_start",
                    "unit_id": "body_main",
                    "element_id": "slot_body_start",
                    "kind": "body_content",
                    "marker": marker,
                    "output_ref": output_ref,
                    "required": True,
                }
            )
            executed.append(_executed(action, output_ref=output_ref))
        else:
            review.append(_needs_review(action, f"unsupported action type: {action_type}"))

    for paragraph in dict.fromkeys(paragraphs_to_remove):
        _remove_paragraph(paragraph)
    doc.save(generated_template_docx)
    return {
        "actions_executed": executed,
        "actions_requiring_review": review,
        "slots": _dedupe_by_key(slots, "slot_id"),
        "generated_fields": generated_fields,
        "page_breaks": [
            {
                "unit_id": action.get("unit_id"),
                "source_ref": action.get("source_ref"),
                "output_ref": action.get("output_ref"),
            }
            for action in executed
            if action.get("action_type") == "insert_page_break_before_unit"
        ],
        "section_breaks": [
            {
                "unit_id": action.get("unit_id"),
                "source_ref": action.get("source_ref"),
                "output_ref": action.get("output_ref"),
            }
            for action in executed
            if action.get("action_type") == "insert_section_break_before_unit"
        ],
        "synthesized_texts": [
            {
                "unit_id": action.get("unit_id"),
                "element_id": action.get("element_id"),
                "text": action.get("target_ref"),
                "output_ref": action.get("output_ref"),
            }
            for action in executed
            if action.get("action_type")
            in {"insert_fixed_text", "insert_synthetic_unit_title_before"}
        ],
    }


def _slot_marker(action: dict[str, Any]) -> str:
    return f"[[DOCFIT_SLOT:{action.get('unit_id')}.{action.get('element_id')}]]"


def _generated_marker(action: dict[str, Any]) -> str:
    return f"[[DOCFIT_GENERATED:{action.get('unit_id')}.{action.get('element_id')}]]"


def _slot_from_action(
    action: dict[str, Any],
    *,
    marker: str,
    output_ref: str,
) -> dict[str, Any]:
    return {
        "slot_id": f"{action.get('unit_id')}.{action.get('element_id')}",
        "unit_id": action.get("unit_id"),
        "element_id": action.get("element_id"),
        "kind": "body_content",
        "marker": marker,
        "output_ref": output_ref,
        "source_seq_refs": action.get("affected_source_seq_refs", []),
        "required": True,
    }


def _executed(action: dict[str, Any], *, output_ref: str | None) -> dict[str, Any]:
    return {
        **action,
        "output_ref": output_ref,
        "status": "executed",
    }


def _needs_review(action: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **action,
        "status": "needs_review",
        "reason": reason,
    }
