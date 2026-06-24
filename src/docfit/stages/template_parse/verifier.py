from __future__ import annotations

import re
from typing import Any

from docfit.core.models import Finding, make_finding
from docfit.core.status import Status
from docfit.template_model.units import expected_slot_ids_from_units


_UNIT_FIELDS = (
    "name",
    "order",
    "status",
    "policy",
    "source",
    "handling",
    "element_order",
    "layout_relation",
    "missing_policy",
)

_UNIT_PAGE_FIELDS = ("page_break", "section_isolation", "keep_together")

_ELEMENT_FIELDS = (
    "name",
    "order",
    "policy",
    "type",
    "fill",
    "content",
    "position",
    "relationship",
)


def expected_units_from_contract_source(
    source_facts: dict[str, Any],
) -> list[dict[str, Any]]:
    units = source_facts.get("units")
    if isinstance(units, list) and units:
        return units
    return []


def verify_template_units_against_expected(
    template_artifact: dict[str, Any],
    expected_units: list[dict[str, Any]],
    *,
    start_index: int = 1,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    if not expected_units:
        return [
            make_finding(
                next_index,
                "template",
                Status.UNKNOWN,
                "template_structured_expected_missing",
                "模板标准缺少可执行的结构化 expected units",
                "real_core_source_facts.units",
                "missing",
                root_cause_bucket="template_contract_gap",
            )
        ]

    actual_units = template_artifact.get("data", {}).get("units", [])
    if not isinstance(actual_units, list) or not actual_units:
        return [
            make_finding(
                next_index,
                "template",
                Status.UNKNOWN,
                "template_actual_units_missing",
                "模板解析结果缺少可比对的 data.units",
                "template_artifact.data.units",
                "missing",
                root_cause_bucket="template_unit_model_gap",
            )
        ]

    expected_ids = [str(unit.get("unit_id")) for unit in expected_units]
    actual_ids = [str(unit.get("unit_id")) for unit in actual_units]
    if expected_ids != actual_ids:
        findings.append(
            make_finding(
                next_index,
                "template",
                Status.FAIL,
                "template_unit_order_mismatch",
                "模板单元顺序或单元集合不符合标准",
                repr(expected_ids),
                repr(actual_ids),
                affected_ids=["template.units"],
                root_cause_bucket="template_generation_final_mismatch",
            )
        )
        next_index += 1

    expected_by_id = {str(unit.get("unit_id")): unit for unit in expected_units}
    actual_by_id = {str(unit.get("unit_id")): unit for unit in actual_units}
    for unit_id in sorted(set(expected_by_id) - set(actual_by_id)):
        findings.append(_missing_finding(next_index, "unit", unit_id))
        next_index += 1
    for unit_id in sorted(set(actual_by_id) - set(expected_by_id)):
        findings.append(_unexpected_finding(next_index, "unit", unit_id))
        next_index += 1

    for unit_id in expected_ids:
        expected_unit = expected_by_id.get(unit_id)
        actual_unit = actual_by_id.get(unit_id)
        if expected_unit is None or actual_unit is None:
            continue
        for field in _UNIT_FIELDS:
            if _normalized(expected_unit.get(field)) != _normalized(
                actual_unit.get(field)
            ):
                findings.append(
                    _field_mismatch_finding(
                        next_index,
                        "template_unit_field_mismatch",
                        f"{unit_id}.{field}",
                        expected_unit.get(field),
                        actual_unit.get(field),
                    )
                )
                next_index += 1
        expected_page = expected_unit.get("page", {})
        actual_page = actual_unit.get("page", {})
        for field in _UNIT_PAGE_FIELDS:
            if _normalized(expected_page.get(field)) != _normalized(
                actual_page.get(field)
            ):
                findings.append(
                    _field_mismatch_finding(
                        next_index,
                        "template_unit_page_mismatch",
                        f"{unit_id}.page.{field}",
                        expected_page.get(field),
                        actual_page.get(field),
                    )
                )
                next_index += 1
        element_findings, next_index = _compare_elements(
            expected_unit,
            actual_unit,
            unit_id,
            next_index,
        )
        findings.extend(element_findings)

    slot_finding = _compare_slot_ids(
        template_artifact,
        expected_units,
        index=next_index,
    )
    if slot_finding is not None:
        findings.append(slot_finding)
    return findings


def verify_template_units_against_source_facts(
    template_artifact: dict[str, Any],
    *,
    start_index: int = 1,
) -> list[Finding]:
    source_facts = template_artifact.get("real_core_source_facts")
    if not isinstance(source_facts, dict):
        return [
            make_finding(
                start_index,
                "template",
                Status.UNKNOWN,
                "template_source_facts_missing",
                "模板 artifact 缺少 real_core_source_facts，无法做细粒度业务验收",
                "real_core_source_facts.units",
                "missing",
                root_cause_bucket="template_contract_gap",
            )
        ]
    return verify_template_units_against_expected(
        template_artifact,
        expected_units_from_contract_source(source_facts),
        start_index=start_index,
    )


def _compare_elements(
    expected_unit: dict[str, Any],
    actual_unit: dict[str, Any],
    unit_id: str,
    next_index: int,
) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    expected_elements = expected_unit.get("elements", [])
    actual_elements = actual_unit.get("elements", [])
    expected_ids = [str(element.get("element_id")) for element in expected_elements]
    actual_ids = [str(element.get("element_id")) for element in actual_elements]
    if expected_ids != actual_ids:
        findings.append(
            make_finding(
                next_index,
                "template",
                Status.FAIL,
                "template_element_order_mismatch",
                f"{unit_id} 的元素顺序或集合不符合标准",
                repr(expected_ids),
                repr(actual_ids),
                affected_ids=[unit_id],
                root_cause_bucket="template_generation_final_mismatch",
            )
        )
        next_index += 1

    expected_by_id = {
        str(element.get("element_id")): element for element in expected_elements
    }
    actual_by_id = {
        str(element.get("element_id")): element for element in actual_elements
    }
    for element_id in sorted(set(expected_by_id) - set(actual_by_id)):
        findings.append(_missing_finding(next_index, "element", f"{unit_id}.{element_id}"))
        next_index += 1
    for element_id in sorted(set(actual_by_id) - set(expected_by_id)):
        findings.append(
            _unexpected_finding(next_index, "element", f"{unit_id}.{element_id}")
        )
        next_index += 1

    for element_id in expected_ids:
        expected = expected_by_id.get(element_id)
        actual = actual_by_id.get(element_id)
        if expected is None or actual is None:
            continue
        for field in _ELEMENT_FIELDS:
            if _normalized(expected.get(field)) != _normalized(actual.get(field)):
                findings.append(
                    _field_mismatch_finding(
                        next_index,
                        "template_element_field_mismatch",
                        f"{unit_id}.{element_id}.{field}",
                        expected.get(field),
                        actual.get(field),
                    )
                )
                next_index += 1
        if _normalized(expected.get("style")) != _normalized(actual.get("style")):
            findings.append(
                _field_mismatch_finding(
                    next_index,
                    "template_element_style_mismatch",
                    f"{unit_id}.{element_id}.style",
                    expected.get("style"),
                    actual.get("style"),
                )
            )
            next_index += 1
    return findings, next_index


def _compare_slot_ids(
    template_artifact: dict[str, Any],
    expected_units: list[dict[str, Any]],
    *,
    index: int,
) -> Finding | None:
    expected_slot_ids = sorted(expected_slot_ids_from_units(expected_units))
    actual_slot_ids = sorted(
        str(slot.get("slot_id"))
        for slot in template_artifact.get("data", {}).get("slots", [])
        if slot.get("slot_id") != "slot_body_start"
    )
    if expected_slot_ids == actual_slot_ids:
        return None
    return make_finding(
        index,
        "template",
        Status.FAIL,
        "template_slot_contract_mismatch",
        "模板可写 slot 集合不符合结构化模板标准",
        repr(expected_slot_ids),
        repr(actual_slot_ids),
        affected_ids=["template.slots"],
        root_cause_bucket="template_generation_final_mismatch",
    )


def _missing_finding(index: int, kind: str, identifier: str) -> Finding:
    return make_finding(
        index,
        "template",
        Status.FAIL,
        f"template_{kind}_missing",
        f"模板解析结果缺少标准要求的 {kind}",
        identifier,
        "missing",
        affected_ids=[identifier],
        root_cause_bucket="template_generation_final_mismatch",
    )


def _unexpected_finding(index: int, kind: str, identifier: str) -> Finding:
    return make_finding(
        index,
        "template",
        Status.FAIL,
        f"template_{kind}_unexpected",
        f"模板解析结果包含标准未声明的 {kind}",
        "not present",
        identifier,
        affected_ids=[identifier],
        root_cause_bucket="template_generation_final_mismatch",
    )


def _field_mismatch_finding(
    index: int,
    type_: str,
    path: str,
    expected: Any,
    actual: Any,
) -> Finding:
    return make_finding(
        index,
        "template",
        Status.FAIL,
        type_,
        f"模板元素字段不符合标准：{path}",
        _preview(expected),
        _preview(actual),
        affected_ids=[path],
        root_cause_bucket="template_generation_final_mismatch",
    )


def _normalized(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _preview(value: Any, limit: int = 240) -> str:
    normalized = _normalized(value)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."
