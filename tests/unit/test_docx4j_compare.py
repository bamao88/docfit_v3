from __future__ import annotations

from pathlib import Path

from docx import Document

from docfit.core.io import read_json
from docfit.ooxml.docx4j_compare import (
    build_docx4j_comparison_report,
    run_docx4j_inspector,
    write_docx4j_comparison_outputs,
)


def _tool_result(status: str = "available") -> dict:
    return {
        "status": status,
        "command": ["fake-docx4j"],
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:01+00:00",
        "returncode": 0,
        "stdout_excerpt": "",
        "stderr_excerpt": "",
    }


def test_comparison_marks_docx4j_only_visible_objects(tmp_path: Path) -> None:
    docx_path = tmp_path / "source.docx"
    docx_path.write_bytes(b"not-a-real-docx-for-pure-report-test")
    python_inspection = {
        "data": {
            "paragraphs": [
                {"text": "正文", "source_ref": "word/document.xml:p[1]"},
            ],
            "tables": [],
            "headers_footers": [],
            "fields": [],
            "footnotes": [],
            "text_boxes": [],
            "images": [],
            "breaks": [],
            "sections": [],
            "numbering_refs": [],
            "numbering_definitions": [],
            "unknown_visible_objects": [],
        }
    }
    docx4j_inspection = {
        "data": {
            "paragraphs": [
                {"text": "正文", "source_ref": "word/document.xml:p[1]"},
            ],
            "tables": [],
            "headers_footers": [],
            "fields": [],
            "footnotes": [],
            "text_boxes": [
                {"text": "文本框内容", "source_ref": "word/document.xml:txbxContent[1]"},
            ],
            "images": [
                {"target": "word/media/image1.png", "source_ref": "word/document.xml:drawing[1]"},
            ],
            "breaks": [],
            "sections": [],
            "numbering_refs": [],
            "numbering_definitions": [],
            "unknown_visible_objects": [],
        }
    }

    report = build_docx4j_comparison_report(
        docx_path,
        python_inspection,
        docx4j_inspection,
        tool_result=_tool_result(),
    )

    assert report["comparison_status"] == "compared"
    assert report["gate_policy"]["decides_pass_fail"] is False
    count_diffs = report["data"]["count_differences"]
    assert {
        (diff["kind"], diff["category"])
        for diff in count_diffs
    } >= {
        ("python_missing_docx4j_seen", "text_boxes"),
        ("python_missing_docx4j_seen", "images"),
    }
    text_diffs = report["data"]["visible_text_differences"]
    assert text_diffs["docx4j_only"][0]["text_preview"] == "文本框内容"


def test_run_docx4j_inspector_reports_unavailable_when_command_is_missing(
    tmp_path: Path,
) -> None:
    docx_path = tmp_path / "source.docx"
    output_json = tmp_path / "out" / "docx4j.json"
    docx_path.write_bytes(b"not-a-real-docx-for-tool-missing-test")

    result = run_docx4j_inspector(
        docx_path,
        output_json,
        command=["/definitely/missing-docx4j-inspector"],
    )

    assert result["status"] == "unavailable"
    assert "not found" in result["error"]
    assert not output_json.exists()


def test_write_outputs_keeps_report_diagnostic_when_java_tool_is_unavailable(
    tmp_path: Path,
) -> None:
    docx_path = tmp_path / "source.docx"
    document = Document()
    document.add_paragraph("可见正文")
    document.save(docx_path)

    out_dir = tmp_path / "diagnostics"
    report = write_docx4j_comparison_outputs(
        docx_path,
        out_dir,
        command=["/definitely/missing-docx4j-inspector"],
    )

    assert report["tool"]["status"] == "unavailable"
    assert report["comparison_status"] == "not_run"
    assert report["data"]["count_differences"] == []
    assert (out_dir / "artifacts" / "python_inspection.json").exists()
    assert not (out_dir / "artifacts" / "docx4j_inspection.json").exists()
    saved_report = read_json(out_dir / "docx4j_comparison_report.json")
    assert saved_report["gate_policy"]["decides_pass_fail"] is False
    assert (out_dir / "docx4j_comparison_report.md").exists()
