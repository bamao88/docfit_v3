from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .page_policy import PAGE_POLICY_FIELDS, normalize_page_policy, page_policy_shape_errors
from .text_utils import _normalize_for_match


T2_STANDARD_RELATIVE_PATH = Path("template_generation/t2_unit_pagination.standard.yaml")
CATALOG_UNIT_IDS = {"toc", "figure_list", "table_list"}


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
    *,
    source_tree: dict[str, Any] | None = None,
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
    anchor_owner_results = (
        _audit_anchor_ownership(unit_map, standard, source_tree)
        if source_tree is not None
        else []
    )
    anchor_owner_failures = [
        result for result in anchor_owner_results if result.get("status") != "PASS"
    ]
    source_range_results = _audit_source_ranges(unit_map, expected_units)
    source_range_failures = [
        result for result in source_range_results if result.get("status") != "PASS"
    ]
    page_policy_results = _audit_page_policies(unit_map, expected_units)
    page_policy_failures = [
        result for result in page_policy_results if result.get("status") != "PASS"
    ]

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
        if anchor_owner_failures:
            findings.append(
                {
                    "type": "t2_standard_anchor_owner_mismatch",
                    "status": "FAIL",
                    "expected": "standard anchors are owned by their expected unit_id",
                    "actual": anchor_owner_failures,
                    "affected_ids": sorted(
                        {
                            str(item.get("expected_unit_id"))
                            for item in anchor_owner_failures
                        }
                    ),
                }
            )
        if source_range_failures:
            findings.append(
                {
                    "type": "t2_standard_source_range_mismatch",
                    "status": "FAIL",
                    "expected": "unit_map units match signed T2 boundary source ranges",
                    "actual": source_range_failures,
                    "affected_ids": sorted(
                        {
                            str(result.get("affected_id"))
                            for result in source_range_failures
                            if result.get("affected_id")
                        }
                    ),
                }
            )
        if page_policy_failures:
            findings.append(
                {
                    "type": "t2_page_policy_mismatch",
                    "status": "FAIL",
                    "expected": "unit_map.units[].page matches signed T2 page policy",
                    "actual": page_policy_failures,
                    "affected_ids": sorted(
                        {
                            str(result.get("affected_id"))
                            for result in page_policy_failures
                            if result.get("affected_id")
                        }
                    ),
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
        "anchor_owner_results": anchor_owner_results,
        "anchor_owner_failures": anchor_owner_failures,
        "source_range_results": source_range_results,
        "source_range_failures": source_range_failures,
        "page_policy_results": page_policy_results,
        "page_policy_failures": page_policy_failures,
        "schema_errors": schema_errors,
        "findings": findings,
    }


def _audit_source_ranges(
    unit_map: dict[str, Any],
    expected_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actual_by_id = {
        str(unit.get("unit_id") or ""): unit
        for unit in unit_map.get("units", []) or []
        if isinstance(unit, dict)
    }
    results: list[dict[str, Any]] = []
    for expected_unit in expected_units:
        unit_id = str(expected_unit.get("unit_id") or "")
        boundary = expected_unit.get("boundary")
        if not unit_id or not isinstance(boundary, dict):
            continue
        expected_seq_range = _range_dict(boundary.get("source_seq_range"))
        expected_ref_range = _range_dict(boundary.get("source_ref_range"))
        if not expected_seq_range and not expected_ref_range:
            continue
        actual_unit = actual_by_id.get(unit_id)
        affected_id = f"{unit_id}.boundary"
        if actual_unit is None:
            results.append(
                {
                    "unit_id": unit_id,
                    "affected_id": affected_id,
                    "status": "FAIL",
                    "reason": "unit missing",
                    "expected": _expected_range_summary(
                        expected_seq_range,
                        expected_ref_range,
                    ),
                    "actual": None,
                }
            )
            continue
        mismatches: list[dict[str, Any]] = []
        actual_seq_range = _actual_source_seq_range(actual_unit)
        actual_ref_range = _actual_source_ref_range(actual_unit)
        if expected_seq_range and actual_seq_range != expected_seq_range:
            mismatches.append(
                {
                    "field": "source_seq_range",
                    "expected": expected_seq_range,
                    "actual": actual_seq_range,
                }
            )
        if expected_ref_range and actual_ref_range != expected_ref_range:
            mismatches.append(
                {
                    "field": "source_ref_range",
                    "expected": expected_ref_range,
                    "actual": actual_ref_range,
                }
            )
        results.append(
            {
                "unit_id": unit_id,
                "affected_id": affected_id,
                "status": "PASS" if not mismatches else "FAIL",
                "expected": _expected_range_summary(
                    expected_seq_range,
                    expected_ref_range,
                ),
                "actual": {
                    "source_seq_range": actual_seq_range,
                    "source_ref_range": actual_ref_range,
                },
                "mismatches": mismatches,
            }
        )
    return results


def _expected_range_summary(
    expected_seq_range: dict[str, Any],
    expected_ref_range: dict[str, Any],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if expected_seq_range:
        summary["source_seq_range"] = expected_seq_range
    if expected_ref_range:
        summary["source_ref_range"] = expected_ref_range
    return summary


def _range_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    if "start" not in value or "end" not in value:
        return {}
    return {"start": value.get("start"), "end": value.get("end")}


def _actual_source_seq_range(unit: dict[str, Any]) -> dict[str, Any]:
    refs = [
        parsed
        for parsed in (_int_or_none(ref) for ref in unit.get("source_seq_refs", []) or [])
        if parsed is not None
    ]
    if refs:
        return {"start": min(refs), "end": max(refs)}
    source_seq_range = unit.get("source_seq_range")
    if isinstance(source_seq_range, dict):
        start = _int_or_none(
            source_seq_range.get("start")
            or source_seq_range.get("start_source_seq")
        )
        end = _int_or_none(
            source_seq_range.get("end")
            or source_seq_range.get("end_source_seq")
        )
        if start is not None and end is not None:
            return {"start": start, "end": end}
    return {}


def _actual_source_ref_range(unit: dict[str, Any]) -> dict[str, Any]:
    source_range = unit.get("source_range")
    if isinstance(source_range, dict):
        start = source_range.get("start") or source_range.get("start_source_ref")
        end = source_range.get("end") or source_range.get("end_source_ref")
        if start and end:
            return {"start": str(start), "end": str(end)}
    refs = [str(ref) for ref in unit.get("source_refs", []) or [] if ref]
    if refs:
        return {"start": refs[0], "end": refs[-1]}
    return {}


def _audit_page_policies(
    unit_map: dict[str, Any],
    expected_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actual_by_id = {
        str(unit.get("unit_id") or ""): unit
        for unit in unit_map.get("units", []) or []
        if isinstance(unit, dict)
    }
    results: list[dict[str, Any]] = []
    for expected_unit in expected_units:
        unit_id = str(expected_unit.get("unit_id") or "")
        expected_page = expected_unit.get("page")
        if not unit_id or not isinstance(expected_page, dict):
            continue
        actual_unit = actual_by_id.get(unit_id)
        affected_id = f"{unit_id}.page"
        if actual_unit is None:
            results.append(
                {
                    "unit_id": unit_id,
                    "affected_id": affected_id,
                    "status": "FAIL",
                    "reason": "unit missing",
                    "expected": {
                        field: expected_page.get(field)
                        for field in PAGE_POLICY_FIELDS
                    },
                    "actual": None,
                }
            )
            continue
        actual_raw = actual_unit.get("page")
        shape_errors = page_policy_shape_errors(actual_raw)
        if shape_errors:
            results.append(
                {
                    "unit_id": unit_id,
                    "affected_id": affected_id,
                    "status": "FAIL",
                    "reason": "actual page policy shape invalid",
                    "expected": {
                        field: expected_page.get(field)
                        for field in PAGE_POLICY_FIELDS
                    },
                    "actual": actual_raw,
                    "shape_errors": shape_errors,
                }
            )
            continue
        actual_page = normalize_page_policy(actual_raw)
        mismatches = []
        for field in PAGE_POLICY_FIELDS:
            expected_value = normalize_page_policy({field: expected_page.get(field)}).get(field)
            actual_value = actual_page.get(field)
            if actual_value != expected_value:
                mismatches.append(
                    {
                        "field": field,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )
        results.append(
            {
                "unit_id": unit_id,
                "affected_id": affected_id,
                "status": "PASS" if not mismatches else "FAIL",
                "expected": {
                    field: normalize_page_policy({field: expected_page.get(field)}).get(field)
                    for field in PAGE_POLICY_FIELDS
                },
                "actual": {
                    field: actual_page.get(field)
                    for field in PAGE_POLICY_FIELDS
                },
                "mismatches": mismatches,
            }
        )
    return results


def _actual_unit_ids(unit_map: dict[str, Any]) -> list[str]:
    units = unit_map.get("units")
    if not isinstance(units, list):
        return []
    return [
        str(unit.get("unit_id"))
        for unit in units
        if isinstance(unit, dict) and unit.get("unit_id") is not None
    ]


def _audit_anchor_ownership(
    unit_map: dict[str, Any],
    standard: dict[str, Any],
    source_tree: dict[str, Any],
) -> list[dict[str, Any]]:
    owner_maps = _owner_maps(unit_map)
    entries = _body_entries(source_tree)
    results: list[dict[str, Any]] = []
    for expected_unit in expected_units_from_t2_standard(standard):
        unit_id = str(expected_unit.get("unit_id") or "")
        anchors = expected_unit.get("anchors") or {}
        boundary = expected_unit.get("boundary") or {}
        if not isinstance(anchors, dict):
            continue
        if isinstance(boundary, dict) and boundary.get("expected_start") == "document_start":
            first_entry = entries[0] if entries else None
            if first_entry is not None:
                matched = [first_entry]
                terms_used = ["document_start"]
            else:
                matched = []
                terms_used = ["document_start"]
        else:
            primary_terms, fallback_terms = _anchor_match_terms(anchors)
            if not primary_terms and not fallback_terms:
                continue
            matched = _match_anchor_entries(
                entries,
                primary_terms,
                expected_unit_id=unit_id,
            )
            terms_used = primary_terms
            if not matched and fallback_terms:
                matched = _match_anchor_entries(
                    entries,
                    fallback_terms,
                    expected_unit_id=unit_id,
                )
                terms_used = fallback_terms
        if not terms_used:
            continue
        if not matched:
            results.append(
                {
                    "expected_unit_id": unit_id,
                    "status": "UNKNOWN",
                    "reason": "no source entry matched standard anchor terms",
                    "anchor_terms": terms_used,
                }
            )
            continue
        owned_matches = [
            entry
            for entry in matched
            if _entry_owner(entry, owner_maps) == unit_id
        ]
        if owned_matches:
            matched = owned_matches
        for entry in matched:
            seq = _int_or_none(entry.get("source_seq"))
            actual_owner = _entry_owner(entry, owner_maps)
            status = "PASS" if actual_owner == unit_id else "FAIL"
            results.append(
                {
                    "expected_unit_id": unit_id,
                    "source_seq": seq,
                    "text": entry.get("text"),
                    "actual_unit_id": actual_owner,
                    "status": status,
                }
            )
    return results


def _entry_owner(
    entry: dict[str, Any],
    owner_maps: dict[str, dict[Any, str]],
) -> str | None:
    seq = _int_or_none(entry.get("source_seq"))
    if seq is not None and seq in owner_maps["source_seq"]:
        return owner_maps["source_seq"][seq]
    source_ref = str(entry.get("source_ref") or "")
    if source_ref:
        return owner_maps["source_ref"].get(source_ref)
    return None


def _owner_maps(unit_map: dict[str, Any]) -> dict[str, dict[Any, str]]:
    seq_mapping: dict[int, str] = {}
    ref_mapping: dict[str, str] = {}
    units = unit_map.get("units")
    if not isinstance(units, list):
        return {"source_seq": seq_mapping, "source_ref": ref_mapping}
    for unit in units:
        if not isinstance(unit, dict):
            continue
        unit_id = str(unit.get("unit_id") or "")
        for seq in unit.get("source_seq_refs", []) or []:
            parsed = _int_or_none(seq)
            if parsed is not None:
                seq_mapping[parsed] = unit_id
        for source_ref in unit.get("source_refs", []) or []:
            if source_ref:
                ref_mapping[str(source_ref)] = unit_id
    return {"source_seq": seq_mapping, "source_ref": ref_mapping}


def _body_entries(source_tree: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [
        item
        for item in source_tree.get("layers", {}).get("body_flow", [])
        if item.get("structure_layer") == "body_flow" and item.get("text")
    ]
    return _with_synthetic_content_control_toc_entries(entries, source_tree)


def _with_synthetic_content_control_toc_entries(
    entries: list[dict[str, Any]],
    source_tree: dict[str, Any],
) -> list[dict[str, Any]]:
    if any(
        _normalize_for_match(str(entry.get("text") or "")) == "目录"
        for entry in entries
    ):
        return entries
    for item in source_tree.get("data", {}).get("content_controls", []) or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "")
        normalized = _normalize_for_match(text)
        if not normalized.startswith("目录"):
            continue
        markers = ("摘要", "abstract", "图目录", "表目录", "参考文献")
        if sum(1 for marker in markers if marker in normalized) < 3:
            continue
        toc_field = _main_toc_field(source_tree)
        source_ref = toc_field.get("source_ref") if toc_field else item.get("source_ref")
        synthetic = {
            "structure_layer": "body_flow",
            "source_ref": source_ref,
            "text": "目录",
            "synthetic": True,
            "synthetic_kind": "content_control_toc",
        }
        insert_at = _first_catalog_entry_index(entries)
        return [*entries[:insert_at], synthetic, *entries[insert_at:]]
    return entries


def _main_toc_field(source_tree: dict[str, Any]) -> dict[str, Any] | None:
    for item in source_tree.get("data", {}).get("fields", []) or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("field_type") or "").upper() != "TOC":
            continue
        instruction = str(item.get("instruction") or "")
        if r"\c" in instruction:
            continue
        return item
    return None


def _first_catalog_entry_index(entries: list[dict[str, Any]]) -> int:
    for index, entry in enumerate(entries):
        normalized = _normalize_for_match(str(entry.get("text") or ""))
        if normalized in {"图目录", "表目录", "listoffigures", "listoftables"}:
            return index
    return len(entries)


def _anchor_match_terms(anchors: dict[str, Any]) -> tuple[list[str], list[str]]:
    primary: list[str] = []
    fallback: list[str] = []
    start_title = anchors.get("start_title")
    if isinstance(start_title, str) and start_title not in {
        "document_start",
        "document_end",
    }:
        primary.append(start_title)
    aliases = anchors.get("title_aliases")
    if isinstance(aliases, list):
        fallback.extend(str(alias) for alias in aliases if alias)
    return _dedupe_normalized_terms(primary), _dedupe_normalized_terms(fallback)


def _dedupe_normalized_terms(terms: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        normalized = _normalize_for_match(term)
        if not normalized or normalized in seen:
            continue
        deduped.append(normalized)
        seen.add(normalized)
    return deduped


def _match_anchor_entries(
    entries: list[dict[str, Any]],
    terms: list[str],
    *,
    expected_unit_id: str,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for entry in entries:
        text = str(entry.get("text") or "")
        normalized = _normalize_for_match(text)
        if not normalized:
            continue
        if expected_unit_id not in CATALOG_UNIT_IDS and _looks_like_toc_entry_text(text):
            continue
        if any(_term_matches_entry(term, normalized) for term in terms):
            matches.append(entry)
    return matches[:3]


def _term_matches_entry(term: str, normalized_entry: str) -> bool:
    if normalized_entry == term:
        return True
    if term == "附录" and normalized_entry.startswith(term):
        return True
    return len(term) >= 3 and normalized_entry.startswith(term)


def _looks_like_toc_entry_text(text: str) -> bool:
    stripped = str(text or "").strip()
    page_suffix = r"(?:\d+|[ivxlcdmIVXLCDM]+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+)"
    return bool(
        "\t" in stripped
        or re.search(rf"(?:…|\.|．|·|•){{2,}}\s*{page_suffix}\s*$", stripped)
    )


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
