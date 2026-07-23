"""T3 hierarchical Stage Input derived only from sealed L1 facts and T2 windows.

The builder creates one validated tree per T2 unit.  Nodes contain factual Word
identity, direct-child relations, completeness and visual bindings; they never
contain T3 policy or action decisions.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import re
from typing import Any

from docfit.core.io import now_iso, sha256_json

from .t3_hierarchical_contract import (
    T3_STAGE_INPUT_VERSION,
    assert_t3_stage_input_clean,
    nodes_by_ref,
    t3_node_evidence,
    validate_t3_hierarchical_stage_input,
)
from .t3_atomic_spans import partition_atomic_run_spans

_CELL_ID_RE = re.compile(r"^(?P<table>.+)\.r_(?P<row>\d+)\.c_(?P<column>\d+)$")


def build_t3_hierarchical_stage_input(
    packet: dict[str, Any],
    *,
    unit_windows: dict[str, Any] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the complete node tree used by sparse T3 traversal.

    ``packet`` is the L1-derived agent packet. ``unit_windows`` is the matching
    T2 route projection.  The returned artifact is deterministic apart from its
    audit timestamp; ``tree_hash`` excludes that timestamp.
    """

    windows = (
        list(unit_windows.get("windows", []) or [])
        if isinstance(unit_windows, dict)
        else list(unit_windows)
    )
    packet_rows = [
        row for row in packet.get("page_text_index", []) or [] if isinstance(row, dict)
    ]
    rows_by_seq = {
        seq: row
        for row in packet_rows
        if (seq := _as_int(row.get("source_seq"))) is not None
    }
    objects_by_ref = {
        str(item.get("source_ref")): item
        for item in packet.get("object_fact_index", []) or []
        if isinstance(item, dict) and item.get("source_ref")
    }
    images_by_page = {
        page_no: image
        for image in (packet.get("render_artifacts") or {}).get(
            "clean_page_images", []
        )
        if isinstance(image, dict)
        and (page_no := _as_int(image.get("page_no"))) is not None
    }

    nodes: list[dict[str, Any]] = []
    unit_roots: list[dict[str, Any]] = []
    for window in windows:
        if not isinstance(window, dict):
            continue
        root_ref, unit_nodes = _build_unit_tree(
            packet=packet,
            packet_rows=packet_rows,
            rows_by_seq=rows_by_seq,
            objects_by_ref=objects_by_ref,
            images_by_page=images_by_page,
            window=window,
        )
        nodes.extend(unit_nodes)
        unit_roots.append(
            {
                "unit_id": str(window.get("unit_id") or ""),
                "root_ref": root_ref,
                "t2_window_id": window.get("window_id"),
            }
        )

    artifact = {
        "artifact_type": "t3_hierarchical_stage_input",
        "artifact_version": T3_STAGE_INPUT_VERSION,
        "created_at": now_iso(),
        "contract": {
            "l1_hash": packet.get("input_contract_hash"),
            "source_render_hash": packet.get("source_render_hash"),
            "t2_route_hash": (
                unit_windows.get("post_t2_observation_hash")
                if isinstance(unit_windows, dict)
                else sha256_json(windows)
            ),
            "stage_input_version": T3_STAGE_INPUT_VERSION,
        },
        "unit_roots": unit_roots,
        "nodes": nodes,
    }
    artifact["tree_hash"] = sha256_json(
        {
            "contract": artifact["contract"],
            "unit_roots": unit_roots,
            "nodes": nodes,
        }
    )
    assert_t3_stage_input_clean(artifact)
    return artifact


def _build_unit_tree(
    *,
    packet: dict[str, Any],
    packet_rows: list[dict[str, Any]],
    rows_by_seq: dict[int, dict[str, Any]],
    objects_by_ref: dict[str, dict[str, Any]],
    images_by_page: dict[int, dict[str, Any]],
    window: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    unit_id = str(window.get("unit_id") or "unknown_unit")
    root_ref = f"unit:{unit_id}"
    requested_seqs = _ints(window.get("source_seq_refs"))
    rows = [rows_by_seq[seq] for seq in requested_seqs if seq in rows_by_seq]
    requested_object_refs = list(
        dict.fromkeys(
            [
                *_strings(window.get("source_ref_refs")),
                *[
                    source_ref
                    for source_ref, fact in objects_by_ref.items()
                    if _as_int(fact.get("source_seq_anchor")) in set(requested_seqs)
                ],
            ]
        )
    )
    nodes: list[dict[str, Any]] = []
    direct_refs: list[str] = []

    seen_tables: set[str] = set()
    for row in rows:
        table_id = str(row.get("table_id") or "")
        if table_id:
            if table_id in seen_tables:
                continue
            seen_tables.add(table_id)
            table_rows = [entry for entry in rows if str(entry.get("table_id") or "") == table_id]
            table_ref, table_nodes = _build_table_nodes(
                parent_ref=root_ref,
                ancestor_refs=[root_ref],
                table_id=table_id,
                unit_rows=table_rows,
                packet_rows=packet_rows,
                packet=packet,
                images_by_page=images_by_page,
            )
            direct_refs.append(table_ref)
            nodes.extend(table_nodes)
            continue
        paragraph_ref, paragraph_nodes = _build_paragraph_nodes(
            parent_ref=root_ref,
            ancestor_refs=[root_ref],
            row=row,
            packet=packet,
            images_by_page=images_by_page,
        )
        direct_refs.append(paragraph_ref)
        nodes.extend(paragraph_nodes)

    for source_ref in requested_object_refs:
        fact = objects_by_ref.get(source_ref)
        if fact is None:
            continue
        object_ref = f"source_object:{fact.get('object_id') or source_ref}"
        node = _leaf_node(
            ref=object_ref,
            source_kind=str(fact.get("object_type") or "source_object"),
            parent_ref=root_ref,
            ancestor_refs=[root_ref],
            source_refs=[source_ref],
            source_seq_refs=[fact.get("source_seq_anchor")],
            page_nos=[fact.get("page_no")],
            facts={"object": deepcopy(fact)},
            completeness=_completeness(
                children_complete=True,
                content_complete=bool(fact),
                visual_complete=_object_visual_complete(fact, images_by_page),
                unbound_member_count=(
                    0 if str(fact.get("binding_status") or "") not in {"unbound", "missing"} else 1
                ),
            ),
            visual_evidence=_visual_evidence(
                ref=object_ref,
                rows=[fact],
                images_by_page=images_by_page,
                render_status=packet.get("render_status"),
            ),
        )
        direct_refs.append(object_ref)
        nodes.append(node)

    existing_seqs = {_as_int(row.get("source_seq")) for row in rows}
    missing_seqs = sorted(set(requested_seqs) - {seq for seq in existing_seqs if seq is not None})
    missing_objects = sorted(set(requested_object_refs) - set(objects_by_ref))
    children = {str(node.get("ref")): node for node in nodes}
    member_leaf_refs = _member_union(direct_refs, children)
    pages = _pages(rows)
    root_completeness = _with_descendant_completeness(
        _completeness(
            children_complete=not missing_seqs and not missing_objects,
            content_complete=not missing_seqs,
            visual_complete=_visual_complete(pages, images_by_page, packet.get("render_status")),
            omitted_child_count=len(missing_seqs) + len(missing_objects),
            reasons=[
                *(f"missing source_seq {seq}" for seq in missing_seqs),
                *(f"missing source_object {ref}" for ref in missing_objects),
            ],
        ),
        child_refs=direct_refs,
        child_lookup=children,
    )
    root = _node(
        ref=root_ref,
        source_kind="unit",
        parent_ref=None,
        ancestor_refs=[],
        child_refs=direct_refs,
        member_leaf_refs=member_leaf_refs,
        source_refs=[str(row.get("source_ref")) for row in rows if row.get("source_ref")]
        + requested_object_refs,
        source_seq_refs=requested_seqs,
        page_nos=pages,
        facts={
            "unit_id": unit_id,
            "t2_window_id": window.get("window_id"),
            "ordered_text": [
                {"source_seq": row.get("source_seq"), "text": row.get("text", "")}
                for row in rows
            ],
            "direct_child_count": len(direct_refs),
        },
        completeness=root_completeness,
        visual_evidence=_visual_evidence(
            ref=root_ref,
            rows=rows,
            images_by_page=images_by_page,
            render_status=packet.get("render_status"),
        ),
        context={"neighbor_units": deepcopy(window.get("neighbor_context") or {})},
    )
    return root_ref, [root, *nodes]


def _build_table_nodes(
    *,
    parent_ref: str,
    ancestor_refs: list[str],
    table_id: str,
    unit_rows: list[dict[str, Any]],
    packet_rows: list[dict[str, Any]],
    packet: dict[str, Any],
    images_by_page: dict[int, dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    table_ref = f"table:{table_id}"
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    unbound = 0
    for row in unit_rows:
        row_no, _column_no = _cell_position(row)
        if row_no is None:
            unbound += 1
            row_no = 1_000_000 + unbound
        grouped[row_no].append(row)

    nodes: list[dict[str, Any]] = []
    row_refs: list[str] = []
    cell_owner_by_run_signature: dict[tuple[str, ...], str] = {}
    for row_no in sorted(grouped):
        row_ref = f"{table_ref}/row:{row_no:03d}"
        row_refs.append(row_ref)
        cell_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in grouped[row_no]:
            _parsed_row, column_no = _cell_position(row)
            cell_key = str(row.get("cell_id") or f"column:{column_no or len(cell_groups) + 1}")
            cell_groups[cell_key].append(row)
        cell_refs: list[str] = []
        row_nodes: list[dict[str, Any]] = []
        for cell_order, cell_rows in enumerate(cell_groups.values(), start=1):
            _row_no, column_no = _cell_position(cell_rows[0])
            cell_ref = f"{row_ref}/cell:{column_no or cell_order:03d}"
            cell_refs.append(cell_ref)
            run_signature = tuple(
                sorted(
                    {
                        raw_run_id
                        for cell_row in cell_rows
                        for raw_run_id in _strings(cell_row.get("raw_run_ids"))
                    }
                )
            )
            alias_of = cell_owner_by_run_signature.get(run_signature) if run_signature else None
            if run_signature and alias_of is None:
                cell_owner_by_run_signature[run_signature] = cell_ref
            if alias_of is not None:
                alias_node = _leaf_node(
                    ref=cell_ref,
                    source_kind="cell",
                    parent_ref=row_ref,
                    ancestor_refs=[*ancestor_refs, table_ref, row_ref],
                    source_refs=[
                        str(row.get("source_ref"))
                        for row in cell_rows
                        if row.get("source_ref")
                    ],
                    source_seq_refs=[row.get("source_seq") for row in cell_rows],
                    page_nos=_pages(cell_rows),
                    facts={
                        "cell_id": cell_rows[0].get("cell_id"),
                        "column": column_no or cell_order,
                        "text": "\n".join(str(row.get("text") or "") for row in cell_rows),
                        "paragraph_count": 0,
                        "merged_alias_of_cell_ref": alias_of,
                        "duplicate_raw_run_ids": list(run_signature),
                        "merge_fact_status": "missing_in_l1_projection",
                    },
                    completeness=_completeness(
                        children_complete=False,
                        content_complete=False,
                        visual_complete=_visual_complete(
                            _pages(cell_rows), images_by_page, packet.get("render_status")
                        ),
                        unbound_member_count=len(run_signature),
                        reasons=[
                            "duplicate run identities indicate a merged-cell alias, but "
                            "gridSpan/vMerge facts are absent from the L1 stage projection"
                        ],
                    ),
                    visual_evidence=_visual_evidence(
                        ref=cell_ref,
                        rows=cell_rows,
                        images_by_page=images_by_page,
                        render_status=packet.get("render_status"),
                    ),
                )
                row_nodes.append(alias_node)
                continue
            paragraph_refs: list[str] = []
            cell_nodes: list[dict[str, Any]] = []
            for cell_row in cell_rows:
                paragraph_ref, paragraph_nodes = _build_paragraph_nodes(
                    parent_ref=cell_ref,
                    ancestor_refs=[*ancestor_refs, table_ref, row_ref, cell_ref],
                    row=cell_row,
                    packet=packet,
                    images_by_page=images_by_page,
                )
                paragraph_refs.append(paragraph_ref)
                cell_nodes.extend(paragraph_nodes)
            child_lookup = {str(node.get("ref")): node for node in cell_nodes}
            cell_node = _node(
                ref=cell_ref,
                source_kind="cell",
                parent_ref=row_ref,
                ancestor_refs=[*ancestor_refs, table_ref, row_ref],
                child_refs=paragraph_refs,
                member_leaf_refs=_member_union(paragraph_refs, child_lookup),
                source_refs=[str(row.get("source_ref")) for row in cell_rows if row.get("source_ref")],
                source_seq_refs=[row.get("source_seq") for row in cell_rows],
                page_nos=_pages(cell_rows),
                facts={
                    "cell_id": cell_rows[0].get("cell_id"),
                    "column": column_no or cell_order,
                    "text": "\n".join(str(row.get("text") or "") for row in cell_rows),
                    "paragraph_count": len(paragraph_refs),
                },
                completeness=_rows_completeness(
                    cell_rows,
                    pages=_pages(cell_rows),
                    images_by_page=images_by_page,
                    render_status=packet.get("render_status"),
                ),
                visual_evidence=_visual_evidence(
                    ref=cell_ref,
                    rows=cell_rows,
                    images_by_page=images_by_page,
                    render_status=packet.get("render_status"),
                ),
            )
            row_nodes.extend([cell_node, *cell_nodes])
        row_lookup = {str(node.get("ref")): node for node in row_nodes}
        row_completeness = _with_descendant_completeness(
            _rows_completeness(
                grouped[row_no],
                pages=_pages(grouped[row_no]),
                images_by_page=images_by_page,
                render_status=packet.get("render_status"),
            ),
            child_refs=cell_refs,
            child_lookup=row_lookup,
        )
        row_node = _node(
            ref=row_ref,
            source_kind="row",
            parent_ref=table_ref,
            ancestor_refs=[*ancestor_refs, table_ref],
            child_refs=cell_refs,
            member_leaf_refs=_member_union(cell_refs, row_lookup),
            source_refs=[str(row.get("source_ref")) for row in grouped[row_no] if row.get("source_ref")],
            source_seq_refs=[row.get("source_seq") for row in grouped[row_no]],
            page_nos=_pages(grouped[row_no]),
            facts={
                "row": row_no,
                "text": " | ".join(str(row.get("text") or "") for row in grouped[row_no]),
                "cell_count": len(cell_refs),
            },
            completeness=row_completeness,
            visual_evidence=_visual_evidence(
                ref=row_ref,
                rows=grouped[row_no],
                images_by_page=images_by_page,
                render_status=packet.get("render_status"),
            ),
        )
        nodes.extend([row_node, *row_nodes])

    packet_table_seqs = {
        _as_int(row.get("source_seq"))
        for row in packet_rows
        if str(row.get("table_id") or "") == table_id
    }
    unit_table_seqs = {_as_int(row.get("source_seq")) for row in unit_rows}
    omitted = {
        seq for seq in packet_table_seqs - unit_table_seqs if seq is not None
    }
    lookup = {str(node.get("ref")): node for node in nodes}
    table_completeness = _with_descendant_completeness(
        _completeness(
            children_complete=not omitted and unbound == 0,
            content_complete=not omitted,
            visual_complete=_visual_complete(
                _pages(unit_rows), images_by_page, packet.get("render_status")
            ),
            omitted_child_count=len(omitted),
            unbound_member_count=unbound,
            reasons=[
                *(f"table member outside T2 unit: source_seq {seq}" for seq in sorted(omitted)),
                *([f"{unbound} table members have no stable row identity"] if unbound else []),
            ],
        ),
        child_refs=row_refs,
        child_lookup=lookup,
    )
    table_node = _node(
        ref=table_ref,
        source_kind="table",
        parent_ref=parent_ref,
        ancestor_refs=ancestor_refs,
        child_refs=row_refs,
        member_leaf_refs=_member_union(row_refs, lookup),
        source_refs=[str(row.get("source_ref")) for row in unit_rows if row.get("source_ref")],
        source_seq_refs=[row.get("source_seq") for row in unit_rows],
        page_nos=_pages(unit_rows),
        facts={
            "table_id": table_id,
            "row_count": len(row_refs),
            "text_by_row": [
                " | ".join(str(row.get("text") or "") for row in grouped[row_no])
                for row_no in sorted(grouped)
            ],
        },
        completeness=table_completeness,
        visual_evidence=_visual_evidence(
            ref=table_ref,
            rows=unit_rows,
            images_by_page=images_by_page,
            render_status=packet.get("render_status"),
        ),
    )
    return table_ref, [table_node, *nodes]


def _build_paragraph_nodes(
    *,
    parent_ref: str,
    ancestor_refs: list[str],
    row: dict[str, Any],
    packet: dict[str, Any],
    images_by_page: dict[int, dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    paragraph_id = str(row.get("paragraph_id") or row.get("node_id") or row.get("source_seq"))
    paragraph_ref = f"{parent_ref}/paragraph:{paragraph_id}"
    run_facts = [
        run
        for run in (row.get("style_details") or {}).get("runs", []) or []
        if isinstance(run, dict)
    ]
    raw_ids = _strings(row.get("raw_run_ids"))
    facts_by_raw = {
        str(run.get("raw_run_id")): run for run in run_facts if run.get("raw_run_id")
    }
    run_refs: list[str] = []
    run_nodes: list[dict[str, Any]] = []
    for order, raw_id in enumerate(raw_ids):
        fact = facts_by_raw.get(raw_id) or (
            run_facts[order] if order < len(run_facts) else {}
        )
        run_ref = f"run:{raw_id}"
        run_refs.append(run_ref)
        run_text = str(fact.get("text") or "")
        span_specs = partition_atomic_run_spans(
            raw_run_id=raw_id,
            text=run_text,
        )
        span_refs = [str(span["ref"]) for span in span_specs]
        span_nodes = [
            _leaf_node(
                ref=str(span["ref"]),
                source_kind="span",
                parent_ref=run_ref,
                ancestor_refs=[*ancestor_refs, paragraph_ref, run_ref],
                source_refs=[fact.get("source_ref")],
                source_seq_refs=[row.get("source_seq")],
                page_nos=[row.get("page_no")],
                facts={
                    "span_ref": span["ref"],
                    "run_ref": run_ref,
                    "raw_run_id": raw_id,
                    "logical_run_id": fact.get("logical_run_id"),
                    "start": span["start"],
                    "end": span["end"],
                    "text": span["text"],
                    "run_text_length": len(run_text),
                    "effective_style": deepcopy(fact.get("effective_style") or {}),
                    "segmentation_version": span["segmentation_version"],
                },
                completeness=_completeness(
                    children_complete=True,
                    content_complete=bool(fact) or not str(row.get("text") or ""),
                    visual_complete=_visual_complete(
                        _pages([row]), images_by_page, packet.get("render_status")
                    ),
                    unbound_member_count=0 if fact else 1,
                    reasons=[] if fact else [f"raw run facts missing for {raw_id}"],
                ),
                visual_evidence=_visual_evidence(
                    ref=str(span["ref"]),
                    rows=[row],
                    images_by_page=images_by_page,
                    render_status=packet.get("render_status"),
                ),
            )
            for span in span_specs
        ]
        run_nodes.extend(
            [
                _node(
                    ref=run_ref,
                    source_kind="run",
                    parent_ref=paragraph_ref,
                    ancestor_refs=[*ancestor_refs, paragraph_ref],
                    child_refs=span_refs,
                    member_leaf_refs=span_refs,
                    source_refs=[fact.get("source_ref")],
                    source_seq_refs=[row.get("source_seq")],
                    page_nos=[row.get("page_no")],
                    facts={
                        "raw_run_id": raw_id,
                        "logical_run_id": fact.get("logical_run_id"),
                        "order": order,
                        "text": run_text,
                        "char_length": len(run_text),
                        "atomic_span_count": len(span_refs),
                        "effective_style": deepcopy(
                            fact.get("effective_style") or {}
                        ),
                    },
                    completeness=_completeness(
                        children_complete=True,
                        content_complete=bool(fact)
                        or not str(row.get("text") or ""),
                        visual_complete=_visual_complete(
                            _pages([row]),
                            images_by_page,
                            packet.get("render_status"),
                        ),
                        unbound_member_count=0 if fact else 1,
                        reasons=[]
                        if fact
                        else [f"raw run facts missing for {raw_id}"],
                    ),
                    visual_evidence=_visual_evidence(
                        ref=run_ref,
                        rows=[row],
                        images_by_page=images_by_page,
                        render_status=packet.get("render_status"),
                    ),
                ),
                *span_nodes,
            ]
        )
    if not run_refs:
        # Empty/field-only paragraphs still need an atomic identity for complete
        # deterministic coverage; no synthetic Word run is created.
        run_refs = [paragraph_ref]
    paragraph_node = _node(
        ref=paragraph_ref,
        source_kind="paragraph",
        parent_ref=parent_ref,
        ancestor_refs=ancestor_refs,
        child_refs=[ref for ref in run_refs if ref != paragraph_ref],
        member_leaf_refs=(
            _member_union(
                run_refs,
                {str(node.get("ref")): node for node in run_nodes},
            )
            if run_nodes
            else [paragraph_ref]
        ),
        source_refs=[row.get("source_ref")],
        source_seq_refs=[row.get("source_seq")],
        page_nos=[row.get("page_no")],
        facts={
            "paragraph_id": paragraph_id,
            "text": row.get("text", ""),
            "paragraph_style": deepcopy((row.get("style_details") or {}).get("paragraph") or {}),
            "raw_run_count": len(raw_ids),
            "render_binding_status": row.get("render_binding_status"),
        },
        completeness=_rows_completeness(
            [row],
            pages=_pages([row]),
            images_by_page=images_by_page,
            render_status=packet.get("render_status"),
            content_complete=(
                bool(raw_ids and len(run_facts) >= len(raw_ids))
                or (not raw_ids and bool(row.get("source_ref") or row.get("paragraph_id")))
            ),
        ),
        visual_evidence=_visual_evidence(
            ref=paragraph_ref,
            rows=[row],
            images_by_page=images_by_page,
            render_status=packet.get("render_status"),
        ),
    )
    return paragraph_ref, [paragraph_node, *run_nodes]


def _node(
    *,
    ref: str,
    source_kind: str,
    parent_ref: str | None,
    ancestor_refs: list[str],
    child_refs: list[str],
    member_leaf_refs: list[str],
    source_refs: list[Any],
    source_seq_refs: list[Any],
    page_nos: list[Any],
    facts: dict[str, Any],
    completeness: dict[str, Any],
    visual_evidence: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ref": ref,
        "source_kind": source_kind,
        "parent_ref": parent_ref,
        "ancestor_refs": list(ancestor_refs),
        "child_refs": list(dict.fromkeys(child_refs)),
        "member_leaf_refs": sorted(set(member_leaf_refs)),
        "source_refs": list(dict.fromkeys(_strings(source_refs))),
        "source_seq_refs": sorted(set(_ints(source_seq_refs))),
        "page_nos": sorted(set(_ints(page_nos))),
        "bbox_refs": [
            {"page_no": item.get("page_no"), "bbox": deepcopy(item.get("bbox"))}
            for item in visual_evidence
            if item.get("bbox") is not None
        ],
        "facts": facts,
        "completeness": completeness,
        "visual_evidence": visual_evidence,
        "context": context or {},
    }


def _leaf_node(**kwargs: Any) -> dict[str, Any]:
    ref = str(kwargs["ref"])
    return _node(
        child_refs=[],
        member_leaf_refs=[ref],
        context={},
        **kwargs,
    )


def _rows_completeness(
    rows: list[dict[str, Any]],
    *,
    pages: list[int],
    images_by_page: dict[int, dict[str, Any]],
    render_status: Any,
    content_complete: bool | None = None,
) -> dict[str, Any]:
    unbound = sum(
        1
        for row in rows
        if str(row.get("render_binding_status") or "") in {"unbound", "missing"}
    )
    return _completeness(
        children_complete=True,
        content_complete=(True if content_complete is None else content_complete),
        visual_complete=_visual_complete(pages, images_by_page, render_status),
        unbound_member_count=unbound,
        reasons=(
            [f"{unbound} members have no render binding"] if unbound else []
        ),
    )


def _completeness(
    *,
    children_complete: bool,
    content_complete: bool,
    visual_complete: bool,
    truncated: bool = False,
    unbound_member_count: int = 0,
    omitted_child_count: int = 0,
    reasons: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "children_complete": bool(children_complete),
        "content_complete": bool(content_complete),
        "visual_complete": bool(visual_complete),
        "truncated": bool(truncated),
        "unbound_member_count": int(unbound_member_count),
        "omitted_child_count": int(omitted_child_count),
        "completeness_reasons": list(reasons or []),
    }


def _with_descendant_completeness(
    base: dict[str, Any],
    *,
    child_refs: list[str],
    child_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result = deepcopy(base)
    children = [child_lookup[ref] for ref in child_refs if ref in child_lookup]
    incomplete_children = [
        child
        for child in children
        if not bool((child.get("completeness") or {}).get("content_complete"))
    ]
    result["content_complete"] = bool(
        result.get("content_complete") and not incomplete_children
    )
    result["unbound_member_count"] = int(result.get("unbound_member_count") or 0) + sum(
        int((child.get("completeness") or {}).get("unbound_member_count") or 0)
        for child in children
    )
    result["omitted_child_count"] = int(result.get("omitted_child_count") or 0) + sum(
        int((child.get("completeness") or {}).get("omitted_child_count") or 0)
        for child in children
    )
    reasons = list(result.get("completeness_reasons") or [])
    reasons.extend(
        f"descendant incomplete: {child.get('ref')}"
        for child in incomplete_children
    )
    result["completeness_reasons"] = list(dict.fromkeys(reasons))
    return result


def _visual_evidence(
    *,
    ref: str,
    rows: list[dict[str, Any]],
    images_by_page: dict[int, dict[str, Any]],
    render_status: Any,
) -> list[dict[str, Any]]:
    if render_status != "real_render":
        return []
    result: list[dict[str, Any]] = []
    for page_no in _pages(rows):
        image = images_by_page.get(page_no) or {}
        path = image.get("path")
        if not path:
            continue
        page_rows = [row for row in rows if _as_int(row.get("page_no")) == page_no]
        bbox = _union_bbox([row.get("bbox") for row in page_rows])
        result.append(
            {
                "visual_ref": f"visual:{ref}:page:{page_no}",
                "target_ref": ref,
                "kind": "page_context",
                "page_no": page_no,
                "bbox": bbox,
                "sha256": image.get("sha256"),
                "coverage": "full" if bbox is not None else "partial",
                "width_px": image.get("width_px"),
                "height_px": image.get("height_px"),
                "_attachment_path": str(path),
            }
        )
    return result


def _visual_complete(
    pages: list[int],
    images_by_page: dict[int, dict[str, Any]],
    render_status: Any,
) -> bool:
    return bool(
        pages
        and render_status == "real_render"
        and all((images_by_page.get(page_no) or {}).get("path") for page_no in pages)
    )


def _object_visual_complete(
    fact: dict[str, Any],
    images_by_page: dict[int, dict[str, Any]],
) -> bool:
    page_no = _as_int(fact.get("page_no"))
    return bool(page_no is not None and (images_by_page.get(page_no) or {}).get("path"))


def _union_bbox(values: list[Any]) -> dict[str, Any] | None:
    boxes = [value for value in values if isinstance(value, dict)]
    if not boxes:
        return None
    coordinates = ("x_min", "y_min", "x_max", "y_max")
    if any(any(not isinstance(box.get(key), (int, float)) for key in coordinates) for box in boxes):
        return None
    first = boxes[0]
    return {
        "x_min": min(float(box["x_min"]) for box in boxes),
        "y_min": min(float(box["y_min"]) for box in boxes),
        "x_max": max(float(box["x_max"]) for box in boxes),
        "y_max": max(float(box["y_max"]) for box in boxes),
        **{
            key: first.get(key)
            for key in ("page_width", "page_height", "unit")
            if first.get(key) is not None
        },
    }


def _member_union(
    child_refs: list[str],
    by_ref: dict[str, dict[str, Any]],
) -> list[str]:
    return sorted(
        {
            leaf_ref
            for child_ref in child_refs
            for leaf_ref in _strings((by_ref.get(child_ref) or {}).get("member_leaf_refs"))
        }
    )


def _pages(rows: list[dict[str, Any]]) -> list[int]:
    return sorted(
        {
            page_no
            for row in rows
            if (page_no := _as_int(row.get("page_no"))) is not None
        }
    )


def _cell_position(row: dict[str, Any]) -> tuple[int | None, int | None]:
    cell_id = str(row.get("cell_id") or "")
    match = _CELL_ID_RE.match(cell_id)
    if match:
        return int(match.group("row")), int(match.group("column"))
    source_ref = str(row.get("source_ref") or "")
    row_match = re.search(r"/tr\[(\d+)\]", source_ref)
    cell_match = re.search(r"/tc\[(\d+)\]", source_ref)
    return (
        int(row_match.group(1)) if row_match else None,
        int(cell_match.group(1)) if cell_match else None,
    )


def _strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value or "").strip()]


def _ints(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    return [value for value in (_as_int(item) for item in values) if value is not None]


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None
