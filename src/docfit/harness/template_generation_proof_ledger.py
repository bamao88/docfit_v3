from __future__ import annotations

from typing import Any

from docfit.core.status import Status, merge_statuses


def build_required_check_ledger(
    expected: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_checks = [_normalize_check(check) for check in checks]
    consumed_paths = {
        str(path)
        for check in normalized_checks
        for path in check.get("standard_paths", [])
        if path
    }
    declared_paths = _declared_expected_paths(expected)
    unconsumed_paths = [
        path
        for path in declared_paths
        if not any(
            path == consumed or path.startswith(f"{consumed}.")
            for consumed in consumed_paths
        )
    ]
    statuses = [Status(str(check["status"])) for check in normalized_checks]
    if unconsumed_paths:
        statuses.append(Status.UNKNOWN)
    status = merge_statuses(statuses)
    return {
        "status": status.value,
        "required_check_count": len(normalized_checks),
        "completed_check_count": sum(
            1 for check in normalized_checks if check["status"] != Status.UNKNOWN.value
        ),
        "checks": normalized_checks,
        "consumed_standard_paths": sorted(consumed_paths),
        "unconsumed_standard_paths": unconsumed_paths,
    }


def required_check(
    check_id: str,
    status: Status,
    *,
    standard_paths: list[str],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": status.value,
        "standard_paths": standard_paths,
        "evidence": evidence or {},
    }


def _normalize_check(check: dict[str, Any]) -> dict[str, Any]:
    status = str(check.get("status") or Status.UNKNOWN.value)
    if status not in {item.value for item in Status}:
        status = Status.UNKNOWN.value
    return {
        "check_id": str(check.get("check_id") or "unnamed_check"),
        "status": status,
        "standard_paths": [
            str(path) for path in check.get("standard_paths", []) or [] if path
        ],
        "evidence": dict(check.get("evidence") or {}),
    }


def _declared_expected_paths(
    value: Any,
    prefix: str = "expected",
) -> list[str]:
    if not isinstance(value, dict) or not value:
        return [prefix]
    paths: list[str] = []
    for key, child in value.items():
        if str(key) == "notes":
            continue
        child_path = f"{prefix}.{key}"
        if isinstance(child, dict):
            paths.extend(_declared_expected_paths(child, child_path))
        else:
            paths.append(child_path)
    return paths
