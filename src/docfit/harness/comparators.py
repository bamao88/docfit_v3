from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from docfit.core.models import Finding, make_finding
from docfit.core.status import Status


ALLOWED_COMPARATOR_MODES = {
    "exact",
    "normalized_text",
    "ordered_sequence",
    "set",
    "set_equality",
    "subset",
    "numeric_tolerance",
    "style_profile",
    "relationship",
    "oracle_required",
}

NUMERIC_TOLERANCE_FIELDS = {"tolerance", "tolerance_abs", "tolerance_percent"}
MISSING = object()


def compare_dimensions(
    expected: dict[str, Any],
    actual: dict[str, Any],
    dimensions: Iterable[dict[str, Any]],
    *,
    stage: str,
    start_index: int = 1,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    for dimension in dimensions:
        finding = compare_dimension(
            expected,
            actual,
            dimension,
            stage=stage,
            index=next_index,
        )
        if finding is not None:
            findings.append(finding)
            next_index += 1
    return findings


def compare_dimension(
    expected: dict[str, Any],
    actual: dict[str, Any],
    dimension: dict[str, Any],
    *,
    stage: str,
    index: int,
) -> Finding | None:
    if dimension.get("required", True) is False:
        return None

    dimension_id = str(dimension.get("dimension_id") or dimension.get("id") or "unknown")
    mode = dimension.get("comparator_mode")
    if mode not in ALLOWED_COMPARATOR_MODES:
        return _unknown(
            index,
            stage,
            dimension_id,
            "unsupported_comparator_mode",
            "Required dimension uses an unsupported comparator mode",
            ", ".join(sorted(ALLOWED_COMPARATOR_MODES)),
            str(mode or "missing"),
        )

    expected_value = _resolve_value(expected, dimension.get("expected_path"))
    actual_value = _resolve_value(actual, dimension.get("actual_path"))
    if expected_value is MISSING or actual_value is MISSING:
        return _unknown(
            index,
            stage,
            dimension_id,
            "dimension_unreadable",
            "Required dimension could not be read from expected or actual artifact",
            _display(expected_value),
            _display(actual_value),
        )

    if mode == "exact":
        return _fail_if(
            expected_value != actual_value,
            index,
            stage,
            dimension_id,
            "exact_mismatch",
            expected_value,
            actual_value,
        )
    if mode == "normalized_text":
        return _fail_if(
            _normalize_text(expected_value) != _normalize_text(actual_value),
            index,
            stage,
            dimension_id,
            "normalized_text_mismatch",
            expected_value,
            actual_value,
        )
    if mode == "ordered_sequence":
        return _fail_if(
            list(expected_value) != list(actual_value),
            index,
            stage,
            dimension_id,
            "ordered_sequence_mismatch",
            expected_value,
            actual_value,
        )
    if mode in {"set", "set_equality"}:
        return _fail_if(
            set(expected_value) != set(actual_value),
            index,
            stage,
            dimension_id,
            "set_mismatch",
            expected_value,
            actual_value,
        )
    if mode == "subset":
        return _fail_if(
            not set(expected_value).issubset(set(actual_value)),
            index,
            stage,
            dimension_id,
            "subset_missing",
            expected_value,
            actual_value,
        )
    if mode == "numeric_tolerance":
        return _compare_numeric_tolerance(
            expected_value,
            actual_value,
            dimension,
            index=index,
            stage=stage,
            dimension_id=dimension_id,
        )
    if mode == "style_profile":
        return _compare_style_profile(
            expected_value,
            actual_value,
            index=index,
            stage=stage,
            dimension_id=dimension_id,
        )
    if mode == "relationship":
        return _fail_if(
            expected_value != actual_value,
            index,
            stage,
            dimension_id,
            "relationship_mismatch",
            expected_value,
            actual_value,
        )
    if mode == "oracle_required":
        return _compare_oracle_required(
            actual_value,
            index=index,
            stage=stage,
            dimension_id=dimension_id,
        )
    return None


def _compare_numeric_tolerance(
    expected_value: Any,
    actual_value: Any,
    dimension: dict[str, Any],
    *,
    index: int,
    stage: str,
    dimension_id: str,
) -> Finding | None:
    tolerance = _numeric_tolerance(dimension, expected_value)
    if tolerance is None:
        return _unknown(
            index,
            stage,
            dimension_id,
            "missing_numeric_tolerance",
            "Numeric dimension must declare an explicit tolerance",
            "tolerance, tolerance_abs, or tolerance_percent",
            "missing",
        )
    try:
        expected_number = float(expected_value)
        actual_number = float(actual_value)
    except (TypeError, ValueError):
        return _unknown(
            index,
            stage,
            dimension_id,
            "numeric_dimension_unreadable",
            "Numeric dimension values must be numeric",
            repr(expected_value),
            repr(actual_value),
        )
    return _fail_if(
        abs(expected_number - actual_number) > tolerance,
        index,
        stage,
        dimension_id,
        "numeric_tolerance_mismatch",
        expected_value,
        actual_value,
    )


def _compare_style_profile(
    expected_value: Any,
    actual_value: Any,
    *,
    index: int,
    stage: str,
    dimension_id: str,
) -> Finding | None:
    if not isinstance(expected_value, dict) or not isinstance(actual_value, dict):
        return _unknown(
            index,
            stage,
            dimension_id,
            "style_profile_unreadable",
            "Style profile dimensions must compare mapping values",
            type(expected_value).__name__,
            type(actual_value).__name__,
        )
    mismatches = {
        key: {"expected": value, "actual": actual_value.get(key, MISSING)}
        for key, value in expected_value.items()
        if actual_value.get(key, MISSING) != value
    }
    return _fail_if(
        bool(mismatches),
        index,
        stage,
        dimension_id,
        "style_profile_mismatch",
        expected_value,
        mismatches,
    )


def _compare_oracle_required(
    actual_value: Any,
    *,
    index: int,
    stage: str,
    dimension_id: str,
) -> Finding | None:
    status = actual_value.get("status") if isinstance(actual_value, dict) else actual_value
    if status is True or status == Status.PASS.value:
        return None
    if status is False or status == Status.FAIL.value:
        return make_finding(
            index,
            stage,
            Status.FAIL,
            "oracle_required_failed",
            f"Oracle-required dimension {dimension_id} failed",
            Status.PASS.value,
            _display(actual_value),
            affected_ids=[dimension_id],
            root_cause_bucket="oracle_gap",
        )
    return _unknown(
        index,
        stage,
        dimension_id,
        "oracle_required_unknown",
        "Oracle-required dimension could not be proven",
        Status.PASS.value,
        _display(actual_value),
        root_cause_bucket="oracle_gap",
    )


def _resolve_value(
    document: dict[str, Any],
    path: str | None,
) -> Any:
    if path is None:
        return document
    current: Any = document
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
            continue
        return MISSING
    return current


def _numeric_tolerance(dimension: dict[str, Any], expected_value: Any) -> float | None:
    if "tolerance" in dimension:
        return float(dimension["tolerance"])
    if "tolerance_abs" in dimension:
        return float(dimension["tolerance_abs"])
    if "tolerance_percent" in dimension:
        if expected_value in (None, 0):
            return None
        return abs(float(expected_value)) * float(dimension["tolerance_percent"]) / 100.0
    return None


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def _fail_if(
    condition: bool,
    index: int,
    stage: str,
    dimension_id: str,
    type_: str,
    expected: Any,
    actual: Any,
) -> Finding | None:
    if not condition:
        return None
    return make_finding(
        index,
        stage,
        Status.FAIL,
        type_,
        f"Dimension {dimension_id} does not match",
        _display(expected),
        _display(actual),
        affected_ids=[dimension_id],
        root_cause_bucket="comparator_mismatch",
    )


def _unknown(
    index: int,
    stage: str,
    dimension_id: str,
    type_: str,
    message: str,
    expected: Any,
    actual: Any,
    *,
    root_cause_bucket: str = "comparator_gap",
) -> Finding:
    return make_finding(
        index,
        stage,
        Status.UNKNOWN,
        type_,
        message,
        _display(expected),
        _display(actual),
        affected_ids=[dimension_id],
        root_cause_bucket=root_cause_bucket,
    )


def _display(value: Any) -> str:
    if value is MISSING:
        return "missing"
    return repr(value)
