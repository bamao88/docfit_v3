from __future__ import annotations

from copy import deepcopy
from typing import Any

from docfit.core.io import now_iso, sha256_json

from .schema import empty_layered_submission


EXECUTABLE_CONFIDENCE = {"medium", "high"}
T3_EXECUTABLE_CONFIDENCE = {"low", "medium", "high"}
POLICY_TO_EXECUTABLE = {
    "fixed": "fixed",
    "template_default": "fixed",
    "fill": "fill",
    "manual_only": "manual_only",
    "generated": "generated",
    "instruction_remove": "remove_instruction",
}
COLLECTION_BY_KIND = {
    "t2": {
        "unit_candidate": "unit_candidates",
        "block_candidate": "block_candidates",
        "boundary_adjustment": "boundary_adjustments",
    },
    "t3": {
        "element_policy_candidate": "element_policy_candidates",
    },
    "t4": {
        "page_policy_hint": "page_policy_hints",
        "section_profile_hint": "section_profile_hints",
        "page_numbering_hint": "page_numbering_hints",
    },
}


def build_observation_bridge(
    *,
    observation_bundle: dict[str, Any],
    packet: dict[str, Any],
    structure_candidates: dict[str, Any],
) -> dict[str, Any]:
    """Convert Module 1 observation artifacts into existing agent proposals.

    T2/T4 stay conservative on confidence because they can move large document
    regions or layout hints. T3 emits evidence-bound policy proposals even when
    the AI confidence is low; deterministic target binding, comparison, and the
    reconciler remain the executable gates before anything reaches merged
    outputs.
    """

    packet_hash = packet.get("source_render_hash")
    bundle_hash = observation_bundle.get("source_render_hash")
    proposals = {"t2": [], "t3": [], "t4": []}
    manual_items: list[dict[str, Any]] = []
    proposal_map: list[dict[str, Any]] = []

    if bundle_hash != packet_hash:
        manual_items.append(
            _manual_item(
                source="observation_bridge",
                layer=None,
                reason_code="OBSERVATION-HASH-MISMATCH",
                summary="observation bundle source_render_hash does not match current render packet",
                affected_refs={},
                agent_summary={
                    "observation_source_render_hash": bundle_hash,
                    "packet_source_render_hash": packet_hash,
                },
            )
        )
    else:
        _bridge_t2(
            observation_bundle.get("ai_unit_observation") or {},
            structure_candidates=structure_candidates,
            proposals=proposals,
            manual_items=manual_items,
            proposal_map=proposal_map,
        )
        _bridge_t3(
            observation_bundle.get("ai_element_observation") or {},
            proposals=proposals,
            manual_items=manual_items,
            proposal_map=proposal_map,
        )
        _bridge_t4(
            observation_bundle.get("ai_layout_observation") or {},
            packet=packet,
            proposals=proposals,
            manual_items=manual_items,
            proposal_map=proposal_map,
        )

    submissions = _submissions_from_proposals(
        proposals,
        source_render_hash=str(packet_hash or ""),
        model=str(observation_bundle.get("model") or "ai_observation"),
    )
    transcript = _transcript_from_submissions(submissions, observation_bundle=observation_bundle)
    summary = {
        "t2_proposals": len(proposals["t2"]),
        "t3_proposals": len(proposals["t3"]),
        "t4_proposals": len(proposals["t4"]),
        "total_proposals": sum(len(values) for values in proposals.values()),
        "manual_review_required": len(manual_items),
    }
    return {
        "artifact_type": "template_agent_observation_bridge",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "source_render_hash": packet_hash,
        "observation_bundle_hash": sha256_json(observation_bundle),
        "observation_model": observation_bundle.get("model"),
        "summary": summary,
        "proposal_map": proposal_map,
        "manual_review_items": manual_items,
        "transcript": transcript,
    }


def observation_bridge_transcript(bridge: dict[str, Any]) -> dict[str, Any]:
    transcript = bridge.get("transcript")
    return transcript if isinstance(transcript, dict) else _transcript_from_submissions([], observation_bundle={})


def _bridge_t2(
    observation: dict[str, Any],
    *,
    structure_candidates: dict[str, Any],
    proposals: dict[str, list[dict[str, Any]]],
    manual_items: list[dict[str, Any]],
    proposal_map: list[dict[str, Any]],
) -> None:
    existing_by_unit = {
        str(unit.get("unit_id") or ""): unit
        for unit in structure_candidates.get("units", []) or []
        if isinstance(unit, dict)
    }
    for index, item in enumerate(_dict_items(observation.get("items")), start=1):
        item_id = _item_id(item, fallback=f"t2_{index:03d}", key="unit_id")
        unit_id = str(item.get("unit_id") or "")
        refs = _ints(item.get("source_seq_refs"))
        if unit_id == "unknown_unit" or not unit_id:
            _reject_observation_item(
                item,
                manual_items,
                layer="t2",
                reason_code="OBSERVATION-UNKNOWN",
                summary="AI unit observation did not choose an executable unit_id",
            )
            continue
        if _confidence(item) not in EXECUTABLE_CONFIDENCE:
            _reject_observation_item(
                item,
                manual_items,
                layer="t2",
                reason_code="OBSERVATION-LOW-CONFIDENCE",
                summary="AI unit observation confidence is too low for automatic bridge",
            )
            continue
        if not refs:
            _reject_observation_item(
                item,
                manual_items,
                layer="t2",
                reason_code="OBSERVATION-EVIDENCE-MISSING",
                summary="AI unit observation has no source_seq_refs",
            )
            continue
        existing = existing_by_unit.get(unit_id)
        if existing is not None and _ints(existing.get("source_seq_refs")) == refs:
            proposal_map.append(_map_item(item_id, "t2", None, "noop", "deterministic unit already matches observation"))
            continue
        proposal_id = f"obs_t2_{_slug(unit_id)}_{index:03d}"
        proposal = {
            "proposal_id": proposal_id,
            "kind": "unit_candidate" if existing is None else "boundary_adjustment",
            "operation": "add_unit" if existing is None else "adjust_unit_range",
            "unit_id": unit_id,
            "target_unit_id": unit_id if existing is not None else None,
            "name": item.get("name"),
            "display_name": item.get("name"),
            "source_seq_refs": refs,
            "rationale": item.get("ai_rationale"),
            "evidence": item.get("evidence_refs", []),
            "origin": "ai_observation",
            "observation_item_id": item_id,
        }
        proposals["t2"].append(proposal)
        proposal_map.append(_map_item(item_id, "t2", proposal_id, "proposal", "converted to T2 proposal"))
    _demotions_to_manual(observation, manual_items, layer="t2")


def _bridge_t3(
    observation: dict[str, Any],
    *,
    proposals: dict[str, list[dict[str, Any]]],
    manual_items: list[dict[str, Any]],
    proposal_map: list[dict[str, Any]],
) -> None:
    for index, item in enumerate(_dict_items(observation.get("items")), start=1):
        item_id = _item_id(item, fallback=f"t3_{index:03d}", key="element_id")
        refs = _ints(item.get("source_seq_refs"))
        raw_policy = str(item.get("policy") or "")
        executable_policy = POLICY_TO_EXECUTABLE.get(raw_policy)
        if executable_policy is None:
            _reject_observation_item(
                item,
                manual_items,
                layer="t3",
                reason_code="OBSERVATION-POLICY-NOT-EXECUTABLE",
                summary=f"AI element policy is not executable by current overlay: {raw_policy}",
            )
            continue
        confidence = _confidence(item)
        if confidence not in T3_EXECUTABLE_CONFIDENCE:
            _reject_observation_item(
                item,
                manual_items,
                layer="t3",
                reason_code="OBSERVATION-CONFIDENCE-INVALID",
                summary="AI element observation confidence is not recognized",
            )
            continue
        if not refs:
            _reject_observation_item(
                item,
                manual_items,
                layer="t3",
                reason_code="OBSERVATION-EVIDENCE-MISSING",
                summary="AI element observation has no source_seq_refs",
            )
            continue
        unit_id = str(item.get("unit_id") or "")
        proposal_id = f"obs_t3_{_slug(unit_id or 'unit')}_{index:03d}"
        proposal = {
            "proposal_id": proposal_id,
            "kind": "element_policy_candidate",
            "policy": executable_policy,
            "unit_id": unit_id,
            "source_seq_refs": refs,
            "target_candidate_id": _target_candidate_id(unit_id, str(item.get("element_id") or "")),
            "rationale": item.get("ai_rationale"),
            "evidence": item.get("evidence_refs", []),
            "origin": "ai_observation",
            "observation_item_id": item_id,
            "observation_confidence": confidence,
            "fill_source": item.get("fill_source"),
            "generated": item.get("generated"),
            "manual_semantics": item.get("manual_semantics"),
        }
        proposals["t3"].append(proposal)
        proposal_map.append(_map_item(item_id, "t3", proposal_id, "proposal", "converted to T3 policy proposal"))
    _demotions_to_manual(observation, manual_items, layer="t3")


def _bridge_t4(
    observation: dict[str, Any],
    *,
    packet: dict[str, Any],
    proposals: dict[str, list[dict[str, Any]]],
    manual_items: list[dict[str, Any]],
    proposal_map: list[dict[str, Any]],
) -> None:
    if observation.get("abstain"):
        manual_items.append(
            _manual_item(
                source="observation_bridge",
                layer="t4",
                reason_code="OBSERVATION-T4-ABSTAIN",
                summary="AI layout observation abstained; T4 requires manual or later real-render review",
                affected_refs={},
                agent_summary={"abstain": True},
                required_action="Provide real render evidence or keep deterministic T4 output.",
            )
        )
    for index, item in enumerate(_dict_items(observation.get("items")), start=1):
        item_id = _item_id(item, fallback=f"t4_{index:03d}", key="section_profile_id")
        if _confidence(item.get("boundary") or item) not in EXECUTABLE_CONFIDENCE:
            _reject_observation_item(
                item,
                manual_items,
                layer="t4",
                reason_code="OBSERVATION-LOW-CONFIDENCE",
                summary="AI layout observation confidence is too low for automatic hint bridge",
            )
            continue
        refs = _ints(item.get("source_seq_refs"))
        page_nos, render_refs = _layout_refs(item)
        if not page_nos:
            page_nos = _pages_for_source_seq_refs(packet, refs)
        proposal_id = f"obs_t4_{index:03d}"
        proposal = {
            "proposal_id": proposal_id,
            "kind": "section_profile_hint",
            "source_seq_refs": refs,
            "page_nos": page_nos,
            "render_target_refs": render_refs,
            "hint": "ai_observation_section_profile",
            "payload": item,
            "rationale": item.get("ai_rationale"),
            "evidence": item.get("evidence_refs", []),
            "origin": "ai_observation",
            "observation_item_id": item_id,
        }
        proposals["t4"].append(proposal)
        proposal_map.append(_map_item(item_id, "t4", proposal_id, "proposal", "converted to T4 advisory hint"))
    _demotions_to_manual(observation, manual_items, layer="t4")


def _submissions_from_proposals(
    proposals: dict[str, list[dict[str, Any]]],
    *,
    source_render_hash: str,
    model: str,
) -> list[dict[str, Any]]:
    specs = [
        ("round_obs_t2", "t2_unit_scan", "observation:t2", "t2"),
        ("round_obs_t3", "t3_unit_elements", "observation:t3", "t3"),
        ("round_obs_t4", "t4_global_layout", "observation:t4", "t4"),
    ]
    submissions: list[dict[str, Any]] = []
    for round_id, pass_kind, window_id, layer in specs:
        submission = empty_layered_submission(
            source_render_hash=source_render_hash,
            round_id=round_id,
            model=model,
        )
        submission["pass_kind"] = pass_kind
        submission["pass_id"] = window_id
        submission["window_id"] = window_id
        submission["allowed_layers"] = [layer]
        for proposal in proposals[layer]:
            collection = COLLECTION_BY_KIND.get(layer, {}).get(
                str(proposal.get("kind") or "")
            )
            if collection is None:
                continue
            submission["layers"][layer][collection].append(deepcopy(proposal))
        submissions.append(submission)
    return submissions


def _transcript_from_submissions(
    submissions: list[dict[str, Any]],
    *,
    observation_bundle: dict[str, Any],
) -> dict[str, Any]:
    rounds = []
    for submission in submissions:
        rounds.append(
            {
                "round_id": submission["round_id"],
                "provider": "observation_bridge",
                "pass_kind": submission.get("pass_kind"),
                "pass_id": submission.get("pass_id"),
                "window_id": submission.get("window_id"),
                "allowed_layers": submission.get("allowed_layers"),
                "submission": submission,
            }
        )
    return {
        "artifact_type": "template_agent_transcript",
        "artifact_version": "1.0",
        "provider": "observation_bridge",
        "source_observation_bundle_hash": sha256_json(observation_bundle),
        "rounds": rounds,
    }


def _demotions_to_manual(
    observation: dict[str, Any],
    manual_items: list[dict[str, Any]],
    *,
    layer: str,
) -> None:
    for demotion in observation.get("quality_report", {}).get("demotions", []) or []:
        if not isinstance(demotion, dict):
            continue
        manual_items.append(
            _manual_item(
                source="observation_demotion",
                layer=layer,
                reason_code=str(demotion.get("check_id") or "OBSERVATION-DEMOTION"),
                summary=str(demotion.get("reason") or "AI observation item was demoted by materialization"),
                affected_refs={},
                agent_summary={"demotion": demotion},
                required_action="Review the demoted observation item before turning it into an executable proposal.",
            )
        )


def _reject_observation_item(
    item: dict[str, Any],
    manual_items: list[dict[str, Any]],
    *,
    layer: str,
    reason_code: str,
    summary: str,
) -> None:
    manual_items.append(
        _manual_item(
            source="observation_bridge",
            layer=layer,
            reason_code=reason_code,
            summary=summary,
            affected_refs={"source_seq_refs": _ints(item.get("source_seq_refs"))},
            agent_summary={"observation_item": item},
        )
    )


def _manual_item(
    *,
    source: str,
    layer: str | None,
    reason_code: str,
    summary: str,
    affected_refs: dict[str, Any],
    agent_summary: dict[str, Any],
    required_action: str | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "layer": layer,
        "blocking_level": "blocking",
        "reason_code": reason_code,
        "summary": summary,
        "affected_refs": affected_refs,
        "agent_submission_summary": agent_summary,
        "deterministic_summary": {},
        "suggested_candidate_policies": [],
        "required_human_action": required_action
        or "Review the AI observation before allowing it into code generation.",
    }


def _map_item(
    item_id: str,
    layer: str,
    proposal_id: str | None,
    status: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "observation_item_id": item_id,
        "layer": layer,
        "proposal_id": proposal_id,
        "status": status,
        "reason": reason,
    }


def _target_candidate_id(unit_id: str, element_id: str) -> str | None:
    if not unit_id or not element_id:
        return None
    if "." in element_id:
        return element_id
    return f"{unit_id}.{element_id}"


def _layout_refs(item: dict[str, Any]) -> tuple[list[int], list[str]]:
    page_nos: list[int] = []
    render_refs: list[str] = []
    for ref in item.get("evidence_refs", []) or []:
        if not isinstance(ref, dict):
            continue
        page_no = _int_or_none(ref.get("page_no"))
        if page_no is not None:
            page_nos.append(page_no)
        render_target = str(ref.get("render_target_id") or "")
        if render_target:
            render_refs.append(render_target)
    return sorted(set(page_nos)), sorted(set(render_refs))


def _pages_for_source_seq_refs(packet: dict[str, Any], source_seq_refs: list[int]) -> list[int]:
    wanted = set(source_seq_refs)
    pages = []
    for item in packet.get("page_text_index", []) or []:
        source_seq = _int_or_none(item.get("source_seq"))
        page_no = _int_or_none(item.get("page_no"))
        if source_seq in wanted and page_no is not None:
            pages.append(page_no)
    return sorted(set(pages))


def _confidence(item: dict[str, Any]) -> str:
    return str(item.get("confidence") or "").strip().lower()


def _item_id(item: dict[str, Any], *, fallback: str, key: str) -> str:
    value = item.get(key)
    if value not in (None, ""):
        return str(value)
    return fallback


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _ints(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    result: list[int] = []
    for value in values:
        parsed = _int_or_none(value)
        if parsed is not None:
            result.append(parsed)
    return sorted(dict.fromkeys(result))


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value)
