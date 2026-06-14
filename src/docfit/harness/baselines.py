from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from docfit.core.models import Finding, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.harness.comparators import (
    ALLOWED_COMPARATOR_MODES,
    NUMERIC_TOLERANCE_FIELDS,
    compare_dimensions,
)

REQUIRED_REVIEW_METADATA_FIELDS = {
    "reviewed_by",
    "review_source",
    "source_docx_sha256",
    "change_reason",
    "auto_update_allowed",
}


@dataclass(frozen=True)
class BaselineComparisonResult:
    stage: str
    status: Status
    findings: list[Finding]


def load_baseline_file(
    path: Path,
    *,
    stage: str = "standards",
    start_index: int = 1,
) -> tuple[dict[str, Any] | None, list[Finding]]:
    if not path.exists():
        return None, [
            make_finding(
                start_index,
                stage,
                Status.UNKNOWN,
                "missing_profile_baseline",
                "Profile baseline is missing and cannot be treated as signed evidence",
                str(path),
                "missing",
                evidence_refs=[str(path)],
                root_cause_bucket="baseline_missing",
            )
        ]

    try:
        if path.suffix == ".json":
            baseline = json.loads(path.read_text(encoding="utf-8"))
        else:
            baseline = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive branch
        return None, [
            make_finding(
                start_index,
                stage,
                Status.UNKNOWN,
                "invalid_baseline_file",
                "Baseline file must be parseable YAML or JSON",
                "valid baseline document",
                repr(exc),
                evidence_refs=[str(path)],
                root_cause_bucket="baseline_invalid",
            )
        ]

    if not isinstance(baseline, dict):
        return None, [
            make_finding(
                start_index,
                stage,
                Status.UNKNOWN,
                "invalid_baseline_file",
                "Baseline root must be an object",
                "mapping/object",
                type(baseline).__name__,
                evidence_refs=[str(path)],
                root_cause_bucket="baseline_invalid",
            )
        ]
    return baseline, validate_baseline_document(
        baseline,
        stage=stage,
        start_index=start_index,
        baseline_ref=str(path),
    )


def validate_baseline_document(
    baseline: dict[str, Any],
    *,
    stage: str,
    start_index: int = 1,
    baseline_ref: str | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index

    metadata = baseline.get("review_metadata")
    if not isinstance(metadata, dict):
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "missing_review_metadata",
                "Signed baselines require review metadata",
                ", ".join(sorted(REQUIRED_REVIEW_METADATA_FIELDS)),
                "missing",
                evidence_refs=_refs(baseline_ref),
                root_cause_bucket="baseline_review_gap",
            )
        )
        next_index += 1
        metadata = {}

    missing_metadata = sorted(REQUIRED_REVIEW_METADATA_FIELDS - set(metadata))
    if missing_metadata:
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "missing_review_metadata_field",
                "Baseline review metadata is incomplete",
                ", ".join(sorted(REQUIRED_REVIEW_METADATA_FIELDS)),
                ", ".join(missing_metadata),
                evidence_refs=_refs(baseline_ref),
                root_cause_bucket="baseline_review_gap",
            )
        )
        next_index += 1

    if metadata.get("auto_update_allowed") is not False:
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "baseline_auto_update_not_allowed",
                "Baselines must explicitly forbid auto-update from current outputs",
                "auto_update_allowed: false",
                repr(metadata.get("auto_update_allowed")),
                evidence_refs=_refs(baseline_ref),
                root_cause_bucket="baseline_review_gap",
            )
        )
        next_index += 1

    source_hash = metadata.get("source_docx_sha256")
    if source_hash is not None and not str(source_hash).startswith("sha256:"):
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "invalid_source_hash",
                "Baseline source hash must bind to a sha256 digest",
                "sha256:<hex>",
                str(source_hash),
                evidence_refs=_refs(baseline_ref),
                root_cause_bucket="baseline_review_gap",
            )
        )
        next_index += 1

    dimensions = list(_iter_dimensions(baseline))
    if not dimensions:
        findings.append(
            make_finding(
                next_index,
                stage,
                Status.UNKNOWN,
                "missing_baseline_dimensions",
                "Signed baselines must declare executable dimensions",
                "one or more dimensions",
                "none",
                evidence_refs=_refs(baseline_ref),
                root_cause_bucket="baseline_schema_gap",
            )
        )
        next_index += 1

    for dimension in dimensions:
        if dimension.get("required", True) is False:
            continue
        dimension_id = str(dimension.get("dimension_id") or dimension.get("id") or "unknown")
        comparator_mode = dimension.get("comparator_mode")
        if not comparator_mode:
            findings.append(
                make_finding(
                    next_index,
                    stage,
                    Status.UNKNOWN,
                    "missing_comparator_mode",
                    f"Required dimension {dimension_id} does not declare comparator_mode",
                    "required dimension has comparator_mode",
                    "missing",
                    evidence_refs=_refs(baseline_ref),
                    affected_ids=[dimension_id],
                    root_cause_bucket="comparator_gap",
                )
            )
            next_index += 1
            continue
        if comparator_mode not in ALLOWED_COMPARATOR_MODES:
            findings.append(
                make_finding(
                    next_index,
                    stage,
                    Status.UNKNOWN,
                    "unsupported_comparator_mode",
                    f"Required dimension {dimension_id} uses an unsupported comparator_mode",
                    ", ".join(sorted(ALLOWED_COMPARATOR_MODES)),
                    str(comparator_mode),
                    evidence_refs=_refs(baseline_ref),
                    affected_ids=[dimension_id],
                    root_cause_bucket="comparator_gap",
                )
            )
            next_index += 1
            continue
        if comparator_mode == "numeric_tolerance" and not (
            NUMERIC_TOLERANCE_FIELDS & set(dimension)
        ):
            findings.append(
                make_finding(
                    next_index,
                    stage,
                    Status.UNKNOWN,
                    "missing_numeric_tolerance",
                    f"Numeric dimension {dimension_id} must declare an explicit tolerance",
                    "tolerance, tolerance_abs, or tolerance_percent",
                    "missing",
                    evidence_refs=_refs(baseline_ref),
                    affected_ids=[dimension_id],
                    root_cause_bucket="comparator_gap",
                )
            )
            next_index += 1

    return findings


def compare_baseline_to_artifact(
    baseline: dict[str, Any],
    actual_artifact: dict[str, Any],
    *,
    stage: str,
    start_index: int = 1,
    baseline_ref: str | None = None,
    expected_key: str = "expected",
) -> BaselineComparisonResult:
    findings = validate_baseline_document(
        baseline,
        stage=stage,
        start_index=start_index,
        baseline_ref=baseline_ref,
    )
    next_index = start_index + len(findings)
    if not findings:
        expected_artifact = baseline.get(expected_key)
        if not isinstance(expected_artifact, dict):
            findings.append(
                make_finding(
                    next_index,
                    stage,
                    Status.UNKNOWN,
                    "missing_expected_artifact",
                    "Baseline comparison requires expected artifact data",
                    f"{expected_key}: <mapping>",
                    repr(expected_artifact),
                    evidence_refs=_refs(baseline_ref),
                    root_cause_bucket="baseline_schema_gap",
                )
            )
        else:
            findings.extend(
                compare_dimensions(
                    expected_artifact,
                    actual_artifact,
                    _iter_dimensions(baseline),
                    stage=stage,
                    start_index=next_index,
                )
            )
    status = (
        merge_statuses([finding.status for finding in findings])
        if findings
        else Status.PASS
    )
    return BaselineComparisonResult(stage=stage, status=status, findings=findings)


def _iter_dimensions(baseline: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for key in ("dimensions", "required_dimensions"):
        dimensions = baseline.get(key, [])
        if isinstance(dimensions, list):
            for dimension in dimensions:
                if isinstance(dimension, dict):
                    yield dimension
                    yield from _iter_child_dimensions(dimension)


def _iter_child_dimensions(dimension: dict[str, Any]) -> Iterable[dict[str, Any]]:
    children = dimension.get("dimensions") or dimension.get("children") or []
    if not isinstance(children, list):
        return
    for child in children:
        if isinstance(child, dict):
            yield child
            yield from _iter_child_dimensions(child)


def _refs(ref: str | None) -> list[str]:
    return [ref] if ref else []
