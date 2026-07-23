from __future__ import annotations

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
                    "source_ref": (
                        f"word/document.xml:tbl[1]/tr[{row_no}]/tc[{column_no}]"
                    ),
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


def t2_unit_result_item() -> dict:
    return {
        "unit_id": "cover",
        "source_seq_refs": list(range(1, 8)),
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
            "instruction": 'TOC \\o "3-3" \\h \\z',
            "paragraph_index": 65,
            "end_paragraph_index": 102,
            "end_source_ref": "word/document.xml:p[102]",
        }
    ]
    return packet


def toc_t2_unit_result_item() -> dict:
    return {
        "unit_id": "toc",
        "source_seq_refs": [],
        "source_ref_refs": [
            "word/document.xml:p[65]/field[39]",
        ],
        "source_ref_range": {
            "start": "word/document.xml:p[65]/field[39]",
            "end": "word/document.xml:p[65]/field[39]",
        },
    }
