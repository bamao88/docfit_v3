"""Compare code, AI and merged T3 routes on one atomic identity ledger."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from docfit.template_generation.t3_action_projection import t3_core_action


def build_t3_atomic_route_comparison(
    *,
    stage_input: dict[str, Any],
    code_element_spec: dict[str, Any],
    ai_observation: dict[str, Any],
    merged_element_spec: dict[str, Any],
) -> dict[str, Any]:
    """Project all three routes onto Stage Input member refs without expanding AI calls."""

    leaves = _atomic_leaves(stage_input)
    code_rows = _element_route(leaves, code_element_spec, route="code_raw")
    ai_rows = _ai_route(leaves, ai_observation)
    merged_rows = _element_route(leaves, merged_element_spec, route="merged")
    code_by_ref = {row["member_ref"]: row for row in code_rows}
    ai_by_ref = {row["member_ref"]: row for row in ai_rows}
    merged_by_ref = {row["member_ref"]: row for row in merged_rows}
    rows: list[dict[str, Any]] = []
    for member_ref in sorted(leaves):
        code = code_by_ref[member_ref]
        ai = ai_by_ref[member_ref]
        merged = merged_by_ref[member_ref]
        code_action = code.get("resolved_action")
        ai_action = ai.get("resolved_action")
        merged_action = merged.get("resolved_action")
        ai_accepted = ai.get("decision_status") == "accepted"
        rows.append(
            {
                "member_ref": member_ref,
                "member_kind": leaves[member_ref].get("source_kind"),
                "source_seq_refs": deepcopy(leaves[member_ref].get("source_seq_refs") or []),
                "raw_run_ids": _raw_run_ids(leaves[member_ref]),
                "span_refs": (
                    [member_ref]
                    if leaves[member_ref].get("source_kind") == "span"
                    else []
                ),
                "char_ranges": _leaf_char_ranges(leaves[member_ref]),
                "code": code,
                "ai": ai,
                "merged": merged,
                "code_ai_relation": (
                    "unavailable"
                    if code_action is None or ai_action is None
                    else ("same" if code_action == ai_action else "different")
                ),
                "merged_resolution": _merged_resolution(
                    code_action=code_action,
                    ai_action=ai_action,
                    merged_action=merged_action,
                    ai_accepted=ai_accepted,
                ),
            }
        )
    relation_counts = Counter(row["code_ai_relation"] for row in rows)
    merge_counts = Counter(row["merged_resolution"] for row in rows)
    return {
        "artifact_type": "t3_atomic_route_comparison",
        "artifact_version": "1.0",
        "stage_input_ref": {
            "artifact_version": stage_input.get("artifact_version"),
            "tree_hash": stage_input.get("tree_hash"),
        },
        "summary": {
            "atomic_member_count": len(rows),
            "code_ai_same": relation_counts["same"],
            "code_ai_different": relation_counts["different"],
            "unavailable": relation_counts["unavailable"],
            "merged_from_ai": merge_counts["ai"],
            "merged_from_code": merge_counts["code"],
            "merged_contested": merge_counts["contested"],
        },
        "rows": rows,
        "validation": {
            "valid": all(
                len({row["member_ref"] for row in route}) == len(leaves)
                for route in (code_rows, ai_rows, merged_rows)
            ),
            "expected_member_count": len(leaves),
            "route_member_counts": {
                "code_raw": len(code_rows),
                "ai_raw": len(ai_rows),
                "merged": len(merged_rows),
            },
        },
    }


def _atomic_leaves(stage_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_ref = {
        str(node.get("ref")): node
        for node in stage_input.get("nodes", []) or []
        if isinstance(node, dict) and node.get("ref")
    }
    refs = {
        str(member_ref)
        for root in stage_input.get("unit_roots", []) or []
        if isinstance(root, dict)
        for member_ref in (
            by_ref.get(str(root.get("root_ref") or ""), {}).get("member_leaf_refs", [])
            or []
        )
    }
    return {ref: by_ref[ref] for ref in refs if ref in by_ref}


def _element_route(
    leaves: dict[str, dict[str, Any]],
    element_spec: dict[str, Any],
    *,
    route: str,
) -> list[dict[str, Any]]:
    elements = [
        element
        for element in element_spec.get("elements", []) or []
        if isinstance(element, dict)
    ]
    rows: list[dict[str, Any]] = []
    for member_ref, leaf in leaves.items():
        raw_ids = set(_raw_run_ids(leaf))
        source_seqs = set(_ints(leaf.get("source_seq_refs")))
        matches = []
        for element in elements:
            element_raw = set(_strings(element.get("raw_run_ids")))
            element_seqs = set(_ints(element.get("source_seq_refs")))
            if raw_ids and raw_ids.issubset(element_raw):
                matches.append(element)
            elif not raw_ids and source_seqs and source_seqs.issubset(element_seqs):
                matches.append(element)
        if len(matches) == 1:
            element = matches[0]
            resolved_actions = _element_actions_for_leaf(element, leaf)
            rows.append(
                {
                    "member_ref": member_ref,
                    "route": route,
                    "resolved_action": (
                        next(iter(resolved_actions))
                        if len(resolved_actions) == 1
                        else None
                    ),
                    "resolved_actions": sorted(resolved_actions),
                    "policy": element.get("policy"),
                    "status": "resolved" if len(resolved_actions) == 1 else "contested",
                    "element_id": element.get("stable_id") or element.get("element_id"),
                    "agent_traces": deepcopy(element.get("agent_traces") or []),
                }
            )
        else:
            rows.append(
                {
                    "member_ref": member_ref,
                    "route": route,
                    "resolved_action": None,
                    "policy": None,
                    "status": "unavailable" if not matches else "contested",
                    "matching_element_ids": [
                        element.get("stable_id") or element.get("element_id")
                        for element in matches
                    ],
                }
            )
    return rows


def _ai_route(
    leaves: dict[str, dict[str, Any]],
    observation: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw in observation.get("atomic_coverage", []) or []:
        if isinstance(raw, dict) and raw.get("member_ref"):
            grouped.setdefault(str(raw["member_ref"]), []).append(raw)
    rows: list[dict[str, Any]] = []
    for member_ref in leaves:
        matches = grouped.get(member_ref, [])
        if len(matches) == 1:
            row = matches[0]
            rows.append(
                {
                    "member_ref": member_ref,
                    "route": "ai_raw",
                    "resolved_action": row.get("resolved_result"),
                    "status": row.get("resolution"),
                    "decision_status": row.get("decision_status"),
                    "decision_ref": row.get("decision_ref"),
                    "decision_target_ref": row.get("decision_target_ref"),
                    "inherited_from": row.get("inherited_from"),
                }
            )
        else:
            rows.append(
                {
                    "member_ref": member_ref,
                    "route": "ai_raw",
                    "resolved_action": "keep" if len(matches) > 1 else None,
                    "status": "contested" if matches else "unavailable",
                    "decision_status": "contested" if matches else "missing",
                }
            )
    return rows


def _merged_resolution(
    *,
    code_action: Any,
    ai_action: Any,
    merged_action: Any,
    ai_accepted: bool,
) -> str:
    if merged_action is None:
        return "unavailable"
    if ai_accepted and ai_action != code_action and merged_action == ai_action:
        return "ai"
    if merged_action == code_action:
        return "code"
    return "contested"


def _element_actions_for_leaf(
    element: dict[str, Any],
    leaf: dict[str, Any],
) -> set[str]:
    parent_action = t3_core_action(element)
    if leaf.get("source_kind") != "span":
        return {parent_action} if parent_action else set()
    facts = leaf.get("facts") or {}
    raw_run_id = str(facts.get("raw_run_id") or "")
    start = facts.get("start")
    end = facts.get("end")
    if not raw_run_id or not isinstance(start, int) or not isinstance(end, int):
        return {parent_action} if parent_action else set()

    actions: set[str] = set()
    covered: list[tuple[int, int]] = []
    span_claimed = False
    for span in element.get("spans", []) or []:
        if not isinstance(span, dict) or raw_run_id not in _span_raw_run_ids(span):
            continue
        ranges = [
            item
            for item in span.get("char_ranges", []) or []
            if isinstance(item, dict)
            and str(item.get("raw_run_id") or "") == raw_run_id
            and isinstance(item.get("start"), int)
            and isinstance(item.get("end"), int)
        ]
        if not ranges:
            span_claimed = True
            action = t3_core_action(span, allow_span_type=True)
            if action:
                actions.add(action)
            continue
        for char_range in ranges:
            overlap_start = max(start, int(char_range["start"]))
            overlap_end = min(end, int(char_range["end"]))
            if overlap_start >= overlap_end and not (
                start == end == overlap_start == overlap_end
            ):
                continue
            span_claimed = True
            covered.append((overlap_start, overlap_end))
            action = t3_core_action(span, allow_span_type=True)
            if action:
                actions.add(action)
    if not span_claimed:
        return {parent_action} if parent_action else set()
    if not _ranges_cover(covered, start=start, end=end) and parent_action:
        actions.add(parent_action)
    return actions


def _span_raw_run_ids(span: dict[str, Any]) -> set[str]:
    result = set(_strings(span.get("raw_run_ids")))
    result.update(
        str(item.get("raw_run_id"))
        for item in span.get("char_ranges", []) or []
        if isinstance(item, dict) and item.get("raw_run_id")
    )
    return result


def _ranges_cover(
    ranges: list[tuple[int, int]],
    *,
    start: int,
    end: int,
) -> bool:
    if start == end:
        return any(range_start <= start <= range_end for range_start, range_end in ranges)
    cursor = start
    for range_start, range_end in sorted(ranges):
        if range_end <= cursor:
            continue
        if range_start > cursor:
            return False
        cursor = max(cursor, range_end)
        if cursor >= end:
            return True
    return cursor >= end


def _leaf_char_ranges(leaf: dict[str, Any]) -> list[dict[str, Any]]:
    facts = leaf.get("facts") or {}
    if leaf.get("source_kind") != "span" or not facts.get("raw_run_id"):
        return []
    if not isinstance(facts.get("start"), int) or not isinstance(facts.get("end"), int):
        return []
    return [
        {
            "raw_run_id": facts["raw_run_id"],
            "start": facts["start"],
            "end": facts["end"],
        }
    ]


def _raw_run_ids(leaf: dict[str, Any]) -> list[str]:
    raw = (leaf.get("facts") or {}).get("raw_run_id")
    return [str(raw)] if raw else []


def _strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if value not in (None, "")]


def _ints(values: Any) -> list[int]:
    result: list[int] = []
    for value in values if isinstance(values, list) else []:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return result
