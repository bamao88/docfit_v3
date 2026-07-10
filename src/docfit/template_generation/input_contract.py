from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso, sha256_json

from .agent.observation_schema import validate_observation


def build_l1_input_contract(
    *,
    document_facts: dict[str, Any],
    render_packet: dict[str, Any] | None = None,
    ai_observation_bundle: dict[str, Any] | None = None,
    observation_bridge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_text_index = _source_text_index(document_facts, render_packet)
    source_object_index = _source_object_index(document_facts, source_text_index)
    layout_fact_index = _layout_fact_index(document_facts)
    visual_page_index = _visual_page_index(render_packet)
    bundle_gate_view = _bundle_gate_view(
        ai_observation_bundle,
        render_packet=render_packet,
        observation_bridge=observation_bridge,
        all_source_seq={
            int(item["source_seq"])
            for item in source_text_index
            if _as_int(item.get("source_seq")) is not None
        },
    )
    coverage = _coverage(
        source_text_index=source_text_index,
        source_object_index=source_object_index,
        layout_fact_index=layout_fact_index,
        visual_page_index=visual_page_index,
        bundle_gate_view=bundle_gate_view,
    )
    return {
        "artifact_type": "template_generation_l1_input_contract",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "input_hashes": {
            "document_facts": sha256_json(document_facts),
            "template_agent_render_packet": (
                sha256_json(render_packet) if render_packet is not None else None
            ),
            "ai_observation_bundle": (
                sha256_json(ai_observation_bundle)
                if ai_observation_bundle is not None
                else None
            ),
        },
        "source_text_index": source_text_index,
        "source_object_index": source_object_index,
        "layout_fact_index": layout_fact_index,
        "visual_page_index": visual_page_index,
        "bundle_gate_view": bundle_gate_view,
        "coverage": coverage,
    }


def _source_text_index(
    document_facts: dict[str, Any],
    render_packet: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    packet_by_seq = {
        int(item["source_seq"]): item
        for item in (render_packet or {}).get("page_text_index", []) or []
        if _as_int(item.get("source_seq")) is not None
    }
    rows: list[dict[str, Any]] = []
    for order, entry in enumerate(document_facts.get("body_flow", []) or [], start=1):
        source_seq = _as_int(entry.get("source_seq"))
        if source_seq is None:
            continue
        packet_row = packet_by_seq.get(source_seq, {})
        rows.append(
            {
                "source_seq": source_seq,
                "source_ref": entry.get("source_ref"),
                "node_id": entry.get("node_id"),
                "part_name": entry.get("part_name"),
                "kind": entry.get("kind"),
                "flow_item_type": entry.get("flow_item_type"),
                "structure_layer": entry.get("structure_layer"),
                "order": entry.get("order", order),
                "text": entry.get("text", ""),
                "style": entry.get("style"),
                "style_details": entry.get("style_details", {}),
                "text_facts": entry.get("text_facts", {}),
                "raw_run_ids": entry.get("raw_run_ids", []),
                "logical_run_ids": entry.get("logical_run_ids", []),
                "page_no": packet_row.get("page_no") or entry.get("page_no"),
                "bbox": packet_row.get("bbox") or entry.get("bbox"),
                "render_target_id": packet_row.get("render_target_id"),
                "binding_status": packet_row.get(
                    "render_binding_status",
                    "no_render_packet" if render_packet is None else "unbound",
                ),
            }
        )
    return rows


def _source_object_index(
    document_facts: dict[str, Any],
    source_text_index: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    text_binding = _source_text_binding(source_text_index)
    data = document_facts.get("data", {}) or {}
    objects: list[dict[str, Any]] = []
    for image in data.get("images", []) or []:
        if not isinstance(image, dict):
            continue
        objects.append(
            _object_row(
                image,
                object_type="image",
                object_id=f"image:{image.get('index')}",
                text_binding=text_binding,
                extra={
                    "relationship_id": image.get("relationship_id"),
                    "target": image.get("target"),
                    "sha256": image.get("sha256"),
                    "byte_count": image.get("byte_count"),
                },
            )
        )
    for text_box in data.get("text_boxes", []) or []:
        if not isinstance(text_box, dict):
            continue
        objects.append(
            _object_row(
                text_box,
                object_type="text_box",
                object_id=f"text_box:{text_box.get('index')}",
                text_binding=text_binding,
                extra={"text": text_box.get("text", "")},
            )
        )
    for control in data.get("content_controls", []) or []:
        if not isinstance(control, dict):
            continue
        objects.append(
            _object_row(
                control,
                object_type="content_control",
                object_id=f"content_control:{control.get('index')}",
                text_binding=text_binding,
                extra={
                    "tag": control.get("tag"),
                    "alias": control.get("alias"),
                    "text": control.get("text", ""),
                },
            )
        )
    for footnote in data.get("footnotes", []) or []:
        if not isinstance(footnote, dict):
            continue
        objects.append(
            _object_row(
                footnote,
                object_type="footnote",
                object_id=f"footnote:{footnote.get('index')}",
                text_binding=text_binding,
                extra={
                    "footnote_id": footnote.get("footnote_id"),
                    "text": footnote.get("text", ""),
                },
            )
        )
    unknowns = [
        *(data.get("unknown_visible_objects", []) or []),
        *(document_facts.get("unknown_objects", []) or []),
    ]
    for index, unknown in enumerate(unknowns, start=1):
        if not isinstance(unknown, dict):
            continue
        objects.append(
            _object_row(
                unknown,
                object_type=str(unknown.get("object_type") or "unknown_visible_object"),
                object_id=str(unknown.get("object_id") or f"unknown:{index}"),
                text_binding=text_binding,
                extra={
                    "reason": unknown.get("reason"),
                    "text": unknown.get("text", ""),
                },
            )
        )
    return objects


def _object_row(
    source: dict[str, Any],
    *,
    object_type: str,
    object_id: str,
    text_binding: dict[str, dict[str, Any]],
    extra: dict[str, Any],
) -> dict[str, Any]:
    source_ref = str(source.get("source_ref") or "")
    anchor = _binding_for_source_ref(source_ref, text_binding)
    binding_status = (
        f"via_text_anchor:{anchor.get('binding_status')}"
        if anchor is not None
        else "unbound_no_source_seq_anchor"
    )
    row = {
        "object_id": object_id,
        "object_type": object_type,
        "source_ref": source_ref or None,
        "source_seq_anchor": anchor.get("source_seq") if anchor is not None else None,
        "binding_status": binding_status,
        "page_no": anchor.get("page_no") if anchor is not None else None,
        "bbox": anchor.get("bbox") if anchor is not None else None,
        "render_target_id": anchor.get("render_target_id") if anchor is not None else None,
    }
    row.update({key: value for key, value in extra.items() if value not in (None, "")})
    return row


def _source_text_binding(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        ref = str(row.get("source_ref") or "")
        if ref:
            result[ref] = row
    return result


def _binding_for_source_ref(
    source_ref: str,
    text_binding: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if not source_ref:
        return None
    if source_ref in text_binding:
        return text_binding[source_ref]
    for ref, row in text_binding.items():
        if source_ref.startswith(ref) or ref.startswith(source_ref):
            return row
    return None


def _layout_fact_index(document_facts: dict[str, Any]) -> dict[str, Any]:
    data = document_facts.get("data", {}) or {}
    return {
        "sections": list(data.get("sections", []) or []),
        "headers_footers": list(data.get("headers_footers", []) or []),
        "fields": list(data.get("fields", []) or []),
        "breaks": list(data.get("breaks", []) or []),
        "numbering_refs": list(data.get("numbering_refs", []) or []),
        "numbering_definitions": list(data.get("numbering_definitions", []) or []),
    }


def _visual_page_index(render_packet: dict[str, Any] | None) -> dict[str, Any]:
    if render_packet is None:
        return {
            "render_status": "not_available",
            "source_render_hash": None,
            "clean_page_images": [],
            "annotated_page_images": [],
            "page_layout_index": [],
            "binding_summary": {"no_render_packet": 0},
        }
    render_artifacts = render_packet.get("render_artifacts", {}) or {}
    binding_summary: dict[str, int] = {}
    for item in render_packet.get("page_text_index", []) or []:
        status = str(item.get("render_binding_status") or "unknown")
        binding_summary[status] = binding_summary.get(status, 0) + 1
    return {
        "render_status": render_packet.get("render_status"),
        "source_render_hash": render_packet.get("source_render_hash"),
        "render_engine": render_artifacts.get("render_engine"),
        "render_version": render_artifacts.get("render_version"),
        "pdf_path": render_artifacts.get("pdf_path"),
        "pdf_sha256": render_artifacts.get("pdf_sha256"),
        "page_count": render_artifacts.get("page_count"),
        "render_error": render_artifacts.get("render_error"),
        "clean_page_images": list(render_artifacts.get("clean_page_images", []) or []),
        "annotated_page_images": list(
            render_artifacts.get("annotated_page_images", []) or []
        ),
        "page_layout_index": list(render_packet.get("page_layout_index", []) or []),
        "binding_summary": binding_summary,
    }


def _bundle_gate_view(
    ai_observation_bundle: dict[str, Any] | None,
    *,
    render_packet: dict[str, Any] | None,
    observation_bridge: dict[str, Any] | None,
    all_source_seq: set[int],
) -> dict[str, Any]:
    expected_hash = (render_packet or {}).get("source_render_hash")
    if ai_observation_bundle is None:
        return {
            "bundle_present": False,
            "expected_source_render_hash": expected_hash,
            "bundle_source_render_hash": None,
            "source_render_hash_match": None,
            "stage_gates": {},
            "bridge_present": observation_bridge is not None,
            "bridge_summary": (observation_bridge or {}).get("summary", {}),
        }
    bundle_hash = ai_observation_bundle.get("source_render_hash")
    stage_gates: dict[str, Any] = {}
    for key in (
        "ai_unit_observation",
        "ai_element_observation",
        "ai_layout_observation",
    ):
        observation = ai_observation_bundle.get(key)
        validation = validate_observation(
            observation,
            expected_source_render_hash=expected_hash,
            all_source_seq=all_source_seq,
        )
        stage_gates[key] = {
            "present": isinstance(observation, dict),
            "valid": bool(validation.get("valid")),
            "errors": validation.get("errors", []),
            "coverage": (validation.get("observation") or {}).get("coverage", {}),
        }
    return {
        "bundle_present": True,
        "expected_source_render_hash": expected_hash,
        "bundle_source_render_hash": bundle_hash,
        "source_render_hash_match": (
            expected_hash is not None and bundle_hash == expected_hash
        ),
        "stage_gates": stage_gates,
        "bridge_present": observation_bridge is not None,
        "bridge_summary": (observation_bridge or {}).get("summary", {}),
    }


def _coverage(
    *,
    source_text_index: list[dict[str, Any]],
    source_object_index: list[dict[str, Any]],
    layout_fact_index: dict[str, Any],
    visual_page_index: dict[str, Any],
    bundle_gate_view: dict[str, Any],
) -> dict[str, Any]:
    object_unbound = [
        item.get("object_id")
        for item in source_object_index
        if str(item.get("binding_status") or "").startswith("unbound")
    ]
    source_unbound = [
        item.get("source_seq")
        for item in source_text_index
        if item.get("binding_status") in {"unbound", "no_render_packet"}
    ]
    stage_gates = bundle_gate_view.get("stage_gates", {}) or {}
    invalid_gates = [
        stage for stage, gate in stage_gates.items() if not gate.get("valid")
    ]
    return {
        "source_text_count": len(source_text_index),
        "source_text_unbound_count": len(source_unbound),
        "source_text_unbound_refs": source_unbound[:50],
        "source_object_count": len(source_object_index),
        "source_object_unbound_count": len(object_unbound),
        "source_object_unbound_ids": object_unbound[:50],
        "section_count": len(layout_fact_index.get("sections", []) or []),
        "header_footer_count": len(layout_fact_index.get("headers_footers", []) or []),
        "field_count": len(layout_fact_index.get("fields", []) or []),
        "break_count": len(layout_fact_index.get("breaks", []) or []),
        "render_status": visual_page_index.get("render_status"),
        "page_count": visual_page_index.get("page_count"),
        "bundle_present": bundle_gate_view.get("bundle_present"),
        "bundle_gate_invalid_stages": invalid_gates,
    }


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None
