from __future__ import annotations

import re
from typing import Any

from docfit.core.io import now_iso, sha256_json
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


def build_template_structure_candidates(source_tree: dict[str, Any]) -> dict[str, Any]:
    entries = _body_entries(source_tree)
    units = _infer_units(entries)
    return {
        "artifact_type": "template_structure_candidates",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.2.0"},
        "created_at": now_iso(),
        "source_template_hash": source_tree.get("metadata", {}).get(
            "source_template_hash"
        ),
        "input_hashes": {"source_template_tree": sha256_json(source_tree)},
        "discovery_method": "deterministic_keyword_and_structure_heuristics",
        "source_context": _source_context_from_source_tree(source_tree),
        "units": units,
        "unknowns": _rule_unknowns(source_tree, units),
        "open_questions": [],
    }


def infer_template_rules(source_tree: dict[str, Any]) -> dict[str, Any]:
    return build_template_structure_candidates(source_tree)


def _body_entries(source_tree: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for item in source_tree.get("layers", {}).get("body_flow", []):
        if item.get("structure_layer") != "body_flow":
            continue
        if item.get("text"):
            entries.append(item)
    return entries


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


def _infer_units(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not entries:
        return [
            {
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
                "evidence": [],
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
        region_source_seq_refs = _source_seq_refs_for_entries(region_entries)
        units.append(
            {
                "unit_id": unit_id,
                "name": anchor["name"],
                "order": (anchor_index + 1) * 10,
                "status": "required",
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
                        "confidence": "medium",
                    }
                ],
                "responsibility_evidence": [
                    {
                        "kind": "default_unit_policy",
                        "value": _unit_policy(unit_id),
                    }
                ],
                "conflicts": [],
                "evidence": _element_evidence(
                    _unit_policy(unit_id),
                    anchor.get("source_ref", ""),
                    source_seq=anchor.get("source_seq"),
                ),
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
                "reason": "默认仅复制单元的整体保留候选区域",
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
                "source_seq": entry.get("source_seq"),
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
                "source_seq": entries[0].get("source_seq"),
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
                "source_seq": entries[body_index].get("source_seq"),
                "text": entries[body_index].get("text", ""),
            }
        )
    return sorted(
        _dedupe_anchors(anchors),
        key=lambda item: (int(item["entry_index"]), item["unit_id"]),
    )


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
