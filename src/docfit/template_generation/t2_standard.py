from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

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
