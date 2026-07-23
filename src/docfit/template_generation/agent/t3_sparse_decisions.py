"""Validated sparse T3 decisions, stop-or-descend traversal and coverage.

AI emits only visited decision boundaries.  This module validates those
boundaries against the Stage Input tree and deterministically expands every
terminal/default/fallback result to exactly one atomic coverage row per leaf.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from docfit.core.io import sha256_json

from .t3_hierarchical_input import nodes_by_ref, t3_node_evidence


T3_SPARSE_DECISION_VERSION = "t3-sparse-decision-1.1"
_RESULTS = frozenset({"keep", "fill", "delete", "split"})
_CONFIDENCE = frozenset({"low", "medium", "high"})
_TERMINAL_ACTIONS = {
    "unit": frozenset({"keep"}),
    "table": frozenset({"keep"}),
    "row": frozenset({"keep", "fill"}),
    "cell": frozenset({"keep", "fill"}),
    "paragraph": frozenset({"keep", "fill"}),
    "run": frozenset({"keep", "fill", "delete"}),
    "span": frozenset({"keep", "fill", "delete"}),
    "field": frozenset({"keep", "fill"}),
    "content_control": frozenset({"keep", "fill"}),
    "text_box": frozenset({"keep"}),
    "image": frozenset({"keep"}),
    "footnote": frozenset({"keep"}),
    "source_object": frozenset({"keep"}),
}


DecisionProvider = Callable[[dict[str, Any], dict[str, Any], str], dict[str, Any]]


def run_t3_sparse_traversal(
    stage_input: dict[str, Any],
    *,
    decide: DecisionProvider,
    max_depth: int = 7,
    max_calls: int = 512,
) -> dict[str, Any]:
    """Traverse each unit from its root and expand complete atomic coverage."""

    by_ref = nodes_by_ref(stage_input)
    decisions: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    call_records: list[dict[str, Any]] = []
    call_count = 0

    def add_decision(
        node: dict[str, Any],
        *,
        unit_id: str,
        raw: dict[str, Any] | None,
        status_override: str | None = None,
        reason_override: str | None = None,
    ) -> dict[str, Any]:
        decision, errors = validate_t3_sparse_decision(
            raw,
            node=node,
            by_ref=by_ref,
        )
        if status_override is not None:
            decision["decision_status"] = status_override
        if reason_override:
            decision["reason"] = reason_override
        decision["unit_id"] = unit_id
        decision["decision_ref"] = _decision_ref(
            tree_hash=str(stage_input.get("tree_hash") or ""),
            target_ref=str(node.get("ref") or ""),
            ordinal=len(decisions),
        )
        decision["validation_errors"] = errors
        decisions.append(decision)
        return decision

    def expand(
        node: dict[str, Any],
        *,
        unit_id: str,
        decision: dict[str, Any],
        action: str,
        resolution: str,
        inherited_from: str | None,
    ) -> None:
        for leaf_ref in node.get("member_leaf_refs", []) or []:
            leaf = by_ref.get(str(leaf_ref))
            if leaf is None:
                continue
            coverage.append(
                _coverage_row(
                    leaf=leaf,
                    unit_id=unit_id,
                    action=action,
                    resolution=resolution,
                    inherited_from=inherited_from,
                    decision=decision,
                )
            )

    def fallback_subtree(
        node: dict[str, Any],
        *,
        unit_id: str,
        status: str,
        reason: str,
    ) -> None:
        decision = add_decision(
            node,
            unit_id=unit_id,
            raw={"target_ref": node.get("ref"), "result": "keep", "confidence": "low"},
            status_override=status,
            reason_override=reason,
        )
        expand(
            node,
            unit_id=unit_id,
            decision=decision,
            action="keep",
            resolution="fallback",
            inherited_from=None,
        )

    def visit(node_ref: str, *, unit_id: str, depth: int) -> None:
        nonlocal call_count
        node = by_ref[node_ref]
        if depth > max_depth:
            fallback_subtree(
                node,
                unit_id=unit_id,
                status="fallback",
                reason=f"maximum traversal depth {max_depth} reached",
            )
            return
        if call_count >= max_calls:
            fallback_subtree(
                node,
                unit_id=unit_id,
                status="fallback",
                reason=f"maximum decision call budget {max_calls} reached",
            )
            return

        evidence = t3_node_evidence(stage_input, target_ref=node_ref)
        call_count += 1
        raw: dict[str, Any]
        error: str | None = None
        try:
            response = decide(evidence, node, unit_id)
            raw = response if isinstance(response, dict) else {}
        except Exception as exc:  # provider failures become explicit safe coverage
            raw = {}
            error = f"{type(exc).__name__}: {exc}"
        if error is not None or raw.get("_observation_error"):
            reason = error or str(raw.get("_observation_error"))
            call_records.append(
                {"target_ref": node_ref, "status": "failed", "error": reason}
            )
            fallback_subtree(
                node,
                unit_id=unit_id,
                status="failed",
                reason=f"node decision call failed: {reason}",
            )
            return

        decision = add_decision(node, unit_id=unit_id, raw=raw)
        call_records.append(
            {
                "target_ref": node_ref,
                "status": decision["decision_status"],
                "result": decision["result"],
                "validation_errors": deepcopy(decision["validation_errors"]),
            }
        )
        result = str(decision["result"])
        if result != "split":
            resolution = (
                "fallback"
                if decision["decision_status"] != "accepted"
                else ("direct" if node_ref in set(node.get("member_leaf_refs") or []) else "inherited")
            )
            expand(
                node,
                unit_id=unit_id,
                decision=decision,
                action=result,
                resolution=resolution,
                inherited_from=(
                    node_ref if resolution == "inherited" else None
                ),
            )
            return

        inspect = set(decision.get("inspect_child_refs") or [])
        inline_child_decisions = {
            str(child_decision.get("target_ref") or ""): child_decision
            for child_decision in decision.get("child_decisions", []) or []
            if isinstance(child_decision, dict)
        }
        for child_ref in node.get("child_refs", []) or []:
            child = by_ref[str(child_ref)]
            if child_ref in inline_child_decisions:
                child_decision = add_decision(
                    child,
                    unit_id=unit_id,
                    raw=inline_child_decisions[child_ref],
                )
                call_records.append(
                    {
                        "target_ref": child_ref,
                        "status": child_decision["decision_status"],
                        "result": child_decision["result"],
                        "source": "parent_inline_child_decision",
                        "validation_errors": deepcopy(
                            child_decision["validation_errors"]
                        ),
                    }
                )
                child_resolution = (
                    "fallback"
                    if child_decision["decision_status"] != "accepted"
                    else (
                        "direct"
                        if child_ref in set(child.get("member_leaf_refs") or [])
                        else "inherited"
                    )
                )
                expand(
                    child,
                    unit_id=unit_id,
                    decision=child_decision,
                    action=str(child_decision["result"]),
                    resolution=child_resolution,
                    inherited_from=(
                        child_ref if child_resolution == "inherited" else None
                    ),
                )
                continue
            if child_ref in inspect:
                visit(str(child_ref), unit_id=unit_id, depth=depth + 1)
                continue
            expand(
                child,
                unit_id=unit_id,
                decision=decision,
                action="keep",
                resolution="inherited",
                inherited_from=node_ref,
            )

    for root in stage_input.get("unit_roots", []) or []:
        if not isinstance(root, dict):
            continue
        root_ref = str(root.get("root_ref") or "")
        if root_ref not in by_ref:
            continue
        visit(
            root_ref,
            unit_id=str(root.get("unit_id") or ""),
            depth=0,
        )

    coverage, coverage_errors = _normalize_coverage(
        coverage,
        expected_leaf_refs={
            str(leaf_ref)
            for root in stage_input.get("unit_roots", []) or []
            if isinstance(root, dict)
            for leaf_ref in (by_ref.get(str(root.get("root_ref") or "")) or {}).get(
                "member_leaf_refs", []
            )
        },
    )
    return {
        "artifact_type": "t3_sparse_decision_trace",
        "artifact_version": T3_SPARSE_DECISION_VERSION,
        "stage_input_ref": {
            "artifact_version": stage_input.get("artifact_version"),
            "tree_hash": stage_input.get("tree_hash"),
            "contract": deepcopy(stage_input.get("contract") or {}),
        },
        "limits": {"max_depth": max_depth, "max_calls": max_calls},
        "call_count": call_count,
        "decisions": decisions,
        "atomic_coverage": coverage,
        "call_records": call_records,
        "validation": {
            "valid": not coverage_errors,
            "errors": coverage_errors,
        },
        "resolution_counts": {
            resolution: sum(1 for row in coverage if row.get("resolution") == resolution)
            for resolution in ("direct", "inherited", "fallback", "contested")
        },
    }


def validate_t3_sparse_decision(
    raw: dict[str, Any] | None,
    *,
    node: dict[str, Any],
    by_ref: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Normalize one model decision; unsafe/invalid output becomes fallback Keep."""

    payload = raw if isinstance(raw, dict) else {}
    target_ref = str(node.get("ref") or "")
    errors: list[dict[str, str]] = []
    proposed_target = str(payload.get("target_ref") or "")
    if proposed_target != target_ref:
        errors.append(_error("target_ref", f"expected {target_ref}, got {proposed_target or '<missing>'}"))
    result = str(payload.get("result") or "").lower()
    if result not in _RESULTS:
        errors.append(_error("result", f"unsupported result: {result or '<missing>'}"))

    confidence = str(payload.get("confidence") or "low").lower()
    if confidence not in _CONFIDENCE:
        confidence = "low"
        errors.append(_error("confidence", "confidence must be low, medium or high"))
    child_refs = _strings(node.get("child_refs"))
    allowed_children = set(child_refs)
    inspect_refs = _strings(payload.get("inspect_child_refs"))
    invalid_children = sorted(set(inspect_refs) - allowed_children)
    if invalid_children:
        errors.append(_error("inspect_child_refs", f"not direct children: {invalid_children}"))
    if len(inspect_refs) != len(set(inspect_refs)):
        errors.append(_error("inspect_child_refs", "duplicate child refs are not allowed"))
    raw_child_decisions = [
        item
        for item in payload.get("child_decisions", []) or []
        if isinstance(item, dict)
    ]
    if payload.get("child_decisions") is not None and not isinstance(
        payload.get("child_decisions"), list
    ):
        errors.append(_error("child_decisions", "child_decisions must be a list"))
    child_decision_refs = [
        str(item.get("target_ref") or "") for item in raw_child_decisions
    ]
    if len(child_decision_refs) != len(set(child_decision_refs)):
        errors.append(_error("child_decisions", "duplicate child decision refs are not allowed"))
    invalid_child_decision_refs = sorted(
        ref for ref in child_decision_refs if ref not in allowed_children
    )
    if invalid_child_decision_refs:
        errors.append(
            _error(
                "child_decisions",
                f"not direct children: {invalid_child_decision_refs}",
            )
        )
    uninspected_child_decisions = sorted(
        ref for ref in child_decision_refs if ref not in set(inspect_refs)
    )
    if uninspected_child_decisions:
        errors.append(
            _error(
                "child_decisions",
                f"child decisions must also appear in inspect_child_refs: {uninspected_child_decisions}",
            )
        )
    if any(str(item.get("result") or "").lower() == "split" for item in raw_child_decisions):
        errors.append(
            _error(
                "child_decisions",
                "inline child decisions must be terminal; recurse for child split",
            )
        )

    source_kind = str(node.get("source_kind") or "source_object")
    allowed_terminal = _TERMINAL_ACTIONS.get(source_kind, frozenset({"keep"}))
    if result == "split":
        if not child_refs:
            errors.append(_error("result", "leaf node cannot split"))
        if not inspect_refs:
            errors.append(_error("inspect_child_refs", "split must inspect at least one direct child"))
        if str(payload.get("default_child_result") or "keep") != "keep":
            errors.append(_error("default_child_result", "split default must be keep"))
        if not bool((node.get("completeness") or {}).get("children_complete")):
            errors.append(_error("completeness", "node children are incomplete and cannot be split safely"))
    elif result not in allowed_terminal:
        errors.append(_error("result", f"{source_kind} does not allow terminal {result}"))
    if result != "split" and raw_child_decisions:
        errors.append(_error("child_decisions", "terminal decisions cannot include child_decisions"))

    if result in {"keep", "fill", "delete"} and not _terminal_scope_complete(node):
        errors.append(_error("completeness", "terminal decision cannot cover an incomplete container"))
    if result == "fill":
        fill = payload.get("fill")
        if not isinstance(fill, dict) or not str(fill.get("source") or "").strip():
            errors.append(_error("fill.source", "fill decision requires a source"))
    if result == "delete":
        if source_kind not in {"run", "span"}:
            errors.append(_error("result", "delete is restricted to exact run/span nodes"))
        if confidence != "high":
            errors.append(_error("confidence", "delete requires high confidence"))
        delete = payload.get("delete")
        if not isinstance(delete, dict) or not str(delete.get("reason") or "").strip():
            errors.append(_error("delete.reason", "delete requires an explicit reason"))

    if errors:
        return (
            {
                "target_ref": target_ref,
                "result": "keep",
                "decision_status": "manual_review",
                "confidence": "low",
                "reason": "unsafe or invalid sparse decision; conservative Keep fallback",
                "default_child_result": None,
                "inspect_child_refs": [],
                "child_decisions": [],
                "fill": None,
                "delete": None,
                "raw_decision": deepcopy(payload),
            },
            errors,
        )

    return (
        {
            "target_ref": target_ref,
            "result": result,
            "decision_status": "accepted",
            "confidence": confidence,
            "reason": str(payload.get("reason") or "")[:2000],
            "default_child_result": "keep" if result == "split" else None,
            "inspect_child_refs": inspect_refs if result == "split" else [],
            "child_decisions": deepcopy(raw_child_decisions) if result == "split" else [],
            "fill": deepcopy(payload.get("fill")) if result == "fill" else None,
            "delete": deepcopy(payload.get("delete")) if result == "delete" else None,
            "raw_decision": deepcopy(payload),
        },
        [],
    )


def _coverage_row(
    *,
    leaf: dict[str, Any],
    unit_id: str,
    action: str,
    resolution: str,
    inherited_from: str | None,
    decision: dict[str, Any],
) -> dict[str, Any]:
    facts = leaf.get("facts") or {}
    raw_run_id = facts.get("raw_run_id")
    start = facts.get("start")
    end = facts.get("end")
    is_span = leaf.get("source_kind") == "span"
    return {
        "member_ref": leaf.get("ref"),
        "member_kind": leaf.get("source_kind"),
        "unit_id": unit_id,
        "source_refs": deepcopy(leaf.get("source_refs") or []),
        "source_seq_refs": deepcopy(leaf.get("source_seq_refs") or []),
        "span_refs": [leaf.get("ref")] if is_span else [],
        "char_ranges": (
            [
                {
                    "raw_run_id": raw_run_id,
                    "start": start,
                    "end": end,
                }
            ]
            if is_span
            and raw_run_id
            and isinstance(start, int)
            and isinstance(end, int)
            else []
        ),
        "run_text_length": facts.get("run_text_length"),
        "raw_run_ids": [raw_run_id] if raw_run_id else [],
        "logical_run_ids": (
            [facts.get("logical_run_id")]
            if facts.get("logical_run_id")
            else []
        ),
        "content": facts.get("text"),
        "resolved_result": action,
        "resolution": resolution,
        "inherited_from": inherited_from,
        "decision_ref": decision.get("decision_ref"),
        "decision_target_ref": decision.get("target_ref"),
        "decision_status": decision.get("decision_status"),
        "confidence": decision.get("confidence"),
        "reason": decision.get("reason"),
        "fill": deepcopy(decision.get("fill")),
        "delete": deepcopy(decision.get("delete")),
    }


def _normalize_coverage(
    rows: list[dict[str, Any]],
    *,
    expected_leaf_refs: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("member_ref") or ""), []).append(row)
    normalized: list[dict[str, Any]] = []
    for member_ref in sorted(expected_leaf_refs):
        claims = grouped.get(member_ref, [])
        if not claims:
            errors.append(_error("atomic_coverage", f"missing atomic member: {member_ref}"))
            continue
        if len(claims) > 1:
            errors.append(_error("atomic_coverage", f"overlapping decisions for: {member_ref}"))
            contested = deepcopy(claims[0])
            contested["resolved_result"] = "keep"
            contested["resolution"] = "contested"
            contested["decision_status"] = "contested"
            contested["reason"] = "multiple sparse decisions resolved the same atomic member"
            normalized.append(contested)
            continue
        normalized.append(claims[0])
    extras = sorted(set(grouped) - expected_leaf_refs)
    if extras:
        errors.append(_error("atomic_coverage", f"unexpected atomic members: {extras[:8]}"))
    return normalized, errors


def _terminal_scope_complete(node: dict[str, Any]) -> bool:
    completeness = node.get("completeness") or {}
    if node.get("child_refs"):
        return bool(
            completeness.get("children_complete")
            and completeness.get("content_complete")
            and not completeness.get("truncated")
            and not completeness.get("omitted_child_count")
            and not completeness.get("unbound_member_count")
        )
    return bool(completeness.get("content_complete") and not completeness.get("truncated"))


def _decision_ref(*, tree_hash: str, target_ref: str, ordinal: int) -> str:
    digest = sha256_json(
        {"tree_hash": tree_hash, "target_ref": target_ref, "ordinal": ordinal}
    )
    return f"decision:{digest[-20:]}"


def _strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value or "").strip()]


def _error(field: str, message: str) -> dict[str, str]:
    return {"field": field, "check_id": "C-T3-SPARSE-DECISION", "message": message}
