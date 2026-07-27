from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import json
from typing import Any

from docfit.core.io import now_iso, sha256_json

def l1_artifact_hash(l1_input_contract: dict[str, Any]) -> str:
    persisted_view = json.loads(
        json.dumps(l1_input_contract, ensure_ascii=False, sort_keys=True)
    )
    return sha256_json(persisted_view)


def build_t2_stage_input(l1_input_contract: dict[str, Any]) -> dict[str, Any]:
    facts = _document_facts_view(l1_input_contract)
    data = facts["data"]
    return {
        "artifact_type": "t2_l1_stage_input",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "l1_hash": l1_artifact_hash(l1_input_contract),
        "source_tree": {
            "artifact_type": "source_template_tree",
            "artifact_version": "l1-view-1.0",
            "producer": {
                "name": "docfit-template-generate",
                "version": "0.3.0",
                "view_of": "template_generation_l1_input_contract",
            },
            "created_at": l1_input_contract.get("created_at") or now_iso(),
            "metadata": facts["metadata"],
            "layers": {
                "package_global": {
                    "numbering_definitions": data.get("numbering_definitions", []),
                },
                "section_rules": data.get("sections", []),
                "header_footer": data.get("headers_footers", []),
                "body_flow": deepcopy(facts["body_flow"]),
                "embedded_resources": data.get("images", []),
                "unknown_objects": facts["unknown_objects"],
            },
            "indexes": deepcopy(facts["indexes"]),
            "warnings": deepcopy(facts["warnings"]),
            "data": deepcopy(data),
            "input_hashes": {"l1": l1_artifact_hash(l1_input_contract)},
        },
        "facts": deepcopy(facts),
    }


def build_t4_stage_input(l1_input_contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": "t4_l1_stage_input",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "l1_hash": l1_artifact_hash(l1_input_contract),
        "facts": _document_facts_view(l1_input_contract),
    }


def build_agent_stage_packet(l1_input_contract: dict[str, Any]) -> dict[str, Any]:
    visual = l1_input_contract.get("visual_page_index", {}) or {}
    raw_runs_by_id = {
        str(item.get("raw_run_id") or ""): item
        for item in (l1_input_contract.get("run_index", {}) or {}).get(
            "raw_runs", []
        )
        if isinstance(item, dict) and item.get("raw_run_id")
    }
    page_text_index = [
        {
            "source_seq": item.get("source_seq"),
            "source_ref": item.get("source_ref"),
            "node_id": item.get("node_id"),
            "part_name": item.get("part_name"),
            "order": item.get("order"),
            "kind": item.get("kind"),
            "paragraph_id": (item.get("source_facts", {}) or {}).get(
                "paragraph_id"
            )
            or _first_raw_run_fact(item, raw_runs_by_id).get("paragraph_id"),
            "table_id": (item.get("source_facts", {}) or {}).get("table_id"),
            "cell_id": (item.get("source_facts", {}) or {}).get("cell_id"),
            "flow_item_type": item.get("flow_item_type"),
            "structure_layer": item.get("structure_layer"),
            "text": item.get("text", ""),
            "text_facts": deepcopy(item.get("text_facts", {})),
            "style_details": _agent_style_details(
                item,
                raw_runs_by_id=raw_runs_by_id,
            ),
            "raw_run_ids": deepcopy(item.get("raw_run_ids", [])),
            "logical_run_ids": deepcopy(item.get("logical_run_ids", [])),
            "page_no": item.get("page_no"),
            "bbox": deepcopy(item.get("bbox")),
            "render_binding_status": item.get("binding_status"),
            "render_target_id": item.get("render_target_id"),
        }
        for item in l1_input_contract.get("source_text_index", []) or []
    ]
    render_artifacts = {
        "render_status": visual.get("render_status"),
        "clean_page_images": deepcopy(list(visual.get("clean_page_images", []) or [])),
        "annotated_page_images": deepcopy(list(
            visual.get("annotated_page_images", []) or []
        )),
        "render_engine": visual.get("render_engine"),
        "render_version": visual.get("render_version"),
        "pdf_path": visual.get("pdf_path"),
        "pdf_sha256": visual.get("pdf_sha256"),
        "page_count": visual.get("page_count"),
        "render_error": visual.get("render_error"),
        "render_hash": visual.get("source_render_hash"),
    }
    object_fact_index = _agent_object_fact_index(l1_input_contract)
    return {
        "artifact_type": "template_agent_l1_stage_packet",
        "artifact_version": "3.0",
        "created_at": now_iso(),
        "input_contract_hash": l1_artifact_hash(l1_input_contract),
        "render_status": visual.get("render_status"),
        "source_render_hash": visual.get("source_render_hash"),
        "status_authority": "verify_template_parse_build",
        "ai_semantic_authority_stages": ["T2", "T3", "T4"],
        "allowed_ai_tasks": [
            "return_t2_page_groups",
            "submit_t3_hierarchical_decisions",
            "return_t4_global_layout_decisions",
            "abstain",
        ],
        "forbidden_ai_tasks": [
            "write_document_facts",
            "write_unit_map",
            "write_element_spec",
            "write_global_spec",
            "write_template_spec",
            "write_generation_plan",
            "write_build_manifest",
            "set_verification_status",
            "read_standards_targets",
        ],
        "render_artifacts": render_artifacts,
        "page_text_index": page_text_index,
        "object_fact_index": object_fact_index,
        "page_layout_index": deepcopy(list(visual.get("page_layout_index", []) or [])),
        "input_windows": {
            "full_pass": {
                "page_thumbnails": render_artifacts.get("clean_page_images", []),
                "page_index_summary": _page_index_summary(page_text_index),
            },
            "focused_pass": [],
        },
        "global_layout_facts": _global_layout_facts(l1_input_contract),
        "round0_snapshot_id": sha256_json(
            {"l1_hash": l1_artifact_hash(l1_input_contract)}
        ),
    }


def _agent_object_fact_index(
    l1_input_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    """Project claimable L1 object identities without T2/T3 policy semantics."""

    rows: list[dict[str, Any]] = []
    for item in l1_input_contract.get("source_object_index", []) or []:
        if not isinstance(item, dict) or not item.get("source_ref"):
            continue
        rows.append(
            {
                key: deepcopy(item.get(key))
                for key in (
                    "object_id",
                    "object_type",
                    "source_ref",
                    "source_seq_anchor",
                    "binding_status",
                    "page_no",
                    "bbox",
                    "render_target_id",
                    "relationship_id",
                    "target",
                    "sha256",
                    "byte_count",
                    "text",
                    "tag",
                    "alias",
                    "footnote_id",
                    "reason",
                )
                if item.get(key) is not None
            }
        )

    existing_refs = {str(item.get("source_ref") or "") for item in rows}
    layout = l1_input_contract.get("layout_fact_index", {}) or {}
    for field in layout.get("fields", []) or []:
        if not isinstance(field, dict):
            continue
        source_ref = str(field.get("source_ref") or "")
        if not source_ref or source_ref in existing_refs:
            continue
        rows.append(
            {
                key: deepcopy(value)
                for key, value in {
                    "object_id": f"field:{source_ref}",
                    "object_type": "field",
                    "source_ref": source_ref,
                    "part_name": field.get("part_name"),
                    "kind": field.get("kind"),
                    "field_type": field.get("field_type"),
                    "instruction": field.get("instruction"),
                    "paragraph_index": field.get("paragraph_index"),
                    "end_paragraph_index": field.get("end_paragraph_index"),
                    "end_source_ref": field.get("end_source_ref"),
                }.items()
                if value is not None
            }
        )
        existing_refs.add(source_ref)
    return rows


def _agent_style_details(
    source_item: dict[str, Any],
    *,
    raw_runs_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Project authoritative L1 run facts without downstream policy semantics."""

    details = deepcopy(source_item.get("style_details", {}) or {})
    source_runs = [
        item for item in details.get("runs", []) or [] if isinstance(item, dict)
    ]
    projected_runs: list[dict[str, Any]] = []
    for index, raw_run_id_value in enumerate(source_item.get("raw_run_ids", []) or []):
        raw_run_id = str(raw_run_id_value or "")
        indexed = raw_runs_by_id.get(raw_run_id, {})
        fallback = source_runs[index] if index < len(source_runs) else {}
        effective_style = deepcopy(indexed.get("effective_style", {}) or {})
        if not effective_style:
            effective_style = {
                key: fallback.get(key)
                for key in (
                    "font_names",
                    "font_size_pt",
                    "bold",
                    "italic",
                    "underline",
                    "color",
                )
                if fallback.get(key) is not None
            }
        projected_runs.append(
            {
                "raw_run_id": raw_run_id,
                "logical_run_id": indexed.get("logical_run_id"),
                "text": indexed.get("text", fallback.get("text", "")),
                "source_ref": indexed.get("source_ref")
                or fallback.get("source_ref"),
                "effective_style": effective_style,
            }
        )
    details["runs"] = projected_runs
    return details


def _first_raw_run_fact(
    source_item: dict[str, Any],
    raw_runs_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    raw_run_ids = list(source_item.get("raw_run_ids", []) or [])
    if not raw_run_ids:
        return {}
    return raw_runs_by_id.get(str(raw_run_ids[0]), {})


def _document_facts_view(l1_input_contract: dict[str, Any]) -> dict[str, Any]:
    structure = deepcopy(l1_input_contract.get("source_structure_index", {}) or {})
    layout = deepcopy(l1_input_contract.get("layout_fact_index", {}) or {})
    body_flow = [
        deepcopy(item.get("source_facts", {}) or {})
        for item in l1_input_contract.get("source_text_index", []) or []
    ]
    object_collections: dict[str, list[dict[str, Any]]] = defaultdict(list)
    type_to_collection = {
        "image": "images",
        "text_box": "text_boxes",
        "content_control": "content_controls",
        "footnote": "footnotes",
    }
    for item in l1_input_contract.get("source_object_index", []) or []:
        collection = type_to_collection.get(str(item.get("object_type") or ""))
        if collection:
            object_collections[collection].append(
                deepcopy(item.get("source_facts", {}) or {})
            )

    logical_runs = deepcopy(list(
        (l1_input_contract.get("run_index", {}) or {}).get("logical_runs", []) or []
    ))
    logical_by_id = {
        str(item.get("logical_run_id")): item
        for item in logical_runs
        if item.get("logical_run_id")
    }
    raw_lookup: dict[str, dict[str, Any]] = {}
    source_lookup: dict[str, dict[str, Any]] = {}
    for raw in deepcopy((l1_input_contract.get("run_index", {}) or {}).get("raw_runs", []) or []):
        logical = logical_by_id.get(str(raw.get("logical_run_id") or ""), {})
        compatibility = {
            **raw,
            "text": logical.get("text", raw.get("text", "")),
            "merged_from": logical.get("raw_run_ids", [raw.get("raw_run_id")]),
            "source_refs": logical.get("source_refs", [raw.get("source_ref")]),
        }
        raw_run_id = str(raw.get("raw_run_id") or "")
        source_ref = str(raw.get("source_ref") or "")
        if raw_run_id:
            raw_lookup[raw_run_id] = compatibility
        if source_ref:
            source_lookup[source_ref] = compatibility

    data = {
        "paragraphs": list(structure.get("paragraphs", []) or []),
        "tables": list(structure.get("tables", []) or []),
        "sections": list(layout.get("sections", []) or []),
        "headers_footers": list(layout.get("headers_footers", []) or []),
        "fields": list(layout.get("fields", []) or []),
        "breaks": list(layout.get("breaks", []) or []),
        "numbering_refs": list(layout.get("numbering_refs", []) or []),
        "numbering_definitions": list(
            layout.get("numbering_definitions", []) or []
        ),
        "images": object_collections["images"],
        "text_boxes": object_collections["text_boxes"],
        "content_controls": object_collections["content_controls"],
        "footnotes": object_collections["footnotes"],
        "unknown_visible_objects": [
            deepcopy(item.get("source_facts", {}) or {})
            for item in l1_input_contract.get("source_object_index", []) or []
            if str(item.get("object_type") or "")
            not in type_to_collection
        ],
    }
    return {
        "artifact_type": "l1_document_facts_stage_view",
        "artifact_version": "1.0",
        "created_at": l1_input_contract.get("created_at"),
        "metadata": dict(structure.get("metadata", {}) or {}),
        "body_flow": body_flow,
        "runs": logical_runs,
        "unknown_objects": list(structure.get("unknown_objects", []) or []),
        "warnings": list(structure.get("warnings", []) or []),
        "indexes": {
            "body_order": list(structure.get("body_order", []) or []),
            "by_source_ref": dict(structure.get("by_source_ref", {}) or {}),
            "by_source_seq": dict(structure.get("by_source_seq", {}) or {}),
            "runs_by_raw_run_id": raw_lookup,
            "runs_by_source_ref": source_lookup,
        },
        "data": data,
        "input_hashes": {"l1": l1_artifact_hash(l1_input_contract)},
    }


def _page_index_summary(page_text_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[int, int] = defaultdict(int)
    for item in page_text_index:
        counts[int(item.get("page_no") or 1)] += 1
    return [
        {"page_no": page_no, "text_items": counts[page_no]}
        for page_no in sorted(counts)
    ]


def _global_layout_facts(l1_input_contract: dict[str, Any]) -> dict[str, Any]:
    layout = l1_input_contract.get("layout_fact_index", {}) or {}
    return {
        "sections": list(layout.get("sections", []) or []),
        "header_footer": list(layout.get("headers_footers", []) or []),
        "fields": list(layout.get("fields", []) or []),
        "breaks": list(layout.get("breaks", []) or []),
        "numbering_definition_count": len(
            layout.get("numbering_definitions", []) or []
        ),
    }
