from __future__ import annotations

import re
from typing import Any

from docfit.core.io import now_iso
from docfit.harness import template_units

from .constants import (
    COPY_ONLY_DEFAULT_EXCLUDED_UNIT_IDS,
    FILLABLE_CONTENT_UNIT_IDS,
    FILLABLE_LABELS,
    FILLABLE_MARKERS,
    GENERATED_MARKERS,
    INSTRUCTION_MARKERS,
    MANUAL_ONLY_MARKERS,
    UNIT_DEFINITION_NAMES,
    UNIT_DEFINITIONS,
)
from .text_utils import _normalize_for_match, _normalize_text


def infer_template_rules(source_tree: dict[str, Any]) -> dict[str, Any]:
    entries = _body_entries(source_tree)
    units = _infer_units(entries)
    return {
        "artifact_type": "discovered_template_rules",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.2.0"},
        "created_at": now_iso(),
        "source_template_hash": source_tree.get("metadata", {}).get(
            "source_template_hash"
        ),
        "discovery_method": "deterministic_keyword_and_structure_heuristics",
        "units": units,
        "unknowns": _rule_unknowns(source_tree, units),
    }


def _body_entries(source_tree: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for item in source_tree.get("layers", {}).get("body_flow", []):
        if item.get("structure_layer") != "body_flow":
            continue
        if item.get("text"):
            entries.append(item)
    return entries


def _infer_units(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not entries:
        return [
            {
                "unit_id": "body_main",
                "name": "正文",
                "order": 10,
                "status": "required",
                "policy": "fill",
                "source_refs": [],
                "elements": [],
            }
        ]
    anchors = _unit_anchors(entries)
    units: list[dict[str, Any]] = []
    for anchor_index, anchor in enumerate(anchors):
        next_start = (
            anchors[anchor_index + 1]["entry_index"]
            if anchor_index + 1 < len(anchors)
            else len(entries)
        )
        region_entries = entries[anchor["entry_index"] : next_start]
        unit_id = anchor["unit_id"]
        region_source_refs = [
            str(entry.get("source_ref"))
            for entry in region_entries
            if entry.get("source_ref")
        ]
        units.append(
            {
                "unit_id": unit_id,
                "name": anchor["name"],
                "order": (anchor_index + 1) * 10,
                "status": "required",
                "policy": _unit_policy(unit_id),
                "source_refs": region_source_refs or [anchor["source_ref"]],
                "page": {},
                "elements": _copy_only_unit_elements(anchor, region_entries)
                if _unit_is_copy_only_by_default(unit_id)
                else _infer_elements(anchor, region_entries),
            }
        )
    return units


def _unit_is_copy_only_by_default(unit_id: str) -> bool:
    return bool(unit_id) and unit_id not in COPY_ONLY_DEFAULT_EXCLUDED_UNIT_IDS


def _copy_only_unit_elements(
    anchor: dict[str, Any],
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_refs = [
        str(entry.get("source_ref")) for entry in entries if entry.get("source_ref")
    ]
    elements: list[dict[str, Any]] = [
        {
            "element_id": "e_001",
            "name": f"{anchor['name']}整体复制区域",
            "order": 1,
            "policy": "fixed",
            "type": "fixed_text",
            "fill": "no",
            "content": anchor.get("text", ""),
            "style": "",
            "position": anchor.get("source_ref", ""),
            "relationship": "whole_unit_copy",
            "role_hint": "whole_unit_copy_candidate",
            "evidence": _element_evidence("fixed", anchor.get("source_ref", "")),
            "source_refs": source_refs or [anchor.get("source_ref", "")],
        }
    ]
    for entry in entries:
        text = str(entry.get("text", "")).strip()
        if not text:
            continue
        policy_hint = _element_policy(anchor["unit_id"], text, entry)
        policy = _copy_only_policy_from_hint(policy_hint)
        elements.append(
            _element_from_entry(
                anchor,
                entry,
                element_id=f"e_{len(elements) + 1:03d}",
                policy=policy,
                role_hint=_role_hint_for_policy(policy_hint),
                relationship="copy_only_internal_candidate",
                policy_hint=policy_hint,
            )
        )
    return elements


def _unit_anchors(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        unit_id, name = _unit_for_text(str(entry.get("text", "")), index)
        if unit_id is None or unit_id in seen:
            continue
        anchors.append(
            {
                "entry_index": index,
                "unit_id": unit_id,
                "name": name,
                "source_ref": entry.get("source_ref"),
                "text": entry.get("text", ""),
            }
        )
        seen.add(unit_id)
    if not anchors or anchors[0]["entry_index"] != 0:
        anchors.insert(
            0,
            {
                "entry_index": 0,
                "unit_id": "cover",
                "name": "封面",
                "source_ref": entries[0].get("source_ref"),
                "text": entries[0].get("text", ""),
            },
        )
    if "body_main" not in {anchor["unit_id"] for anchor in anchors}:
        body_index = _first_body_like_index(entries)
        anchors.append(
            {
                "entry_index": body_index,
                "unit_id": "body_main",
                "name": "正文",
                "source_ref": entries[body_index].get("source_ref"),
                "text": entries[body_index].get("text", ""),
            }
        )
    return sorted(
        _dedupe_anchors(anchors),
        key=lambda item: (int(item["entry_index"]), item["unit_id"]),
    )


def _infer_elements(anchor: dict[str, Any], entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for entry in entries:
        text = str(entry.get("text", "")).strip()
        if not text:
            continue
        policy = _element_policy(anchor["unit_id"], text, entry)
        elements.append(
            _element_from_entry(
                anchor,
                entry,
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
                "policy": fallback_policy,
                "content": anchor.get("text", ""),
                "style": "",
                "role_hint": _role_hint_for_policy(fallback_policy),
                "evidence": _element_evidence(fallback_policy, anchor.get("source_ref", "")),
                "source_refs": [anchor.get("source_ref", "")],
            }
        )
    return elements


def _element_from_entry(
    anchor: dict[str, Any],
    entry: dict[str, Any],
    *,
    element_id: str,
    policy: str,
    role_hint: str,
    relationship: str = "",
    policy_hint: str | None = None,
) -> dict[str, Any]:
    text = str(entry.get("text", "")).strip()
    source_ref = entry.get("source_ref", "")
    return {
        "element_id": element_id,
        "name": _element_name(anchor["unit_id"], text, policy_hint or policy),
        "order": int(element_id.rsplit("_", 1)[-1]),
        "policy": policy,
        "type": _element_type(policy),
        "fill": "yes" if policy == "fill" else "no",
        "content": text if policy != "remove_instruction" else "",
        "style": _style_summary(entry),
        "position": source_ref,
        "relationship": relationship,
        "role_hint": role_hint,
        "evidence": _element_evidence(policy_hint or policy, source_ref),
        "source_refs": [source_ref],
    }


def _copy_only_policy_from_hint(policy_hint: str) -> str:
    if policy_hint == "remove_instruction":
        return "remove_instruction"
    if policy_hint == "manual_only":
        return "manual_only"
    return "fixed"


def _role_hint_for_policy(policy: str) -> str:
    return {
        "remove_instruction": "instruction_candidate",
        "generated": "generated_field_candidate",
        "fill": "student_field_candidate",
        "manual_only": "manual_field_candidate",
        "fixed": "fixed_text_candidate",
    }.get(policy, "fixed_text_candidate")


def _element_evidence(policy_hint: str, source_ref: Any) -> list[dict[str, Any]]:
    return [
        {
            "kind": "source_ref",
            "value": str(source_ref or ""),
        },
        {
            "kind": "heuristic_policy_hint",
            "value": policy_hint,
        },
    ]


def _find_body_main_source_entry(
    entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    for entry in entries:
        text = str(entry.get("text") or "").strip()
        normalized = _normalize_for_match(text)
        style = str(entry.get("style") or "").lower()
        signals = entry.get("structural_signals") or {}
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
    for unit_id, name, needles in UNIT_DEFINITIONS:
        if unit_id == "cover" and index > 12:
            continue
        for needle in needles:
            if _normalize_text(needle) in normalized:
                return unit_id, name
    return None, None


def _unit_policy(unit_id: str) -> str:
    if unit_id in {"body_main", "abstract_cn", "abstract_en"}:
        return "fill"
    if unit_id in {"toc"}:
        return "generated"
    return "fixed"


def _element_policy(unit_id: str, text: str, entry: dict[str, Any]) -> str:
    lowered = text.lower()
    if _looks_like_instruction(text):
        return "remove_instruction"
    if unit_id == "toc" or any(marker.lower() in lowered for marker in GENERATED_MARKERS):
        return "generated"
    if any(marker in text for marker in MANUAL_ONLY_MARKERS):
        return "manual_only"
    if any(marker in text for marker in FILLABLE_MARKERS) and any(
        label in text for label in FILLABLE_LABELS
    ):
        return "fill"
    if unit_id in FILLABLE_CONTENT_UNIT_IDS and not _looks_like_heading(entry):
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
    return {
        "centered": paragraph.get("alignment") == "center",
        "short_text": len(text.strip()) <= 20,
        "large_font": (dominant.get("font_size_pt") or 0) >= 16,
        "bold": bool(dominant.get("bold")),
        "looks_like_instruction_text": _looks_like_instruction(text),
        "likely_unit_heading": _looks_like_heading(entry),
    }


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


def _first_body_like_index(entries: list[dict[str, Any]]) -> int:
    for index, entry in enumerate(entries):
        unit_id, _ = _unit_for_text(str(entry.get("text", "")), index)
        if unit_id == "body_main":
            return index
    return max(len(entries) - 1, 0)


def _dedupe_anchors(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for anchor in anchors:
        unit_id = str(anchor.get("unit_id"))
        if unit_id in seen:
            continue
        deduped.append(anchor)
        seen.add(unit_id)
    return deduped
