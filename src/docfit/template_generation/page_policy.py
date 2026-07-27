"""Canonical page policy derived from the T2 page-group contract."""

from __future__ import annotations

from typing import Any


UNIT_PAGE_POLICY_FIELDS = ("start", "scope")
UNIT_PAGE_START_VALUES = {
    "document_start",
    "new_page",
}
UNIT_PAGE_SCOPE_VALUES = {
    "page_range_exclusive",
}


def normalize_unit_page_policy(
    unit_page_policy: Any,
    *,
    document_start: bool = False,
) -> dict[str, str]:
    if isinstance(unit_page_policy, dict):
        start = unit_page_policy.get("start")
        scope = unit_page_policy.get("scope")
        if start in UNIT_PAGE_START_VALUES and scope in UNIT_PAGE_SCOPE_VALUES:
            return {"start": str(start), "scope": str(scope)}
    return {
        "start": "document_start" if document_start else "new_page",
        "scope": "page_range_exclusive",
    }


def unit_page_policy_shape_errors(unit_page_policy: Any) -> list[str]:
    if not isinstance(unit_page_policy, dict) or not unit_page_policy:
        return ["page_policy must be a non-empty object"]
    errors: list[str] = []
    missing = [
        field for field in UNIT_PAGE_POLICY_FIELDS if field not in unit_page_policy
    ]
    if missing:
        errors.append(f"missing page_policy fields: {missing}")
    if unit_page_policy.get("start") not in UNIT_PAGE_START_VALUES:
        errors.append(
            f"page_policy.start has invalid value: {unit_page_policy.get('start')!r}"
        )
    if unit_page_policy.get("scope") not in UNIT_PAGE_SCOPE_VALUES:
        errors.append(
            f"page_policy.scope has invalid value: {unit_page_policy.get('scope')!r}"
        )
    return errors
