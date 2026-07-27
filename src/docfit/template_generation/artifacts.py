from __future__ import annotations

import hashlib
import re
from typing import Any

from docfit.core.io import now_iso, sha256_json

from .stage_inputs import l1_artifact_hash
from .final_results import (
    FinalStageResult,
    conservative_availability,
    publish_final_stage_result,
    require_final_stage_result,
)

from .constants import FILLABLE_LABELS, FILLABLE_MARKERS
from .page_policy import normalize_unit_page_policy
from .refs import _paragraph_index, _part_name


def source_tree_from_document_facts(document_facts: dict[str, Any]) -> dict[str, Any]:
    data = document_facts.get("data", {})
    body_flow = document_facts.get("body_flow", [])
    return {
        "artifact_type": "source_template_tree",
        "artifact_version": "legacy-view-1.0",
        "producer": {
            "name": "docfit-template-generate",
            "version": "0.3.0",
            "view_of": "document_facts",
        },
        "created_at": document_facts.get("created_at") or now_iso(),
        "metadata": document_facts.get("metadata", {}),
        "layers": {
            "package_global": {
                "numbering_definitions": data.get("numbering_definitions", []),
            },
            "section_rules": data.get("sections", []),
            "header_footer": data.get("headers_footers", []),
            "body_flow": body_flow,
            "embedded_resources": data.get("images", []),
            "unknown_objects": document_facts.get("unknown_objects", []),
        },
        "indexes": document_facts.get("indexes", {}),
        "warnings": document_facts.get("warnings", []),
        "data": data,
    }


def build_element_spec(generation_model: dict[str, Any]) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []
    for unit in generation_model.get("units", []):
        unit_id = str(unit.get("unit_id") or "")
        for element in unit.get("elements", []):
            policy = _canonical_policy(str(element.get("policy") or "fixed"))
            element_id = str(element.get("element_id") or "")
            spec = {
                "element_id": element_id,
                "unit_id": unit_id,
                "stable_id": f"{unit_id}.{element_id}" if unit_id and element_id else element_id,
                "order": element.get("order"),
                "policy": policy,
                "role": _role_for_element(element, policy),
                "fill_source": _fill_source_for_policy(policy, element),
                "fill_field": element.get("fill_field"),
                "removal_reason": element.get("removal_reason"),
                "source_refs": element.get("source_refs", []),
                "source_seq_refs": element.get("source_seq_refs", []),
                "raw_run_ids": element.get("raw_run_ids", []),
                "logical_run_ids": element.get("logical_run_ids", []),
                "content": element.get("content", ""),
                "style": element.get("style") or element.get("style_summary", ""),
                "spans": list(element.get("spans", []) or []),
                "confidence": _element_confidence(
                    policy,
                    element.get("content", ""),
                    str(element.get("role_hint") or ""),
                ),
                "evidence": element.get("evidence", []),
                "agent_traces": list(element.get("agent_traces", []) or []),
                "flags": list(element.get("review_notes", [])),
            }
            confidence_flag = _confidence_flag(
                flag_id=f"{unit_id}.{element_id}.confidence_needs_review",
                type_="element_confidence_needs_review",
                confidence=str(spec.get("confidence") or ""),
                reason_subject=f"element {unit_id}.{element_id}",
                source_ref=(spec.get("source_refs") or [None])[0],
                affected_id=spec["stable_id"],
            )
            if confidence_flag is not None:
                spec["flags"].append(confidence_flag)
                flags.append(confidence_flag)
            if policy == "generated":
                spec["generated"] = {
                    "field_type": _generated_field_type(element, unit)
                }
            if policy == "fill" and not spec["fill_source"]:
                flags.append(
                    {
                        "flag_id": f"{unit_id}.{element_id}.fill_source_missing",
                        "severity": "blocking",
                        "status": "FAIL",
                        "reason": "fill element has no fill_source",
                    }
                )
            elements.append(spec)
    return {
        "artifact_type": "element_spec",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "input_hashes": {
            "template_generation_model": sha256_json(generation_model),
            **(
                {"l1": generation_model.get("input_hashes", {}).get("l1")}
                if generation_model.get("input_hashes", {}).get("l1")
                else {}
            ),
        },
        "ontology_ref": "src/docfit/template_generation/ontology.yaml",
        "elements": elements,
        "ai_traces": [
            {
                "unit_id": element.get("unit_id"),
                "element_id": element.get("element_id"),
                **trace,
            }
            for element in elements
            for trace in element.get("agent_traces", []) or []
            if isinstance(trace, dict)
        ],
        "flags": flags,
    }


def build_template_spec(
    l1_final: FinalStageResult,
    t2_final: FinalStageResult,
    t3_final: FinalStageResult,
    t4_final: FinalStageResult,
) -> FinalStageResult:
    l1_result = require_final_stage_result(
        l1_final,
        stage_id="L1",
        artifact_type="template_generation_l1_input_contract",
        artifact_name="01.5_l1_input_contract.json",
    )
    unit_result = require_final_stage_result(
        t2_final,
        stage_id="T2",
        artifact_type="unit_map",
        artifact_name="02_unit_map.yaml",
        expected_l1_hash=l1_result.sha256,
    )
    element_result = require_final_stage_result(
        t3_final,
        stage_id="T3",
        artifact_type="element_spec",
        artifact_name="03_element_spec.yaml",
        expected_l1_hash=l1_result.sha256,
    )
    global_result = require_final_stage_result(
        t4_final,
        stage_id="T4",
        artifact_type="global_spec",
        artifact_name="04_global_spec.yaml",
        expected_l1_hash=l1_result.sha256,
    )
    payload = _build_template_spec_payload(
        l1_result.payload,
        unit_result.payload,
        element_result.payload,
        global_result.payload,
    )
    availability, reason = conservative_availability(
        unit_result,
        element_result,
        global_result,
    )
    return publish_final_stage_result(
        payload,
        stage_id="T5",
        artifact_type="template_spec",
        artifact_name="05_template_spec.yaml",
        availability=availability,
        reason=reason,
        producer_mode="code",
        input_refs={
            "l1": l1_result.input_ref(),
            "t2_final": unit_result.input_ref(),
            "t3_final": element_result.input_ref(),
            "t4_final": global_result.input_ref(),
        },
    )


def _build_template_spec_payload(
    l1_input_contract: dict[str, Any],
    unit_map: dict[str, Any],
    element_spec: dict[str, Any],
    global_spec: dict[str, Any],
) -> dict[str, Any]:
    elements_by_unit: dict[str, list[dict[str, Any]]] = {}
    for element in element_spec.get("elements", []):
        elements_by_unit.setdefault(str(element.get("unit_id")), []).append(element)

    section_bindings = bind_units_to_section_profiles(unit_map, global_spec)
    units = []
    for unit_index, unit in enumerate(unit_map.get("units", [])):
        unit_id = str(unit.get("unit_id"))
        section_profile_refs = section_bindings["bindings_by_unit_index"][unit_index]
        primary_section_profile = _primary_section_profile_from_refs(
            section_profile_refs,
            fallback=str(unit.get("section_profile") or "section_unknown"),
        )
        page_policy = normalize_unit_page_policy(
            unit.get("page_policy"),
            document_start=unit_index == 0,
        )
        units.append(
            {
                **{key: value for key, value in unit.items() if key != "page"},
                "page_policy": page_policy,
                "section_profile": primary_section_profile,
                "section_profile_refs": section_profile_refs,
                "elements": sorted(
                    elements_by_unit.get(unit_id, []),
                    key=lambda item: int(item.get("order") or 0),
                ),
            }
        )

    review_flags = [
        *unit_map.get("flags", []),
        *element_spec.get("flags", []),
        *section_bindings["flags"],
    ]
    return {
        "artifact_type": "template_spec",
        "artifact_version": "1.1",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "l1_input_contract_ref": {
            "artifact": "01.5_l1_input_contract.json",
            "hash": l1_artifact_hash(l1_input_contract),
        },
        "input_hashes": {
            "l1": l1_artifact_hash(l1_input_contract),
            "document_facts": l1_input_contract.get("input_hashes", {}).get(
                "document_facts"
            ),
            "unit_map": sha256_json(unit_map),
            "element_spec": sha256_json(element_spec),
            "global_spec": sha256_json(global_spec),
        },
        "global": global_spec,
        "units": units,
        "review_flags": review_flags,
        "review_decisions": [],
    }


def bind_units_to_section_profiles(
    unit_map: dict[str, Any],
    global_spec: dict[str, Any],
) -> dict[str, Any]:
    section_profiles = list(global_spec.get("section_profiles", []))
    bindings_by_unit_id: dict[str, list[dict[str, Any]]] = {}
    bindings_by_unit_index: list[list[dict[str, Any]]] = []
    flags: list[dict[str, Any]] = []
    for unit in unit_map.get("units", []):
        unit_id = str(unit.get("unit_id") or "")
        source_seq_refs = _unit_source_seq_refs(unit)
        refs = _section_profile_refs_for_source_seq_refs(
            source_seq_refs,
            section_profiles,
        )
        if not refs:
            refs = _section_profile_refs_for_source_refs(
                list(unit.get("source_refs", []) or []),
                section_profiles,
            )
        bindings_by_unit_index.append(refs)
        bindings_by_unit_id.setdefault(unit_id, refs)
        if not refs:
            flags.append(
                {
                    "flag_id": f"{unit_id}.section_profile_unmapped",
                    "type": "unit_section_profile_unmapped",
                    "status": "UNKNOWN",
                    "affected_ids": [unit_id] if unit_id else [],
                    "reason": "unit source_seq range does not overlap any section profile boundary",
                }
            )
        elif len(refs) > 1:
            flags.append(
                {
                    "flag_id": f"{unit_id}.section_profile_cross_section",
                    "type": "unit_crosses_section_profiles",
                    "status": "UNKNOWN",
                    "source_ref": (unit.get("source_refs") or [None])[0],
                    "affected_ids": [unit_id] if unit_id else [],
                    "reason": "unit source_seq range overlaps multiple section profiles",
                }
            )
    return {
        "bindings_by_unit_id": bindings_by_unit_id,
        "bindings_by_unit_index": bindings_by_unit_index,
        "flags": flags,
    }


def _unit_source_seq_refs(unit: dict[str, Any]) -> list[int]:
    refs = [
        int(ref)
        for ref in unit.get("source_seq_refs", [])
        if _int_or_none(ref) is not None
    ]
    if refs:
        return refs
    source_seq_range = unit.get("source_seq_range") or {}
    start = _int_or_none(source_seq_range.get("start"))
    end = _int_or_none(source_seq_range.get("end"))
    if start is None or end is None:
        return []
    return list(range(start, end + 1))


def _section_profile_refs_for_source_seq_refs(
    source_seq_refs: list[int],
    section_profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not source_seq_refs:
        return []
    unit_range = {
        "start": min(source_seq_refs),
        "end": max(source_seq_refs),
    }
    refs = []
    for profile in section_profiles:
        profile_range = _profile_source_seq_range(profile)
        overlap = _overlap_range(unit_range, profile_range)
        if overlap is None:
            continue
        profile_id = str(profile.get("section_profile_id") or "section_unknown")
        refs.append(
            {
                "section_profile_id": profile_id,
                "overlap_source_seq_range": overlap,
                "page_numbering": {
                    "inherited_from": profile_id,
                    "declared": profile.get("page_numbering", {}).get("declared", {}),
                    "display": profile.get("page_numbering", {}).get("display", {}),
                },
                "header_footer": {"inherited_from": profile_id},
            }
        )
    return refs


def _section_profile_refs_for_source_refs(
    source_refs: list[str],
    section_profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    paragraph_indices = [
        parsed
        for source_ref in source_refs
        if (parsed := _paragraph_index_from_source_ref(str(source_ref))) is not None
    ]
    if not paragraph_indices:
        return []
    unit_range = {"start": min(paragraph_indices), "end": max(paragraph_indices)}
    refs = []
    for profile in section_profiles:
        boundary = profile.get("boundary") or {}
        start = _int_or_none(boundary.get("start_paragraph_index"))
        end = _int_or_none(boundary.get("end_paragraph_index"))
        if start is None or end is None:
            continue
        overlap = _overlap_range(unit_range, {"start": start, "end": end})
        if overlap is None:
            continue
        profile_id = str(profile.get("section_profile_id") or "section_unknown")
        refs.append(
            {
                "section_profile_id": profile_id,
                "overlap_paragraph_range": overlap,
                "page_numbering": {
                    "inherited_from": profile_id,
                    "declared": profile.get("page_numbering", {}).get("declared", {}),
                    "display": profile.get("page_numbering", {}).get("display", {}),
                },
                "header_footer": {"inherited_from": profile_id},
            }
        )
    return refs


def _paragraph_index_from_source_ref(source_ref: str) -> int | None:
    match = re.search(r":p\[(\d+)\]", source_ref)
    if not match:
        return None
    return _int_or_none(match.group(1))


def _profile_source_seq_range(profile: dict[str, Any]) -> dict[str, int] | None:
    boundary = profile.get("boundary") or {}
    start = _int_or_none(boundary.get("start_source_seq"))
    end = _int_or_none(boundary.get("end_source_seq"))
    if start is None or end is None:
        return None
    return {"start": start, "end": end}


def _overlap_range(
    left: dict[str, int] | None,
    right: dict[str, int] | None,
) -> dict[str, int] | None:
    if left is None or right is None:
        return None
    start = max(int(left["start"]), int(right["start"]))
    end = min(int(left["end"]), int(right["end"]))
    if start > end:
        return None
    return {"start": start, "end": end}


def _primary_section_profile_from_refs(
    refs: list[dict[str, Any]],
    *,
    fallback: str,
) -> str:
    if not refs:
        return fallback
    best = max(
        refs,
        key=lambda ref: (
            int(ref.get("overlap_source_seq_range", {}).get("end") or 0)
            - int(ref.get("overlap_source_seq_range", {}).get("start") or 0),
            -len(refs),
        ),
    )
    return str(best.get("section_profile_id") or fallback)


def _element_confidence(policy: str, content: Any, role_hint: str) -> str:
    """Grade evidence strength for an element's FINAL (canonical) policy.

    high   = an explicit deterministic marker decided the policy, or the element
             is non-empty verbatim fixed text that is safe to auto-pass.
    medium = policy inferred without an explicit marker, OR the resolved policy
             disagrees with the upstream role hint (a fill/generated candidate
             collapsed to ``fixed`` by whole-unit copy). These stay reviewable
             instead of being silently auto-passed (see T3-ISSUE-002).
    low    = no positive evidence (empty / spacing-only fixed text).
    """
    text = str(content or "")
    # Role hint vs final policy disagreement: a student/generated field that was
    # downgraded to fixed must remain visible for review, not auto-pass as high.
    if policy in {"fixed", "template_default"} and role_hint in {
        "student_field_candidate",
        "generated_field_candidate",
    }:
        return "medium"
    if policy == "instruction_remove":
        # Only assigned upstream when an instruction marker / format annotation fired.
        return "high"
    if policy == "generated":
        return "high"
    if policy == "fill":
        has_marker = any(marker in text for marker in FILLABLE_MARKERS)
        has_label = any(label in text for label in FILLABLE_LABELS)
        return "high" if has_marker and has_label else "medium"
    # fixed / template_default
    if not text.strip():
        return "low"
    return "high"


def _confidence_flag(
    *,
    flag_id: str,
    type_: str,
    confidence: str,
    reason_subject: str,
    source_ref: Any,
    affected_id: str,
) -> dict[str, Any] | None:
    normalized = str(confidence or "").lower()
    if normalized in {"", "high"}:
        return None
    return {
        "flag_id": flag_id,
        "type": type_,
        "status": "UNKNOWN",
        "confidence": normalized,
        "source_ref": source_ref,
        "affected_ids": [affected_id] if affected_id else [],
        "reason": f"{reason_subject} confidence={normalized} requires review",
    }


def _canonical_policy(policy: str) -> str:
    return {
        "fixed": "fixed",
        "fill": "fill",
        "generated": "generated",
        "remove_instruction": "instruction_remove",
        "template_default": "template_default",
        # unknown 只属于 T3 判断层；生成 element_spec 时已进入执行层，
        # 因此必须保守降级为 fixed（keep）。
        "unknown": "fixed",
    }.get(policy, "fixed")


def _role_for_element(element: dict[str, Any], policy: str) -> str:
    role_hint = str(element.get("role_hint") or "")
    return {
        "instruction_candidate": "template_instruction",
        "student_field_candidate": "student_content",
        "generated_field_candidate": "generated_field",
        "fixed_text_candidate": "template_fixed",
        "copy_region_candidate": "template_fixed",
    }.get(role_hint, {
        "fill": "student_content",
        "generated": "generated_field",
        "fixed": "template_fixed",
        "instruction_remove": "template_instruction",
    }.get(policy, "template_fixed"))


def _fill_source_for_policy(policy: str, element: dict[str, Any]) -> str | None:
    if policy == "fill":
        return "student_content"
    if policy == "generated":
        return "generated_field"
    return None


def _generated_field_type(
    element: dict[str, Any],
    unit: dict[str, Any],
) -> str:
    text = str(element.get("content") or element.get("name") or "").lower()
    if "seq" in text or "编号" in text:
        return "SEQ"
    if "页码" in text or "page" in text:
        return "PAGE"
    unit_name = re.sub(
        r"\s+",
        "",
        str(unit.get("unit_name") or unit.get("name") or "").lower(),
    )
    if (
        unit_name in {"目录", "tableofcontents"}
        or "目录" in text
        or "toc" in text
    ):
        return "TOC"
    return "FIELD_PLACEHOLDER"


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
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


def _text_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
