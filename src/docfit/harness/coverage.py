from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document

from docfit.core.io import read_json
from docfit.core.models import Finding, make_finding
from docfit.core.status import Status
from docfit.ooxml.package import is_valid_docx, read_document_xml


BOOTSTRAP_REQUIRED = {
    "template": [
        "template.docx_openable",
        "template.required_regions",
        "template.required_slots",
        "template.styles_inventory",
    ],
    "content": [
        "content.visible_paragraphs",
        "content.visible_tables",
        "content.reading_order",
        "content.stable_ids",
    ],
    "placement": [
        "placement.no_silent_drop",
        "placement.slot_compatibility",
        "placement.required_slots",
    ],
    "render": [
        "render.valid_docx_package",
        "render.plan_coverage",
        "render.feature_snapshot",
        "render.content_hash_coverage",
    ],
}


def bootstrap_required_capabilities() -> list[str]:
    return [capability for items in BOOTSTRAP_REQUIRED.values() for capability in items]


def validate_standard_coverage_requirements(
    profile: str | None,
    required_capabilities: list[str],
    *,
    stage: str = "standards",
    start_index: int = 1,
) -> list[Finding]:
    if profile != "bootstrap-core":
        return [
            make_finding(
                start_index,
                stage,
                Status.UNKNOWN,
                "unknown_coverage_profile",
                "Signed standard references an unknown coverage profile",
                "bootstrap-core",
                profile or "missing",
                root_cause_bucket="coverage_gap",
            )
        ]

    expected = set(bootstrap_required_capabilities())
    actual = set(required_capabilities)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if not missing and not unknown:
        return []

    details = []
    if missing:
        details.append("missing: " + ", ".join(missing))
    if unknown:
        details.append("unknown: " + ", ".join(unknown))
    return [
        make_finding(
            start_index,
            stage,
            Status.UNKNOWN,
            "coverage_requirements_drift",
            "Signed standard coverage requirements do not match the bootstrap-core capability profile",
            ", ".join(sorted(expected)),
            "; ".join(details),
            root_cause_bucket="coverage_gap",
        )
    ]


def coverage_gate_findings(
    stage: str,
    coverage: dict[str, Any],
    required_capabilities: list[str],
    *,
    start_index: int = 1,
) -> list[Finding]:
    missing = [
        capability
        for capability in required_capabilities
        if coverage.get(capability) is not True
    ]
    if not missing:
        return []
    actual = [
        f"{capability}={coverage.get(capability, 'missing')}"
        for capability in missing
    ]
    return [
        make_finding(
            start_index,
            stage,
            Status.UNKNOWN,
            "coverage_insufficient",
            f"{stage} coverage is insufficient for the active contract",
            "all required capabilities covered",
            ", ".join(actual),
            affected_ids=missing,
            root_cause_bucket="coverage_gap",
        )
    ]


def _safe_document(path: Path):
    if not path.exists() or not is_valid_docx(path):
        return None
    try:
        return Document(path)
    except Exception:
        return None


def _has_slot_marker(path: Path) -> bool:
    if not path.exists() or not is_valid_docx(path):
        return False
    try:
        return "[[DOCFIT_SLOT:body]]" in read_document_xml(path)
    except Exception:
        return False


def _has_required_content_hashes(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(read_json(path).get("required_content_hashes"))
    except Exception:
        return False


def evaluate_bootstrap_coverage(root: Path) -> tuple[dict[str, Any], list[Finding]]:
    template_docx = root / "inputs/bootstrap-demo-school-template.docx"
    student_docx = root / "inputs/bootstrap-demo-student-pass.docx"
    expected_placement = root / "inputs/bootstrap-demo-placement-plan.json"
    expected_snapshot = root / "inputs/bootstrap-demo-feature-snapshot.json"
    template_doc = _safe_document(template_docx)
    student_doc = _safe_document(student_docx)
    has_visible_content = bool(
        student_doc
        and (
            any(paragraph.text.strip() for paragraph in student_doc.paragraphs)
            or student_doc.tables
        )
    )
    capability_checks = {
        "template.docx_openable": is_valid_docx(template_docx),
        "template.required_regions": _has_slot_marker(template_docx),
        "template.required_slots": _has_slot_marker(template_docx),
        "template.styles_inventory": bool(template_doc and list(template_doc.styles)),
        "content.visible_paragraphs": bool(
            student_doc
            and any(paragraph.text.strip() for paragraph in student_doc.paragraphs)
        ),
        "content.visible_tables": bool(student_doc and student_doc.tables),
        "content.reading_order": has_visible_content,
        "content.stable_ids": has_visible_content,
        "placement.no_silent_drop": expected_placement.exists(),
        "placement.slot_compatibility": expected_placement.exists(),
        "placement.required_slots": _has_slot_marker(template_docx),
        "render.valid_docx_package": is_valid_docx(template_docx) and is_valid_docx(student_docx),
        "render.plan_coverage": expected_placement.exists(),
        "render.feature_snapshot": expected_snapshot.exists(),
        "render.content_hash_coverage": _has_required_content_hashes(expected_snapshot),
    }
    missing = [
        capability
        for capability, is_covered in capability_checks.items()
        if not is_covered
    ]
    required_flat = [item for items in BOOTSTRAP_REQUIRED.values() for item in items]
    covered = sorted(
        capability
        for capability in required_flat
        if capability_checks.get(capability) is True
    )
    status = Status.UNKNOWN if missing else Status.PASS
    report = {
        "profile": "bootstrap-core",
        "status": status.value,
        "required": len(required_flat),
        "covered": len(covered),
        "missing": missing,
    }
    findings: list[Finding] = []
    if missing:
        findings.append(
            make_finding(
                1,
                "coverage",
                Status.UNKNOWN,
                "coverage_insufficient",
                "bootstrap-core input asset coverage is incomplete",
                "all required bootstrap capabilities have input assets",
                ", ".join(missing),
                root_cause_bucket="coverage_gap",
            )
        )
    return report, findings
