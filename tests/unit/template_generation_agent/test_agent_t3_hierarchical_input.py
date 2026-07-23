from __future__ import annotations

from copy import deepcopy

from docfit.template_generation.agent.t3_hierarchical_input import (
    build_t3_hierarchical_stage_input,
    nodes_by_ref,
    t3_node_evidence,
    validate_t3_hierarchical_stage_input,
)

from .test_agent_t3_input import table_packet, toc_object_packet, toc_object_window, unit_window


def _windows(*windows: dict) -> dict:
    return {
        "artifact_type": "ai_observation_unit_windows",
        "post_t2_observation_hash": "sha256:t2",
        "windows": list(windows),
    }


def test_hierarchical_input_builds_unit_table_row_cell_paragraph_run_span_tree() -> None:
    artifact = build_t3_hierarchical_stage_input(
        table_packet(),
        unit_windows=_windows(unit_window()),
    )

    validation = validate_t3_hierarchical_stage_input(artifact)
    assert validation == {"valid": True, "errors": []}
    nodes = nodes_by_ref(artifact)
    root = nodes["unit:cover"]
    assert root["child_refs"] == [
        "table:tbl_0001",
        "unit:cover/paragraph:p_0099",
    ]
    table = nodes["table:tbl_0001"]
    assert table["child_refs"] == [
        "table:tbl_0001/row:001",
        "table:tbl_0001/row:002",
        "table:tbl_0001/row:003",
    ]
    first_cell = nodes["table:tbl_0001/row:001/cell:001"]
    assert first_cell["child_refs"] == [
        "table:tbl_0001/row:001/cell:001/paragraph:p_0001"
    ]
    paragraph = nodes[first_cell["child_refs"][0]]
    assert paragraph["child_refs"] == ["run:p_0001.r_001"]
    run = nodes[paragraph["child_refs"][0]]
    assert len(run["child_refs"]) == 1
    assert nodes[run["child_refs"][0]]["source_kind"] == "span"
    assert {
        nodes[ref]["facts"]["raw_run_id"] for ref in root["member_leaf_refs"]
    } == {
        *(f"p_{seq:04d}.r_001" for seq in range(1, 7)),
        "p_0099.r_001",
    }
    assert all(nodes[ref]["source_kind"] == "span" for ref in root["member_leaf_refs"])


def test_run_text_is_partitioned_into_policy_neutral_exact_span_children() -> None:
    packet = table_packet()
    row = packet["page_text_index"][-1]
    row["text"] = "学号：20XX（填写说明）"
    row["style_details"]["runs"][0]["text"] = row["text"]
    artifact = build_t3_hierarchical_stage_input(
        packet,
        unit_windows=_windows({**unit_window(), "source_seq_refs": [7]}),
    )
    nodes = nodes_by_ref(artifact)
    run = nodes["run:p_0099.r_001"]
    spans = [nodes[ref] for ref in run["child_refs"]]

    assert [span["facts"]["text"] for span in spans] == [
        "学号：",
        "20XX",
        "（填写说明）",
    ]
    assert [
        (span["facts"]["start"], span["facts"]["end"]) for span in spans
    ] == [(0, 3), (3, 7), (7, 13)]
    assert all("policy" not in span["facts"] for span in spans)


def test_node_evidence_contains_only_target_and_direct_children() -> None:
    artifact = build_t3_hierarchical_stage_input(
        table_packet(),
        unit_windows=_windows(unit_window()),
    )

    evidence = t3_node_evidence(artifact, target_ref="table:tbl_0001")

    assert evidence["target"]["ref"] == "table:tbl_0001"
    assert [child["source_kind"] for child in evidence["children"]] == [
        "row",
        "row",
        "row",
    ]
    assert all("child_refs" not in child for child in evidence["children"])
    assert "policy" not in str(evidence)


def test_table_cut_across_t2_units_is_incomplete_and_fails_unique_identity() -> None:
    first = {**unit_window(), "unit_id": "cover_a", "window_id": "unit:cover_a", "source_seq_refs": [1, 2]}
    second = {**unit_window(), "unit_id": "cover_b", "window_id": "unit:cover_b", "source_seq_refs": [3, 4, 5, 6, 7]}

    artifact = build_t3_hierarchical_stage_input(
        table_packet(),
        unit_windows=_windows(first, second),
    )
    validation = validate_t3_hierarchical_stage_input(artifact)

    assert validation["valid"] is False
    assert any("duplicate node ref: table:tbl_0001" in error["message"] for error in validation["errors"])
    table_nodes = [node for node in artifact["nodes"] if node["ref"] == "table:tbl_0001"]
    assert all(node["completeness"]["children_complete"] is False for node in table_nodes)
    assert sum(node["completeness"]["omitted_child_count"] for node in table_nodes) > 0


def test_missing_run_facts_are_explicitly_incomplete() -> None:
    packet = table_packet()
    packet["page_text_index"][0]["style_details"]["runs"] = []

    artifact = build_t3_hierarchical_stage_input(
        packet,
        unit_windows=_windows(unit_window()),
    )
    nodes = nodes_by_ref(artifact)

    run = nodes["run:p_0001.r_001"]
    assert run["completeness"]["content_complete"] is False
    assert run["completeness"]["unbound_member_count"] == 1
    assert "raw run facts missing" in run["completeness"]["completeness_reasons"][0]


def test_duplicate_run_identity_across_cells_becomes_incomplete_merge_alias() -> None:
    packet = table_packet()
    owner = packet["page_text_index"][0]
    alias = packet["page_text_index"][1]
    alias.update(
        {
            "paragraph_id": owner["paragraph_id"],
            "text": owner["text"],
            "raw_run_ids": list(owner["raw_run_ids"]),
            "logical_run_ids": list(owner["logical_run_ids"]),
            "style_details": deepcopy(owner["style_details"]),
        }
    )

    artifact = build_t3_hierarchical_stage_input(
        packet,
        unit_windows=_windows(unit_window()),
    )

    assert validate_t3_hierarchical_stage_input(artifact) == {"valid": True, "errors": []}
    nodes = nodes_by_ref(artifact)
    alias_node = nodes["table:tbl_0001/row:001/cell:002"]
    assert alias_node["facts"]["merged_alias_of_cell_ref"] == (
        "table:tbl_0001/row:001/cell:001"
    )
    assert alias_node["facts"]["merge_fact_status"] == "missing_in_l1_projection"
    assert alias_node["completeness"]["content_complete"] is False
    assert nodes["table:tbl_0001"]["completeness"]["content_complete"] is False
    assert nodes["unit:cover"]["completeness"]["content_complete"] is False


def test_real_visual_descriptor_binds_target_bbox_hash_and_attachment() -> None:
    packet = table_packet()
    packet["render_status"] = "real_render"
    packet["render_artifacts"] = {
        "clean_page_images": [
            {
                "page_no": 1,
                "path": "/tmp/page-01.png",
                "sha256": "sha256:image",
                "width_px": 900,
                "height_px": 1200,
            }
        ]
    }
    for row in packet["page_text_index"]:
        row["bbox"] = {"x_min": 10, "y_min": 20, "x_max": 40, "y_max": 60}

    artifact = build_t3_hierarchical_stage_input(
        packet,
        unit_windows=_windows(unit_window()),
    )
    visual = nodes_by_ref(artifact)["table:tbl_0001"]["visual_evidence"][0]

    assert visual["target_ref"] == "table:tbl_0001"
    assert visual["bbox"] == {"x_min": 10.0, "y_min": 20.0, "x_max": 40.0, "y_max": 60.0}
    assert visual["sha256"] == "sha256:image"
    assert visual["coverage"] == "full"
    assert visual["_attachment_path"] == "/tmp/page-01.png"


def test_source_object_without_source_seq_remains_an_atomic_leaf() -> None:
    packet = toc_object_packet()
    window = toc_object_window()
    artifact = build_t3_hierarchical_stage_input(
        packet,
        unit_windows=_windows(window),
    )

    assert validate_t3_hierarchical_stage_input(artifact)["valid"] is True
    root = nodes_by_ref(artifact)["unit:toc"]
    assert len(root["child_refs"]) == 1
    object_node = nodes_by_ref(artifact)[root["child_refs"][0]]
    assert object_node["source_kind"] == "field"
    assert object_node["member_leaf_refs"] == [object_node["ref"]]
    assert object_node["source_seq_refs"] == []
