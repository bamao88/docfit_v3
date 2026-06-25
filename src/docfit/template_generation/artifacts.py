from __future__ import annotations

import hashlib
from typing import Any

from docfit.core.io import now_iso, sha256_json

from .constants import FILLABLE_LABELS, FILLABLE_MARKERS, MANUAL_ONLY_MARKERS
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


def build_unit_map(
    document_facts: dict[str, Any],
    structure_candidates: dict[str, Any],
) -> dict[str, Any]:
    section_profiles = _section_profiles_from_facts(document_facts)
    units: list[dict[str, Any]] = []
    for unit in structure_candidates.get("units", []):
        source_seq_refs = list(unit.get("source_seq_refs", []))
        confidence = _unit_confidence(unit)
        flags = _unit_flags(unit, confidence=confidence)
        mapped_unit = {
            "unit_id": unit.get("unit_id"),
            "name": unit.get("name"),
            "order": unit.get("order"),
            "status": unit.get("status", "required"),
            "label_status": unit.get("label_status"),
            "canonical_label_id": unit.get("canonical_label_id"),
            "raw_title": unit.get("raw_title"),
            "normalized_title": unit.get("normalized_title"),
            "display_name": unit.get("display_name"),
            "source_range": unit.get("source_range", {}),
            "source_seq_range": unit.get("source_seq_range", {}),
            "source_refs": unit.get("source_refs", []),
            "source_seq_refs": source_seq_refs,
            "page_start": _page_start_for_unit(unit),
            "section_profile": _section_profile_for_unit(
                section_profiles,
                source_seq_refs,
            ),
            "confidence": confidence,
            "flags": flags,
            "anchors": unit.get("anchors", []),
            "evidence": unit.get("evidence", []),
        }
        if unit.get("container"):
            mapped_unit["container"] = unit.get("container")
        units.append(mapped_unit)
    flags = [
        *_map_flags(document_facts, structure_candidates),
        *[
            flag
            for mapped_unit in units
            for flag in mapped_unit.get("flags", [])
        ],
    ]
    return {
        "artifact_type": "unit_map",
        "artifact_version": "1.1",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "input_hashes": {
            "document_facts": sha256_json(document_facts),
            "template_structure_candidates": sha256_json(structure_candidates),
        },
        "units": units,
        "flags": flags,
        "open_questions": _unit_map_open_questions(structure_candidates, flags),
        "taxonomy_review_queue": structure_candidates.get("taxonomy_review_queue", []),
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
                "confidence": _element_confidence(
                    policy,
                    element.get("content", ""),
                    str(element.get("role_hint") or ""),
                ),
                "evidence": element.get("evidence", []),
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
    section_profiles = _section_profiles_from_facts(document_facts)
    return {
        "artifact_type": "global_spec",
        "artifact_version": "1.1",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "input_hashes": {"document_facts": sha256_json(document_facts)},
        "section_profiles": section_profiles,
        "default_font": _default_font_from_facts(document_facts),
        "page_numbering": _page_numbering_from_profiles(section_profiles),
        "header_footer": data.get("headers_footers", []),
        "numbering_rules": {
            "definitions": data.get("numbering_definitions", []),
            "refs": data.get("numbering_refs", []),
        },
        "flags": _global_flags(document_facts, section_profiles),
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

    section_bindings = bind_units_to_section_profiles(unit_map, global_spec)
    units = []
    for unit_index, unit in enumerate(unit_map.get("units", [])):
        unit_id = str(unit.get("unit_id"))
        section_profile_refs = section_bindings["bindings_by_unit_index"][unit_index]
        primary_section_profile = _primary_section_profile_from_refs(
            section_profile_refs,
            fallback=str(unit.get("section_profile") or "section_unknown"),
        )
        units.append(
            {
                **unit,
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
    section_profiles: list[dict[str, Any]],
    source_seq_refs: list[int],
) -> str:
    refs = _section_profile_refs_for_source_seq_refs(source_seq_refs, section_profiles)
    return _primary_section_profile_from_refs(refs, fallback="section_unknown")


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


def _section_profiles_from_facts(document_facts: dict[str, Any]) -> list[dict[str, Any]]:
    data = document_facts.get("data", {})
    sections = list(data.get("sections", []))
    if not sections:
        return [_unknown_section_profile()]

    boundaries = _section_boundaries_from_facts(document_facts)
    parts_by_name = {
        str(part.get("part_name")): part
        for part in data.get("headers_footers", [])
        if part.get("part_name")
    }
    profiles: list[dict[str, Any]] = []
    for index, section in enumerate(sections, start=1):
        profile_id = f"section_{index:03d}"
        boundary = boundaries.get(index, _unknown_boundary(section.get("source_ref")))
        effective_refs = list(section.get("effective_references", []))
        page_fields = _page_fields_for_section(document_facts, boundary, effective_refs)
        page_numbering = _section_page_numbering(
            section,
            boundary=boundary,
            effective_refs=effective_refs,
            page_fields=page_fields,
        )
        flags = []
        if boundary.get("status") == "UNKNOWN":
            flags.append(
                {
                    "flag_id": f"{profile_id}.boundary_unknown",
                    "type": "section_boundary_unknown",
                    "status": "UNKNOWN",
                    "source_ref": section.get("source_ref"),
                    "affected_ids": [profile_id],
                    "reason": "section boundary source_seq range could not be determined",
                }
            )
        if page_numbering.get("display", {}).get("status") == "missing_evidence":
            flags.append(
                {
                    "flag_id": f"{profile_id}.page_numbering_missing_evidence",
                    "type": "section_page_numbering_missing_evidence",
                    "status": "UNKNOWN",
                    "source_ref": section.get("source_ref"),
                    "affected_ids": [f"{profile_id}.page_numbering"],
                    "reason": "section page numbering evidence could not be checked",
                }
            )
        profiles.append(
            {
                "section_profile_id": profile_id,
                "source_ref": section.get("source_ref"),
                "boundary": boundary,
                "page_setup": section,
                "header_footer_refs": section.get("header_footer_refs", {}),
                "header_footer": {
                    "references": list(section.get("references", [])),
                    "effective_references": effective_refs,
                    "parts": _header_footer_parts_for_refs(effective_refs, parts_by_name),
                },
                "page_numbering": page_numbering,
                "flags": flags,
            }
        )
    return profiles


def _unknown_section_profile() -> dict[str, Any]:
    return {
        "section_profile_id": "section_unknown",
        "source_ref": None,
        "boundary": _unknown_boundary(None),
        "page_setup": "UNKNOWN",
        "header_footer_refs": {},
        "header_footer": {
            "references": [],
            "effective_references": [],
            "parts": [],
        },
        "page_numbering": {
            "declared": {"status": "missing_evidence"},
            "fields": [],
            "display": {
                "status": "missing_evidence",
                "has_page_field": False,
                "confidence": "low",
                "checked_scopes": {},
            },
        },
        "flags": [
            {
                "flag_id": "section_unknown.boundary_unknown",
                "type": "section_boundary_unknown",
                "status": "UNKNOWN",
                "affected_ids": ["section_unknown"],
                "reason": "document sections could not be parsed",
            }
        ],
    }


def _section_boundaries_from_facts(document_facts: dict[str, Any]) -> dict[int, dict[str, Any]]:
    sections = list(document_facts.get("data", {}).get("sections", []))
    items = _body_source_seq_items(document_facts)
    paragraph_indices = [
        int(item["paragraph_index"])
        for item in items
        if item.get("paragraph_index") is not None
    ]
    section_paragraph_indices = [
        int(paragraph_index)
        for section in sections
        if (paragraph_index := _int_or_none(section.get("paragraph_index"))) is not None
    ]
    min_paragraph = min(paragraph_indices) if paragraph_indices else None
    max_paragraph = max(
        [*paragraph_indices, *section_paragraph_indices],
        default=None,
    )
    boundaries: dict[int, dict[str, Any]] = {}
    previous_end: int | None = None
    for index, section in enumerate(sections, start=1):
        section_end = _int_or_none(section.get("paragraph_index"))
        end_reason = "sectPr" if section_end is not None else "body_sectPr"
        if section_end is not None:
            end_paragraph = section_end
        elif max_paragraph is not None and previous_end is not None:
            end_paragraph = max(max_paragraph, previous_end + 1)
        else:
            end_paragraph = max_paragraph
        start_paragraph = (
            previous_end + 1
            if previous_end is not None
            else min_paragraph
        )
        section_items = _items_in_paragraph_range(
            items,
            start_paragraph=start_paragraph,
            end_paragraph=end_paragraph,
        )
        source_seq_refs = [
            int(item["source_seq"])
            for item in section_items
            if item.get("source_seq") is not None
        ]
        evidence_refs = _dedupe_str(
            [
                section.get("source_ref"),
                section_items[0].get("source_ref") if section_items else None,
                section_items[-1].get("source_ref") if section_items else None,
            ]
        )
        detected = (
            start_paragraph is not None
            and end_paragraph is not None
            and bool(source_seq_refs)
        )
        boundary = {
            "status": "detected" if detected else "UNKNOWN",
            "start_paragraph_index": start_paragraph,
            "end_paragraph_index": end_paragraph,
            "start_source_seq": min(source_seq_refs) if source_seq_refs else None,
            "end_source_seq": max(source_seq_refs) if source_seq_refs else None,
            "end_reason": end_reason,
            "confidence": "high" if detected else "low",
            "evidence_refs": evidence_refs,
        }
        boundaries[index] = boundary
        if end_paragraph is not None:
            previous_end = end_paragraph
    return boundaries


def _body_source_seq_items(document_facts: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in document_facts.get("body_flow", []):
        source_ref = str(item.get("source_ref") or "")
        part_name = str(item.get("part_name") or _part_name(source_ref))
        if part_name != "word/document.xml":
            continue
        source_seq = _int_or_none(item.get("source_seq"))
        if source_seq is None:
            continue
        paragraph_index = _flow_paragraph_index(item)
        items.append(
            {
                "source_seq": source_seq,
                "source_ref": source_ref,
                "paragraph_index": paragraph_index,
            }
        )
    return sorted(items, key=lambda item: int(item["source_seq"]))


def _flow_paragraph_index(item: dict[str, Any]) -> int | None:
    source_ref = str(item.get("source_ref") or "")
    paragraph_index = _paragraph_index(source_ref)
    if paragraph_index is not None:
        return paragraph_index
    paragraph_id = str(item.get("paragraph_id") or "")
    if paragraph_id.startswith("p_"):
        return _int_or_none(paragraph_id.removeprefix("p_"))
    return None


def _items_in_paragraph_range(
    items: list[dict[str, Any]],
    *,
    start_paragraph: int | None,
    end_paragraph: int | None,
) -> list[dict[str, Any]]:
    if start_paragraph is None or end_paragraph is None:
        return []
    return [
        item
        for item in items
        if item.get("paragraph_index") is not None
        and start_paragraph <= int(item["paragraph_index"]) <= end_paragraph
    ]


def _unknown_boundary(source_ref: Any) -> dict[str, Any]:
    return {
        "status": "UNKNOWN",
        "start_paragraph_index": None,
        "end_paragraph_index": None,
        "start_source_seq": None,
        "end_source_seq": None,
        "end_reason": "UNKNOWN",
        "confidence": "low",
        "evidence_refs": _dedupe_str([source_ref]),
    }


def _header_footer_parts_for_refs(
    effective_refs: list[dict[str, Any]],
    parts_by_name: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    parts = []
    seen: set[str] = set()
    for ref in effective_refs:
        part_name = str(ref.get("part_name") or "")
        if not part_name or part_name in seen:
            continue
        part = parts_by_name.get(part_name)
        if not part:
            continue
        text = str(part.get("text") or "")
        parts.append(
            {
                "part_name": part_name,
                "kind": part.get("kind") or ref.get("kind"),
                "source_ref": part.get("source_ref") or part_name,
                "text_hash": _text_hash(text),
            }
        )
        seen.add(part_name)
    return parts


def _section_page_numbering(
    section: dict[str, Any],
    *,
    boundary: dict[str, Any],
    effective_refs: list[dict[str, Any]],
    page_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    declared = _declared_page_numbering(section)
    has_page_field = any(_is_page_field(field) for field in page_fields)
    checked_scopes = _checked_scopes(boundary, effective_refs)
    if has_page_field:
        display_status = "detected"
        confidence = "high"
    elif declared.get("status") == "detected":
        display_status = "declared_only"
        confidence = "medium"
    elif boundary.get("status") == "detected" or effective_refs:
        display_status = "no_page_field"
        confidence = "high"
    else:
        display_status = "missing_evidence"
        confidence = "low"
    return {
        "declared": declared,
        "fields": page_fields,
        "display": {
            "status": display_status,
            "has_page_field": has_page_field,
            "inferred_format": declared.get("format") or ("decimal" if has_page_field else None),
            "confidence": confidence,
            "checked_scopes": checked_scopes,
            "evidence_refs": _dedupe_str(
                [
                    *(field.get("source_ref") for field in page_fields),
                    *checked_scopes.get("evidence_refs", []),
                ]
            ),
        },
        "flags": [],
    }


def _declared_page_numbering(section: dict[str, Any]) -> dict[str, Any]:
    page_numbering = section.get("page_numbering") or {}
    if not page_numbering:
        return {"status": "not_declared"}
    source_ref = section.get("source_ref")
    return {
        "status": "detected",
        "format": page_numbering.get("format"),
        "start": page_numbering.get("start"),
        "source_ref": f"{source_ref}/pgNumType" if source_ref else None,
    }


def _page_fields_for_section(
    document_facts: dict[str, Any],
    boundary: dict[str, Any],
    effective_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fields = document_facts.get("data", {}).get("fields", [])
    effective_part_names = {
        str(ref.get("part_name") or "")
        for ref in effective_refs
        if ref.get("part_name")
    }
    page_fields = []
    seen: set[str] = set()
    for field in fields:
        if not _is_page_numbering_field(field):
            continue
        part_name = str(field.get("part_name") or "")
        in_effective_part = part_name in effective_part_names
        in_body_boundary = (
            part_name == "word/document.xml"
            and _field_overlaps_boundary(field, boundary)
        )
        if not (in_effective_part or in_body_boundary):
            continue
        source_ref = str(field.get("source_ref") or "")
        if source_ref in seen:
            continue
        page_fields.append(_page_field_spec(field))
        seen.add(source_ref)
    return page_fields


def _field_overlaps_boundary(field: dict[str, Any], boundary: dict[str, Any]) -> bool:
    start_paragraph = _int_or_none(boundary.get("start_paragraph_index"))
    end_paragraph = _int_or_none(boundary.get("end_paragraph_index"))
    field_start = _int_or_none(field.get("paragraph_index"))
    if start_paragraph is None or end_paragraph is None or field_start is None:
        return False
    field_end = _int_or_none(field.get("end_paragraph_index")) or field_start
    return start_paragraph <= field_end and field_start <= end_paragraph


def _is_page_numbering_field(field: dict[str, Any]) -> bool:
    field_type = str(field.get("field_type") or "").upper()
    instruction = str(field.get("instruction") or field.get("field_code") or "").upper()
    return field_type in {"PAGE", "NUMPAGES"} or instruction.startswith("PAGE")


def _is_page_field(field: dict[str, Any]) -> bool:
    field_type = str(field.get("field_type") or "").upper()
    instruction = str(field.get("instruction") or field.get("field_code") or "").upper()
    return field_type == "PAGE" or instruction.startswith("PAGE")


def _page_field_spec(field: dict[str, Any]) -> dict[str, Any]:
    return {
        "field_type": field.get("field_type"),
        "kind": field.get("kind"),
        "instruction": field.get("instruction") or field.get("field_code"),
        "part_name": field.get("part_name"),
        "paragraph_index": field.get("paragraph_index"),
        "end_paragraph_index": field.get("end_paragraph_index"),
        "source_ref": field.get("source_ref"),
    }


def _checked_scopes(
    boundary: dict[str, Any],
    effective_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    header_footer_parts = sorted(
        {
            str(ref.get("part_name"))
            for ref in effective_refs
            if ref.get("part_name")
        }
    )
    evidence_refs = _dedupe_str(
        [
            *boundary.get("evidence_refs", []),
            *(ref.get("source_ref") for ref in effective_refs),
        ]
    )
    return {
        "body_source_seq_range": {
            "start": boundary.get("start_source_seq"),
            "end": boundary.get("end_source_seq"),
        },
        "header_footer_parts": header_footer_parts,
        "evidence_refs": evidence_refs,
    }


def _page_numbering_from_profiles(section_profiles: list[dict[str, Any]]) -> dict[str, Any]:
    display_statuses = [
        str(profile.get("page_numbering", {}).get("display", {}).get("status") or "missing_evidence")
        for profile in section_profiles
    ]
    fields_by_section = {
        str(profile.get("section_profile_id")): [
            field.get("source_ref")
            for field in profile.get("page_numbering", {}).get("fields", [])
        ]
        for profile in section_profiles
    }
    formats = _dedupe_str(
        [
            profile.get("page_numbering", {}).get("declared", {}).get("format")
            for profile in section_profiles
            if profile.get("page_numbering", {}).get("declared", {}).get("format")
        ]
    )
    if not section_profiles or "missing_evidence" in display_statuses:
        status = "UNKNOWN"
    elif all(status == "no_page_field" for status in display_statuses):
        status = "none"
    elif len(formats) > 1 or len(set(display_statuses)) > 1:
        status = "mixed"
    else:
        status = "single"
    sections_with_page_field = sum(
        1
        for profile in section_profiles
        if profile.get("page_numbering", {}).get("display", {}).get("has_page_field")
    )
    return {
        "status": status,
        "summary": {
            "section_count": len(section_profiles),
            "sections_with_page_field": sections_with_page_field,
            "sections_without_page_field": len(section_profiles) - sections_with_page_field,
            "display_statuses": sorted(set(display_statuses)),
            "formats": formats,
        },
        "field_refs_by_section": fields_by_section,
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


def _unit_confidence(unit: dict[str, Any]) -> str:
    confidence = str(unit.get("confidence") or "").lower()
    if confidence in {"high", "medium", "low"}:
        return confidence
    if unit.get("source_refs"):
        return "medium"
    return "low"


def _unit_flags(unit: dict[str, Any], *, confidence: str) -> list[dict[str, Any]]:
    flags = list(unit.get("flags", []))
    confidence_flag = _confidence_flag(
        flag_id=f"{unit.get('unit_id')}.confidence_needs_review",
        type_="unit_confidence_needs_review",
        confidence=confidence,
        reason_subject=f"unit {unit.get('unit_id')}",
        source_ref=(unit.get("source_refs") or [None])[0],
        affected_id=str(unit.get("unit_id") or ""),
    )
    if confidence_flag is not None:
        flags.append(confidence_flag)
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
    if policy == "manual_only":
        return "high" if any(marker in text for marker in MANUAL_ONLY_MARKERS) else "medium"
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
            "kind": "flag",
            "source_ref": flag.get("source_ref"),
            "reason": flag.get("reason"),
            "status": flag.get("status", "UNKNOWN"),
        }
        for index, flag in enumerate(flags, start=1)
    ]


def _unit_map_open_questions(
    structure_candidates: dict[str, Any],
    flags: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    questions = [
        dict(question)
        for question in structure_candidates.get("open_questions", [])
    ]
    offset = len(questions)
    for index, question in enumerate(_open_questions_from_flags(flags), start=1):
        questions.append(
            {
                **question,
                "question_id": question.get("question_id") or f"q_{offset + index:03d}",
            }
        )
    return questions


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


def _global_flags(
    document_facts: dict[str, Any],
    section_profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    flags = []
    if not document_facts.get("data", {}).get("sections"):
        flags.append(
            {
                "type": "sections_missing",
                "status": "UNKNOWN",
                "reason": "document sections could not be parsed",
            }
        )
    if _page_numbering_from_profiles(section_profiles).get("status") == "UNKNOWN":
        flags.append(
            {
                "flag_id": "global.page_numbering_missing_evidence",
                "type": "page_numbering_missing_evidence",
                "status": "UNKNOWN",
                "source_ref": None,
                "affected_ids": ["global.page_numbering"],
                "reason": "one or more sections lack enough evidence for page numbering facts",
            }
        )
    return flags


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
