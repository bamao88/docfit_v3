"""T3 单元窗口：按【AI 自己的 T2 单元】切窗口（端到端独立）。

Module 1 的关键独立性约束：T3 元素观察的窗口来源是 AI 在 T2 自己认出的单元
（``ai_unit_observation.items``），**不是**代码的 ``structure_candidates``。这样
AI 这个证人从头到尾不靠代码结论；T2 错误传导到 T3 的级联记入 quality_report。
"""

from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso, sha256_json


def build_observation_windows(
    *,
    ai_unit_observation: dict[str, Any],
    packet: dict[str, Any],
) -> dict[str, Any]:
    page_by_seq = _page_by_source_seq(packet)
    target_by_seq = _render_target_by_source_seq(packet)
    items = [item for item in ai_unit_observation.get("items", []) if isinstance(item, dict)]
    windows = [
        _window_for_item(
            item,
            previous_unit_id=_unit_id_at(items, index - 1),
            next_unit_id=_unit_id_at(items, index + 1),
            page_by_seq=page_by_seq,
            target_by_seq=target_by_seq,
        )
        for index, item in enumerate(items)
    ]
    return {
        "artifact_type": "ai_observation_unit_windows",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "window_source": str(
            ai_unit_observation.get("artifact_type") or "ai_unit_observation"
        ),
        "post_t2_observation_hash": sha256_json(ai_unit_observation.get("items", [])),
        "windows": windows,
    }


def window_for_unit(
    unit_windows: dict[str, Any] | None,
    unit_id: str,
) -> dict[str, Any] | None:
    if unit_windows is None:
        return None
    for window in unit_windows.get("windows", []):
        if isinstance(window, dict) and window.get("unit_id") == unit_id:
            return window
    return None


def _window_for_item(
    item: dict[str, Any],
    *,
    previous_unit_id: str | None,
    next_unit_id: str | None,
    page_by_seq: dict[int, int],
    target_by_seq: dict[int, str],
) -> dict[str, Any]:
    unit_id = str(item.get("unit_id") or "")
    source_seq_refs = _ints(item.get("source_seq_refs", []))
    source_ref_refs = _source_ref_refs(item)
    page_nos = sorted(
        {page_by_seq[seq] for seq in source_seq_refs if seq in page_by_seq}
    )
    return {
        "window_id": f"unit:{unit_id}",
        "unit_id": unit_id,
        "source_seq_refs": source_seq_refs,
        "source_ref_refs": source_ref_refs,
        "source_ref_range": item.get("source_ref_range"),
        "page_nos": page_nos,
        "render_target_refs": [
            target_by_seq[seq] for seq in source_seq_refs if seq in target_by_seq
        ],
        "neighbor_context": {
            "previous_unit_id": previous_unit_id,
            "next_unit_id": next_unit_id,
        },
    }


def _page_by_source_seq(packet: dict[str, Any]) -> dict[int, int]:
    result: dict[int, int] = {}
    for item in packet.get("page_text_index", []):
        seq = _int_or_none(item.get("source_seq"))
        page_no = _int_or_none(item.get("page_no"))
        if seq is not None and page_no is not None:
            result[seq] = page_no
    return result


def _render_target_by_source_seq(packet: dict[str, Any]) -> dict[int, str]:
    result: dict[int, str] = {}
    for item in packet.get("page_text_index", []):
        seq = _int_or_none(item.get("source_seq"))
        target = str(item.get("render_target_id") or "")
        if seq is not None and target:
            result[seq] = target
    return result


def _unit_id_at(items: list[dict[str, Any]], index: int) -> str | None:
    if index < 0 or index >= len(items):
        return None
    return str(items[index].get("unit_id") or "") or None


def _ints(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    return [v for v in (_int_or_none(x) for x in values) if v is not None]


def _source_ref_refs(item: dict[str, Any]) -> list[str]:
    explicit = [
        str(value)
        for value in item.get("source_ref_refs", []) or []
        if str(value or "").strip()
    ]
    if explicit:
        return list(dict.fromkeys(explicit))
    source_ref_range = item.get("source_ref_range")
    if not isinstance(source_ref_range, dict):
        return []
    start = str(source_ref_range.get("start") or "").strip()
    end = str(source_ref_range.get("end") or "").strip()
    return list(dict.fromkeys(value for value in (start, end) if value))


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
