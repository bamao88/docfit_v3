from __future__ import annotations

from copy import deepcopy
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
    units = _materialize_template_units(structure_candidates.get("units", []))
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

def _materialize_template_units(candidate_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for unit in candidate_units:
        materialized = deepcopy(unit)
        generation_mode = _unit_generation_mode(materialized)
        materialized["elements"] = [
            _materialize_template_element(element, generation_mode=generation_mode)
            for element in unit.get("elements", [])
        ]
        units.append(materialized)
    return units


def _materialize_template_element(
    element: dict[str, Any],
    *,
    generation_mode: str,
) -> dict[str, Any]:
    materialized = deepcopy(element)
    candidate_policy = str(
        element.get("candidate_policy") or element.get("policy") or "fixed"
    )
    final_policy = _final_policy_for_generation(candidate_policy, generation_mode)
    materialized["candidate_policy"] = candidate_policy
    materialized["policy"] = final_policy
    materialized["type"] = _element_type(final_policy)
    materialized["fill"] = "yes" if final_policy == "fill" else "no"
    return materialized


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
