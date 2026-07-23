from __future__ import annotations

from copy import deepcopy
from typing import Any

from docfit.core.io import sha256_json
from docfit.template_generation.page_policy import normalize_unit_page_policy
from docfit.template_generation.constants import KEEP_ONLY_UNIT_IDS, UNIT_DEFINITION_NAMES
from docfit.template_generation.structure_candidates import (
    _element_name,
    _element_policy,
    _element_type,
    _role_hint_for_policy,
)


T2_OPERATIONS = {
    "add_unit",
    "relabel_unit",
    "adjust_unit_range",
    "replace_unit_elements",
    "set_page_policy",
}
T3_POLICIES = {"fixed", "fill", "generated", "remove_instruction"}


def t3_execution_policy(value: Any) -> str:
    """Map a semantic T3 decision to its safe executable policy.

    ``unknown`` must remain observable in the judgment artifact, but execution
    is deliberately asymmetric: uncertainty may preserve content and may never
    authorize replacement or deletion.
    """

    policy = str(value or "").strip()
    return "fixed" if policy == "unknown" else policy


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
    elif operation == "set_page_policy":
        target = _resolve_target_unit(units, proposal)
        if target is None:
            return None, None, "set_page_policy target is ambiguous or missing"
        target["page_policy"] = normalize_unit_page_policy(proposal.get("page_policy"))
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


def apply_t2_boundary_adjustment_batch(
    structure_candidates: dict[str, Any],
    proposals: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str]:
    if not proposals:
        return structure_candidates, [], ""
    before_hash = sha256_json(structure_candidates)
    patched = deepcopy(structure_candidates)
    units = list(patched.get("units", []))
    original_assigned = _assigned_source_seq_refs(units)
    entries_by_seq = _source_entries_by_seq(patched)
    target_payloads: list[tuple[dict[str, Any], dict[str, Any], list[int], str]] = []
    seen_targets: set[str] = set()
    claimed_by_seq: dict[int, str] = {}

    for proposal in proposals:
        operation = _t2_operation(proposal, "boundary_adjustments")
        if operation != "adjust_unit_range":
            return None, [], f"batch only supports adjust_unit_range, got: {operation}"
        target = _resolve_target_unit(units, proposal)
        if target is None:
            return None, [], "adjust_unit_range target is ambiguous or missing"
        target_unit_id = str(target.get("unit_id") or "")
        if target_unit_id in seen_targets:
            return None, [], f"duplicate boundary adjustment target: {target_unit_id}"
        source_seq_refs = _proposal_source_seq_refs(proposal)
        if not source_seq_refs:
            return None, [], "adjust_unit_range requires source_seq_refs or start/end source_seq"
        source_error = _proposal_source_context_error(source_seq_refs, entries_by_seq)
        if source_error is not None:
            return None, [], source_error
        for source_seq in source_seq_refs:
            existing_target = claimed_by_seq.get(source_seq)
            if existing_target is not None and existing_target != target_unit_id:
                return (
                    None,
                    [],
                    f"source_seq {source_seq} claimed by multiple boundary targets",
                )
            claimed_by_seq[source_seq] = target_unit_id
        seen_targets.add(target_unit_id)
        target_payloads.append((proposal, target, source_seq_refs, target_unit_id))

    target_ids = {target_unit_id for _, _, _, target_unit_id in target_payloads}
    claimed_refs = set(claimed_by_seq)
    for unit in units:
        if str(unit.get("unit_id") or "") not in target_ids:
            _remove_source_seq_refs_from_units([unit], claimed_refs, entries_by_seq)
    for proposal, target, source_seq_refs, _target_unit_id in target_payloads:
        _replace_unit_sources(target, source_seq_refs, entries_by_seq)
        target.setdefault("agent_traces", []).append(_trace(proposal))
    patched["units"] = _sorted_units(units)

    executable_error = _overlay_executable_error(
        original_assigned,
        patched.get("units", []),
        all_source_seq_refs=set(entries_by_seq),
    )
    if executable_error is not None:
        return None, [], executable_error

    after_hash = sha256_json(patched)
    operations = [
        {
            "proposal_id": proposal.get("proposal_id"),
            "operation": "adjust_unit_range",
            "collection": "boundary_adjustments",
            "target_unit_id": target_unit_id,
            "source_seq_refs": source_seq_refs,
            "round0_unassigned_source_seq_refs": [
                seq for seq in source_seq_refs if seq not in original_assigned
            ],
            "round0_reassigned_source_seq_refs": [
                seq for seq in source_seq_refs if seq in original_assigned
            ],
            "batch_id": "t2_boundary_adjustments",
            "batch_size": len(target_payloads),
            "before_hash": before_hash,
            "after_hash": after_hash,
        }
        for proposal, _target, source_seq_refs, target_unit_id in target_payloads
    ]
    return patched, operations, ""


def apply_t3_proposal(
    structure_candidates: dict[str, Any],
    proposal: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    observed_policy = str(
        proposal.get("observed_policy")
        or proposal.get("policy")
        or proposal.get("candidate_policy")
        or ""
    ).strip()
    policy = t3_execution_policy(
        proposal.get("policy") or proposal.get("candidate_policy")
    )
    if observed_policy == "remove":
        return None, None, "policy remove is not executable in current generation code"
    if policy not in T3_POLICIES:
        return None, None, f"unsupported T3 policy: {policy}"
    before_hash = sha256_json(structure_candidates)
    patched = deepcopy(structure_candidates)
    target = bind_t3_target(patched, proposal)
    if target is None:
        return None, None, "T3 target is ambiguous or missing"
    unit, element = target
    unit_id = str(unit.get("unit_id") or "")
    if policy == "fill" and unit_id in KEEP_ONLY_UNIT_IDS:
        return (
            None,
            None,
            f"T3 fill policy is not executable for keep-only unit: {unit_id}",
        )
    proposal_raw_run_ids = _strings(proposal.get("raw_run_ids", []))
    element_raw_run_ids = _strings(element.get("raw_run_ids", []))
    targets = [element]
    if proposal_raw_run_ids and set(proposal_raw_run_ids) != set(element_raw_run_ids):
        targets, split_error = _split_t3_element_for_raw_runs(
            patched,
            unit=unit,
            element=element,
            selected_raw_run_ids=proposal_raw_run_ids,
        )
        if split_error:
            return None, None, split_error
    for target in targets:
        _apply_t3_policy(target, policy=policy, proposal=proposal)
    target_ids = [
        f"{unit.get('unit_id')}.{target.get('element_id')}"
        for target in targets
    ]
    operation_payload = {
        "proposal_id": proposal.get("proposal_id"),
        "operation": "set_candidate_policy",
        "target_candidate_id": target_ids[0] if len(target_ids) == 1 else None,
        "target_candidate_ids": target_ids,
        "policy": policy,
        "observed_policy": observed_policy,
        "execution_fallback_action": (
            "keep" if observed_policy == "unknown" else None
        ),
        "source_seq_refs": _proposal_source_seq_refs(proposal),
        "raw_run_ids": proposal_raw_run_ids,
        "logical_run_ids": _strings(proposal.get("logical_run_ids", [])),
        "span_refs": _strings(proposal.get("span_refs", [])),
        "char_ranges": deepcopy(proposal.get("char_ranges") or []),
        "decision_ref": proposal.get("decision_ref"),
        "decision_target_ref": proposal.get("decision_target_ref"),
        "member_ref": proposal.get("member_ref"),
        "member_refs": _strings(proposal.get("member_refs", [])),
        "resolution": proposal.get("resolution"),
        "before_hash": before_hash,
        "after_hash": sha256_json(patched),
    }
    return patched, operation_payload, ""


def bind_t3_target(
    structure_candidates: dict[str, Any],
    proposal: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    explicit = str(proposal.get("target_candidate_id") or "").strip()
    proposal_unit_id = str(proposal.get("unit_id") or "").strip()
    source_seq_refs = set(_proposal_source_seq_refs(proposal))
    raw_run_ids = set(_strings(proposal.get("raw_run_ids", [])))
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for unit in structure_candidates.get("units", []):
        unit_id = str(unit.get("unit_id") or "")
        if proposal_unit_id and proposal_unit_id != unit_id:
            continue
        for element in unit.get("elements", []):
            element_id = str(element.get("element_id") or "")
            target_id = f"{unit_id}.{element_id}"
            if raw_run_ids:
                element_raw_run_ids = set(_strings(element.get("raw_run_ids", [])))
                if raw_run_ids.issubset(element_raw_run_ids):
                    matches.append((unit, element))
                continue
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


def _apply_t3_policy(
    element: dict[str, Any],
    *,
    policy: str,
    proposal: dict[str, Any],
) -> None:
    element["candidate_policy"] = policy
    if proposal.get("fill_source") not in (None, ""):
        element["fill_source"] = proposal.get("fill_source")
    if proposal.get("fill_field") not in (None, ""):
        element["fill_field"] = proposal.get("fill_field")
    if proposal.get("generated") is not None:
        element["generated"] = deepcopy(proposal.get("generated"))
    if proposal.get("removal_reason") not in (None, ""):
        element["removal_reason"] = proposal.get("removal_reason")
    element.setdefault("agent_traces", []).append(_trace(proposal))


def _split_t3_element_for_raw_runs(
    structure_candidates: dict[str, Any],
    *,
    unit: dict[str, Any],
    element: dict[str, Any],
    selected_raw_run_ids: list[str],
) -> tuple[list[dict[str, Any]], str]:
    original_raw_ids = _strings(element.get("raw_run_ids", []))
    selected = set(selected_raw_run_ids)
    if not original_raw_ids or not selected.issubset(set(original_raw_ids)):
        return [], "T3 raw_run_ids are not contained by the bound element"
    runs_by_raw = (
        structure_candidates.get("source_context", {}).get("runs_by_raw_run_id", {})
        or {}
    )
    missing = [raw_run_id for raw_run_id in original_raw_ids if raw_run_id not in runs_by_raw]
    if missing:
        return [], f"T3 run-level split lacks source run facts: {missing}"

    groups: list[tuple[bool, list[str]]] = []
    for raw_run_id in original_raw_ids:
        is_selected = raw_run_id in selected
        if groups and groups[-1][0] == is_selected:
            groups[-1][1].append(raw_run_id)
        else:
            groups.append((is_selected, [raw_run_id]))

    original_id = str(element.get("element_id") or "element")
    replacements: list[dict[str, Any]] = []
    selected_elements: list[dict[str, Any]] = []
    for index, (is_selected, raw_ids) in enumerate(groups, start=1):
        replacement = deepcopy(element)
        replacement["element_id"] = (
            original_id if index == 1 else f"{original_id}.agent_split_{index:03d}"
        )
        replacement["raw_run_ids"] = raw_ids
        replacement["logical_run_ids"] = _dedupe_strings(
            (runs_by_raw.get(raw_run_id) or {}).get("logical_run_id")
            for raw_run_id in raw_ids
        )
        replacement["run_source_refs"] = _dedupe_strings(
            (runs_by_raw.get(raw_run_id) or {}).get("source_ref")
            for raw_run_id in raw_ids
        )
        replacement["content"] = "".join(
            str((runs_by_raw.get(raw_run_id) or {}).get("text") or "")
            for raw_run_id in raw_ids
        )
        replacement["normalized_content"] = str(replacement["content"]).strip()
        replacement["merge"] = {
            "type": "agent_exact_raw_run_split",
            "source_element_id": original_id,
            "selected": is_selected,
        }
        replacements.append(replacement)
        if is_selected:
            selected_elements.append(replacement)

    elements = list(unit.get("elements", []))
    try:
        position = next(index for index, candidate in enumerate(elements) if candidate is element)
    except StopIteration:
        return [], "T3 bound element disappeared before run-level split"
    elements[position : position + 1] = replacements
    for order, candidate in enumerate(elements, start=1):
        candidate["order"] = order
    unit["elements"] = elements
    return selected_elements, ""


def _unit_policy(unit: dict[str, Any]) -> str:
    policy = str(unit.get("candidate_policy") or unit.get("policy") or "").strip()
    if policy:
        return policy
    unit_id = str(unit.get("unit_id") or "")
    if unit_id in KEEP_ONLY_UNIT_IDS:
        return "fixed"
    return ""


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
        policy = _element_policy(unit_id, text, entry)
        raw_run_ids = [str(value) for value in entry.get("raw_run_ids", []) or [] if value]
        logical_run_ids = [
            str(value) for value in entry.get("logical_run_ids", []) or [] if value
        ]
        run_source_refs = [
            str(value) for value in entry.get("run_source_refs", []) or [] if value
        ]
        elements.append(
            {
                "element_id": f"e_{index:03d}",
                "name": _element_name(unit_id, text, policy),
                "order": index,
                "candidate_policy": policy,
                "type": _element_type(policy),
                "fill": "yes" if policy == "fill" else "no",
                "role_hint": _role_hint_for_policy(policy),
                "relationship": "agent_overlay_source",
                "content": text if policy != "remove_instruction" else "",
                "normalized_content": text,
                "style": entry.get("style", ""),
                "style_evidence": entry.get("style_details", {}),
                "source_refs": [source_ref] if source_ref else [],
                "source_seq_refs": [source_seq],
                "raw_run_ids": raw_run_ids,
                "logical_run_ids": logical_run_ids,
                "run_source_refs": run_source_refs,
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
        "spans": list(element.get("spans") or []),
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
        "decision_ref": proposal.get("decision_ref"),
        "decision_target_ref": proposal.get("decision_target_ref"),
        "decision_status": proposal.get("decision_status"),
        "resolution": proposal.get("resolution"),
        "inherited_from": proposal.get("inherited_from"),
        "member_ref": proposal.get("member_ref"),
        "raw_run_ids": _strings(proposal.get("raw_run_ids", [])),
        "logical_run_ids": _strings(proposal.get("logical_run_ids", [])),
        "span_refs": _strings(proposal.get("span_refs", [])),
        "char_ranges": deepcopy(proposal.get("char_ranges") or []),
    }


def _strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return _dedupe_strings(values)


def _dedupe_strings(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


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
