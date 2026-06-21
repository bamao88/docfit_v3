from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso, sha256_json
from docfit.harness import template_units

from .plan import _decision_reason
from .refs import _first_source_ref, _paragraph_index
from .structure_candidates import (
    _body_entries,
    _looks_like_instruction,
    _unit_is_copy_only_by_default,
)
from .text_utils import _dedupe_by_key, _normalize_for_match


def build_template_artifact(
    request: dict[str, Any],
    source_tree: dict[str, Any],
    discovered_rules: dict[str, Any],
) -> dict[str, Any]:
    units = discovered_rules.get("units", [])
    paragraphs = source_tree.get("data", {}).get("paragraphs", [])
    copy_only_source_refs = _copy_only_unit_source_refs(units)
    instruction_paragraphs = _dedupe_by_key(
        [
            *_instruction_paragraphs_from_units(units),
            *_instruction_paragraphs_from_source_tree(
                source_tree,
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
                "policy": "fill",
            }
        )
    return {
        "artifact_type": "template_artifact",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.2.0"},
        "created_at": now_iso(),
        "input_hashes": {
            "template_docx": request.get("source_template_hash"),
            "source_template_tree": sha256_json(source_tree),
            "discovered_template_rules": sha256_json(discovered_rules),
        },
        "provenance": {"template_docx": request.get("source_template_docx")},
        "status_notes": [
            "units are inferred from source Word structure and deterministic keywords",
            "formal quality still requires template-gap against accepted standards",
        ],
        "data": {
            "source_template_tree": "source_template_tree.json",
            "discovered_template_rules": "discovered_template_rules.json",
            "page_setup": {
                "sections": source_tree.get("layers", {}).get("section_rules", [])
            },
            "styles": _style_inventory(source_tree),
            "paragraphs": paragraphs,
            "units": units,
            "instruction_paragraphs": instruction_paragraphs,
            "regions": regions,
            "slots": slots,
            "protected_zones": template_units.protected_zones_from_units(units),
            "numbering": source_tree.get("data", {}).get("numbering_definitions", []),
            "headers_footers": source_tree.get("layers", {}).get("header_footer", []),
            "required_fields": template_units.required_fields_from_units(units),
            "unsupported": source_tree.get("layers", {}).get("unknown_objects", []),
        },
    }


def build_template_unit_decisions(template_artifact: dict[str, Any]) -> dict[str, Any]:
    units: list[dict[str, Any]] = []
    for unit in template_artifact.get("data", {}).get("units", []):
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
                    "copy_scope": "whole_unit",
                    "reason": "this unit can be preserved by the initial source DOCX copy",
                }
            )
        else:
            for element in unit.get("elements", []):
                policy = element.get("policy")
                element_id = element.get("element_id")
                source_ref = _first_source_ref(element)
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
                        "reason": _decision_reason(decision_type),
                    }
                )
        units.append(
            {
                "unit_id": unit_id,
                "unit_name": unit.get("name"),
                "source_policy": unit.get("policy"),
                "generation_mode": generation_mode,
                "generation_policy": "whole_unit_copy"
                if generation_mode == "whole_unit_copy"
                else "unit_actions",
                "copy_source_ref": unit_anchor_ref,
                "decisions": decisions,
                "unresolved_questions": [],
            }
        )
    return {
        "artifact_type": "template_unit_decisions",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.2.0"},
        "created_at": now_iso(),
        "input_hashes": {"template_artifact": sha256_json(template_artifact)},
        "units": units,
    }


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
            source_ref = _first_source_ref(element)
            paragraph_index = _paragraph_index(source_ref)
            if paragraph_index is None:
                continue
            paragraphs.append(
                {
                    "source_ref": source_ref,
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


def _instruction_paragraphs_from_source_tree(
    source_tree: dict[str, Any],
    *,
    excluded_source_refs: set[str] | None = None,
) -> list[dict[str, Any]]:
    excluded_source_refs = excluded_source_refs or set()
    paragraphs: list[dict[str, Any]] = []
    for entry in _body_entries(source_tree):
        text = str(entry.get("text", ""))
        if not _looks_like_instruction(text):
            continue
        source_ref = entry.get("source_ref")
        if not source_ref:
            continue
        if str(source_ref) in excluded_source_refs:
            continue
        paragraphs.append(
            {
                "source_ref": source_ref,
                "paragraph_index": _paragraph_index(source_ref),
                "text": text,
                "policy": "strip",
                "final_disposition": "omit_from_final",
                "reason": "detected template instruction text should not appear in the generated fillable template",
            }
        )
    return paragraphs


def _style_inventory(source_tree: dict[str, Any]) -> list[dict[str, Any]]:
    styles: dict[str, dict[str, Any]] = {}
    for paragraph in source_tree.get("data", {}).get("paragraphs", []):
        style = paragraph.get("style")
        if not style:
            continue
        styles.setdefault(str(style), {"name": style, "count": 0})
        styles[str(style)]["count"] += 1
    return list(styles.values())


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
