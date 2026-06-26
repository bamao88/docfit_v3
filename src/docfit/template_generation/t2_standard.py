from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


T2_STANDARD_RELATIVE_PATH = Path("template_generation/t2_unit_pagination.standard.yaml")


def load_t2_unit_pagination_standard(
    root: Path,
    school_id: str,
    template_version: str = "v1",
) -> dict[str, Any]:
    path = t2_unit_pagination_standard_path(root, school_id, template_version)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    standard = loaded or {}
    standard["_standard_path"] = str(path)
    return standard


def t2_unit_pagination_standard_path(
    root: Path,
    school_id: str,
    template_version: str = "v1",
) -> Path:
    return (
        root
        / "standards"
        / "targets"
        / school_id
        / template_version
        / T2_STANDARD_RELATIVE_PATH
    )


def expected_unit_ids_from_t2_standard(standard: dict[str, Any]) -> list[str]:
    expected = standard.get("expected", {})
    unit_order = expected.get("unit_order")
    if isinstance(unit_order, list):
        return [str(unit_id) for unit_id in unit_order]
    units = expected.get("units")
    if isinstance(units, list):
        return [
            str(unit.get("unit_id"))
            for unit in units
            if isinstance(unit, dict) and unit.get("unit_id") is not None
        ]
    return []


def expected_units_from_t2_standard(standard: dict[str, Any]) -> list[dict[str, Any]]:
    units = standard.get("expected", {}).get("units")
    if not isinstance(units, list):
        return []
    return [unit for unit in units if isinstance(unit, dict)]


def audit_unit_map_against_t2_standard(
    unit_map: dict[str, Any],
    standard: dict[str, Any],
) -> dict[str, Any]:
    expected_unit_ids = expected_unit_ids_from_t2_standard(standard)
    expected_units = expected_units_from_t2_standard(standard)
    expected_ids_from_units = [
        str(unit.get("unit_id"))
        for unit in expected_units
        if unit.get("unit_id") is not None
    ]
    actual_unit_ids = _actual_unit_ids(unit_map)
    custom_unit_ids = [
        unit_id for unit_id in actual_unit_ids if unit_id.startswith("custom:")
    ]
    unexpected_unit_ids = [
        unit_id for unit_id in actual_unit_ids if unit_id not in expected_unit_ids
    ]
    missing_unit_ids = [
        unit_id for unit_id in expected_unit_ids if unit_id not in actual_unit_ids
    ]
    unit_order_matches = bool(expected_unit_ids) and actual_unit_ids == expected_unit_ids

    schema_errors = _schema_errors(
        standard,
        expected_unit_ids=expected_unit_ids,
        expected_ids_from_units=expected_ids_from_units,
    )
    findings: list[dict[str, Any]] = []
    if schema_errors:
        findings.append(
            {
                "type": "t2_standard_schema_invalid",
                "status": "UNKNOWN",
                "expected": "valid T2 unit pagination standard",
                "actual": schema_errors,
            }
        )
    else:
        if not unit_order_matches:
            findings.append(
                {
                    "type": "t2_standard_unit_order_mismatch",
                    "status": "FAIL",
                    "expected": expected_unit_ids,
                    "actual": actual_unit_ids,
                }
            )
        if missing_unit_ids:
            findings.append(
                {
                    "type": "t2_standard_units_missing",
                    "status": "FAIL",
                    "expected": missing_unit_ids,
                    "actual": actual_unit_ids,
                    "affected_ids": missing_unit_ids,
                }
            )
        non_custom_unexpected = [
            unit_id for unit_id in unexpected_unit_ids if not unit_id.startswith("custom:")
        ]
        if non_custom_unexpected:
            findings.append(
                {
                    "type": "t2_standard_units_unexpected",
                    "status": "FAIL",
                    "expected": expected_unit_ids,
                    "actual": non_custom_unexpected,
                    "affected_ids": non_custom_unexpected,
                }
            )
        if custom_unit_ids:
            findings.append(
                {
                    "type": "t2_standard_custom_units_present",
                    "status": "FAIL",
                    "expected": "no custom units when a signed T2 standard exists",
                    "actual": custom_unit_ids,
                    "affected_ids": custom_unit_ids,
                }
            )

    audit_status = _audit_status(findings)
    gate_enabled = bool(standard.get("gate_enabled"))
    return {
        "artifact_type": "t2_standard_audit",
        "school_id": standard.get("school_id"),
        "standard_id": standard.get("standard_id"),
        "standard_path": standard.get("_standard_path"),
        "verifier_state": standard.get("verifier_state"),
        "gate_enabled": gate_enabled,
        "audit_status": audit_status,
        "gate_status": _gate_status(audit_status, gate_enabled=gate_enabled),
        "expected_unit_ids": expected_unit_ids,
        "actual_unit_ids": actual_unit_ids,
        "missing_unit_ids": missing_unit_ids,
        "unexpected_unit_ids": unexpected_unit_ids,
        "custom_unit_ids": custom_unit_ids,
        "unit_order_matches": unit_order_matches,
        "schema_errors": schema_errors,
        "findings": findings,
    }


def _actual_unit_ids(unit_map: dict[str, Any]) -> list[str]:
    units = unit_map.get("units")
    if not isinstance(units, list):
        return []
    return [
        str(unit.get("unit_id"))
        for unit in units
        if isinstance(unit, dict) and unit.get("unit_id") is not None
    ]


def _schema_errors(
    standard: dict[str, Any],
    *,
    expected_unit_ids: list[str],
    expected_ids_from_units: list[str],
) -> list[str]:
    errors: list[str] = []
    if standard.get("artifact_under_test") != "unit_map":
        errors.append("artifact_under_test must be unit_map")
    if not expected_unit_ids:
        errors.append("expected.unit_order is missing or empty")
    if not expected_ids_from_units:
        errors.append("expected.units is missing or empty")
    if expected_unit_ids and expected_ids_from_units:
        if expected_unit_ids != expected_ids_from_units:
            errors.append("expected.unit_order does not match expected.units[].unit_id")
    return errors


def _audit_status(findings: list[dict[str, Any]]) -> str:
    statuses = {str(finding.get("status") or "") for finding in findings}
    if "FAIL" in statuses:
        return "FAIL"
    if "UNKNOWN" in statuses:
        return "UNKNOWN"
    return "PASS"


def _gate_status(audit_status: str, *, gate_enabled: bool) -> str:
    if gate_enabled:
        return audit_status
    if audit_status == "PASS":
        return "AUDIT_PASS"
    if audit_status == "UNKNOWN":
        return "AUDIT_UNKNOWN"
    return "AUDIT_FAIL"
