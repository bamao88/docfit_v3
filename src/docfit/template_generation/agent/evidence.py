"""Module 1 第一相的 clean evidence 投影与防火墙。

AI 独立观察的前提是它**只看干净 Word 事实**，看不到任何代码阶段结论。本模块：

1. 用字段白名单把 ``document_facts`` / render packet 投影成 T2/T4 的证据视图：
   - T2 = 全文压缩（每 source_seq 文本/样式/页/锚点事实 + 页缩略图 refs）
   - T3 = 由 ``t3_input`` 按最新的整单元路由与条件式局部窗口构造
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
    "t2": (
        "source_seq",
        "page_no",
        "render_target_id",
        "flow_item_type",
        "text",
        "style",
        "text_facts",
        "page_position",
    ),
    "t4": (
        "page_no",
        "render_target_id",
        "page_top_ratio",
        "bbox",
    ),
}

T2_TEXT_FACT_FIELDS = (
    "alignment",
    "dominant_bold",
    "dominant_font_size_pt",
    "has_line_break",
    "has_tab",
    "leader_char_run",
    "trailing_token",
)
T2_BREAK_FACT_FIELDS = (
    "index",
    "kind",
    "type",
    "paragraph_index",
)
T2_PAGE_IMAGE_REF_FIELDS = (
    "page_no",
    "sha256",
    "width_px",
    "height_px",
    "image_type",
)

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
    """T2 全文压缩证据：文本顺序 + 紧凑样式事实 + 可回绑分页事实。"""

    packet_rows = [
        item
        for item in packet.get("page_text_index", [])
        if isinstance(item, dict) and item.get("source_seq") is not None
    ]
    render_available = packet.get("render_status") == "real_render"
    layout_by_seq = {
        seq: item
        for item in packet.get("page_layout_index", [])
        if isinstance(item, dict)
        and (seq := _as_int(item.get("source_seq"))) is not None
    }
    first_seq_by_page = _first_source_seq_by_page(packet_rows) if render_available else {}
    rows: list[dict[str, Any]] = []
    for item in packet_rows:
        row = _project(item, "t2")
        row["text_facts"] = _project_t2_text_facts(item.get("text_facts"))
        source_seq = _as_int(item.get("source_seq"))
        layout = layout_by_seq.get(source_seq, {})
        page_position = _t2_page_position(
            item,
            layout,
            render_available=render_available,
            first_seq_by_page=first_seq_by_page,
        )
        if page_position:
            row["page_position"] = page_position
        if not row["text_facts"]:
            row.pop("text_facts")
        rows.append(row)

    render_artifacts = packet.get("render_artifacts", {}) or {}
    layout_facts = packet.get("global_layout_facts", {}) or {}
    view = {
        "scope": "t2_full_document",
        "source_render_hash": packet.get("source_render_hash"),
        "render_status": packet.get("render_status"),
        "render_available": render_available,
        "document_summary": {
            "source_seq_count": len(rows),
            "page_count": render_artifacts.get("page_count"),
        },
        "rows": rows,
        "page_summary": _t2_page_summary(packet_rows) if render_available else [],
        "break_facts": _t2_break_facts(layout_facts.get("breaks"), packet_rows),
        # T2 text responder does not receive image bytes. Keep only stable page-image
        # references and strip machine-local paths from the JSON prompt.
        "page_thumbnails": [
            projected
            for item in render_artifacts.get("clean_page_images", []) or []
            if isinstance(item, dict)
            and (projected := _project_fields(item, T2_PAGE_IMAGE_REF_FIELDS))
        ],
    }
    assert_firewall_clean(view)
    return view


def _project_fields(value: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        field: value.get(field)
        for field in fields
        if value.get(field) is not None
    }


def _project_t2_text_facts(value: Any) -> dict[str, Any]:
    projected = _project_fields(value, T2_TEXT_FACT_FIELDS)
    return {
        key: item
        for key, item in projected.items()
        if item is not False
    }


def _first_source_seq_by_page(rows: list[dict[str, Any]]) -> dict[int, int]:
    first_by_page: dict[int, int] = {}
    for item in rows:
        page_no = _as_int(item.get("page_no"))
        source_seq = _as_int(item.get("source_seq"))
        if page_no is None or source_seq is None:
            continue
        first_by_page.setdefault(page_no, source_seq)
    return first_by_page


def _t2_page_position(
    row: dict[str, Any],
    layout: dict[str, Any],
    *,
    render_available: bool,
    first_seq_by_page: dict[int, int],
) -> dict[str, Any]:
    if not render_available:
        return {}
    page_no = _as_int(row.get("page_no"))
    source_seq = _as_int(row.get("source_seq"))
    if page_no is None or source_seq is None:
        return {}
    if first_seq_by_page.get(page_no) != source_seq:
        return {}
    position: dict[str, Any] = {"starts_new_rendered_page": True}
    top_ratio = _as_float(layout.get("page_top_ratio"))
    if top_ratio is not None:
        position["page_top_ratio"] = round(top_ratio, 4)
    return position


def _t2_break_facts(value: Any, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered_rows = sorted(
        (
            (order, source_seq)
            for row in rows
            if (order := _as_int(row.get("order"))) is not None
            and (source_seq := _as_int(row.get("source_seq"))) is not None
        ),
        key=lambda item: item[0],
    )
    last_source_seq = ordered_rows[-1][1] if ordered_rows else None
    result: list[dict[str, Any]] = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        projected = _project_fields(item, T2_BREAK_FACT_FIELDS)
        paragraph_index = _as_int(item.get("paragraph_index"))
        preceding = [
            source_seq
            for order, source_seq in ordered_rows
            if paragraph_index is not None and order <= paragraph_index
        ]
        after_source_seq = preceding[-1] if preceding else None
        if (
            after_source_seq is None
            and paragraph_index is None
            and str(item.get("source_ref") or "").endswith(":body/sectPr")
        ):
            after_source_seq = last_source_seq
        if after_source_seq is not None:
            projected["after_source_seq"] = after_source_seq
        if projected:
            result.append(projected)
    return result


def _t2_page_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_page: dict[int, list[int]] = {}
    for item in rows:
        page_no = _as_int(item.get("page_no"))
        source_seq = _as_int(item.get("source_seq"))
        if page_no is None or source_seq is None:
            continue
        by_page.setdefault(page_no, []).append(source_seq)
    return [
        {
            "page_no": page_no,
            "first_source_seq": refs[0],
            "last_source_seq": refs[-1],
            "text_items": len(refs),
        }
        for page_no, refs in sorted(by_page.items())
    ]


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
        # Track A：确定性全局版式事实（无需页图）。
        "global_layout_facts": packet.get("global_layout_facts", {}),
        # Track B：真实页图（视觉分页）。
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


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None
