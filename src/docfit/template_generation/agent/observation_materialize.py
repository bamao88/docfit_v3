"""T4 layout-observation materialization gates.

T2 has its own page-native exact contract in :mod:`docfit.template_generation.t2_ai`.
"""

from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso
from .observation_schema import (
    CONFIDENCE_LEVELS,
    OBSERVATION_SCHEMA_VERSION,
    PROMPT_CONTRACT_VERSION,
    compute_coverage,
    open_questions_from,
)
from .packet import packet_source_seq_set

_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


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

    # T4 语义只来自 AI。没有真实渲染时，原始输出不能升级为布局决定。
    visual_abstained = not render_available
    if not render_available:
        if raw_payload.get("section_profiles"):
            unknown_items.extend(list(raw_payload.get("section_profiles", []) or []))
        demotions.append(
            _demotion(
                "layout_visual",
                "C-LAYOUT-VISUAL-ABSTAIN",
                "no real_render page images; T4 AI layout decision is unavailable",
            )
        )
        observation = _finalize_layout(
            packet=packet,
            model=model,
            items=[],
            unknown_items=unknown_items,
            coverage=compute_coverage([], all_source_seq=valid_seq),
            demotions=demotions,
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
                "source_ref": raw.get("source_ref"),
                "boundary": {
                    "start_source_seq": start,
                    "end_source_seq": end,
                    "confidence": _normalize_confidence(boundary.get("confidence")),
                },
                "confidence": _normalize_confidence(boundary.get("confidence")),
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
        raw_payload=raw_payload,
        visual_abstained=False,
        page_observations=page_observations,
    )


def _finalize_layout(
    *,
    packet: dict[str, Any],
    model: str,
    items: list[dict[str, Any]],
    unknown_items: list[dict[str, Any]],
    coverage: dict[str, Any],
    demotions: list[dict[str, Any]],
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
    observation["abstain"] = not items
    observation["visual_abstained"] = visual_abstained
    observation["default_font"] = raw_payload.get("default_font")
    observation["page_numbering"] = raw_payload.get("page_numbering")
    observation["header_footer"] = raw_payload.get("header_footer", [])
    observation["numbering_rules"] = raw_payload.get("numbering_rules", [])
    if raw_payload.get("_observation_error"):
        observation["_observation_error"] = raw_payload["_observation_error"]

    # 页码映射只用于把 AI 决定绑定回已封存的 render 事实，不产生 T4 语义。
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
        observation["page_structure_source"] = "sealed_render_binding"
        observation["page_count"] = len(pages)
        observation["page_map"] = {str(k): v for k, v in sorted(page_map.items())}
        for profile in observation["items"]:
            spanned = sorted({page_map[s] for s in profile.get("source_seq_refs", []) if s in page_map})
            profile["pages"] = spanned
    else:
        observation["page_structure_source"] = "unavailable_no_render"
        observation["page_count"] = None

    # 逐页视觉观察是同一次 T4 AI 判断的补充证据。
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
    """Resolve overlapping claims by confidence; ties remain unknown."""

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
    return {**raw, "unit_id": "unknown_unit", "demotion_reason": reason}


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
