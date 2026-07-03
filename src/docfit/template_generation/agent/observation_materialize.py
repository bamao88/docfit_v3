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
    open_questions_from,
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
    page_observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    valid_seq = packet_source_seq_set(packet)
    page_observations = page_observations or []
    demotions: list[dict[str, Any]] = []
    survivors: list[dict[str, Any]] = []
    unknown_items: list[dict[str, Any]] = []

    # Track A：从确定性全局版式事实构造 section_profile（无需图/模型，不会幻觉）。
    global_facts = packet.get("global_layout_facts", {}) or {}
    survivors.extend(_deterministic_global_profiles(global_facts, valid_seq))

    # Track B：视觉分页只在有真实页图时用模型输出；无图则该子项弃权，但不整体 abstain。
    visual_abstained = not render_available
    if not render_available:
        if raw_payload.get("section_profiles"):
            unknown_items.extend(list(raw_payload.get("section_profiles", []) or []))
        demotions.append(
            _demotion(
                "layout_visual",
                "C-LAYOUT-VISUAL-ABSTAIN",
                "no real_render page images; visual per-unit sub-scope abstained (Track B)",
            )
        )
        items = _resolve_overlap(survivors, unknown_items, demotions, id_key="section_profile_id")
        observation = _finalize_layout(
            packet=packet,
            model=model,
            items=items,
            unknown_items=unknown_items,
            coverage=compute_coverage(items, all_source_seq=valid_seq),
            demotions=demotions,
            global_facts=global_facts,
            raw_payload=raw_payload,
            visual_abstained=visual_abstained,
            page_observations=page_observations,
        )
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
    return _finalize_layout(
        packet=packet,
        model=model,
        items=items,
        unknown_items=unknown_items,
        coverage=compute_coverage(items, all_source_seq=valid_seq),
        demotions=demotions,
        global_facts=global_facts,
        raw_payload=raw_payload,
        visual_abstained=False,
        page_observations=page_observations,
    )


def _deterministic_global_profiles(
    global_facts: dict[str, Any],
    valid_seq: set[int],
) -> list[dict[str, Any]]:
    """Track A：把 T1 分节事实确定性地转成 section_profile（不问模型，不幻觉）。

    源事实里分节没有 source_seq 边界（paragraph_index 为空）；单分节则覆盖全文，
    多分节则各建 profile 但不硬绑 seq（边界要靠 Track B 页图，见修复计划）。
    """

    sections = global_facts.get("sections") or []
    if not sections:
        return []
    single = len(sections) == 1
    profiles: list[dict[str, Any]] = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            continue
        profiles.append(
            {
                "section_profile_id": f"section_{section.get('index', index)}",
                "source": "deterministic_facts",
                "confidence": "high",
                "page_setup": {
                    "page_margins": section.get("page_margins"),
                    "page_size": section.get("page_size"),
                },
                "page_numbering": section.get("page_numbering"),
                "header_footer": section.get("references", []),
                "source_seq_refs": sorted(valid_seq) if single else [],
                "boundary_source": (
                    "single_section_covers_document" if single else "unknown_from_facts_needs_render"
                ),
            }
        )
    return profiles


def _finalize_layout(
    *,
    packet: dict[str, Any],
    model: str,
    items: list[dict[str, Any]],
    unknown_items: list[dict[str, Any]],
    coverage: dict[str, Any],
    demotions: list[dict[str, Any]],
    global_facts: dict[str, Any],
    raw_payload: dict[str, Any],
    visual_abstained: bool,
    page_observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
    # 有确定性全局 profile 就不整体 abstain；只标视觉子项是否弃权。
    observation["abstain"] = not items
    observation["visual_abstained"] = visual_abstained
    observation["default_font"] = raw_payload.get("default_font")
    observation["header_footer"] = global_facts.get("header_footer", [])
    observation["numbering_rules"] = raw_payload.get("numbering_rules", [])
    observation["numbering_definition_count"] = global_facts.get("numbering_definition_count", 0)

    # Track B(确定性)：有真实页图渲染时，page_layout_index 带 per-seq 真实 page_no
    # （pdftotext 版面），据此给出确定性页结构——无需模型视觉，不幻觉。
    if not visual_abstained:
        page_map = {
            seq: page
            for seq, page in (
                (_int_or_none(i.get("source_seq")), _int_or_none(i.get("page_no")))
                for i in packet.get("page_layout_index", [])
                if isinstance(i, dict)
            )
            if seq is not None and page is not None
        }
        pages = sorted(set(page_map.values()))
        observation["page_structure_source"] = "deterministic_pdf_layout"
        observation["page_count"] = len(pages)
        observation["page_map"] = {str(k): v for k, v in sorted(page_map.items())}
        for profile in observation["items"]:
            spanned = sorted({page_map[s] for s in profile.get("source_seq_refs", []) if s in page_map})
            profile["pages"] = spanned
    else:
        observation["page_structure_source"] = "unavailable_no_render"
        observation["page_count"] = None

    # Track B 视觉：逐页读图观察 + 从中聚合页眉脚/页码显示策略。
    pages = page_observations or []
    observation["page_observations"] = pages
    if pages:
        observation["vision_source"] = "minimax_m3"
        observation["header_footer_policy"] = {
            "pages_with_header": [p["page_no"] for p in pages if p.get("has_header")],
            "pages_with_footer": [p["page_no"] for p in pages if p.get("has_footer")],
        }
        observation["page_numbering_display"] = {
            "pages_with_visible_number": [p["page_no"] for p in pages if p.get("page_number_visible")],
            "samples": [
                {"page_no": p["page_no"], "text": p.get("page_number_text")}
                for p in pages
                if p.get("page_number_visible") and p.get("page_number_text")
            ][:8],
        }
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
        "open_questions": open_questions_from(
            demotions=demotions, coverage=coverage, self_consistency=self_consistency
        ),
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
