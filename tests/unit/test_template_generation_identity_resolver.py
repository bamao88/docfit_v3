from __future__ import annotations

from pathlib import Path

from docfit.core.io import sha256_file
from docfit.template_generation.identity_resolver import L1IdentityResolver


def _l1(source: Path) -> dict:
    return {
        "input_hashes": {"source_template": sha256_file(source)},
        "source_text_index": [
            {
                "source_seq": 1,
                "source_ref": "word/document.xml:p[1]",
            },
            {
                "source_seq": 2,
                "source_ref": "word/document.xml:tbl[1]/tr[1]/tc[1]/p[1]",
            },
            {
                "source_seq": 3,
                "source_ref": "word/document.xml:tbl[1]/tr[1]/tc[1]/p[1]",
            },
        ],
        "run_index": {
            "raw_runs": [
                {
                    "raw_run_id": "p_0001.r_001",
                    "source_ref": "word/document.xml:p[1]/r[1]",
                    "text": "学校模板",
                    "parent_source_seq_refs": [1],
                },
                {
                    "raw_run_id": "tbl_0001.r_001",
                    "source_ref": "word/document.xml:tbl[1]/tr[1]/tc[1]/p[1]/r[1]",
                    "text": "重复单元格",
                    "parent_source_seq_refs": [2, 3],
                },
            ]
        },
        "layout_fact_index": {
            "fields": [
                {"source_ref": "word/document.xml:p[1]/field[1]"}
            ]
        },
    }


def test_identity_resolver_rejects_source_package_hash_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    source.write_bytes(b"source")
    resolver = L1IdentityResolver(_l1(source))
    source.write_bytes(b"changed")

    result = resolver.validate_source_package(source)

    assert result["status"] == "FAIL"
    assert result["reason"] == "source DOCX hash does not match sealed L1"


def test_identity_resolver_rejects_unbound_identity_and_span(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    source.write_bytes(b"source")
    resolver = L1IdentityResolver(_l1(source))

    result = resolver.validate_action(
        {
            "action_id": "a_002",
            "action_type": "replace_span_with_slot",
            "source_ref": "word/document.xml:p[10]",
            "affected_source_seq_refs": [10],
            "affected_raw_run_ids": ["missing.r_001"],
            "affected_char_ranges": [
                {"raw_run_id": "p_0001.r_001", "start": 0, "end": 99}
            ],
        }
    )

    assert result["status"] == "FAIL"
    assert "source_ref is not bound in L1" in "\n".join(result["errors"])
    assert "source_seq is not bound in L1" in "\n".join(result["errors"])
    assert "raw_run_id is not bound in L1" in "\n".join(result["errors"])
    assert "char range is outside L1 raw run text" in "\n".join(result["errors"])


def test_identity_resolver_accepts_any_exact_table_parent_binding(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    source.write_bytes(b"source")
    resolver = L1IdentityResolver(_l1(source))

    result = resolver.validate_action(
        {
            "action_id": "a_003",
            "action_type": "remove_instruction_text",
            "source_ref": "word/document.xml:tbl[1]/tr[1]/tc[1]/p[1]",
            "affected_source_seq_refs": [3],
            "affected_raw_run_ids": ["tbl_0001.r_001"],
            "affected_char_ranges": [
                {"raw_run_id": "tbl_0001.r_001", "start": 0, "end": 2}
            ],
        }
    )

    assert result["status"] == "PASS"
    assert result["errors"] == []


def test_identity_resolver_accepts_exact_l1_layout_object_ref(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    source.write_bytes(b"source")
    resolver = L1IdentityResolver(_l1(source))

    result = resolver.validate_action(
        {
            "action_id": "a_004",
            "action_type": "insert_page_break_before_unit",
            "source_ref": "word/document.xml:p[1]/field[1]",
        }
    )

    assert result["status"] == "PASS"
