from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.models import Finding, make_finding
from docfit.core.status import Status


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


def evaluate_bootstrap_coverage(root: Path) -> tuple[dict[str, Any], list[Finding]]:
    fixture_checks = {
        "template.docx_openable": root / "fixtures/bootstrap/schools/demo-school/template.docx",
        "content.visible_paragraphs": root / "fixtures/bootstrap/students/demo-thesis.docx",
        "content.visible_tables": root / "fixtures/bootstrap/students/demo-thesis.docx",
        "placement.no_silent_drop": root / "fixtures/bootstrap/expected/placement_plan.json",
        "render.feature_snapshot": root / "fixtures/bootstrap/expected/feature_snapshot.json",
    }
    missing = [
        capability
        for capability, path in fixture_checks.items()
        if not path.exists()
    ]
    required_flat = [item for items in BOOTSTRAP_REQUIRED.values() for item in items]
    covered = sorted(set(required_flat) - set(missing))
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
                "bootstrap-core fixture coverage is incomplete",
                "all required bootstrap capabilities have fixtures",
                ", ".join(missing),
                root_cause_bucket="coverage_gap",
            )
        )
    return report, findings
