from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso, sha256_json


def build_l1_input_contract(
    *,
    document_facts: dict[str, Any],
    render_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_text_index = _source_text_index(document_facts, render_packet)
    run_index = _run_index(document_facts, source_text_index)
    source_object_index = _source_object_index(document_facts, source_text_index)
    source_structure_index = _source_structure_index(document_facts)
    layout_fact_index = _layout_fact_index(document_facts)
    visual_page_index = _visual_page_index(render_packet)
    coverage = _coverage(
        source_text_index=source_text_index,
        run_index=run_index,
        source_object_index=source_object_index,
        layout_fact_index=layout_fact_index,
        visual_page_index=visual_page_index,
    )
    return {
        "artifact_type": "template_generation_l1_input_contract",
        "artifact_version": "2.0",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "input_hashes": {
            "source_template": document_facts.get("metadata", {}).get(
                "source_template_hash"
            ),
            "document_facts": sha256_json(document_facts),
            "render_facts": (
                sha256_json(render_packet) if render_packet is not None else None
            ),
        },
        "source_text_index": source_text_index,
        "run_index": run_index,
        "source_object_index": source_object_index,
        "source_structure_index": source_structure_index,
        "layout_fact_index": layout_fact_index,
        "visual_page_index": visual_page_index,
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
                "source_facts": dict(entry),
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


def _source_structure_index(document_facts: dict[str, Any]) -> dict[str, Any]:
    data = document_facts.get("data", {}) or {}
    indexes = document_facts.get("indexes", {}) or {}
    return {
        "metadata": dict(document_facts.get("metadata", {}) or {}),
        "paragraphs": list(data.get("paragraphs", []) or []),
        "tables": list(data.get("tables", []) or []),
        "body_order": list(indexes.get("body_order", []) or []),
        "by_source_ref": dict(indexes.get("by_source_ref", {}) or {}),
        "by_source_seq": dict(indexes.get("by_source_seq", {}) or {}),
        "warnings": list(document_facts.get("warnings", []) or []),
        "unknown_objects": list(document_facts.get("unknown_objects", []) or []),
    }


def _run_index(
    document_facts: dict[str, Any],
    source_text_index: list[dict[str, Any]],
) -> dict[str, Any]:
    source_by_raw_run: dict[str, dict[str, Any]] = {}
    raw_runs_by_id: dict[str, dict[str, Any]] = {}
    indexed_runs = (
        document_facts.get("indexes", {}).get("runs_by_raw_run_id", {}) or {}
    )
    for source in document_facts.get("body_flow", []) or []:
        if not isinstance(source, dict):
            continue
        raw_run_ids = list(source.get("raw_run_ids", []) or [])
        style_runs = list((source.get("style_details", {}) or {}).get("runs", []) or [])
        for index, raw_run_id_value in enumerate(raw_run_ids):
            raw_run_id = str(raw_run_id_value or "")
            if not raw_run_id:
                continue
            indexed = indexed_runs.get(raw_run_id, {}) or {}
            style_run = style_runs[index] if index < len(style_runs) else {}
            if not isinstance(style_run, dict):
                style_run = {}
            existing = raw_runs_by_id.get(raw_run_id)
            if existing is not None:
                source_seq = source.get("source_seq")
                source_ref = source.get("source_ref")
                if source_seq not in existing["parent_source_seq_refs"]:
                    existing["parent_source_seq_refs"].append(source_seq)
                if source_ref not in existing["parent_source_refs"]:
                    existing["parent_source_refs"].append(source_ref)
                continue
            row = {
                "raw_run_id": raw_run_id,
                "logical_run_id": indexed.get("logical_run_id"),
                "parent_source_seq": source.get("source_seq"),
                "parent_source_seq_refs": [source.get("source_seq")],
                "parent_source_ref": source.get("source_ref"),
                "parent_source_refs": [source.get("source_ref")],
                "paragraph_id": indexed.get("paragraph_id")
                or source.get("paragraph_id"),
                "source_ref": style_run.get("source_ref")
                or indexed.get("source_ref"),
                "text": style_run.get("text", ""),
                "effective_style": _effective_style(style_run, indexed),
                "style_provenance": indexed.get("style_provenance", {}),
                "container_refs": indexed.get("container_refs", []),
                "kind": indexed.get("kind", "text"),
            }
            raw_runs_by_id[raw_run_id] = row
            source_by_raw_run[raw_run_id] = row

    raw_runs = list(raw_runs_by_id.values())

    logical_runs: list[dict[str, Any]] = []
    for logical in document_facts.get("runs", []) or []:
        if not isinstance(logical, dict):
            continue
        merged_from = [str(value) for value in logical.get("merged_from", []) or []]
        parent = next(
            (source_by_raw_run[raw_id] for raw_id in merged_from if raw_id in source_by_raw_run),
            {},
        )
        logical_runs.append(
            {
                "logical_run_id": logical.get("logical_run_id"),
                "raw_run_id": logical.get("raw_run_id"),
                "raw_run_ids": merged_from,
                "parent_source_seq": parent.get("parent_source_seq"),
                "parent_source_seq_refs": parent.get("parent_source_seq_refs", []),
                "parent_source_ref": parent.get("parent_source_ref"),
                "parent_source_refs": parent.get("parent_source_refs", []),
                "paragraph_id": logical.get("paragraph_id"),
                "source_refs": logical.get("source_refs", []),
                "text": logical.get("text", ""),
                "effective_style": logical.get("effective_style", {}),
                "style_provenance": logical.get("style_provenance", {}),
                "container_refs": logical.get("container_refs", []),
                "kind": logical.get("kind", "text"),
            }
        )

    source_run_refs = {
        str(int(row["source_seq"])): {
            "raw_run_ids": list(row.get("raw_run_ids", []) or []),
            "logical_run_ids": list(row.get("logical_run_ids", []) or []),
        }
        for row in source_text_index
        if _as_int(row.get("source_seq")) is not None
    }
    return {
        "raw_runs": raw_runs,
        "logical_runs": logical_runs,
        "source_run_refs": source_run_refs,
    }


def _effective_style(
    style_run: dict[str, Any],
    indexed_run: dict[str, Any],
) -> dict[str, Any]:
    direct = {
        key: style_run.get(key)
        for key in (
            "font_names",
            "font_size_pt",
            "bold",
            "italic",
            "underline",
            "color",
        )
        if key in style_run
    }
    return direct or dict(indexed_run.get("effective_style", {}) or {})


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
        "source_facts": dict(source),
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


def _coverage(
    *,
    source_text_index: list[dict[str, Any]],
    run_index: dict[str, Any],
    source_object_index: list[dict[str, Any]],
    layout_fact_index: dict[str, Any],
    visual_page_index: dict[str, Any],
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
    raw_runs = list(run_index.get("raw_runs", []) or [])
    logical_runs = list(run_index.get("logical_runs", []) or [])
    raw_run_unbound = [
        item.get("raw_run_id")
        for item in raw_runs
        if _as_int(item.get("parent_source_seq")) is None
        or not item.get("source_ref")
    ]
    logical_run_unbound = [
        item.get("logical_run_id")
        for item in logical_runs
        if _as_int(item.get("parent_source_seq")) is None
        or not item.get("raw_run_ids")
    ]
    return {
        "source_text_count": len(source_text_index),
        "source_text_unbound_count": len(source_unbound),
        "source_text_unbound_refs": source_unbound[:50],
        "raw_run_count": len(raw_runs),
        "raw_run_unbound_count": len(raw_run_unbound),
        "raw_run_unbound_ids": raw_run_unbound[:50],
        "logical_run_count": len(logical_runs),
        "logical_run_unbound_count": len(logical_run_unbound),
        "logical_run_unbound_ids": logical_run_unbound[:50],
        "source_object_count": len(source_object_index),
        "source_object_unbound_count": len(object_unbound),
        "source_object_unbound_ids": object_unbound[:50],
        "section_count": len(layout_fact_index.get("sections", []) or []),
        "header_footer_count": len(layout_fact_index.get("headers_footers", []) or []),
        "field_count": len(layout_fact_index.get("fields", []) or []),
        "break_count": len(layout_fact_index.get("breaks", []) or []),
        "render_status": visual_page_index.get("render_status"),
        "render_error": visual_page_index.get("render_error"),
        "page_count": visual_page_index.get("page_count"),
    }


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None
