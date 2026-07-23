from __future__ import annotations

from collections import Counter
from typing import Any

from docfit.core.io import now_iso, sha256_json

from .packet import packet_page_set, packet_render_target_set, packet_source_seq_set


AUTO_STATUSES = {"compatible", "missing"}


def build_submission_comparison(
    items: list[dict[str, Any]],
    *,
    packet: dict[str, Any],
    deterministic_structure: dict[str, Any],
) -> dict[str, Any]:
    normalized_items = []
    for index, item in enumerate(items, start=1):
        comparison_id = item.get("comparison_id") or _stable_comparison_id(item, index)
        normalized_items.append({"comparison_id": comparison_id, **item})
    status_counts = Counter(str(item.get("status") or "unknown") for item in normalized_items)
    return {
        "artifact_type": "template_agent_submission_comparison",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "source_render_hash": packet.get("source_render_hash"),
        "deterministic_structure_hash": sha256_json(deterministic_structure),
        "summary": {
            "total": len(normalized_items),
            "compatible": status_counts.get("compatible", 0),
            "missing": status_counts.get("missing", 0),
            "conflict": status_counts.get("conflict", 0),
            "unknown": status_counts.get("unknown", 0),
            "manual_review_required": sum(
                1 for item in normalized_items if item.get("manual_review_required")
            ),
            "auto_executable": sum(
                1 for item in normalized_items if item.get("can_auto_execute")
            ),
        },
        "items": normalized_items,
    }


def compare_proposal(
    *,
    structure_candidates: dict[str, Any],
    packet: dict[str, Any],
    proposal: dict[str, Any],
    layer: str,
    collection: str,
) -> dict[str, Any]:
    affected_refs = _affected_refs(proposal)
    uncertain_reason = _explicit_uncertainty_reason(proposal)
    if uncertain_reason is not None:
        return _item(
            proposal,
            layer=layer,
            collection=collection,
            status="unknown",
            check_id="C-AI-UNCERTAIN",
            reason=uncertain_reason,
            affected_refs=affected_refs,
            deterministic={},
        )

    binding_error = _binding_error(packet, proposal)
    if binding_error is not None:
        return _item(
            proposal,
            layer=layer,
            collection=collection,
            status="unknown",
            check_id="C-EVIDENCE-EXIST",
            reason=binding_error,
            affected_refs=affected_refs,
            deterministic={},
        )

    if layer == "t2":
        return _compare_t2(
            structure_candidates=structure_candidates,
            packet=packet,
            proposal=proposal,
            collection=collection,
            affected_refs=affected_refs,
        )
    if layer == "t4":
        return _compare_t4(packet=packet, proposal=proposal, collection=collection, affected_refs=affected_refs)
    return _item(
        proposal,
        layer=layer,
        collection=collection,
        status="unknown",
        check_id="C-SCHEMA",
        reason=f"unsupported layer for comparison: {layer}",
        affected_refs=affected_refs,
        deterministic={},
    )


def compare_blocked_by_open_questions(
    *,
    proposal: dict[str, Any],
    layer: str,
    collection: str,
    open_questions: list[dict[str, Any]],
) -> dict[str, Any]:
    return _item(
        proposal,
        layer=layer,
        collection=collection,
        status="unknown",
        check_id="C-OPEN-QUESTION",
        reason=f"layer {layer} has blocking open_questions",
        affected_refs=_affected_refs(proposal),
        deterministic={},
        ai={"open_question_ids": [_question_id(question) for question in open_questions]},
    )


def blocking_open_questions_by_layer(
    submission: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    layers = submission.get("layers") or {}
    if not isinstance(layers, dict):
        return result
    for layer, layer_value in layers.items():
        if not isinstance(layer_value, dict):
            continue
        questions = []
        for raw_question in layer_value.get("open_questions", []) or []:
            question = (
                raw_question
                if isinstance(raw_question, dict)
                else {"question": str(raw_question)}
            )
            if _is_blocking_open_question(question):
                questions.append(question)
        if questions:
            result[str(layer)] = questions
    return result


def comparison_rejection_decision(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposal_id": item.get("proposal_id"),
        "round_id": item.get("round_id"),
        "decision": "rejected",
        "checks": [
            {
                "check_id": item.get("check_id") or "C-COMPARISON",
                "status": "FAIL",
                "reason": item.get("reason"),
                "comparison_id": item.get("comparison_id"),
            }
        ],
        "target_path": item.get("target_path"),
        "before_hash": None,
        "after_hash": None,
        "reason": item.get("reason"),
        "origin": "comparison",
        "manual_review_required": True,
        **_pass_context(item),
    }


def _compare_t2(
    *,
    structure_candidates: dict[str, Any],
    packet: dict[str, Any],
    proposal: dict[str, Any],
    collection: str,
    affected_refs: dict[str, Any],
) -> dict[str, Any]:
    operation = _t2_operation(proposal, collection)
    source_seq_refs = affected_refs["source_seq_refs"]
    owners = _source_seq_owners(structure_candidates)
    owner_ids = sorted({owners[seq] for seq in source_seq_refs if seq in owners})
    deterministic = {
        "operation": operation,
        "source_seq_owners": {str(seq): owners.get(seq) for seq in source_seq_refs},
    }
    if operation == "add_unit":
        unit_id = str(proposal.get("unit_id") or "").strip()
        if _unit_by_id(structure_candidates, unit_id) is not None:
            return _item(
                proposal,
                layer="t2",
                collection=collection,
                status="conflict",
                check_id="C-COMPARISON-CONFLICT",
                reason=f"deterministic structure already has unit_id: {unit_id}",
                affected_refs=affected_refs,
                deterministic=deterministic,
            )
        if not source_seq_refs:
            return _item(
                proposal,
                layer="t2",
                collection=collection,
                status="unknown",
                check_id="C-EVIDENCE-EXIST",
                reason="add_unit requires source_seq_refs for comparison",
                affected_refs=affected_refs,
                deterministic=deterministic,
            )
        if len(owner_ids) > 1:
            return _item(
                proposal,
                layer="t2",
                collection=collection,
                status="conflict",
                check_id="C-COMPARISON-CONFLICT",
                reason=(
                    "proposal conflicts with deterministic ownership by multiple "
                    f"existing units: {owner_ids}"
                ),
                affected_refs=affected_refs,
                deterministic=deterministic,
            )
        if owner_ids and owner_ids != ["body_main"]:
            return _item(
                proposal,
                layer="t2",
                collection=collection,
                status="conflict",
                check_id="C-COMPARISON-CONFLICT",
                reason=(
                    "proposal assigns source_seq_refs to a new unit, but deterministic "
                    f"ownership is {owner_ids}"
                ),
                affected_refs=affected_refs,
                deterministic=deterministic,
            )
        reason = (
            "deterministic structure has no owner for these source_seq_refs"
            if not owner_ids
            else "deterministic structure only has generic body_main ownership"
        )
        return _item(
            proposal,
            layer="t2",
            collection=collection,
            status="missing",
            check_id="C-COMPARISON-MISSING",
            reason=reason,
            affected_refs=affected_refs,
            deterministic=deterministic,
        )

    if operation == "adjust_unit_range":
        pages = _pages_for_source_seq_refs(packet, source_seq_refs)
        if len(pages) > 1 and not _is_contiguous(source_seq_refs):
            return _item(
                proposal,
                layer="t2",
                collection=collection,
                status="unknown",
                check_id="C-HIGH-RISK",
                reason=(
                    "adjust_unit_range crosses multiple pages with non-contiguous "
                    "source_seq_refs and requires manual review"
                ),
                affected_refs=affected_refs,
                deterministic={**deterministic, "page_nos": pages},
                risk_level="high",
            )
        target_unit = _target_unit(structure_candidates, proposal)
        if target_unit is None:
            return _item(
                proposal,
                layer="t2",
                collection=collection,
                status="unknown",
                check_id="C-TARGET-BIND",
                reason="adjust_unit_range target is ambiguous or missing",
                affected_refs=affected_refs,
                deterministic=deterministic,
            )
        target_id = str(target_unit.get("unit_id") or "")
        external_owners = [owner_id for owner_id in owner_ids if owner_id != target_id]
        if len(external_owners) > 1:
            return _item(
                proposal,
                layer="t2",
                collection=collection,
                status="conflict",
                check_id="C-COMPARISON-CONFLICT",
                reason=(
                    "adjust_unit_range claims source_seq_refs from multiple existing "
                    f"units: {external_owners}"
                ),
                affected_refs=affected_refs,
                deterministic={**deterministic, "target_unit_id": target_id},
            )
        return _item(
            proposal,
            layer="t2",
            collection=collection,
            status="compatible",
            check_id="C-COMPARISON-COMPATIBLE",
            reason="boundary proposal is compatible with deterministic target binding",
            affected_refs=affected_refs,
            deterministic={**deterministic, "target_unit_id": target_id},
        )

    if operation in {"relabel_unit", "replace_unit_elements", "set_page_policy"}:
        target_unit = _target_unit(structure_candidates, proposal)
        if target_unit is None:
            return _item(
                proposal,
                layer="t2",
                collection=collection,
                status="unknown",
                check_id="C-TARGET-BIND",
                reason=f"{operation} target is ambiguous or missing",
                affected_refs=affected_refs,
                deterministic=deterministic,
            )
        return _item(
            proposal,
            layer="t2",
            collection=collection,
            status="compatible",
            check_id="C-COMPARISON-COMPATIBLE",
            reason=f"{operation} target is present in deterministic structure",
            affected_refs=affected_refs,
            deterministic={
                **deterministic,
                "target_unit_id": target_unit.get("unit_id"),
                "current_page_policy": target_unit.get("page_policy") if operation == "set_page_policy" else None,
            },
        )

    return _item(
        proposal,
        layer="t2",
        collection=collection,
        status="unknown",
        check_id="C-EXECUTABLE-ENUM",
        reason=f"unsupported T2 operation: {operation}",
        affected_refs=affected_refs,
        deterministic=deterministic,
    )


def _compare_t4(
    *,
    packet: dict[str, Any],
    proposal: dict[str, Any],
    collection: str,
    affected_refs: dict[str, Any],
) -> dict[str, Any]:
    if packet.get("render_status") != "real_render":
        return _item(
            proposal,
            layer="t4",
            collection=collection,
            status="unknown",
            check_id="C-RENDER-REQUIRED",
            reason="T4 layout hints require a real_render packet",
            affected_refs=affected_refs,
            deterministic={"render_status": packet.get("render_status")},
        )
    return _item(
        proposal,
        layer="t4",
        collection=collection,
        status="compatible",
        check_id="C-COMPARISON-COMPATIBLE",
        reason="T4 hint is advisory-only and has render evidence",
        affected_refs=affected_refs,
        deterministic={"render_status": packet.get("render_status")},
    )


def _item(
    proposal: dict[str, Any],
    *,
    layer: str,
    collection: str,
    status: str,
    check_id: str,
    reason: str,
    affected_refs: dict[str, Any],
    deterministic: dict[str, Any],
    ai: dict[str, Any] | None = None,
    risk_level: str = "low",
) -> dict[str, Any]:
    manual_review_required = status not in AUTO_STATUSES or risk_level == "high"
    proposal_id = proposal.get("proposal_id")
    return {
        **(
            {"comparison_id": f"cmp_{_slug(str(proposal_id))}"}
            if proposal_id not in (None, "")
            else {}
        ),
        "proposal_id": proposal_id,
        "round_id": proposal.get("round_id"),
        "layer": layer,
        "collection": collection,
        "status": status,
        "check_id": check_id,
        "reason": reason,
        "risk_level": risk_level,
        "manual_review_required": manual_review_required,
        "can_auto_execute": not manual_review_required,
        "affected_refs": affected_refs,
        "ai": {
            "kind": proposal.get("kind"),
            "operation": proposal.get("operation"),
            "unit_id": proposal.get("unit_id"),
            "target_unit_id": proposal.get("target_unit_id"),
            "target_candidate_id": proposal.get("target_candidate_id"),
            "policy": proposal.get("policy") or proposal.get("candidate_policy"),
            "rationale": proposal.get("rationale"),
            **(ai or {}),
        },
        "deterministic": deterministic,
        **_pass_context(proposal),
    }


def _binding_error(packet: dict[str, Any], proposal: dict[str, Any]) -> str | None:
    valid_source_seq = packet_source_seq_set(packet)
    valid_render_targets = packet_render_target_set(packet)
    valid_pages = packet_page_set(packet)

    invalid_seq = [
        source_seq
        for source_seq in _proposal_source_seq_refs(proposal)
        if source_seq not in valid_source_seq
    ]
    if invalid_seq:
        return f"source_seq_refs not present in render packet: {invalid_seq}"

    render_target_refs = proposal.get("render_target_refs") or []
    if isinstance(render_target_refs, list) and render_target_refs:
        invalid_targets = [
            str(target)
            for target in render_target_refs
            if str(target) not in valid_render_targets
        ]
        if invalid_targets:
            return f"render_target_refs not present in render packet: {invalid_targets}"

    invalid_pages = [
        page_no for page_no in _proposal_page_nos(proposal) if page_no not in valid_pages
    ]
    if invalid_pages:
        return f"page_nos not present in render packet: {invalid_pages}"
    return None


def _affected_refs(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_seq_refs": _proposal_source_seq_refs(proposal),
        "source_refs": _strings(proposal.get("source_refs", [])),
        "raw_run_ids": _strings(proposal.get("raw_run_ids", [])),
        "logical_run_ids": _strings(proposal.get("logical_run_ids", [])),
        "member_refs": _strings(
            [proposal.get("member_ref")] if proposal.get("member_ref") else []
        ),
        "decision_refs": _strings(
            [proposal.get("decision_ref")] if proposal.get("decision_ref") else []
        ),
        "page_nos": _proposal_page_nos(proposal),
        "render_target_refs": [
            str(target)
            for target in proposal.get("render_target_refs", []) or []
            if target not in (None, "")
        ],
    }


def _strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(
        dict.fromkeys(
            str(value)
            for value in values
            if value not in (None, "") and str(value).strip()
        )
    )


def _proposal_source_seq_refs(proposal: dict[str, Any]) -> list[int]:
    values = _ints(proposal.get("source_seq_refs", []))
    if not values and proposal.get("source_seq") is not None:
        values = _ints([proposal.get("source_seq")])
    if not values:
        start = _int_or_none(proposal.get("start_source_seq"))
        end = _int_or_none(proposal.get("end_source_seq"))
        if start is not None and end is not None and start <= end:
            values = list(range(start, end + 1))
    return sorted(dict.fromkeys(values))


def _is_contiguous(values: list[int]) -> bool:
    if not values:
        return False
    ordered = sorted(dict.fromkeys(values))
    return ordered == list(range(ordered[0], ordered[-1] + 1))


def _proposal_page_nos(proposal: dict[str, Any]) -> list[int]:
    values: list[int] = []
    if proposal.get("page_no") is not None:
        parsed = _int_or_none(proposal.get("page_no"))
        if parsed is not None:
            values.append(parsed)
    values.extend(_ints(proposal.get("page_nos", [])))
    return sorted(dict.fromkeys(values))


def _pages_for_source_seq_refs(packet: dict[str, Any], source_seq_refs: list[int]) -> list[int]:
    wanted = set(source_seq_refs)
    pages = []
    for item in packet.get("page_text_index", []) or []:
        source_seq = _int_or_none(item.get("source_seq"))
        page_no = _int_or_none(item.get("page_no"))
        if source_seq in wanted and page_no is not None:
            pages.append(page_no)
    return sorted(dict.fromkeys(pages))


def _source_seq_owners(structure_candidates: dict[str, Any]) -> dict[int, str]:
    owners: dict[int, str] = {}
    for unit in structure_candidates.get("units", []) or []:
        unit_id = str(unit.get("unit_id") or "")
        for source_seq in _ints(unit.get("source_seq_refs", [])):
            owners[source_seq] = unit_id
    return owners


def _target_unit(
    structure_candidates: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any] | None:
    target_unit_id = str(proposal.get("target_unit_id") or "").strip()
    if target_unit_id:
        return _unit_by_id(structure_candidates, target_unit_id)
    source_seq_refs = set(_proposal_source_seq_refs(proposal))
    if not source_seq_refs:
        return None
    matches = [
        unit
        for unit in structure_candidates.get("units", []) or []
        if source_seq_refs.intersection(set(_ints(unit.get("source_seq_refs", []))))
    ]
    unique = {str(unit.get("unit_id") or index): unit for index, unit in enumerate(matches)}
    if len(unique) != 1:
        return None
    return next(iter(unique.values()))


def _unit_by_id(
    structure_candidates: dict[str, Any],
    unit_id: str,
) -> dict[str, Any] | None:
    if not unit_id:
        return None
    for unit in structure_candidates.get("units", []) or []:
        if str(unit.get("unit_id") or "") == unit_id:
            return unit
    return None


def _t2_operation(proposal: dict[str, Any], collection: str) -> str:
    operation = str(proposal.get("operation") or "").strip()
    if operation:
        return operation
    return {
        "unit_candidates": "add_unit",
        "block_candidates": "replace_unit_elements",
        "boundary_adjustments": "adjust_unit_range",
        "page_policy_candidates": "set_page_policy",
    }.get(collection, "")


def _explicit_uncertainty_reason(proposal: dict[str, Any]) -> str | None:
    if proposal.get("needs_human_review") is True:
        return "proposal explicitly requested human review"
    for key in ("status", "state", "classification"):
        value = str(proposal.get(key) or "").strip().lower()
        if value in {"unknown", "ambiguous", "needs_human_review"}:
            return f"proposal marked {value}"
    if proposal.get("ambiguous") is True:
        return "proposal marked ambiguous"
    return None


def _is_blocking_open_question(question: dict[str, Any]) -> bool:
    value = str(question.get("blocking_level") or question.get("severity") or "").lower()
    if not value:
        return question.get("blocking", True) is not False
    return value not in {"non_blocking", "non-blocking", "info", "low"}


def _question_id(question: dict[str, Any]) -> str | None:
    value = question.get("question_id") or question.get("id")
    return str(value) if value not in (None, "") else None


def _stable_comparison_id(item: dict[str, Any], index: int) -> str:
    proposal_id = str(item.get("proposal_id") or "").strip()
    if proposal_id:
        return f"cmp_{_slug(proposal_id)}"
    return f"cmp_{index:03d}"


def _pass_context(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "pass_id": item.get("pass_id"),
        "pass_kind": item.get("pass_kind"),
        "window_id": item.get("window_id"),
        "pass_unit_id": item.get("pass_unit_id") or item.get("unit_id"),
    }


def _ints(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    result: list[int] = []
    for value in values:
        parsed = _int_or_none(value)
        if parsed is not None:
            result.append(parsed)
    return result


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value)
