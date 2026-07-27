from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso, sha256_json

from .constants import BODY_SLOT_MARKER
from .final_results import AVAILABLE, FinalStageResult, require_final_stage_result
from .page_policy import normalize_unit_page_policy
from .refs import _first_source_ref, _paragraph_index, _source_seq_refs
from .synthesis_policy import should_synthesize_visible_text
from .text_utils import _normalize_text


def build_template_generation_plan(
    request: dict[str, Any],
    *,
    template_final: FinalStageResult,
) -> dict[str, Any]:
    template_result = require_final_stage_result(
        template_final,
        stage_id="T5",
        artifact_type="template_spec",
        artifact_name="05_template_spec.yaml",
    )
    template_spec = template_result.payload
    t2_available = _upstream_final_available(
        template_spec,
        "t2_final",
        fallback=template_result.availability == AVAILABLE,
    )
    t3_available = _upstream_final_available(
        template_spec,
        "t3_final",
        fallback=template_result.availability == AVAILABLE,
    )
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
    pagination = (
        _build_pagination_actions(
            list(template_spec.get("units") or []),
            next_id=next_id,
        )
        if t2_available
        else _unavailable_pagination(
            list(template_spec.get("units") or []),
            next_id=next_id,
        )
    )
    actions.extend(pagination["actions"])
    next_id = int(pagination["next_id"])
    if t3_available:
        synthetic_actions = _synthetic_unit_title_actions(
            list(template_spec.get("units") or [])
        )
        unit_strategies = _unit_strategies_from_template_spec(template_spec)
    else:
        synthetic_actions = []
        unit_strategies = []
    for action in synthetic_actions:
        action["action_id"] = f"a_{next_id:03d}"
        actions.append(action)
        next_id += 1
    for unit in unit_strategies:
        decisions = list(unit.get("decisions", []) or [])
        span_slot_elements = {
            (decision.get("unit_id"), decision.get("element_id"))
            for decision in decisions
            if decision.get("decision_type") == "replace_span_with_slot"
            and len(decision.get("source_seq_refs", []) or []) == 1
        }
        for decision in decisions:
            if (
                decision.get("decision_type") == "create_fillable_slot"
                and (decision.get("unit_id"), decision.get("element_id"))
                in span_slot_elements
            ):
                continue
            action_type = _action_type_for_decision(decision["decision_type"])
            actions.append(
                {
                    "action_id": f"a_{next_id:03d}",
                    "action_type": action_type,
                    "unit_id": decision.get("unit_id"),
                    "element_id": decision.get("element_id"),
                    "source_ref": decision.get("source_ref"),
                    "affected_source_seq_refs": decision.get("source_seq_refs", []),
                    "affected_raw_run_ids": decision.get("raw_run_ids", []),
                    "affected_logical_run_ids": decision.get("logical_run_ids", []),
                    "affected_char_ranges": decision.get("char_ranges", []),
                    "span_id": decision.get("span_id"),
                    "span_type": decision.get("span_type"),
                    "target_ref": _target_ref_for_decision(decision),
                    "status": "planned",
                    "reason": decision.get("reason"),
                    "upstream_stage": "T5",
                    "upstream_artifact": "05_template_spec.yaml",
                    "upstream_artifact_hash": template_result.sha256,
                    "decision_trace_refs": list(
                        decision.get("decision_trace_refs") or []
                    ),
                    "preconditions": {
                        "t5_availability": template_result.availability,
                        "t3_availability": AVAILABLE,
                        "identity_bound": bool(
                            decision.get("source_ref")
                            or decision.get("raw_run_ids")
                            or decision.get("char_ranges")
                        ),
                    },
                }
            )
            next_id += 1
    if not any(
        action.get("action_type") == "ensure_body_slot" for action in actions
    ):
        actions.append(
            {
                "action_id": f"a_{next_id:03d}",
                "action_type": "ensure_body_slot",
                "owner_scope": "document_body",
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
            "template_spec": template_result.sha256,
        },
        "input_refs": {"t5_final": template_result.input_ref()},
        "upstream_availability": {
            "status": template_result.availability,
            "reason": template_result.reason,
        },
        "page_policy_results": pagination["page_policy_results"],
        "actions": actions,
    }


def _build_pagination_actions(
    units: list[dict[str, Any]],
    *,
    next_id: int,
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    page_policy_results: list[dict[str, Any]] = []
    page_boundary_refs: set[str] = set()
    for index, unit in enumerate(units):
        page_policy = normalize_unit_page_policy(
            unit.get("page_policy"),
            document_start=index == 0,
        )
        unit_id = str(unit.get("unit_id") or "")
        result = {
            "unit_id": unit_id,
            "page_policy": page_policy,
            "status": "no_action_required",
            "planned_action_ids": [],
            "reason": "page policy has no executable requirement",
        }
        planned_ids: list[str] = []
        page_start = page_policy.get("start")
        source_ref = _first_source_ref(unit)
        if page_start == "new_page":
            observed_boundary = unit.get("boundary")
            observed_start_page = (
                observed_boundary.get("start_page")
                if isinstance(observed_boundary, dict)
                else None
            )
            if (
                isinstance(observed_start_page, int)
                and not isinstance(observed_start_page, bool)
                and observed_start_page > 1
            ):
                result.update(
                    {
                        "status": "already_satisfied",
                        "reason": (
                            "T2 real render already observes this unit at a new "
                            f"page boundary: page {observed_start_page}"
                        ),
                        "observed_boundary": dict(observed_boundary),
                    }
                )
            elif not source_ref:
                result.update(
                    {
                        "status": "manual_review",
                        "reason": "page_policy.start=new_page but unit has no source_ref",
                    }
                )
            elif index == 0:
                result["reason"] = "first unit already starts at document start"
            else:
                action_id = f"a_{next_id:03d}"
                action_type = "insert_page_break_before_unit"
                boundary_refs = page_boundary_refs
                if source_ref not in boundary_refs:
                    actions.append(
                        _page_boundary_action(
                            action_id,
                            action_type=action_type,
                            target_unit=unit,
                            policy_unit=unit,
                            page_policy=page_policy,
                            reason="unit page_policy.start requires a boundary before this unit",
                        )
                    )
                    boundary_refs.add(source_ref)
                    planned_ids.append(action_id)
                    next_id += 1
        if planned_ids:
            result.update(
                {
                    "status": "action_planned",
                    "planned_action_ids": planned_ids,
                    "reason": "page policy mapped to planned T6 actions",
                }
            )
        page_policy_results.append(result)
    actions = _dedupe_boundary_actions(actions, page_policy_results)
    return {
        "actions": actions,
        "page_policy_results": page_policy_results,
        "next_id": next_id,
    }


def _unavailable_pagination(
    units: list[dict[str, Any]],
    *,
    next_id: int,
) -> dict[str, Any]:
    return {
        "actions": [],
        "page_policy_results": [
            {
                "unit_id": str(unit.get("unit_id") or ""),
                "page_policy": normalize_unit_page_policy(
                    unit.get("page_policy"),
                    document_start=index == 0,
                ),
                "status": "manual_review",
                "planned_action_ids": [],
                "reason": "T2 final is NOT_AVAILABLE; pagination is not executable",
            }
            for index, unit in enumerate(units)
            if isinstance(unit, dict)
        ],
        "next_id": next_id,
    }


def _upstream_final_available(
    template_spec: dict[str, Any],
    ref_name: str,
    *,
    fallback: bool,
) -> bool:
    ref = (template_spec.get("input_refs") or {}).get(ref_name)
    if not isinstance(ref, dict):
        return fallback
    return str(ref.get("availability") or "") == AVAILABLE


def _dedupe_boundary_actions(
    actions: list[dict[str, Any]],
    page_policy_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collapse duplicate page/section boundaries at the same source ref.

    A next-page section break satisfies the same page boundary as a page break.
    When both are planned for the same unit start, keep the section break and
    point every affected page-policy result at that single executable action.
    """
    section_by_ref = {
        str(action.get("source_ref")): action
        for action in actions
        if action.get("action_type") == "insert_section_break_before_unit"
        and action.get("source_ref")
    }
    remap_action_ids: dict[str, str] = {}
    removed_action_ids: set[str] = set()
    for action in actions:
        if action.get("action_type") != "insert_page_break_before_unit":
            continue
        source_ref = str(action.get("source_ref") or "")
        section_action = section_by_ref.get(source_ref)
        if not section_action:
            continue
        old_id = str(action.get("action_id") or "")
        new_id = str(section_action.get("action_id") or "")
        if not old_id or not new_id:
            continue
        remap_action_ids[old_id] = new_id
        removed_action_ids.add(old_id)
        _merge_boundary_policy_trace(section_action, action)

    if not removed_action_ids:
        return actions

    for result in page_policy_results:
        planned_ids = [
            remap_action_ids.get(str(action_id), str(action_id))
            for action_id in result.get("planned_action_ids", []) or []
            if action_id
        ]
        result["planned_action_ids"] = _dedupe_str(planned_ids)
    return [
        action
        for action in actions
        if str(action.get("action_id") or "") not in removed_action_ids
    ]


def _merge_boundary_policy_trace(
    kept_action: dict[str, Any],
    removed_action: dict[str, Any],
) -> None:
    kept_action["satisfies_page_policy_unit_ids"] = _dedupe_str(
        [
            *list(kept_action.get("satisfies_page_policy_unit_ids", []) or []),
            str(kept_action.get("page_policy_unit_id") or ""),
            str(removed_action.get("page_policy_unit_id") or ""),
        ]
    )
    kept_action["supersedes_action_ids"] = _dedupe_str(
        [
            *list(kept_action.get("supersedes_action_ids", []) or []),
            str(removed_action.get("action_id") or ""),
        ]
    )
    kept_action["page_policy_evidence_refs"] = _dedupe_str(
        [
            *list(kept_action.get("page_policy_evidence_refs", []) or []),
            *list(removed_action.get("page_policy_evidence_refs", []) or []),
        ]
    )
    kept_action["page_policy_proposal_ids"] = _dedupe_str(
        [
            *list(kept_action.get("page_policy_proposal_ids", []) or []),
            *list(removed_action.get("page_policy_proposal_ids", []) or []),
        ]
    )
    kept_action["reason"] = (
        f"{kept_action.get('reason')}; section break also satisfies "
        f"deduped page boundary action {removed_action.get('action_id')}"
    )


def _dedupe_str(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result


def _page_boundary_action(
    action_id: str,
    *,
    action_type: str,
    target_unit: dict[str, Any],
    policy_unit: dict[str, Any],
    page_policy: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    source_ref = _first_source_ref(target_unit)
    return {
        "action_id": action_id,
        "action_type": action_type,
        "unit_id": target_unit.get("unit_id"),
        "page_policy_unit_id": policy_unit.get("unit_id"),
        "element_id": None,
        "source_ref": source_ref,
        "affected_source_seq_refs": target_unit.get("source_seq_refs", []),
        "page_policy_owner_source_seq_refs": policy_unit.get("source_seq_refs", []),
        "target_ref": source_ref,
        "status": "planned",
        "reason": reason,
        "page_policy": dict(page_policy),
    }


def _unit_strategies_from_template_spec(
    template_spec: dict[str, Any],
) -> list[dict[str, Any]]:
    strategies: list[dict[str, Any]] = []
    for unit in template_spec.get("units", []) or []:
        if not isinstance(unit, dict):
            continue
        unit_id = str(unit.get("unit_id") or "")
        decisions: list[dict[str, Any]] = []
        for element in unit.get("elements", []) or []:
            if not isinstance(element, dict):
                continue
            decisions.extend(_element_span_decisions(unit_id, element))
            policy = str(element.get("policy") or "")
            if policy in {"instruction_remove", "remove_instruction"}:
                decision_type = "remove_instruction_text"
            elif policy == "fill":
                decision_type = "create_fillable_slot"
            elif policy == "generated":
                decision_type = "create_generated_field_placeholder"
            elif policy == "fixed" and (
                _first_source_ref(element) is None
                and should_synthesize_visible_text(element)
            ):
                decision_type = "insert_fixed_text"
            else:
                continue
            source_ref = _first_source_ref(element) or _first_source_ref(unit)
            decisions.append(
                {
                    "decision_id": (
                        f"{unit_id}.{_element_id(element)}.{decision_type}"
                    ),
                    "decision_type": decision_type,
                    "unit_id": unit_id,
                    "element_id": _element_id(element),
                    "element_name": element.get("name"),
                    "content": element.get("content") or element.get("name") or "",
                    "source_ref": source_ref,
                    "source_seq_refs": _source_seq_refs(element),
                    "raw_run_ids": list(element.get("raw_run_ids") or []),
                    "logical_run_ids": list(element.get("logical_run_ids") or []),
                    "decision_trace_refs": _element_trace_refs(element),
                    "reason": _decision_reason(decision_type),
                }
            )
        strategies.append(
            {
                "unit_id": unit_id,
                "decisions": decisions,
            }
        )
    return strategies


def _element_span_decisions(
    unit_id: str,
    element: dict[str, Any],
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    element_id = _element_id(element)
    for span in element.get("spans", []) or []:
        if not isinstance(span, dict):
            continue
        span_type = str(span.get("span_type") or "")
        if span_type not in {"layout_spacer", "inline_instruction", "sample_value"}:
            continue
        decision_type = (
            "replace_span_with_slot"
            if span_type == "sample_value"
            else "remove_instruction_text"
        )
        decisions.append(
            {
                "decision_id": (
                    f"{unit_id}.{element_id}.{span.get('span_id')}.{decision_type}"
                ),
                "decision_type": decision_type,
                "unit_id": unit_id,
                "element_id": element_id,
                "span_id": span.get("span_id"),
                "span_type": span_type,
                "element_name": element.get("name"),
                "content": span.get("text") or "",
                "source_ref": _first_source_ref(element),
                "source_seq_refs": _source_seq_refs(element),
                "raw_run_ids": list(span.get("raw_run_ids") or []),
                "logical_run_ids": list(span.get("logical_run_ids") or [])
                or list(element.get("logical_run_ids") or []),
                "char_ranges": list(span.get("char_ranges") or []),
                "decision_trace_refs": _element_trace_refs(element),
                "reason": _decision_reason(decision_type),
            }
        )
    return decisions


def _element_id(element: dict[str, Any]) -> str:
    return str(element.get("element_id") or element.get("stable_id") or "")


def _element_trace_refs(element: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for trace in element.get("agent_traces", []) or []:
        if not isinstance(trace, dict):
            continue
        for key in ("decision_ref", "decision_target_ref", "member_ref"):
            value = trace.get(key)
            if value not in (None, ""):
                refs.append(str(value))
    return list(dict.fromkeys(refs))


def _synthetic_unit_title_actions(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for index, unit in enumerate(units):
        if not _is_table_of_contents_unit(unit):
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


def _is_table_of_contents_unit(unit: dict[str, Any]) -> bool:
    unit_name = _normalize_text(str(unit.get("unit_name") or unit.get("name") or ""))
    return unit_name in {"目录", "tableofcontents"}


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
        "remove_instruction_text": "instruction/example text should not enter the fillable template",
        "replace_span_with_slot": "sample placeholder text should be replaced by a fillable slot",
        "create_fillable_slot": "fillable source element needs a stable content control tag for later placement",
        "create_generated_field_placeholder": "generated element needs a stable content control tag for later field generation",
        "insert_fixed_text": "visible standard text is missing from the aligned source region and should be present in the generated template",
    }.get(decision_type, "template generation decision")


def _action_type_for_decision(decision_type: str) -> str:
    return {
        "remove_instruction_text": "remove_instruction_text",
        "replace_span_with_slot": "replace_span_with_slot",
        "create_fillable_slot": "create_fillable_slot",
        "create_generated_field_placeholder": "create_generated_field_placeholder",
        "insert_fixed_text": "insert_fixed_text",
    }[decision_type]


def _target_ref_for_decision(decision: dict[str, Any]) -> str:
    decision_type = decision.get("decision_type")
    if decision_type == "create_fillable_slot":
        return f"sdt:{decision.get('unit_id')}.{decision.get('element_id')}"
    if decision_type == "replace_span_with_slot":
        return f"sdt:{decision.get('unit_id')}.{decision.get('element_id')}.{decision.get('span_id')}"
    if decision_type == "create_generated_field_placeholder":
        return f"sdt:generated.{decision.get('unit_id')}.{decision.get('element_id')}"
    if decision_type == "insert_fixed_text":
        return str(decision.get("content") or "")
    return str(decision.get("source_ref") or "")
