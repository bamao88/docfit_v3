"""Materialize the sole T3 AI decision route onto the structural shell."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from docfit.core.io import sha256_json


_EXECUTION_POLICY = {
    "fixed": "fixed",
    "template_default": "fixed",
    "fill": "fill",
    "generated": "generated",
    "instruction_remove": "remove_instruction",
    "remove_instruction": "remove_instruction",
    "unknown": "fixed",
}


def materialize_ai_t3_structure(
    structure_candidates: dict[str, Any],
    observation: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replace every source-backed T3 policy with AI authority or safe Keep.

    Accepted AI decisions own their exact raw runs. Invalid, fallback,
    contested, missing, or conflicting claims resolve to ``fixed`` (core
    action Keep), never to a deterministic policy that happened to be present
    on the structural shell.
    """

    before_hash = sha256_json(structure_candidates)
    patched = deepcopy(structure_candidates)
    claims, conflicting_raw_run_ids = _claims_by_raw_run(observation)
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
    operation = {
        "proposal_id": "ai_t3_authority",
        "operation": "materialize_ai_atomic_policies",
        "authority": "ai",
        "observation_available": bool(observation.get("items")),
        "safe_failure_action": "keep",
        "claimed_raw_run_count": len(claims),
        "matched_raw_run_count": len(matched_raw_run_ids),
        "materialized_element_count": materialized_count,
        "conflicting_raw_run_ids": conflicting_raw_run_ids,
        "missing_claim_raw_run_ids": missing_claim_raw_run_ids,
        "unclaimed_source_raw_run_ids": unclaimed_source_raw_run_ids,
        "before_hash": before_hash,
        "after_hash": sha256_json(patched),
    }
    return patched, operation


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
    accepted = (
        str(item.get("decision_status") or "") == "accepted"
        and str(item.get("resolution") or "") in {"direct", "inherited"}
        and item.get("execution_eligible") is not False
    )
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
