from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso, sha256_json


def build_agent_decisions(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_type": "template_agent_decisions",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "decisions": decisions,
        "accepted_proposal_ids": [
            item.get("proposal_id")
            for item in decisions
            if item.get("decision") == "accepted"
        ],
        "rejected_proposal_ids": [
            item.get("proposal_id")
            for item in decisions
            if item.get("decision") == "rejected"
        ],
    }


def build_agent_pass_plan(pass_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": "template_agent_pass_plan",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        **pass_plan,
    }


def build_agent_t2_overlay(operations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_type": "agent_t2_overlay",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "operations": operations,
        "advisory_only": False,
    }


def build_agent_t3_overlay(operations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_type": "agent_t3_overlay",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "operations": operations,
        "advisory_only": False,
    }


def build_agent_t4_hints(hints: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = {
        "page_policy_hints": [],
        "section_profile_hints": [],
        "page_numbering_hints": [],
    }
    for hint in hints:
        collection = str(hint.get("collection") or "")
        if collection in grouped:
            grouped[collection].append(
                {key: value for key, value in hint.items() if key != "collection"}
            )
    return {
        "artifact_type": "agent_t4_hints",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "advisory_only": True,
        **grouped,
    }


def build_agent_attribution(
    *,
    transcript: dict[str, Any] | None,
    decisions: dict[str, Any],
    round0_unit_map: dict[str, Any],
    post_agent_unit_map: dict[str, Any],
    round0_element_spec: dict[str, Any],
    post_agent_element_spec: dict[str, Any],
    t2_overlay: dict[str, Any],
    t3_overlay: dict[str, Any],
    t4_hints: dict[str, Any],
    submission_comparison: dict[str, Any] | None = None,
    manual_review_items: dict[str, Any] | None = None,
    observation_bridge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "agent_attribution",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "rounds": list((transcript or {}).get("rounds", [])),
        "round0_hashes": {
            "unit_map": sha256_json(round0_unit_map),
            "element_spec": sha256_json(round0_element_spec),
        },
        "post_agent_hashes": {
            "unit_map": sha256_json(post_agent_unit_map),
            "element_spec": sha256_json(post_agent_element_spec),
        },
        "field_diffs": [
            *_diff_json(round0_unit_map, post_agent_unit_map, "$.unit_map"),
            *_diff_json(round0_element_spec, post_agent_element_spec, "$.element_spec"),
        ],
        "applied_proposal_ids": decisions.get("accepted_proposal_ids", []),
        "rejected_proposal_ids": decisions.get("rejected_proposal_ids", []),
        "overlays": {
            "t2": t2_overlay.get("operations", []),
            "t3": t3_overlay.get("operations", []),
        },
        "t4_hint_counts": {
            "page_policy_hints": len(t4_hints.get("page_policy_hints", [])),
            "section_profile_hints": len(t4_hints.get("section_profile_hints", [])),
            "page_numbering_hints": len(t4_hints.get("page_numbering_hints", [])),
        },
        "comparison_summary": (submission_comparison or {}).get("summary", {}),
        "manual_review": {
            "required": bool((manual_review_items or {}).get("blocking_item_ids")),
            "blocking_item_ids": (manual_review_items or {}).get("blocking_item_ids", []),
            "non_blocking_item_ids": (manual_review_items or {}).get(
                "non_blocking_item_ids", []
            ),
        },
        "observation_bridge": {
            "present": observation_bridge is not None,
            "summary": (observation_bridge or {}).get("summary", {}),
            "observation_bundle_hash": (observation_bridge or {}).get(
                "observation_bundle_hash"
            ),
        },
    }


def _diff_json(before: Any, after: Any, path: str, *, limit: int = 200) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    _diff_json_inner(before, after, path, diffs, limit)
    return diffs


def _diff_json_inner(
    before: Any,
    after: Any,
    path: str,
    diffs: list[dict[str, Any]],
    limit: int,
) -> None:
    if len(diffs) >= limit:
        return
    if type(before) is not type(after):
        diffs.append({"path": path, "before": before, "after": after})
        return
    if isinstance(before, dict):
        keys = sorted(set(before) | set(after))
        for key in keys:
            _diff_json_inner(
                before.get(key),
                after.get(key),
                f"{path}.{key}",
                diffs,
                limit,
            )
            if len(diffs) >= limit:
                return
        return
    if isinstance(before, list):
        keyed = _keyed_list_pair(before, after)
        if keyed is not None:
            before_by_key, after_by_key = keyed
            for item_key in sorted(set(before_by_key) - set(after_by_key)):
                diffs.append(
                    {
                        "path": f"{path}[{item_key}]",
                        "before": before_by_key[item_key],
                        "after": None,
                        "change": "removed",
                    }
                )
                if len(diffs) >= limit:
                    return
            for item_key in sorted(set(after_by_key) - set(before_by_key)):
                diffs.append(
                    {
                        "path": f"{path}[{item_key}]",
                        "before": None,
                        "after": after_by_key[item_key],
                        "change": "added",
                    }
                )
                if len(diffs) >= limit:
                    return
            for item_key in sorted(set(before_by_key) & set(after_by_key)):
                _diff_json_inner(
                    before_by_key[item_key],
                    after_by_key[item_key],
                    f"{path}[{item_key}]",
                    diffs,
                    limit,
                )
                if len(diffs) >= limit:
                    return
            return
        if len(before) != len(after):
            diffs.append(
                {
                    "path": f"{path}.length",
                    "before": len(before),
                    "after": len(after),
                }
            )
            if len(diffs) >= limit:
                return
        for index, (before_item, after_item) in enumerate(zip(before, after)):
            _diff_json_inner(before_item, after_item, f"{path}[{index}]", diffs, limit)
            if len(diffs) >= limit:
                return
        return
    if before != after:
        diffs.append({"path": path, "before": before, "after": after})


def _keyed_list_pair(
    before: list[Any],
    after: list[Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]] | None:
    if not before and not after:
        return None
    if not all(isinstance(item, dict) for item in [*before, *after]):
        return None
    before_by_key = _keyed_items(before)
    after_by_key = _keyed_items(after)
    if before_by_key is None or after_by_key is None:
        return None
    return before_by_key, after_by_key


def _keyed_items(items: list[Any]) -> dict[str, dict[str, Any]] | None:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            return None
        key = _stable_item_key(item)
        if key is None or key in result:
            return None
        result[key] = item
    return result


def _stable_item_key(item: dict[str, Any]) -> str | None:
    for field in ("unit_id", "stable_id", "target_candidate_id", "proposal_id"):
        value = item.get(field)
        if value not in (None, ""):
            return f"{field}={value}"
    element_id = item.get("element_id")
    if element_id not in (None, ""):
        unit_id = item.get("unit_id")
        if unit_id not in (None, ""):
            return f"element_id={unit_id}.{element_id}"
        return f"element_id={element_id}"
    return None
