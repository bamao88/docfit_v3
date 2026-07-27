"""Materialize the sole T3 AI decision route onto the structural shell."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from docfit.core.io import now_iso, sha256_json


_EXECUTION_POLICY = {
    "fixed": "fixed",
    "template_default": "fixed",
    "fill": "fill",
    "generated": "generated",
    "instruction_remove": "remove_instruction",
    "remove_instruction": "remove_instruction",
    "unknown": "fixed",
}


def build_t3_source_structure(
    source_tree: dict[str, Any],
    unit_map: dict[str, Any],
) -> dict[str, Any]:
    """Build the neutral T3 source shell from the published T2 page groups."""

    layers = source_tree.get("layers", {}) or {}
    data = source_tree.get("data", {}) or {}
    indexes = source_tree.get("indexes", {}) or {}
    source_context = {
        "source_template_tree_ref": "source_template_tree.json",
        "body_order": deepcopy(indexes.get("body_order", [])),
        "body_flow": deepcopy(layers.get("body_flow", [])),
        "by_source_ref": deepcopy(indexes.get("by_source_ref", {})),
        "by_source_seq": deepcopy(indexes.get("by_source_seq", {})),
        "style_inventory": _style_inventory(data.get("paragraphs", [])),
        "numbering_definitions": deepcopy(
            (layers.get("package_global", {}) or {}).get(
                "numbering_definitions",
                data.get("numbering_definitions", []),
            )
        ),
        "numbering_refs": deepcopy(data.get("numbering_refs", [])),
        "section_rules": deepcopy(layers.get("section_rules", [])),
        "header_footer": deepcopy(layers.get("header_footer", [])),
        "unknown_objects": deepcopy(layers.get("unknown_objects", [])),
        "warnings": deepcopy(source_tree.get("warnings", [])),
        "paragraphs": deepcopy(data.get("paragraphs", [])),
        "runs_by_raw_run_id": deepcopy(indexes.get("runs_by_raw_run_id", {})),
        "runs_by_source_ref": deepcopy(indexes.get("runs_by_source_ref", {})),
    }
    entries_by_seq = {
        source_seq: entry
        for entry in source_context["body_flow"]
        if isinstance(entry, dict)
        and (source_seq := _as_int(entry.get("source_seq"))) is not None
    }
    units: list[dict[str, Any]] = []
    for unit in unit_map.get("units", []) or []:
        if not isinstance(unit, dict):
            continue
        refs = _unique_ints(unit.get("source_seq_refs", []))
        entries = [entries_by_seq[ref] for ref in refs if ref in entries_by_seq]
        units.append(
            {
                **deepcopy(unit),
                "name": unit.get("unit_name"),
                "status": "required",
                "source_range": {
                    "start": (unit.get("source_refs") or [None])[0],
                    "end": (unit.get("source_refs") or [None])[-1],
                }
                if unit.get("source_refs")
                else {},
                "elements": [
                    _neutral_element(entry, order=index)
                    for index, entry in enumerate(entries, start=1)
                ],
            }
        )
    return {
        "artifact_type": "t3_source_structure",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "input_hashes": {
            "source_template_tree": sha256_json(source_tree),
            "unit_map": sha256_json(unit_map),
            **(
                {"l1": source_tree.get("input_hashes", {}).get("l1")}
                if source_tree.get("input_hashes", {}).get("l1")
                else {}
            ),
        },
        "source_method": "ai_page_groups_with_deterministic_l1_binding",
        "source_context": source_context,
        "units": units,
        "unknowns": [],
        "open_questions": [],
    }


def materialize_ai_t3_structure(
    downstream_structure: dict[str, Any],
    observation: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replace every source-backed T3 policy with AI authority or safe Keep.

    Accepted AI decisions own their exact raw runs. Invalid, fallback,
    contested, missing, or conflicting claims resolve to ``fixed`` (core
    action Keep), never to a deterministic policy that happened to be present
    on the structural shell.
    """

    before_hash = sha256_json(downstream_structure)
    patched = deepcopy(downstream_structure)
    claims, conflicting_raw_run_ids = _claims_by_raw_run(observation)
    observation_items = [
        item
        for item in observation.get("items", []) or []
        if isinstance(item, dict)
    ]
    object_items = [
        item
        for item in observation.get("object_items", []) or []
        if isinstance(item, dict)
    ]
    runs_by_raw = (
        patched.get("source_context", {}).get("runs_by_raw_run_id", {}) or {}
    )
    matched_raw_run_ids: set[str] = set()
    materialized_count = 0
    source_raw_run_ids: set[str] = set()

    for unit in patched.get("units", []) or []:
        if not isinstance(unit, dict):
            continue
        replacements: list[dict[str, Any]] = []
        for element in unit.get("elements", []) or []:
            if not isinstance(element, dict):
                continue
            raw_run_ids = _strings(element.get("raw_run_ids"))
            source_raw_run_ids.update(raw_run_ids)
            if not raw_run_ids:
                replacement = deepcopy(element)
                _apply_claim(replacement, _safe_keep_claim(reason="element has no raw-run identity"))
                replacements.append(replacement)
                materialized_count += 1
                continue
            groups = _contiguous_claim_groups(raw_run_ids, claims=claims)
            for group_index, (group_raw_ids, claim) in enumerate(groups, start=1):
                replacement = deepcopy(element)
                original_id = str(element.get("element_id") or "element")
                replacement["element_id"] = (
                    original_id
                    if group_index == 1
                    else f"{original_id}.ai_{group_index:03d}"
                )
                _bind_raw_runs(
                    replacement,
                    raw_run_ids=group_raw_ids,
                    runs_by_raw=runs_by_raw,
                )
                _apply_claim(replacement, claim)
                replacements.append(replacement)
                matched_raw_run_ids.update(
                    raw_run_id for raw_run_id in group_raw_ids if raw_run_id in claims
                )
                materialized_count += 1
        for order, replacement in enumerate(replacements, start=1):
            replacement["order"] = order
        unit["elements"] = replacements

    missing_claim_raw_run_ids = sorted(set(claims) - matched_raw_run_ids)
    unclaimed_source_raw_run_ids = sorted(source_raw_run_ids - set(claims))
    safe_keep_claim_raw_run_ids = sorted(
        raw_run_id
        for raw_run_id, claim in claims.items()
        if claim.get("safe_fallback")
    )
    availability = "AVAILABLE" if observation_items else "NOT_AVAILABLE"
    operation = {
        "operation": "materialize_ai_atomic_policies",
        "authority": "ai",
        "availability": availability,
        "materialization_status": (
            "MATERIALIZED" if availability == "AVAILABLE" else "SAFE_KEEP_ONLY"
        ),
        "observation_item_count": len(observation_items),
        "accepted_observation_item_count": sum(
            1 for item in observation_items if _is_accepted_item(item)
        ),
        "fallback_observation_item_count": sum(
            1 for item in observation_items if not _is_accepted_item(item)
        ),
        "object_observation_item_count": len(object_items),
        "unmaterialized_object_refs": sorted(
            {
                str(item.get("member_ref") or item.get("element_id") or "")
                for item in object_items
                if item.get("member_ref") or item.get("element_id")
            }
        ),
        "safe_failure_action": "keep",
        "source_raw_run_count": len(source_raw_run_ids),
        "claimed_raw_run_count": len(claims),
        "matched_raw_run_count": len(matched_raw_run_ids),
        "safe_keep_claim_raw_run_ids": safe_keep_claim_raw_run_ids,
        "materialized_element_count": materialized_count,
        "conflicting_raw_run_ids": conflicting_raw_run_ids,
        "missing_claim_raw_run_ids": missing_claim_raw_run_ids,
        "unclaimed_source_raw_run_ids": unclaimed_source_raw_run_ids,
        "coverage_self_check": {
            "all_source_runs_materialized": materialized_count > 0
            or not source_raw_run_ids,
            "unmatched_claim_count": len(missing_claim_raw_run_ids),
            "unclaimed_source_run_count": len(unclaimed_source_raw_run_ids),
            "conflict_count": len(conflicting_raw_run_ids),
            "safe_keep_is_only_failure_action": True,
        },
        "before_hash": before_hash,
        "after_hash": sha256_json(patched),
    }
    return patched, operation


def _neutral_element(entry: dict[str, Any], *, order: int) -> dict[str, Any]:
    source_ref = str(entry.get("source_ref") or "")
    source_seq = _as_int(entry.get("source_seq"))
    content = str(entry.get("text") or "")
    return {
        "element_id": f"e_{order:03d}",
        "name": content.strip()[:80] or f"source_{source_seq or order}",
        "order": order,
        "candidate_policy": "fixed",
        "type": "fixed_text",
        "fill": "no",
        "content": content,
        "style": entry.get("style") or "",
        "style_summary": entry.get("style") or "",
        "style_evidence": deepcopy(entry.get("style_details", {})),
        "position": source_ref,
        "role_hint": "unclassified_source_content",
        "evidence": [],
        "source_refs": [source_ref] if source_ref else [],
        "source_seq_refs": [source_seq] if source_seq is not None else [],
        "raw_run_ids": deepcopy(entry.get("raw_run_ids", [])),
        "logical_run_ids": deepcopy(entry.get("logical_run_ids", [])),
        "run_source_refs": deepcopy(entry.get("run_source_refs", [])),
        "entry_refs": [entry.get("node_id")] if entry.get("node_id") else [],
        "structure": {
            "kind": entry.get("kind"),
            "container_ref": entry.get("container_ref"),
            "source_refs": [source_ref] if source_ref else [],
        },
        "confidence": "high",
        "review_notes": [],
    }


def _style_inventory(paragraphs: Any) -> list[dict[str, Any]]:
    styles: dict[str, int] = {}
    for paragraph in paragraphs if isinstance(paragraphs, list) else []:
        if not isinstance(paragraph, dict):
            continue
        style = str(paragraph.get("style") or "").strip()
        if style:
            styles[style] = styles.get(style, 0) + 1
    return [{"name": name, "count": count} for name, count in styles.items()]


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return None


def _unique_ints(values: Any) -> list[int]:
    result: list[int] = []
    for value in values:
        parsed = _as_int(value)
        if parsed is not None and parsed not in result:
            result.append(parsed)
    return result


def _claims_by_raw_run(
    observation: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in observation.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        claim = _claim_from_item(item)
        for raw_run_id in _strings(item.get("raw_run_ids")):
            candidates[raw_run_id].append(claim)

    claims: dict[str, dict[str, Any]] = {}
    conflicts: list[str] = []
    for raw_run_id, raw_claims in candidates.items():
        signatures = {sha256_json(_execution_payload(claim)) for claim in raw_claims}
        if len(signatures) == 1:
            claims[raw_run_id] = raw_claims[0]
            continue
        conflicts.append(raw_run_id)
        claims[raw_run_id] = _safe_keep_claim(
            reason="conflicting AI claims for one raw run"
        )
    return claims, sorted(conflicts)


def _claim_from_item(item: dict[str, Any]) -> dict[str, Any]:
    accepted = _is_accepted_item(item)
    if not accepted:
        return _safe_keep_claim(
            reason=str(item.get("ai_rationale") or "AI decision was not accepted"),
            item=item,
        )
    policy = _EXECUTION_POLICY.get(str(item.get("policy") or ""), "fixed")
    return {
        "policy": policy,
        "fill_source": item.get("fill_source"),
        "fill_field": item.get("fill_field"),
        "generated": deepcopy(item.get("generated")),
        "removal_reason": item.get("removal_reason"),
        "item": item,
        "safe_fallback": False,
    }


def _is_accepted_item(item: dict[str, Any]) -> bool:
    return (
        str(item.get("decision_status") or "") == "accepted"
        and str(item.get("resolution") or "") in {"direct", "inherited"}
        and item.get("execution_eligible") is not False
    )


def _safe_keep_claim(
    *,
    reason: str,
    item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "policy": "fixed",
        "fill_source": None,
        "fill_field": None,
        "generated": None,
        "removal_reason": None,
        "item": item or {},
        "safe_fallback": True,
        "fallback_reason": reason,
    }


def _execution_payload(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(claim.get(key))
        for key in (
            "policy",
            "fill_source",
            "fill_field",
            "generated",
            "removal_reason",
            "safe_fallback",
        )
    }


def _contiguous_claim_groups(
    raw_run_ids: list[str],
    *,
    claims: dict[str, dict[str, Any]],
) -> list[tuple[list[str], dict[str, Any]]]:
    groups: list[tuple[list[str], dict[str, Any]]] = []
    for raw_run_id in raw_run_ids:
        claim = claims.get(
            raw_run_id,
            _safe_keep_claim(reason="raw run is unclaimed by AI observation"),
        )
        signature = sha256_json(_execution_payload(claim))
        if groups and sha256_json(_execution_payload(groups[-1][1])) == signature:
            groups[-1][0].append(raw_run_id)
        else:
            groups.append(([raw_run_id], claim))
    return groups


def _bind_raw_runs(
    element: dict[str, Any],
    *,
    raw_run_ids: list[str],
    runs_by_raw: dict[str, Any],
) -> None:
    element["raw_run_ids"] = raw_run_ids
    element["logical_run_ids"] = _dedupe(
        (runs_by_raw.get(raw_run_id) or {}).get("logical_run_id")
        for raw_run_id in raw_run_ids
    )
    element["run_source_refs"] = _dedupe(
        (runs_by_raw.get(raw_run_id) or {}).get("source_ref")
        for raw_run_id in raw_run_ids
    )
    element["content"] = "".join(
        str((runs_by_raw.get(raw_run_id) or {}).get("text") or "")
        for raw_run_id in raw_run_ids
    )
    element["normalized_content"] = str(element["content"]).strip()


def _apply_claim(element: dict[str, Any], claim: dict[str, Any]) -> None:
    policy = str(claim.get("policy") or "fixed")
    element["candidate_policy"] = policy
    for key in ("fill_source", "fill_field", "generated", "removal_reason"):
        value = claim.get(key)
        if value in (None, ""):
            element.pop(key, None)
        else:
            element[key] = deepcopy(value)
    item = claim.get("item") if isinstance(claim.get("item"), dict) else {}
    element.setdefault("agent_traces", []).append(
        {
            "origin": "ai_direct_materialization",
            "decision_ref": item.get("decision_ref"),
            "decision_target_ref": item.get("decision_target_ref"),
            "member_ref": item.get("member_ref"),
            "decision_status": item.get("decision_status"),
            "resolution": item.get("resolution"),
            "safe_fallback": bool(claim.get("safe_fallback")),
            "fallback_reason": claim.get("fallback_reason"),
        }
    )


def _strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if value not in (None, "")]


def _dedupe(values: Any) -> list[str]:
    return list(
        dict.fromkeys(
            str(value) for value in values if value not in (None, "")
        )
    )
