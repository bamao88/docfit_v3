from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso, sha256_json

from .overlay import _proposal_source_seq_refs


def build_agent_unit_windows(
    *,
    structure_candidates: dict[str, Any],
    packet: dict[str, Any],
) -> dict[str, Any]:
    page_by_seq = _page_by_source_seq(packet)
    target_by_seq = _render_target_by_source_seq(packet)
    units = [
        _window_for_unit(
            unit,
            previous_unit_id=_unit_id(structure_candidates.get("units", []), index - 1),
            next_unit_id=_unit_id(structure_candidates.get("units", []), index + 1),
            page_by_seq=page_by_seq,
            target_by_seq=target_by_seq,
        )
        for index, unit in enumerate(structure_candidates.get("units", []))
        if isinstance(unit, dict)
    ]
    return {
        "artifact_type": "template_agent_unit_windows",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "post_t2_structure_hash": sha256_json(structure_candidates),
        "windows": units,
    }


def t3_window_error(
    *,
    proposal: dict[str, Any],
    window: dict[str, Any] | None,
) -> str | None:
    if window is None:
        return None
    window_refs = set(_ints(window.get("source_seq_refs", [])))
    proposal_refs = set(_proposal_source_seq_refs(proposal))
    if proposal_refs and not proposal_refs.issubset(window_refs):
        return (
            "T3 proposal source_seq_refs outside unit window "
            f"{window.get('window_id')}: {sorted(proposal_refs - window_refs)}"
        )
    explicit = str(proposal.get("target_candidate_id") or "").strip()
    if explicit:
        targets = {
            str(target.get("target_candidate_id") or "")
            for target in window.get("candidate_targets", [])
            if isinstance(target, dict)
        }
        if explicit not in targets:
            return (
                "T3 proposal target_candidate_id outside unit window "
                f"{window.get('window_id')}: {explicit}"
            )
    return None


def window_for_step(
    unit_windows: dict[str, Any] | None,
    step: dict[str, Any],
) -> dict[str, Any] | None:
    if unit_windows is None:
        return None
    unit_id = str(step.get("unit_id") or "")
    window_id = str(step.get("window_id") or "")
    for window in unit_windows.get("windows", []):
        if not isinstance(window, dict):
            continue
        if unit_id and window.get("unit_id") == unit_id:
            return window
        if window_id and window.get("window_id") == window_id:
            return window
    return None


def _window_for_unit(
    unit: dict[str, Any],
    *,
    previous_unit_id: str | None,
    next_unit_id: str | None,
    page_by_seq: dict[int, int],
    target_by_seq: dict[int, str],
) -> dict[str, Any]:
    unit_id = str(unit.get("unit_id") or "")
    source_seq_refs = _ints(unit.get("source_seq_refs", []))
    page_nos = sorted(
        {
            page_by_seq[source_seq]
            for source_seq in source_seq_refs
            if source_seq in page_by_seq
        }
    )
    return {
        "window_id": f"unit:{unit_id}",
        "unit_id": unit_id,
        "source_seq_refs": source_seq_refs,
        "page_nos": page_nos,
        "candidate_targets": [
            _candidate_target(unit, element, target_by_seq=target_by_seq)
            for element in unit.get("elements", [])
            if isinstance(element, dict)
        ],
        "neighbor_context": {
            "previous_unit_id": previous_unit_id,
            "next_unit_id": next_unit_id,
        },
    }


def _candidate_target(
    unit: dict[str, Any],
    element: dict[str, Any],
    *,
    target_by_seq: dict[int, str],
) -> dict[str, Any]:
    unit_id = str(unit.get("unit_id") or "")
    element_id = str(element.get("element_id") or "")
    source_seq_refs = _ints(element.get("source_seq_refs", []))
    return {
        "target_candidate_id": f"{unit_id}.{element_id}",
        "source_seq_refs": source_seq_refs,
        "render_target_refs": [
            target_by_seq[source_seq]
            for source_seq in source_seq_refs
            if source_seq in target_by_seq
        ],
        "current_candidate_policy": element.get("candidate_policy"),
        "name": element.get("name"),
    }


def _page_by_source_seq(packet: dict[str, Any]) -> dict[int, int]:
    result: dict[int, int] = {}
    for item in packet.get("page_text_index", []):
        source_seq = _int_or_none(item.get("source_seq"))
        page_no = _int_or_none(item.get("page_no"))
        if source_seq is not None and page_no is not None:
            result[source_seq] = page_no
    return result


def _render_target_by_source_seq(packet: dict[str, Any]) -> dict[int, str]:
    result: dict[int, str] = {}
    for item in packet.get("page_text_index", []):
        source_seq = _int_or_none(item.get("source_seq"))
        target = str(item.get("render_target_id") or "")
        if source_seq is not None and target:
            result[source_seq] = target
    return result


def _unit_id(units: list[Any], index: int) -> str | None:
    if index < 0 or index >= len(units) or not isinstance(units[index], dict):
        return None
    return str(units[index].get("unit_id") or "")


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
