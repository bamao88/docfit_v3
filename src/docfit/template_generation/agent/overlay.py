from __future__ import annotations

from copy import deepcopy
from typing import Any

from docfit.core.io import sha256_json
from docfit.template_generation.constants import UNIT_DEFINITION_NAMES


T2_OPERATIONS = {
    "add_unit",
    "relabel_unit",
    "adjust_unit_range",
    "replace_unit_elements",
}
T3_POLICIES = {"fixed", "fill", "manual_only", "generated", "remove_instruction"}


def apply_t2_proposal(
    structure_candidates: dict[str, Any],
    proposal: dict[str, Any],
    *,
    collection: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    operation = _t2_operation(proposal, collection)
    if operation not in T2_OPERATIONS:
        return None, None, f"unsupported T2 operation: {operation}"
    before_hash = sha256_json(structure_candidates)
    patched = deepcopy(structure_candidates)
    units = list(patched.get("units", []))
    original_assigned = _assigned_source_seq_refs(units)
    entries_by_seq = _source_entries_by_seq(patched)

    if operation == "add_unit":
        unit_id = str(proposal.get("unit_id") or "").strip()
        if not unit_id:
            return None, None, "add_unit requires unit_id"
        if _unit_by_id(units, unit_id) is not None:
            return None, None, f"unit_id already exists: {unit_id}"
        source_seq_refs = _proposal_source_seq_refs(proposal)
        if not source_seq_refs:
            return None, None, "add_unit requires source_seq_refs"
        source_error = _proposal_source_context_error(source_seq_refs, entries_by_seq)
        if source_error is not None:
            return None, None, source_error
        owner_error = _multi_owner_claim_error(
            units,
            source_seq_refs,
            target_unit=None,
        )
        if owner_error is not None:
            return None, None, owner_error
        _remove_source_seq_refs_from_units(units, set(source_seq_refs), entries_by_seq)
        new_unit = _new_unit_from_proposal(proposal, source_seq_refs, entries_by_seq)
        units.append(new_unit)
        patched["units"] = _sorted_units(units)
    elif operation == "relabel_unit":
        target = _resolve_target_unit(units, proposal)
        if target is None:
            return None, None, "relabel_unit target is ambiguous or missing"
        new_unit_id = str(
            proposal.get("unit_id")
            or proposal.get("canonical_label_id_suggestion")
            or proposal.get("target_unit_id")
            or ""
        ).strip()
        if not new_unit_id:
            return None, None, "relabel_unit requires unit_id or canonical_label_id_suggestion"
        existing = _unit_by_id(units, new_unit_id)
        if existing is not None and existing is not target:
            return None, None, f"unit_id already exists: {new_unit_id}"
        target["unit_id"] = new_unit_id
        target["name"] = str(
            proposal.get("name")
            or proposal.get("display_name")
            or UNIT_DEFINITION_NAMES.get(new_unit_id, new_unit_id)
        )
        target["display_name"] = proposal.get("display_name", target.get("name"))
        target["canonical_label_id"] = proposal.get(
            "canonical_label_id_suggestion",
            target.get("canonical_label_id"),
        )
        target["label_status"] = "agent_relabel"
        target.setdefault("agent_traces", []).append(_trace(proposal))
        patched["units"] = _sorted_units(units)
    elif operation == "adjust_unit_range":
        target = _resolve_target_unit(units, proposal)
        if target is None:
            return None, None, "adjust_unit_range target is ambiguous or missing"
        source_seq_refs = _proposal_source_seq_refs(proposal)
        if not source_seq_refs:
            return None, None, "adjust_unit_range requires source_seq_refs or start/end source_seq"
        source_error = _proposal_source_context_error(source_seq_refs, entries_by_seq)
        if source_error is not None:
            return None, None, source_error
        owner_error = _multi_owner_claim_error(
            units,
            source_seq_refs,
            target_unit=target,
        )
        if owner_error is not None:
            return None, None, owner_error
        _remove_source_seq_refs_from_units(
            [unit for unit in units if unit is not target],
            set(source_seq_refs),
            entries_by_seq,
        )
        _replace_unit_sources(target, source_seq_refs, entries_by_seq)
        target.setdefault("agent_traces", []).append(_trace(proposal))
        patched["units"] = _sorted_units(units)
    elif operation == "replace_unit_elements":
        target = _resolve_target_unit(units, proposal)
        if target is None:
            return None, None, "replace_unit_elements target is ambiguous or missing"
        source_seq_refs = _proposal_source_seq_refs(proposal) or list(target.get("source_seq_refs", []))
        if not set(source_seq_refs).issubset(set(target.get("source_seq_refs", []))):
            return None, None, "replace_unit_elements source_seq_refs must belong to target unit"
        target["elements"] = _elements_from_proposal(
            proposal,
            source_seq_refs,
            entries_by_seq,
            unit_id=str(target.get("unit_id") or ""),
        )
        target.setdefault("agent_traces", []).append(_trace(proposal))
        patched["units"] = _sorted_units(units)

    executable_error = _overlay_executable_error(
        original_assigned,
        patched.get("units", []),
        all_source_seq_refs=set(entries_by_seq),
    )
    if executable_error is not None:
        return None, None, executable_error
    source_seq_refs = _proposal_source_seq_refs(proposal)
    operation_payload = {
        "proposal_id": proposal.get("proposal_id"),
        "operation": operation,
        "collection": collection,
        "target_unit_id": proposal.get("target_unit_id") or proposal.get("unit_id"),
        "source_seq_refs": source_seq_refs,
        "round0_unassigned_source_seq_refs": [
            seq for seq in source_seq_refs if seq not in original_assigned
        ],
        "round0_reassigned_source_seq_refs": [
            seq for seq in source_seq_refs if seq in original_assigned
        ],
        "before_hash": before_hash,
        "after_hash": sha256_json(patched),
    }
    return patched, operation_payload, ""


def apply_t3_proposal(
    structure_candidates: dict[str, Any],
    proposal: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    policy = str(proposal.get("policy") or proposal.get("candidate_policy") or "").strip()
    if policy == "remove":
        return None, None, "policy remove is not executable in current generation code"
    if policy not in T3_POLICIES:
        return None, None, f"unsupported T3 policy: {policy}"
    before_hash = sha256_json(structure_candidates)
    patched = deepcopy(structure_candidates)
    target = bind_t3_target(patched, proposal)
    if target is None:
        return None, None, "T3 target is ambiguous or missing"
    unit, element = target
    element["candidate_policy"] = policy
    element.setdefault("agent_traces", []).append(_trace(proposal))
    operation_payload = {
        "proposal_id": proposal.get("proposal_id"),
        "operation": "set_candidate_policy",
        "target_candidate_id": f"{unit.get('unit_id')}.{element.get('element_id')}",
        "policy": policy,
        "source_seq_refs": _proposal_source_seq_refs(proposal),
        "before_hash": before_hash,
        "after_hash": sha256_json(patched),
    }
    return patched, operation_payload, ""


def bind_t3_target(
    structure_candidates: dict[str, Any],
    proposal: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    explicit = str(proposal.get("target_candidate_id") or "").strip()
    source_seq_refs = set(_proposal_source_seq_refs(proposal))
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for unit in structure_candidates.get("units", []):
        unit_id = str(unit.get("unit_id") or "")
        for element in unit.get("elements", []):
            element_id = str(element.get("element_id") or "")
            target_id = f"{unit_id}.{element_id}"
            if explicit and explicit == target_id:
                matches.append((unit, element))
                continue
            if not source_seq_refs:
                continue
            element_refs = set(_ints(element.get("source_seq_refs", [])))
            if source_seq_refs and source_seq_refs.issubset(element_refs):
                matches.append((unit, element))
    unique: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for unit, element in matches:
        unique[f"{unit.get('unit_id')}.{element.get('element_id')}"] = (unit, element)
    if len(unique) != 1:
        return None
    return next(iter(unique.values()))


def _t2_operation(proposal: dict[str, Any], collection: str) -> str:
    operation = str(proposal.get("operation") or "").strip()
    if operation:
        return operation
    return {
        "unit_candidates": "add_unit",
        "block_candidates": "replace_unit_elements",
        "boundary_adjustments": "adjust_unit_range",
    }.get(collection, "")


def _new_unit_from_proposal(
    proposal: dict[str, Any],
    source_seq_refs: list[int],
    entries_by_seq: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    unit_id = str(proposal.get("unit_id") or "")
    name = str(
        proposal.get("name")
        or proposal.get("display_name")
        or UNIT_DEFINITION_NAMES.get(unit_id, unit_id)
    )
    source_refs = _source_refs_for_seq_refs(source_seq_refs, entries_by_seq)
    return {
        "unit_id": unit_id,
        "name": name,
        "order": 0,
        "status": "required",
        "label_status": "agent_added",
        "canonical_label_id": proposal.get("canonical_label_id_suggestion"),
        "raw_title": proposal.get("raw_label") or proposal.get("display_name") or name,
        "normalized_title": proposal.get("normalized_label"),
        "display_name": proposal.get("display_name") or name,
        "candidate_policy": proposal.get("candidate_policy") or "fill",
        "source_refs": source_refs,
        "source_seq_refs": source_seq_refs,
        "source_range": _source_range(source_seq_refs, entries_by_seq),
        "source_seq_range": _source_seq_range(source_seq_refs),
        "anchors": [
            {
                "source_ref": source_refs[0] if source_refs else None,
                "source_seq": source_seq_refs[0] if source_seq_refs else None,
                "text": proposal.get("raw_label") or name,
                "confidence": "medium",
                "signals": [{"kind": "agent_overlay", "proposal_id": proposal.get("proposal_id")}],
            }
        ],
        "responsibility_evidence": [
            {
                "kind": "agent_t2_overlay",
                "proposal_id": proposal.get("proposal_id"),
            }
        ],
        "conflicts": [],
        "confidence": "medium",
        "flags": [],
        "evidence": [{"kind": "agent_t2_overlay", "proposal_id": proposal.get("proposal_id")}],
        "elements": _elements_from_proposal(proposal, source_seq_refs, entries_by_seq, unit_id=unit_id),
        "agent_traces": [_trace(proposal)],
    }


def _replace_unit_sources(
    unit: dict[str, Any],
    source_seq_refs: list[int],
    entries_by_seq: dict[int, dict[str, Any]],
) -> None:
    unit["source_seq_refs"] = source_seq_refs
    unit["source_refs"] = _source_refs_for_seq_refs(source_seq_refs, entries_by_seq)
    unit["source_range"] = _source_range(source_seq_refs, entries_by_seq)
    unit["source_seq_range"] = _source_seq_range(source_seq_refs)
    unit["elements"] = _elements_from_proposal(
        {},
        source_seq_refs,
        entries_by_seq,
        unit_id=str(unit.get("unit_id") or ""),
    )


def _remove_source_seq_refs_from_units(
    units: list[dict[str, Any]],
    refs: set[int],
    entries_by_seq: dict[int, dict[str, Any]],
) -> None:
    for unit in units:
        remaining = [seq for seq in _ints(unit.get("source_seq_refs", [])) if seq not in refs]
        if remaining == _ints(unit.get("source_seq_refs", [])):
            continue
        _replace_unit_sources(unit, remaining, entries_by_seq)


def _elements_from_proposal(
    proposal: dict[str, Any],
    source_seq_refs: list[int],
    entries_by_seq: dict[int, dict[str, Any]],
    *,
    unit_id: str,
) -> list[dict[str, Any]]:
    proposal_elements = proposal.get("elements")
    if isinstance(proposal_elements, list) and proposal_elements:
        return [
            _normalize_proposal_element(element, index, entries_by_seq, unit_id=unit_id)
            for index, element in enumerate(proposal_elements, start=1)
            if isinstance(element, dict)
        ]
    elements: list[dict[str, Any]] = []
    for index, source_seq in enumerate(source_seq_refs, start=1):
        entry = entries_by_seq.get(source_seq, {})
        source_ref = str(entry.get("source_ref") or "")
        text = str(entry.get("text") or "")
        elements.append(
            {
                "element_id": f"e_{index:03d}",
                "name": text[:32] or f"{unit_id} element {index}",
                "order": index,
                "candidate_policy": "fixed",
                "role_hint": "fixed_text_candidate",
                "relationship": "agent_overlay_source",
                "content": text,
                "style": entry.get("style", ""),
                "source_refs": [source_ref] if source_ref else [],
                "source_seq_refs": [source_seq],
                "entry_refs": [entry.get("node_id")] if entry.get("node_id") else [],
                "evidence": [
                    {
                        "kind": "agent_overlay_source_seq",
                        "source_seq": source_seq,
                    }
                ],
            }
        )
    return elements


def _normalize_proposal_element(
    element: dict[str, Any],
    index: int,
    entries_by_seq: dict[int, dict[str, Any]],
    *,
    unit_id: str,
) -> dict[str, Any]:
    source_seq_refs = _ints(element.get("source_seq_refs", []))
    source_refs = _source_refs_for_seq_refs(source_seq_refs, entries_by_seq)
    return {
        "element_id": str(element.get("element_id") or f"e_{index:03d}"),
        "name": str(element.get("name") or element.get("content") or f"{unit_id} element {index}"),
        "order": int(element.get("order") or index),
        "candidate_policy": str(element.get("candidate_policy") or element.get("policy") or "fixed"),
        "role_hint": str(element.get("role_hint") or "fixed_text_candidate"),
        "relationship": str(element.get("relationship") or "agent_overlay_source"),
        "content": str(element.get("content") or ""),
        "style": element.get("style", ""),
        "source_refs": list(element.get("source_refs") or source_refs),
        "source_seq_refs": source_seq_refs,
        "entry_refs": list(element.get("entry_refs") or []),
        "evidence": list(element.get("evidence") or []),
    }


def _resolve_target_unit(
    units: list[dict[str, Any]],
    proposal: dict[str, Any],
) -> dict[str, Any] | None:
    target_unit_id = str(proposal.get("target_unit_id") or "").strip()
    if target_unit_id:
        return _unit_by_id(units, target_unit_id)
    source_seq_refs = set(_proposal_source_seq_refs(proposal))
    if not source_seq_refs:
        return None
    matches = [
        unit
        for unit in units
        if source_seq_refs.issubset(set(_ints(unit.get("source_seq_refs", []))))
        or source_seq_refs.intersection(set(_ints(unit.get("source_seq_refs", []))))
    ]
    unique: dict[str, dict[str, Any]] = {
        str(unit.get("unit_id") or index): unit
        for index, unit in enumerate(matches)
    }
    if len(unique) != 1:
        return None
    return next(iter(unique.values()))


def _overlay_executable_error(
    original_assigned: set[int],
    units: list[dict[str, Any]],
    *,
    all_source_seq_refs: set[int],
) -> str | None:
    seen: dict[int, str] = {}
    unit_ids: set[str] = set()
    body_main = None
    for unit in units:
        unit_id = str(unit.get("unit_id") or "")
        if unit_id in unit_ids:
            return f"duplicate unit_id after overlay: {unit_id}"
        unit_ids.add(unit_id)
        if unit_id == "body_main":
            body_main = unit
        for seq in _ints(unit.get("source_seq_refs", [])):
            if seq in seen:
                return f"source_seq {seq} is owned by multiple units"
            if seq not in all_source_seq_refs:
                return f"source_seq {seq} is not present in source context"
            seen[seq] = unit_id
    if "body_main" not in unit_ids:
        return "body_main cannot be removed"
    if body_main is not None and original_assigned and not body_main.get("source_seq_refs"):
        return "body_main cannot be emptied by overlay"
    unowned_original = sorted(original_assigned - set(seen))
    if unowned_original:
        return f"overlay cannot leave round0-owned source_seq unowned: {unowned_original}"
    return None


def _proposal_source_context_error(
    source_seq_refs: list[int],
    entries_by_seq: dict[int, dict[str, Any]],
) -> str | None:
    missing = [seq for seq in source_seq_refs if seq not in entries_by_seq]
    if missing:
        return f"source_seq_refs not present in source context: {missing}"
    return None


def _multi_owner_claim_error(
    units: list[dict[str, Any]],
    source_seq_refs: list[int],
    *,
    target_unit: dict[str, Any] | None,
) -> str | None:
    owner_ids: set[str] = set()
    refs = set(source_seq_refs)
    for unit in units:
        if target_unit is not None and unit is target_unit:
            continue
        owned = refs.intersection(set(_ints(unit.get("source_seq_refs", []))))
        if owned:
            owner_ids.add(str(unit.get("unit_id") or ""))
    if len(owner_ids) > 1:
        return (
            "overlay cannot claim source_seq_refs from multiple existing units: "
            f"{sorted(owner_ids)}"
        )
    return None


def _sorted_units(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_units = sorted(
        units,
        key=lambda unit: (
            min(_ints(unit.get("source_seq_refs", [])) or [10**9]),
            str(unit.get("unit_id") or ""),
        ),
    )
    for index, unit in enumerate(sorted_units, start=1):
        unit["order"] = index * 10
    return sorted_units


def _source_entries_by_seq(structure_candidates: dict[str, Any]) -> dict[int, dict[str, Any]]:
    entries: dict[int, dict[str, Any]] = {}
    for entry in structure_candidates.get("source_context", {}).get("body_flow", []):
        source_seq = _int_or_none(entry.get("source_seq"))
        if source_seq is not None:
            entries[source_seq] = entry
    return entries


def _assigned_source_seq_refs(units: list[dict[str, Any]]) -> set[int]:
    return {
        source_seq
        for unit in units
        for source_seq in _ints(unit.get("source_seq_refs", []))
    }


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


def _source_refs_for_seq_refs(
    source_seq_refs: list[int],
    entries_by_seq: dict[int, dict[str, Any]],
) -> list[str]:
    return [
        str(entries_by_seq.get(source_seq, {}).get("source_ref") or "")
        for source_seq in source_seq_refs
        if entries_by_seq.get(source_seq, {}).get("source_ref")
    ]


def _source_range(
    source_seq_refs: list[int],
    entries_by_seq: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    source_refs = _source_refs_for_seq_refs(source_seq_refs, entries_by_seq)
    if not source_refs:
        return {}
    return {
        "start_source_ref": source_refs[0],
        "end_source_ref": source_refs[-1],
        "source_refs": source_refs,
    }


def _source_seq_range(source_seq_refs: list[int]) -> dict[str, Any]:
    if not source_seq_refs:
        return {}
    return {
        "start": source_seq_refs[0],
        "end": source_seq_refs[-1],
        "source_seq_refs": source_seq_refs,
    }


def _unit_by_id(units: list[dict[str, Any]], unit_id: str) -> dict[str, Any] | None:
    for unit in units:
        if str(unit.get("unit_id") or "") == unit_id:
            return unit
    return None


def _trace(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "round_id": proposal.get("round_id"),
        "rationale": proposal.get("rationale"),
        "evidence": proposal.get("evidence"),
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
