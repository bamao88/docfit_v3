from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from docfit.core.io import sha256_file, sha256_json
from docfit.core.models import Finding, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.ooxml.package import is_valid_docx

from .page_policy import (
    PAGE_POLICY_FIELDS,
    page_policy_has_unknown,
    page_policy_known_values,
    page_policy_shape_errors,
)
from .stage_inputs import l1_artifact_hash


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def verify_template_parse_build(
    *,
    document_facts: dict[str, Any],
    l1_input_contract: dict[str, Any],
    unit_map: dict[str, Any],
    element_spec: dict[str, Any],
    global_spec: dict[str, Any],
    template_spec: dict[str, Any],
    build_manifest: dict[str, Any],
    fillable_template_docx: Path,
) -> tuple[Status, list[Finding], dict[str, Any], dict[str, bool]]:
    findings: list[Finding] = []
    stage_reports: list[dict[str, Any]] = []
    next_index = 1

    for stage, artifact, verifier in [
        ("T1", document_facts, _verify_t1_document_facts),
        ("L1", l1_input_contract, _verify_l1_input_contract),
        ("T2", unit_map, _verify_t2_unit_map),
        ("T3", element_spec, _verify_t3_element_spec),
        ("T4", global_spec, _verify_t4_global_spec),
        ("T5", template_spec, _verify_t5_template_spec),
    ]:
        stage_findings = verifier(artifact, start_index=next_index)
        findings.extend(stage_findings)
        next_index += len(stage_findings)
        stage_reports.append(
            _stage_report(stage, artifact, _status_for_findings(stage_findings))
        )

    l1_trace_findings = _verify_l1_trace_chain(
        document_facts=document_facts,
        l1_input_contract=l1_input_contract,
        artifacts={
            "T2": unit_map,
            "T3": element_spec,
            "T4": global_spec,
            "T5": template_spec,
            "T6": build_manifest,
        },
        start_index=next_index,
    )
    findings.extend(l1_trace_findings)
    next_index += len(l1_trace_findings)

    t6_findings = _verify_t6_build(
        template_spec,
        build_manifest,
        fillable_template_docx,
        start_index=next_index,
    )
    findings.extend(t6_findings)
    stage_reports.append(
        _stage_report("T6", build_manifest, _status_for_findings(t6_findings))
    )

    status = merge_statuses([_status_for_findings(findings)])
    first_bad_stage = _first_bad_stage(stage_reports)
    report = {
        "artifact_type": "verification_report",
        "artifact_version": "1.0",
        "status": status.value,
        "first_bad_stage": first_bad_stage,
        "input_hashes": {"l1": l1_artifact_hash(l1_input_contract)},
        "stages": stage_reports,
        "findings": [finding.to_dict() for finding in findings],
    }
    statuses_by_stage = {item["stage"]: item["status"] for item in stage_reports}
    coverage = {
        "template_generation.document_facts": statuses_by_stage.get("T1") == Status.PASS.value,
        "template_generation.l1_input_contract": statuses_by_stage.get("L1") == Status.PASS.value,
        "template_generation.unit_map": statuses_by_stage.get("T2") == Status.PASS.value,
        "template_generation.element_spec": statuses_by_stage.get("T3") == Status.PASS.value,
        "template_generation.global_spec": statuses_by_stage.get("T4") == Status.PASS.value,
        "template_generation.template_spec": statuses_by_stage.get("T5") == Status.PASS.value,
        "template_generation.fillable_template": statuses_by_stage.get("T6") == Status.PASS.value,
        "template_generation.verification_report": True,
    }
    return status, findings, report, coverage


def _verify_l1_input_contract(
    l1_input_contract: dict[str, Any],
    *,
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    if l1_input_contract.get("artifact_type") != "template_generation_l1_input_contract":
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "l1_input_contract_missing",
                "L1 must be the sealed fact input contract",
                "artifact_type=template_generation_l1_input_contract",
                str(l1_input_contract.get("artifact_type")),
                root_cause_bucket="template_l1_contract_gap",
            )
        )
        next_index += 1
    coverage = l1_input_contract.get("coverage", {}) or {}
    for count_key in ("source_text_unbound_count", "raw_run_unbound_count", "logical_run_unbound_count"):
        if int(coverage.get(count_key) or 0) > 0:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    f"l1_{count_key}",
                    "L1 text and run identities must be fully bound",
                    f"{count_key}=0",
                    str(coverage.get(count_key)),
                    root_cause_bucket="template_l1_identity_gap",
                )
            )
            next_index += 1
    serialized = repr(l1_input_contract)
    forbidden = [
        field
        for field in (
            "ai_observation_bundle",
            "observation_bridge",
            "candidate_policy",
            "accepted_decision",
            "judge_status",
        )
        if field in serialized
    ]
    if forbidden:
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "l1_forbidden_semantics",
                "L1 must contain objective facts only",
                "no AI/bridge/judge semantics",
                ",".join(forbidden),
                root_cause_bucket="template_l1_boundary_violation",
            )
        )
    return findings


def _verify_l1_trace_chain(
    *,
    document_facts: dict[str, Any],
    l1_input_contract: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    expected_l1_hash = l1_artifact_hash(l1_input_contract)
    expected_document_facts_hash = sha256_json(document_facts)
    observed_document_facts_hash = l1_input_contract.get("input_hashes", {}).get(
        "document_facts"
    )
    if observed_document_facts_hash != expected_document_facts_hash:
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "l1_document_facts_hash_mismatch",
                "sealed L1 must bind the current T1 facts",
                expected_document_facts_hash,
                str(observed_document_facts_hash),
                root_cause_bucket="template_l1_hash_gap",
            )
        )
        next_index += 1
    for stage, artifact in artifacts.items():
        observed = (
            artifact.get("input_hashes", {}).get("l1")
            or artifact.get("route", {}).get("l1_hash")
            or artifact.get("l1_input_contract_ref", {}).get("hash")
        )
        if observed == expected_l1_hash:
            continue
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "l1_stage_hash_mismatch",
                f"{stage} must bind the same sealed L1 hash",
                expected_l1_hash,
                str(observed),
                evidence_refs=[stage],
                root_cause_bucket="template_l1_hash_gap",
            )
        )
        next_index += 1
    return findings


def _verify_t1_document_facts(
    document_facts: dict[str, Any],
    *,
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    if document_facts.get("artifact_type") != "document_facts":
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.UNKNOWN,
                "document_facts_artifact_missing",
                "T1 must produce document_facts.json",
                "artifact_type=document_facts",
                str(document_facts.get("artifact_type")),
                root_cause_bucket="template_t1_contract_gap",
            )
        )
        next_index += 1
    duplicate_findings = _duplicate_id_findings(
        document_facts.get("body_flow", []),
        ["node_id", "cell_id"],
        stage="T1",
        start_index=next_index,
    )
    findings.extend(duplicate_findings)
    next_index += len(duplicate_findings)
    duplicate_run_findings = _duplicate_id_findings(
        document_facts.get("runs", []),
        ["raw_run_id", "logical_run_id"],
        stage="T1",
        start_index=next_index,
    )
    findings.extend(duplicate_run_findings)
    next_index += len(duplicate_run_findings)
    source_text_by_ref = _source_paragraph_texts(document_facts)
    for item in document_facts.get("body_flow", []):
        item_ref = str(item.get("source_ref") or item.get("node_id") or "")
        raw_run_ids = [str(raw_id) for raw_id in item.get("raw_run_ids", [])]
        paragraph_id = str(item.get("paragraph_id") or "")
        if item.get("kind") == "paragraph" and paragraph_id and raw_run_ids:
            raw_prefix = raw_run_ids[0].split(".", 1)[0]
            if raw_prefix != paragraph_id:
                findings.append(
                    make_finding(
                        next_index,
                        "template_generate",
                        Status.UNKNOWN,
                        "document_facts_paragraph_trace_mismatch",
                        "T1 paragraph_id and raw run ids must use one coordinate system",
                        paragraph_id,
                        raw_run_ids[0],
                        evidence_refs=[item_ref],
                        root_cause_bucket="template_t1_coordinate_gap",
                    )
                )
                next_index += 1
        if _visible_body_item(item) and item.get("kind") == "paragraph" and not raw_run_ids:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.UNKNOWN,
                    "document_facts_visible_paragraph_trace_missing",
                    "T1 visible paragraphs must have raw run trace",
                    "raw_run_ids non-empty",
                    item_ref,
                    evidence_refs=[item_ref],
                    root_cause_bucket="template_t1_run_trace_gap",
                )
            )
            next_index += 1
        if _visible_body_item(item) and item.get("kind") == "table_cell":
            has_cell_trace = bool(
                raw_run_ids
                or item.get("cell_run_refs")
                or item.get("cell_paragraph_refs")
            )
            if not has_cell_trace:
                findings.append(
                    make_finding(
                        next_index,
                        "template_generate",
                        Status.UNKNOWN,
                        "document_facts_visible_table_cell_trace_missing",
                        "T1 visible table cells must link to cell paragraph or run trace",
                        "raw_run_ids or cell_run_refs or cell_paragraph_refs",
                        item_ref,
                        evidence_refs=[item_ref],
                        root_cause_bucket="template_t1_table_trace_gap",
                    )
                )
                next_index += 1
        if _visible_body_item(item) and item.get("kind") in {"header", "footer"}:
            has_part_trace = bool(
                raw_run_ids
                or item.get("part_flow_ref")
                or item.get("part_run_refs")
            )
            if not has_part_trace:
                findings.append(
                    make_finding(
                        next_index,
                        "template_generate",
                        Status.UNKNOWN,
                        "document_facts_header_footer_trace_missing",
                        "T1 header/footer items must link to part-local trace",
                        "raw_run_ids or part_flow_ref or part_run_refs",
                        item_ref,
                        evidence_refs=[item_ref],
                        root_cause_bucket="template_t1_header_footer_trace_gap",
                    )
                )
                next_index += 1
        semantic_fields = _semantic_field_names(item)
        if semantic_fields:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    "document_facts_semantic_field_in_t1",
                    "T1 document_facts must not contain semantic judgment fields",
                    "fact-only body_flow item",
                    ",".join(semantic_fields),
                    evidence_refs=[item_ref],
                    root_cause_bucket="template_t1_boundary_violation",
                )
            )
            next_index += 1
        expected_text = source_text_by_ref.get(str(item.get("source_ref") or ""))
        actual_text = str(item.get("text") or "").strip()
        if expected_text is not None and actual_text and expected_text != actual_text:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.UNKNOWN,
                    "document_facts_source_ref_text_mismatch",
                    "T1 source_ref must point to the OOXML paragraph containing body_flow text",
                    actual_text[:80],
                    expected_text[:80],
                    evidence_refs=[item_ref],
                    root_cause_bucket="template_t1_coordinate_gap",
                )
            )
            next_index += 1
    for run in document_facts.get("runs", []):
        missing = [
            key
            for key in ["raw_run_id", "logical_run_id", "merged_from", "kind", "effective_style", "style_provenance"]
            if _missing_value(run.get(key))
        ]
        if missing:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.UNKNOWN,
                    "document_facts_run_trace_missing",
                    "T1 run facts must be traceable",
                    ",".join(missing),
                    str(run.get("raw_run_id") or run.get("source_ref")),
                    root_cause_bucket="template_t1_run_trace_gap",
                )
            )
            next_index += 1
    for item in document_facts.get("unknown_objects", []):
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.UNKNOWN,
                "document_facts_unknown_visible_object",
                "T1 found visible object that is not modeled",
                "unknown_objects is empty or reviewed",
                item.get("reason", "unknown visible object"),
                evidence_refs=[str(item.get("source_ref") or "")],
                root_cause_bucket="template_t1_unknown_object",
            )
        )
        next_index += 1
    return findings


def _visible_body_item(item: dict[str, Any]) -> bool:
    return bool(item.get("visible", True) and str(item.get("text") or "").strip())


def _semantic_field_names(item: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in item:
        if _semantic_field_name(str(key)):
            names.append(str(key))
    signals = item.get("structural_signals")
    if isinstance(signals, dict):
        names.append("structural_signals")
        for key in signals:
            if _semantic_field_name(str(key)):
                names.append(f"structural_signals.{key}")
    return sorted(dict.fromkeys(names))


def _semantic_field_name(name: str) -> bool:
    return (
        name.startswith("is_")
        or name.startswith("looks_like_")
        or name.startswith("likely_")
        or name in {"large_font", "short_text", "policy", "confidence", "unit_id"}
    )


def _source_paragraph_texts(document_facts: dict[str, Any]) -> dict[str, str]:
    path_value = document_facts.get("metadata", {}).get("source_template_docx")
    if not path_value:
        return {}
    path = Path(str(path_value))
    if not path.exists():
        return {}
    try:
        with ZipFile(path) as package:
            root = ET.fromstring(package.read("word/document.xml"))
    except (KeyError, OSError, ET.ParseError):
        return {}
    return {
        f"word/document.xml:p[{index}]": _ooxml_visible_text(paragraph).strip()
        for index, paragraph in enumerate(root.iter(f"{W_NS}p"), start=1)
    }


def _ooxml_visible_text(root: ET.Element) -> str:
    chunks: list[str] = []

    def walk(node: ET.Element) -> None:
        local_name = node.tag.rsplit("}", 1)[-1]
        if local_name in {"del", "moveFrom"}:
            return
        if node.tag == f"{W_NS}t":
            chunks.append(node.text or "")
        elif node.tag == f"{W_NS}tab":
            chunks.append("\t")
        elif node.tag in {f"{W_NS}br", f"{W_NS}cr"}:
            chunks.append("\n")
        for child in list(node):
            walk(child)

    walk(root)
    return "".join(chunks)


def _missing_value(value: Any) -> bool:
    return value is None or value == "" or value == []


def _verify_t2_unit_map(unit_map: dict[str, Any], *, start_index: int) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    units = unit_map.get("units", [])
    if not units:
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.UNKNOWN,
                "unit_map_units_missing",
                "T2 must produce at least one unit",
                "unit_map.units non-empty",
                "missing",
                root_cause_bucket="template_t2_unit_gap",
            )
        )
        next_index += 1
    unit_ids = [str(unit.get("unit_id") or "") for unit in units]
    if "body_main" not in unit_ids:
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "unit_map_required_unit_missing",
                "T2 must identify required body_main unit",
                "body_main",
                repr(unit_ids),
                root_cause_bucket="template_t2_required_unit_gap",
            )
        )
        next_index += 1
    for unit in units:
        unit_id = str(unit.get("unit_id") or "")
        page_errors = page_policy_shape_errors(unit.get("page"))
        if page_errors:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    "unit_map_page_policy_invalid",
                    "T2 must emit canonical page policy for each unit",
                    ",".join(PAGE_POLICY_FIELDS),
                    "; ".join(page_errors),
                    affected_ids=[unit_id] if unit_id else [],
                    root_cause_bucket="template_t2_page_policy_gap",
                )
            )
            next_index += 1
        if not unit.get("page_start"):
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.UNKNOWN,
                    "unit_map_page_start_missing",
                    "T2 must make page_start explicit or UNKNOWN",
                    "page_start",
                    str(unit.get("unit_id")),
                    root_cause_bucket="template_t2_page_rule_gap",
                )
            )
            next_index += 1
    findings.extend(_flag_findings(unit_map.get("flags", []), start_index=next_index, stage="T2"))
    return findings


def _verify_t3_element_spec(
    element_spec: dict[str, Any],
    *,
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    allowed_policies = {
        "fixed",
        "template_default",
        "fill",
        "manual_only",
        "generated",
        "instruction_remove",
    }
    for element in element_spec.get("elements", []):
        policy = element.get("policy")
        stable_id = str(element.get("stable_id") or element.get("element_id"))
        if policy not in allowed_policies:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    "element_spec_policy_invalid",
                    "T3 policy must be in ontology",
                    ",".join(sorted(allowed_policies)),
                    str(policy),
                    affected_ids=[stable_id],
                    root_cause_bucket="template_t3_policy_gap",
                )
            )
            next_index += 1
        if policy == "fill" and not element.get("fill_source"):
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    "element_spec_fill_source_missing",
                    "T3 fill element must declare fill_source",
                    "fill_source",
                    stable_id,
                    affected_ids=[stable_id],
                    root_cause_bucket="template_t3_fill_source_gap",
                )
            )
            next_index += 1
        if policy == "manual_only" and not element.get("manual_semantics"):
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    "element_spec_manual_semantics_missing",
                    "T3 manual_only element must declare human-fill semantics",
                    "manual_semantics",
                    stable_id,
                    affected_ids=[stable_id],
                    root_cause_bucket="template_t3_manual_gap",
                )
            )
            next_index += 1
        if policy == "generated" and not element.get("generated", {}).get("field_type"):
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    "element_spec_generated_field_type_missing",
                    "T3 generated element must declare field_type",
                    "generated.field_type",
                    stable_id,
                    affected_ids=[stable_id],
                    root_cause_bucket="template_t3_generated_gap",
                )
            )
            next_index += 1
    findings.extend(_flag_findings(element_spec.get("flags", []), start_index=next_index, stage="T3"))
    return findings


def _verify_t4_global_spec(
    global_spec: dict[str, Any],
    *,
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    if global_spec.get("artifact_type") != "global_spec":
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.UNKNOWN,
                "global_spec_artifact_missing",
                "T4 must produce global_spec.yaml",
                "artifact_type=global_spec",
                str(global_spec.get("artifact_type")),
                root_cause_bucket="template_t4_contract_gap",
            )
        )
        next_index += 1
    section_profiles = global_spec.get("section_profiles") or []
    if not section_profiles:
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.UNKNOWN,
                "global_spec_section_profiles_missing",
                "T4 must produce section profiles or explicit UNKNOWN profile",
                "section_profiles",
                "missing",
                root_cause_bucket="template_t4_section_gap",
            )
        )
        next_index += 1
    profile_ids = [
        str(profile.get("section_profile_id") or "")
        for profile in section_profiles
    ]
    duplicates = sorted({profile_id for profile_id in profile_ids if profile_ids.count(profile_id) > 1})
    if duplicates:
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "global_spec_duplicate_section_profile_id",
                "T4 section_profile ids must be unique",
                "unique section_profile_id",
                repr(duplicates),
                root_cause_bucket="template_t4_section_id_gap",
            )
        )
        next_index += 1
    header_footer_parts = {
        str(part.get("part_name"))
        for part in global_spec.get("header_footer", [])
        if part.get("part_name")
    }
    for profile in section_profiles:
        profile_id = str(profile.get("section_profile_id") or "section_unknown")
        boundary = profile.get("boundary")
        if not isinstance(boundary, dict) or not boundary:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.UNKNOWN,
                    "global_spec_section_boundary_missing",
                    "T4 section profile must declare boundary or explicit UNKNOWN",
                    "boundary",
                    profile_id,
                    affected_ids=[profile_id],
                    root_cause_bucket="template_t4_section_boundary_gap",
                )
            )
            next_index += 1
        elif boundary.get("status") == "UNKNOWN":
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.UNKNOWN,
                    "global_spec_section_boundary_unknown",
                    "T4 section profile boundary must be mappable to source_seq",
                    "boundary.status=detected",
                    profile_id,
                    evidence_refs=[str(ref) for ref in boundary.get("evidence_refs", [])],
                    affected_ids=[profile_id],
                    root_cause_bucket="template_t4_section_boundary_gap",
                )
            )
            next_index += 1
        if profile_id != "section_unknown" and not profile.get("source_ref"):
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.UNKNOWN,
                    "global_spec_section_source_ref_missing",
                    "T4 section profile must trace back to T1 section source_ref",
                    "source_ref",
                    profile_id,
                    affected_ids=[profile_id],
                    root_cause_bucket="template_t4_section_trace_gap",
                )
            )
            next_index += 1
        page_numbering = profile.get("page_numbering") or {}
        display = page_numbering.get("display") or {}
        display_status = str(display.get("status") or "")
        if not display_status:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.UNKNOWN,
                    "global_spec_page_numbering_display_status_missing",
                    "T4 per-section page numbering display status must be explicit",
                    "page_numbering.display.status",
                    profile_id,
                    affected_ids=[f"{profile_id}.page_numbering"],
                    root_cause_bucket="template_t4_page_numbering_gap",
                )
            )
            next_index += 1
        if display_status == "detected" and not any(
            _is_page_field_evidence(field)
            for field in page_numbering.get("fields", [])
        ):
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    "global_spec_page_numbering_detected_without_page_field",
                    "T4 detected page numbering must include PAGE field evidence",
                    "PAGE field evidence",
                    profile_id,
                    affected_ids=[f"{profile_id}.page_numbering"],
                    root_cause_bucket="template_t4_page_numbering_gap",
                )
            )
            next_index += 1
        if display_status == "no_page_field":
            checked_scopes = display.get("checked_scopes") or {}
            if not checked_scopes.get("body_source_seq_range") and not checked_scopes.get("header_footer_parts"):
                findings.append(
                    make_finding(
                        next_index,
                        "template_generate",
                        Status.UNKNOWN,
                        "global_spec_no_page_field_scope_missing",
                        "T4 no_page_field must include checked body/header/footer scopes",
                        "checked_scopes",
                        profile_id,
                        affected_ids=[f"{profile_id}.page_numbering"],
                        root_cause_bucket="template_t4_page_numbering_gap",
                    )
                )
                next_index += 1
        for ref in (profile.get("header_footer") or {}).get("effective_references", []):
            part_name = str(ref.get("part_name") or "")
            if part_name and part_name not in header_footer_parts:
                findings.append(
                    make_finding(
                        next_index,
                        "template_generate",
                        Status.UNKNOWN,
                        "global_spec_header_footer_part_missing",
                        "T4 section header/footer references must point to parsed parts",
                        "part_name in global_spec.header_footer",
                        part_name,
                        evidence_refs=[str(ref.get("source_ref") or "")],
                        affected_ids=[profile_id],
                        root_cause_bucket="template_t4_header_footer_gap",
                    )
                )
                next_index += 1
        profile_flag_findings = _flag_findings(
            profile.get("flags", []),
            start_index=next_index,
            stage="T4",
        )
        findings.extend(profile_flag_findings)
        next_index += len(profile_flag_findings)
    global_flag_findings = _flag_findings(
        global_spec.get("flags", []),
        start_index=next_index,
        stage="T4",
    )
    findings.extend(global_flag_findings)
    return findings


def _verify_t5_template_spec(
    template_spec: dict[str, Any],
    *,
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    if template_spec.get("artifact_type") != "template_spec":
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.UNKNOWN,
                "template_spec_artifact_missing",
                "T5 must produce template_spec.yaml",
                "artifact_type=template_spec",
                str(template_spec.get("artifact_type")),
                root_cause_bucket="template_t5_contract_gap",
            )
        )
        next_index += 1
    unit_ids = [str(unit.get("unit_id") or "") for unit in template_spec.get("units", [])]
    duplicate_unit_ids = sorted(
        {
            unit_id
            for unit_id in unit_ids
            if unit_id != "other" and unit_ids.count(unit_id) > 1
        }
    )
    if duplicate_unit_ids:
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "template_spec_duplicate_unit_id",
                "T5 unit ids must be unique",
                "unique unit_id",
                repr(duplicate_unit_ids),
                root_cause_bucket="template_t5_id_gap",
            )
        )
        next_index += 1
    if unit_ids.count("other") > 1:
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.UNKNOWN,
                "template_spec_duplicate_other_unit_id",
                "T5 may contain multiple unresolved other units, but they require review",
                "other units reviewed or promoted to specific unit ids",
                repr([unit_id for unit_id in unit_ids if unit_id == "other"]),
                root_cause_bucket="template_t5_other_unit_review",
            )
        )
        next_index += 1
    section_profiles = template_spec.get("global", {}).get("section_profiles", [])
    section_profile_ids = {
        str(profile.get("section_profile_id") or "")
        for profile in section_profiles
    }
    for unit in template_spec.get("units", []):
        unit_id = str(unit.get("unit_id") or "")
        page_errors = page_policy_shape_errors(unit.get("page"))
        if page_errors:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    "template_spec_unit_page_policy_invalid",
                    "T5 must preserve canonical T2 page policy on each unit",
                    ",".join(PAGE_POLICY_FIELDS),
                    "; ".join(page_errors),
                    affected_ids=[unit_id] if unit_id else [],
                    root_cause_bucket="template_t5_page_policy_gap",
                )
            )
            next_index += 1
        section_profile_refs = unit.get("section_profile_refs") or []
        unit_range = _unit_source_seq_range(unit)
        if not section_profile_refs:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.UNKNOWN,
                    "template_spec_unit_section_profile_refs_missing",
                    "T5 must bind each unit to at least one section profile",
                    "section_profile_refs non-empty",
                    unit_id,
                    affected_ids=[unit_id] if unit_id else [],
                    root_cause_bucket="template_t5_section_join_gap",
                )
            )
            next_index += 1
        for ref in section_profile_refs:
            section_profile_id = str(ref.get("section_profile_id") or "")
            if section_profile_id not in section_profile_ids:
                findings.append(
                    make_finding(
                        next_index,
                        "template_generate",
                        Status.FAIL,
                        "template_spec_unit_section_profile_ref_missing",
                        "T5 unit section_profile_refs must reference global section profiles",
                        "existing section_profile_id",
                        section_profile_id or "missing",
                        affected_ids=[unit_id] if unit_id else [],
                        root_cause_bucket="template_t5_section_join_gap",
                    )
                )
                next_index += 1
                continue
            overlap = ref.get("overlap_source_seq_range") or {}
            if unit_range and not _ranges_overlap(unit_range, overlap):
                findings.append(
                    make_finding(
                        next_index,
                        "template_generate",
                        Status.FAIL,
                        "template_spec_unit_section_profile_range_mismatch",
                        "T5 unit-section binding must overlap unit source_seq range",
                        repr(unit_range),
                        repr(overlap),
                        affected_ids=[unit_id] if unit_id else [],
                        root_cause_bucket="template_t5_section_join_gap",
                    )
                )
                next_index += 1
        for element in unit.get("elements", []):
            if element.get("policy") == "fill" and not element.get("fill_source"):
                findings.append(
                    make_finding(
                        next_index,
                        "template_generate",
                        Status.FAIL,
                        "template_spec_fill_source_missing",
                        "T5 fill element must preserve fill_source",
                        "fill_source",
                        str(element.get("stable_id")),
                        affected_ids=[str(element.get("stable_id"))],
                        root_cause_bucket="template_t5_fill_source_gap",
                    )
                )
                next_index += 1
    findings.extend(
        _flag_findings(
            template_spec.get("review_flags", []),
            start_index=next_index,
            stage="T5",
        )
    )
    return findings


def _verify_t6_build(
    template_spec: dict[str, Any],
    build_manifest: dict[str, Any],
    fillable_template_docx: Path,
    *,
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    if not is_valid_docx(fillable_template_docx):
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "fillable_template_invalid_docx",
                "T6 output must be a valid DOCX",
                "valid DOCX",
                str(fillable_template_docx),
                root_cause_bucket="template_t6_docx_gap",
            )
        )
        next_index += 1
    expected_hash = build_manifest.get("output", {}).get("fillable_template_docx_hash")
    if fillable_template_docx.exists() and expected_hash != sha256_file(fillable_template_docx):
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "build_manifest_output_hash_mismatch",
                "T6 manifest output hash must match fillable template",
                str(expected_hash),
                sha256_file(fillable_template_docx),
                root_cause_bucket="template_t6_hash_gap",
            )
        )
        next_index += 1
    if _docx_contains_internal_marker(fillable_template_docx):
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "fillable_template_internal_marker_residue",
                "T6 output must not contain internal DOCFIT text markers",
                "no [[DOCFIT_*]] text",
                "marker found",
                root_cause_bucket="template_t6_marker_residue",
            )
        )
        next_index += 1
    sdt_tags = _sdt_tags(fillable_template_docx)
    required_tags = {
        str(element.get("stable_id"))
        for unit in template_spec.get("units", [])
        for element in unit.get("elements", [])
        if element.get("policy") in {"fill", "manual_only"}
    }
    manifest_tags = {
        str(slot.get("sdt_tag"))
        for slot in build_manifest.get("slots", [])
        if slot.get("sdt_tag")
    }
    missing_tags = sorted(required_tags - sdt_tags - manifest_tags)
    if missing_tags:
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "fillable_template_sdt_tag_missing",
                "T6 fill/manual elements must be content controls with tags",
                repr(sorted(required_tags)),
                repr(missing_tags),
                affected_ids=missing_tags,
                root_cause_bucket="template_t6_sdt_gap",
            )
        )
        next_index += 1
    for action in build_manifest.get("actions_requiring_review", []):
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.UNKNOWN,
                "build_action_needs_review",
                "T6 build action requires human review",
                "all actions executed",
                str(action.get("reason") or action.get("action_id")),
                affected_ids=[str(action.get("action_id"))],
                root_cause_bucket="template_t6_action_review",
            )
        )
        next_index += 1
    page_policy_results = build_manifest.get("page_policy_results") or []
    results_by_unit = {
        str(item.get("unit_id") or ""): item
        for item in page_policy_results
        if isinstance(item, dict) and item.get("unit_id")
    }
    for unit in template_spec.get("units", []):
        unit_id = str(unit.get("unit_id") or "")
        page = unit.get("page") or {}
        known_values = page_policy_known_values(page)
        if known_values and unit_id not in results_by_unit:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    "build_page_policy_result_missing",
                    "T6 must report a result for each known T2 page policy",
                    repr(known_values),
                    "missing",
                    affected_ids=[unit_id] if unit_id else [],
                    root_cause_bucket="template_t6_page_policy_drop",
                )
            )
            next_index += 1
            continue
        result = results_by_unit.get(unit_id)
        if result is not None and result.get("status") == "manual_review":
            status = Status.UNKNOWN if page_policy_has_unknown(page) else Status.FAIL
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    status,
                    "build_page_policy_needs_review",
                    "T6 page policy is not fully executable",
                    "executed, no_action_required, or already_satisfied",
                    str(result.get("reason") or unit_id),
                    affected_ids=[unit_id] if unit_id else [],
                    root_cause_bucket="template_t6_page_policy_review",
                )
            )
            next_index += 1
    return findings


def _duplicate_id_findings(
    items: list[dict[str, Any]],
    keys: list[str],
    *,
    stage: str,
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []
    next_index = start_index
    for key in keys:
        values = [str(item.get(key)) for item in items if item.get(key)]
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            findings.append(
                make_finding(
                    next_index,
                    "template_generate",
                    Status.FAIL,
                    f"{stage.lower()}_duplicate_{key}",
                    f"{stage} ids must be unique",
                    f"unique {key}",
                    repr(duplicates),
                    root_cause_bucket=f"template_{stage.lower()}_id_gap",
                )
            )
            next_index += 1
    return findings


def _flag_findings(
    flags: list[dict[str, Any]],
    *,
    start_index: int,
    stage: str,
) -> list[Finding]:
    findings: list[Finding] = []
    for offset, flag in enumerate(flags):
        status = Status(str(flag.get("status") or "UNKNOWN"))
        findings.append(
            make_finding(
                start_index + offset,
                "template_generate",
                status,
                f"{stage.lower()}_{flag.get('type', 'flag')}",
                f"{stage} has unresolved flag",
                "flag reviewed or resolved",
                str(flag.get("reason") or flag.get("source_ref") or flag),
                evidence_refs=[str(flag.get("source_ref") or "")],
                affected_ids=[str(item) for item in flag.get("affected_ids", [])],
                root_cause_bucket=f"template_{stage.lower()}_flag",
            )
        )
    return findings


def _is_page_field_evidence(field: dict[str, Any]) -> bool:
    field_type = str(field.get("field_type") or "").upper()
    instruction = str(field.get("instruction") or field.get("field_code") or "").upper()
    return field_type == "PAGE" or instruction.startswith("PAGE")


def _unit_source_seq_range(unit: dict[str, Any]) -> dict[str, int] | None:
    refs = [
        int(ref)
        for ref in unit.get("source_seq_refs", [])
        if _int_or_none(ref) is not None
    ]
    if refs:
        return {"start": min(refs), "end": max(refs)}
    source_seq_range = unit.get("source_seq_range") or {}
    start = _int_or_none(source_seq_range.get("start"))
    end = _int_or_none(source_seq_range.get("end"))
    if start is None or end is None:
        return None
    return {"start": start, "end": end}


def _ranges_overlap(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    left_start = _int_or_none(left.get("start"))
    left_end = _int_or_none(left.get("end"))
    right_start = _int_or_none(right.get("start"))
    right_end = _int_or_none(right.get("end"))
    if None in {left_start, left_end, right_start, right_end}:
        return False
    return int(left_start) <= int(right_end) and int(right_start) <= int(left_end)


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _status_for_findings(findings: list[Finding]) -> Status:
    return merge_statuses([finding.status for finding in findings]) if findings else Status.PASS


def _stage_report(stage: str, artifact: dict[str, Any], status: Status) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": status.value,
        "artifact_type": artifact.get("artifact_type"),
        "output_hash": sha256_json(artifact),
    }


def _first_bad_stage(stage_reports: list[dict[str, Any]]) -> str | None:
    for stage in stage_reports:
        if stage.get("status") != Status.PASS.value:
            return str(stage.get("stage"))
    return None


def _docx_contains_internal_marker(path: Path) -> bool:
    if not path.exists():
        return False
    with ZipFile(path) as package:
        for name in package.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            if b"[[DOCFIT_" in package.read(name):
                return True
    return False


def _sdt_tags(path: Path) -> set[str]:
    tags: set[str] = set()
    if not path.exists():
        return tags
    with ZipFile(path) as package:
        for name in package.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            try:
                root = ET.fromstring(package.read(name))
            except ET.ParseError:
                continue
            for tag in root.iter(f"{W_NS}tag"):
                value = tag.attrib.get(f"{W_NS}val")
                if value:
                    tags.add(value)
    return tags
