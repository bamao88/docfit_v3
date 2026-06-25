from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from docfit.core.io import sha256_file, sha256_json
from docfit.core.models import Finding, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.ooxml.package import is_valid_docx


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def verify_template_parse_build(
    *,
    document_facts: dict[str, Any],
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
        "stages": stage_reports,
        "findings": [finding.to_dict() for finding in findings],
    }
    coverage = {
        "template_generation.document_facts": stage_reports[0]["status"] == Status.PASS.value,
        "template_generation.unit_map": stage_reports[1]["status"] == Status.PASS.value,
        "template_generation.element_spec": stage_reports[2]["status"] == Status.PASS.value,
        "template_generation.global_spec": stage_reports[3]["status"] == Status.PASS.value,
        "template_generation.template_spec": stage_reports[4]["status"] == Status.PASS.value,
        "template_generation.fillable_template": stage_reports[5]["status"] == Status.PASS.value,
        "template_generation.verification_report": True,
    }
    return status, findings, report, coverage


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
    if not global_spec.get("section_profiles"):
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
    findings.extend(_flag_findings(global_spec.get("flags", []), start_index=next_index, stage="T4"))
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
    if len(unit_ids) != len(set(unit_ids)):
        findings.append(
            make_finding(
                next_index,
                "template_generate",
                Status.FAIL,
                "template_spec_duplicate_unit_id",
                "T5 unit ids must be unique",
                "unique unit_id",
                repr(unit_ids),
                root_cause_bucket="template_t5_id_gap",
            )
        )
        next_index += 1
    for unit in template_spec.get("units", []):
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
