from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso, sha256_json

from .constants import BODY_SLOT_MARKER
from .refs import _first_source_ref, _paragraph_index
from .text_utils import _normalize_text


def build_template_generation_plan(
    request: dict[str, Any],
    *,
    generation_model: dict[str, Any],
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = [
        {
            "action_id": "a_001",
            "action_type": "copy_source_docx",
            "unit_id": None,
            "element_id": None,
            "source_ref": request.get("source_template_docx"),
            "affected_source_seq_refs": [],
            "target_ref": "generated_template.docx",
            "status": "planned",
            "reason": "create the generated Word from the source template package",
        }
    ]
    next_id = 2
    page_boundary_refs: set[str] = set()
    section_boundary_refs: set[str] = set()
    for index, unit in enumerate(generation_model.get("data", {}).get("units", [])):
        if index == 0:
            continue
        page = unit.get("page") or {}
        page_break_rule = str(page.get("page_break") or "")
        page_policy = _generation_page_policy(page)
        policy_requires_new_page = page_policy.get("requires_new_page") is True
        enforcement_hint = str(page_policy.get("enforcement_hint") or "")
        source_ref = _first_source_ref(unit)
        if not source_ref:
            continue
        if (
            _page_break_rule_requires_break(page_break_rule)
            or (
                policy_requires_new_page
                and enforcement_hint not in {"section_break", "section"}
            )
        ) and source_ref not in page_boundary_refs:
            actions.append(
                {
                    "action_id": f"a_{next_id:03d}",
                    "action_type": "insert_page_break_before_unit",
                    "unit_id": unit.get("unit_id"),
                    "element_id": None,
                    "source_ref": source_ref,
                    "affected_source_seq_refs": unit.get("source_seq_refs", []),
                    "target_ref": source_ref,
                    "status": "planned",
                    "reason": "unit page rule requires a deterministic page break before this unit",
                }
            )
            page_boundary_refs.add(source_ref)
            next_id += 1
        section_isolation_rule = str(page.get("section_isolation") or "")
        if (
            _page_break_rule_requires_break(section_isolation_rule)
            or (
                policy_requires_new_page
                and enforcement_hint in {"section_break", "section"}
            )
        ) and source_ref not in section_boundary_refs:
            actions.append(
                {
                    "action_id": f"a_{next_id:03d}",
                    "action_type": "insert_section_break_before_unit",
                    "unit_id": unit.get("unit_id"),
                    "element_id": None,
                    "source_ref": source_ref,
                    "affected_source_seq_refs": unit.get("source_seq_refs", []),
                    "target_ref": source_ref,
                    "status": "planned",
                    "reason": "unit page rule requires a deterministic section boundary before this unit",
                }
            )
            section_boundary_refs.add(source_ref)
            next_id += 1
    for action in _synthetic_unit_title_actions(generation_model):
        action["action_id"] = f"a_{next_id:03d}"
        actions.append(action)
        next_id += 1
    for unit in generation_model.get("unit_strategies", []):
        for decision in unit.get("decisions", []):
            action_type = _action_type_for_decision(decision["decision_type"])
            actions.append(
                {
                    "action_id": f"a_{next_id:03d}",
                    "action_type": action_type,
                    "unit_id": decision.get("unit_id"),
                    "element_id": decision.get("element_id"),
                    "source_ref": decision.get("source_ref"),
                    "affected_source_seq_refs": decision.get("source_seq_refs", []),
                    "target_ref": _target_ref_for_decision(decision),
                    "status": "planned",
                    "reason": decision.get("reason"),
                }
            )
            next_id += 1
    planned_instruction_refs = {
        action.get("source_ref")
        for action in actions
        if action.get("action_type") == "remove_instruction_text"
    }
    for instruction in generation_model.get("cleanup", []):
        source_ref = instruction.get("source_ref")
        if not source_ref or source_ref in planned_instruction_refs:
            continue
        actions.append(
            {
                "action_id": f"a_{next_id:03d}",
                "action_type": "remove_instruction_text",
                "unit_id": "template_instructions",
                "element_id": None,
                "source_ref": source_ref,
                "affected_source_seq_refs": instruction.get("source_seq_refs", []),
                "target_ref": source_ref,
                "status": "planned",
                "reason": instruction.get(
                    "reason",
                    "detected template instruction text should not appear in the generated fillable template",
                ),
            }
        )
        planned_instruction_refs.add(source_ref)
        next_id += 1
    if not any(action.get("action_type") == "ensure_body_slot" for action in actions):
        actions.append(
            {
                "action_id": f"a_{next_id:03d}",
                "action_type": "ensure_body_slot",
                "unit_id": "body_main",
                "element_id": "slot_body_start",
                "source_ref": None,
                "affected_source_seq_refs": [],
                "target_ref": BODY_SLOT_MARKER,
                "status": "planned",
                "reason": "guarantee a stable write position for later content placement",
            }
        )
    return {
        "artifact_type": "template_generation_plan",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.2.0"},
        "created_at": now_iso(),
        "strategy": request.get("strategy"),
        "source_template_docx": request.get("source_template_docx"),
        "input_hashes": {
            "source_template_docx": request.get("source_template_hash"),
            "template_generation_model": sha256_json(generation_model),
        },
        "actions": actions,
    }


def _synthetic_unit_title_actions(generation_model: dict[str, Any]) -> list[dict[str, Any]]:
    units = generation_model.get("data", {}).get("units", [])
    actions: list[dict[str, Any]] = []
    for index, unit in enumerate(units):
        if str(unit.get("unit_id") or "") != "toc":
            continue
        title = _generated_unit_title_text(unit)
        if not title:
            continue
        source_ref = _first_source_ref(unit)
        next_ref = _next_unit_source_ref(units, index)
        if not next_ref:
            continue
        source_order = _paragraph_index(source_ref)
        previous_order = _paragraph_index(_previous_unit_source_ref(units, index))
        next_order = _paragraph_index(next_ref)
        if next_order is None:
            continue
        source_is_in_expected_window = (
            source_order is not None
            and (previous_order is None or source_order > previous_order)
            and source_order < next_order
        )
        if source_is_in_expected_window:
            continue
        actions.append(
            {
                "action_id": "",
                "action_type": "insert_synthetic_unit_title_before",
                "unit_id": unit.get("unit_id"),
                "element_id": "e_001",
                "source_ref": next_ref,
                "affected_source_seq_refs": unit.get("source_seq_refs", []),
                "target_ref": title,
                "status": "planned",
                "reason": (
                    "toc has no visible title in the expected unit position; "
                    "insert a generated title before the next unit"
                ),
            }
        )
    return actions


def _generated_unit_title_text(unit: dict[str, Any]) -> str | None:
    for element in unit.get("elements", []):
        if str(element.get("element_id") or "") != "e_001":
            continue
        if str(element.get("policy") or "") != "generated":
            continue
        content = _normalize_text(str(element.get("content") or element.get("name") or ""))
        if content and len(content) <= 12:
            return content
    return None


def _previous_unit_source_ref(units: list[dict[str, Any]], index: int) -> str | None:
    for unit in reversed(units[:index]):
        ref = _first_source_ref(unit)
        if ref:
            return ref
    return None


def _next_unit_source_ref(units: list[dict[str, Any]], index: int) -> str | None:
    for unit in units[index + 1 :]:
        ref = _first_source_ref(unit)
        if ref:
            return ref
    return None


def _decision_reason(decision_type: str) -> str:
    return {
        "keep_whole_unit_copy": "unit is preserved by the initial source DOCX copy",
        "remove_instruction_text": "instruction/example text should not enter the fillable template",
        "create_fillable_slot": "fillable source element needs a stable content control tag for later placement",
        "create_generated_field_placeholder": "generated element needs a stable content control tag for later field generation",
        "create_manual_placeholder": "manual-only content is preserved but not automatically filled",
        "insert_fixed_text": "visible standard text is missing from the aligned source region and should be present in the generated template",
    }.get(decision_type, "template generation decision")


def _action_type_for_decision(decision_type: str) -> str:
    return {
        "keep_whole_unit_copy": "preserve_whole_unit_copy",
        "remove_instruction_text": "remove_instruction_text",
        "create_fillable_slot": "create_fillable_slot",
        "create_generated_field_placeholder": "create_generated_field_placeholder",
        "create_manual_placeholder": "create_manual_placeholder",
        "insert_fixed_text": "insert_fixed_text",
    }[decision_type]


def _target_ref_for_decision(decision: dict[str, Any]) -> str:
    decision_type = decision.get("decision_type")
    if decision_type == "create_fillable_slot":
        return f"sdt:{decision.get('unit_id')}.{decision.get('element_id')}"
    if decision_type == "create_generated_field_placeholder":
        return f"sdt:generated.{decision.get('unit_id')}.{decision.get('element_id')}"
    if decision_type == "insert_fixed_text":
        return str(decision.get("content") or "")
    return str(decision.get("source_ref") or "")


def _page_break_rule_requires_break(rule: str) -> bool:
    normalized = _normalize_text(rule)
    return normalized in {"是", "true", "yes"} or normalized.startswith("是；")


def _generation_page_policy(page: dict[str, Any]) -> dict[str, Any]:
    page_policy = page.get("page_policy") or {}
    generation_policy = page_policy.get("generation_policy") or {}
    return generation_policy if isinstance(generation_policy, dict) else {}
