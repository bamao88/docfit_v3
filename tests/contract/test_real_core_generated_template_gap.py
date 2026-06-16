from __future__ import annotations

from pathlib import Path

from docx import Document

from docfit.convert.orchestrator import run_template_gap_eval
from docfit.core.io import read_json, sha256_file
from docfit.core.status import Status
from docfit.harness.generated_template_gap import summarize_check_items
from docfit.harness.profiles import REAL_CORE_SCHOOLS


ROOT = Path.cwd()


def test_real_core_template_gap_outputs_tree_and_reports_for_all_schools(
    tmp_path,
) -> None:
    for school in REAL_CORE_SCHOOLS:
        school_id = str(school["school_id"])
        out_dir = tmp_path / school_id

        result = run_template_gap_eval(
            ROOT,
            school_id,
            ROOT / school["template_docx"],
            out_dir,
        )

        artifacts = out_dir / "artifacts"
        generated_template = artifacts / "generated_template.docx"
        tree_path = artifacts / "generated_template_tree.json"
        report_json = artifacts / "template_gap_report.json"
        report_md = artifacts / "template_gap_report.md"
        report_docx = artifacts / "template_gap_report.docx"

        assert result.status in {Status.PASS, Status.FAIL, Status.UNKNOWN}
        assert generated_template.exists()
        assert tree_path.exists()
        assert report_json.exists()
        assert report_md.exists()
        assert report_docx.exists()

        tree = read_json(tree_path)
        report = read_json(report_json)
        assert tree["input_valid_docx"] is True
        assert tree["data"]["paragraphs"] or tree["data"]["tables"]
        assert report["generated_template"]["sha256"] == sha256_file(generated_template)
        assert {
            "known_status",
            "display_status",
            "passed_count",
            "failed_count",
            "unknown_count",
            "blocking_status",
        } <= set(report["summary"])
        assert report["check_items"]
        assert any(
            item["check_id"] == "template_generation.output_docx"
            for item in report["check_items"]
        )


def test_generated_template_gap_bad_docx_does_not_pass(tmp_path) -> None:
    bad_docx = tmp_path / "bad_generated_template.docx"
    doc = Document()
    doc.add_paragraph("这不是湖南农业大学模板。")
    doc.save(bad_docx)

    result = run_template_gap_eval(
        ROOT,
        "hunannongye",
        bad_docx,
        tmp_path / "bad_gap",
    )
    report = read_json(tmp_path / "bad_gap/artifacts/template_gap_report.json")

    assert result.status == Status.FAIL
    assert report["summary"]["blocking_status"] == Status.FAIL.value
    assert report["summary"]["failed_count"] > 0
    assert any(
        item["type"] == "template_generation_unit_missing"
        for item in report["check_items"]
    )


def test_generated_template_gap_reports_ooxml_style_details(tmp_path) -> None:
    result = run_template_gap_eval(
        ROOT,
        "hunannongye",
        ROOT / "inputs/school-hunannongye-requirement.docx",
        tmp_path / "style_gap",
    )
    tree = read_json(tmp_path / "style_gap/artifacts/generated_template_tree.json")
    report = read_json(tmp_path / "style_gap/artifacts/template_gap_report.json")

    assert result.status == Status.FAIL
    paragraph = next(
        item
        for item in tree["data"]["paragraphs"]
        if item["text"].startswith("湖 南 农 业 大 学")
    )
    assert paragraph["style_details"]["dominant_run"]["font_names"] == ["华文行楷"]
    assert paragraph["style_details"]["dominant_run"]["font_size_pt"] == 26.0
    assert paragraph["style_details"]["paragraph"]["alignment"] == "center"

    style_mismatches = [
        item
        for item in report["check_items"]
        if item["type"] == "template_generation_style_mismatch"
    ]
    assert style_mismatches
    assert any("font_size=" in item["actual"] for item in style_mismatches)


def test_generated_template_gap_missing_docx_is_unknown(tmp_path) -> None:
    result = run_template_gap_eval(
        ROOT,
        "hunannongye",
        tmp_path / "missing_generated_template.docx",
        tmp_path / "missing_gap",
    )
    report = read_json(tmp_path / "missing_gap/artifacts/template_gap_report.json")

    assert result.status == Status.UNKNOWN
    assert report["summary"]["blocking_status"] == Status.UNKNOWN.value
    assert report["summary"]["display_status"] == Status.UNKNOWN.value
    assert any(
        item["type"] == "template_generation_output_missing"
        for item in report["check_items"]
    )


def test_template_gap_status_combination_rules() -> None:
    assert summarize_check_items([{"status": "PASS"}]) == {
        "known_status": "PASS",
        "display_status": "PASS",
        "passed_count": 1,
        "failed_count": 0,
        "unknown_count": 0,
        "blocking_status": "PASS",
    }
    assert summarize_check_items([{"status": "PASS"}, {"status": "UNKNOWN"}])[
        "display_status"
    ] == "PASS + UNKNOWN"
    assert summarize_check_items([{"status": "FAIL"}])["blocking_status"] == "FAIL"
    assert summarize_check_items([{"status": "FAIL"}, {"status": "UNKNOWN"}])[
        "display_status"
    ] == "FAIL + UNKNOWN"
    assert summarize_check_items([{"status": "UNKNOWN"}]) == {
        "known_status": "UNKNOWN",
        "display_status": "UNKNOWN",
        "passed_count": 0,
        "failed_count": 0,
        "unknown_count": 1,
        "blocking_status": "UNKNOWN",
    }
