from __future__ import annotations

from docfit.core.status import Status
from docfit.harness.word_evidence import (
    build_word_image_evidence_manifest,
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
