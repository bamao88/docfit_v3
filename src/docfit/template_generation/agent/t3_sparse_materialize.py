"""Canonical observation materialization for sparse T3 decisions.

The sparse trace remains authoritative for hierarchy and coverage.  This module
derives the flat ``ai_element_observation.items`` view consumed by evaluation
and the sole AI-to-element-spec materializer.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from docfit.core.io import now_iso

from .observation_schema import (
    OBSERVATION_SCHEMA_VERSION,
    PROMPT_CONTRACT_VERSION,
    compute_coverage,
    open_questions_from,
)
from .packet import packet_source_seq_set


def materialize_sparse_t3_observation(
    trace: dict[str, Any],
    *,
    packet: dict[str, Any],
    model: str,
    stage_input: dict[str, Any],
) -> dict[str, Any]:
    """Derive executable atomic policy items and retain the sparse audit ledger."""

    items: list[dict[str, Any]] = []
    object_items: list[dict[str, Any]] = []
    demotions: list[dict[str, Any]] = []
    decisions_by_ref = {
        str(decision.get("decision_ref")): decision
        for decision in trace.get("decisions", []) or []
        if isinstance(decision, dict) and decision.get("decision_ref")
    }
    coverage_groups = _group_atomic_coverage(trace.get("atomic_coverage", []) or [])
    for order, rows in enumerate(coverage_groups):
        item = _atomic_policy_item(
            rows,
            decisions_by_ref=decisions_by_ref,
            order=order,
        )
        if item.get("source_seq_refs"):
            items.append(item)
        else:
            object_items.append(item)
        if not item.get("execution_eligible"):
            demotions.append(
                {
                    "item_id": item["element_id"],
                    "check_id": (
                        "C-T3-SPAN-MIXED"
                        if item.get("projection_status") == "mixed_span_actions"
                        else "C-T3-SPARSE-FALLBACK"
                    ),
                    "reason": (
                        "accepted span actions cannot be losslessly projected to one run action"
                        if item.get("projection_status") == "mixed_span_actions"
                        else item.get("ai_rationale")
                        or "sparse decision was not accepted"
                    ),
                    "member_ref": item.get("member_ref"),
                    "member_refs": deepcopy(item.get("member_refs") or []),
                    "decision_ref": item.get("decision_ref"),
                    "decision_refs": deepcopy(item.get("decision_refs") or []),
                    "decision_status": item.get("decision_status"),
                }
            )
    valid_seq = packet_source_seq_set(packet)
    coverage = compute_coverage(items, all_source_seq=valid_seq)
    open_questions = open_questions_from(demotions=demotions, coverage=coverage)
    open_questions.extend(
        {
            "question_id": f"q_sparse_{index:04d}",
            "blocking_level": "non_blocking",
            "check_id": item.get("check_id"),
            "affected_refs": [item.get("member_ref")],
            "reason": item.get("reason"),
        }
        for index, item in enumerate(demotions)
    )
    return {
        "artifact_type": "ai_element_observation",
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "sparse_decision_contract_version": trace.get("artifact_version"),
        "stage_input_ref": deepcopy(trace.get("stage_input_ref") or {}),
        "stage": "t3",
        "source_render_hash": packet.get("source_render_hash"),
        "model": model,
        "created_at": now_iso(),
        "coverage": coverage,
        "items": items,
        "object_items": object_items,
        "unknown_items": [],
        "open_questions": open_questions,
        "abstain": not items and not object_items,
        "self_consistency": None,
        "sparse_decisions": deepcopy(trace.get("decisions") or []),
        "atomic_coverage": deepcopy(trace.get("atomic_coverage") or []),
        "sparse_call_records": deepcopy(trace.get("call_records") or []),
        "quality_report": {
            "demotions": demotions,
            "owned_count": len(coverage.get("owned_source_seq", [])),
            "unknown_count": len(coverage.get("unknown_source_seq", [])),
            "object_member_count": len(object_items),
            "mixed_span_run_count": sum(
                1
                for item in items
                if item.get("projection_status") == "mixed_span_actions"
            ),
            "t2_route_hash": (stage_input.get("contract") or {}).get(
                "t2_route_hash"
            ),
            "input_mode": "hierarchical_sparse_stop_or_descend",
            "decision_call_count": trace.get("call_count"),
            "resolution_counts": deepcopy(trace.get("resolution_counts") or {}),
            "coverage_validation": deepcopy(trace.get("validation") or {}),
        },
    }


def _atomic_policy_item(
    rows: list[dict[str, Any]],
    *,
    decisions_by_ref: dict[str, dict[str, Any]],
    order: int,
) -> dict[str, Any]:
    first = rows[0]
    decisions = [
        decisions_by_ref.get(str(row.get("decision_ref") or ""), {}) for row in rows
    ]
    actions = {str(row.get("resolved_result") or "keep") for row in rows}
    action = next(iter(actions)) if len(actions) == 1 else "mixed"
    decision = decisions[0]
    semantic_values = [
        (
            row.get("resolved_result"),
            current.get("fill"),
            current.get("delete"),
        )
        for row, current in zip(rows, decisions)
    ]
    semantics_uniform = all(value == semantic_values[0] for value in semantic_values)
    if action == "mixed":
        policy, semantic_role, transformation = (
            "mixed",
            "mixed_span_content",
            "span_actions",
        )
    else:
        policy, semantic_role, transformation = _policy_fields(action, decision)
    member_refs = [str(row.get("member_ref") or "") for row in rows]
    raw_run_ids = _unique_strings(
        raw_run_id for row in rows for raw_run_id in row.get("raw_run_ids", []) or []
    )
    member_ref = (
        member_refs[0]
        if len(member_refs) == 1
        else f"run:{raw_run_ids[0]}" if len(raw_run_ids) == 1 else f"member-group:{order}"
    )
    decision_refs = _unique_strings(row.get("decision_ref") for row in rows)
    statuses = {str(row.get("decision_status") or "") for row in rows}
    resolutions = {str(row.get("resolution") or "") for row in rows}
    run_text_lengths = {
        int(row.get("run_text_length"))
        for row in rows
        if isinstance(row.get("run_text_length"), int)
    }
    execution_eligible = bool(
        statuses == {"accepted"}
        and action != "mixed"
        and semantics_uniform
        and _covers_complete_raw_run(rows)
    )
    item = {
        "element_id": _element_id(str(first.get("unit_id") or "unit"), member_ref),
        "unit_id": first.get("unit_id"),
        "order": order,
        "core_action": action,
        "policy": policy,
        "role": _role(policy),
        "content": "".join(str(row.get("content") or "") for row in rows),
        "source_seq_refs": sorted(
            {
                int(value)
                for row in rows
                for value in row.get("source_seq_refs", []) or []
            }
        ),
        "source_refs": _unique_strings(
            value for row in rows for value in row.get("source_refs", []) or []
        ),
        "raw_run_ids": raw_run_ids,
        "logical_run_ids": _unique_strings(
            value for row in rows for value in row.get("logical_run_ids", []) or []
        ),
        "run_text_length": (
            next(iter(run_text_lengths)) if len(run_text_lengths) == 1 else None
        ),
        "span_refs": _unique_strings(
            value for row in rows for value in row.get("span_refs", []) or []
        ),
        "char_ranges": [
            deepcopy(char_range)
            for row in rows
            for char_range in row.get("char_ranges", []) or []
            if isinstance(char_range, dict)
        ],
        "spans": [
            _atomic_policy_span(row, current)
            for row, current in zip(rows, decisions)
            if row.get("member_kind") == "span"
        ],
        "confidence": (
            first.get("confidence")
            if len({row.get("confidence") for row in rows}) == 1
            else "low"
        )
        or "low",
        "semantic_role": semantic_role,
        "transformation": transformation,
        "fill_source": None,
        "generated": None,
        "removal_reason": None,
        "ai_rationale": first.get("reason"),
        "ai_decision_path": (
            f"{first.get('decision_target_ref')} -> {member_ref} via "
            f"{next(iter(resolutions)) if len(resolutions) == 1 else 'mixed'} -> {action}"
        ),
        "decision_ref": decision_refs[0] if len(decision_refs) == 1 else None,
        "decision_refs": decision_refs,
        "decision_target_ref": (
            first.get("decision_target_ref")
            if len({row.get("decision_target_ref") for row in rows}) == 1
            else None
        ),
        "decision_status": next(iter(statuses)) if len(statuses) == 1 else "contested",
        "resolution": next(iter(resolutions)) if len(resolutions) == 1 else "mixed",
        "inherited_from": (
            first.get("inherited_from")
            if len({row.get("inherited_from") for row in rows}) == 1
            else None
        ),
        "member_ref": member_ref,
        "member_refs": member_refs,
        "projection_status": (
            "mixed_span_actions" if action == "mixed" else "uniform_span_action"
        ),
        "execution_eligible": execution_eligible,
    }
    fill = decision.get("fill") if isinstance(decision.get("fill"), dict) else {}
    if action == "fill":
        source = str(fill.get("source") or "student_content")
        if source in {"generated", "generated_field"}:
            item["policy"] = "generated"
            item["role"] = "generated_field"
            item["generated"] = {"field_type": fill.get("field") or "FIELD_PLACEHOLDER"}
        else:
            item["fill_source"] = source
            if fill.get("field"):
                item["fill_field"] = fill.get("field")
    if action == "delete":
        delete = decision.get("delete") if isinstance(decision.get("delete"), dict) else {}
        item["removal_reason"] = delete.get("reason") or first.get("reason")
    return item


def _group_atomic_coverage(values: Any) -> list[list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    order: list[tuple[str, str]] = []
    for row in values if isinstance(values, list) else []:
        if not isinstance(row, dict):
            continue
        raw_run_ids = [str(value) for value in row.get("raw_run_ids", []) or [] if value]
        if row.get("member_kind") == "span" and len(raw_run_ids) == 1:
            key = ("raw_run", raw_run_ids[0])
        else:
            key = ("member", str(row.get("member_ref") or len(order)))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    return [groups[key] for key in order]


def _atomic_policy_span(row: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    action = str(row.get("resolved_result") or "keep")
    policy, _semantic_role, _transformation = _policy_fields(action, decision)
    return {
        "span_id": row.get("member_ref"),
        "span_ref": row.get("member_ref"),
        "span_type": "atomic_range",
        "core_action": action,
        "policy": policy,
        "text": row.get("content"),
        "raw_run_ids": deepcopy(row.get("raw_run_ids") or []),
        "logical_run_ids": deepcopy(row.get("logical_run_ids") or []),
        "char_ranges": deepcopy(row.get("char_ranges") or []),
        "run_text_length": row.get("run_text_length"),
        "decision_ref": row.get("decision_ref"),
        "decision_target_ref": row.get("decision_target_ref"),
        "decision_status": row.get("decision_status"),
        "resolution": row.get("resolution"),
        "inherited_from": row.get("inherited_from"),
        "origin": "hierarchical_sparse_coverage",
        "confidence": row.get("confidence"),
    }


def _covers_complete_raw_run(rows: list[dict[str, Any]]) -> bool:
    if not rows or rows[0].get("member_kind") != "span":
        return True
    ranges = [
        char_range
        for row in rows
        for char_range in row.get("char_ranges", []) or []
        if isinstance(char_range, dict)
    ]
    raw_ids = {str(item.get("raw_run_id") or "") for item in ranges}
    lengths = {
        int(row.get("run_text_length"))
        for row in rows
        if isinstance(row.get("run_text_length"), int)
    }
    if len(raw_ids) != 1 or len(lengths) != 1:
        return False
    expected_start = 0
    for item in sorted(ranges, key=lambda value: (value.get("start"), value.get("end"))):
        if item.get("start") != expected_start or not isinstance(item.get("end"), int):
            return False
        expected_start = int(item["end"])
    return expected_start == next(iter(lengths))


def _unique_strings(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "")
        if text and text not in result:
            result.append(text)
    return result


def _policy_fields(
    action: str,
    decision: dict[str, Any],
) -> tuple[str, str, str]:
    if action == "fill":
        fill = decision.get("fill") if isinstance(decision.get("fill"), dict) else {}
        if str(fill.get("source") or "") in {"generated", "generated_field"}:
            return "generated", "generated_field", "generate"
        return "fill", "student_field", "replace_with_slot"
    if action == "delete":
        return "instruction_remove", "format_annotation", "remove_exact_span"
    return "fixed", "fixed_content", "preserve"


def _role(policy: str) -> str:
    if policy == "fill":
        return "student_content"
    if policy == "generated":
        return "generated_field"
    if policy == "instruction_remove":
        return "template_instruction"
    return "template_fixed"


def _element_id(unit_id: str, member_ref: str) -> str:
    safe = "".join(character if character.isalnum() else "_" for character in member_ref)
    return f"{unit_id}.sparse.{safe[-80:]}"
