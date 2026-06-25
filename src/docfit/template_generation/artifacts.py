from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso, sha256_json


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


def build_unit_map(
    document_facts: dict[str, Any],
    structure_candidates: dict[str, Any],
) -> dict[str, Any]:
    units: list[dict[str, Any]] = []
    for unit in structure_candidates.get("units", []):
        source_seq_refs = list(unit.get("source_seq_refs", []))
        units.append(
            {
                "unit_id": unit.get("unit_id"),
                "name": unit.get("name"),
                "order": unit.get("order"),
                "status": unit.get("status", "required"),
                "source_range": unit.get("source_range", {}),
                "source_seq_range": unit.get("source_seq_range", {}),
                "source_refs": unit.get("source_refs", []),
                "source_seq_refs": source_seq_refs,
                "page_start": _page_start_for_unit(unit),
                "section_profile": _section_profile_for_unit(document_facts, source_seq_refs),
                "confidence": _unit_confidence(unit),
                "flags": _unit_flags(unit),
                "anchors": unit.get("anchors", []),
            }
        )
    flags = _map_flags(document_facts, structure_candidates)
    return {
        "artifact_type": "unit_map",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "input_hashes": {
            "document_facts": sha256_json(document_facts),
            "template_structure_candidates": sha256_json(structure_candidates),
        },
        "units": units,
        "flags": flags,
        "open_questions": _open_questions_from_flags(flags),
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
                "source_refs": element.get("source_refs", []),
                "source_seq_refs": element.get("source_seq_refs", []),
                "raw_run_ids": element.get("raw_run_ids", []),
                "logical_run_ids": element.get("logical_run_ids", []),
                "content": element.get("content", ""),
                "style": element.get("style") or element.get("style_summary", ""),
                "confidence": element.get("confidence", "medium"),
                "evidence": element.get("evidence", []),
                "flags": list(element.get("review_notes", [])),
            }
            if policy == "generated":
                spec["generated"] = {"field_type": _generated_field_type(element, unit_id)}
            if policy == "manual_only":
                spec["manual_semantics"] = _manual_semantics(element)
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
        },
        "ontology_ref": "src/docfit/template_generation/ontology.yaml",
        "elements": elements,
        "ai_traces": [],
        "flags": flags,
    }


def build_global_spec(document_facts: dict[str, Any]) -> dict[str, Any]:
    data = document_facts.get("data", {})
    sections = data.get("sections", [])
    section_profiles = [
        {
            "section_profile_id": f"section_{index:03d}",
            "source_ref": section.get("source_ref"),
            "page_setup": section,
            "header_footer_refs": section.get("header_footer_refs", {}),
        }
        for index, section in enumerate(sections, start=1)
    ]
    if not section_profiles:
        section_profiles.append(
            {
                "section_profile_id": "section_unknown",
                "source_ref": None,
                "page_setup": "UNKNOWN",
                "header_footer_refs": {},
            }
        )
    return {
        "artifact_type": "global_spec",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "input_hashes": {"document_facts": sha256_json(document_facts)},
        "section_profiles": section_profiles,
        "default_font": _default_font_from_facts(document_facts),
        "page_numbering": _page_numbering_from_facts(document_facts),
        "header_footer": data.get("headers_footers", []),
        "numbering_rules": {
            "definitions": data.get("numbering_definitions", []),
            "refs": data.get("numbering_refs", []),
        },
        "flags": _global_flags(document_facts),
    }


def build_template_spec(
    document_facts: dict[str, Any],
    unit_map: dict[str, Any],
    element_spec: dict[str, Any],
    global_spec: dict[str, Any],
) -> dict[str, Any]:
    elements_by_unit: dict[str, list[dict[str, Any]]] = {}
    for element in element_spec.get("elements", []):
        elements_by_unit.setdefault(str(element.get("unit_id")), []).append(element)

    units = []
    for unit in unit_map.get("units", []):
        unit_id = str(unit.get("unit_id"))
        units.append(
            {
                **unit,
                "elements": sorted(
                    elements_by_unit.get(unit_id, []),
                    key=lambda item: int(item.get("order") or 0),
                ),
            }
        )

    review_flags = [
        *unit_map.get("flags", []),
        *element_spec.get("flags", []),
        *global_spec.get("flags", []),
    ]
    return {
        "artifact_type": "template_spec",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "document_facts_ref": {
            "artifact": "document_facts.json",
            "hash": sha256_json(document_facts),
        },
        "input_hashes": {
            "document_facts": sha256_json(document_facts),
            "unit_map": sha256_json(unit_map),
            "element_spec": sha256_json(element_spec),
            "global_spec": sha256_json(global_spec),
        },
        "global": global_spec,
        "units": units,
        "review_flags": review_flags,
        "review_decisions": [],
    }


def template_artifact_view_from_template_spec(
    request: dict[str, Any],
    template_spec: dict[str, Any],
    *,
    fillable_template_docx: str | None = None,
    build_manifest: str | None = None,
) -> dict[str, Any]:
    slots = []
    regions = []
    protected_zones = []
    required_fields = []
    for unit in template_spec.get("units", []):
        region_id = str(unit.get("unit_id"))
        anchors = []
        for element in unit.get("elements", []):
            policy = element.get("policy")
            stable_id = str(element.get("stable_id") or f"{region_id}.{element.get('element_id')}")
            if policy == "fill":
                slot = {
                    "slot_id": stable_id,
                    "unit_id": region_id,
                    "element_id": element.get("element_id"),
                    "kind": "body_content",
                    "writable": True,
                    "required": True,
                    "accepted_content_kinds": ["heading", "paragraph", "table", "image"],
                    "source_refs": element.get("source_refs", []),
                    "source_seq_refs": element.get("source_seq_refs", []),
                    "policy": policy,
                    "sdt_tag": stable_id,
                }
                slots.append(slot)
                anchors.append(stable_id)
            elif policy == "manual_only":
                protected_zones.append(
                    {
                        "zone_id": stable_id,
                        "unit_id": region_id,
                        "element_id": element.get("element_id"),
                        "policy": policy,
                        "source_refs": element.get("source_refs", []),
                    }
                )
            elif policy == "generated":
                required_fields.append(
                    {
                        "field_id": stable_id,
                        "unit_id": region_id,
                        "element_id": element.get("element_id"),
                        "field_type": element.get("generated", {}).get("field_type"),
                        "source_refs": element.get("source_refs", []),
                    }
                )
        if anchors or region_id == "body_main":
            regions.append(
                {
                    "region_id": region_id,
                    "kind": "body",
                    "required": unit.get("status") == "required",
                    "anchors": anchors or ["slot_body_start"],
                    "source_refs": unit.get("source_refs", []),
                }
            )
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
                "source_ref": "template-spec:body-slot",
                "source_seq_refs": [],
                "policy": "fill",
                "sdt_tag": "slot_body_start",
            }
        )
    return {
        "artifact_type": "template_artifact",
        "artifact_version": "template-spec-view-1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "input_hashes": {
            "template_spec": sha256_json(template_spec),
            "template_docx": request.get("source_template_hash"),
        },
        "provenance": {
            "source_template_docx": request.get("source_template_docx"),
            "template_docx": fillable_template_docx or request.get("source_template_docx"),
            "fillable_template_docx": fillable_template_docx,
            "build_manifest": build_manifest,
            "template_spec": "template_spec.yaml",
        },
        "status_notes": [
            "template_artifact is a compatibility view over template_spec.yaml",
        ],
        "unsupported": template_spec.get("global", {}).get("flags", []),
        "data": {
            "page_setup": {"sections": template_spec.get("global", {}).get("section_profiles", [])},
            "styles": [],
            "paragraphs": [],
            "units": template_spec.get("units", []),
            "regions": regions,
            "slots": slots,
            "protected_zones": protected_zones,
            "numbering": template_spec.get("global", {}).get("numbering_rules", {}),
            "headers_footers": template_spec.get("global", {}).get("header_footer", []),
            "required_fields": required_fields,
            "unsupported": template_spec.get("review_flags", []),
        },
    }


def _page_start_for_unit(unit: dict[str, Any]) -> str:
    page = unit.get("page") or {}
    explicit = page.get("page_break") or page.get("section_isolation")
    if explicit:
        return str(explicit)
    if int(unit.get("order") or 0) <= 10:
        return "document_start"
    return "preserve_source_flow"


def _section_profile_for_unit(
    document_facts: dict[str, Any],
    source_seq_refs: list[int],
) -> str:
    sections = document_facts.get("data", {}).get("sections", [])
    if not sections:
        return "section_unknown"
    return "section_001"


def _unit_confidence(unit: dict[str, Any]) -> str:
    if unit.get("source_refs"):
        return "medium"
    return "low"


def _unit_flags(unit: dict[str, Any]) -> list[dict[str, Any]]:
    flags = []
    if not unit.get("source_refs"):
        flags.append(
            {
                "type": "unit_source_missing",
                "status": "UNKNOWN",
                "reason": "unit has no source range",
            }
        )
    if _page_start_for_unit(unit) == "UNKNOWN":
        flags.append(
            {
                "type": "page_start_unknown",
                "status": "UNKNOWN",
                "reason": "unit page start could not be determined from source facts",
            }
        )
    return flags


def _map_flags(
    document_facts: dict[str, Any],
    structure_candidates: dict[str, Any],
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for item in document_facts.get("unknown_objects", []):
        flags.append(
            {
                "type": "unknown_visible_object",
                "status": "UNKNOWN",
                "source_ref": item.get("source_ref"),
                "reason": item.get("reason", "unknown visible object"),
            }
        )
    for item in structure_candidates.get("unknowns", []):
        flags.append(
            {
                "type": "unit_discovery_unknown",
                "status": "UNKNOWN",
                "source_ref": item.get("source_ref"),
                "reason": item.get("reason"),
            }
        )
    return flags


def _open_questions_from_flags(flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "question_id": f"q_{index:03d}",
            "source_ref": flag.get("source_ref"),
            "reason": flag.get("reason"),
        }
        for index, flag in enumerate(flags, start=1)
    ]


def _canonical_policy(policy: str) -> str:
    return {
        "fixed": "fixed",
        "fill": "fill",
        "generated": "generated",
        "manual_only": "manual_only",
        "remove_instruction": "instruction_remove",
        "template_default": "template_default",
    }.get(policy, "fixed")


def _role_for_element(element: dict[str, Any], policy: str) -> str:
    role_hint = str(element.get("role_hint") or "")
    return {
        "instruction_candidate": "template_instruction",
        "student_field_candidate": "student_content",
        "generated_field_candidate": "generated_field",
        "manual_field_candidate": "manual_field",
        "fixed_text_candidate": "template_fixed",
        "copy_region_candidate": "template_fixed",
    }.get(role_hint, {
        "fill": "student_content",
        "generated": "generated_field",
        "manual_only": "manual_field",
        "instruction_remove": "template_instruction",
    }.get(policy, "template_fixed"))


def _fill_source_for_policy(policy: str, element: dict[str, Any]) -> str | None:
    if policy == "fill":
        return "student_content"
    if policy == "manual_only":
        return "manual"
    if policy == "generated":
        return "generated_field"
    return None


def _generated_field_type(element: dict[str, Any], unit_id: str) -> str:
    text = str(element.get("content") or element.get("name") or "").lower()
    if "seq" in text or "编号" in text:
        return "SEQ"
    if "页码" in text or "page" in text:
        return "PAGE"
    if unit_id == "toc" or "目录" in text or "toc" in text:
        return "TOC"
    return "FIELD_PLACEHOLDER"


def _manual_semantics(element: dict[str, Any]) -> str:
    content = str(element.get("content") or element.get("name") or "").strip()
    return content or "manual human input required"


def _default_font_from_facts(document_facts: dict[str, Any]) -> dict[str, Any]:
    for run in document_facts.get("runs", []):
        style = run.get("effective_style") or {}
        if style.get("font_names") or style.get("font_size_pt"):
            return {
                "font_names": style.get("font_names", []),
                "font_size_pt": style.get("font_size_pt"),
                "source_run_id": run.get("raw_run_id"),
            }
    return {"status": "UNKNOWN"}


def _page_numbering_from_facts(document_facts: dict[str, Any]) -> dict[str, Any]:
    fields = document_facts.get("data", {}).get("fields", [])
    page_fields = [field for field in fields if str(field.get("field_code", "")).upper().startswith("PAGE")]
    return {
        "field_refs": [field.get("source_ref") for field in page_fields],
        "status": "detected" if page_fields else "UNKNOWN",
    }


def _global_flags(document_facts: dict[str, Any]) -> list[dict[str, Any]]:
    flags = []
    if not document_facts.get("data", {}).get("sections"):
        flags.append(
            {
                "type": "sections_missing",
                "status": "UNKNOWN",
                "reason": "document sections could not be parsed",
            }
        )
    return flags
