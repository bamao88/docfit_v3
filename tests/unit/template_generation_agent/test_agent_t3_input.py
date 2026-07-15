from __future__ import annotations

from docfit.template_generation.agent.t3_input import (
    build_t3_local_evidence,
    build_t3_object_plan_evidence,
    build_t3_object_tasks,
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


def test_t3_table_input_keeps_object_and_row_structure_before_local_split() -> None:
    tasks = build_t3_object_tasks(
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


def test_t3_local_evidence_contains_plan_and_only_claimable_plus_context_rows() -> None:
    packet = table_packet()
    task = build_t3_object_tasks(
        packet,
        unit_windows=[unit_window()],
        max_table_items=2,
    )[0]
    local = task["local_windows"][1]
    evidence = build_t3_local_evidence(
        packet,
        task=task,
        local_window=local,
        object_plan={
            "object_hypothesis": {
                "archetype": "metadata_form",
                "purpose": "学生信息",
                "confidence": "high",
                "invented": "drop me",
            },
            "quality_risks": ["不要把标签和值合并"],
            "items": [{"policy": "fill"}],
        },
    )

    assert evidence["scope"] == "t3_object_local_window"
    assert evidence["object_plan"]["object_hypothesis"] == {
        "archetype": "metadata_form",
        "purpose": "学生信息",
        "confidence": "high",
    }
    assert "items" not in evidence["object_plan"]
    assert {row["source_seq"] for row in evidence["rows"]} == (
        set(local["source_seq_refs"]) | set(local["context_source_seq_refs"])
    )
    claimable = {row["source_seq"] for row in evidence["rows"] if row["evidence_role"] == "claimable"}
    assert claimable == set(local["source_seq_refs"])
    assert evidence["rows"][0]["runs"][0]["raw_run_id"]


def test_t3_object_plan_evidence_is_overview_not_full_local_rows() -> None:
    packet = table_packet()
    task = build_t3_object_tasks(packet, unit_windows=[unit_window()])[0]
    evidence = build_t3_object_plan_evidence(packet, task=task)

    assert evidence["scope"] == "t3_object_overview"
    assert evidence["object_overview"]["object_type"] == "table"
    assert "rows" not in evidence
