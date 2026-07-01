"""Module 1 第一相的 clean evidence 投影与防火墙。

AI 独立观察的前提是它**只看干净 Word 事实**，看不到任何代码阶段结论。本模块：

1. 用字段白名单把 ``document_facts`` / render packet 投影成三 scope 的证据视图：
   - T2 = 全文压缩（每 source_seq 文本/样式/页/锚点事实 + 页缩略图 refs）
   - T3 = 单元窗口全文（窗口内每 source_seq 全文 + run/style 事实 + 命中窗口 fields）
   - T4 = 真实页图（要求 real_render，否则该阶段 abstain）+ 页眉脚/sections/numbering 事实
2. ``assert_firewall_clean`` 在证据子树上扫 deny-set **键名**，命中即抛
   ``EvidenceFirewallError``——拦住 ``unit_map`` / ``element_spec`` / ``template_policy``
   / ``standards`` / ``gold`` 等结论字段被偷偷喂给模型。

真实陷阱：T1 产物的 ``data.paragraphs[*]`` 已被观测到混入 ``template_policy`` /
``final_disposition`` / ``policy_reason`` 这类下游策略字段；投影只取白名单字段即把它们挡在外面。
"""

from __future__ import annotations

from typing import Any

# 每 scope 允许进入证据视图的字段白名单（唯一真相，单测护）。
EVIDENCE_FIELD_WHITELIST = {
    "t2": ("source_seq", "page_no", "render_target_id", "text", "style"),
    "t3": (
        "source_seq",
        "page_no",
        "render_target_id",
        "text",
        "style",
        "style_details",
        "raw_run_ids",
        "logical_run_ids",
    ),
    "t4": (
        "page_no",
        "render_target_id",
        "page_top_ratio",
        "bbox",
    ),
}

# 命中即判定证据被代码结论污染的 deny-set 键名（精确名 + expected_ 前缀）。
FIREWALL_DENY_KEYS = frozenset(
    {
        "unit_map",
        "unit_id",
        "structure_candidates",
        "candidate_policy",
        "candidate_policies",
        "candidate_targets",
        "element_spec",
        "global_spec",
        "template_spec",
        "template_policy",
        "final_disposition",
        "policy_reason",
        "standards",
        "gold",
        "judge",
    }
)
FIREWALL_DENY_PREFIXES = ("expected_",)


class EvidenceFirewallError(RuntimeError):
    """证据视图混入了代码阶段结论字段。"""


def assert_firewall_clean(view: Any, *, where: str = "$") -> None:
    """递归扫描视图的 dict 键名；命中 deny-set 即抛。

    只扫键名、不扫字符串值——packet 自带的 ``forbidden_ai_tasks`` 任务清单文案
    （值里有 ``write_unit_map`` 等字样）不应误报。
    """

    if isinstance(view, dict):
        for key, value in view.items():
            key_str = str(key)
            if key_str in FIREWALL_DENY_KEYS or any(
                key_str.startswith(prefix) for prefix in FIREWALL_DENY_PREFIXES
            ):
                raise EvidenceFirewallError(
                    f"evidence view leaked code-stage conclusion field {key_str!r} at {where}"
                )
            assert_firewall_clean(value, where=f"{where}.{key_str}")
    elif isinstance(view, list):
        for index, item in enumerate(view):
            assert_firewall_clean(item, where=f"{where}[{index}]")


def _project(item: dict[str, Any], scope: str) -> dict[str, Any]:
    fields = EVIDENCE_FIELD_WHITELIST[scope]
    return {field: item.get(field) for field in fields if item.get(field) is not None}


def build_t2_evidence(packet: dict[str, Any]) -> dict[str, Any]:
    """T2 全文压缩证据：每 source_seq 一条事实行 + 页缩略图 refs。"""

    rows = [
        _project(item, "t2")
        for item in packet.get("page_text_index", [])
        if item.get("source_seq") is not None
    ]
    render_artifacts = packet.get("render_artifacts", {}) or {}
    view = {
        "scope": "t2_full_document",
        "source_render_hash": packet.get("source_render_hash"),
        "render_status": packet.get("render_status"),
        "rows": rows,
        "page_thumbnails": list(render_artifacts.get("clean_page_images", []) or []),
    }
    assert_firewall_clean(view)
    return view


def build_t3_evidence(
    packet: dict[str, Any],
    *,
    window: dict[str, Any],
) -> dict[str, Any]:
    """T3 单元窗口全文证据：窗口内 source_seq 的全文 + run/style 事实。"""

    window_refs = {
        ref for ref in (_as_int(x) for x in window.get("source_seq_refs", [])) if ref is not None
    }
    rows = [
        _project(item, "t3")
        for item in packet.get("page_text_index", [])
        if _as_int(item.get("source_seq")) in window_refs
    ]
    view = {
        "scope": "t3_unit_window",
        "source_render_hash": packet.get("source_render_hash"),
        "window_id": window.get("window_id"),
        "neighbor_context": window.get("neighbor_context"),
        "rows": rows,
    }
    assert_firewall_clean(view)
    return view


def build_t4_evidence(packet: dict[str, Any]) -> dict[str, Any]:
    """T4 真实页图证据：无 real_render 时 ``render_available=False`` → 上层强制 abstain。"""

    render_artifacts = packet.get("render_artifacts", {}) or {}
    clean_images = list(render_artifacts.get("clean_page_images", []) or [])
    real_render = packet.get("render_status") == "real_render" and bool(clean_images)
    view = {
        "scope": "t4_global_layout",
        "source_render_hash": packet.get("source_render_hash"),
        "render_status": packet.get("render_status"),
        "render_available": real_render,
        "page_images": clean_images,
        "page_layout_index": [_project(item, "t4") for item in packet.get("page_layout_index", [])],
    }
    assert_firewall_clean(view)
    return view


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None
