"""物化校验闸门：让产物“无论模型质量都良构”。

逐 item 跑 5 道确定性闸门，越界即降级 unknown 并写 ``quality_report.demotions``
（也是 Module 2 的冲突种子）：

  ② 标签闭合：unit_id∈taxonomy、policy∈6、confidence∈3、field_type∈4；越界 → 降级
  ③ 证据绑定：source_seq_refs 必须存在于 render packet；未绑定 → 降级
  ④ 必填规则（镜像 ontology）：fill→fill_source、generated→field_type、manual_only→manual_semantics
  ⑤ 覆盖/不重叠：owned=∪存活 item.refs；同一 seq 被争用时高 confidence 留、平票判 contested→unknown

① schema 形状校验 + source_render_hash 对齐由 observation_schema / loop 负责。
空/垃圾响应也产 schema-valid 产物（全 unknown，abstain=true）。
"""

from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso

from .observation_schema import (
    ALLOWED_FIELD_TYPES,
    ALLOWED_FILL_SOURCES,
    ALLOWED_POLICIES,
    ALLOWED_ROLES,
    ALLOWED_UNIT_IDS,
    CONFIDENCE_LEVELS,
    OBSERVATION_SCHEMA_VERSION,
    PROMPT_CONTRACT_VERSION,
    UNKNOWN_UNIT_ID,
    compute_coverage,
)
from .packet import packet_source_seq_set

_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


def materialize_unit_observation(
    raw_items: list[dict[str, Any]],
    *,
    packet: dict[str, Any],
    model: str = "replay",
    self_consistency: dict[str, Any] | None = None,
) -> dict[str, Any]:
    valid_seq = packet_source_seq_set(packet)
    demotions: list[dict[str, Any]] = []
    survivors: list[dict[str, Any]] = []
    unknown_items: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_items):
        item_id = str(raw.get("unit_id") or f"unit_{index:03d}")
        unit_id = str(raw.get("unit_id") or "")
        confidence = _normalize_confidence(raw.get("confidence"))
        # ② 标签闭合
        if unit_id not in ALLOWED_UNIT_IDS:
            unknown_items.append(_as_unknown(raw, reason="unit_id not in taxonomy"))
            demotions.append(_demotion(item_id, "C-LABEL-CLOSURE", f"unit_id {unit_id!r} not in taxonomy"))
            continue
        # ③ 证据绑定
        refs = _ints(raw.get("source_seq_refs"))
        bound = [seq for seq in refs if seq in valid_seq]
        if not bound:
            unknown_items.append(_as_unknown(raw, reason="no evidence binding"))
            demotions.append(_demotion(item_id, "C-EVIDENCE-BIND", "source_seq_refs not in render packet"))
            continue
        unbound = sorted(set(refs) - valid_seq)
        if unbound:
            demotions.append(_demotion(item_id, "C-EVIDENCE-BIND", f"dropped unbound source_seq {unbound}"))
        survivors.append(
            {
                "unit_id": unit_id,
                "name": raw.get("name"),
                "order": raw.get("order", index),
                "source_seq_refs": sorted(bound),
                "page_start": raw.get("page_start"),
                "confidence": confidence,
                "anchors": raw.get("anchors", []),
                "evidence_refs": raw.get("evidence_refs", []),
                "flags": raw.get("flags", []),
                "ai_rationale": raw.get("ai_rationale"),
            }
        )

    # ⑤ 覆盖/不重叠
    items = _resolve_overlap(survivors, unknown_items, demotions)
    coverage = compute_coverage(items, all_source_seq=valid_seq)
    return _envelope(
        "ai_unit_observation",
        packet=packet,
        model=model,
        items=items,
        unknown_items=unknown_items,
        coverage=coverage,
        demotions=demotions,
        self_consistency=self_consistency,
    )


def materialize_element_observation(
    raw_items: list[dict[str, Any]],
    *,
    packet: dict[str, Any],
    window: dict[str, Any],
    model: str = "replay",
) -> dict[str, Any]:
    valid_seq = packet_source_seq_set(packet)
    window_refs = set(_ints(window.get("source_seq_refs")))
    unit_id = str(window.get("unit_id") or "")
    demotions: list[dict[str, Any]] = []
    survivors: list[dict[str, Any]] = []
    unknown_items: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_items):
        element_id = str(raw.get("element_id") or f"{unit_id}.{index:03d}")
        policy = str(raw.get("policy") or "")
        confidence = _normalize_confidence(raw.get("confidence"))
        # ② 标签闭合
        if policy not in ALLOWED_POLICIES:
            unknown_items.append(_as_unknown(raw, reason="policy not in ontology"))
            demotions.append(_demotion(element_id, "C-LABEL-CLOSURE", f"policy {policy!r} not in ontology"))
            continue
        role = raw.get("role")
        if role is not None and role not in ALLOWED_ROLES:
            demotions.append(_demotion(element_id, "C-LABEL-CLOSURE", f"role {role!r} not in ontology; dropped"))
            role = None
        # ③ 证据绑定 + 窗口边界
        refs = _ints(raw.get("source_seq_refs"))
        bound = [seq for seq in refs if seq in valid_seq and seq in window_refs]
        if not bound:
            unknown_items.append(_as_unknown(raw, reason="no in-window evidence binding"))
            demotions.append(_demotion(element_id, "C-EVIDENCE-BIND", "source_seq_refs outside unit window or packet"))
            continue
        # ④ 必填规则
        missing = _required_field_error(policy, raw)
        if missing is not None:
            unknown_items.append(_as_unknown(raw, reason=missing))
            demotions.append(_demotion(element_id, "C-REQUIRED-FIELD", missing))
            continue
        survivors.append(
            {
                "element_id": element_id,
                "unit_id": unit_id,
                "order": raw.get("order", index),
                "policy": policy,
                "role": role,
                "content": raw.get("content"),
                "source_seq_refs": sorted(bound),
                "raw_run_ids": raw.get("raw_run_ids", []),
                "confidence": confidence,
                "evidence_refs": raw.get("evidence_refs", []),
                "fill_source": raw.get("fill_source"),
                "generated": raw.get("generated"),
                "manual_semantics": raw.get("manual_semantics"),
                "ai_rationale": raw.get("ai_rationale"),
                "ai_decision_path": raw.get("ai_decision_path"),
            }
        )

    items = _resolve_overlap(survivors, unknown_items, demotions, id_key="element_id")
    # 元素覆盖只在本单元窗口内衡量。
    coverage = compute_coverage(items, all_source_seq=window_refs & valid_seq)
    observation = _envelope(
        "ai_element_observation",
        packet=packet,
        model=model,
        items=items,
        unknown_items=unknown_items,
        coverage=coverage,
        demotions=demotions,
        self_consistency=None,
    )
    observation["window_id"] = window.get("window_id")
    observation["unit_id"] = unit_id
    return observation


def materialize_layout_observation(
    raw_payload: dict[str, Any],
    *,
    packet: dict[str, Any],
    render_available: bool,
    model: str = "replay",
) -> dict[str, Any]:
    valid_seq = packet_source_seq_set(packet)
    demotions: list[dict[str, Any]] = []
    survivors: list[dict[str, Any]] = []
    unknown_items: list[dict[str, Any]] = []

    # T4 无真实页图 → 一等公民 abstain，不幻觉版式。
    if not render_available:
        observation = _envelope(
            "ai_layout_observation",
            packet=packet,
            model=model,
            items=[],
            unknown_items=list(raw_payload.get("section_profiles", []) or []),
            coverage=compute_coverage([], all_source_seq=valid_seq),
            demotions=[_demotion("layout", "C-LAYOUT-ABSTAIN", "no real_render page images; abstaining")],
            self_consistency=None,
        )
        observation["abstain"] = True
        observation["default_font"] = None
        observation["page_numbering"] = None
        observation["header_footer"] = []
        return observation

    for index, raw in enumerate(raw_payload.get("section_profiles", []) or []):
        profile_id = str(raw.get("section_profile_id") or f"section_{index:03d}")
        boundary = raw.get("boundary") or {}
        start = _int_or_none(boundary.get("start_source_seq"))
        end = _int_or_none(boundary.get("end_source_seq"))
        evidence_refs = raw.get("evidence_refs") or []
        # ③ 证据绑定：边界 source_seq 在 packet 内，且 evidence_refs 需带 page_no+render_target
        if start is None or end is None or start not in valid_seq or end not in valid_seq:
            unknown_items.append(_as_unknown(raw, reason="section boundary not bound to packet"))
            demotions.append(_demotion(profile_id, "C-EVIDENCE-BIND", "section boundary source_seq not in packet"))
            continue
        if not _has_layout_evidence(evidence_refs):
            unknown_items.append(_as_unknown(raw, reason="evidence_refs missing page_no/render_target"))
            demotions.append(_demotion(profile_id, "C-EVIDENCE-BIND", "section evidence_refs lack page_no+render_target"))
            continue
        survivors.append(
            {
                "section_profile_id": profile_id,
                "boundary": {
                    "start_source_seq": start,
                    "end_source_seq": end,
                    "confidence": _normalize_confidence(boundary.get("confidence")),
                },
                "source_seq_refs": list(range(start, end + 1)),
                "page_setup": raw.get("page_setup"),
                "header_footer": raw.get("header_footer"),
                "page_numbering": raw.get("page_numbering"),
                "evidence_refs": evidence_refs,
            }
        )

    items = _resolve_overlap(survivors, unknown_items, demotions, id_key="section_profile_id")
    coverage = compute_coverage(items, all_source_seq=valid_seq)
    observation = _envelope(
        "ai_layout_observation",
        packet=packet,
        model=model,
        items=items,
        unknown_items=unknown_items,
        coverage=coverage,
        demotions=demotions,
        self_consistency=None,
    )
    observation["default_font"] = raw_payload.get("default_font")
    observation["page_numbering"] = raw_payload.get("page_numbering")
    observation["header_footer"] = raw_payload.get("header_footer", [])
    observation["numbering_rules"] = raw_payload.get("numbering_rules", [])
    return observation


def _resolve_overlap(
    survivors: list[dict[str, Any]],
    unknown_items: list[dict[str, Any]],
    demotions: list[dict[str, Any]],
    *,
    id_key: str = "unit_id",
) -> list[dict[str, Any]]:
    """同一 source_seq 被多 item 争用：高 confidence 留，平票判 contested→让位 unknown。"""

    claims: dict[int, list[int]] = {}
    for idx, item in enumerate(survivors):
        for seq in item.get("source_seq_refs", []):
            claims.setdefault(seq, []).append(idx)

    contested_drop: dict[int, set[int]] = {}
    for seq, claimants in claims.items():
        if len(claimants) <= 1:
            continue
        ranked = sorted(claimants, key=lambda i: _rank(survivors[i]), reverse=True)
        top = _rank(survivors[ranked[0]])
        winners = [i for i in ranked if _rank(survivors[i]) == top]
        if len(winners) == 1:
            keep = winners[0]
            losers = [i for i in claimants if i != keep]
        else:
            # 平票：该 seq 谁都不占，判 contested。
            keep = None
            losers = list(claimants)
            demotions.append(
                _demotion(str(seq), "C-COVERAGE-CONTESTED", f"source_seq {seq} contested by tie; left unknown")
            )
        for i in losers:
            contested_drop.setdefault(i, set()).add(seq)
        if keep is None:
            continue

    result: list[dict[str, Any]] = []
    for idx, item in enumerate(survivors):
        drop = contested_drop.get(idx, set())
        kept = [seq for seq in item.get("source_seq_refs", []) if seq not in drop]
        if not kept:
            unknown_items.append({**item, "demotion_reason": "lost all refs in overlap resolution"})
            demotions.append(_demotion(str(item.get(id_key)), "C-COVERAGE-OVERLAP", "lost all refs to higher-confidence items"))
            continue
        result.append({**item, "source_seq_refs": kept})
    return result


def _required_field_error(policy: str, raw: dict[str, Any]) -> str | None:
    if policy == "fill":
        source = raw.get("fill_source")
        if source not in ALLOWED_FILL_SOURCES:
            return f"fill policy requires fill_source in {sorted(ALLOWED_FILL_SOURCES)}"
    if policy == "generated":
        generated = raw.get("generated") or {}
        if generated.get("field_type") not in ALLOWED_FIELD_TYPES:
            return f"generated policy requires generated.field_type in {sorted(ALLOWED_FIELD_TYPES)}"
    if policy == "manual_only":
        if not raw.get("manual_semantics"):
            return "manual_only policy requires manual_semantics"
    return None


def _has_layout_evidence(evidence_refs: list[Any]) -> bool:
    for ref in evidence_refs or []:
        if isinstance(ref, dict) and ref.get("page_no") is not None and ref.get("render_target_id"):
            return True
    return False


def _envelope(
    artifact_type: str,
    *,
    packet: dict[str, Any],
    model: str,
    items: list[dict[str, Any]],
    unknown_items: list[dict[str, Any]],
    coverage: dict[str, Any],
    demotions: list[dict[str, Any]],
    self_consistency: dict[str, Any] | None,
) -> dict[str, Any]:
    from .observation_schema import OBSERVATION_STAGES

    return {
        "artifact_type": artifact_type,
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "stage": OBSERVATION_STAGES[artifact_type],
        "source_render_hash": packet.get("source_render_hash"),
        "model": model,
        "created_at": now_iso(),
        "coverage": coverage,
        "items": items,
        "unknown_items": unknown_items,
        "open_questions": [],
        "abstain": not items,
        "self_consistency": self_consistency,
        "quality_report": {
            "demotions": demotions,
            "owned_count": len(coverage.get("owned_source_seq", [])),
            "unknown_count": len(coverage.get("unknown_source_seq", [])),
        },
    }


def _as_unknown(raw: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {**raw, "unit_id": UNKNOWN_UNIT_ID, "demotion_reason": reason}


def _demotion(item_id: str, check_id: str, reason: str) -> dict[str, Any]:
    return {"item_id": item_id, "check_id": check_id, "reason": reason}


def _rank(item: dict[str, Any]) -> int:
    return _CONFIDENCE_RANK.get(str(item.get("confidence") or ""), 0)


def _normalize_confidence(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in CONFIDENCE_LEVELS else "low"


def _ints(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    return [v for v in (_int_or_none(x) for x in values) if v is not None]


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None
