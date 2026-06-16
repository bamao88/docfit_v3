from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import shutil

from docx import Document

from docfit.core.io import ensure_dir, now_iso, sha256_file, write_json, write_text
from docfit.core.models import Finding, StageResult, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.harness.generated_template_inspector import (
    inspect_generated_template_docx,
    iter_visible_text_entries,
)
from docfit.harness.real_core import accepted_expected_artifact, load_template_unit_baseline
from docfit.harness.standards import StandardBundle


TEMPLATE_GENERATION_CAPABILITIES = (
    "template_generation.output_docx",
    "template_generation.actual_tree",
    "template_generation.unit_match",
    "template_generation.element_match",
    "template_generation.style_match",
    "template_generation.header_footer_match",
    "template_generation.page_rule_match",
    "template_generation.field_match",
    "template_generation.numbering_match",
    "template_generation.report",
)


def evaluate_generated_template_gap(
    bundle: StandardBundle,
    generated_template_docx: Path,
    out_dir: Path,
    *,
    stage: str = "template",
) -> StageResult:
    artifacts_dir = ensure_dir(out_dir / "artifacts")
    generated_copy = artifacts_dir / "generated_template.docx"
    tree_path = artifacts_dir / "generated_template_tree.json"
    report_json_path = artifacts_dir / "template_gap_report.json"
    report_md_path = artifacts_dir / "template_gap_report.md"
    report_docx_path = artifacts_dir / "template_gap_report.docx"

    if generated_template_docx.exists():
        if generated_template_docx.resolve() != generated_copy.resolve():
            shutil.copyfile(generated_template_docx, generated_copy)
        inspected_path = generated_copy
    else:
        inspected_path = generated_template_docx

    tree = inspect_generated_template_docx(inspected_path)
    write_json(tree_path, tree)

    baseline, baseline_findings = load_template_unit_baseline(
        bundle,
        stage=stage,
        start_index=1,
    )
    expected = accepted_expected_artifact(baseline or {})
    expected_units = expected.get("units", []) if isinstance(expected, dict) else []
    standard_path = _template_unit_contract_path(bundle)
    report = build_template_gap_report(
        bundle=bundle,
        generated_template=inspected_path,
        generated_template_source=generated_template_docx,
        standard_path=standard_path,
        expected_units=expected_units,
        tree=tree,
    )
    write_json(report_json_path, report)
    write_text(report_md_path, render_template_gap_markdown(report))
    write_template_gap_docx(report_docx_path, report)

    findings = list(baseline_findings)
    findings.extend(
        findings_from_template_gap_report(
            report,
            stage=stage,
            start_index=len(findings) + 1,
        )
    )
    status = Status(report["summary"]["blocking_status"])
    if baseline_findings:
        status = merge_statuses([status] + [finding.status for finding in baseline_findings])
    result = StageResult(
        stage,
        status,
        findings=findings,
        artifacts={
            "generated_template_tree": tree,
            "template_gap_report": report,
        },
        artifact_paths={
            "generated_template_docx": generated_copy
            if generated_copy.exists()
            else inspected_path,
            "generated_template_tree": tree_path,
            "template_gap_report_json": report_json_path,
            "template_gap_report_md": report_md_path,
            "template_gap_report_docx": report_docx_path,
        },
        coverage=template_generation_coverage(report, tree),
        blocked_at=stage if status != Status.PASS else None,
    )
    return result


def build_template_gap_report(
    *,
    bundle: StandardBundle,
    generated_template: Path,
    generated_template_source: Path,
    standard_path: Path,
    expected_units: list[dict[str, Any]],
    tree: dict[str, Any],
) -> dict[str, Any]:
    check_items: list[dict[str, Any]] = []

    if not tree.get("input_exists"):
        check_items.append(
            _check(
                "template_generation.output_docx",
                Status.UNKNOWN,
                "template_generation_output_missing",
                "缺少 generated_template.docx，被测生成模板 Word 还没有进入评测",
                str(generated_template_source),
                "missing",
                affected_ids=[bundle.school_id],
            )
        )
    elif not tree.get("input_valid_docx"):
        check_items.append(
            _check(
                "template_generation.output_docx",
                Status.FAIL,
                "template_generation_output_invalid",
                "generated_template.docx 不是有效 DOCX 包",
                "valid DOCX package",
                str(generated_template),
                evidence_refs=[str(generated_template)],
                affected_ids=[bundle.school_id],
            )
        )
    else:
        check_items.append(
            _check(
                "template_generation.output_docx",
                Status.PASS,
                "template_generation_output_docx_present",
                "generated_template.docx 已作为被测输入记录路径和 hash",
                "valid DOCX with sha256",
                tree.get("input_hashes", {}).get("generated_template_docx", ""),
                evidence_refs=[str(generated_template)],
                affected_ids=[bundle.school_id],
            )
        )

    if not expected_units:
        check_items.append(
            _check(
                "template_generation.unit_match",
                Status.UNKNOWN,
                "template_generation_expected_units_missing",
                "模板差距检查缺少 template_unit_contract.yaml 中的 expected.units",
                "expected.units",
                "missing",
                evidence_refs=[str(standard_path)],
                affected_ids=[bundle.school_id],
            )
        )
    elif tree.get("input_valid_docx"):
        check_items.extend(_compare_units(expected_units, tree))
        check_items.extend(_unknown_visible_object_checks(tree))

    summary = summarize_check_items(check_items)
    return {
        "artifact_type": "template_gap_report",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-generated-template-gap", "version": "0.1.0"},
        "created_at": now_iso(),
        "school_id": bundle.school_id,
        "template_version": bundle.template_version,
        "generated_template": {
            "path": str(generated_template),
            "source_path": str(generated_template_source),
            "sha256": tree.get("input_hashes", {}).get("generated_template_docx"),
        },
        "standard": {
            "path": str(standard_path),
            "sha256": sha256_file(standard_path) if standard_path.exists() else None,
        },
        "generated_template_tree": "generated_template_tree.json",
        "summary": summary,
        "coverage": template_generation_coverage_from_items(check_items, tree),
        "check_items": check_items,
    }


def summarize_check_items(check_items: list[dict[str, Any]]) -> dict[str, Any]:
    passed_count = sum(1 for item in check_items if item.get("status") == Status.PASS.value)
    failed_count = sum(1 for item in check_items if item.get("status") == Status.FAIL.value)
    unknown_count = sum(
        1 for item in check_items if item.get("status") == Status.UNKNOWN.value
    )
    if failed_count:
        known_status = Status.FAIL.value
    elif passed_count:
        known_status = Status.PASS.value
    else:
        known_status = Status.UNKNOWN.value

    if known_status == Status.UNKNOWN.value:
        display_status = Status.UNKNOWN.value
    elif unknown_count:
        display_status = f"{known_status} + UNKNOWN"
    else:
        display_status = known_status

    if failed_count:
        blocking_status = Status.FAIL.value
    elif unknown_count:
        blocking_status = Status.UNKNOWN.value
    else:
        blocking_status = Status.PASS.value

    return {
        "known_status": known_status,
        "display_status": display_status,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "unknown_count": unknown_count,
        "blocking_status": blocking_status,
    }


def findings_from_template_gap_report(
    report: dict[str, Any],
    *,
    stage: str = "template",
    start_index: int = 1,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    for item in report.get("check_items", []):
        status = Status(item["status"])
        if status == Status.PASS:
            continue
        findings.append(
            make_finding(
                next_index,
                stage,
                status,
                str(item.get("type", "template_generation_gap")),
                str(item.get("message", "")),
                str(item.get("expected", "")),
                str(item.get("actual", "")),
                evidence_refs=list(item.get("evidence_refs", [])),
                affected_ids=list(item.get("affected_ids", [])),
                root_cause_bucket=str(
                    item.get("root_cause_bucket", "template_generation_gap")
                ),
            )
        )
        next_index += 1
    return findings


def template_generation_coverage(
    report: dict[str, Any],
    tree: dict[str, Any],
) -> dict[str, bool]:
    return {
        f"template_generation.{key}": value
        for key, value in template_generation_coverage_from_items(
            report.get("check_items", []),
            tree,
        ).items()
    }


def template_generation_coverage_from_items(
    check_items: list[dict[str, Any]],
    tree: dict[str, Any],
) -> dict[str, bool]:
    categories = {str(item.get("category", "")) for item in check_items}
    valid_tree = bool(tree.get("input_valid_docx"))
    has_source_refs = any(
        entry.get("source_ref") for entry in iter_visible_text_entries(tree)
    )
    return {
        "output_docx": bool(tree.get("input_exists") and tree.get("input_valid_docx")),
        "actual_tree": valid_tree and has_source_refs,
        "unit_match": "unit" in categories,
        "element_match": "element" in categories,
        "style_match": "style" in categories,
        "header_footer_match": "header_footer" in categories,
        "page_rule_match": "page_rule" in categories,
        "field_match": "field" in categories,
        "numbering_match": "numbering" in categories,
        "report": bool(check_items),
    }


def render_template_gap_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"# 生成模板 Word 差距报告：{report['school_id']}",
        "",
        f"- 已知状态：{summary['known_status']}",
        f"- 展示状态：{summary['display_status']}",
        (
            "- 检查计数："
            f"PASS {summary['passed_count']} / "
            f"FAIL {summary['failed_count']} / "
            f"UNKNOWN {summary['unknown_count']}"
        ),
        f"- Gate 状态：{summary['blocking_status']}",
        f"- 生成模板 Word：{report['generated_template']['path']}",
        f"- 生成模板 hash：{report['generated_template'].get('sha256') or 'missing'}",
        f"- 标准文件：{report['standard']['path']}",
        "",
        "## 差距清单",
    ]
    for item in report.get("check_items", []):
        lines.extend(
            [
                "",
                f"### [{item['status']}] {item['check_id']}",
                "",
                item["message"],
                "",
                f"- 标准期望：{item['expected']}",
                f"- 实际结果：{item['actual']}",
                f"- 来源位置：{', '.join(item.get('evidence_refs', [])) or 'missing'}",
                f"- 下一步：{item.get('next_step', '')}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def write_template_gap_docx(path: Path, report: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    doc = Document()
    doc.add_heading(f"生成模板 Word 差距报告：{report['school_id']}", level=1)
    summary = report["summary"]
    for label, value in (
        ("已知状态", summary["known_status"]),
        ("展示状态", summary["display_status"]),
        ("Gate 状态", summary["blocking_status"]),
        (
            "检查计数",
            (
                f"PASS {summary['passed_count']} / "
                f"FAIL {summary['failed_count']} / "
                f"UNKNOWN {summary['unknown_count']}"
            ),
        ),
        ("生成模板 Word", report["generated_template"]["path"]),
        ("生成模板 hash", report["generated_template"].get("sha256") or "missing"),
        ("标准文件", report["standard"]["path"]),
    ):
        doc.add_paragraph(f"{label}：{value}")
    doc.add_heading("差距清单", level=2)
    for item in report.get("check_items", []):
        doc.add_heading(f"[{item['status']}] {item['check_id']}", level=3)
        doc.add_paragraph(item["message"])
        doc.add_paragraph(f"标准期望：{item['expected']}")
        doc.add_paragraph(f"实际结果：{item['actual']}")
        doc.add_paragraph(
            "来源位置：" + (", ".join(item.get("evidence_refs", [])) or "missing")
        )
        doc.add_paragraph(f"下一步：{item.get('next_step', '')}")
    doc.save(path)


def _compare_units(
    expected_units: list[dict[str, Any]],
    tree: dict[str, Any],
) -> list[dict[str, Any]]:
    entries = iter_visible_text_entries(tree)
    checks: list[dict[str, Any]] = []
    unit_first_orders: list[tuple[str, int]] = []
    unit_matched_orders: dict[str, list[int]] = {}
    for unit in expected_units:
        unit_id = str(unit.get("unit_id") or "unknown_unit")
        element_checks, matched_orders = _compare_elements(unit, entries, tree)
        checks.extend(element_checks)
        unit_matched_orders[unit_id] = matched_orders
        if matched_orders:
            first_order = min(matched_orders)
            unit_first_orders.append((unit_id, first_order))
            checks.append(
                _check(
                    "template_generation.unit_match",
                    Status.PASS,
                    "template_generation_unit_found",
                    f"生成模板 Word 中找到单元 {unit_id} 的可见来源证据",
                    unit_id,
                    f"first_source_order={first_order}",
                    category="unit",
                    evidence_refs=_matched_evidence(element_checks),
                    affected_ids=[unit_id],
                )
            )
        else:
            status = (
                Status.UNKNOWN
                if unit.get("status") == "template_default_optional"
                else Status.FAIL
            )
            checks.append(
                _check(
                    "template_generation.unit_match",
                    status,
                    "template_generation_unit_missing",
                    f"生成模板 Word 中没有找到单元 {unit_id} 的可见来源证据",
                    unit_id,
                    "missing",
                    category="unit",
                    affected_ids=[unit_id],
                    next_step="如果生成逻辑应输出该单元，修模板生成；如果解析器无法识别，补生成模板解析器。",
                )
            )
    for unit in expected_units:
        unit_id = str(unit.get("unit_id") or "unknown_unit")
        matched_orders = unit_matched_orders.get(unit_id, [])
        checks.extend(_header_footer_checks(unit, tree, matched_orders))
        checks.extend(_page_rule_checks(unit, tree, matched_orders, unit_first_orders))
    checks.extend(
        _field_checks(expected_units, tree, unit_matched_orders, unit_first_orders)
    )
    checks.extend(
        _numbering_checks(
            expected_units,
            tree,
            unit_matched_orders,
            unit_first_orders,
        )
    )
    if len(unit_first_orders) >= 2:
        ordered = sorted(unit_first_orders, key=lambda item: item[1])
        checks.append(
            _check(
                "template_generation.unit_match",
                Status.PASS if ordered == unit_first_orders else Status.FAIL,
                (
                    "template_generation_unit_order_ok"
                    if ordered == unit_first_orders
                    else "template_generation_unit_order_mismatch"
                ),
                "生成模板 Word 的已识别单元顺序与标准顺序对齐",
                repr([unit_id for unit_id, _order in unit_first_orders]),
                repr([unit_id for unit_id, _order in ordered]),
                category="unit",
                affected_ids=[unit_id for unit_id, _order in unit_first_orders],
                next_step="若顺序不一致，修模板生成的单元输出顺序。",
            )
        )
    return checks


def _compare_elements(
    unit: dict[str, Any],
    entries: list[dict[str, Any]],
    tree: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[int]]:
    unit_id = str(unit.get("unit_id") or "unknown_unit")
    checks: list[dict[str, Any]] = []
    matched_orders: list[int] = []
    for element in unit.get("elements", []):
        element_id = str(element.get("element_id") or "unknown_element")
        affected_id = f"{unit_id}.{element_id}"
        needles = _candidate_needles(element)
        matches = _find_matches(entries, needles)
        policy = str(element.get("policy") or "")
        if matches:
            matched_orders.extend(int(match.get("order", 0)) for match in matches)
            checks.append(
                _check(
                    "template_generation.element_match",
                    Status.PASS,
                    "template_generation_element_found",
                    f"生成模板 Word 中找到元素 {affected_id} 的可见文本来源",
                    " / ".join(needles),
                    _preview(matches[0].get("text", "")),
                    category="element",
                    evidence_refs=[match.get("source_ref", "") for match in matches[:3]],
                    affected_ids=[affected_id],
                )
            )
            checks.append(_style_check(unit_id, element, matches[0]))
            continue

        if policy in {"fixed", "manual_only"}:
            checks.append(
                _check(
                    "template_generation.element_match",
                    Status.FAIL,
                    "template_generation_element_missing",
                    f"生成模板 Word 缺少标准要求保留的元素 {affected_id}",
                    element.get("content") or element.get("name") or affected_id,
                    "missing",
                    category="element",
                    affected_ids=[affected_id],
                    next_step="修模板生成逻辑，保留该固定内容或手工填写位置。",
                )
            )
        elif policy == "generated":
            field_status = (
                "field parsed"
                if _has_generated_field(tree, element)
                else "no field parsed"
            )
            checks.append(
                _check(
                    "template_generation.element_match",
                    Status.UNKNOWN,
                    "template_generation_generated_element_source_unknown",
                    f"生成元素 {affected_id} 需要可检查的 Word 字段或等价占位",
                    element.get("content") or element.get("name") or affected_id,
                    field_status,
                    category="element",
                    affected_ids=[affected_id],
                    next_step="补字段到单元/元素的绑定检查，或修模板生成逻辑输出字段。",
                )
            )
        else:
            checks.append(
                _check(
                    "template_generation.element_match",
                    Status.UNKNOWN,
                    "template_generation_element_source_unknown",
                    f"元素 {affected_id} 需要可写位置或生成规则，但当前解析树无法证明",
                    element.get("content") or element.get("name") or affected_id,
                    "no matched Word source",
                    category="element",
                    affected_ids=[affected_id],
                    next_step="补解析器对可写位置、content control、字段或占位符的识别。",
                )
            )
    return checks, matched_orders


def _field_checks(
    expected_units: list[dict[str, Any]],
    tree: dict[str, Any],
    unit_matched_orders: dict[str, list[int]],
    unit_first_orders: list[tuple[str, int]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    requirements = _field_requirements(expected_units)
    if not requirements:
        return [
            _check(
                "template_generation.field_match",
                Status.PASS,
                "template_generation_no_required_fields",
                "模板标准没有声明必须检查的 Word 生成字段",
                "no generated field requirements",
                "no generated field requirements",
                category="field",
            )
        ]

    fields = tree.get("data", {}).get("fields", [])
    for requirement in requirements:
        evaluation = _evaluate_field_requirement(
            requirement,
            fields,
            unit_matched_orders.get(requirement["unit_id"], []),
            unit_first_orders,
        )
        checks.append(
            _check(
                "template_generation.field_match",
                evaluation["status"],
                evaluation["type"],
                evaluation["message"],
                requirement["expected"],
                evaluation["actual"],
                category="field",
                evidence_refs=evaluation["evidence_refs"],
                affected_ids=[requirement["affected_id"]],
                next_step=evaluation["next_step"],
            )
        )
    return checks


def _field_requirements(expected_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for unit in expected_units:
        unit_id = str(unit.get("unit_id") or "unknown_unit")
        explicit_element_added = False
        for element in unit.get("elements", []):
            element_id = str(element.get("element_id") or "unknown_element")
            element_text = _field_requirement_text(element)
            kind = _expected_element_field_kind(element_text)
            if not kind:
                continue
            if kind != "SEQ" and (
                element.get("policy") != "generated"
                or _is_generated_result_element(element)
            ):
                continue
            explicit_element_added = True
            requirements.append(
                {
                    "unit_id": unit_id,
                    "affected_id": f"{unit_id}.{element_id}.field",
                    "kind": kind,
                    "sequence_label": _expected_sequence_label(element_text),
                    "context_text": element_text,
                    "expected": _field_expected_summary(kind, element_text),
                    "toc_range": _expected_toc_range(element_text),
                    "allows_equivalent": _allows_equivalent_field_generation(
                        kind,
                        element_text,
                    ),
                    "source_refs": element.get("source_refs", []),
                }
            )
        if explicit_element_added:
            continue
        unit_text = _field_requirement_text(unit)
        kind = _expected_unit_field_kind(unit_text)
        if kind:
            requirements.append(
                {
                    "unit_id": unit_id,
                    "affected_id": f"{unit_id}.field",
                    "kind": kind,
                    "sequence_label": _expected_sequence_label(unit_text),
                    "context_text": unit_text,
                    "expected": _field_expected_summary(kind, unit_text),
                    "toc_range": _expected_toc_range(unit_text),
                    "allows_equivalent": _allows_equivalent_field_generation(
                        kind,
                        unit_text,
                    ),
                    "source_refs": unit.get("source_refs", []),
                }
            )
    return requirements


def _evaluate_field_requirement(
    requirement: dict[str, Any],
    fields: list[dict[str, Any]],
    matched_orders: list[int],
    unit_first_orders: list[tuple[str, int]],
) -> dict[str, Any]:
    unit_id = requirement["unit_id"]
    kind = requirement["kind"]
    if not matched_orders:
        return {
            "status": Status.UNKNOWN,
            "type": "template_generation_field_unverified",
            "message": f"单元 {unit_id} 未绑定到 Word 来源，无法检查字段",
            "actual": "unit source not matched",
            "evidence_refs": requirement.get("source_refs", []),
            "next_step": "先修单元/元素匹配，再检查字段是否出现在该单元范围内。",
        }

    start_order, end_order = _field_unit_bounds(
        requirement["unit_id"],
        matched_orders,
        unit_first_orders,
    )
    matching_kind_fields = [
        field for field in fields if str(field.get("field_type", "")).upper() == kind
    ]
    candidate_fields = _field_candidates_for_requirement(
        requirement,
        matching_kind_fields,
    )
    in_unit_fields = [
        field
        for field in candidate_fields
        if _field_overlaps_unit(field, start_order, end_order)
        or _field_semantically_matches_requirement(requirement, field)
    ]
    if in_unit_fields:
        mismatch = _field_parameter_mismatch(requirement, in_unit_fields)
        if mismatch:
            status = (
                Status.UNKNOWN
                if requirement.get("allows_equivalent")
                else Status.FAIL
            )
            return {
                "status": status,
                "type": (
                    "template_generation_field_unverified"
                    if status == Status.UNKNOWN
                    else "template_generation_field_mismatch"
                ),
                "message": f"单元 {unit_id} 找到 {kind} 字段，但字段参数与标准不一致",
                "actual": mismatch,
                "evidence_refs": _field_refs(in_unit_fields),
                "next_step": (
                    "补等价目录机制解析，或修模板生成逻辑输出标准 TOC 参数。"
                    if status == Status.UNKNOWN
                    else "修模板生成逻辑，输出标准要求的 Word 字段参数。"
                ),
            }
        return {
            "status": Status.PASS,
            "type": "template_generation_field_match",
            "message": f"单元 {unit_id} 的 {kind} 字段已绑定到 Word 来源",
            "actual": _field_actual_summary(in_unit_fields),
            "evidence_refs": _field_refs(in_unit_fields),
            "next_step": "none",
        }

    if matching_kind_fields:
        return {
            "status": Status.FAIL,
            "type": "template_generation_field_out_of_unit",
            "message": f"模板中存在 {kind} 字段，但没有绑定到单元 {unit_id}",
            "actual": _field_actual_summary(matching_kind_fields),
            "evidence_refs": _field_refs(matching_kind_fields),
            "next_step": "修模板生成逻辑，把字段放回对应单元；或补更准确的单元边界解析。",
        }

    if requirement.get("allows_equivalent"):
        return {
            "status": Status.UNKNOWN,
            "type": "template_generation_field_unverified",
            "message": f"单元 {unit_id} 允许 Word 字段或等价生成机制，但当前未解析到 {kind} 字段",
            "actual": "no Word field parsed; equivalent mechanism not parsed",
            "evidence_refs": requirement.get("source_refs", []),
            "next_step": "补等价目录生成机制的确定性解析，或修模板生成逻辑输出 Word 字段。",
        }

    return {
        "status": Status.FAIL,
        "type": "template_generation_field_missing",
        "message": f"单元 {unit_id} 缺少标准要求的 {kind} 字段",
        "actual": "no matching Word field parsed",
        "evidence_refs": requirement.get("source_refs", []),
        "next_step": "修模板生成逻辑输出字段，或补字段解析器对该 Word 字段的识别。",
    }


def _field_requirement_text(item: dict[str, Any]) -> str:
    values = [
        str(item.get(field, ""))
        for field in (
            "name",
            "source",
            "handling",
            "content",
            "position",
            "relationship",
            "raw",
            "element_order",
            "layout_relation",
        )
    ]
    return " ".join(values)


def _is_generated_result_element(element: dict[str, Any]) -> bool:
    text = _normalize_text(_field_requirement_text(element))
    return (
        "生成结果" in text
        or "结果条目" in text
        or "Word 更新域后生成" in text
    )


def _expected_element_field_kind(text: str) -> str | None:
    normalized = text.upper()
    if _is_sequence_field_requirement(text):
        return "SEQ"
    if (
        "TOC" in normalized
        and ("字段" in text or "目录生成机制" in text or "自动目录" in text)
    ):
        return "TOC"
    if "自动目录字段" in text or "目录生成机制" in text:
        return "TOC"
    if "页码字段" in text or re.search(r"\b(NUM)?PAGES?\b", normalized):
        return "PAGE"
    return None


def _expected_unit_field_kind(text: str) -> str | None:
    normalized = text.upper()
    if "TOC" in normalized and ("字段" in text or "自动目录" in text):
        return "TOC"
    if (
        "Word 自动目录" in text
        or "Word 目录字段" in text
        or "Word 图目录" in text
        or "Word 表目录" in text
    ):
        return "TOC"
    if "页码字段" in text or re.search(r"\b(NUM)?PAGES?\b", normalized):
        return "PAGE"
    return None


def _field_expected_summary(kind: str, text: str) -> str:
    if kind == "TOC":
        toc_range = _expected_toc_range(text)
        return f"Word TOC field{f' with range {toc_range}' if toc_range else ''}"
    if kind == "PAGE":
        return "Word PAGE/NUMPAGES field"
    if kind == "SEQ":
        label = _expected_sequence_label(text)
        if label:
            return f"Word SEQ field for {label} generated numbering"
        return "Word SEQ field"
    return f"Word {kind} field"


def _is_sequence_field_requirement(text: str) -> bool:
    if not _expected_sequence_label(text):
        return False
    normalized = text.upper()
    if "目录" in text:
        return False
    if "SEQ" in normalized:
        return True
    if any(token in text for token in ("域代码", "更新域", "Word 字段", "字段")):
        return True
    return any(token in text for token in ("生成图编号", "生成表编号", "生成公式编号"))


def _expected_sequence_label(text: str) -> str | None:
    if any(token in text for token in ("生成公式编号", "公式编号", "公式序号")):
        return "公式"
    if any(token in text for token in ("生成表编号", "表号", "表名", "表题")):
        return "表"
    if any(token in text for token in ("生成图编号", "图号", "图名", "图题")):
        return "图"
    return None


def _expected_toc_range(text: str) -> str | None:
    explicit = re.search(r"\\o\s+\"([^\"]+)\"", text)
    if explicit:
        return explicit.group(1)
    range_match = re.search(r"(\d+)\s*-\s*(\d+)\s*级", text)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"
    level_match = re.search(r"(?:层级到|目录层级到|到)\s*(\d+)\s*级", text)
    if level_match:
        return f"1-{level_match.group(1)}"
    return None


def _allows_equivalent_generation(text: str) -> bool:
    return "等价" in text or "可使用" in text or "可用" in text


def _allows_equivalent_field_generation(kind: str, text: str) -> bool:
    if _allows_equivalent_generation(text):
        return True
    if kind != "SEQ":
        return False
    if any(token in text for token in ("域代码", "更新域", "Word 字段", "SEQ")):
        return False
    return "生成" in text and "编号" in text


def _field_overlaps_unit(
    field: dict[str, Any],
    start_order: int,
    end_order: int,
) -> bool:
    paragraph_index = field.get("paragraph_index")
    if paragraph_index is None:
        return False
    field_start = int(paragraph_index)
    field_end = int(field.get("end_paragraph_index") or field_start)
    upper_bound = max(end_order + 8, start_order + 120)
    return field_end >= start_order - 2 and field_start <= upper_bound


def _field_candidates_for_requirement(
    requirement: dict[str, Any],
    fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if requirement.get("kind") == "SEQ":
        sequence_label = requirement.get("sequence_label")
        if not sequence_label:
            return fields
        labeled = [
            field
            for field in fields
            if _sequence_label_matches(
                _field_sequence_label(field),
                str(sequence_label),
            )
        ]
        return labeled or fields
    if requirement.get("kind") != "TOC":
        return fields
    toc_range = requirement.get("toc_range")
    if toc_range:
        expected_fragment = f'\\o "{toc_range}"'
        ranged = [
            field
            for field in fields
            if expected_fragment in str(field.get("instruction", ""))
        ]
        if ranged:
            return ranged
    context_text = str(requirement.get("context_text", ""))
    if "图目录" in context_text or "figure" in requirement.get("unit_id", ""):
        themed = [
            field
            for field in fields
            if "图" in str(field.get("instruction", ""))
        ]
        if themed:
            return themed
    if "表目录" in context_text or "table" in requirement.get("unit_id", ""):
        themed = [
            field
            for field in fields
            if "表" in str(field.get("instruction", ""))
        ]
        if themed:
            return themed
    if requirement.get("unit_id") == "toc":
        outline_fields = [
            field
            for field in fields
            if "\\o" in str(field.get("instruction", ""))
        ]
        if outline_fields:
            return outline_fields
    return fields


def _field_semantically_matches_requirement(
    requirement: dict[str, Any],
    field: dict[str, Any],
) -> bool:
    instruction = str(field.get("instruction", ""))
    if requirement.get("kind") == "SEQ":
        sequence_label = requirement.get("sequence_label")
        return bool(
            sequence_label
            and _sequence_label_matches(
                _field_sequence_label(field),
                str(sequence_label),
            )
        )
    if requirement.get("kind") != "TOC":
        return False
    toc_range = requirement.get("toc_range")
    if toc_range and f'\\o "{toc_range}"' in instruction:
        return True
    context_text = str(requirement.get("context_text", ""))
    if ("图目录" in context_text or "figure" in requirement.get("unit_id", "")) and (
        "图" in instruction
    ):
        return True
    if ("表目录" in context_text or "table" in requirement.get("unit_id", "")) and (
        "表" in instruction
    ):
        return True
    return False


def _field_unit_bounds(
    unit_id: str,
    matched_orders: list[int],
    unit_first_orders: list[tuple[str, int]],
) -> tuple[int, int]:
    start_order = min(matched_orders)
    fallback_end = max(matched_orders)
    ordered_unit_ids = [item[0] for item in unit_first_orders]
    if unit_id not in ordered_unit_ids:
        return start_order, fallback_end
    unit_index = ordered_unit_ids.index(unit_id)
    later_starts = [
        order
        for _next_unit_id, order in unit_first_orders[unit_index + 1 :]
        if order > start_order
    ]
    if later_starts:
        return start_order, min(later_starts) - 1
    return start_order, fallback_end + 8


def _field_parameter_mismatch(
    requirement: dict[str, Any],
    fields: list[dict[str, Any]],
) -> str:
    toc_range = requirement.get("toc_range")
    if requirement.get("kind") == "TOC" and toc_range:
        expected_fragment = f'\\o "{toc_range}"'
        if not any(
            expected_fragment in str(field.get("instruction", ""))
            for field in fields
        ):
            return (
                f"expected {expected_fragment}; actual "
                f"{_field_actual_summary(fields)}"
            )
    if requirement.get("kind") == "SEQ":
        sequence_label = requirement.get("sequence_label")
        if sequence_label and not any(
            _sequence_label_matches(
                _field_sequence_label(field),
                str(sequence_label),
            )
            for field in fields
        ):
            return (
                f"expected SEQ {sequence_label}; actual "
                f"{_field_actual_summary(fields)}"
            )
    return ""


def _field_sequence_label(field: dict[str, Any]) -> str:
    instruction = str(field.get("instruction", ""))
    match = re.search(r"\bSEQ\s+([^\\\s]+)", instruction, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip('"')


def _sequence_label_matches(actual: str, expected: str) -> bool:
    if actual == expected:
        return True
    if expected == "公式" and actual.lower() in {"equation", "formula"}:
        return True
    return False


def _field_actual_summary(fields: list[dict[str, Any]]) -> str:
    return "; ".join(
        str(field.get("instruction") or field.get("field_type") or "unknown field")
        for field in fields[:5]
    )


def _field_refs(fields: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for field in fields:
        refs.append(str(field.get("source_ref", "")))
        end_ref = field.get("end_source_ref")
        if end_ref:
            refs.append(str(end_ref))
    return [ref for ref in refs if ref]


def _numbering_checks(
    expected_units: list[dict[str, Any]],
    tree: dict[str, Any],
    unit_matched_orders: dict[str, list[int]],
    unit_first_orders: list[tuple[str, int]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    requirements = _numbering_requirements(expected_units)
    if not requirements:
        return [
            _check(
                "template_generation.numbering_match",
                Status.PASS,
                "template_generation_no_numbering_requirements",
                "模板标准没有声明必须用 Word 自动编号证明的规则",
                "no Word automatic numbering requirements",
                "no Word automatic numbering requirements",
                category="numbering",
            )
        ]
    numbering_refs = tree.get("data", {}).get("numbering_refs", [])
    numbering_definitions = tree.get("data", {}).get("numbering_definitions", [])
    for requirement in requirements:
        evaluation = _evaluate_numbering_requirement(
            requirement,
            numbering_refs,
            numbering_definitions,
            unit_matched_orders.get(requirement["unit_id"], []),
            unit_first_orders,
        )
        checks.append(
            _check(
                "template_generation.numbering_match",
                evaluation["status"],
                evaluation["type"],
                evaluation["message"],
                requirement["expected"],
                evaluation["actual"],
                category="numbering",
                evidence_refs=evaluation["evidence_refs"],
                affected_ids=[requirement["affected_id"]],
                next_step=evaluation["next_step"],
            )
        )
    return checks


def _numbering_requirements(
    expected_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for unit in expected_units:
        unit_id = str(unit.get("unit_id") or "unknown_unit")
        for element in unit.get("elements", []):
            text = _numbering_item_text(element)
            if not _requires_word_numbering(text):
                continue
            element_id = str(element.get("element_id") or "unknown_element")
            expected_formats = _expected_numbering_formats(text)
            requirements.append(
                {
                    "unit_id": unit_id,
                    "element_id": element_id,
                    "affected_id": f"{unit_id}.{element_id}.numbering",
                    "context_text": text,
                    "expected_formats": expected_formats,
                    "expected": _numbering_expected_summary(
                        expected_formats,
                        text,
                    ),
                    "source_refs": element.get("source_refs", []),
                }
            )
    return requirements


def _evaluate_numbering_requirement(
    requirement: dict[str, Any],
    numbering_refs: list[dict[str, Any]],
    numbering_definitions: list[dict[str, Any]],
    matched_orders: list[int],
    unit_first_orders: list[tuple[str, int]],
) -> dict[str, Any]:
    unit_id = requirement["unit_id"]
    if not numbering_refs and not numbering_definitions:
        return {
            "status": Status.FAIL,
            "type": "template_generation_numbering_missing",
            "message": f"单元 {unit_id} 要求 Word 自动编号，但生成模板没有 OOXML 编号定义",
            "actual": "no word/numbering.xml definitions or paragraph numPr parsed",
            "evidence_refs": requirement.get("source_refs", []),
            "next_step": "修模板生成逻辑，写入 Word 自动编号定义和对应段落样式。",
        }

    if not matched_orders:
        return {
            "status": Status.UNKNOWN,
            "type": "template_generation_numbering_unverified",
            "message": f"单元 {unit_id} 未绑定到 Word 来源，无法检查自动编号",
            "actual": _numbering_actual_summary(numbering_refs[:5])
            or _numbering_definition_summary(numbering_definitions[:5]),
            "evidence_refs": _numbering_evidence_refs(numbering_refs[:5]),
            "next_step": "先修单元/元素匹配，再检查编号段落是否出现在该单元范围内。",
        }

    start_order, end_order = _field_unit_bounds(
        requirement["unit_id"],
        matched_orders,
        unit_first_orders,
    )
    bounded_refs = [
        ref
        for ref in numbering_refs
        if _numbering_ref_overlaps_unit(ref, start_order, end_order)
    ]
    expected_formats = requirement.get("expected_formats", [])
    search_refs = bounded_refs or numbering_refs
    if expected_formats:
        matched_by_format = {
            expected: [
                ref
                for ref in search_refs
                if _numbering_format_matches(expected, ref)
            ]
            for expected in expected_formats
        }
        missing_formats = [
            expected
            for expected, refs in matched_by_format.items()
            if not refs
        ]
        if not missing_formats:
            matched_refs = [
                refs[0]
                for refs in matched_by_format.values()
                if refs
            ]
            return {
                "status": Status.PASS,
                "type": "template_generation_numbering_match",
                "message": f"单元 {unit_id} 的 Word 自动编号格式已绑定到 OOXML 来源",
                "actual": _numbering_actual_summary(matched_refs),
                "evidence_refs": _numbering_evidence_refs(matched_refs),
                "next_step": "none",
            }
        if bounded_refs:
            return {
                "status": Status.FAIL,
                "type": "template_generation_numbering_mismatch",
                "message": f"单元 {unit_id} 的 Word 自动编号格式与标准不一致",
                "actual": (
                    f"missing formats={missing_formats}; "
                    f"actual {_numbering_actual_summary(bounded_refs[:5])}"
                ),
                "evidence_refs": _numbering_evidence_refs(bounded_refs[:5]),
                "next_step": "修模板生成逻辑，确保编号格式、层级和段落样式符合标准。",
            }

    if bounded_refs:
        has_resolved_definition = any(
            ref.get("num_fmt") or ref.get("lvl_text")
            for ref in bounded_refs
        )
        return {
            "status": Status.PASS if has_resolved_definition else Status.UNKNOWN,
            "type": (
                "template_generation_numbering_match"
                if has_resolved_definition
                else "template_generation_numbering_unverified"
            ),
            "message": f"单元 {unit_id} 的 Word 自动编号段落已绑定到单元范围",
            "actual": _numbering_actual_summary(bounded_refs[:5]),
            "evidence_refs": _numbering_evidence_refs(bounded_refs[:5]),
            "next_step": (
                "none"
                if has_resolved_definition
                else "补 numbering.xml 层级定义解析，证明编号格式。"
            ),
        }

    matching_definitions = _numbering_definitions_matching_formats(
        numbering_definitions,
        expected_formats,
    )
    if matching_definitions:
        return {
            "status": Status.UNKNOWN,
            "type": "template_generation_numbering_unverified",
            "message": f"单元 {unit_id} 有匹配的编号定义，但当前还不能绑定到单元段落",
            "actual": _numbering_definition_summary(matching_definitions[:5]),
            "evidence_refs": [
                str(item.get("source_ref", ""))
                for item in matching_definitions[:5]
                if item.get("source_ref")
            ],
            "next_step": "补该单元的可见来源或段落样式绑定，确认编号定义实际用于该单元。",
        }

    return {
        "status": Status.FAIL,
        "type": "template_generation_numbering_missing",
        "message": f"单元 {unit_id} 缺少标准要求的 Word 自动编号段落",
        "actual": (
            f"unit bounds p[{start_order}]-p[{end_order}] have no numbering refs"
        ),
        "evidence_refs": requirement.get("source_refs", []),
        "next_step": "修模板生成逻辑，把自动编号样式应用到该单元对应段落。",
    }


def _numbering_item_text(item: dict[str, Any]) -> str:
    values = [
        str(item.get(field, ""))
        for field in (
            "name",
            "type",
            "content",
            "position",
            "relationship",
            "raw",
        )
    ]
    return " ".join(values)


def _requires_word_numbering(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized or "编号" not in normalized:
        return False
    non_numbering_mechanisms = (
        "脚注",
        "图编号",
        "表编号",
        "公式编号",
        "图号",
        "表号",
        "题注",
        "域代码",
        "目录条目",
        "点引导线",
    )
    if any(marker in normalized for marker in non_numbering_mechanisms):
        return False
    strong_markers = (
        "Word 列表编号",
        "由 Word 列表编号生成",
        "模板编号规则生成",
        "编号由模板生成",
        "章号由模板生成",
        "Word 自动编号",
        "自动编号",
    )
    if any(marker in normalized for marker in strong_markers):
        return True
    return "编号生成" in normalized and (
        "标题" in normalized or "章" in normalized
    )


def _expected_numbering_formats(text: str) -> list[str]:
    formats: list[str] = []
    for match in re.finditer(r"(?:四级|五级)?格式[=＝]\s*([^；。\n]+)", text):
        normalized = _normalize_expected_numbering_format(match.group(1))
        if normalized:
            formats.append(normalized)
    return _dedupe(formats)


def _normalize_expected_numbering_format(value: str) -> str:
    normalized = value.strip().replace("％", "%")
    if "+" in normalized:
        base, suffix = normalized.split("+", 1)
        normalized = base.strip()
        if "半角空格" in suffix:
            normalized += " "
    return normalized.strip("；。")


def _numbering_expected_summary(
    expected_formats: list[str],
    text: str,
) -> str:
    if expected_formats:
        return "Word automatic numbering formats: " + ", ".join(
            repr(item) for item in expected_formats
        )
    if "列表" in text:
        return "Word automatic list numbering"
    return "Word automatic numbering bound to paragraph style"


def _numbering_ref_overlaps_unit(
    ref: dict[str, Any],
    start_order: int,
    end_order: int,
) -> bool:
    paragraph_index = ref.get("paragraph_index")
    if paragraph_index is None:
        return False
    paragraph_index = int(paragraph_index)
    upper_bound = max(end_order + 8, start_order + 120)
    return start_order - 2 <= paragraph_index <= upper_bound


def _numbering_format_matches(expected: str, ref: dict[str, Any]) -> bool:
    actual = str(ref.get("lvl_text") or "")
    if not actual:
        return False
    return _normalize_numbering_format_for_compare(
        expected,
    ) == _normalize_numbering_format_for_compare(actual)


def _normalize_numbering_format_for_compare(value: str) -> str:
    return value.replace("％", "%").strip()


def _numbering_definitions_matching_formats(
    numbering_definitions: list[dict[str, Any]],
    expected_formats: list[str],
) -> list[dict[str, Any]]:
    if not expected_formats:
        return numbering_definitions
    return [
        definition
        for definition in numbering_definitions
        if any(
            _numbering_format_matches(expected, definition)
            for expected in expected_formats
        )
    ]


def _numbering_actual_summary(refs: list[dict[str, Any]]) -> str:
    return "; ".join(
        (
            f"p[{ref.get('paragraph_index')}]"
            f" style={ref.get('paragraph_style_id') or 'missing'}"
            f" numId={ref.get('num_id') or 'missing'}"
            f" ilvl={ref.get('ilvl') or 'missing'}"
            f" fmt={ref.get('num_fmt') or 'missing'}"
            f" text={ref.get('lvl_text') or 'missing'}"
        )
        for ref in refs
    )


def _numbering_definition_summary(definitions: list[dict[str, Any]]) -> str:
    return "; ".join(
        (
            f"numId={definition.get('num_id') or 'missing'}"
            f" ilvl={definition.get('ilvl') or 'missing'}"
            f" fmt={definition.get('num_fmt') or 'missing'}"
            f" text={definition.get('lvl_text') or 'missing'}"
            f" pStyle={definition.get('paragraph_style_id') or 'missing'}"
        )
        for definition in definitions
    )


def _numbering_evidence_refs(refs: list[dict[str, Any]]) -> list[str]:
    evidence_refs: list[str] = []
    for ref in refs:
        if ref.get("source_ref"):
            evidence_refs.append(str(ref.get("source_ref")))
        evidence_refs.extend(str(item) for item in ref.get("source_refs", []))
        if ref.get("definition_source_ref"):
            evidence_refs.append(str(ref.get("definition_source_ref")))
    return _dedupe(evidence_refs)


def _style_check(
    unit_id: str,
    element: dict[str, Any],
    match: dict[str, Any],
) -> dict[str, Any]:
    element_id = str(element.get("element_id") or "unknown_element")
    expected_style = _normalize_text(element.get("style"))
    if not expected_style:
        return _check(
            "template_generation.style_match",
            Status.PASS,
            "template_generation_style_not_required",
            f"元素 {unit_id}.{element_id} 没有声明必须检查的样式字段",
            "no required style",
            "no required style",
            category="style",
            affected_ids=[f"{unit_id}.{element_id}.style"],
        )
    actual_style = _style_actual_summary(match)
    style_result = _compare_style_details(expected_style, match)
    if _style_matches(expected_style, _normalize_text(match.get("style"))):
        status = Status.PASS
        type_ = "template_generation_style_match"
        message = f"元素 {unit_id}.{element_id} 的段落样式名称与标准可比对"
        next_step = "none"
    elif style_result["mismatches"]:
        status = Status.FAIL
        type_ = "template_generation_style_mismatch"
        message = f"元素 {unit_id}.{element_id} 的 OOXML 样式属性不符合标准"
        next_step = "修模板生成样式，或修解析器的样式继承规则。"
    elif style_result["matched"] and not style_result["unknown"]:
        status = Status.PASS
        type_ = "template_generation_style_match"
        message = f"元素 {unit_id}.{element_id} 的 OOXML 样式属性符合已声明标准"
        next_step = "none"
    else:
        status = Status.UNKNOWN
        type_ = "template_generation_style_unverified"
        message = f"元素 {unit_id}.{element_id} 的样式细节还不能由当前解析器完整证明"
        next_step = "补 OOXML 样式解析，比较字体、字号、加粗、对齐、缩进、段距和行距。"
    return _check(
        "template_generation.style_match",
        status,
        type_,
        message,
        expected_style,
        actual_style or "style details unavailable",
        category="style",
        evidence_refs=[match.get("source_ref", "")],
        affected_ids=[f"{unit_id}.{element_id}.style"],
        next_step=next_step,
    )


def _header_footer_checks(
    unit: dict[str, Any],
    tree: dict[str, Any],
    matched_orders: list[int],
) -> list[dict[str, Any]]:
    unit_id = str(unit.get("unit_id") or "unknown_unit")
    header_footer = unit.get("header_footer") or {}
    if not isinstance(header_footer, dict):
        return []
    checks: list[dict[str, Any]] = []
    header_rule = _normalize_text(header_footer.get("header"))
    page_rule = _normalize_text(header_footer.get("page_number"))
    context = _header_footer_context(tree, matched_orders)

    if header_rule:
        header_check = _evaluate_header_rule(
            unit_id,
            header_rule,
            context,
        )
        checks.append(
            _check(
                "template_generation.header_footer_match",
                header_check["status"],
                header_check["type"],
                header_check["message"],
                header_rule,
                header_check["actual"],
                category="header_footer",
                evidence_refs=header_check["evidence_refs"],
                affected_ids=[f"{unit_id}.header_footer.header"],
                next_step=header_check["next_step"],
            )
        )
    if page_rule:
        page_check = _evaluate_page_number_rule(
            unit_id,
            page_rule,
            context,
        )
        checks.append(
            _check(
                "template_generation.header_footer_match",
                page_check["status"],
                page_check["type"],
                page_check["message"],
                page_rule,
                page_check["actual"],
                category="header_footer",
                evidence_refs=page_check["evidence_refs"],
                affected_ids=[f"{unit_id}.header_footer.page_number"],
                next_step=page_check["next_step"],
            )
        )
    return checks


def _header_footer_context(
    tree: dict[str, Any],
    matched_orders: list[int],
) -> dict[str, Any]:
    if not matched_orders:
        return {
            "section": None,
            "header_parts": [],
            "footer_parts": [],
            "page_fields": [],
            "page_numbering": {},
            "evidence_refs": [],
        }
    first_order = min(matched_orders)
    section = _section_for_order(tree, first_order)
    if not section:
        return {
            "section": None,
            "header_parts": [],
            "footer_parts": [],
            "page_fields": [],
            "page_numbering": {},
            "evidence_refs": [],
        }
    part_by_name = {
        part.get("part_name"): part
        for part in tree.get("data", {}).get("headers_footers", [])
    }
    header_part_names = _section_part_names(section, "header")
    footer_part_names = _section_part_names(section, "footer")
    header_parts = [
        part_by_name[name]
        for name in header_part_names
        if name in part_by_name
    ]
    footer_parts = [
        part_by_name[name]
        for name in footer_part_names
        if name in part_by_name
    ]
    page_fields = [
        field
        for field in tree.get("data", {}).get("fields", [])
        if field.get("part_name") in footer_part_names
        and (
            "PAGE" in str(field.get("instruction", "")).upper()
            or "NUMPAGES" in str(field.get("instruction", "")).upper()
        )
    ]
    return {
        "section": section,
        "header_parts": header_parts,
        "footer_parts": footer_parts,
        "page_fields": page_fields,
        "page_numbering": section.get("page_numbering", {}),
        "evidence_refs": [
            section.get("source_ref", ""),
            *[ref.get("source_ref", "") for ref in section.get("effective_references", [])],
        ],
    }


def _section_for_order(tree: dict[str, Any], order: int) -> dict[str, Any] | None:
    sections = tree.get("data", {}).get("sections", [])
    if not sections:
        return None
    for section in sections:
        paragraph_index = section.get("paragraph_index")
        if paragraph_index is None or order <= int(paragraph_index):
            return section
    return sections[-1]


def _section_part_names(section: dict[str, Any], kind: str) -> list[str]:
    names = [
        str(ref.get("part_name", ""))
        for ref in section.get("effective_references", [])
        if ref.get("kind") == kind and ref.get("part_name")
    ]
    return _dedupe(names)


def _evaluate_header_rule(
    unit_id: str,
    header_rule: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    if not context["section"]:
        return {
            "status": Status.UNKNOWN,
            "type": "template_generation_header_footer_unverified",
            "message": f"单元 {unit_id} 未绑定到 Word section，无法检查页眉",
            "actual": "unit section not resolved",
            "evidence_refs": [],
            "next_step": "先修单元到 section 的绑定，再检查页眉。",
        }
    header_text = _normalize_text(
        " ".join(part.get("text", "") for part in context["header_parts"])
    )
    no_header_expected = _means_none(header_rule)
    if no_header_expected:
        status = Status.PASS if not header_text else Status.FAIL
    else:
        status = Status.PASS if header_rule in header_text else Status.FAIL
    return {
        "status": status,
        "type": (
            "template_generation_header_footer_match"
            if status == Status.PASS
            else "template_generation_header_footer_mismatch"
        ),
        "message": f"单元 {unit_id} 的页眉规则已按 Word section 检查",
        "actual": header_text or "no section header text parsed",
        "evidence_refs": _header_footer_refs(context, "header"),
        "next_step": (
            "none"
            if status == Status.PASS
            else "修模板生成逻辑，确保该单元所在 section 的页眉符合标准。"
        ),
    }


def _evaluate_page_number_rule(
    unit_id: str,
    page_rule: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    if not context["section"]:
        return {
            "status": Status.UNKNOWN,
            "type": "template_generation_page_number_rule_unverified",
            "message": f"单元 {unit_id} 未绑定到 Word section，无法检查页码",
            "actual": "unit section not resolved",
            "evidence_refs": [],
            "next_step": "先修单元到 section 的绑定，再检查页脚页码字段和页码格式。",
        }
    page_fields = context["page_fields"]
    footer_text = _normalize_text(
        " ".join(part.get("text", "") for part in context["footer_parts"])
    )
    page_numbering = context["page_numbering"]
    actual = _page_number_actual(page_fields, footer_text, page_numbering)
    no_page_expected = page_rule == "无" or "不显示页码" in page_rule
    source_no_field = "无页码字段" in page_rule
    has_page_evidence = bool(page_fields or footer_text)
    if no_page_expected:
        status = Status.PASS if not has_page_evidence else Status.FAIL
        type_ = (
            "template_generation_page_number_rule_match"
            if status == Status.PASS
            else "template_generation_page_number_rule_mismatch"
        )
    elif "前置页页码规则" in page_rule:
        status = (
            Status.PASS
            if has_page_evidence
            and str(page_numbering.get("format", "")).lower().endswith("roman")
            else Status.FAIL
        )
        type_ = (
            "template_generation_page_number_rule_match"
            if status == Status.PASS
            else "template_generation_page_number_rule_mismatch"
        )
    elif "阿拉伯数字页码规则" in page_rule:
        fmt = str(page_numbering.get("format") or "decimal")
        status = (
            Status.PASS
            if has_page_evidence and fmt in {"decimal", ""}
            else Status.FAIL
        )
        type_ = (
            "template_generation_page_number_rule_match"
            if status == Status.PASS
            else "template_generation_page_number_rule_mismatch"
        )
    elif source_no_field and not has_page_evidence:
        status = Status.PASS
        type_ = "template_generation_page_number_rule_match"
    else:
        status = Status.UNKNOWN
        type_ = "template_generation_page_number_rule_unverified"
    return {
        "status": status,
        "type": type_,
        "message": f"单元 {unit_id} 的页码规则已按 Word section 检查",
        "actual": actual,
        "evidence_refs": _header_footer_refs(context, "footer")
        + [field.get("source_ref", "") for field in page_fields],
        "next_step": (
            "none"
            if status == Status.PASS
            else "修模板生成逻辑，或补页码格式/section 继承的更细检查。"
        ),
    }


def _page_number_actual(
    page_fields: list[dict[str, Any]],
    footer_text: str,
    page_numbering: dict[str, Any],
) -> str:
    parts = []
    if page_fields:
        parts.append(
            "fields="
            + ", ".join(str(field.get("instruction", "")) for field in page_fields)
        )
    if footer_text:
        parts.append(f"footer_text={footer_text}")
    if page_numbering:
        parts.append(f"page_numbering={page_numbering}")
    return "; ".join(parts) or "no section footer page evidence parsed"


def _header_footer_refs(context: dict[str, Any], kind: str) -> list[str]:
    refs = [ref for ref in context["evidence_refs"] if ref]
    parts = context["header_parts"] if kind == "header" else context["footer_parts"]
    refs.extend(part.get("source_ref", "") for part in parts)
    return [ref for ref in refs if ref]


def _page_rule_checks(
    unit: dict[str, Any],
    tree: dict[str, Any],
    matched_orders: list[int],
    unit_first_orders: list[tuple[str, int]],
) -> list[dict[str, Any]]:
    unit_id = str(unit.get("unit_id") or "unknown_unit")
    page = unit.get("page") or {}
    if not isinstance(page, dict):
        return []
    checks: list[dict[str, Any]] = []
    for field in ("page_break", "section_isolation", "keep_together"):
        rule = _normalize_text(page.get(field))
        if not rule:
            continue
        page_check = _evaluate_page_rule(
            unit_id,
            field,
            rule,
            tree,
            matched_orders,
            unit_first_orders,
        )
        checks.append(
            _check(
                "template_generation.page_rule_match",
                page_check["status"],
                page_check["type"],
                page_check["message"],
                rule,
                page_check["actual"],
                category="page_rule",
                evidence_refs=page_check["evidence_refs"],
                affected_ids=[f"{unit_id}.page.{field}"],
                next_step=page_check["next_step"],
            )
        )
    return checks


def _evaluate_page_rule(
    unit_id: str,
    field: str,
    rule: str,
    tree: dict[str, Any],
    matched_orders: list[int],
    unit_first_orders: list[tuple[str, int]],
) -> dict[str, Any]:
    if not matched_orders:
        return {
            "status": Status.UNKNOWN,
            "type": "template_generation_page_rule_unverified",
            "message": f"单元 {unit_id} 未绑定到 Word 来源，无法检查分页规则：{field}",
            "actual": "unit source not matched",
            "evidence_refs": [],
            "next_step": "先修单元/元素匹配，再检查分页规则。",
        }

    bounded_orders = _unit_bounded_orders(unit_id, matched_orders, unit_first_orders)
    first_order = min(bounded_orders or matched_orders)
    context = _page_context(tree, first_order, bounded_orders or matched_orders)
    if field == "page_break":
        if _page_rule_is_document_start(rule):
            status = Status.PASS if first_order <= 5 else Status.FAIL
            return {
                "status": status,
                "type": (
                    "template_generation_page_rule_match"
                    if status == Status.PASS
                    else "template_generation_page_rule_mismatch"
                ),
                "message": f"单元 {unit_id} 应在文档首页开始",
                "actual": f"first matched paragraph p[{first_order}]",
                "evidence_refs": [context["paragraph_ref"]],
                "next_step": (
                    "none"
                    if status == Status.PASS
                    else "修模板生成顺序，让该单元从文档首页开始。"
                ),
            }
        if _page_rule_requires_yes(rule):
            has_break = bool(context["page_break_refs"] or context["section_refs"])
            status = Status.PASS if has_break else Status.FAIL
            return {
                "status": status,
                "type": (
                    "template_generation_page_rule_match"
                    if status == Status.PASS
                    else "template_generation_page_rule_mismatch"
                ),
                "message": f"单元 {unit_id} 要求另起页",
                "actual": (
                    ", ".join(context["page_break_refs"] + context["section_refs"])
                    or f"no explicit page/section break before p[{first_order}]"
                ),
                "evidence_refs": context["page_break_refs"] + context["section_refs"],
                "next_step": (
                    "none"
                    if status == Status.PASS
                    else "修模板生成逻辑，在该单元前写入显式分页符或分节符。"
                ),
            }
        if _page_rule_means_no_or_optional(rule):
            has_break = bool(context["page_break_refs"])
            status = Status.FAIL if has_break else Status.PASS
            return {
                "status": status,
                "type": (
                    "template_generation_page_rule_mismatch"
                    if status == Status.FAIL
                    else "template_generation_page_rule_match"
                ),
                "message": f"单元 {unit_id} 不要求另起页",
                "actual": (
                    ", ".join(context["page_break_refs"])
                    if has_break
                    else f"no explicit page break before p[{first_order}]"
                ),
                "evidence_refs": context["page_break_refs"] or [context["paragraph_ref"]],
                "next_step": (
                    "修模板生成逻辑，移除不应存在的显式分页符。"
                    if status == Status.FAIL
                    else "none"
                ),
            }

    if field == "section_isolation":
        if _page_rule_requires_yes(rule):
            has_section = bool(context["section_refs"])
            status = Status.PASS if has_section else Status.FAIL
            return {
                "status": status,
                "type": (
                    "template_generation_page_rule_match"
                    if status == Status.PASS
                    else "template_generation_page_rule_mismatch"
                ),
                "message": f"单元 {unit_id} 要求分页隔离",
                "actual": (
                    ", ".join(context["section_refs"])
                    or f"no section break before p[{first_order}]"
                ),
                "evidence_refs": context["section_refs"] or [context["paragraph_ref"]],
                "next_step": (
                    "none"
                    if status == Status.PASS
                    else "修模板生成逻辑，用 section 或等价确定性边界隔离该单元。"
                ),
            }

    if field == "keep_together":
        keep_refs = context["keep_refs"] + context["table_keep_refs"]
        if keep_refs:
            return {
                "status": Status.PASS,
                "type": "template_generation_page_rule_match",
                "message": f"单元 {unit_id} 有 OOXML keep 或表格不拆行证据",
                "actual": ", ".join(keep_refs),
                "evidence_refs": keep_refs,
                "next_step": "none",
            }
        if context["table_refs"]:
            return {
                "status": Status.UNKNOWN,
                "type": "template_generation_page_rule_unverified",
                "message": f"单元 {unit_id} 已绑定到表格块，但同页约束仍无法完整证明",
                "actual": (
                    "table block parsed without cantSplit/keep evidence: "
                    + ", ".join(context["table_refs"])
                ),
                "evidence_refs": context["table_refs"],
                "next_step": "补表格行不拆分、内容控件、页面图像或 Word evidence 检查。",
            }
        return {
            "status": Status.UNKNOWN,
            "type": "template_generation_page_rule_unverified",
            "message": f"单元 {unit_id} 的同页约束当前无法完整证明",
            "actual": f"no keepNext/keepLines/table no-split parsed near p[{first_order}]",
            "evidence_refs": [context["paragraph_ref"]],
            "next_step": "补单元范围、表格边界和 keep-with-next/keep-lines 的绑定检查。",
        }

    return {
        "status": Status.UNKNOWN,
        "type": "template_generation_page_rule_unverified",
        "message": f"单元 {unit_id} 的分页规则当前无法完整证明：{field}",
        "actual": f"unsupported page rule value near p[{first_order}]",
        "evidence_refs": [context["paragraph_ref"]],
        "next_step": "补单元边界到 OOXML 分页符、分节符、keep 属性的映射检查。",
    }


def _page_context(
    tree: dict[str, Any],
    first_order: int,
    matched_orders: list[int] | None = None,
) -> dict[str, Any]:
    matched_paragraph_orders = [
        int(order)
        for order in (matched_orders or [first_order])
        if int(order) < 20_000
    ]
    range_start = min(matched_paragraph_orders) if matched_paragraph_orders else first_order
    range_end = max(matched_paragraph_orders) if matched_paragraph_orders else first_order
    paragraphs = {
        int(paragraph.get("index")): paragraph
        for paragraph in tree.get("data", {}).get("paragraphs", [])
        if paragraph.get("index") is not None
    }
    paragraph = paragraphs.get(first_order, {})
    style = (paragraph.get("style_details") or {}).get("paragraph") or {}
    breaks = tree.get("data", {}).get("breaks", [])
    nearby_breaks = [
        item
        for item in breaks
        if item.get("paragraph_index") is not None
        and first_order - 2 <= int(item.get("paragraph_index")) <= first_order
    ]
    page_break_refs = [
        item.get("source_ref", "")
        for item in nearby_breaks
        if item.get("kind") == "break" and item.get("type") == "page"
    ]
    section_refs = [
        item.get("source_ref", "")
        for item in nearby_breaks
        if item.get("kind") == "section"
    ]
    if style.get("page_break_before"):
        page_break_refs.append(f"word/document.xml:p[{first_order}]/pageBreakBefore")
    keep_refs: list[str] = []
    for paragraph_index in range(range_start, range_end + 1):
        paragraph_style = (
            (paragraphs.get(paragraph_index, {}).get("style_details") or {}).get(
                "paragraph"
            )
            or {}
        )
        if paragraph_style.get("keep_next"):
            keep_refs.append(f"word/document.xml:p[{paragraph_index}]/keepNext")
        if paragraph_style.get("keep_lines"):
            keep_refs.append(f"word/document.xml:p[{paragraph_index}]/keepLines")
    if not keep_refs:
        if style.get("keep_next"):
            keep_refs.append(f"word/document.xml:p[{first_order}]/keepNext")
        if style.get("keep_lines"):
            keep_refs.append(f"word/document.xml:p[{first_order}]/keepLines")

    table_refs: list[str] = []
    table_keep_refs: list[str] = []
    for table in tree.get("data", {}).get("tables", []):
        table_start = table.get("first_paragraph_index")
        table_end = table.get("last_paragraph_index")
        if table_start is None or table_end is None:
            continue
        if not _ranges_overlap(
            range_start - 2,
            range_end + 2,
            int(table_start),
            int(table_end),
        ):
            continue
        table_refs.append(str(table.get("source_ref", "")))
        table_keep_refs.extend(str(ref) for ref in table.get("cant_split_row_refs", []))
        table_keep_refs.extend(str(ref) for ref in table.get("keep_refs", []))
    return {
        "paragraph_ref": paragraph.get("source_ref", f"word/document.xml:p[{first_order}]"),
        "page_break_refs": [ref for ref in page_break_refs if ref],
        "section_refs": [ref for ref in section_refs if ref],
        "keep_refs": _dedupe(keep_refs),
        "table_refs": _dedupe(table_refs),
        "table_keep_refs": _dedupe(table_keep_refs),
    }


def _unit_bounded_orders(
    unit_id: str,
    matched_orders: list[int],
    unit_first_orders: list[tuple[str, int]],
) -> list[int]:
    if not matched_orders:
        return []
    start_order, end_order = _field_unit_bounds(
        unit_id,
        matched_orders,
        unit_first_orders,
    )
    return [
        order
        for order in matched_orders
        if start_order <= int(order) <= end_order
    ]


def _ranges_overlap(
    left_start: int,
    left_end: int,
    right_start: int,
    right_end: int,
) -> bool:
    return left_start <= right_end and right_start <= left_end


def _page_rule_is_document_start(rule: str) -> bool:
    return "文档首页" in rule


def _page_rule_requires_yes(rule: str) -> bool:
    normalized = _normalize_text(rule)
    return normalized == "是" or normalized.startswith("是；")


def _page_rule_means_no_or_optional(rule: str) -> bool:
    normalized = _normalize_text(rule)
    return (
        normalized == "否"
        or "否/未要求" in normalized
        or "不要求" in normalized
        or "随正文首页" in normalized
    )


def _unknown_visible_object_checks(tree: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for index, item in enumerate(
        tree.get("data", {}).get("unknown_visible_objects", []),
        start=1,
    ):
        checks.append(
            _check(
                "template_generation.actual_tree",
                Status.UNKNOWN,
                "template_generation_visible_object_unmodeled",
                f"生成模板 Word 中存在当前解析器未建模的可见对象：{item.get('object_type')}",
                "visible object modeled or explicitly exempted",
                item.get("reason", "unmodeled"),
                category="actual_tree",
                evidence_refs=[item.get("source_ref", "")],
                affected_ids=[item.get("content_id", f"unknown_visible_object_{index}")],
                next_step="补解析器能力或登记明确例外，不能静默忽略可见对象。",
            )
        )
    return checks


def _candidate_needles(element: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    content = _normalize_text(element.get("content"))
    if content and not _looks_like_descriptor(content):
        candidates.append(content)
        if len(content) > 80:
            candidates.append(content[:80])
    name = _normalize_text(element.get("name"))
    label = re.sub(r"(标签|内容|正文|结果|机制)$", "", name).strip()
    if label and not _looks_like_descriptor(label) and len(label) >= 2:
        candidates.append(label)
    candidates.extend(_fixed_visible_field_needles(element))
    return _dedupe(candidates)


def _fixed_visible_field_needles(element: dict[str, Any]) -> list[str]:
    raw = _normalize_text(element.get("raw"))
    if not raw:
        return []
    match = re.search(r"固定可见字段[:：](?P<fields>.+?)(?:样式[:：]|$)", raw)
    if not match:
        return []
    fields = re.split(r"[；;、,，。]", match.group("fields"))
    return [
        field.strip()
        for field in fields
        if len(field.strip()) >= 2 and not _looks_like_descriptor(field.strip())
    ]


def _find_matches(
    entries: list[dict[str, Any]],
    needles: list[str],
) -> list[dict[str, Any]]:
    if not needles:
        return []
    matches: list[dict[str, Any]] = []
    for entry in entries:
        text = _normalize_text(entry.get("text"))
        if any(_normalize_text(needle) in text for needle in needles):
            matches.append(entry)
    return sorted(matches, key=lambda entry: int(entry.get("order") or 0))


def _has_generated_field(tree: dict[str, Any], element: dict[str, Any]) -> bool:
    fields = tree.get("data", {}).get("fields", [])
    if not fields:
        return False
    name = _normalize_text(element.get("name")).lower()
    content = _normalize_text(element.get("content")).lower()
    instructions = [
        str(field.get("instruction", "")).upper()
        for field in fields
    ]
    if "toc" in name or "目录" in name or "toc" in content or "目录" in content:
        return any("TOC" in instruction for instruction in instructions)
    if "页码" in name or "page" in name or "页码" in content:
        return any("PAGE" in instruction for instruction in instructions)
    return bool(fields)


def _compare_style_details(
    expected_style: str,
    match: dict[str, Any],
) -> dict[str, list[str]]:
    expected = _expected_style_requirements(expected_style)
    actual = _actual_style_properties(match)
    matched: list[str] = []
    mismatches: list[str] = []
    unknown: list[str] = []

    for font in expected["fonts"]:
        actual_fonts = actual["font_names"]
        if font in actual_fonts:
            matched.append(f"font={font}")
        elif actual_fonts:
            mismatches.append(f"font expected {font}, actual {'/'.join(actual_fonts)}")
        else:
            unknown.append(f"font expected {font}")

    expected_size = expected["font_size_pt"]
    if expected_size is not None:
        actual_size = actual["font_size_pt"]
        if actual_size is None:
            unknown.append(f"font_size expected {expected_size:g}pt")
        elif abs(actual_size - expected_size) <= 0.25:
            matched.append(f"font_size={actual_size:g}pt")
        else:
            mismatches.append(
                f"font_size expected {expected_size:g}pt, actual {actual_size:g}pt"
            )

    expected_bold = expected["bold"]
    if expected_bold is not None:
        actual_bold = actual["bold"]
        if actual_bold is None:
            unknown.append(f"bold expected {expected_bold}")
        elif actual_bold == expected_bold:
            matched.append(f"bold={actual_bold}")
        else:
            mismatches.append(f"bold expected {expected_bold}, actual {actual_bold}")

    expected_alignment = expected["alignment"]
    if expected_alignment:
        actual_alignment = actual["alignment"]
        if not actual_alignment:
            unknown.append(f"alignment expected {expected_alignment}")
        elif actual_alignment == expected_alignment:
            matched.append(f"alignment={actual_alignment}")
        else:
            mismatches.append(
                f"alignment expected {expected_alignment}, actual {actual_alignment}"
            )

    expected_line_spacing = expected["line_spacing"]
    if expected_line_spacing:
        actual_line_spacing = actual["line_spacing"]
        if not actual_line_spacing:
            unknown.append(f"line_spacing expected {expected_line_spacing}")
        elif _line_spacing_matches(expected_line_spacing, actual_line_spacing):
            matched.append(f"line_spacing={actual_line_spacing}")
        else:
            mismatches.append(
                "line_spacing expected "
                f"{expected_line_spacing}, actual {actual_line_spacing}"
            )

    return {
        "matched": matched,
        "mismatches": mismatches,
        "unknown": unknown,
    }


def _expected_style_requirements(expected_style: str) -> dict[str, Any]:
    normalized = _normalize_text(expected_style)
    fonts = [
        font
        for font in ("华文行楷", "黑体", "宋体", "Times New Roman")
        if font in normalized
    ]
    size_match = re.search(r"(?P<size>\d+(?:\.\d+)?)\s*pt", normalized)
    bold: bool | None = None
    if "不加粗" in normalized:
        bold = False
    elif "加粗" in normalized:
        bold = True
    alignment = None
    if "居中" in normalized:
        alignment = "center"
    elif "两端对齐" in normalized:
        alignment = "both"
    elif "左对齐" in normalized:
        alignment = "left"
    line_spacing = None
    if "单倍行距" in normalized:
        line_spacing = "single"
    elif "1.5 倍行距" in normalized or "1.5倍行距" in normalized:
        line_spacing = "1.5"
    multiple_match = re.search(
        r"多倍行距[；;，, ]*设置值[=＝]?\s*(?P<size>\d+(?:\.\d+)?)",
        normalized,
    )
    if multiple_match:
        line_spacing = f"multiple:{float(multiple_match.group('size')):g}"
    exact_match = re.search(
        r"固定(?:值|行距约)?\s*(?P<size>\d+(?:\.\d+)?)\s*pt",
        normalized,
    )
    if exact_match:
        line_spacing = f"exact:{float(exact_match.group('size')):g}pt"
    return {
        "fonts": fonts,
        "font_size_pt": float(size_match.group("size")) if size_match else None,
        "bold": bold,
        "alignment": alignment,
        "line_spacing": line_spacing,
    }


def _actual_style_properties(match: dict[str, Any]) -> dict[str, Any]:
    details = match.get("style_details") or {}
    dominant = details.get("dominant_run") or {}
    paragraph_run = details.get("paragraph_run_properties") or {}
    paragraph = details.get("paragraph") or {}
    font_names = list(
        dict.fromkeys(
            [
                *dominant.get("font_names", []),
                *paragraph_run.get("font_names", []),
            ]
        )
    )
    return {
        "font_names": font_names,
        "font_size_pt": dominant.get("font_size_pt")
        or paragraph_run.get("font_size_pt"),
        "bold": _first_known(dominant.get("bold"), paragraph_run.get("bold")),
        "alignment": paragraph.get("alignment"),
        "line_spacing": (paragraph.get("spacing") or {}).get("line_spacing"),
    }


def _line_spacing_matches(expected: str, actual: str) -> bool:
    if expected == actual:
        return True
    expected_kind, expected_value = _line_spacing_parts(expected)
    actual_kind, actual_value = _line_spacing_parts(actual)
    if expected_kind != actual_kind:
        return False
    if expected_value is None or actual_value is None:
        return False
    tolerance = 0.05 if expected_kind == "multiple" else 0.25
    return abs(expected_value - actual_value) <= tolerance


def _line_spacing_parts(value: str) -> tuple[str, float | None]:
    if value.startswith("exact:") and value.endswith("pt"):
        return "exact", _float_or_none(value.removeprefix("exact:").removesuffix("pt"))
    if value.startswith("multiple:"):
        return "multiple", _float_or_none(value.removeprefix("multiple:"))
    if value == "single":
        return "multiple", 1.0
    if value == "1.5":
        return "multiple", 1.5
    if value == "double":
        return "multiple", 2.0
    return value, None


def _style_actual_summary(match: dict[str, Any]) -> str:
    details = match.get("style_details") or {}
    props = _actual_style_properties(match)
    paragraph = details.get("paragraph") or {}
    parts = [
        f"style={match.get('style') or paragraph.get('style_id') or 'missing'}",
        f"font={'/'.join(props['font_names']) or 'missing'}",
        (
            "font_size="
            + (
                f"{props['font_size_pt']:g}pt"
                if props["font_size_pt"] is not None
                else "missing"
            )
        ),
        f"bold={props['bold']}",
        f"alignment={props['alignment'] or 'missing'}",
        f"line_spacing={props['line_spacing'] or 'missing'}",
    ]
    return "; ".join(parts)


def _first_known(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _style_matches(expected_style: str, actual_style: str) -> bool:
    if not expected_style or not actual_style:
        return False
    expected = expected_style.lower()
    actual = actual_style.lower()
    return expected == actual or actual in expected or expected in actual


def _means_none(value: str) -> bool:
    return value in {"无", "默认无"} or "默认无" in value or "源模板无" in value


def _looks_like_descriptor(value: str) -> bool:
    descriptor_markers = (
        "学生",
        "当前阶段",
        "目标输出",
        "系统生成",
        "××",
        "模板",
        "正文",
        "标题",
        "内容流",
    )
    if value in {"固定", "填充", "生成", "手工"}:
        return True
    return any(marker in value for marker in descriptor_markers) and "：" not in value


def _matched_evidence(checks: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for check in checks:
        if check.get("status") != Status.PASS.value:
            continue
        refs.extend(check.get("evidence_refs", []))
    return _dedupe(refs)[:5]


def _template_unit_contract_path(bundle: StandardBundle) -> Path:
    rel_path = bundle.signed_standard.get("evidence_baselines", {}).get(
        "template_unit_contract",
        "template_unit_contract.yaml",
    )
    return bundle.school_dir / rel_path


def _check(
    check_id: str,
    status: Status,
    type_: str,
    message: str,
    expected: Any,
    actual: Any,
    *,
    category: str | None = None,
    evidence_refs: list[str] | None = None,
    affected_ids: list[str] | None = None,
    next_step: str = "none",
    root_cause_bucket: str = "template_generation_gap",
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "category": category or check_id.split(".")[-1],
        "status": status.value,
        "type": type_,
        "message": message,
        "expected": _preview(expected),
        "actual": _preview(actual),
        "evidence_refs": [ref for ref in (evidence_refs or []) if ref],
        "affected_ids": [identifier for identifier in (affected_ids or []) if identifier],
        "next_step": next_step,
        "root_cause_bucket": root_cause_bucket,
    }


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _preview(value: Any, limit: int = 320) -> str:
    normalized = _normalize_text(value)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped
