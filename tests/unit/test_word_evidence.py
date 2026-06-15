from __future__ import annotations

from docfit.core.io import read_json, sha256_file
from docfit.core.models import make_finding
from docfit.core.status import Status
from docfit.harness.reports import write_report_bundle
from docfit.harness.word_evidence import (
    build_word_image_evidence_manifest,
    reconcile_word_image_evidence_report,
    verify_word_image_evidence,
)


def _write_bytes(path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def test_word_image_evidence_manifest_passes_when_complete(tmp_path) -> None:
    final_docx = tmp_path / "final.docx"
    page_1 = tmp_path / "page-1.png"
    page_2 = tmp_path / "page-2.png"
    _write_bytes(final_docx, b"docx")
    _write_bytes(page_1, b"page1")
    _write_bytes(page_2, b"page2")

    manifest = build_word_image_evidence_manifest(
        case_id="case-001",
        school_id="school",
        student_id="student",
        final_docx=final_docx,
        image_paths=[page_1, page_2],
        word_application="Microsoft Word",
        word_version="16.test",
        platform="macOS",
        export_method="pdf-page-images",
    )

    assert verify_word_image_evidence(manifest, expected_final_docx=final_docx) == []


def test_word_image_export_unavailable_is_unknown(tmp_path) -> None:
    final_docx = tmp_path / "final.docx"
    _write_bytes(final_docx, b"docx")

    manifest = {
        "case_id": "case-001",
        "school_id": "school",
        "student_id": "student",
        "final_docx": str(final_docx),
        "final_docx_sha256": "sha256:placeholder",
        "word_application": "Microsoft Word",
        "word_version": "unknown",
        "platform": "macOS",
        "export_method": "pdf-page-images",
        "page_count": 0,
        "exported_image_count": 0,
        "images": [],
        "export_status": "blocked",
        "open_repair_warnings": [],
    }

    findings = verify_word_image_evidence(manifest, expected_final_docx=final_docx)

    assert any(finding.status == Status.UNKNOWN for finding in findings)
    assert any(finding.type == "word_image_export_unavailable" for finding in findings)


def test_word_image_final_docx_path_is_required_without_expected_path(tmp_path) -> None:
    final_docx = tmp_path / "missing-final.docx"
    page_1 = tmp_path / "page-1.png"
    _write_bytes(page_1, b"page1")

    manifest = {
        "case_id": "case-001",
        "school_id": "school",
        "student_id": "student",
        "final_docx": str(final_docx),
        "final_docx_sha256": "sha256:placeholder",
        "word_application": "Microsoft Word",
        "word_version": "16.test",
        "platform": "macOS",
        "export_method": "pdf-page-images",
        "page_count": 1,
        "exported_image_count": 1,
        "images": [{"page": 1, "path": str(page_1), "sha256": sha256_file(page_1)}],
        "export_status": "exported",
        "open_repair_warnings": [],
    }

    findings = verify_word_image_evidence(manifest)

    assert any(finding.status == Status.UNKNOWN for finding in findings)
    assert any(finding.type == "word_image_final_docx_missing" for finding in findings)


def test_word_image_count_mismatch_fails(tmp_path) -> None:
    final_docx = tmp_path / "final.docx"
    page_1 = tmp_path / "page-1.png"
    _write_bytes(final_docx, b"docx")
    _write_bytes(page_1, b"page1")

    manifest = build_word_image_evidence_manifest(
        case_id="case-001",
        school_id="school",
        student_id="student",
        final_docx=final_docx,
        image_paths=[page_1],
        word_application="Microsoft Word",
        word_version="16.test",
        platform="macOS",
        export_method="pdf-page-images",
    )
    manifest["page_count"] = 2

    findings = verify_word_image_evidence(manifest, expected_final_docx=final_docx)

    assert any(finding.status == Status.FAIL for finding in findings)
    assert any(finding.type == "word_image_count_mismatch" for finding in findings)


def test_word_image_final_docx_hash_mismatch_fails(tmp_path) -> None:
    final_docx = tmp_path / "final.docx"
    page_1 = tmp_path / "page-1.png"
    _write_bytes(final_docx, b"docx")
    _write_bytes(page_1, b"page1")

    manifest = build_word_image_evidence_manifest(
        case_id="case-001",
        school_id="school",
        student_id="student",
        final_docx=final_docx,
        image_paths=[page_1],
        word_application="Microsoft Word",
        word_version="16.test",
        platform="macOS",
        export_method="pdf-page-images",
    )
    manifest["final_docx_sha256"] = "sha256:wrong"

    findings = verify_word_image_evidence(manifest, expected_final_docx=final_docx)

    assert any(finding.status == Status.FAIL for finding in findings)
    assert any(finding.type == "word_image_final_docx_hash_mismatch" for finding in findings)


def test_word_image_evidence_reconciles_stale_case_report(tmp_path) -> None:
    case_dir = tmp_path / "case-001"
    evidence_dir = case_dir / "evidence"
    final_docx = case_dir / "final.docx"
    page_1 = evidence_dir / "page-1.png"
    manifest_path = evidence_dir / "word_image_evidence.json"
    _write_bytes(final_docx, b"docx")
    _write_bytes(page_1, b"page1")
    stale_finding = make_finding(
        1,
        "render",
        Status.UNKNOWN,
        "coverage_insufficient",
        "render coverage is insufficient for the active contract",
        "all required capabilities covered",
        "render.word_image_evidence=False",
        affected_ids=["render.word_image_evidence"],
        root_cause_bucket="coverage_gap",
    ).to_dict()
    write_report_bundle(
        case_dir,
        stage="e2e",
        status=Status.UNKNOWN,
        findings=[stale_finding],
        artifacts={"final_docx": str(final_docx)},
        coverage={"render.word_image_evidence": False},
        stage_statuses={
            "template": "PASS",
            "content": "PASS",
            "placement": "PASS",
            "render": "UNKNOWN",
        },
        stage_run_states={
            "template": "ran",
            "content": "ran",
            "placement": "ran",
            "render": "ran",
        },
        blocked_at="render",
    )
    manifest = build_word_image_evidence_manifest(
        case_id="case-001",
        school_id="school",
        student_id="student",
        final_docx=final_docx,
        image_paths=[page_1],
        word_application="Microsoft Word",
        word_version="16.test",
        platform="macOS",
        export_method="test fixture",
    )

    evidence_findings = reconcile_word_image_evidence_report(
        case_dir,
        manifest,
        expected_final_docx=final_docx,
        manifest_path=manifest_path,
    )

    assert evidence_findings == []
    assert read_json(case_dir / "findings.json") == []
    summary = read_json(case_dir / "summary.json")
    assert summary["status"] == Status.PASS.value
    assert summary["blocked_at"] is None
    assert summary["stage_statuses"]["render"] == Status.PASS.value
    assert summary["coverage"]["render.word_image_evidence"] is True
    assert (
        summary["artifacts"]["word_image_evidence"]
        == "evidence/word_image_evidence.json"
    )
