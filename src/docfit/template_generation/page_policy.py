from __future__ import annotations

from copy import deepcopy
from typing import Any

from .text_utils import _normalize_text


PAGE_POLICY_FIELDS = (
    "page_break",
    "page_isolation",
    "allow_multi_page",
    "keep_together",
)

PAGE_BREAK_VALUES = {True, False, "document_start", "unknown"}
BOOLEAN_OR_UNKNOWN_VALUES = {True, False, "unknown"}
KEEP_TOGETHER_VALUES = {True, False, "local_groups_only", "unknown"}


def canonical_unknown_page_policy(
    *,
    document_start: bool = False,
    origin: str = "unknown",
    confidence: str = "low",
    evidence_refs: list[str] | None = None,
    proposal_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "page_break": "document_start" if document_start else "unknown",
        "page_isolation": "unknown",
        "allow_multi_page": "unknown",
        "keep_together": "unknown",
        "decision": {
            "origin": origin,
            "confidence": confidence,
            "evidence_refs": list(evidence_refs or []),
            "conflict_status": "none",
            "proposal_ids": list(proposal_ids or []),
        },
    }


def canonical_mechanical_page_policy(
    *,
    page_break_evidence_refs: list[str],
    section_break_evidence_refs: list[str],
) -> dict[str, Any]:
    page_refs = _dedupe_str(page_break_evidence_refs)
    section_refs = _dedupe_str(section_break_evidence_refs)
    evidence_refs = _dedupe_str([*page_refs, *section_refs])
    enforcement_hint = "section_break" if section_refs and not page_refs else "page_break"
    page = {
        "page_break": True,
        "page_isolation": "unknown",
        "allow_multi_page": "unknown",
        "keep_together": "unknown",
        "decision": {
            "origin": "mechanical_fact",
            "confidence": "high",
            "evidence_refs": evidence_refs,
            "conflict_status": "none",
            "proposal_ids": [],
        },
        "page_policy": {
            "mechanical": {
                "has_explicit_break": True,
                "page_break_evidence_refs": page_refs,
                "section_break_evidence_refs": section_refs,
            },
            "observed": {},
            "generation_policy": {
                "requires_new_page": True,
                "source": "mechanical_fact",
                "confidence": "high",
                "enforcement_hint": enforcement_hint,
                "evidence_refs": evidence_refs,
            },
        },
    }
    if page_refs:
        page["legacy_page_break"] = "是"
    if section_refs:
        page["section_isolation"] = "是"
    return page


def normalize_page_policy(
    page: Any,
    *,
    document_start: bool = False,
    default_origin: str = "unknown",
    default_confidence: str = "low",
    default_evidence_refs: list[str] | None = None,
    default_proposal_ids: list[str] | None = None,
) -> dict[str, Any]:
    raw = deepcopy(page) if isinstance(page, dict) else {}
    decision = raw.get("decision") if isinstance(raw.get("decision"), dict) else {}
    evidence_refs = _dedupe_str(
        [
            *list(default_evidence_refs or []),
            *list(decision.get("evidence_refs") or []),
            *list(raw.get("evidence_refs") or []),
        ]
    )
    proposal_ids = _dedupe_str(
        [
            *[str(value) for value in (default_proposal_ids or []) if value],
            *[str(value) for value in (decision.get("proposal_ids") or []) if value],
        ]
    )
    normalized = {
        "page_break": _normalize_page_break(
            raw.get("page_break"),
            document_start=document_start,
            legacy_section=raw.get("section_isolation"),
        ),
        "page_isolation": _normalize_bool_unknown(raw.get("page_isolation")),
        "allow_multi_page": _normalize_bool_unknown(raw.get("allow_multi_page")),
        "keep_together": _normalize_keep_together(raw.get("keep_together")),
        "decision": {
            "origin": str(decision.get("origin") or raw.get("origin") or default_origin),
            "confidence": _normalize_confidence(
                decision.get("confidence") or raw.get("confidence") or default_confidence
            ),
            "evidence_refs": evidence_refs,
            "conflict_status": str(decision.get("conflict_status") or "none"),
            "proposal_ids": proposal_ids,
        },
    }
    for key in ("page_policy", "section_isolation", "legacy_page_break"):
        if key in raw:
            normalized[key] = raw[key]
    return normalized


def page_policy_shape_errors(page: Any) -> list[str]:
    if not isinstance(page, dict) or not page:
        return ["page must be a non-empty object"]
    errors: list[str] = []
    missing = [field for field in PAGE_POLICY_FIELDS if field not in page]
    if missing:
        errors.append(f"missing page fields: {missing}")
    if page.get("page_break") not in PAGE_BREAK_VALUES:
        errors.append(f"page_break has invalid value: {page.get('page_break')!r}")
    for field in ("page_isolation", "allow_multi_page"):
        if page.get(field) not in BOOLEAN_OR_UNKNOWN_VALUES:
            errors.append(f"{field} has invalid value: {page.get(field)!r}")
    if page.get("keep_together") not in KEEP_TOGETHER_VALUES:
        errors.append(f"keep_together has invalid value: {page.get('keep_together')!r}")
    decision = page.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision must be an object")
    else:
        if not decision.get("origin"):
            errors.append("decision.origin is required")
        if decision.get("confidence") not in {"low", "medium", "high"}:
            errors.append(
                f"decision.confidence has invalid value: {decision.get('confidence')!r}"
            )
        if not isinstance(decision.get("evidence_refs", []), list):
            errors.append("decision.evidence_refs must be a list")
        if not isinstance(decision.get("proposal_ids", []), list):
            errors.append("decision.proposal_ids must be a list")
    return errors


def pages_equivalent(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    return {
        field: left.get(field)
        for field in PAGE_POLICY_FIELDS
    } == {
        field: right.get(field)
        for field in PAGE_POLICY_FIELDS
    }


def page_start_projection(page: Any, *, unit_order: int = 0) -> str:
    normalized = normalize_page_policy(
        page,
        document_start=unit_order <= 10,
    )
    page_break = normalized.get("page_break")
    if page_break == "document_start":
        return "document_start"
    if page_break is True:
        return "是"
    if normalized.get("section_isolation"):
        return str(normalized.get("section_isolation"))
    return "preserve_source_flow"


def page_policy_known_values(page: Any) -> dict[str, Any]:
    if not isinstance(page, dict):
        return {}
    return {
        field: page.get(field)
        for field in PAGE_POLICY_FIELDS
        if page.get(field) != "unknown"
    }


def page_policy_has_unknown(page: Any) -> bool:
    return any(
        (isinstance(page, dict) and page.get(field) == "unknown")
        for field in PAGE_POLICY_FIELDS
    )


def _normalize_page_break(
    value: Any,
    *,
    document_start: bool,
    legacy_section: Any = None,
) -> bool | str:
    if value == "document_start":
        return "document_start"
    normalized = _normalize_bool(value)
    if normalized is not None:
        return normalized
    if _normalize_bool(legacy_section) is True:
        return True
    if document_start:
        return "document_start"
    return "unknown"


def _normalize_bool_unknown(value: Any) -> bool | str:
    normalized = _normalize_bool(value)
    if normalized is not None:
        return normalized
    return "unknown"


def _normalize_keep_together(value: Any) -> bool | str:
    if value == "local_groups_only":
        return "local_groups_only"
    normalized = _normalize_bool(value)
    if normalized is not None:
        return normalized
    return "unknown"


def _normalize_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    normalized = _normalize_text(str(value or ""))
    if normalized in {"true", "yes", "是"}:
        return True
    if normalized in {"false", "no", "否"}:
        return False
    return None


def _normalize_confidence(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in {"low", "medium", "high"} else "low"


def _dedupe_str(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result
