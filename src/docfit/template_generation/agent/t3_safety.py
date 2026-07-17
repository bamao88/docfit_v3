"""T3 保守路由与删除门禁。

模型可以提出语义判断，但删除是不可逆动作：只有精确绑定到 raw run、证据明确且单元
路由允许时才保留 ``instruction_remove``。其余情况降级成单元计划声明的安全保留策略，
并留下审计记录。
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any


_FORMAT_TERMS_RE = re.compile(
    r"(?:宋体|黑体|楷体|仿宋|华文\S{0,4}|Times\s+New\s+Roman|字体|字号|"
    r"小?[一二三四五六七八九0-9]+号|pt|磅|加粗|不加粗|斜体|下划线|"
    r"行距|缩进|段前|段后|居中|左对齐|右对齐|两端对齐|空\s*\d*\s*格|"
    r"页边距|上下左右|顶格|单倍|多倍|固定值)",
    re.IGNORECASE,
)
_NON_SEMANTIC_RE = re.compile(
    r"[\s\d０-９.,，。:：;；、()（）\[\]【】<>《》\-—_/＋+至和与或为用采用设置字体字号"
    r"宋体黑体楷体仿宋华文新魏小初一二三四五六七八九十号磅ptPT加粗不斜体下划线"
    r"行距缩进段前后居中左右两端对齐空格页边距上下顶格单倍多倍固定值]+"
)


def restrict_tasks_to_unit_plan(
    tasks: list[dict[str, Any]],
    unit_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    """按整单元路由裁剪后续局部调用，保留对象/表格边界。"""

    route = str(unit_plan.get("route") or "")
    if route == "preserve_whole":
        return []
    inspect = {int(value) for value in unit_plan.get("inspect_source_seq_refs", [])}
    if route != "inspect_suspected_regions":
        return deepcopy(tasks)
    selected: list[dict[str, Any]] = []
    for task in tasks:
        copied = deepcopy(task)
        windows: list[dict[str, Any]] = []
        for window in copied.get("local_windows", []):
            claimable = [
                int(value)
                for value in window.get("source_seq_refs", [])
                if int(value) in inspect
            ]
            if not claimable:
                continue
            windows.append({**window, "source_seq_refs": claimable})
        copied["local_windows"] = windows
        if windows:
            selected.append(copied)
    return selected


def guard_t3_payload(
    payload: dict[str, Any],
    *,
    evidence: dict[str, Any],
    unit_plan: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """阻止宽泛或低把握删除；被阻止的内容转成显式保留，而不是静默丢失。"""

    guarded = deepcopy(payload)
    items: list[dict[str, Any]] = []
    demotions: list[dict[str, Any]] = []
    rows = [row for row in evidence.get("rows", []) if isinstance(row, dict)]
    run_text = {
        str(run.get("raw_run_id")): str(run.get("text") or "")
        for row in rows
        if row.get("evidence_role") == "claimable"
        for run in row.get("runs", [])
        if isinstance(run, dict) and run.get("raw_run_id")
    }
    protected = {int(value) for value in unit_plan.get("protected_source_seq_refs", [])}
    inspect = {int(value) for value in unit_plan.get("inspect_source_seq_refs", [])}
    route = str(unit_plan.get("route") or "")
    for index, raw in enumerate(payload.get("items", []) or []):
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        if item.get("policy") != "instruction_remove":
            items.append(item)
            continue
        refs = _ints(item.get("source_seq_refs"))
        raw_ids = [str(value) for value in item.get("raw_run_ids", []) if value]
        reasons: list[str] = []
        if route not in {"inspect_suspected_regions", "full_local_analysis"}:
            reasons.append("unit route does not permit deletion")
        if str(item.get("confidence") or "") != "high":
            reasons.append("deletion confidence is not high")
        if not raw_ids or any(raw_id not in run_text for raw_id in raw_ids):
            reasons.append("deletion lacks exact in-window raw_run_ids")
        if protected.intersection(refs):
            reasons.append("deletion touches protected unit content")
        if route == "inspect_suspected_regions" and not set(refs).issubset(inspect):
            reasons.append("deletion falls outside inspected regions")
        selected_text = "".join(run_text.get(raw_id, "") for raw_id in raw_ids)
        if not _is_pure_format_annotation(selected_text):
            reasons.append("selected run text is not a pure formatting annotation")
        if not str(item.get("removal_reason") or "").strip():
            reasons.append("deletion has no explicit removal_reason")
        if not reasons:
            # 括号/空白等包装 run 本身不含格式语义，不能因为包住格式词就一并删除。
            # 只保留真正承载格式语言的最小 raw-run 集，其余 run 由保留 fallback 接管。
            exact_format_ids = [
                raw_id for raw_id in raw_ids if _FORMAT_TERMS_RE.search(run_text.get(raw_id, ""))
            ]
            if not exact_format_ids:
                reasons.append("no individual raw run carries formatting language")
            else:
                item["raw_run_ids"] = exact_format_ids
        if not reasons:
            item.setdefault("semantic_role", "format_annotation")
            item.setdefault("transformation", "remove_exact_span")
            items.append(item)
            continue
        safe = _safe_item(item, unit_plan=unit_plan)
        items.append(safe)
        demotions.append(
            {
                "item_id": str(item.get("element_id") or f"guarded_{index:03d}"),
                "check_id": "C-T3-CONSERVATIVE-DELETE",
                "reason": "; ".join(reasons),
                "original_policy": "instruction_remove",
                "effective_policy": safe["policy"],
            }
        )
    guarded["items"] = items
    return guarded, demotions


def preservation_fallback_items(
    packet: dict[str, Any],
    *,
    unit_window: dict[str, Any],
    unit_plan: dict[str, Any],
    existing_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """为未被局部判断认领的 run 生成安全默认项，保持整单元/整对象完整。"""

    wanted = {int(value) for value in unit_window.get("source_seq_refs", [])}
    claimed_whole = {
        seq
        for item in existing_items
        if not item.get("raw_run_ids")
        for seq in _ints(item.get("source_seq_refs"))
    }
    claimed_runs = {
        str(raw_id)
        for item in existing_items
        for raw_id in item.get("raw_run_ids", []) or []
        if raw_id
    }
    claimed_refs = {
        seq
        for item in existing_items
        for seq in _ints(item.get("source_seq_refs"))
    }
    result: list[dict[str, Any]] = []
    for row in packet.get("page_text_index", []):
        if not isinstance(row, dict):
            continue
        seq = _as_int(row.get("source_seq"))
        if seq is None or seq not in wanted or seq in claimed_whole:
            continue
        all_raw = [str(value) for value in row.get("raw_run_ids", []) if value]
        remaining = [raw_id for raw_id in all_raw if raw_id not in claimed_runs]
        if all_raw and not remaining:
            continue
        if not all_raw and seq in claimed_refs:
            continue
        item = {
            "element_id": f"{unit_window.get('unit_id')}.safe_{seq:04d}",
            "source_seq_refs": [seq],
            "raw_run_ids": remaining,
            "logical_run_ids": [str(value) for value in row.get("logical_run_ids", []) if value],
            "content": row.get("text"),
            "confidence": "medium",
            "ai_decision_path": "unit route safe preservation fallback",
        }
        result.append(_safe_item(item, unit_plan=unit_plan))
    return result


def _safe_item(item: dict[str, Any], *, unit_plan: dict[str, Any]) -> dict[str, Any]:
    policy = str(unit_plan.get("default_preservation_policy") or "fixed")
    if policy not in {"fixed", "template_default", "manual_only", "generated"}:
        policy = "fixed"
    safe = {
        **item,
        "policy": policy,
        "transformation": "preserve",
        "removal_reason": None,
    }
    if policy == "fixed":
        safe.setdefault("role", "template_fixed")
        safe.setdefault("semantic_role", "fixed_content")
    elif policy == "template_default":
        safe.setdefault("role", "template_fixed")
        safe.setdefault("semantic_role", "template_default_content")
    elif policy == "manual_only":
        safe.setdefault("role", "manual_field")
        safe.setdefault("semantic_role", "manual_field")
        safe.setdefault("manual_semantics", "保留原有人工填写或签署区域")
    else:
        safe.setdefault("role", "generated_field")
        safe.setdefault("semantic_role", "generated_field")
        safe.setdefault("generated", {"field_type": "FIELD_PLACEHOLDER"})
    return safe


def _is_pure_format_annotation(text: str) -> bool:
    value = text.strip()
    if not value or not _FORMAT_TERMS_RE.search(value):
        return False
    # 格式词之外仍有明显正文/声明/填写语义时拒绝删除。该门禁有意偏保守。
    residue = _NON_SEMANTIC_RE.sub("", value)
    return len(residue) <= 2


def _ints(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    return [value for value in (_as_int(item) for item in values) if value is not None]


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None
