from __future__ import annotations

import re
from typing import Any


_REVIEW_SECTION_RE = re.compile(
    r"^\s*(?P<tier>[12])\.(?P<order>\d+)\s+(?P<name>.+?)（(?P<unit_id>[^）]+)）"
)

_ELEMENT_RE = re.compile(r"^\s+-\s+(?P<name>.+?)\s*$")

INSTRUCTION_MARKERS = (
    "附件",
    "基本格式",
    "空一行",
    "几号",
    "号字",
    "论文题目（三号黑体）",
    "摘要（四号黑体）",
    "研究生院网站上的毕业论文模板功能有严重欠缺",
)

def parse_reviewed_template_units(review_text: str) -> list[dict[str, Any]]:
    sections = _review_sections(review_text)
    units: dict[str, dict[str, Any]] = {}
    for section in sections:
        unit = units.setdefault(
            section["unit_id"],
            {
                "unit_id": section["unit_id"],
                "name": section["name"],
                "order": section["order"],
                "status": "required",
                "source_refs": [],
                "page": {},
                "policy": "fixed",
                "elements": [],
            },
        )
        unit["source_refs"].append(section["source_ref"])
        if section["tier"] == "1":
            unit.update(_parse_unit_overview(section["body"], unit))
        elif section["tier"] == "2":
            unit.update(_parse_unit_detail(section["body"], unit))

    ordered = sorted(units.values(), key=lambda item: int(item.get("order", 0)))
    for unit in ordered:
        if not unit.get("elements"):
            unit["elements"] = [
                {
                    "element_id": "e_001",
                    "name": unit["name"],
                    "order": 1,
                    "policy": unit.get("policy", "fixed"),
                    "content": unit.get("handling", ""),
                    "style": "",
                    "source_refs": list(unit.get("source_refs", [])),
                }
            ]
    return ordered


def classify_instruction_paragraphs(
    paragraphs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    instruction_paragraphs: list[dict[str, Any]] = []
    for paragraph in paragraphs:
        text = str(paragraph.get("text", ""))
        if not contains_instruction_marker(text):
            continue
        instruction_paragraphs.append(
            {
                "source_ref": f"word/document.xml:p[{paragraph.get('index')}]",
                "paragraph_index": paragraph.get("index"),
                "text": text,
                "policy": "strip",
                "final_disposition": "omit_from_final",
                "reason": (
                    "reviewed template instruction/example text is evidence, "
                    "not final thesis content"
                ),
            }
        )
    return instruction_paragraphs


def apply_instruction_policy(
    paragraphs: list[dict[str, Any]],
    instruction_paragraphs: list[dict[str, Any]],
) -> None:
    policy_by_index = {
        item.get("paragraph_index"): item for item in instruction_paragraphs
    }
    for paragraph in paragraphs:
        policy = policy_by_index.get(paragraph.get("index"))
        if policy is None:
            continue
        paragraph["template_policy"] = policy["policy"]
        paragraph["final_disposition"] = policy["final_disposition"]
        paragraph["policy_reason"] = policy["reason"]


def contains_instruction_marker(text: str) -> bool:
    return any(marker in text for marker in INSTRUCTION_MARKERS)


def extend_slots_and_regions_from_units(
    slots: list[dict[str, Any]],
    regions: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> None:
    existing_slots = {slot.get("slot_id") for slot in slots}
    existing_regions = {region.get("region_id") for region in regions}
    for unit in units:
        unit_id = str(unit.get("unit_id"))
        unit_slots: list[str] = []
        for element in unit.get("elements", []):
            policy = element.get("policy")
            if policy not in {"fill", "generated", "template_default_optional"}:
                continue
            slot_id = f"{unit_id}.{element.get('element_id')}"
            unit_slots.append(slot_id)
            if slot_id in existing_slots:
                continue
            slots.append(
                {
                    "slot_id": slot_id,
                    "unit_id": unit_id,
                    "element_id": element.get("element_id"),
                    "element_name": element.get("name"),
                    "kind": slot_kind(unit_id, element),
                    "writable": policy != "generated",
                    "required": unit.get("status") == "required",
                    "accepted_content_kinds": accepted_content_kinds(
                        unit_id,
                        element,
                    ),
                    "source_ref": ",".join(element.get("source_refs", [])),
                    "policy": policy,
                }
            )
            existing_slots.add(slot_id)
        if unit_id not in existing_regions:
            regions.append(
                {
                    "region_id": unit_id,
                    "kind": unit_id,
                    "required": unit.get("status") == "required",
                    "anchors": unit_slots,
                    "source_ref": ",".join(unit.get("source_refs", [])),
                    "policy": unit.get("policy", "fixed"),
                }
            )
            existing_regions.add(unit_id)


def slot_kind(unit_id: str, element: dict[str, Any]) -> str:
    name = f"{unit_id} {element.get('name', '')}"
    if "表" in name or "table" in name.lower():
        return "table"
    if "图" in name or "image" in name.lower() or "figure" in name.lower():
        return "image"
    if "标题" in name or "题名" in name or "heading" in name.lower():
        return "heading"
    return "body_content"


def accepted_content_kinds(unit_id: str, element: dict[str, Any]) -> list[str]:
    kind = slot_kind(unit_id, element)
    if kind == "table":
        return ["table"]
    if kind == "image":
        return ["image"]
    if kind == "heading":
        return ["heading", "paragraph"]
    return ["heading", "paragraph", "table", "image"]


def protected_zones_from_units(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    for unit in units:
        fixed_elements = [
            element.get("element_id")
            for element in unit.get("elements", [])
            if element.get("policy") in {"fixed", "manual_only"}
        ]
        if not fixed_elements:
            continue
        zones.append(
            {
                "zone_id": f"{unit.get('unit_id')}.fixed",
                "unit_id": unit.get("unit_id"),
                "policy": unit.get("policy"),
                "element_ids": fixed_elements,
                "source_refs": unit.get("source_refs", []),
            }
        )
    return zones


def required_fields_from_units(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for unit in units:
        for element in unit.get("elements", []):
            if element.get("policy") not in {"fill", "generated"}:
                continue
            fields.append(
                {
                    "field_id": f"{unit.get('unit_id')}.{element.get('element_id')}",
                    "unit_id": unit.get("unit_id"),
                    "element_id": element.get("element_id"),
                    "name": element.get("name"),
                    "policy": element.get("policy"),
                    "source_refs": element.get("source_refs", []),
                }
            )
    return fields


def expected_slot_ids_from_units(units: list[dict[str, Any]]) -> list[str]:
    slot_ids: list[str] = []
    for unit in units:
        unit_id = str(unit.get("unit_id"))
        for element in unit.get("elements", []):
            if element.get("policy") in {
                "fill",
                "generated",
                "template_default_optional",
            }:
                slot_ids.append(f"{unit_id}.{element.get('element_id')}")
    return slot_ids


def _review_sections(review_text: str) -> list[dict[str, Any]]:
    lines = review_text.splitlines()
    headers: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        match = _REVIEW_SECTION_RE.match(line)
        if match:
            headers.append((index, match))

    sections: list[dict[str, Any]] = []
    for header_index, (line_index, match) in enumerate(headers):
        next_index = (
            headers[header_index + 1][0]
            if header_index + 1 < len(headers)
            else len(lines)
        )
        sections.append(
            {
                "tier": match.group("tier"),
                "order": int(match.group("order")),
                "name": match.group("name").strip(),
                "unit_id": _safe_identifier(match.group("unit_id")),
                "source_ref": f"review_text:{match.group('tier')}.{match.group('order')}",
                "body": lines[line_index + 1 : next_index],
            }
        )
    return sections


def _parse_unit_overview(
    lines: list[str],
    unit: dict[str, Any],
) -> dict[str, Any]:
    text = "\n".join(lines)
    status = _field_value(text, "状态") or str(unit.get("status") or "required")
    handling = _line_value(lines, "处理")
    return {
        "status": status,
        "source": _field_value(text, "来源") or "",
        "policy": _policy_from_values(status=status, type_text="", fill_text=""),
        "handling": handling,
        "page": {
            "page_break": _field_value(text, "另起页") or "",
            "section_isolation": _field_value(text, "分页隔离") or "",
            "keep_together": _line_value(lines, "同页约束"),
        },
    }


def _parse_unit_detail(
    lines: list[str],
    unit: dict[str, Any],
) -> dict[str, Any]:
    elements = _parse_elements(
        lines,
        default_policy=str(unit.get("policy") or "fixed"),
    )
    return {
        "header_footer": {
            "header": _line_value(lines, "页眉"),
            "page_number": _line_value(lines, "页码"),
        },
        "element_order": _line_value(lines, "元素顺序"),
        "layout_relation": _line_value(lines, "排版关系"),
        "missing_policy": _line_value(lines, "缺失处理"),
        "elements": elements,
    }


def _parse_elements(lines: list[str], *, default_policy: str) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    current_name: str | None = None
    current_lines: list[str] = []
    for line in lines:
        match = _ELEMENT_RE.match(line)
        if match:
            if current_name is not None:
                elements.append(
                    _build_element(
                        current_name,
                        current_lines,
                        len(elements) + 1,
                        default_policy,
                    )
                )
            current_name = match.group("name").strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)
    if current_name is not None:
        elements.append(
            _build_element(current_name, current_lines, len(elements) + 1, default_policy)
        )
    return elements


def _build_element(
    name: str,
    lines: list[str],
    order: int,
    default_policy: str,
) -> dict[str, Any]:
    text = "\n".join(lines)
    type_text = _line_value(lines, "类型")
    fill_text = _line_value(lines, "是否填充")
    policy = _policy_from_values(
        status=default_policy,
        type_text=type_text,
        fill_text=fill_text,
    )
    return {
        "element_id": f"e_{order:03d}",
        "name": name,
        "order": order,
        "policy": policy,
        "type": type_text,
        "fill": fill_text,
        "content": _line_value(lines, "内容"),
        "style": _line_value(lines, "样式"),
        "position": _line_value(lines, "位置"),
        "relationship": _line_value(lines, "排版关系"),
        "source_refs": [f"review_text:element:{_safe_identifier(name)}"],
        "raw": text.strip(),
    }


def _field_value(text: str, field: str) -> str:
    match = re.search(rf"{re.escape(field)}=([^；\n]+)", text)
    return match.group(1).strip() if match else ""


def _line_value(lines: list[str], field: str) -> str:
    prefix = f"{field}："
    for line in lines:
        stripped = line.strip()
        if field in {"类型", "是否填充"}:
            for part in re.split(r"[；;]", stripped):
                segment = part.strip()
                if segment.startswith(prefix):
                    return segment[len(prefix) :].strip()
            continue
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return ""


def _policy_from_values(*, status: str, type_text: str, fill_text: str) -> str:
    haystack = f"{status} {type_text} {fill_text}"
    if "manual_only" in haystack or "手工" in haystack or "手填" in haystack:
        return "manual_only"
    if "生成" in haystack or "系统生成" in haystack:
        return "generated"
    if "填充" in type_text or (fill_text and "否" not in fill_text):
        return "fill"
    if "optional" in haystack:
        return "template_default_optional"
    return "fixed"


def _safe_identifier(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z_-]+", "_", value.strip())
    normalized = normalized.strip("_")
    return normalized or "unnamed"
