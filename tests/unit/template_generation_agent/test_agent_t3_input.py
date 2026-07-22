from __future__ import annotations

from docfit.template_generation.agent.t3_input import (
    build_t3_local_evidence,
    build_t3_local_tasks,
    build_t3_unit_plan_evidence,
    sanitize_unit_plan,
)
from docfit.template_generation.agent.observation_windows import (
    build_observation_windows,
)


def table_packet() -> dict:
    rows = []
    seq = 1
    for row_no, values in enumerate(
        [
            ("字段", "内容"),
            ("学生姓名", "张三"),
            ("指导教师签字", "________"),
        ],
        start=1,
    ):
        for column_no, text in enumerate(values, start=1):
            raw_id = f"p_{seq:04d}.r_001"
            rows.append(
                {
                    "source_seq": seq,
                    "source_ref": f"word/document.xml:tbl[1]/tr[{row_no}]/tc[{column_no}]",
                    "kind": "table_cell",
                    "paragraph_id": f"p_{seq:04d}",
                    "table_id": "tbl_0001",
                    "cell_id": f"tbl_0001.r_{row_no:03d}.c_{column_no:03d}",
                    "text": text,
                    "raw_run_ids": [raw_id],
                    "logical_run_ids": [f"p_{seq:04d}.lr_001"],
                    "style_details": {
                        "paragraph": {"alignment": "center"},
                        "dominant_run": {"bold": column_no == 1},
                        "runs": [{"text": text, "bold": column_no == 1}],
                    },
                    "page_no": 1,
                    "render_target_id": f"source_seq:{seq}",
                }
            )
            seq += 1
    rows.append(
        {
            "source_seq": seq,
            "source_ref": "word/document.xml:p[99]",
            "kind": "paragraph",
            "paragraph_id": "p_0099",
            "text": "表格后的说明",
            "raw_run_ids": ["p_0099.r_001"],
            "logical_run_ids": ["p_0099.lr_001"],
            "style_details": {"runs": [{"text": "表格后的说明"}]},
            "page_no": 1,
        }
    )
    return {
        "source_render_hash": "sha256:test",
        "page_text_index": rows,
        "render_artifacts": {"clean_page_images": []},
    }


def unit_window() -> dict:
    return {
        "window_id": "unit:cover",
        "unit_id": "cover",
        "source_seq_refs": list(range(1, 8)),
        "neighbor_context": {"previous_unit_id": None, "next_unit_id": "body_main"},
    }


def toc_object_packet() -> dict:
    packet = table_packet()
    packet["object_fact_index"] = [
        {
            "object_id": "field:word/document.xml:p[65]/field[39]",
            "object_type": "field",
            "source_ref": "word/document.xml:p[65]/field[39]",
            "part_name": "word/document.xml",
            "kind": "complexField",
            "field_type": "TOC",
            "instruction": "TOC \\o \"3-3\" \\h \\z",
            "paragraph_index": 65,
            "end_paragraph_index": 102,
            "end_source_ref": "word/document.xml:p[102]",
        }
    ]
    return packet


def toc_object_window() -> dict:
    packet = toc_object_packet()
    windows = build_observation_windows(
        ai_unit_observation={
            "artifact_type": "t3_gold_unit_observation",
            "items": [
                {
                    "unit_id": "toc",
                    "source_seq_refs": [],
                    "source_ref_refs": [
                        "word/document.xml:p[65]/field[39]"
                    ],
                    "source_ref_range": {
                        "start": "word/document.xml:p[65]/field[39]",
                        "end": "word/document.xml:p[65]/field[39]",
                    },
                }
            ],
        },
        packet=packet,
    )
    return windows["windows"][0]


def test_t3_table_input_keeps_object_and_row_structure_before_local_split() -> None:
    tasks = build_t3_local_tasks(
        table_packet(),
        unit_windows=[unit_window()],
        max_table_items=2,
    )

    assert [task["object_type"] for task in tasks] == ["table", "text_flow"]
    table = tasks[0]
    assert table["object_overview"]["dimensions"] == {"rows": 3, "columns": 2}
    assert len(table["local_windows"]) == 3
    assert table["local_windows"][0]["source_seq_refs"] == [1, 2]
    assert table["local_windows"][1]["source_seq_refs"] == [3, 4]
    # 后续行组可读第一行和相邻行，但只有自己的行可以正式认领。
    assert {1, 2} <= set(table["local_windows"][1]["context_source_seq_refs"])


def test_t3_local_evidence_contains_unit_route_and_only_claimable_plus_context_rows() -> None:
    packet = table_packet()
    task = build_t3_local_tasks(
        packet,
        unit_windows=[unit_window()],
        max_table_items=2,
    )[0]
    local = task["local_windows"][1]
    evidence = build_t3_local_evidence(
        packet,
        task=task,
        local_window=local,
        unit_plan={
            "route": "inspect_suspected_regions",
            "default_preservation_policy": "fixed",
        },
    )

    assert evidence["scope"] == "t3_local_window"
    assert evidence["unit_plan"]["route"] == "inspect_suspected_regions"
    assert {row["source_seq"] for row in evidence["rows"]} == (
        set(local["source_seq_refs"]) | set(local["context_source_seq_refs"])
    )
    claimable = {row["source_seq"] for row in evidence["rows"] if row["evidence_role"] == "claimable"}
    assert claimable == set(local["source_seq_refs"])
    assert evidence["rows"][0]["runs"][0]["raw_run_id"]
def test_t3_unit_plan_evidence_preprocesses_table_before_any_policy_call() -> None:
    packet = table_packet()
    tasks = build_t3_local_tasks(packet, unit_windows=[unit_window()])
    evidence = build_t3_unit_plan_evidence(
        packet,
        unit_window=unit_window(),
        tasks=tasks,
    )

    assert evidence["scope"] == "t3_unit_overview"
    assert evidence["unit_overview"]["object_type_counts"] == {"table": 1, "text_flow": 1}
    table = evidence["unit_overview"]["objects"][0]["overview"]
    assert table["dimensions"] == {"rows": 3, "columns": 2}
    assert any(
        "manual_action_language" in region["content_signals"]
        for region in table["candidate_regions"]
    )
    assert {option["route"] for option in evidence["routing_options"]} == {
        "preserve_whole",
        "preserve_structure_classify_fields",
        "inspect_suspected_regions",
        "full_local_analysis",
    }


def test_t3_unit_plan_defaults_to_protected_preservation_when_model_output_is_invalid() -> None:
    plan = sanitize_unit_plan(
        {"route": "delete_everything", "default_preservation_policy": "instruction_remove"},
        unit_window=unit_window(),
    )

    assert plan["route"] == "preserve_structure_classify_fields"
    assert plan["default_preservation_policy"] == "fixed"
    assert plan["protected_source_seq_refs"] == list(range(1, 8))
    assert plan["inspect_source_seq_refs"] == list(range(1, 8))


def test_t3_source_ref_object_becomes_claimable_field_task_and_evidence() -> None:
    packet = toc_object_packet()
    window = toc_object_window()
    tasks = build_t3_local_tasks(packet, unit_windows=[window])

    assert window["source_seq_refs"] == []
    assert window["source_ref_refs"] == [
        "word/document.xml:p[65]/field[39]"
    ]
    assert len(tasks) == 1
    task = tasks[0]
    assert task["object_type"] == "field"
    assert task["source_ref_refs"] == window["source_ref_refs"]

    overview = build_t3_unit_plan_evidence(
        packet,
        unit_window=window,
        tasks=tasks,
    )
    assert overview["unit_overview"]["source_object_count"] == 1
    assert overview["unit_overview"]["objects"][0]["overview"]["facts"][
        "field_type"
    ] == "TOC"

    plan = sanitize_unit_plan(
        {"route": "preserve_structure_classify_fields"},
        unit_window=window,
    )
    assert plan["inspect_source_ref_refs"] == window["source_ref_refs"]
    evidence = build_t3_local_evidence(
        packet,
        task=task,
        local_window=task["local_windows"][0],
        unit_plan=plan,
    )
    assert evidence["rows"] == []
    assert evidence["claimable_source_ref_refs"] == window["source_ref_refs"]
    assert evidence["object_facts"][0]["evidence_role"] == "claimable"
    assert evidence["object_facts"][0]["instruction"].startswith("TOC")
