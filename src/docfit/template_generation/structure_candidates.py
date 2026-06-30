from __future__ import annotations

import re
from typing import Any

from docfit.core.io import now_iso, sha256_json
from docfit.template_model import units as template_units

from .constants import (
    COPY_ONLY_DEFAULT_UNIT_IDS,
    FILLABLE_CONTENT_UNIT_IDS,
    FILLABLE_LABELS,
    FILLABLE_MARKERS,
    GENERATED_MARKERS,
    INSTRUCTION_MARKERS,
    MANUAL_ONLY_MARKERS,
    UNIT_DEFINITION_NAMES,
    UNIT_DEFINITIONS,
)
from .text_utils import _normalize_for_match, _normalize_text, _strip_format_annotations


BOUNDARY_SCORE_THRESHOLD = 2
CORE_REQUIRED_UNIT_IDS = {"body_main"}


def build_template_structure_candidates(source_tree: dict[str, Any]) -> dict[str, Any]:
    entries = _body_entries(source_tree)
    inference = _infer_units(entries, source_tree)
    units = inference["units"]
    open_questions = inference["open_questions"]
    result = {
        "artifact_type": "template_structure_candidates",
        "artifact_version": "1.1",
        "producer": {"name": "docfit-template-generate", "version": "0.2.0"},
        "created_at": now_iso(),
        "source_template_hash": source_tree.get("metadata", {}).get(
            "source_template_hash"
        ),
        "input_hashes": {"source_template_tree": sha256_json(source_tree)},
        "discovery_method": "deterministic_multi_signal_boundary_detector",
        "source_context": _source_context_from_source_tree(source_tree),
        "units": units,
        "unknowns": _rule_unknowns(source_tree, units),
        "open_questions": open_questions,
        "taxonomy_review_queue": inference.get("taxonomy_review_queue", []),
    }
    debug = {
        "t2_derived_signals_by_source_seq": _t2_derived_signals_by_source_seq(entries),
    }
    toc_blocks = inference.get("toc_blocks")
    if toc_blocks:
        debug["toc_blocks"] = toc_blocks
    state_machine_trace = inference.get("state_machine_trace")
    if state_machine_trace:
        debug["state_machine_trace"] = state_machine_trace
    result["debug"] = debug
    t2_input = inference.get("t2_input")
    if t2_input is not None:
        result["t2_input"] = t2_input
    return result


def infer_template_rules(source_tree: dict[str, Any]) -> dict[str, Any]:
    return build_template_structure_candidates(source_tree)


def _body_entries(source_tree: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for item in source_tree.get("layers", {}).get("body_flow", []):
        if item.get("structure_layer") != "body_flow":
            continue
        if item.get("text"):
            entries.append(item)
    return _with_synthetic_content_control_toc_entries(entries, source_tree)


def _with_synthetic_content_control_toc_entries(
    entries: list[dict[str, Any]],
    source_tree: dict[str, Any],
) -> list[dict[str, Any]]:
    if _has_visible_catalog_title(entries, "toc"):
        return entries
    toc_control = _main_toc_content_control(source_tree)
    if toc_control is None:
        return entries
    toc_field = _main_toc_field(source_tree)
    insert_index = _first_catalog_or_body_index(entries)
    if insert_index is None:
        return entries
    source_ref = toc_field.get("source_ref") if toc_field else toc_control.get("source_ref")
    synthetic = {
        "structure_layer": "body_flow",
        "source_ref": source_ref,
        "text": "目录",
        "order": _synthetic_order_before(entries[insert_index], insert_index),
        "style": "content_control_toc",
        "style_details": {
            "paragraph": {"alignment": "center", "style_name": "content_control_toc"},
            "dominant_run": {"font_size_pt": 16.0, "bold": True},
        },
        "synthetic": True,
        "synthetic_kind": "content_control_toc",
        "source_evidence": {
            "kind": "content_control",
            "source_ref": toc_control.get("source_ref"),
            "field_source_ref": toc_field.get("source_ref") if toc_field else None,
        },
    }
    return [*entries[:insert_index], synthetic, *entries[insert_index:]]


def _has_visible_catalog_title(entries: list[dict[str, Any]], unit_id: str) -> bool:
    return any(
        _toc_title_like(entry) and _list_title_unit_id(entry) == unit_id
        for entry in entries
    )


def _main_toc_content_control(source_tree: dict[str, Any]) -> dict[str, Any] | None:
    for item in source_tree.get("data", {}).get("content_controls", []) or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "")
        normalized = _normalize_for_match(text)
        if not normalized.startswith("目录"):
            continue
        markers = ("摘要", "abstract", "图目录", "表目录", "参考文献")
        if sum(1 for marker in markers if marker in normalized) >= 3:
            return item
    return None


def _main_toc_field(source_tree: dict[str, Any]) -> dict[str, Any] | None:
    for item in source_tree.get("data", {}).get("fields", []) or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("field_type") or "").upper() != "TOC":
            continue
        instruction = str(item.get("instruction") or "")
        if r"\c" in instruction:
            continue
        return item
    return None


def _first_catalog_or_body_index(entries: list[dict[str, Any]]) -> int | None:
    for index, entry in enumerate(entries):
        if _toc_title_like(entry) and _list_title_unit_id(entry) in {
            "figure_list",
            "table_list",
        }:
            return index
    body_index = _first_body_like_index(entries)
    if body_index is not None:
        return body_index
    return len(entries) if entries else None


def _synthetic_order_before(entry: dict[str, Any], index: int) -> float:
    try:
        return float(entry.get("order")) - 0.5
    except (TypeError, ValueError):
        return float(index) - 0.5


def _source_context_from_source_tree(source_tree: dict[str, Any]) -> dict[str, Any]:
    data = source_tree.get("data", {})
    layers = source_tree.get("layers", {})
    indexes = source_tree.get("indexes", {})
    return {
        "source_template_tree_ref": "source_template_tree.json",
        "body_order": indexes.get("body_order", []),
        "body_flow": layers.get("body_flow", []),
        "by_source_ref": indexes.get("by_source_ref", {}),
        "by_source_seq": indexes.get("by_source_seq", {}),
        "style_inventory": _style_inventory_from_source_tree(source_tree),
        "numbering_definitions": layers.get("package_global", {}).get(
            "numbering_definitions",
            data.get("numbering_definitions", []),
        ),
        "numbering_refs": data.get("numbering_refs", []),
        "section_rules": layers.get("section_rules", []),
        "header_footer": layers.get("header_footer", []),
        "unknown_objects": layers.get("unknown_objects", []),
        "warnings": source_tree.get("warnings", []),
        "paragraphs": data.get("paragraphs", []),
    }


def _style_inventory_from_source_tree(source_tree: dict[str, Any]) -> list[dict[str, Any]]:
    styles: dict[str, dict[str, Any]] = {}
    for paragraph in source_tree.get("data", {}).get("paragraphs", []):
        style = paragraph.get("style")
        if not style:
            continue
        styles.setdefault(str(style), {"name": style, "count": 0})
        styles[str(style)]["count"] += 1
    return list(styles.values())


def _infer_units(
    entries: list[dict[str, Any]],
    source_tree: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not entries:
        unit = _empty_body_main_unit()
        open_questions = _assign_question_ids(
            [
                _required_missing_question(
                    "body_main",
                    entries=[],
                    reason="no visible body entries were available for unit discovery",
                )
            ]
        )
        return {
            "units": [unit],
            "open_questions": open_questions,
            "t2_input": _t2_input_projection(source_tree or {}, entries, [unit], open_questions),
        }

    source_tree = source_tree or {}
    context = _boundary_context(source_tree)
    boundary_result = _boundary_anchors(entries, context)
    label_result = _label_boundaries(boundary_result["anchors"])
    zone_result = _reconcile_document_zones(label_result["anchors"])
    anchors = zone_result["anchors"]
    open_questions = list(label_result["open_questions"])
    open_questions.extend(
        _candidate_open_question(candidate)
        for candidate in boundary_result["candidates"]
    )
    taxonomy_review_queue = list(label_result.get("taxonomy_review_queue", []))

    units: list[dict[str, Any]] = []
    for anchor_index, anchor in enumerate(anchors):
        start_index = int(anchor["entry_index"])
        next_start = (
            int(anchors[anchor_index + 1]["entry_index"])
            if anchor_index + 1 < len(anchors)
            else len(entries)
        )
        region_end = _unit_region_end_index(anchor, next_start, len(entries))
        region_entries = entries[start_index:region_end]
        unit_id = anchor["unit_id"]
        region_source_refs = [
            str(entry.get("source_ref"))
            for entry in region_entries
            if entry.get("source_ref")
        ]
        region_source_seq_refs = _source_seq_refs_for_entries(region_entries)
        page = _mechanical_page_policy_for_unit(
            anchor,
            region_entries,
            previous_entry=entries[start_index - 1] if start_index > 0 else None,
            context=context,
        )
        units.append(
            {
                "unit_id": unit_id,
                "name": anchor["name"],
                "order": (anchor_index + 1) * 10,
                "status": "required",
                "label_status": anchor.get("label_status"),
                "canonical_label_id": anchor.get("canonical_label_id"),
                "raw_title": anchor.get("raw_title"),
                "normalized_title": anchor.get("normalized_title"),
                "display_name": anchor.get("display_name"),
                "candidate_policy": _unit_policy(unit_id),
                "source_refs": region_source_refs or [anchor["source_ref"]],
                "source_seq_refs": region_source_seq_refs,
                "source_range": {
                    "start_source_ref": region_source_refs[0] if region_source_refs else anchor["source_ref"],
                    "end_source_ref": region_source_refs[-1] if region_source_refs else anchor["source_ref"],
                    "source_refs": region_source_refs or [anchor["source_ref"]],
                },
                "source_seq_range": _source_seq_range(region_source_seq_refs),
                "anchors": [
                    {
                        "source_ref": anchor.get("source_ref"),
                        "source_seq": anchor.get("source_seq"),
                        "text": anchor.get("text", ""),
                        "confidence": anchor.get("confidence", "medium"),
                        "score": anchor.get("score"),
                        "signals": anchor.get("signals", []),
                    }
                ],
                "responsibility_evidence": [
                    {
                        "kind": "default_unit_policy",
                        "value": _unit_policy(unit_id),
                    }
                ],
                "conflicts": [],
                "confidence": anchor.get("confidence", "medium"),
                "variant_block_detected": _region_has_variant_marker(region_entries),
                "form_block_detected": _looks_like_form_block(anchor, region_entries),
                "flags": list(anchor.get("flags", [])),
                "evidence": _unit_boundary_evidence(anchor),
                "boundary_score": anchor.get("score"),
                "boundary_signals": anchor.get("signals", []),
                "container": _unit_container(region_entries),
                "page": page,
                "elements": _copy_only_unit_elements(anchor, region_entries)
                if _unit_is_copy_only_by_default(unit_id)
                else _infer_elements(anchor, region_entries),
            }
        )

    open_questions.extend(_missing_required_questions(units, entries))
    open_questions = _assign_question_ids(open_questions)
    result: dict[str, Any] = {
        "units": units,
        "open_questions": open_questions,
        "taxonomy_review_queue": taxonomy_review_queue,
        "toc_blocks": boundary_result.get("toc_blocks", []),
        "state_machine_trace": zone_result.get("trace", []),
    }
    if open_questions:
        result["t2_input"] = _t2_input_projection(
            source_tree,
            entries,
            units,
            open_questions,
        )
    return result


def _unit_region_end_index(
    anchor: dict[str, Any],
    next_start: int,
    total_entries: int,
) -> int:
    """Return the exclusive unit end, honoring locked block ranges when present."""
    block_range = anchor.get("block_range") or {}
    block_end = _int_or_none(block_range.get("end_index"))
    start = _int_or_none(anchor.get("entry_index"))
    if block_end is None or start is None or block_end < start:
        return next_start
    return min(next_start, block_end + 1, total_entries)


def _empty_body_main_unit() -> dict[str, Any]:
    return {
        "unit_id": "body_main",
        "name": "正文",
        "order": 10,
        "status": "required",
        "candidate_policy": "fill",
        "source_refs": [],
        "source_seq_refs": [],
        "source_range": {},
        "source_seq_range": {},
        "anchors": [],
        "responsibility_evidence": [],
        "conflicts": [],
        "confidence": "low",
        "flags": [
            {
                "flag_id": "body_main.required_missing",
                "type": "required_unit_missing",
                "status": "UNKNOWN",
                "affected_ids": ["body_main"],
                "reason": "no visible source range could be assigned to required unit body_main",
            }
        ],
        "evidence": [],
        "elements": [],
    }


def _mechanical_page_policy_for_unit(
    anchor: dict[str, Any],
    region_entries: list[dict[str, Any]],
    *,
    previous_entry: dict[str, Any] | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Translate OOXML break facts near a unit boundary into unit page policy."""
    if not region_entries:
        return {}

    first_entry = region_entries[0]
    first_source_ref = str(
        first_entry.get("source_ref") or anchor.get("source_ref") or ""
    )
    first_paragraph_index = _paragraph_index_from_source_ref(first_source_ref)
    page_refs: list[str] = []
    section_refs: list[str] = []

    paragraph = (first_entry.get("style_details") or {}).get("paragraph") or {}
    if paragraph.get("page_break_before") and first_source_ref:
        page_refs.append(f"{first_source_ref}/pageBreakBefore")

    break_items_by_paragraph = context.get("break_items_by_paragraph", {})
    for paragraph_index in _boundary_scan_paragraph_indices(
        first_paragraph_index,
        previous_entry,
    ):
        for item in break_items_by_paragraph.get(paragraph_index, []):
            kind = str(item.get("kind") or "")
            source_ref = str(item.get("source_ref") or "")
            if not source_ref:
                continue
            if kind == "break" and str(item.get("type") or "").lower() == "page":
                page_refs.append(source_ref)
            elif kind == "section":
                section_refs.append(source_ref)

    page_refs = _dedupe_str(page_refs)
    section_refs = _dedupe_str(section_refs)
    evidence_refs = _dedupe_str([*page_refs, *section_refs])
    if not evidence_refs:
        return {}

    enforcement_hint = "section_break" if section_refs and not page_refs else "page_break"
    page: dict[str, Any] = {
        "page_policy": {
            "mechanical": {
                "has_explicit_break": True,
                "page_break_evidence_refs": page_refs,
                "section_break_evidence_refs": section_refs,
            },
            "observed": {},
            "generation_policy": {
                "requires_new_page": True,
                "source": "mechanical_fact",
                "confidence": "high",
                "enforcement_hint": enforcement_hint,
                "evidence_refs": evidence_refs,
            },
        }
    }
    if page_refs:
        page["page_break"] = "是"
    if section_refs:
        page["section_isolation"] = "是"
    return page


def _boundary_scan_paragraph_indices(
    first_paragraph_index: int | None,
    previous_entry: dict[str, Any] | None,
) -> list[int]:
    if first_paragraph_index is None:
        return []
    previous_paragraph_index = _paragraph_index_from_source_ref(
        str((previous_entry or {}).get("source_ref") or "")
    )
    if previous_paragraph_index is None:
        return []
    start = min(previous_paragraph_index, first_paragraph_index)
    end = max(previous_paragraph_index, first_paragraph_index) - 1
    if end < start:
        return []
    return list(range(start, end + 1))


def _boundary_context(source_tree: dict[str, Any]) -> dict[str, Any]:
    data = source_tree.get("data", {})
    breaks = list(data.get("breaks", []))
    page_break_paragraphs = {
        int(item["paragraph_index"])
        for item in breaks
        if item.get("paragraph_index") is not None
        and item.get("kind") == "break"
        and str(item.get("type") or "").lower() == "page"
    }
    section_break_paragraphs = {
        int(item["paragraph_index"])
        for item in breaks
        if item.get("paragraph_index") is not None
        and item.get("kind") == "section"
    }
    break_refs_by_paragraph: dict[int, list[str]] = {}
    break_items_by_paragraph: dict[int, list[dict[str, Any]]] = {}
    for item in breaks:
        paragraph_index = _int_or_none(item.get("paragraph_index"))
        if paragraph_index is None:
            continue
        break_refs_by_paragraph.setdefault(paragraph_index, []).append(
            str(item.get("source_ref") or "")
        )
        break_items_by_paragraph.setdefault(paragraph_index, []).append(item)
    return {
        "page_break_paragraphs": page_break_paragraphs,
        "section_break_paragraphs": section_break_paragraphs,
        "break_refs_by_paragraph": break_refs_by_paragraph,
        "break_items_by_paragraph": break_items_by_paragraph,
    }


def _boundary_anchors(
    entries: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, Any]:
    blocks = _segment_toc_blocks(entries)
    locked = _locked_indices(blocks)

    boundaries: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if index in locked:
            continue
        decision = _boundary_decision(entry, index, context)
        if decision["is_boundary"]:
            boundaries.append(decision)
        elif decision.get("is_candidate"):
            candidates.append(decision)

    for block in blocks:
        boundaries.append(_toc_block_anchor(entries, block))

    if 0 not in locked and not any(anchor["entry_index"] == 0 for anchor in boundaries):
        boundaries.insert(0, _document_start_boundary(entries[0]))

    boundaries.extend(_keyword_only_fallback_boundaries(entries, boundaries, locked))
    boundaries.extend(_body_title_block_fallback_boundaries(entries, boundaries, locked))

    if "body_main" not in {
        str(anchor.get("unit_id_hint") or "")
        for anchor in boundaries
    }:
        body_index = _first_body_like_index(entries, locked)
        if body_index is not None:
            boundaries.append(
                _body_main_fallback_boundary(entries[body_index], body_index)
            )

    promoted_indices = {int(anchor["entry_index"]) for anchor in boundaries}
    return {
        "anchors": sorted(
            _dedupe_boundary_anchors(boundaries),
            key=lambda item: (
                int(item["entry_index"]),
                str(item.get("unit_id_hint") or ""),
            ),
        ),
        "candidates": [
            candidate
            for candidate in candidates
            if int(candidate["entry_index"]) not in promoted_indices
        ],
        "toc_blocks": blocks,
    }


def _boundary_decision(
    entry: dict[str, Any],
    index: int,
    context: dict[str, Any],
) -> dict[str, Any]:
    text = str(entry.get("text") or "")
    signals = _structural_signals(entry)
    vetoes = _boundary_vetoes(signals)
    if _is_table_cell(entry):
        # Content inside a table is never a top-level unit boundary.
        vetoes = [*vetoes, "table_cell"]
    normalized_text = _boundary_text(text)
    unit_hint = _unit_for_boundary_text(normalized_text, index)
    if vetoes:
        return {
            "entry_index": index,
            "source_ref": entry.get("source_ref"),
            "source_seq": entry.get("source_seq"),
            "text": text,
            "normalized_text": normalized_text,
            "score": 0,
            "signals": [],
            "vetoes": vetoes,
            "unit_id_hint": unit_hint.get("unit_id"),
            "name_hint": unit_hint.get("name"),
            "is_boundary": False,
            "is_candidate": False,
            "confidence": "low",
        }

    score = 0
    hits: list[dict[str, Any]] = []
    break_evidence = _preceded_by_break(entry, context)
    has_break = bool(break_evidence)
    if has_break:
        score += 3
        hits.append({"kind": "break", "weight": 3, "evidence_refs": break_evidence})
    heading_level = _heading_level(entry)
    has_heading = heading_level is not None
    has_top_heading = heading_level == 1
    if has_heading:
        score += 3 if has_top_heading else 1
        hits.append(
            {
                "kind": "heading_style",
                "weight": 3 if has_top_heading else 1,
                "style": _entry_style_name(entry),
                "level": heading_level,
            }
        )
    has_text_props = bool(
        signals.get("centered") and (signals.get("large_font") or signals.get("bold"))
    )
    if has_text_props:
        # plan §6.5: text_properties is candidate-strength only, never enough
        # to open a top-level unit on its own.
        score += 1
        hits.append(
            {
                "kind": "text_properties",
                "weight": 1,
                "centered": True,
                "large_font": bool(signals.get("large_font")),
                "bold": bool(signals.get("bold")),
                "short_text": bool(signals.get("short_text")),
            }
        )
    has_keyword = bool(unit_hint.get("unit_id"))
    if has_keyword:
        score += 1
        hits.append(
            {
                "kind": "keyword",
                "weight": 1,
                "unit_id": unit_hint["unit_id"],
                "name": unit_hint["name"],
            }
        )
    ambiguous_instruction_title = (
        signals.get("instruction_class") == "ambiguous_instruction_title"
        and not has_keyword
    )

    # A formal top-level boundary requires a level-1 heading style, a labeled
    # heading of any level, or text_properties reinforced by a core/alias
    # keyword or an explicit break (strong_context). A bare sub-heading
    # (level 2+), text_properties alone, a bare keyword, or a bare mechanical
    # break are not enough — they become candidates or label-only (plan §6.5).
    is_boundary = (
        not ambiguous_instruction_title
        and (
            has_top_heading
            or (has_heading and has_keyword)
            or (has_text_props and (has_keyword or has_break))
        )
    )
    is_candidate = (not is_boundary) and (
        has_text_props or has_break or has_heading or ambiguous_instruction_title
    )
    candidate_reason = None
    if is_candidate:
        if ambiguous_instruction_title:
            candidate_reason = "ambiguous_instruction_title"
        elif has_heading:
            candidate_reason = "subheading_only"
        elif has_text_props:
            candidate_reason = "text_properties_only"
        else:
            candidate_reason = "mechanical_break_only"
    return {
        "entry_index": index,
        "source_ref": entry.get("source_ref"),
        "source_seq": entry.get("source_seq"),
        "text": text,
        "normalized_text": normalized_text,
        "score": score,
        "signals": hits,
        "vetoes": [],
        "unit_id_hint": unit_hint.get("unit_id"),
        "name_hint": unit_hint.get("name"),
        "is_boundary": is_boundary,
        "is_candidate": is_candidate,
        "candidate_reason": candidate_reason,
        "confidence": _boundary_confidence(score, hits, unit_hint.get("unit_id")),
    }


def _document_start_boundary(entry: dict[str, Any]) -> dict[str, Any]:
    text = str(entry.get("text") or "")
    unit_hint = _unit_for_boundary_text(_boundary_text(text), 0)
    return {
        "entry_index": 0,
        "source_ref": entry.get("source_ref"),
        "source_seq": entry.get("source_seq"),
        "text": text,
        "normalized_text": _boundary_text(text),
        "score": BOUNDARY_SCORE_THRESHOLD,
        "signals": [{"kind": "document_start", "weight": 2}],
        "vetoes": [],
        "unit_id_hint": unit_hint.get("unit_id"),
        "name_hint": unit_hint.get("name"),
        "is_boundary": True,
        "confidence": "medium",
        "fallback_reason": "document_start",
    }


def _body_main_fallback_boundary(
    entry: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    return {
        "entry_index": index,
        "source_ref": entry.get("source_ref"),
        "source_seq": entry.get("source_seq"),
        "text": entry.get("text", ""),
        "normalized_text": _boundary_text(str(entry.get("text") or "")),
        "score": 0,
        "signals": [{"kind": "required_unit_fallback", "weight": 0}],
        "vetoes": [],
        "unit_id_hint": "body_main",
        "name_hint": UNIT_DEFINITION_NAMES["body_main"],
        "is_boundary": True,
        "confidence": "low",
        "fallback_reason": "required_missing",
    }


def _keyword_only_fallback_boundaries(
    entries: list[dict[str, Any]],
    existing: list[dict[str, Any]],
    locked: set[int] | None = None,
) -> list[dict[str, Any]]:
    locked = locked or set()
    seen_units = {
        str(boundary.get("unit_id_hint") or "")
        for boundary in existing
        if boundary.get("unit_id_hint")
    }
    fallbacks: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if index in locked:
            continue
        signals = _structural_signals(entry)
        if _boundary_vetoes(signals):
            continue
        text = _boundary_text(str(entry.get("text") or ""))
        unit_hint = _unit_for_boundary_text(text, index)
        unit_id = unit_hint.get("unit_id")
        if not unit_id or unit_id in seen_units:
            continue
        if not _is_exact_unit_heading_text(text, str(unit_id)):
            continue
        fallbacks.append(
            {
                "entry_index": index,
                "source_ref": entry.get("source_ref"),
                "source_seq": entry.get("source_seq"),
                "text": entry.get("text", ""),
                "normalized_text": text,
                "score": 1,
                "signals": [
                    {
                        "kind": "keyword_exact_fallback",
                        "weight": 1,
                        "unit_id": unit_id,
                        "name": unit_hint.get("name"),
                    }
                ],
                "vetoes": [],
                "unit_id_hint": unit_id,
                "name_hint": unit_hint.get("name"),
                "is_boundary": True,
                "confidence": "low",
                "fallback_reason": "keyword_exact_heading",
                "flags": [
                    {
                        "flag_id": f"{unit_id}.keyword_only_boundary",
                        "type": "unit_boundary_keyword_only",
                        "status": "UNKNOWN",
                        "source_ref": entry.get("source_ref"),
                        "affected_ids": [str(unit_id)],
                        "reason": "unit boundary uses exact heading keyword fallback without structural signals",
                    }
                ],
            }
        )
        seen_units.add(str(unit_id))
    return fallbacks


def _body_title_block_fallback_boundaries(
    entries: list[dict[str, Any]],
    existing: list[dict[str, Any]],
    locked: set[int] | None = None,
) -> list[dict[str, Any]]:
    locked = locked or set()
    if any(str(boundary.get("unit_id_hint") or "") == "body_title_block" for boundary in existing):
        return []

    toc_end = _last_anchor_index(existing, "toc")
    abstract_start = _first_anchor_index(existing, "abstract_cn")
    if toc_end is None or abstract_start is None or toc_end >= abstract_start:
        return []

    window = [
        (index, entries[index])
        for index in range(toc_end + 1, abstract_start)
        if index not in locked
    ]
    if not window:
        return []

    start: int | None = None
    has_title = False
    has_student = False
    has_tutor = False
    for index, entry in window:
        normalized = _normalize_for_match(str(entry.get("text") or ""))
        if not normalized:
            continue
        if start is None and (
            "正文基本格式" in normalized
            or "毕业论文设计中文题目" in normalized
            or "毕业论文中文题目" in normalized
        ):
            start = index
        if "毕业论文设计中文题目" in normalized or "毕业论文中文题目" in normalized:
            has_title = True
        if normalized.startswith("学生") or "学生" in normalized[:8]:
            has_student = True
        if normalized.startswith("指导老师") or normalized.startswith("指导教师"):
            has_tutor = True

    if start is None or not (has_title and has_student and has_tutor):
        return []

    entry = entries[start]
    return [
        {
            "entry_index": start,
            "source_ref": entry.get("source_ref"),
            "source_seq": entry.get("source_seq"),
            "text": entry.get("text", ""),
            "normalized_text": _boundary_text(str(entry.get("text") or "")),
            "score": 1,
            "signals": [
                {
                    "kind": "body_title_block_fallback",
                    "weight": 1,
                    "evidence": {
                        "has_title": has_title,
                        "has_student": has_student,
                        "has_tutor": has_tutor,
                    },
                }
            ],
            "vetoes": [],
            "unit_id_hint": "body_title_block",
            "name_hint": UNIT_DEFINITION_NAMES["body_title_block"],
            "is_boundary": True,
            "confidence": "medium",
            "fallback_reason": "body_title_block_between_toc_and_abstract",
            "flags": [
                {
                    "flag_id": "body_title_block.fallback_boundary",
                    "type": "unit_boundary_fallback",
                    "status": "UNKNOWN",
                    "source_ref": entry.get("source_ref"),
                    "affected_ids": ["body_title_block"],
                    "reason": (
                        "正文题名信息缺少显式标题，按目录后、摘要前的题名/学生/指导老师"
                        "证据切分"
                    ),
                }
            ],
        }
    ]


def _last_anchor_index(boundaries: list[dict[str, Any]], unit_id: str) -> int | None:
    matches = [
        int(boundary["entry_index"])
        for boundary in boundaries
        if str(boundary.get("unit_id_hint") or "") == unit_id
    ]
    return max(matches) if matches else None


def _first_anchor_index(boundaries: list[dict[str, Any]], unit_id: str) -> int | None:
    matches = [
        int(boundary["entry_index"])
        for boundary in boundaries
        if str(boundary.get("unit_id_hint") or "") == unit_id
    ]
    return min(matches) if matches else None


def _is_exact_unit_heading_text(text: str, unit_id: str) -> bool:
    normalized = _normalize_for_match(text)
    if not normalized or len(normalized) > 24:
        return False
    exact_by_unit = {
        "toc": {"目录", "目錄"},
        "figure_list": {"图目录", "listoffigures"},
        "table_list": {"表目录", "listoftables"},
        "body_title_block": {"正文题名信息"},
        "abstract_cn": {"摘要", "摘要关键词", "摘要关键字"},
        "abstract_en": {"abstract", "title", "keywords", "keywordsabstract", "abstractkeywords"},
        "body_main": {"正文", "绪论", "前言", "第一章"},
        "references": {"参考文献", "references"},
        "academic_achievements": {"相关的学术成果目录", "学术成果目录", "博士期间工作成果"},
        "acknowledgement": {"致谢", "acknowledgement"},
        "appendix": {"附录", "appendix"},
        "copyright_notice": {"版权声明"},
        "originality_authorization_statement": {"原创性声明和使用授权说明", "北京大学学位论文原创性声明和使用授权说明"},
        "originality_statement": {"原创性声明", "南京农业大学本科生毕业论文设计原创性声明"},
        "authorization_statement": {"使用授权声明", "使用授权说明", "南京农业大学本科生毕业论文设计使用授权声明"},
        "integrity_statement": {"诚信声明"},
        "design_task": {"毕业设计任务书", "毕业论文任务书", "任务书"},
        "proposal": {"开题报告"},
        "proposal_record": {"开题论证记录表"},
        "defense_record": {"答辩记录表"},
        "topic_change_approval": {"题目变更审批表", "课题变更审批表", "选题变更审批表"},
        "grade_form": {"成绩评定表"},
        "post_forms": {"评审表"},
    }
    allowed = exact_by_unit.get(unit_id, set())
    if normalized in allowed:
        return True
    if unit_id == "body_main":
        return bool(re.match(r"^(?:第[一二三四五六七八九十0-9]+章|[0-9]+[\.\u3001]?\S{1,12})$", normalized))
    return False


def _dedupe_boundary_anchors(boundaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for boundary in boundaries:
        key = (int(boundary.get("entry_index") or 0), str(boundary.get("unit_id_hint") or ""))
        if key in seen:
            continue
        deduped.append(boundary)
        seen.add(key)
    return deduped


# --- label model: core closed-set + alias + custom_unit (plan §6.7) ---------

# Exact (canonical-normalized) title -> core unit_id. This is the alias
# registry: known title variants that resolve to a closed-set unit.
_CORE_ALIAS_EXACT = {
    "目录": "toc",
    "目錄": "toc",
    "图目录": "figure_list",
    "圖目錄": "figure_list",
    "插图目录": "figure_list",
    "listoffigures": "figure_list",
    "tableoffigures": "figure_list",
    "表目录": "table_list",
    "表目錄": "table_list",
    "附表目录": "table_list",
    "listoftables": "table_list",
    "tableoftables": "table_list",
    "contents": "toc",
    "tableofcontents": "toc",
    "正文题名信息": "body_title_block",
    "摘要": "abstract_cn",
    "中文摘要": "abstract_cn",
    "摘要关键词": "abstract_cn",
    "摘要及关键词": "abstract_cn",
    "abstract": "abstract_en",
    "englishabstract": "abstract_en",
    "title": "abstract_en",
    "keywords": "abstract_en",
    "keyword": "abstract_en",
    "参考文献": "references",
    "references": "references",
    "reference": "references",
    "相关的学术成果目录": "academic_achievements",
    "学术成果目录": "academic_achievements",
    "博士期间工作成果": "academic_achievements",
    "致谢": "acknowledgement",
    "acknowledgement": "acknowledgement",
    "acknowledgements": "acknowledgement",
    "附录": "appendix",
    "appendix": "appendix",
    "appendices": "appendix",
    "版权声明": "copyright_notice",
    "原创性声明和使用授权说明": "originality_authorization_statement",
    "北京大学学位论文原创性声明和使用授权说明": "originality_authorization_statement",
    "原创性声明": "originality_statement",
    "学位论文原创性声明": "originality_statement",
    "南京农业大学本科生毕业论文设计原创性声明": "originality_statement",
    "使用授权声明": "authorization_statement",
    "使用授权说明": "authorization_statement",
    "南京农业大学本科生毕业论文设计使用授权声明": "authorization_statement",
    "诚信声明": "integrity_statement",
    "诚 信 声 明": "integrity_statement",
    "毕业设计任务书": "design_task",
    "毕业论文任务书": "design_task",
    "开题报告": "proposal",
    "开题论证记录表": "proposal_record",
    "答辩记录表": "defense_record",
    "题目变更审批表": "topic_change_approval",
    "题目变更": "topic_change_approval",
    "课题变更审批表": "topic_change_approval",
    "选题变更审批表": "topic_change_approval",
    "成绩评定表": "grade_form",
}


def canonical_title(text: str) -> str:
    """Normalize a heading for label matching (plan §6.7)."""
    return _normalize_for_match(text)


def _display_title(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", _strip_format_annotations(str(text or ""))).strip()
    cleaned = re.sub(r"\s*(?:…|\.|．|·|•){2,}.*$", "", cleaned).strip()
    return cleaned or "模板单元"


def _alias_unit_id(normalized: str) -> str | None:
    if not normalized:
        return None
    if normalized in _CORE_ALIAS_EXACT:
        return _CORE_ALIAS_EXACT[normalized]
    if normalized.startswith(("englishtitle", "titleofyourthesis")):
        return "abstract_en"
    if "博士期间工作成果" in normalized or "学术成果" in normalized:
        return "academic_achievements"
    if normalized.startswith(("附录", "appendix")):
        return "appendix"
    if normalized.startswith(("参考文献", "references")):
        return "references"
    return None


def _boundary_has_structural_evidence(boundary: dict[str, Any]) -> bool:
    kinds = {str(signal.get("kind")) for signal in boundary.get("signals", [])}
    return bool(kinds & {"heading_style", "break", "text_properties", "toc_block"})


def _classify_core_label(
    boundary: dict[str, Any],
    normalized_title: str,
) -> tuple[str, str, str, str] | None:
    """Resolve a boundary to a core/alias unit; None when unmatched."""
    hint = boundary.get("unit_id_hint")
    if hint:
        unit_id = str(hint)
        status = (
            "core_matched"
            if _is_exact_unit_heading_text(str(boundary.get("text") or ""), unit_id)
            else "alias_matched"
        )
        name = str(boundary.get("name_hint") or UNIT_DEFINITION_NAMES.get(unit_id, unit_id))
        return unit_id, name, status, unit_id
    alias = _alias_unit_id(normalized_title)
    if alias:
        return alias, UNIT_DEFINITION_NAMES.get(alias, alias), "alias_matched", alias
    if boundary.get("fallback_reason") == "document_start":
        return "cover", UNIT_DEFINITION_NAMES["cover"], "core_matched", "cover"
    return None


def _custom_unit_fields(
    boundary: dict[str, Any],
    normalized_title: str,
    display_name: str,
) -> tuple[str, str, str, None]:
    slug = re.sub(r"\s+", "", normalized_title)[:16] or "unit"
    unit_id = f"custom:template:{slug}:{boundary.get('source_seq')}"
    return unit_id, display_name, "custom_detected", None


def _label_boundaries(boundaries: list[dict[str, Any]]) -> dict[str, Any]:
    anchors: list[dict[str, Any]] = []
    open_questions: list[dict[str, Any]] = []
    taxonomy_review_queue: list[dict[str, Any]] = []
    seen_unit_ids: set[str] = set()
    for boundary in boundaries:
        raw_title = str(boundary.get("text") or "")
        normalized_title = canonical_title(raw_title)
        display_name = _display_title(raw_title)
        flags = list(boundary.get("flags", []))
        confidence = str(boundary.get("confidence") or "medium")
        strong = _boundary_has_structural_evidence(boundary) and confidence in {
            "high",
            "medium",
        }

        core = _classify_core_label(boundary, normalized_title)
        canonical_label_id: str | None = None
        is_custom = False
        if core is not None and not (
            core[0] in seen_unit_ids and core[0] != "other"
        ):
            unit_id, name, label_status, canonical_label_id = core
            seen_unit_ids.add(unit_id)
        elif strong:
            # Strong boundary with no usable closed-set label (unknown section,
            # or a repeated core section such as a second form/chapter) becomes a
            # custom_unit instead of being discarded into `other` (plan §6.7).
            unit_id, name, label_status, canonical_label_id = _custom_unit_fields(
                boundary, normalized_title, display_name
            )
            is_custom = True
            if core is not None:
                flags.append(
                    {
                        "flag_id": f"{core[0]}.repeated_as_custom",
                        "type": "unit_label_repeated_custom",
                        "status": "UNKNOWN",
                        "source_ref": boundary.get("source_ref"),
                        "affected_ids": [unit_id],
                        "reason": (
                            f"core label {core[0]} already used; this repeated "
                            "section is held as a custom_unit pending review"
                        ),
                    }
                )
        else:
            unit_id = "other"
            name = display_name if len(display_name) <= 24 else "其他模板单元"
            label_status = "unmapped" if core is None else "candidate_only"
            confidence = "low"
            flags.append(
                {
                    "flag_id": f"other.{boundary.get('source_seq') or boundary.get('entry_index')}.label_unknown",
                    "type": "unit_label_unknown",
                    "status": "UNKNOWN",
                    "source_ref": boundary.get("source_ref"),
                    "affected_ids": ["other"],
                    "reason": "boundary was detected but closed-set unit_id label was not confident",
                }
            )
            open_questions.append(_label_open_question(boundary, flags[-1]))

        anchor = {
            **boundary,
            "unit_id": unit_id,
            "name": name,
            "confidence": confidence,
            "flags": flags,
            "label_status": label_status,
            "canonical_label_id": canonical_label_id,
            "raw_title": raw_title,
            "normalized_title": normalized_title,
            "display_name": display_name,
        }
        anchors.append(anchor)
        if is_custom:
            taxonomy_review_queue.append(_taxonomy_review_entry(anchor))
        if confidence != "high":
            open_questions.append(_boundary_open_question(anchor))
    return {
        "anchors": anchors,
        "open_questions": open_questions,
        "taxonomy_review_queue": taxonomy_review_queue,
    }


FRONT_MATTER_UNIT_IDS = {
    "cover",
    "integrity_statement",
    "copyright_notice",
    "originality_statement",
    "authorization_statement",
    "originality_authorization_statement",
    "abstract_cn",
    "abstract_en",
    "toc",
    "figure_list",
    "table_list",
    "body_title_block",
}

BACK_MATTER_UNIT_IDS = {
    "references",
    "appendix",
    "academic_achievements",
    "acknowledgement",
    "originality_statement",
    "authorization_statement",
    "originality_authorization_statement",
    "design_task",
    "proposal",
    "proposal_record",
    "defense_record",
    "topic_change_approval",
    "grade_form",
}

BODY_ABSORBABLE_UNIT_IDS = {"body_main", "toc", "figure_list", "table_list"}


def _reconcile_document_zones(anchors: list[dict[str, Any]]) -> dict[str, Any]:
    final: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    state = "front_matter"
    body_ready = False

    for index, anchor in enumerate(anchors):
        unit_id = str(anchor.get("unit_id") or "")
        canonical_unit_id = _canonical_unit_for_anchor(anchor) or unit_id

        if state == "front_matter":
            if canonical_unit_id == "abstract_en" and not _has_future_canonical_anchor(
                anchors,
                index,
                "abstract_en",
            ):
                body_ready = True
            elif (
                canonical_unit_id in {"toc", "figure_list", "table_list"}
                and not _has_future_canonical_anchor(anchors, index, "abstract_cn")
                and not _has_future_canonical_anchor(anchors, index, "abstract_en")
            ):
                body_ready = True
            if (
                final
                and canonical_unit_id in FRONT_MATTER_UNIT_IDS
                and _canonical_unit_for_anchor(final[-1]) == canonical_unit_id
            ):
                trace.append(
                    _zone_trace(
                        anchor,
                        "front_matter",
                        "front_matter",
                        final[-1],
                        "absorb_front_matter_continuation",
                    )
                )
                continue
            if (
                final
                and not body_ready
                and _custom_front_matter_continues_previous(
                    anchor,
                    final[-1],
                    canonical_unit_id,
                )
            ):
                trace.append(
                    _zone_trace(
                        anchor,
                        "front_matter",
                        "front_matter",
                        final[-1],
                        "absorb_front_matter_custom_continuation",
                    )
                )
                continue
            if unit_id == "body_main" or (
                body_ready
                and _custom_anchor_can_start_body_main(anchor, canonical_unit_id)
            ):
                body_anchor = (
                    anchor
                    if unit_id == "body_main"
                    else _relabel_anchor(anchor, "body_main", "start_body_main")
                )
                final.append(body_anchor)
                state = "body_main"
                trace.append(
                    _zone_trace(anchor, "front_matter", state, body_anchor, "start_body_main")
                )
                continue
            final.append(anchor)
            continue

        if state == "body_main":
            if _is_references_inside_body(anchors, index):
                trace.append(
                    _zone_trace(
                        anchor,
                        "body_main",
                        "body_main",
                        final[-1] if final else anchor,
                        "absorb_internal_references_heading",
                    )
                )
                continue
            if canonical_unit_id in BACK_MATTER_UNIT_IDS:
                relabeled = (
                    _relabel_anchor(anchor, canonical_unit_id, "start_back_matter_unit")
                    if canonical_unit_id != unit_id
                    else anchor
                )
                final.append(relabeled)
                state = "back_matter"
                trace.append(
                    _zone_trace(
                        anchor,
                        "body_main",
                        state,
                        relabeled,
                        "start_back_matter_unit",
                    )
                )
                continue
            if unit_id in BODY_ABSORBABLE_UNIT_IDS or _is_custom_unit_id(unit_id):
                trace.append(
                    _zone_trace(
                        anchor,
                        "body_main",
                        "body_main",
                        final[-1] if final else anchor,
                        "absorb_into_body_main",
                    )
                )
                continue
            final.append(anchor)
            continue

        if state == "back_matter":
            if unit_id in BODY_ABSORBABLE_UNIT_IDS or _is_custom_unit_id(unit_id):
                trace.append(
                    _zone_trace(
                        anchor,
                        "back_matter",
                        "back_matter",
                        final[-1] if final else anchor,
                        "absorb_after_back_matter",
                    )
                )
                continue
            if (
                final
                and _canonical_unit_for_anchor(final[-1])
                == "originality_authorization_statement"
                and canonical_unit_id
                in {
                    "originality_authorization_statement",
                    "originality_statement",
                    "authorization_statement",
                }
            ):
                trace.append(
                    _zone_trace(
                        anchor,
                        "back_matter",
                        "back_matter",
                        final[-1],
                        "absorb_declaration_continuation",
                    )
                )
                continue
            if (
                unit_id == "originality_statement"
                and any(str(prev.get("unit_id")) == "acknowledgement" for prev in final[-2:])
            ):
                relabeled = _relabel_anchor(
                    anchor,
                    "originality_authorization_statement",
                    "back_matter_declaration_merge",
                )
                final.append(relabeled)
                trace.append(
                    _zone_trace(
                        anchor,
                        "back_matter",
                        "back_matter",
                        relabeled,
                        "back_matter_declaration_merge",
                    )
                )
                continue
            final.append(anchor)

    return {"anchors": final, "trace": trace}


def _has_future_canonical_anchor(
    anchors: list[dict[str, Any]],
    index: int,
    unit_id: str,
) -> bool:
    for future in anchors[index + 1 :]:
        future_unit_id = _canonical_unit_for_anchor(future) or str(
            future.get("unit_id") or ""
        )
        if future_unit_id == unit_id:
            return True
    return False


def _custom_anchor_can_start_body_main(
    anchor: dict[str, Any],
    canonical_unit_id: str,
) -> bool:
    unit_id = str(anchor.get("unit_id") or "")
    if not _is_custom_unit_id(unit_id) or canonical_unit_id != unit_id:
        return False
    text = str(anchor.get("raw_title") or anchor.get("text") or "")
    normalized = _normalize_for_match(_strip_format_annotations(text))
    if not normalized:
        return False
    if _looks_like_front_matter_continuation_title(normalized):
        return False
    return True


def _custom_front_matter_continues_previous(
    anchor: dict[str, Any],
    previous: dict[str, Any],
    canonical_unit_id: str,
) -> bool:
    unit_id = str(anchor.get("unit_id") or "")
    if not _is_custom_unit_id(unit_id) or canonical_unit_id != unit_id:
        return False
    previous_unit_id = _canonical_unit_for_anchor(previous) or str(
        previous.get("unit_id") or ""
    )
    text = str(anchor.get("raw_title") or anchor.get("text") or "")
    normalized = _normalize_for_match(_strip_format_annotations(text))
    if previous_unit_id == "cover" and _looks_like_cover_continuation(normalized):
        return True
    return previous_unit_id in {"abstract_cn", "abstract_en"} and (
        _looks_like_front_matter_continuation_title(normalized)
        or normalized.startswith(("yourname", "directedby"))
    )


def _looks_like_cover_continuation(normalized_title: str) -> bool:
    if not normalized_title:
        return False
    if normalized_title in {"二〇年月", "年月", "年月日"}:
        return True
    return bool(re.fullmatch(r"[二〇零一二三四五六七八九十0-9]{2,8}年月日?", normalized_title))


def _looks_like_front_matter_continuation_title(normalized_title: str) -> bool:
    return bool(
        re.search(
            r"(?:abstract|keywords?|key\s*words?|title|论文英文题目|英文题目|"
            r"论文题目|中文题目)$",
            normalized_title,
        )
        or any(
            marker in normalized_title
            for marker in (
                "abstract",
                "keywords",
                "keyword",
                "key words",
                "论文英文题目",
                "英文题目",
            )
        )
    )


def _canonical_unit_for_anchor(anchor: dict[str, Any]) -> str | None:
    normalized_title = str(anchor.get("normalized_title") or "")
    alias = _alias_unit_id(normalized_title)
    if alias:
        return alias
    unit_id = str(anchor.get("unit_id") or "")
    if _is_custom_unit_id(unit_id):
        return _alias_unit_id(canonical_title(str(anchor.get("raw_title") or "")))
    return unit_id or None


def _is_references_inside_body(
    anchors: list[dict[str, Any]],
    index: int,
) -> bool:
    if _canonical_unit_for_anchor(anchors[index]) != "references":
        return False
    for future in anchors[index + 1 :]:
        future_canonical = _canonical_unit_for_anchor(future)
        future_unit_id = str(future.get("unit_id") or "")
        if future_canonical in BACK_MATTER_UNIT_IDS - {"references"}:
            return False
        if _is_custom_unit_id(future_unit_id) or future_unit_id == "body_main":
            return True
    return False


def _is_custom_unit_id(unit_id: str) -> bool:
    return unit_id.startswith("custom:")


def _relabel_anchor(
    anchor: dict[str, Any],
    unit_id: str,
    label_status: str,
) -> dict[str, Any]:
    flags = [
        flag
        for flag in anchor.get("flags", [])
        if flag.get("type") != "unit_label_repeated_custom"
    ]
    return {
        **anchor,
        "unit_id": unit_id,
        "name": UNIT_DEFINITION_NAMES.get(unit_id, unit_id),
        "label_status": label_status,
        "canonical_label_id": unit_id,
        "confidence": "medium"
        if anchor.get("confidence") == "low"
        else anchor.get("confidence", "medium"),
        "flags": flags,
    }


def _zone_trace(
    original: dict[str, Any],
    from_state: str,
    to_state: str,
    result: dict[str, Any],
    decision: str,
) -> dict[str, Any]:
    return {
        "source_seq": original.get("source_seq"),
        "raw_title": original.get("raw_title") or original.get("text"),
        "from_state": from_state,
        "to_state": to_state,
        "preliminary_unit_id": original.get("unit_id"),
        "final_unit_id": result.get("unit_id"),
        "decision": decision,
    }


def _taxonomy_review_entry(anchor: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_id": f"taxonomy-{anchor.get('source_seq')}",
        "raw_title": anchor.get("raw_title"),
        "normalized_title": anchor.get("normalized_title"),
        "display_name": anchor.get("display_name"),
        "source_seq": anchor.get("source_seq"),
        "source_ref": anchor.get("source_ref"),
        "suggested_scope": "template",
        "evidence": [
            signal.get("kind") for signal in anchor.get("signals", [])
        ],
        "status": "pending",
    }


def _fallback_unit_name(boundary: dict[str, Any]) -> str:
    text = str(boundary.get("normalized_text") or boundary.get("text") or "").strip()
    if text and len(text) <= 24:
        return text
    return "其他模板单元"


def _boundary_vetoes(signals: dict[str, Any]) -> list[str]:
    vetoes = []
    if signals.get("is_toc_entry"):
        vetoes.append("toc_entry")
    if signals.get("is_spacing_line"):
        vetoes.append("spacing_line")
    if signals.get("instruction_class") == "pure_instruction":
        vetoes.append("instruction_text")
    return vetoes


def _boundary_text(text: str) -> str:
    return _strip_format_annotations(text).strip()


def _unit_for_boundary_text(text: str, index: int) -> dict[str, str | None]:
    unit_id, name = _unit_for_text(text, index)
    return {"unit_id": unit_id, "name": name}


def _preceded_by_break(entry: dict[str, Any], context: dict[str, Any]) -> list[str]:
    source_ref = str(entry.get("source_ref") or "")
    paragraph_index = _paragraph_index_from_source_ref(source_ref)
    paragraph = (entry.get("style_details") or {}).get("paragraph") or {}
    refs: list[str] = []
    if paragraph.get("page_break_before"):
        refs.append(f"{source_ref}/pageBreakBefore")
    if paragraph_index is None:
        return refs
    for candidate_index in (paragraph_index, paragraph_index - 1):
        if candidate_index in context.get("page_break_paragraphs", set()):
            refs.extend(context.get("break_refs_by_paragraph", {}).get(candidate_index, []))
        if candidate_index in context.get("section_break_paragraphs", set()):
            refs.extend(context.get("break_refs_by_paragraph", {}).get(candidate_index, []))
    return _dedupe_str(refs)


def _heading_level(entry: dict[str, Any]) -> int | None:
    style_name = _entry_style_name(entry).strip().lower()
    compact = re.sub(r"\s+", "", style_name)
    for pattern in (
        r"\bheading\s*([1-9])\b",
        r"标题\s*([1-9])",
        r"heading([1-9])",
        r"标题([1-9])",
    ):
        match = re.search(pattern, style_name) or re.search(pattern, compact)
        if match:
            return int(match.group(1))
    return None


def _boundary_confidence(
    score: int,
    hits: list[dict[str, Any]],
    unit_id: Any,
) -> str:
    hit_kinds = {str(hit.get("kind")) for hit in hits}
    if unit_id and (
        ("heading_style" in hit_kinds and "keyword" in hit_kinds)
        or ("heading_style" in hit_kinds and "break" in hit_kinds)
        or ("break" in hit_kinds and "keyword" in hit_kinds and score >= 4)
    ):
        return "high"
    if score >= BOUNDARY_SCORE_THRESHOLD:
        return "medium"
    return "low"


def _unit_boundary_evidence(anchor: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = _element_evidence(
        _unit_policy(str(anchor.get("unit_id") or "")),
        anchor.get("source_ref", ""),
        source_seq=anchor.get("source_seq"),
    )
    for signal in anchor.get("signals", []):
        evidence.append(
            {
                "kind": f"boundary_signal.{signal.get('kind')}",
                "value": signal,
            }
        )
    if anchor.get("vetoes"):
        evidence.append({"kind": "boundary_vetoes", "value": anchor.get("vetoes")})
    return evidence


def _unit_container(entries: list[dict[str, Any]]) -> dict[str, Any]:
    containers = {
        str(entry.get("container_ref") or "")
        for entry in entries
        if entry.get("container_ref")
    }
    if len(containers) != 1:
        return {}
    container_ref = next(iter(containers))
    return {"type": "table", "source_ref": container_ref}


def _missing_required_questions(
    units: list[dict[str, Any]],
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    present = {str(unit.get("unit_id") or "") for unit in units}
    return [
        _required_missing_question(
            unit_id,
            entries=entries,
            reason=f"required unit {unit_id} was not detected with high-confidence boundaries",
        )
        for unit_id in sorted(CORE_REQUIRED_UNIT_IDS - present)
    ]


def _boundary_open_question(anchor: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "boundary",
        "interval": _question_interval(anchor),
        "candidates": [
            {
                "unit_id": anchor.get("unit_id"),
                "name": anchor.get("name"),
                "confidence": anchor.get("confidence"),
            }
        ],
        "signals_summary": _signals_summary(anchor),
        "status": "UNKNOWN",
        "prompt": "Confirm whether this paragraph is a template unit boundary.",
        "visual_refs": [],
    }


def _candidate_open_question(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "boundary_candidate",
        "interval": _question_interval(candidate),
        "candidates": [
            {
                "unit_id": candidate.get("unit_id_hint") or "other",
                "name": candidate.get("name_hint") or _fallback_unit_name(candidate),
                "confidence": "candidate_only",
            }
        ],
        "signals_summary": _signals_summary(candidate),
        "status": "UNKNOWN",
        "prompt": (
            "Weak boundary candidate (text properties only); confirm whether this "
            "starts a top-level template unit."
        ),
        "candidate_reason": candidate.get("candidate_reason"),
        "visual_refs": [],
    }


def _label_open_question(
    boundary: dict[str, Any],
    flag: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "label",
        "interval": _question_interval(boundary),
        "candidates": _unit_candidate_list(),
        "signals_summary": _signals_summary(boundary),
        "status": "UNKNOWN",
        "prompt": "Choose the closed-set unit_id for this detected boundary, or keep other.",
        "reason": flag.get("reason"),
        "visual_refs": [],
    }


def _required_missing_question(
    unit_id: str,
    *,
    entries: list[dict[str, Any]],
    reason: str,
) -> dict[str, Any]:
    return {
        "kind": "required_missing",
        "interval": _whole_document_interval(entries),
        "candidates": [{"unit_id": unit_id, "name": UNIT_DEFINITION_NAMES.get(unit_id, unit_id)}],
        "signals_summary": {"required_unit_id": unit_id, "reason": reason},
        "status": "UNKNOWN",
        "prompt": f"Decide whether required unit {unit_id} is absent or was missed.",
        "visual_refs": [],
    }


def _question_interval(anchor: dict[str, Any]) -> dict[str, Any]:
    source_ref = anchor.get("source_ref")
    source_seq = anchor.get("source_seq")
    return {
        "start_source_ref": source_ref,
        "end_source_ref": source_ref,
        "start_source_seq": source_seq,
        "end_source_seq": source_seq,
    }


def _whole_document_interval(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not entries:
        return {}
    seq_refs = _source_seq_refs_for_entries(entries)
    return {
        "start_source_ref": entries[0].get("source_ref"),
        "end_source_ref": entries[-1].get("source_ref"),
        "start_source_seq": min(seq_refs) if seq_refs else None,
        "end_source_seq": max(seq_refs) if seq_refs else None,
    }


def _signals_summary(anchor: dict[str, Any]) -> dict[str, Any]:
    return {
        "score": anchor.get("score"),
        "threshold": BOUNDARY_SCORE_THRESHOLD,
        "signals": anchor.get("signals", []),
        "vetoes": anchor.get("vetoes", []),
        "confidence": anchor.get("confidence"),
        "fallback_reason": anchor.get("fallback_reason"),
        "text": anchor.get("text"),
        "normalized_text": anchor.get("normalized_text"),
        "source_ref": anchor.get("source_ref"),
        "source_seq": anchor.get("source_seq"),
    }


def _unit_candidate_list() -> list[dict[str, str]]:
    return [
        {"unit_id": unit_id, "name": name}
        for unit_id, name, _needles in UNIT_DEFINITIONS
    ] + [{"unit_id": "other", "name": "其他模板单元"}]


def _assign_question_ids(open_questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assigned = []
    for index, question in enumerate(open_questions, start=1):
        assigned.append({"question_id": f"t2_q_{index:03d}", **question})
    return assigned


def _t2_input_projection(
    source_tree: dict[str, Any],
    entries: list[dict[str, Any]],
    units: list[dict[str, Any]],
    open_questions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "t2_input",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.2.0"},
        "created_at": now_iso(),
        "input_hashes": {"source_template_tree": sha256_json(source_tree)},
        "framework": {
            "required_unit_ids": sorted(CORE_REQUIRED_UNIT_IDS),
            "unit_candidates": _unit_candidate_list(),
            "rules": {
                "boundary_threshold": BOUNDARY_SCORE_THRESHOLD,
                "vetoes": ["toc_entry", "spacing_line", "instruction_text"],
            },
        },
        "confirmed_units": [
            _unit_projection(unit)
            for unit in units
            if unit.get("confidence") == "high"
        ],
        "open_questions": open_questions,
        "contexts": [
            _question_context(question, entries, units)
            for question in open_questions
        ],
        "visual_refs": [],
    }


def _unit_projection(unit: dict[str, Any]) -> dict[str, Any]:
    return {
        "unit_id": unit.get("unit_id"),
        "name": unit.get("name"),
        "confidence": unit.get("confidence"),
        "source_range": unit.get("source_range", {}),
        "source_seq_range": unit.get("source_seq_range", {}),
        "boundary_score": unit.get("boundary_score"),
        "boundary_signals": unit.get("boundary_signals", []),
    }


def _question_context(
    question: dict[str, Any],
    entries: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> dict[str, Any]:
    interval = question.get("interval") or {}
    start = _int_or_none(interval.get("start_source_seq"))
    end = _int_or_none(interval.get("end_source_seq"))
    window_entries = _entries_near_interval(entries, start, end)
    return {
        "question_id": question.get("question_id"),
        "entries": [_entry_projection(entry) for entry in window_entries],
        "current_units": [
            _unit_projection(unit)
            for unit in units
            if _unit_overlaps_interval(unit, start, end)
        ],
    }


def _entries_near_interval(
    entries: list[dict[str, Any]],
    start: int | None,
    end: int | None,
) -> list[dict[str, Any]]:
    if start is None or end is None:
        return entries[:8]
    selected = []
    for index, entry in enumerate(entries):
        seq = _int_or_none(entry.get("source_seq"))
        if seq is None:
            continue
        if start - 2 <= seq <= end + 2:
            selected.append(entry)
    return selected[:12]


def _entry_projection(entry: dict[str, Any]) -> dict[str, Any]:
    signals = _structural_signals(entry)
    return {
        "source_ref": entry.get("source_ref"),
        "source_seq": entry.get("source_seq"),
        "text": entry.get("text"),
        "style": entry.get("style"),
        "style_name": _entry_style_name(entry),
        "structural_signals": {
            key: signals.get(key)
            for key in (
                "centered",
                "bold",
                "large_font",
                "short_text",
                "is_toc_entry",
                "is_spacing_line",
                "looks_like_instruction_text",
                "instruction_class",
            )
        },
        "container_ref": entry.get("container_ref"),
    }


def _unit_overlaps_interval(
    unit: dict[str, Any],
    start: int | None,
    end: int | None,
) -> bool:
    if start is None or end is None:
        return True
    refs = [
        int(ref)
        for ref in unit.get("source_seq_refs", [])
        if _int_or_none(ref) is not None
    ]
    if not refs:
        return False
    return min(refs) <= end and start <= max(refs)


def _unit_is_copy_only_by_default(unit_id: str) -> bool:
    return bool(unit_id) and unit_id in COPY_ONLY_DEFAULT_UNIT_IDS


def _copy_only_unit_elements(
    anchor: dict[str, Any],
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_refs = [
        str(entry.get("source_ref")) for entry in entries if entry.get("source_ref")
    ]
    source_seq_refs = _source_seq_refs_for_entries(entries)
    elements: list[dict[str, Any]] = [
        {
            "element_id": "e_001",
            "name": f"{anchor['name']}整体复制区域",
            "order": 1,
            "candidate_policy": "fixed",
            "type": "fixed_text",
            "fill": "no",
            "content": anchor.get("text", ""),
            "style": "",
            "position": anchor.get("source_ref", ""),
            "relationship": "copy_region_candidate",
            "role_hint": "copy_region_candidate",
            "evidence": _element_evidence(
                "fixed",
                anchor.get("source_ref", ""),
                source_seq=anchor.get("source_seq"),
            ),
            "source_refs": source_refs or [anchor.get("source_ref", "")],
            "source_seq_refs": source_seq_refs,
            "entry_refs": [
                str(entry.get("node_id"))
                for entry in entries
                if entry.get("node_id")
            ],
            "merge": {
                "type": "whole_unit_copy_region",
                "merged_source_seq_refs": source_seq_refs,
                "reason": "copy-only 单元的整体保留候选区域",
            },
        }
    ]
    for group in _logical_entry_groups(entries):
        text = _merged_text(group)
        policy_hint = _element_policy(anchor["unit_id"], text, group[0])
        elements.append(
            _element_from_entries(
                anchor,
                group,
                element_id=f"e_{len(elements) + 1:03d}",
                policy=policy_hint,
                role_hint=_role_hint_for_policy(policy_hint),
                relationship="copy_only_internal_candidate",
                policy_hint=policy_hint,
            )
        )
    return elements


def _infer_elements(anchor: dict[str, Any], entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for group in _logical_entry_groups(entries):
        text = _merged_text(group)
        policy = _element_policy(anchor["unit_id"], text, group[0])
        elements.append(
            _element_from_entries(
                anchor,
                group,
                element_id=f"e_{len(elements) + 1:03d}",
                policy=policy,
                role_hint=_role_hint_for_policy(policy),
            )
        )
    if not elements:
        fallback_policy = "fill" if anchor["unit_id"] == "body_main" else "fixed"
        elements.append(
            {
                "element_id": "e_001",
                "name": anchor["name"],
                "order": 1,
                "candidate_policy": fallback_policy,
                "content": anchor.get("text", ""),
                "style": "",
                "role_hint": _role_hint_for_policy(fallback_policy),
                "evidence": _element_evidence(
                    fallback_policy,
                    anchor.get("source_ref", ""),
                    source_seq=anchor.get("source_seq"),
                ),
                "source_refs": [anchor.get("source_ref", "")],
                "source_seq_refs": [anchor.get("source_seq")]
                if anchor.get("source_seq") is not None
                else [],
                "entry_refs": [],
            }
        )
    return elements


def _logical_entry_groups(entries: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        text = str(entry.get("text", "")).strip()
        if not text:
            index += 1
            continue

        table_pair = _table_label_value_pair(entries, index)
        if table_pair:
            groups.append(table_pair)
            index += len(table_pair)
            continue

        group = [entry]
        index += 1
        while index < len(entries):
            candidate = entries[index]
            if not _should_merge_entry_continuation(group[-1], candidate):
                break
            group.append(candidate)
            index += 1
        groups.append(group)
    return groups


def _table_label_value_pair(
    entries: list[dict[str, Any]],
    index: int,
) -> list[dict[str, Any]]:
    if index + 1 >= len(entries):
        return []
    entry = entries[index]
    candidate = entries[index + 1]
    if not (_is_table_cell(entry) and _is_table_cell(candidate)):
        return []
    if _table_row_ref(entry) != _table_row_ref(candidate):
        return []

    text = str(entry.get("text", "")).strip()
    candidate_text = str(candidate.get("text", "")).strip()
    if not text or not candidate_text:
        return []
    if _looks_like_instruction(text) or _looks_like_instruction(candidate_text):
        return []
    if not _looks_like_fillable_label_fragment(text):
        return []
    if not _looks_like_table_value_fragment(candidate):
        return []
    return [entry, candidate]


def _should_merge_entry_continuation(
    previous: dict[str, Any],
    candidate: dict[str, Any],
) -> bool:
    previous_text = str(previous.get("text", "")).strip()
    candidate_text = str(candidate.get("text", "")).strip()
    if not previous_text or not candidate_text:
        return False
    if _is_table_cell(previous) or _is_table_cell(candidate):
        return False

    previous_is_instruction = _looks_like_instruction(previous_text)
    candidate_is_instruction = _looks_like_instruction(candidate_text)
    if previous_is_instruction and candidate_is_instruction:
        return not _starts_new_logical_entry(candidate)
    if candidate_is_instruction:
        return False
    if _starts_new_logical_entry(candidate):
        return False
    if _looks_like_fillable_label_fragment(candidate_text):
        return False

    if previous_is_instruction:
        return _continues_business_sentence(previous_text, candidate_text)
    return _continues_business_sentence(previous_text, candidate_text)


def _continues_business_sentence(previous_text: str, candidate_text: str) -> bool:
    previous = previous_text.strip()
    candidate = candidate_text.strip()
    if not previous or not candidate:
        return False
    if previous.endswith(("，", ",", "、", "；", ";", "：", ":")):
        return True
    if _has_unclosed_bracket(previous):
        return True
    if previous.endswith(("。", "！", "？", ".", "!", "?")):
        return False
    return candidate.startswith(("，", ",", "、", "；", ";", "）", ")"))


def _has_unclosed_bracket(text: str) -> bool:
    return (
        text.count("（") > text.count("）")
        or text.count("(") > text.count(")")
        or text.count("《") > text.count("》")
    )


def _is_table_cell(entry: dict[str, Any]) -> bool:
    return entry.get("kind") == "table_cell" or "/tc[" in str(
        entry.get("source_ref") or ""
    )


def _table_row_ref(entry: dict[str, Any]) -> str | None:
    match = re.search(
        r"(word/document\.xml:tbl\[\d+\]/tr\[\d+\])",
        str(entry.get("source_ref") or ""),
    )
    if not match:
        return None
    return match.group(1)


def _looks_like_fillable_label_fragment(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if not any(label in stripped for label in FILLABLE_LABELS):
        return False
    return stripped.endswith((":", "：")) or any(
        marker in stripped for marker in FILLABLE_MARKERS
    )


def _looks_like_table_value_fragment(entry: dict[str, Any]) -> bool:
    text = str(entry.get("text", "")).strip()
    if not text:
        return False
    if _starts_new_logical_entry(entry):
        return False
    if _looks_like_fillable_label_fragment(text):
        return False
    value_markers = ("××", "□□", "____", "——", "___")
    return any(marker in text for marker in value_markers) or len(text) <= 40


def _starts_new_logical_entry(entry: dict[str, Any]) -> bool:
    text = str(entry.get("text", "")).strip()
    if not text:
        return False
    unit_id, _ = _unit_for_text(text, int(float(entry.get("order") or 0)))
    return bool(unit_id) or _looks_like_heading(entry)


def _merged_text(entries: list[dict[str, Any]]) -> str:
    return "\n".join(str(entry.get("text", "")).strip() for entry in entries).strip()


def _element_from_entries(
    anchor: dict[str, Any],
    entries: list[dict[str, Any]],
    *,
    element_id: str,
    policy: str,
    role_hint: str,
    relationship: str = "",
    policy_hint: str | None = None,
) -> dict[str, Any]:
    first_entry = entries[0]
    text = _merged_text(entries)
    source_refs = [
        str(entry.get("source_ref")) for entry in entries if entry.get("source_ref")
    ]
    source_seq_refs = _source_seq_refs_for_entries(entries)
    source_ref = source_refs[0] if source_refs else ""
    candidate_policy = policy_hint or policy
    merge = _merge_details_for_entries(entries, source_seq_refs)
    return {
        "element_id": element_id,
        "name": _element_name(anchor["unit_id"], text, candidate_policy),
        "order": int(element_id.rsplit("_", 1)[-1]),
        "candidate_policy": candidate_policy,
        "type": _element_type(policy),
        "fill": "yes" if policy == "fill" else "no",
        "content": text if policy != "remove_instruction" else "",
        "normalized_content": _normalize_for_match(text),
        "style": _style_summary(first_entry),
        "style_summary": _style_summary(first_entry),
        "style_evidence": first_entry.get("style_details", {}),
        "position": source_ref,
        "relationship": relationship,
        "role_hint": role_hint,
        "evidence": _element_evidence(
            candidate_policy,
            source_ref,
            source_seq=source_seq_refs[0] if source_seq_refs else None,
        ),
        "source_refs": source_refs,
        "source_seq_refs": source_seq_refs,
        "entry_refs": [
            str(entry.get("node_id")) for entry in entries if entry.get("node_id")
        ],
        "merge": merge,
        "structure": {
            "kind": first_entry.get("kind"),
            "container_ref": first_entry.get("container_ref"),
            "source_refs": source_refs,
        },
        "confidence": "medium",
        "review_notes": [],
    }


def _merge_details_for_entries(
    entries: list[dict[str, Any]],
    source_seq_refs: list[int],
) -> dict[str, Any]:
    if len(entries) == 1:
        return {
            "type": "single_source_entry",
            "merged_source_seq_refs": source_seq_refs,
            "reason": "单个阶段一元素形成候选元素",
        }
    if _entries_are_same_table_row(entries):
        return {
            "type": "table_row_label_value",
            "merged_source_seq_refs": source_seq_refs,
            "reason": "同一表格行的标签和值合并为一个候选元素",
        }
    if all(_looks_like_instruction(str(entry.get("text", ""))) for entry in entries):
        return {
            "type": "instruction_block_continuation",
            "merged_source_seq_refs": source_seq_refs,
            "reason": "连续说明文字合并",
        }
    if any(_looks_like_instruction(str(entry.get("text", ""))) for entry in entries):
        return {
            "type": "instruction_block_continuation",
            "merged_source_seq_refs": source_seq_refs,
            "reason": "说明文字和后续延续片段合并",
        }
    return {
        "type": "business_sentence_continuation",
        "merged_source_seq_refs": source_seq_refs,
        "reason": "跨段落业务句延续合并",
    }


def _entries_are_same_table_row(entries: list[dict[str, Any]]) -> bool:
    row_refs = {_table_row_ref(entry) for entry in entries}
    return len(entries) > 1 and None not in row_refs and len(row_refs) == 1


def _role_hint_for_policy(policy: str) -> str:
    return {
        "remove_instruction": "instruction_candidate",
        "generated": "generated_field_candidate",
        "fill": "student_field_candidate",
        "manual_only": "manual_field_candidate",
        "fixed": "fixed_text_candidate",
    }.get(policy, "fixed_text_candidate")


def _element_evidence(
    policy_hint: str,
    source_ref: Any,
    *,
    source_seq: Any = None,
) -> list[dict[str, Any]]:
    return [
        {
            "kind": "source_ref",
            "value": str(source_ref or ""),
        },
        {
            "kind": "source_seq",
            "value": source_seq,
        },
        {
            "kind": "heuristic_policy_hint",
            "value": policy_hint,
        },
    ]


def _source_seq_refs_for_entries(entries: list[dict[str, Any]]) -> list[int]:
    refs: list[int] = []
    for entry in entries:
        seq = entry.get("source_seq")
        if seq is None:
            continue
        refs.append(int(seq))
    return refs


def _source_seq_range(source_seq_refs: list[int]) -> dict[str, Any]:
    if not source_seq_refs:
        return {}
    return {
        "start": source_seq_refs[0],
        "end": source_seq_refs[-1],
        "source_seq_refs": source_seq_refs,
    }


def _find_body_main_source_entry(
    entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    for entry in entries:
        text = str(entry.get("text") or "").strip()
        normalized = _normalize_for_match(text)
        style = str(entry.get("style") or "").lower()
        signals = _structural_signals(entry)
        chapter_heading = _looks_like_body_chapter_heading(normalized)
        if _body_main_anchor_excluded(text) and not chapter_heading:
            continue
        score = 0
        if style in {"heading 1", "标题 1"} or "heading 1" in style:
            score += 100
        if chapter_heading:
            score += 80
        if score <= 0:
            continue
        if signals.get("short_text"):
            score += 20
        if _has_placeholder_chapter_number(text):
            score -= 70
        if signals.get("looks_like_instruction_text") and not chapter_heading:
            score -= 80
        elif signals.get("looks_like_instruction_text"):
            score -= 15
        if len(text) > 60:
            score -= 40
        if score <= 0:
            continue
        candidates.append((score, -int(entry.get("order") or 0), entry))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def _looks_like_body_chapter_heading(normalized_text: str) -> bool:
    return bool(re.match(r"^第[一二三四五六七八九十0-9]+章", normalized_text))


def _has_placeholder_chapter_number(text: str) -> bool:
    return bool(re.search(r"第\s*[Xx]\s*章", text))


def _body_main_anchor_excluded(text: str) -> bool:
    normalized = _normalize_for_match(text)
    if not normalized:
        return True
    excluded = (
        "目录",
        "摘要",
        "abstract",
        "参考文献",
        "致谢",
        "附录",
        "声明",
        "封面",
        "图目录",
        "表目录",
        "正文基本格式",
        "正文标题",
        "格式",
        "说明",
        "黑体",
        "三号",
        "第x章",
    )
    return any(marker in normalized for marker in excluded)


def _rule_unknowns(source_tree: dict[str, Any], units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unknowns = [
        {
            "source_ref": item.get("source_ref"),
            "reason": item.get("reason", "unknown visible object"),
            "recommended_disposition": "preserve_or_review",
        }
        for item in source_tree.get("layers", {}).get("unknown_objects", [])
    ]
    if len(units) <= 1:
        unknowns.append(
            {
                "source_ref": None,
                "reason": "template unit discovery found one or fewer units",
                "recommended_disposition": "review_template_rule_discovery",
            }
        )
    return unknowns


def _unit_for_text(text: str, index: int) -> tuple[str | None, str | None]:
    normalized = _normalize_text(text)
    normalized_match = _normalize_for_match(text)
    alias = _alias_unit_id(normalized_match)
    if alias and (alias != "cover" or index <= 12):
        return alias, UNIT_DEFINITION_NAMES.get(alias, alias)
    for unit_id, name, needles in UNIT_DEFINITIONS:
        if unit_id == "cover" and index > 12:
            continue
        for needle in needles:
            needle_normalized = _normalize_text(needle)
            needle_match = _normalize_for_match(needle)
            if needle_normalized in normalized or (
                needle_match and len(needle_match) >= 2 and needle_match in normalized_match
            ):
                return unit_id, name
    return None, None


def _unit_policy(unit_id: str) -> str:
    if unit_id in {"body_main", "abstract_cn", "abstract_en", "references", "appendix", "acknowledgement"}:
        return "fill"
    if unit_id in {"toc", "figure_list", "table_list"}:
        return "generated"
    if unit_id in {
        "integrity_statement",
        "copyright_notice",
        "originality_statement",
        "authorization_statement",
        "originality_authorization_statement",
        "design_task",
        "proposal",
        "proposal_record",
        "defense_record",
        "topic_change_approval",
        "grade_form",
    }:
        return "manual_only"
    return "fixed"


def _element_policy(unit_id: str, text: str, entry: dict[str, Any]) -> str:
    lowered = text.lower()
    unit_policy = _unit_policy(unit_id)
    if _looks_like_instruction(text):
        return "remove_instruction"
    if unit_id in {"toc", "figure_list", "table_list"} or any(marker.lower() in lowered for marker in GENERATED_MARKERS):
        return "generated"
    if unit_policy == "manual_only":
        return "manual_only"
    if any(marker in text for marker in MANUAL_ONLY_MARKERS):
        return "manual_only"
    if any(marker in text for marker in FILLABLE_MARKERS) and any(
        label in text for label in FILLABLE_LABELS
    ):
        return "fill"
    if unit_policy == "fixed":
        return "fixed"
    if unit_id in FILLABLE_CONTENT_UNIT_IDS and not _looks_like_unit_heading(
        entry,
        unit_id,
    ):
        return "fill"
    return "fixed"


def _looks_like_instruction(text: str) -> bool:
    if _has_substantive_template_text(text) and re.search(
        r"[（(].*(宋体|黑体|楷体|居中|行距|字号|号字|pt).*[）)]",
        text,
    ):
        return False
    if template_units.contains_instruction_marker(text):
        return True
    if any(marker in text for marker in INSTRUCTION_MARKERS):
        return True
    return bool(re.search(r"[（(].*(宋体|黑体|楷体|居中|行距|字号|号字|pt).*[）)]", text))


def _instruction_class(text: str) -> str:
    canonical = canonical_title(text)
    if _has_format_annotation(text) and canonical and _alias_unit_id(canonical):
        return "title_with_format_annotation"
    if canonical and _alias_unit_id(canonical):
        return "unit_title"
    unit_id, _name = _unit_for_text(_strip_format_annotations(text), 999)
    if _has_format_annotation(text) and unit_id:
        return "title_with_format_annotation"
    if not _looks_like_instruction(text):
        return "not_instruction"
    if canonical and len(canonical) <= 16 and _has_format_annotation(text):
        return "ambiguous_instruction_title"
    return "pure_instruction"


def _has_format_annotation(text: str) -> bool:
    return bool(
        re.search(r"[（(].*(宋体|黑体|楷体|仿宋|居中|行距|字号|号字|pt).*[）)]", text)
    )


def _has_substantive_template_text(text: str) -> bool:
    cleaned = _normalize_for_match(text)
    if not cleaned:
        return False
    if cleaned in {
        "目录",
        "摘要",
        "abstract",
        "keywords",
        "keyword",
        "论文题目",
        "毕业论文设计中文题目",
        "titleofgraduationpaper",
    }:
        return True
    if any(marker in cleaned for marker in ("目录", "摘要", "论文", "题目")):
        return len(cleaned) <= 24
    return False


def _element_name(unit_id: str, text: str, policy: str) -> str:
    if policy == "remove_instruction":
        return "模板说明文字"
    if policy == "generated":
        return "系统生成占位"
    if policy == "fill":
        for label in FILLABLE_LABELS:
            if label in text:
                return label
        return "可填写内容"
    if policy == "manual_only":
        return "人工填写位置"
    if len(text) <= 24:
        return text
    return f"{UNIT_DEFINITION_NAMES.get(unit_id, unit_id)}固定内容"


def _element_type(policy: str) -> str:
    return {
        "fill": "fillable",
        "generated": "generated",
        "manual_only": "manual_only",
        "remove_instruction": "instruction_text",
    }.get(policy, "fixed_text")


def _style_summary(entry: dict[str, Any]) -> str:
    details = entry.get("style_details") or {}
    dominant = details.get("dominant_run") or {}
    paragraph = details.get("paragraph") or {}
    parts = []
    if dominant.get("font_names"):
        parts.append("/".join(str(name) for name in dominant["font_names"]))
    if dominant.get("font_size_pt"):
        parts.append(f"{dominant['font_size_pt']}pt")
    if dominant.get("bold"):
        parts.append("加粗")
    if paragraph.get("alignment"):
        parts.append(str(paragraph["alignment"]))
    return "；".join(parts)


def _structural_signals(entry: dict[str, Any]) -> dict[str, Any]:
    text = str(entry.get("text", ""))
    details = entry.get("style_details") or {}
    paragraph = details.get("paragraph") or {}
    dominant = details.get("dominant_run") or {}
    instruction_class = _instruction_class(text)
    return {
        "centered": paragraph.get("alignment") == "center",
        "short_text": len(text.strip()) <= 20,
        "large_font": (dominant.get("font_size_pt") or 0) >= 16,
        "bold": bool(dominant.get("bold")),
        "looks_like_instruction_text": instruction_class == "pure_instruction",
        "instruction_class": instruction_class,
        "is_toc_entry": _is_toc_entry(entry),
        "is_spacing_line": _is_spacing_line(text),
        # Compatibility-only advisory signal. T2 owns boundary decisions.
        "likely_unit_heading": _looks_like_heading(entry),
    }


def _is_toc_entry(entry: dict[str, Any]) -> bool:
    text = str(entry.get("text", ""))
    stripped = text.strip()
    if not stripped or _is_toc_title(stripped):
        return False
    style_name = _entry_style_name(entry)
    if re.search(r"\btoc\s*\d+\b", style_name.lower()):
        return True
    page_suffix = r"(?:\d+|[ivxlcdmIVXLCDM]+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+)"
    has_tab_page = bool(re.search(rf"\t\s*{page_suffix}\s*$", stripped))
    has_leader_page = bool(
        re.search(rf"(?:…|\.|．|·|•){{2,}}\s*{page_suffix}\s*$", stripped)
    )
    return has_tab_page or has_leader_page


# --- TOC block segmenter (plan §6.2) ----------------------------------------
#
# The TOC must be claimed as a whole block *before* generic boundary detection,
# otherwise three failure modes appear in the real templates:
#   - the TOC title produces no boundary so the whole region is swallowed by the
#     previous unit (hunan),
#   - the body_main fallback anchors on a TOC entry like "第一章 文献综述" and
#     splits the TOC (nannong),
#   - a second catalog title ("表目录") collides with "目录" and is downgraded to
#     `other`, orphaning its entries (pku).
# Detecting a block and *locking* its entries removes all three.

_LIST_TITLE_UNIT_BY_NORMALIZED = {
    "目录": "toc",
    "目錄": "toc",
    "contents": "toc",
    "tableofcontents": "toc",
    "图目录": "figure_list",
    "圖目錄": "figure_list",
    "插图目录": "figure_list",
    "tableoffigures": "figure_list",
    "listoffigures": "figure_list",
    "表目录": "table_list",
    "表目錄": "table_list",
    "附表目录": "table_list",
    "tableoftables": "table_list",
    "listoftables": "table_list",
}

# Largest run of non-entry interstitial lines tolerated inside a TOC block once
# at least one entry has been seen (spacing/variant markers between two variant
# tables, leader-only "……" lines, etc.).
_TOC_BLOCK_GAP_TOLERANCE = 4


def _toc_entry_like(entry: dict[str, Any]) -> bool:
    return _is_toc_entry(entry)


def _toc_title_like(entry: dict[str, Any]) -> bool:
    if _toc_entry_like(entry):
        return False
    normalized = _normalize_for_match(entry.get("text"))
    if not normalized:
        return False
    if normalized in _LIST_TITLE_UNIT_BY_NORMALIZED:
        return True
    style_name = _entry_style_name(entry).lower()
    if "目录" in style_name or "table of contents" in style_name:
        return True
    if len(normalized) <= 8 and ("目录" in normalized or "目錄" in normalized):
        return True
    return False


def _list_title_unit_id(entry: dict[str, Any]) -> str:
    normalized = _normalize_for_match(entry.get("text"))
    if normalized in _LIST_TITLE_UNIT_BY_NORMALIZED:
        return _LIST_TITLE_UNIT_BY_NORMALIZED[normalized]
    return "toc"


def _looks_like_variant_marker(entry: dict[str, Any]) -> bool:
    normalized = _normalize_for_match(entry.get("text"))
    if not normalized or len(normalized) > 16:
        return False
    return bool(re.search(r"(理工科|文科|文法经管|类专业用|以下.{0,6}用)", normalized))


def _is_leader_noise(text: str) -> bool:
    stripped = re.sub(r"[\s□×Xx_＿…·•.。．、]+", "", str(text or ""))
    return stripped == ""


_FORM_KEYWORDS = (
    "意见",
    "记录",
    "检查",
    "评审",
    "答辩",
    "任务书",
    "开题",
    "成绩",
    "评定",
    "报告",
    "审核",
    "审批",
)


def _looks_like_form_block(anchor: dict[str, Any], region_entries: list[dict[str, Any]]) -> bool:
    """Plan §6.4: a titled, table/form-dense region (school forms, review tables)."""
    title = canonical_title(str(anchor.get("text") or ""))
    if any(keyword in title for keyword in _FORM_KEYWORDS):
        return True
    if len(region_entries) < 3:
        return False
    cells = sum(1 for entry in region_entries if _is_table_cell(entry))
    return cells >= max(2, len(region_entries) // 2)


def _region_has_variant_marker(region_entries: list[dict[str, Any]]) -> bool:
    return any(_looks_like_variant_marker(entry) for entry in region_entries)


def _t2_derived_signals_by_source_seq(
    entries: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Per-paragraph T2 structure signals derived only from T1 atomic facts.

    Emitted for observability and downstream (AI input) consumption. Only
    paragraphs with at least one active signal are recorded to keep the artifact
    compact. T2 never writes these back to document_facts and never reads any
    legacy `structural_signals` to compute them (plan §0.3, §6.1).
    """
    derived: dict[str, dict[str, Any]] = {}
    for entry in entries:
        seq = entry.get("source_seq")
        if seq is None:
            continue
        text = str(entry.get("text") or "")
        signals = {
            "toc_title_like": _toc_title_like(entry),
            "toc_entry_like": _toc_entry_like(entry),
            "instruction_like": _looks_like_instruction(text),
            "instruction_class": _instruction_class(text),
            "spacing_line_like": _is_spacing_line(text),
            "unit_heading_like": _heading_level(entry) is not None,
            "variant_marker_like": _looks_like_variant_marker(entry),
        }
        active = {key: value for key, value in signals.items() if value}
        if active:
            derived[str(seq)] = active
    return derived


def _is_toc_block_member(entry: dict[str, Any]) -> bool:
    """Entries allowed *inside* a TOC block besides the TOC entries themselves."""
    text = str(entry.get("text") or "")
    if _toc_entry_like(entry) or _toc_title_like(entry):
        return True
    if _is_spacing_line(text) or _looks_like_variant_marker(entry):
        return True
    if _is_leader_noise(text):
        return True
    return not _normalize_for_match(text)


def _extend_toc_block(entries: list[dict[str, Any]], start_index: int) -> int | None:
    """Walk forward from start_index, return the index of the last TOC entry."""
    last_entry_index: int | None = None
    gap = 0
    for index in range(start_index, len(entries)):
        entry = entries[index]
        if (
            index > start_index
            and last_entry_index is not None
            and _toc_title_like(entry)
        ):
            break
        if _toc_entry_like(entry):
            last_entry_index = index
            gap = 0
            continue
        if index == start_index and _toc_title_like(entry):
            continue
        if _is_toc_block_member(entry):
            if last_entry_index is not None:
                gap += 1
                if gap > _TOC_BLOCK_GAP_TOLERANCE:
                    break
            continue
        break
    return last_entry_index


def _has_toc_entry_within(
    entries: list[dict[str, Any]],
    start_index: int,
    window: int,
) -> bool:
    for index in range(start_index, min(len(entries), start_index + window)):
        entry = entries[index]
        if _toc_entry_like(entry):
            return True
        if not _is_toc_block_member(entry):
            return False
    return False


def _lookback_toc_title(
    entries: list[dict[str, Any]],
    entry_index: int,
    window: int,
) -> int | None:
    for index in range(entry_index - 1, max(-1, entry_index - 1 - window), -1):
        if _toc_title_like(entries[index]):
            return index
        if not _is_toc_block_member(entries[index]):
            break
    return None


def _segment_toc_blocks(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    index = 0
    total = len(entries)
    while index < total:
        entry = entries[index]
        if entry.get("synthetic_kind") == "content_control_toc":
            blocks.append(
                {
                    "start": index,
                    "end": index,
                    "unit_id": "toc",
                    "title_led": True,
                    "weak": False,
                    "entries_count": 1,
                }
            )
            index += 1
            continue
        start: int | None = None
        title_led = False
        if _toc_title_like(entry) and _has_toc_entry_within(entries, index + 1, 4):
            start = index
            title_led = True
        elif _toc_entry_like(entry):
            lookback = _lookback_toc_title(entries, index, 3)
            if lookback is not None:
                start = lookback
                title_led = True
            else:
                start = index
        if start is None:
            index += 1
            continue
        end = _extend_toc_block(entries, start)
        if end is None or end < start:
            index += 1
            continue
        entries_count = sum(
            1 for k in range(start, end + 1) if _toc_entry_like(entries[k])
        )
        if title_led:
            weak = False
        elif entries_count >= 3:
            weak = True
        else:
            index += 1
            continue
        blocks.append(
            {
                "start": start,
                "end": end,
                "unit_id": _list_title_unit_id(entries[start]) if title_led else "toc",
                "title_led": title_led,
                "weak": weak,
                "entries_count": entries_count,
            }
        )
        index = end + 1
    return blocks


def _toc_block_anchor(
    entries: list[dict[str, Any]],
    block: dict[str, Any],
) -> dict[str, Any]:
    start = block["start"]
    end = block["end"]
    entry = entries[start]
    text = str(entry.get("text") or "")
    if block["weak"]:
        confidence = "low"
    elif block["entries_count"] >= 2:
        confidence = "high"
    else:
        confidence = "medium"
    flags: list[dict[str, Any]] = []
    unit_id = str(block.get("unit_id") or "toc")
    unit_name = UNIT_DEFINITION_NAMES.get(unit_id, UNIT_DEFINITION_NAMES["toc"])
    if block["weak"]:
        flags.append(
            {
                "flag_id": f"{unit_id}.{entry.get('source_seq')}.weak_block",
                "type": "toc_block_weak",
                "status": "UNKNOWN",
                "source_ref": entry.get("source_ref"),
                "affected_ids": [unit_id],
                "reason": "TOC block formed from a run of toc entries without a confident title",
            }
        )
    return {
        "entry_index": start,
        "source_ref": entry.get("source_ref"),
        "source_seq": entry.get("source_seq"),
        "text": text,
        "normalized_text": _boundary_text(text),
        "score": BOUNDARY_SCORE_THRESHOLD + 1,
        "signals": [
            {
                "kind": "toc_block",
                "weight": 3,
                "start_source_seq": entries[start].get("source_seq"),
                "end_source_seq": entries[end].get("source_seq"),
                "entries_count": block["entries_count"],
                "title_led": block["title_led"],
                "unit_id": unit_id,
            }
        ],
        "vetoes": [],
        "unit_id_hint": unit_id,
        "name_hint": unit_name,
        "is_boundary": True,
        "confidence": confidence,
        "locked_by_block": unit_id,
        "block_range": {
            "start_index": start,
            "end_index": end,
            "start_source_seq": entries[start].get("source_seq"),
            "end_source_seq": entries[end].get("source_seq"),
            "unit_id": unit_id,
        },
        "fallback_reason": "toc_block",
        "flags": flags,
    }


def _locked_indices(blocks: list[dict[str, Any]]) -> set[int]:
    locked: set[int] = set()
    for block in blocks:
        for index in range(block["start"], block["end"] + 1):
            locked.add(index)
    return locked


def _entry_style_name(entry: dict[str, Any]) -> str:
    details = entry.get("style_details") or {}
    paragraph = details.get("paragraph") or {}
    return str(
        entry.get("style")
        or paragraph.get("style_name")
        or paragraph.get("style_id")
        or ""
    )


def _is_toc_title(text: str) -> bool:
    normalized = _normalize_for_match(text)
    return normalized in _LIST_TITLE_UNIT_BY_NORMALIZED


def _is_spacing_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    content = _parenthesized_content(stripped)
    if content is None:
        return False
    compact = re.sub(r"\s+", "", content)
    return bool(
        re.search(
            r"空(?:[一二两三四五六七八九十0-9]+(?:或[一二两三四五六七八九十0-9]+)?|)[行格]",
            compact,
        )
    )


def _parenthesized_content(text: str) -> str | None:
    if (text.startswith("（") and text.endswith("）")) or (
        text.startswith("(") and text.endswith(")")
    ):
        return text[1:-1]
    return None


def _looks_like_heading(entry: dict[str, Any]) -> bool:
    text = str(entry.get("text", ""))
    unit_id, _ = _unit_for_text(text, int(float(entry.get("order") or 0)))
    details = entry.get("style_details") or {}
    paragraph = details.get("paragraph") or {}
    dominant = details.get("dominant_run") or {}
    short_text = len(text.strip()) <= 20
    centered = paragraph.get("alignment") == "center"
    large_font = (dominant.get("font_size_pt") or 0) >= 16
    return bool(unit_id) or (
        short_text
        and (centered or large_font)
    )


def _looks_like_unit_heading(entry: dict[str, Any], unit_id: str) -> bool:
    text_unit_id, _ = _unit_for_text(
        str(entry.get("text", "")),
        int(float(entry.get("order") or 0)),
    )
    if text_unit_id and text_unit_id != unit_id:
        return False
    if text_unit_id == unit_id:
        return True
    return _looks_like_heading(entry)


def _first_body_like_index(
    entries: list[dict[str, Any]],
    locked: set[int] | None = None,
) -> int | None:
    locked = locked or set()
    for index, entry in enumerate(entries):
        if index in locked:
            continue
        unit_id, _ = _unit_for_text(str(entry.get("text", "")), index)
        if unit_id == "body_main":
            return index
    for index in range(len(entries) - 1, -1, -1):
        if index not in locked:
            return index
    return None


def _dedupe_str(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        item = str(value)
        if not item or item in seen:
            continue
        result.append(item)
        seen.add(item)
    return result


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _paragraph_index_from_source_ref(source_ref: str) -> int | None:
    match = re.search(r"word/document\.xml:p\[(\d+)\]", source_ref)
    if not match:
        return None
    return _int_or_none(match.group(1))
