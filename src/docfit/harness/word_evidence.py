from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import read_json, sha256_file
from docfit.core.models import Finding, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.harness.reports import write_report_bundle


WORD_IMAGE_COVERAGE_CAPABILITY = "render.word_image_evidence"

REQUIRED_WORD_EVIDENCE_FIELDS = {
    "case_id",
    "school_id",
    "student_id",
    "final_docx",
    "final_docx_sha256",
    "word_application",
    "word_version",
    "platform",
    "export_method",
    "page_count",
    "exported_image_count",
    "images",
    "export_status",
    "open_repair_warnings",
}


def build_word_image_evidence_manifest(
    *,
    case_id: str,
    school_id: str,
    student_id: str,
    final_docx: Path,
    image_paths: list[Path],
    word_application: str,
    word_version: str,
    platform: str,
    export_method: str,
    export_status: str = "exported",
    open_repair_warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "word_image_evidence",
        "artifact_version": "1.0",
        "case_id": case_id,
        "school_id": school_id,
        "student_id": student_id,
        "final_docx": str(final_docx),
        "final_docx_sha256": sha256_file(final_docx),
        "word_application": word_application,
        "word_version": word_version,
        "platform": platform,
        "export_method": export_method,
        "page_count": len(image_paths),
        "exported_image_count": len(image_paths),
        "images": [
            {
                "page": index,
                "path": str(path),
                "sha256": sha256_file(path),
            }
            for index, path in enumerate(image_paths, start=1)
        ],
        "export_status": export_status,
        "open_repair_warnings": open_repair_warnings or [],
    }


def verify_word_image_evidence(
    manifest: dict[str, Any],
    *,
    expected_final_docx: Path | None = None,
    stage: str = "render",
    start_index: int = 1,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index

    missing = sorted(REQUIRED_WORD_EVIDENCE_FIELDS - set(manifest))
    if missing:
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "word_image_evidence_incomplete",
                "Word image evidence manifest is missing required fields",
                ", ".join(sorted(REQUIRED_WORD_EVIDENCE_FIELDS)),
                ", ".join(missing),
                root_cause_bucket="oracle_gap",
            )
        )
        next_index += 1

    if manifest.get("export_status") != "exported":
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "word_image_export_unavailable",
                "Word image evidence could not be produced by the configured exporter",
                "export_status: exported",
                str(manifest.get("export_status", "missing")),
                root_cause_bucket="oracle_gap",
            )
        )
        next_index += 1

    page_count = manifest.get("page_count")
    exported_count = manifest.get("exported_image_count")
    images = manifest.get("images")
    if not isinstance(page_count, int) or page_count < 1:
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "word_image_page_count_unknown",
                "Word image evidence must include a positive page count",
                "page_count >= 1",
                repr(page_count),
                root_cause_bucket="oracle_gap",
            )
        )
        next_index += 1
    if not isinstance(exported_count, int) or exported_count < 1:
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "word_image_export_count_unknown",
                "Word image evidence must include a positive exported image count",
                "exported_image_count >= 1",
                repr(exported_count),
                root_cause_bucket="oracle_gap",
            )
        )
        next_index += 1
    if isinstance(page_count, int) and isinstance(exported_count, int) and page_count != exported_count:
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.FAIL,
                "word_image_count_mismatch",
                "Word image evidence must contain one exported image per page",
                str(page_count),
                str(exported_count),
                root_cause_bucket="oracle_gap",
            )
        )
        next_index += 1
    if not isinstance(images, list):
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "word_image_list_unknown",
                "Word image evidence must list exported page images",
                "images: <list>",
                type(images).__name__,
                root_cause_bucket="oracle_gap",
            )
        )
        next_index += 1
    elif isinstance(exported_count, int) and len(images) != exported_count:
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.FAIL,
                "word_image_manifest_count_mismatch",
                "Word image manifest count must match exported_image_count",
                str(exported_count),
                str(len(images)),
                root_cause_bucket="oracle_gap",
            )
        )
        next_index += 1

    for image in images if isinstance(images, list) else []:
        image_findings = _verify_image_entry(image, next_index, stage)
        findings.extend(image_findings)
        next_index += len(image_findings)

    expected_hash = manifest.get("final_docx_sha256")
    manifest_final_docx = _manifest_final_docx(manifest)
    final_docx_to_check = expected_final_docx or manifest_final_docx
    if final_docx_to_check is None:
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "word_image_final_docx_missing",
                "Word image evidence must bind to the rendered DOCX",
                "final_docx path",
                "missing",
                root_cause_bucket="oracle_gap",
            )
        )
        next_index += 1
    elif not final_docx_to_check.exists():
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "word_image_final_docx_missing",
                "Word image evidence must bind to the rendered DOCX",
                str(final_docx_to_check),
                "missing",
                root_cause_bucket="oracle_gap",
            )
        )
        next_index += 1
    elif expected_hash != sha256_file(final_docx_to_check):
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.FAIL,
                "word_image_final_docx_hash_mismatch",
                "Word image evidence final DOCX hash must match the rendered output",
                sha256_file(final_docx_to_check),
                str(expected_hash),
                root_cause_bucket="oracle_gap",
            )
        )
        next_index += 1

    warnings = manifest.get("open_repair_warnings", [])
    if warnings:
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "word_image_open_repair_warning",
                "Word opened or exported the DOCX with repair warnings",
                "no open/repair warnings",
                repr(warnings),
                root_cause_bucket="oracle_gap",
            )
        )
    return findings


def reconcile_word_image_evidence_report(
    case_dir: Path,
    manifest: dict[str, Any],
    *,
    expected_final_docx: Path,
    manifest_path: Path | None = None,
) -> list[Finding]:
    """Refresh a case report after Word page-image evidence has been produced."""

    summary_path = case_dir / "summary.json"
    findings_path = case_dir / "findings.json"
    summary: dict[str, Any] = {}
    existing_findings: list[dict[str, Any]] = []
    if summary_path.exists():
        summary = read_json(summary_path)
    if findings_path.exists():
        existing_findings = read_json(findings_path)

    retained_findings = [
        finding
        for finding in existing_findings
        if not _is_stale_word_image_coverage_finding(finding)
    ]
    evidence_findings = verify_word_image_evidence(
        manifest,
        expected_final_docx=expected_final_docx,
        stage="render",
        start_index=len(retained_findings) + 1,
    )
    for finding in evidence_findings:
        if WORD_IMAGE_COVERAGE_CAPABILITY not in finding.affected_ids:
            finding.affected_ids.append(WORD_IMAGE_COVERAGE_CAPABILITY)

    combined_findings = retained_findings + [
        finding.to_dict() for finding in evidence_findings
    ]
    coverage = dict(summary.get("coverage") or {})
    coverage[WORD_IMAGE_COVERAGE_CAPABILITY] = not evidence_findings
    artifacts = dict(summary.get("artifacts") or {})
    if manifest_path is not None:
        artifacts["word_image_evidence"] = _artifact_ref(case_dir, manifest_path)

    stage_statuses = dict(
        summary.get("stage_statuses") or {"render": Status.UNKNOWN.value}
    )
    if evidence_findings:
        stage_statuses["render"] = merge_statuses(
            [finding.status for finding in evidence_findings]
        ).value
    elif not any(
        finding.get("stage") == "render" and finding.get("severity") == "blocking"
        for finding in retained_findings
    ):
        stage_statuses["render"] = Status.PASS.value

    status = _status_from_report_state(stage_statuses, combined_findings)
    blocked_at = _blocked_at(combined_findings)
    write_report_bundle(
        case_dir,
        stage=str(summary.get("stage") or "e2e"),
        status=status,
        findings=combined_findings,
        artifacts=artifacts,
        coverage=coverage,
        stage_statuses=stage_statuses,
        stage_run_states=summary.get("stage_run_states"),
        blocked_at=blocked_at,
        user_message=summary.get("user_message"),
    )
    return evidence_findings


def _is_stale_word_image_coverage_finding(finding: dict[str, Any]) -> bool:
    return (
        finding.get("type") == "coverage_insufficient"
        and WORD_IMAGE_COVERAGE_CAPABILITY in finding.get("affected_ids", [])
    )


def _artifact_ref(case_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(case_dir))
    except ValueError:
        return str(path)


def _status_from_report_state(
    stage_statuses: dict[str, str],
    findings: list[dict[str, Any]],
) -> Status:
    stage_status = merge_statuses(
        [Status(status) for status in stage_statuses.values()]
    )
    blocking_statuses = [
        Status(finding["status"])
        for finding in findings
        if finding.get("severity") == "blocking"
    ]
    if not blocking_statuses:
        return stage_status
    return merge_statuses([stage_status, *blocking_statuses])


def _blocked_at(findings: list[dict[str, Any]]) -> str | None:
    for finding in findings:
        if finding.get("severity") == "blocking":
            return str(finding.get("stage") or "unknown")
    return None


def _manifest_final_docx(manifest: dict[str, Any]) -> Path | None:
    final_docx = manifest.get("final_docx")
    if not isinstance(final_docx, str) or not final_docx.strip():
        return None
    return Path(final_docx)


def _verify_image_entry(image: Any, index: int, stage: str) -> list[Finding]:
    if not isinstance(image, dict):
        return [
            make_finding(
                index,
                stage,
                Status.UNKNOWN,
                "word_image_entry_invalid",
                "Each Word image evidence entry must be an object",
                "image entry mapping",
                type(image).__name__,
                root_cause_bucket="oracle_gap",
            )
        ]

    path = Path(str(image.get("path", "")))
    image_hash = image.get("sha256")
    if not path.exists():
        return [
            make_finding(
                index,
                stage,
                Status.UNKNOWN,
                "word_image_file_missing",
                "Exported Word page image is missing",
                str(path),
                "missing",
                root_cause_bucket="oracle_gap",
            )
        ]
    if not image_hash:
        return [
            make_finding(
                index,
                stage,
                Status.UNKNOWN,
                "word_image_hash_missing",
                "Exported Word page image must include a sha256 hash",
                "sha256:<hex>",
                "missing",
                root_cause_bucket="oracle_gap",
            )
        ]
    actual_hash = sha256_file(path)
    if image_hash != actual_hash:
        return [
            make_finding(
                index,
                stage,
                Status.FAIL,
                "word_image_hash_mismatch",
                "Exported Word page image hash does not match the manifest",
                actual_hash,
                str(image_hash),
                root_cause_bucket="oracle_gap",
            )
        ]
    return []
