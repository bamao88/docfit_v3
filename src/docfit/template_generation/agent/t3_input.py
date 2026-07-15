"""T3 分层输入：对象整体画像 → 对象计划 → 局部判断窗口。

本模块只重组 Word/render 事实，不提前写 policy。表格保留 table/row/cell 关系，先生成
整体画像，再按完整行组切局部窗口；普通文本按连续事实块切窗。视觉证据以独立附件引用
存在，prompt 里只显示引用，responder 再把真实图片作为多模态内容发送。
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re
from typing import Any

from .evidence import assert_firewall_clean


_CELL_ID_RE = re.compile(r"^(?P<table>.+)\.r_(?P<row>\d+)\.c_(?P<column>\d+)$")


def build_t3_object_tasks(
    packet: dict[str, Any],
    *,
    unit_windows: list[dict[str, Any]],
    max_table_items: int = 24,
    max_text_items: int = 24,
    max_local_chars: int = 6000,
) -> list[dict[str, Any]]:
    """把 T2 单元窗口继续拆成对象任务；表格对象不会被扁平化。"""

    packet_rows = [row for row in packet.get("page_text_index", []) if isinstance(row, dict)]
    by_seq = {
        seq: row
        for row in packet_rows
        if (seq := _as_int(row.get("source_seq"))) is not None
    }
    tasks: list[dict[str, Any]] = []
    for unit_window in unit_windows:
        refs = [seq for seq in _ints(unit_window.get("source_seq_refs")) if seq in by_seq]
        rows = [by_seq[seq] for seq in refs]
        for object_index, segment in enumerate(_object_segments(rows), start=1):
            object_type = "table" if segment[0].get("table_id") else "text_flow"
            object_id = str(segment[0].get("table_id") or f"text_{object_index:03d}")
            task_id = f"{unit_window.get('window_id')}:{object_id}"
            overview = _object_overview(
                object_id=object_id,
                object_type=object_type,
                rows=segment,
            )
            local_windows = (
                _table_local_windows(
                    rows=segment,
                    parent_window=unit_window,
                    task_id=task_id,
                    max_items=max_table_items,
                    max_chars=max_local_chars,
                )
                if object_type == "table"
                else _text_local_windows(
                    rows=segment,
                    parent_window=unit_window,
                    task_id=task_id,
                    max_items=max_text_items,
                    max_chars=max_local_chars,
                )
            )
            tasks.append(
                {
                    "task_id": task_id,
                    "object_id": object_id,
                    "object_type": object_type,
                    "unit_id": unit_window.get("unit_id"),
                    "parent_window_id": unit_window.get("window_id"),
                    "source_seq_refs": [_as_int(row.get("source_seq")) for row in segment],
                    "object_overview": overview,
                    "visual_evidence": _visual_evidence(packet, rows=segment, limit=4),
                    "local_windows": local_windows,
                }
            )
    return tasks


def build_t3_object_plan_evidence(
    packet: dict[str, Any],
    *,
    task: dict[str, Any],
) -> dict[str, Any]:
    view = {
        "scope": "t3_object_overview",
        "source_render_hash": packet.get("source_render_hash"),
        "parent_window_id": task.get("parent_window_id"),
        "object_overview": deepcopy(task.get("object_overview") or {}),
        "visual_evidence": deepcopy(task.get("visual_evidence") or []),
    }
    assert_firewall_clean(view)
    return view


def build_t3_local_evidence(
    packet: dict[str, Any],
    *,
    task: dict[str, Any],
    local_window: dict[str, Any],
    object_plan: dict[str, Any],
) -> dict[str, Any]:
    claimable = set(_ints(local_window.get("source_seq_refs")))
    context_only = set(_ints(local_window.get("context_source_seq_refs"))) - claimable
    wanted = claimable | context_only
    rows = [
        _local_row(row, claimable=claimable)
        for row in packet.get("page_text_index", [])
        if isinstance(row, dict) and _as_int(row.get("source_seq")) in wanted
    ]
    visual_rows = [
        row
        for row in packet.get("page_text_index", [])
        if isinstance(row, dict) and _as_int(row.get("source_seq")) in claimable
    ]
    view = {
        "scope": "t3_object_local_window",
        "source_render_hash": packet.get("source_render_hash"),
        "window_id": local_window.get("window_id"),
        "parent_window_id": task.get("parent_window_id"),
        "object_overview": deepcopy(task.get("object_overview") or {}),
        "object_plan": sanitize_object_plan(object_plan),
        "claimable_source_seq_refs": sorted(claimable),
        "context_only_source_seq_refs": sorted(context_only),
        "rows": rows,
        "visual_evidence": _visual_evidence(packet, rows=visual_rows, limit=2),
    }
    assert_firewall_clean(view)
    return view


def sanitize_object_plan(plan: dict[str, Any] | None) -> dict[str, Any]:
    """对象计划是软上下文，只保留已声明字段，避免模型把结论字段带回事实层。"""

    if not isinstance(plan, dict):
        return {}
    hypothesis = plan.get("object_hypothesis") or {}
    clean_hypothesis = {
        key: hypothesis.get(key)
        for key in ("archetype", "purpose", "confidence")
        if hypothesis.get(key) is not None
    }
    return {
        "object_hypothesis": clean_hypothesis,
        "regions": _clean_list(plan.get("regions"), limit=30),
        "relationship_patterns": _clean_list(
            plan.get("relationship_patterns") or plan.get("expected_relationships"),
            limit=20,
        ),
        "quality_risks": [str(value) for value in (plan.get("quality_risks") or [])[:20]],
    }


def task_summary(task: dict[str, Any]) -> dict[str, Any]:
    """写入审计 artifact 的紧凑对象窗口摘要，不复制全部事实。"""

    return {
        "task_id": task.get("task_id"),
        "object_id": task.get("object_id"),
        "object_type": task.get("object_type"),
        "parent_window_id": task.get("parent_window_id"),
        "source_seq_refs": task.get("source_seq_refs", []),
        "local_windows": [
            {
                "window_id": window.get("window_id"),
                "source_seq_refs": window.get("source_seq_refs", []),
                "context_source_seq_refs": window.get("context_source_seq_refs", []),
            }
            for window in task.get("local_windows", [])
        ],
    }


def _object_segments(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    segments: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_key: tuple[str, str] | None = None
    for row in rows:
        table_id = str(row.get("table_id") or "")
        key = ("table", table_id) if table_id else ("text", "")
        if current and key != current_key:
            segments.append(current)
            current = []
        current.append(row)
        current_key = key
    if current:
        segments.append(current)
    return segments


def _object_overview(
    *,
    object_id: str,
    object_type: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    pages = sorted(
        {page for row in rows if (page := _as_int(row.get("page_no"))) is not None}
    )
    if object_type == "table":
        grouped = _table_rows(rows)
        row_numbers = sorted(grouped)
        column_numbers = sorted(
            {
                column
                for entries in grouped.values()
                for entry in entries
                if (column := _cell_position(entry)[1]) is not None
            }
        )
        shapes = Counter(len(entries) for entries in grouped.values())
        representative = _representative_values(row_numbers, limit=16)
        row_summaries = [
            {
                "row": row_no,
                "cells": [
                    {
                        "cell_id": entry.get("cell_id"),
                        "column": _cell_position(entry)[1],
                        "source_seq": _as_int(entry.get("source_seq")),
                        "text": str(entry.get("text") or "")[:160],
                        "style_signature": _style_signature(entry),
                    }
                    for entry in grouped[row_no]
                ],
            }
            for row_no in representative
        ]
        return {
            "object_id": object_id,
            "object_type": object_type,
            "dimensions": {
                "rows": len(row_numbers),
                "columns": max(column_numbers, default=0),
            },
            "pages": pages,
            "row_shape_counts": [
                {"cells_per_row": shape, "row_count": count}
                for shape, count in sorted(shapes.items())
            ],
            "empty_visible_cell_count": sum(1 for row in rows if not str(row.get("text") or "").strip()),
            "representative_rows": row_summaries,
            "omitted_row_count": max(0, len(row_numbers) - len(representative)),
        }
    representative_rows = _representative_values(list(range(len(rows))), limit=24)
    return {
        "object_id": object_id,
        "object_type": object_type,
        "item_count": len(rows),
        "pages": pages,
        "representative_rows": [
            {
                "source_seq": _as_int(rows[index].get("source_seq")),
                "text": str(rows[index].get("text") or "")[:240],
                "kind": rows[index].get("kind"),
                "style_signature": _style_signature(rows[index]),
            }
            for index in representative_rows
        ],
        "omitted_item_count": max(0, len(rows) - len(representative_rows)),
    }


def _table_local_windows(
    *,
    rows: list[dict[str, Any]],
    parent_window: dict[str, Any],
    task_id: str,
    max_items: int,
    max_chars: int,
) -> list[dict[str, Any]]:
    grouped = _table_rows(rows)
    row_numbers = sorted(grouped)
    groups: list[list[int]] = []
    current: list[int] = []
    current_items = 0
    current_chars = 0
    for row_no in row_numbers:
        row_items = len(grouped[row_no])
        row_chars = sum(len(str(item.get("text") or "")) for item in grouped[row_no])
        if current and (current_items + row_items > max_items or current_chars + row_chars > max_chars):
            groups.append(current)
            current = []
            current_items = 0
            current_chars = 0
        current.append(row_no)
        current_items += row_items
        current_chars += row_chars
    if current:
        groups.append(current)

    windows: list[dict[str, Any]] = []
    for index, group in enumerate(groups, start=1):
        claimable = _seqs_for_table_rows(grouped, group)
        context_rows: list[int] = []
        if row_numbers and row_numbers[0] not in group:
            context_rows.append(row_numbers[0])
        first_index = row_numbers.index(group[0])
        last_index = row_numbers.index(group[-1])
        if first_index > 0:
            context_rows.append(row_numbers[first_index - 1])
        if last_index + 1 < len(row_numbers):
            context_rows.append(row_numbers[last_index + 1])
        context = _seqs_for_table_rows(grouped, sorted(set(context_rows)))
        windows.append(
            _local_window(
                parent_window=parent_window,
                task_id=task_id,
                index=index,
                claimable=claimable,
                context=context,
            )
        )
    return windows


def _text_local_windows(
    *,
    rows: list[dict[str, Any]],
    parent_window: dict[str, Any],
    task_id: str,
    max_items: int,
    max_chars: int,
) -> list[dict[str, Any]]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    chars = 0
    for row in rows:
        row_chars = len(str(row.get("text") or ""))
        if current and (len(current) >= max_items or chars + row_chars > max_chars):
            groups.append(current)
            current = []
            chars = 0
        current.append(row)
        chars += row_chars
    if current:
        groups.append(current)

    windows: list[dict[str, Any]] = []
    for index, group in enumerate(groups, start=1):
        claimable = [_as_int(row.get("source_seq")) for row in group]
        context: list[int] = []
        start = rows.index(group[0])
        end = rows.index(group[-1])
        if start > 0:
            previous = _as_int(rows[start - 1].get("source_seq"))
            if previous is not None:
                context.append(previous)
        if end + 1 < len(rows):
            following = _as_int(rows[end + 1].get("source_seq"))
            if following is not None:
                context.append(following)
        windows.append(
            _local_window(
                parent_window=parent_window,
                task_id=task_id,
                index=index,
                claimable=[value for value in claimable if value is not None],
                context=context,
            )
        )
    return windows


def _local_window(
    *,
    parent_window: dict[str, Any],
    task_id: str,
    index: int,
    claimable: list[int],
    context: list[int],
) -> dict[str, Any]:
    return {
        "window_id": f"{task_id}:part_{index:03d}",
        "unit_id": parent_window.get("unit_id"),
        "source_seq_refs": sorted(set(claimable)),
        "context_source_seq_refs": sorted(set(context) - set(claimable)),
        "neighbor_context": parent_window.get("neighbor_context"),
    }


def _local_row(row: dict[str, Any], *, claimable: set[int]) -> dict[str, Any]:
    seq = _as_int(row.get("source_seq"))
    style_details = row.get("style_details") or {}
    style_runs = [run for run in style_details.get("runs", []) if isinstance(run, dict)]
    raw_ids = [str(value) for value in (row.get("raw_run_ids") or [])]
    logical_ids = [str(value) for value in (row.get("logical_run_ids") or [])]
    run_facts: list[dict[str, Any]] = []
    for index, run in enumerate(style_runs):
        run_facts.append(
            {
                "raw_run_id": raw_ids[index] if index < len(raw_ids) else None,
                "logical_run_id": logical_ids[min(index, len(logical_ids) - 1)] if logical_ids else None,
                "text": run.get("text"),
                "source_ref": run.get("source_ref"),
                "effective_style": {
                    key: run.get(key)
                    for key in ("font_names", "font_size_pt", "bold", "italic", "underline", "color")
                    if run.get(key) is not None
                },
            }
        )
    return {
        "evidence_role": "claimable" if seq in claimable else "context_only",
        "source_seq": seq,
        "source_ref": row.get("source_ref"),
        "kind": row.get("kind"),
        "paragraph_id": row.get("paragraph_id"),
        "table_id": row.get("table_id"),
        "cell_id": row.get("cell_id"),
        "page_no": row.get("page_no"),
        "bbox": deepcopy(row.get("bbox")),
        "render_binding_status": row.get("render_binding_status"),
        "text": row.get("text", ""),
        "paragraph_style": deepcopy(style_details.get("paragraph") or {}),
        "raw_run_ids": raw_ids,
        "logical_run_ids": logical_ids,
        "runs": run_facts,
    }


def _visual_evidence(
    packet: dict[str, Any],
    *,
    rows: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    pages = sorted(
        {page for row in rows if (page := _as_int(row.get("page_no"))) is not None}
    )
    selected = _representative_values(pages, limit=limit)
    images = {
        _as_int(item.get("page_no")): item
        for item in (packet.get("render_artifacts") or {}).get("clean_page_images", [])
        if isinstance(item, dict) and _as_int(item.get("page_no")) is not None
    }
    result: list[dict[str, Any]] = []
    for page_no in selected:
        image = images.get(page_no) or {}
        path = image.get("path")
        if not path:
            continue
        result.append(
            {
                "visual_ref": f"page:{page_no}",
                "evidence_level": "page_context",
                "page_no": page_no,
                "width_px": image.get("width_px"),
                "height_px": image.get("height_px"),
                "_attachment_path": str(path),
            }
        )
    return result


def _table_rows(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    fallback = 0
    for item in rows:
        row_no, column_no = _cell_position(item)
        if row_no is None:
            fallback += 1
            row_no = 1_000_000 + fallback
        result.setdefault(row_no, []).append(item)
        result[row_no].sort(key=lambda value: _cell_position(value)[1] or 0)
    return result


def _cell_position(row: dict[str, Any]) -> tuple[int | None, int | None]:
    cell_id = str(row.get("cell_id") or "")
    match = _CELL_ID_RE.match(cell_id)
    if match:
        return int(match.group("row")), int(match.group("column"))
    source_ref = str(row.get("source_ref") or "")
    row_match = re.search(r"/tr\[(\d+)\]", source_ref)
    cell_match = re.search(r"/tc\[(\d+)\]", source_ref)
    return (
        int(row_match.group(1)) if row_match else None,
        int(cell_match.group(1)) if cell_match else None,
    )


def _seqs_for_table_rows(
    grouped: dict[int, list[dict[str, Any]]],
    row_numbers: list[int],
) -> list[int]:
    return sorted(
        {
            seq
            for row_no in row_numbers
            for item in grouped.get(row_no, [])
            if (seq := _as_int(item.get("source_seq"))) is not None
        }
    )


def _style_signature(row: dict[str, Any]) -> dict[str, Any]:
    dominant = (row.get("style_details") or {}).get("dominant_run") or {}
    paragraph = (row.get("style_details") or {}).get("paragraph") or {}
    return {
        "font_names": dominant.get("font_names"),
        "font_size_pt": dominant.get("font_size_pt"),
        "bold": dominant.get("bold"),
        "alignment": paragraph.get("alignment"),
    }


def _representative_values(values: list[int], *, limit: int) -> list[int]:
    if len(values) <= limit:
        return list(values)
    indexes = {0, len(values) - 1}
    for step in range(1, limit - 1):
        indexes.add(round(step * (len(values) - 1) / (limit - 1)))
    return [values[index] for index in sorted(indexes)][:limit]


def _clean_list(value: Any, *, limit: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value[:limit] if isinstance(item, dict)]


def _ints(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    return [value for value in (_as_int(item) for item in values) if value is not None]


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
