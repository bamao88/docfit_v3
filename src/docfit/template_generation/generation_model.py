from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from docfit.core.io import now_iso, sha256_json
from docfit.template_model import units as template_units

from .plan import _decision_reason
from .refs import _first_source_ref, _paragraph_index
from .refs import _source_seq_refs
from .structure_candidates import _looks_like_instruction, _unit_is_copy_only_by_default
from .text_utils import _dedupe_by_key, _normalize_for_match


def build_template_generation_model(
    request: dict[str, Any],
    structure_candidates: dict[str, Any],
) -> dict[str, Any]:
    source_context = structure_candidates.get("source_context", {})
    source_entries_by_seq = _source_entries_by_seq(source_context)
    units = _materialize_template_units(
        structure_candidates.get("units", []),
        runs_by_raw=source_context.get("runs_by_raw_run_id", {}),
        source_entries_by_seq=source_entries_by_seq,
    )
    paragraphs = source_context.get("paragraphs", [])
    copy_only_source_refs = _copy_only_unit_source_refs(units)
    instruction_paragraphs = _dedupe_by_key(
        [
            *_instruction_paragraphs_from_units(units),
            *_instruction_paragraphs_from_source_context(
                source_context,
                excluded_source_refs=copy_only_source_refs,
            ),
        ],
        "source_ref",
    )
    template_units.apply_instruction_policy(paragraphs, instruction_paragraphs)
    slots: list[dict[str, Any]] = []
    regions: list[dict[str, Any]] = []
    template_units.extend_slots_and_regions_from_units(slots, regions, units)
    if not any(slot.get("slot_id") == "slot_body_start" for slot in slots):
        slots.append(
            {
                "slot_id": "slot_body_start",
                "unit_id": "body_main",
                "element_id": "slot_body_start",
                "kind": "body_content",
                "writable": True,
                "required": True,
                "accepted_content_kinds": ["heading", "paragraph", "table", "image"],
                "source_ref": "template-generate:body-slot",
                "source_seq_refs": [],
                "policy": "fill",
            }
        )
    if not any(region.get("region_id") == "body_main" for region in regions):
        regions.append(
            {
                "region_id": "body_main",
                "kind": "body",
                "required": True,
                "anchors": ["slot_body_start"],
                "source_ref": "template-generate:body-slot",
                "source_seq_refs": [],
                "policy": "fill",
            }
        )
    data = {
        "source_template_tree": "source_template_tree.json",
        "template_structure_candidates": "template_structure_candidates.json",
        "page_setup": {"sections": source_context.get("section_rules", [])},
        "styles": source_context.get("style_inventory", []),
        "paragraphs": paragraphs,
        "units": units,
        "instruction_paragraphs": instruction_paragraphs,
        "regions": regions,
        "slots": slots,
        "protected_zones": template_units.protected_zones_from_units(units),
        "numbering": source_context.get("numbering_definitions", []),
        "headers_footers": source_context.get("header_footer", []),
        "required_fields": template_units.required_fields_from_units(units),
        "unsupported": source_context.get("unknown_objects", []),
    }
    unit_strategies = _build_unit_strategies(units)
    return {
        "artifact_type": "template_generation_model",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.2.0"},
        "created_at": now_iso(),
        "input_hashes": {
            "template_docx": request.get("source_template_hash"),
            "template_structure_candidates": sha256_json(structure_candidates),
        },
        "provenance": {"template_docx": request.get("source_template_docx")},
        "status_notes": [
            "units are inferred from source Word structure and deterministic keywords",
            "formal quality still requires template-gap against accepted standards",
        ],
        "source_context": source_context,
        "units": units,
        "unit_strategies": unit_strategies,
        "slots": slots,
        "required_fields": data["required_fields"],
        "protected_zones": data["protected_zones"],
        "cleanup": instruction_paragraphs,
        "unsupported": data["unsupported"],
        "unresolved_questions": _unresolved_questions_from_candidates(
            structure_candidates,
            unit_strategies,
        ),
        "data": data,
    }

def _materialize_template_units(
    candidate_units: list[dict[str, Any]],
    *,
    runs_by_raw: dict[str, Any],
    source_entries_by_seq: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for unit in candidate_units:
        materialized = deepcopy(unit)
        generation_mode = _unit_generation_mode(materialized)
        materialized["elements"] = [
            _materialize_template_element(
                element,
                generation_mode=generation_mode,
                runs_by_raw=runs_by_raw,
                source_entries_by_seq=source_entries_by_seq,
            )
            for element in unit.get("elements", [])
        ]
        units.append(materialized)
    return units


def _materialize_template_element(
    element: dict[str, Any],
    *,
    generation_mode: str,
    runs_by_raw: dict[str, Any],
    source_entries_by_seq: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    materialized = deepcopy(element)
    _backfill_element_source_facts(materialized, source_entries_by_seq)
    run_text_overrides = _source_run_texts_for_element(
        materialized,
        source_entries_by_seq,
    )
    candidate_policy = str(
        element.get("candidate_policy") or element.get("policy") or "fixed"
    )
    final_policy = _final_policy_for_generation(candidate_policy, generation_mode)
    materialized["candidate_policy"] = candidate_policy
    materialized["policy"] = final_policy
    materialized["type"] = _element_type(final_policy)
    materialized["fill"] = "yes" if final_policy == "fill" else "no"
    materialized["spans"] = _element_spans(
        materialized,
        runs_by_raw=runs_by_raw,
        run_text_overrides=run_text_overrides,
    )
    return materialized


def _backfill_element_source_facts(
    element: dict[str, Any],
    source_entries_by_seq: dict[int, dict[str, Any]],
) -> None:
    entries = [
        source_entries_by_seq[source_seq]
        for source_seq in _source_seq_refs(element)
        if source_seq in source_entries_by_seq
    ]
    if not entries:
        return
    if not element.get("source_refs"):
        element["source_refs"] = [
            entry.get("source_ref") for entry in entries if entry.get("source_ref")
        ]
    if not element.get("entry_refs"):
        element["entry_refs"] = [
            entry.get("node_id") for entry in entries if entry.get("node_id")
        ]
    if not element.get("raw_run_ids"):
        element["raw_run_ids"] = _dedupe_strings(
            raw_run_id
            for entry in entries
            for raw_run_id in entry.get("raw_run_ids", []) or []
        )
    if not element.get("logical_run_ids"):
        element["logical_run_ids"] = _dedupe_strings(
            logical_run_id
            for entry in entries
            for logical_run_id in entry.get("logical_run_ids", []) or []
        )
    if not str(element.get("content") or "").strip():
        element["content"] = "\n".join(
            str(entry.get("text") or "") for entry in entries if entry.get("text")
        )


def _dedupe_strings(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result


def _source_run_texts_for_element(
    element: dict[str, Any],
    source_entries_by_seq: dict[int, dict[str, Any]],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for source_seq in _source_seq_refs(element):
        entry = source_entries_by_seq.get(source_seq)
        if not isinstance(entry, dict):
            continue
        raw_run_ids = [
            str(raw_run_id) for raw_run_id in entry.get("raw_run_ids", []) or []
        ]
        runs = (entry.get("style_details") or {}).get("runs") or []
        for index, raw_run_id in enumerate(raw_run_ids):
            if index >= len(runs) or not isinstance(runs[index], dict):
                continue
            result[raw_run_id] = str(runs[index].get("text") or "")
    return result


def _final_policy_for_generation(candidate_policy: str, generation_mode: str) -> str:
    if generation_mode != "whole_unit_copy":
        return candidate_policy
    if candidate_policy in {"remove_instruction", "manual_only"}:
        return candidate_policy
    return "fixed"


def _element_type(policy: str) -> str:
    return {
        "fill": "fillable",
        "generated": "generated",
        "manual_only": "manual_only",
        "remove_instruction": "instruction_text",
    }.get(policy, "fixed_text")


def _element_spans(
    element: dict[str, Any],
    *,
    runs_by_raw: dict[str, Any],
    run_text_overrides: dict[str, str],
) -> list[dict[str, Any]]:
    content = str(element.get("content") or "")
    raw_run_ids = [
        str(raw_run_id) for raw_run_id in element.get("raw_run_ids", []) if raw_run_id
    ]
    if not raw_run_ids:
        return []
    run_texts = _run_texts_for_element(
        raw_run_ids,
        content,
        runs_by_raw,
        run_text_overrides=run_text_overrides,
    )
    logical_by_raw = _logical_run_ids_by_raw(raw_run_ids, runs_by_raw)
    run_parts = _run_parts(raw_run_ids, run_texts, logical_by_raw)
    combined_text = "".join(str(part["text"]) for part in run_parts)
    inline_instruction_ranges = _inline_instruction_ranges(combined_text)
    sample_value_ranges = _sample_value_ranges(
        combined_text,
        inline_instruction_ranges=inline_instruction_ranges,
    )
    if not sample_value_ranges and str(element.get("policy") or "") == "fill":
        sample_value_ranges = _fallback_fill_sample_value_ranges(
            combined_text,
            inline_instruction_ranges=inline_instruction_ranges,
        )
    protected_ranges = [*inline_instruction_ranges, *sample_value_ranges]
    spans: list[dict[str, Any]] = []
    order = 1
    for start, end in inline_instruction_ranges:
        spans.append(
            _span_from_combined_range(
                element,
                order=order,
                span_type="inline_instruction",
                policy="remove_instruction",
                text=combined_text[start:end],
                start=start,
                end=end,
                run_parts=run_parts,
            )
        )
        order += 1
    for start, end in sample_value_ranges:
        spans.append(
            _span_from_combined_range(
                element,
                order=order,
                span_type="sample_value",
                policy="fill",
                text=combined_text[start:end],
                start=start,
                end=end,
                run_parts=run_parts,
            )
        )
        order += 1
    layout_ranges: list[tuple[int, int]] = []
    for part in run_parts:
        raw_run_id = str(part["raw_run_id"])
        logical_run_id = str(part.get("logical_run_id") or "")
        text = str(part["text"])
        combined_offset = int(part["start"])
        for match in re.finditer(r"□+", text):
            combined_start = combined_offset + match.start()
            combined_end = combined_offset + match.end()
            if _range_overlaps_any(combined_start, combined_end, protected_ranges):
                continue
            layout_ranges.append((combined_start, combined_end))
            spans.append(
                _span(
                    element,
                    order=order,
                    span_type="layout_spacer",
                    policy="remove_instruction",
                    text=match.group(0),
                    raw_run_id=raw_run_id,
                    logical_run_id=logical_run_id,
                    start=match.start(),
                    end=match.end(),
                )
            )
            order += 1
    protected_ranges = [*protected_ranges, *layout_ranges]
    for part in run_parts:
        raw_run_id = str(part["raw_run_id"])
        logical_run_id = str(part.get("logical_run_id") or "")
        text = str(part["text"])
        combined_offset = int(part["start"])
        for start, end in _unprotected_part_ranges(
            text,
            combined_offset=combined_offset,
            protected_ranges=protected_ranges,
        ):
            label_text = text[start:end]
            if not label_text.strip():
                continue
            spans.append(
                {
                    "span_id": f"{element.get('element_id')}.span_{order:03d}",
                    "span_type": "label",
                    "policy": "fixed",
                    "text": label_text,
                    "raw_run_ids": [raw_run_id],
                    "logical_run_ids": [logical_run_id] if logical_run_id else [],
                    "char_ranges": [
                        {
                            "raw_run_id": raw_run_id,
                            "start": start,
                            "end": end,
                            "replacement": "",
                        }
                    ],
                    "origin": "deterministic_parser",
                    "confidence": "high",
                }
            )
            order += 1
    return spans


def _unprotected_part_ranges(
    text: str,
    *,
    combined_offset: int,
    protected_ranges: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    cursor = 0
    local_protected = sorted(
        (
            max(0, start - combined_offset),
            min(len(text), end - combined_offset),
        )
        for start, end in protected_ranges
        if start < combined_offset + len(text) and end > combined_offset
    )
    for start, end in local_protected:
        if cursor < start:
            ranges.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < len(text):
        ranges.append((cursor, len(text)))
    return ranges


def _run_parts(
    raw_run_ids: list[str],
    run_texts: dict[str, str],
    logical_by_raw: dict[str, str],
) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    cursor = 0
    for raw_run_id in raw_run_ids:
        text = run_texts.get(raw_run_id, "")
        parts.append(
            {
                "raw_run_id": raw_run_id,
                "logical_run_id": logical_by_raw.get(raw_run_id, ""),
                "text": text,
                "start": cursor,
                "end": cursor + len(text),
            }
        )
        cursor += len(text)
    return parts


def _inline_instruction_ranges(text: str) -> list[tuple[int, int]]:
    return [
        (match.start(), match.end())
        for match in re.finditer(r"[（(][^（）()]{1,80}[）)]", text)
        if _looks_like_inline_instruction(match.group(0))
    ]


def _looks_like_inline_instruction(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text).lower()
    if "或" in normalized and ("×" in normalized or "□" in normalized):
        return False
    markers = (
        "号",
        "黑体",
        "宋体",
        "楷体",
        "华文",
        "times",
        "newroman",
        "加粗",
        "居中",
        "大写",
        "小写",
        "行距",
        "页边距",
        "空一行",
        "空二行",
        "空三行",
        "字空",
        "用全称",
    )
    return any(marker in normalized for marker in markers)


def _sample_value_ranges(
    text: str,
    *,
    inline_instruction_ranges: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    if _contains_internal_marker(text):
        return []
    colon_indexes = [index for index in (text.find("："), text.find(":")) if index >= 0]
    if colon_indexes:
        start = min(colon_indexes) + 1
        end = len(text)
        for inline_start, _inline_end in sorted(inline_instruction_ranges):
            if inline_start >= start:
                end = inline_start
                break
        start, end = _trim_range(text, start, end)
        if start < end and _contains_placeholder_marker(text[start:end]):
            return [(start, end)]
    stripped_start, stripped_end = _trim_range(text, 0, len(text))
    for inline_start, _inline_end in sorted(inline_instruction_ranges):
        if inline_start >= stripped_start:
            stripped_end = min(stripped_end, inline_start)
            break
    stripped_start, stripped_end = _trim_range(text, stripped_start, stripped_end)
    standalone_ellipsis = _standalone_ellipsis_range(text, stripped_start, stripped_end)
    if standalone_ellipsis is not None:
        return [standalone_ellipsis]
    stripped = text[stripped_start:stripped_end]
    if stripped and _looks_like_sample_value(stripped):
        return [(stripped_start, stripped_end)]
    return []


def _fallback_fill_sample_value_ranges(
    text: str,
    *,
    inline_instruction_ranges: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    if _contains_internal_marker(text):
        return []
    start, end = _trim_range(text, 0, len(text))
    for inline_start, _inline_end in sorted(inline_instruction_ranges):
        if inline_start >= start:
            end = min(end, inline_start)
            break
    start, end = _trim_range(text, start, end)
    while start < end and text[start] in {"□", " "}:
        start += 1
    start, end = _trim_range(text, start, end)
    if start >= end:
        return []
    colon_indexes = [
        index
        for index in (text.find("：", start, end), text.find(":", start, end))
        if index >= 0
    ]
    if colon_indexes:
        sample_start, sample_end = _trim_range(text, min(colon_indexes) + 1, end)
        return [(sample_start, sample_end)] if sample_start < sample_end else []
    return [(start, end)]


def _contains_placeholder_marker(text: str) -> bool:
    return any(marker in text for marker in ("□", "×", "……")) or bool(
        re.search(r"…{2,}", text)
    )


def _standalone_ellipsis_range(
    text: str,
    start: int,
    end: int,
) -> tuple[int, int] | None:
    while start < end and text[start] in {"□", " "}:
        start += 1
    start, end = _trim_range(text, start, end)
    if start >= end:
        return None
    candidate = text[start:end]
    if re.fullmatch(r"…{2,}", candidate):
        return (start, end)
    match = re.search(r"…{2,}$", candidate)
    if match is None:
        return None
    prefix = candidate[: match.start()]
    if re.search(r"…{2,}.+\d\s*$", candidate):
        return None
    if re.search(r"[一二三四五六七八九十\d]+[\.、)]?[^…]{0,12}$", prefix):
        return (start + match.start(), start + match.end())
    return None


def _trim_range(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _range_overlaps_any(
    start: int,
    end: int,
    ranges: list[tuple[int, int]],
) -> bool:
    return any(start < range_end and end > range_start for range_start, range_end in ranges)


def _span_from_combined_range(
    element: dict[str, Any],
    *,
    order: int,
    span_type: str,
    policy: str,
    text: str,
    start: int,
    end: int,
    run_parts: list[dict[str, Any]],
) -> dict[str, Any]:
    char_ranges: list[dict[str, Any]] = []
    raw_run_ids: list[str] = []
    logical_run_ids: list[str] = []
    for part in run_parts:
        part_start = int(part["start"])
        part_end = int(part["end"])
        overlap_start = max(start, part_start)
        overlap_end = min(end, part_end)
        if overlap_start >= overlap_end:
            continue
        raw_run_id = str(part["raw_run_id"])
        raw_run_ids.append(raw_run_id)
        logical_run_id = str(part.get("logical_run_id") or "")
        if logical_run_id:
            logical_run_ids.append(logical_run_id)
        char_ranges.append(
            {
                "raw_run_id": raw_run_id,
                "start": overlap_start - part_start,
                "end": overlap_end - part_start,
                "replacement": "",
            }
        )
    return {
        "span_id": f"{element.get('element_id')}.span_{order:03d}",
        "span_type": span_type,
        "policy": policy,
        "text": text,
        "raw_run_ids": raw_run_ids,
        "logical_run_ids": _dedupe_strings(logical_run_ids),
        "char_ranges": char_ranges,
        "origin": "deterministic_parser",
        "confidence": "high",
    }


def _run_texts_for_element(
    raw_run_ids: list[str],
    content: str,
    runs_by_raw: dict[str, Any],
    *,
    run_text_overrides: dict[str, str],
) -> dict[str, str]:
    result: dict[str, str] = {}
    missing = False
    for raw_run_id in raw_run_ids:
        if raw_run_id in run_text_overrides:
            result[raw_run_id] = run_text_overrides[raw_run_id]
            continue
        run = runs_by_raw.get(raw_run_id)
        if not isinstance(run, dict):
            missing = True
            continue
        result[raw_run_id] = str(run.get("text") or "")
    if run_text_overrides:
        return result
    semantic = _semantic_field_run_texts(raw_run_ids, content, result)
    if semantic is not None:
        return semantic
    if missing and len(raw_run_ids) == 1:
        return {raw_run_ids[0]: content}
    return result


def _logical_run_ids_by_raw(
    raw_run_ids: list[str],
    runs_by_raw: dict[str, Any],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_run_id in raw_run_ids:
        run = runs_by_raw.get(raw_run_id)
        if not isinstance(run, dict):
            continue
        logical_run_id = str(run.get("logical_run_id") or "").strip()
        if logical_run_id:
            result[raw_run_id] = logical_run_id
    return result


def _semantic_field_run_texts(
    raw_run_ids: list[str],
    content: str,
    run_texts: dict[str, str],
) -> dict[str, str] | None:
    if len(raw_run_ids) < 2:
        return None
    if any(run_texts.get(raw_run_id) != content for raw_run_id in raw_run_ids):
        return None
    match = re.match(r"^(□+)(.+?[：:])(.+)$", content)
    if match is None:
        return None
    leading, label, sample = match.groups()
    if len(raw_run_ids) == 2:
        return {
            raw_run_ids[0]: leading,
            raw_run_ids[1]: f"{label}{sample}",
        }
    return {
        raw_run_ids[0]: leading,
        raw_run_ids[1]: label,
        raw_run_ids[2]: sample,
        **{raw_run_id: "" for raw_run_id in raw_run_ids[3:]},
    }


def _is_layout_square_text(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and set(stripped) <= {"□"}


def _looks_like_sample_value(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return "×" in stripped or stripped in {"……", "..."} or bool(re.fullmatch(r"…+", stripped))


def _contains_internal_marker(text: str) -> bool:
    return "[[DOCFIT_" in text


def _span(
    element: dict[str, Any],
    *,
    order: int,
    span_type: str,
    policy: str,
    text: str,
    raw_run_id: str,
    logical_run_id: str,
    start: int,
    end: int,
) -> dict[str, Any]:
    return {
        "span_id": f"{element.get('element_id')}.span_{order:03d}",
        "span_type": span_type,
        "policy": policy,
        "text": text,
        "raw_run_ids": [raw_run_id],
        "logical_run_ids": [logical_run_id] if logical_run_id else [],
        "char_ranges": [
            {
                "raw_run_id": raw_run_id,
                "start": start,
                "end": end,
                "replacement": "",
            }
        ],
        "origin": "deterministic_parser",
        "confidence": "high",
    }


def _span_decisions(
    unit_id: str,
    element: dict[str, Any],
    *,
    source_ref: str | None,
) -> list[dict[str, Any]]:
    if element.get("policy") == "remove_instruction":
        return []
    if not source_ref or "word/document.xml:p[" not in source_ref:
        return []
    decisions: list[dict[str, Any]] = []
    element_id = element.get("element_id")
    for span in element.get("spans", []) or []:
        span_type = str(span.get("span_type") or "")
        if span_type not in {"layout_spacer", "inline_instruction", "sample_value"}:
            continue
        decision_type = (
            "replace_span_with_slot"
            if span_type == "sample_value"
            else "remove_instruction_text"
        )
        decisions.append(
            {
                "decision_id": f"{unit_id}.{element_id}.{span.get('span_id')}.{decision_type}",
                "decision_type": decision_type,
                "unit_id": unit_id,
                "element_id": element_id,
                "span_id": span.get("span_id"),
                "span_type": span_type,
                "element_name": element.get("name"),
                "content": span.get("text") or "",
                "source_ref": source_ref,
                "source_seq_refs": _source_seq_refs(element),
                "raw_run_ids": list(span.get("raw_run_ids") or []),
                "logical_run_ids": list(span.get("logical_run_ids") or [])
                or element.get("logical_run_ids", []),
                "char_ranges": list(span.get("char_ranges") or []),
                "reason": _decision_reason(decision_type),
            }
        )
    return decisions


def _build_unit_strategies(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    strategies: list[dict[str, Any]] = []
    for unit in units:
        unit_id = str(unit.get("unit_id"))
        unit_anchor_ref = _first_source_ref(unit)
        decisions: list[dict[str, Any]] = []
        generation_mode = _unit_generation_mode(unit)
        if generation_mode == "whole_unit_copy":
            decisions.append(
                {
                    "decision_id": f"{unit_id}.keep_whole_unit_copy",
                    "decision_type": "keep_whole_unit_copy",
                    "unit_id": unit_id,
                    "element_id": None,
                    "source_ref": unit_anchor_ref,
                    "source_seq_refs": _source_seq_refs(unit),
                    "copy_scope": "whole_unit",
                    "reason": "this unit can be preserved by the initial source DOCX copy",
                }
            )
            for element in unit.get("elements", []):
                element_id = element.get("element_id")
                source_ref = _first_source_ref(element)
                decisions.extend(_span_decisions(unit_id, element, source_ref=source_ref))
                if element.get("policy") == "remove_instruction":
                    decisions.append(
                        {
                            "decision_id": f"{unit_id}.{element_id}.remove_instruction_text",
                            "decision_type": "remove_instruction_text",
                            "unit_id": unit_id,
                            "element_id": element_id,
                            "element_name": element.get("name"),
                            "content": element.get("content") or element.get("name") or "",
                            "source_ref": source_ref,
                            "source_seq_refs": _source_seq_refs(element),
                            "raw_run_ids": element.get("raw_run_ids", []),
                            "logical_run_ids": element.get("logical_run_ids", []),
                            "reason": _decision_reason("remove_instruction_text"),
                        }
                    )
                elif element.get("policy") == "manual_only":
                    decisions.append(
                        {
                            "decision_id": f"{unit_id}.{element_id}.create_manual_placeholder",
                            "decision_type": "create_manual_placeholder",
                            "unit_id": unit_id,
                            "element_id": element_id,
                            "element_name": element.get("name"),
                            "content": element.get("content") or element.get("name") or "",
                            "source_ref": source_ref,
                            "source_seq_refs": _source_seq_refs(element),
                            "raw_run_ids": element.get("raw_run_ids", []),
                            "logical_run_ids": element.get("logical_run_ids", []),
                            "reason": _decision_reason("create_manual_placeholder"),
                        }
                    )
        else:
            for element in unit.get("elements", []):
                policy = element.get("policy")
                element_id = element.get("element_id")
                source_ref = _first_source_ref(element)
                decisions.extend(_span_decisions(unit_id, element, source_ref=source_ref))
                if policy == "remove_instruction":
                    decision_type = "remove_instruction_text"
                elif policy == "fill":
                    decision_type = "create_fillable_slot"
                elif policy == "generated":
                    decision_type = "create_generated_field_placeholder"
                elif policy in {"fixed", "manual_only"} and (
                    source_ref is None
                    and _should_synthesize_visible_text(element)
                ):
                    decision_type = "insert_fixed_text"
                    source_ref = unit_anchor_ref
                elif policy == "manual_only":
                    decision_type = "create_manual_placeholder"
                else:
                    continue
                decisions.append(
                    {
                        "decision_id": f"{unit_id}.{element_id}.{decision_type}",
                        "decision_type": decision_type,
                        "unit_id": unit_id,
                        "element_id": element_id,
                        "element_name": element.get("name"),
                        "content": element.get("content") or element.get("name") or "",
                        "source_ref": source_ref,
                        "source_seq_refs": _source_seq_refs(element),
                        "raw_run_ids": element.get("raw_run_ids", []),
                        "logical_run_ids": element.get("logical_run_ids", []),
                        "reason": _decision_reason(decision_type),
                    }
                )
        strategies.append(
            {
                "unit_id": unit_id,
                "unit_name": unit.get("name"),
                "source_policy": unit.get("candidate_policy") or unit.get("policy"),
                "generation_mode": generation_mode,
                "generation_policy": "whole_unit_copy"
                if generation_mode == "whole_unit_copy"
                else "unit_actions",
                "copy_source_ref": unit_anchor_ref,
                "source_seq_refs": _source_seq_refs(unit),
                "decisions": decisions,
                "unresolved_questions": [],
            }
        )
    return strategies


def _unit_generation_mode(unit: dict[str, Any]) -> str:
    if _unit_is_copy_only_by_default(str(unit.get("unit_id") or "")) and _first_source_ref(
        unit
    ):
        return "whole_unit_copy"
    return "copy_then_patch"


def _instruction_paragraphs_from_units(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paragraphs: list[dict[str, Any]] = []
    for unit in units:
        for element in unit.get("elements", []):
            if element.get("policy") != "remove_instruction":
                continue
            source_refs = element.get("source_refs") or [_first_source_ref(element)]
            seq_refs = _source_seq_refs(element)
            for index, source_ref in enumerate(source_refs):
                paragraph_index = _paragraph_index(source_ref)
                if paragraph_index is None:
                    continue
                source_seq_refs = [seq_refs[index]] if index < len(seq_refs) else []
                paragraphs.append(
                    {
                        "source_ref": source_ref,
                        "source_seq_refs": source_seq_refs,
                        "paragraph_index": paragraph_index,
                        "text": element.get("content") or element.get("name", ""),
                        "policy": "strip",
                        "final_disposition": "omit_from_final",
                        "reason": "detected template instruction text should not appear in the generated fillable template",
                    }
                )
    return paragraphs


def _copy_only_unit_source_refs(units: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for unit in units:
        if not _unit_is_copy_only_by_default(str(unit.get("unit_id") or "")):
            continue
        refs.update(str(ref) for ref in unit.get("source_refs", []) if ref)
    return refs


def _source_entries_by_seq(source_context: dict[str, Any]) -> dict[int, dict[str, Any]]:
    entries: dict[int, dict[str, Any]] = {}
    by_source_seq = source_context.get("by_source_seq", {})
    if isinstance(by_source_seq, dict):
        for key, value in by_source_seq.items():
            if isinstance(value, dict):
                try:
                    entries[int(key)] = value
                except (TypeError, ValueError):
                    continue
    for entry in source_context.get("body_flow", []) or []:
        if not isinstance(entry, dict):
            continue
        try:
            source_seq = int(entry.get("source_seq"))
        except (TypeError, ValueError):
            continue
        entries[source_seq] = entry
    return entries


def _instruction_paragraphs_from_source_context(
    source_context: dict[str, Any],
    *,
    excluded_source_refs: set[str] | None = None,
) -> list[dict[str, Any]]:
    excluded_source_refs = excluded_source_refs or set()
    paragraphs: list[dict[str, Any]] = []
    for entry in source_context.get("body_flow", []):
        if entry.get("structure_layer") != "body_flow":
            continue
        text = str(entry.get("text", ""))
        if not _looks_like_instruction(text):
            continue
        source_ref = entry.get("source_ref")
        if not source_ref or str(source_ref) in excluded_source_refs:
            continue
        paragraphs.append(
            {
                "source_ref": source_ref,
                "source_seq_refs": _source_seq_refs(entry),
                "paragraph_index": _paragraph_index(source_ref),
                "text": text,
                "policy": "strip",
                "final_disposition": "omit_from_final",
                "reason": "detected template instruction text should not appear in the generated fillable template",
            }
        )
    return paragraphs


def _unresolved_questions_from_candidates(
    structure_candidates: dict[str, Any],
    unit_strategies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for item in structure_candidates.get("unknowns", []):
        questions.append(
            {
                "kind": "unknown_source_object",
                "source_ref": item.get("source_ref"),
                "source_seq_refs": item.get("source_seq_refs", []),
                "reason": item.get("reason"),
            }
        )
    for strategy in unit_strategies:
        questions.extend(strategy.get("unresolved_questions", []))
    return questions

def _should_synthesize_visible_text(element: dict[str, Any]) -> bool:
    order = element.get("order") or element.get("element_order")
    if order not in {1, "1"}:
        return False
    text = str(element.get("content") or element.get("name") or "").strip()
    if not text:
        return False
    if len(text) > 120:
        return False
    normalized = _normalize_for_match(text)
    if not normalized or _looks_like_nonvisible_requirement(normalized):
        return False
    return True


def _looks_like_nonvisible_requirement(normalized: str) -> bool:
    markers = (
        "页眉",
        "页脚",
        "页码",
        "页边距",
        "装订线",
        "纸张",
        "section",
        "schoolyaml",
        "ooxml",
        "审查口径",
        "全局规则",
        "源模板",
        "源文件",
        "当前阶段",
        "目标输出",
        "生成机制",
        "标题编号体系",
        "样式",
        "字体",
        "字号",
        "行距",
        "大纲级别",
        "保留学校封面本体",
        "不属于模板的说明文字",
        "markdown",
        "自动化测试",
        "渲染测试",
        "验收",
    )
    return any(marker in normalized for marker in markers)
