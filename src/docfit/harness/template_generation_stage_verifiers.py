from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docfit.core.models import Finding, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.harness.template_generation_run_bundle import (
    BoundArtifact,
    TemplateGenerationRunBundle,
)
from docfit.harness.template_generation_standard_quality import (
    StageStandardSpec,
    TemplateGenerationStandardQualityReport,
    TemplateGenerationStandardSet,
    TEMPLATE_GENERATION_STAGE_KEYS,
)
from docfit.template_generation.artifacts import source_tree_from_document_facts
from docfit.template_generation.t2_standard import audit_unit_map_against_t2_standard


@dataclass
class StageCheck:
    stage_key: str
    stage_id: str
    verifier_state: str
    gate_enabled: bool
    standard_path: Path | None
    standard_sha256: str | None
    artifact_path: Path | None
    artifact_sha256: str | None
    status: Status
    audit_status: str | None
    findings: list[Finding]
    audit: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_key": self.stage_key,
            "stage_id": self.stage_id,
            "verifier_state": self.verifier_state,
            "gate_enabled": self.gate_enabled,
            "standard_path": str(self.standard_path) if self.standard_path else None,
            "standard_sha256": self.standard_sha256,
            "artifact_path": str(self.artifact_path) if self.artifact_path else None,
            "artifact_sha256": self.artifact_sha256,
            "status": self.status.value,
            "audit_status": self.audit_status,
            "findings": [finding.to_dict() for finding in self.findings],
            "audit": self.audit,
        }


def run_template_generation_stage_verifiers(
    *,
    standard_set: TemplateGenerationStandardSet,
    standard_quality: TemplateGenerationStandardQualityReport,
    run_bundle: TemplateGenerationRunBundle,
) -> list[StageCheck]:
    return [
        judge_template_generation_stage(
            stage_key,
            standard=standard_set.stages.get(stage_key),
            artifact=run_bundle.artifact_for_stage(stage_key),
            standard_quality=standard_quality,
            run_bundle=run_bundle,
        )
        for stage_key in TEMPLATE_GENERATION_STAGE_KEYS
    ]


def judge_template_generation_stage(
    stage_key: str,
    *,
    standard: StageStandardSpec | None,
    artifact: BoundArtifact | None,
    standard_quality: TemplateGenerationStandardQualityReport,
    run_bundle: TemplateGenerationRunBundle,
) -> StageCheck:
    stage_id = _stage_id(stage_key, standard, artifact)
    findings: list[Finding] = []
    audit: dict[str, Any] = {}
    if standard is None:
        findings.append(
            _stage_finding(
                len(findings) + 1,
                stage_key,
                Status.UNKNOWN,
                "template_generation_stage_standard_missing",
                f"{stage_key} standard is missing",
                "stage standard exists",
                "missing",
                bucket="standard_missing",
            )
        )
        return _check(
            stage_key,
            stage_id,
            standard,
            artifact,
            Status.UNKNOWN,
            "UNKNOWN",
            findings,
            audit,
        )

    stage_quality_status = standard_quality.stage_statuses.get(stage_key, Status.UNKNOWN.value)
    if stage_quality_status != Status.PASS.value:
        findings.append(
            _stage_finding(
                len(findings) + 1,
                stage_key,
                Status.UNKNOWN,
                "template_generation_stage_standard_quality_not_pass",
                f"{stage_key} standard quality is not PASS",
                Status.PASS.value,
                stage_quality_status,
                evidence_refs=[str(standard.path)],
                bucket="standard_invalid",
            )
        )

    if artifact is None or artifact.path is None or artifact.payload is None:
        findings.append(
            _stage_finding(
                len(findings) + 1,
                stage_key,
                Status.UNKNOWN,
                "template_generation_stage_artifact_missing",
                f"{stage_key} run artifact is missing",
                standard.artifact_under_test,
                "missing",
                bucket="run_bundle_missing",
            )
        )
        return _check(
            stage_key,
            stage_id,
            standard,
            artifact,
            Status.UNKNOWN,
            "UNKNOWN",
            findings,
            audit,
        )

    if run_bundle.status != Status.PASS:
        findings.append(
            _stage_finding(
                len(findings) + 1,
                stage_key,
                Status.UNKNOWN,
                "template_generation_run_bundle_not_pass",
                "Run bundle evidence binding is not PASS",
                Status.PASS.value,
                run_bundle.status.value,
                evidence_refs=[str(artifact.path)],
                bucket="run_bundle_invalid",
            )
        )

    audit, audit_findings = _run_stage_audit(
        stage_key,
        standard,
        artifact,
        run_bundle,
        start_index=len(findings) + 1,
    )
    findings.extend(audit_findings)
    audit_status = _audit_status(audit_findings)
    audit["audit_status"] = audit_status

    status = _gate_status(
        audit_status,
        standard=standard,
        existing_findings=findings,
        stage_key=stage_key,
    )
    if standard.verifier_state != "configured":
        findings.append(
            _stage_finding(
                len(findings) + 1,
                stage_key,
                Status.UNKNOWN,
                "template_generation_stage_verifier_not_configured",
                f"{stage_key} verifier is not configured, so gate status cannot PASS",
                "verifier_state=configured",
                standard.verifier_state,
                evidence_refs=[str(standard.path)],
                bucket="verifier_missing",
            )
        )
    elif not standard.gate_enabled:
        findings.append(
            _stage_finding(
                len(findings) + 1,
                stage_key,
                Status.UNKNOWN,
                "template_generation_stage_gate_disabled",
                f"{stage_key} verifier is configured but gate_enabled is false",
                "gate_enabled=true",
                "false",
                evidence_refs=[str(standard.path)],
                bucket="verifier_disabled",
            )
        )

    if standard.verifier_state != "configured" or not standard.gate_enabled:
        status = Status.UNKNOWN
    else:
        status = merge_statuses(
            [status]
            + [
                finding.status
                for finding in findings
                if finding.severity == "blocking"
            ]
        )
    return _check(
        stage_key,
        stage_id,
        standard,
        artifact,
        status,
        audit_status,
        findings,
        audit,
    )


def _run_stage_audit(
    stage_key: str,
    standard: StageStandardSpec,
    artifact: BoundArtifact,
    run_bundle: TemplateGenerationRunBundle,
    *,
    start_index: int,
) -> tuple[dict[str, Any], list[Finding]]:
    dispatch = {
        "t1_document_facts": _audit_t1_document_facts,
        "t2_unit_pagination": _audit_t2_unit_pagination,
        "t3_element_policy": _audit_t3_element_policy,
        "t4_global_layout": _audit_t4_global_layout,
        "t5_template_spec": _audit_t5_template_spec,
    }
    return dispatch[stage_key](
        standard,
        artifact.payload or {},
        run_bundle,
        start_index=start_index,
    )


def _audit_t1_document_facts(
    standard: StageStandardSpec,
    payload: dict[str, Any],
    run_bundle: TemplateGenerationRunBundle,
    *,
    start_index: int,
) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    expected = standard.expected
    contract = expected.get("source_fact_contract", {})
    if payload.get("artifact_type") != expected.get("artifact_type", "document_facts"):
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t1_artifact_type_mismatch",
                "T1 artifact_type must match the stage standard",
                expected.get("artifact_type", "document_facts"),
                payload.get("artifact_type"),
                bucket="artifact_schema",
            )
        )
    missing_top = [
        field
        for field in contract.get("required_top_level_fields", []) or []
        if field not in payload
    ]
    if missing_top:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t1_required_top_level_fields_missing",
                "document_facts is missing required top-level fields",
                contract.get("required_top_level_fields", []),
                missing_top,
                affected_ids=missing_top,
                bucket="artifact_schema",
            )
        )
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    missing_groups = [
        group
        for group in contract.get("required_data_groups", []) or []
        if group not in data
    ]
    if missing_groups:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t1_required_data_groups_missing",
                "document_facts.data is missing required groups",
                contract.get("required_data_groups", []),
                missing_groups,
                affected_ids=missing_groups,
                bucket="artifact_schema",
            )
        )
    locator_contract = contract.get("locator_contract", {})
    visible_missing = _visible_body_flow_locator_gaps(
        payload,
        source_seq_required=bool(
            locator_contract.get("source_seq_required_for_visible_body_flow")
        ),
        source_ref_required=bool(
            locator_contract.get("source_ref_required_for_visible_body_flow")
        ),
    )
    if visible_missing:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.FAIL,
                "t1_visible_body_flow_locator_missing",
                "Visible body_flow entries must keep source_seq/source_ref locators",
                "source_seq and source_ref on visible body_flow entries",
                visible_missing[:20],
                affected_ids=[str(item.get("node_id")) for item in visible_missing[:20]],
                bucket="artifact_trace",
            )
        )
    forbidden_paths = _forbidden_key_paths(
        payload,
        set(expected.get("forbidden_semantic_fields", []) or []),
    )
    if forbidden_paths:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.FAIL,
                "t1_forbidden_semantic_fields_present",
                "T1 must not emit semantic judgement fields",
                expected.get("forbidden_semantic_fields", []),
                forbidden_paths[:30],
                affected_ids=forbidden_paths[:30],
                bucket="stage_boundary",
            )
        )
    return {
        "artifact_type": payload.get("artifact_type"),
        "missing_top_level_fields": missing_top,
        "missing_data_groups": missing_groups,
        "visible_locator_gaps": visible_missing,
        "forbidden_semantic_field_paths": forbidden_paths,
    }, findings


def _audit_t2_unit_pagination(
    standard: StageStandardSpec,
    payload: dict[str, Any],
    run_bundle: TemplateGenerationRunBundle,
    *,
    start_index: int,
) -> tuple[dict[str, Any], list[Finding]]:
    source_tree = None
    document_facts = run_bundle.payload("document_facts")
    if isinstance(document_facts, dict):
        source_tree = source_tree_from_document_facts(document_facts)
    audit = audit_unit_map_against_t2_standard(
        payload,
        standard.raw,
        source_tree=source_tree,
    )
    findings = [
        _raw_audit_finding(
            start_index + index,
            standard.stage_key,
            raw,
            bucket="template_generation_t2_standard",
        )
        for index, raw in enumerate(audit.get("findings", []))
    ]
    if payload.get("artifact_type") != "unit_map":
        findings.insert(
            0,
            _audit_finding(
                start_index,
                standard.stage_key,
                Status.UNKNOWN,
                "t2_artifact_type_mismatch",
                "T2 artifact_type must be unit_map",
                "unit_map",
                payload.get("artifact_type"),
                bucket="artifact_schema",
            ),
        )
    return audit, findings


def _audit_t3_element_policy(
    standard: StageStandardSpec,
    payload: dict[str, Any],
    run_bundle: TemplateGenerationRunBundle,
    *,
    start_index: int,
) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    expected = standard.expected
    elements = _dict_items(payload.get("elements"))
    if payload.get("artifact_type") != "element_spec":
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t3_artifact_type_mismatch",
                "T3 artifact_type must be element_spec",
                "element_spec",
                payload.get("artifact_type"),
                bucket="artifact_schema",
            )
        )
    expected_order = _string_list(expected.get("unit_order"))
    actual_order = _unique_preserving_order(
        str(element.get("unit_id"))
        for element in elements
        if element.get("unit_id") is not None
    )
    if expected_order and actual_order != expected_order:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.FAIL,
                "t3_unit_order_mismatch",
                "Element spec unit order must match the stage standard",
                expected_order,
                actual_order,
                bucket="stage_standard_mismatch",
            )
        )
    policy_groups = expected.get("policy_groups", {})
    conflicts = _t3_policy_group_conflicts(elements, policy_groups)
    if conflicts:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.FAIL,
                "t3_policy_group_conflict",
                "Element policies must not conflict with unit policy groups",
                policy_groups,
                conflicts[:30],
                affected_ids=[
                    str(item.get("stable_id") or item.get("element_id"))
                    for item in conflicts[:30]
                ],
                bucket="stage_standard_mismatch",
            )
        )
    required_fields = (
        expected.get("element_policy_contract", {}).get("required_fields_by_policy", {})
    )
    missing_required = _required_policy_field_gaps(elements, required_fields)
    if missing_required:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.FAIL,
                "t3_required_policy_fields_missing",
                "Elements must carry fields required by their policy",
                required_fields,
                missing_required[:30],
                affected_ids=[
                    str(item.get("stable_id") or item.get("element_id"))
                    for item in missing_required[:30]
                ],
                bucket="artifact_schema",
            )
        )
    element_expectation_gaps = _t3_element_expectation_gaps(
        elements,
        _dict_items(expected.get("element_expectations")),
    )
    if element_expectation_gaps:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.FAIL,
                "t3_element_expectation_mismatch",
                "Human-reviewed element expectations must match element_spec",
                expected.get("element_expectations", []),
                element_expectation_gaps[:30],
                affected_ids=[
                    str(item.get("stable_id") or item.get("element_ref"))
                    for item in element_expectation_gaps[:30]
                ],
                bucket="stage_standard_mismatch",
            )
        )
    run_level_gaps = _t3_run_level_element_gaps(
        elements,
        _dict_items(expected.get("run_level_elements")),
    )
    if run_level_gaps:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.FAIL,
                "t3_run_level_element_mismatch",
                "Run-level element expectations must match element_spec",
                expected.get("run_level_elements", []),
                run_level_gaps[:30],
                affected_ids=[
                    str(item.get("unit_id") or item.get("source_seq"))
                    for item in run_level_gaps[:30]
                ],
                bucket="stage_standard_mismatch",
            )
        )
    run_span_gaps = _t3_run_span_ledger_gaps(
        elements,
        _dict_items(expected.get("run_span_ledger")),
    )
    if run_span_gaps:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.FAIL,
                "t3_run_span_ledger_mismatch",
                "Run/span ledger expectations must match element_spec coverage",
                expected.get("run_span_ledger", []),
                run_span_gaps[:30],
                affected_ids=[
                    str(item.get("raw_run_id") or item.get("logical_run_id"))
                    for item in run_span_gaps[:30]
                ],
                bucket="stage_standard_mismatch",
            )
        )
    return {
        "artifact_type": payload.get("artifact_type"),
        "expected_unit_order": expected_order,
        "actual_unit_order": actual_order,
        "policy_group_conflicts": conflicts,
        "required_policy_field_gaps": missing_required,
        "element_expectation_gaps": element_expectation_gaps,
        "run_level_element_gaps": run_level_gaps,
        "run_span_ledger_gaps": run_span_gaps,
    }, findings


def _audit_t4_global_layout(
    standard: StageStandardSpec,
    payload: dict[str, Any],
    run_bundle: TemplateGenerationRunBundle,
    *,
    start_index: int,
) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    expected = standard.expected
    contract = expected.get("global_layout_contract")
    if payload.get("artifact_type") != "global_spec":
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t4_artifact_type_mismatch",
                "T4 artifact_type must be global_spec",
                "global_spec",
                payload.get("artifact_type"),
                bucket="artifact_schema",
            )
        )
    if not isinstance(contract, dict):
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t4_global_layout_contract_missing",
                "T4 standard must declare expected.global_layout_contract",
                "expected.global_layout_contract",
                "missing",
                bucket="standard_invalid",
            )
        )
    required_fields = ["section_profiles", "page_numbering", "header_footer", "numbering_rules"]
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t4_global_spec_evidence_fields_missing",
                "global_spec must expose layout evidence fields",
                required_fields,
                missing_fields,
                affected_ids=missing_fields,
                bucket="artifact_schema",
            )
        )
    if not _dict_items(payload.get("section_profiles")):
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t4_section_profiles_missing",
                "global_spec must include at least one section profile",
                "non-empty section_profiles",
                payload.get("section_profiles"),
                bucket="artifact_schema",
            )
        )
    page_numbering = payload.get("page_numbering")
    if not isinstance(page_numbering, dict):
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t4_page_numbering_missing",
                "global_spec must include page_numbering evidence",
                "page_numbering object",
                page_numbering,
                bucket="artifact_schema",
            )
        )
    return {
        "artifact_type": payload.get("artifact_type"),
        "has_global_layout_contract": isinstance(contract, dict),
        "missing_evidence_fields": missing_fields,
        "section_profile_count": len(_dict_items(payload.get("section_profiles"))),
        "page_numbering_status": page_numbering.get("status")
        if isinstance(page_numbering, dict)
        else None,
    }, findings


def _audit_t5_template_spec(
    standard: StageStandardSpec,
    payload: dict[str, Any],
    run_bundle: TemplateGenerationRunBundle,
    *,
    start_index: int,
) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    expected = standard.expected
    if payload.get("artifact_type") != "template_spec":
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t5_artifact_type_mismatch",
                "T5 artifact_type must be template_spec",
                "template_spec",
                payload.get("artifact_type"),
                bucket="artifact_schema",
            )
        )
    units = _dict_items(payload.get("units"))
    actual_order = [
        str(unit.get("unit_id"))
        for unit in units
        if unit.get("unit_id") is not None
    ]
    expected_order = _string_list(expected.get("unit_order"))
    if expected_order and actual_order != expected_order:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.FAIL,
                "t5_unit_order_mismatch",
                "template_spec unit order must match the stage standard",
                expected_order,
                actual_order,
                bucket="stage_standard_mismatch",
            )
        )
    contract = expected.get("template_spec_contract", {})
    required_hashes = _string_list(contract.get("required_input_hashes"))
    input_hashes = payload.get("input_hashes") if isinstance(payload.get("input_hashes"), dict) else {}
    missing_hashes = [key for key in required_hashes if key not in input_hashes]
    if missing_hashes:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t5_required_input_hashes_missing",
                "template_spec must bind upstream input hashes",
                required_hashes,
                missing_hashes,
                affected_ids=missing_hashes,
                bucket="artifact_trace",
            )
        )
    missing_section_refs = [
        str(unit.get("unit_id"))
        for unit in units
        if not unit.get("section_profile_refs")
    ]
    if missing_section_refs:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.UNKNOWN,
                "t5_unit_section_profile_refs_missing",
                "Every template_spec unit must keep section_profile_refs",
                "section_profile_refs on every unit",
                missing_section_refs,
                affected_ids=missing_section_refs,
                bucket="artifact_trace",
            )
        )
    missing_flags = _review_flag_gaps(payload, run_bundle)
    if missing_flags:
        findings.append(
            _audit_finding(
                start_index + len(findings),
                standard.stage_key,
                Status.FAIL,
                "t5_review_flags_dropped",
                "template_spec.review_flags must preserve upstream review flags",
                "all upstream review flags",
                missing_flags[:30],
                bucket="artifact_trace",
            )
        )
    return {
        "artifact_type": payload.get("artifact_type"),
        "expected_unit_order": expected_order,
        "actual_unit_order": actual_order,
        "missing_input_hashes": missing_hashes,
        "missing_section_profile_refs": missing_section_refs,
        "missing_review_flags": missing_flags,
    }, findings


def _visible_body_flow_locator_gaps(
    payload: dict[str, Any],
    *,
    source_seq_required: bool,
    source_ref_required: bool,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for item in _dict_items(payload.get("body_flow")):
        if not _is_visible_body_flow_item(item):
            continue
        missing: list[str] = []
        if source_seq_required and item.get("source_seq") is None:
            missing.append("source_seq")
        if source_ref_required and not item.get("source_ref"):
            missing.append("source_ref")
        if missing:
            gaps.append(
                {
                    "node_id": item.get("node_id"),
                    "missing": missing,
                    "text": item.get("text"),
                }
            )
    return gaps


def _is_visible_body_flow_item(item: dict[str, Any]) -> bool:
    if item.get("text"):
        return True
    if item.get("kind") in {"table", "image", "drawing", "field"}:
        return True
    return bool(item.get("source_ref"))


def _forbidden_key_paths(value: Any, forbidden: set[str], prefix: str = "$") -> list[str]:
    if not forbidden:
        return []
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            if str(key) in forbidden:
                paths.append(child_path)
            paths.extend(_forbidden_key_paths(child, forbidden, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_forbidden_key_paths(child, forbidden, f"{prefix}[{index}]"))
    return paths


def _t3_policy_group_conflicts(
    elements: list[dict[str, Any]],
    policy_groups: dict[str, Any],
) -> list[dict[str, Any]]:
    manual_only_units = set(_string_list(policy_groups.get("manual_only_units")))
    generated_units = set(_string_list(policy_groups.get("generated_units")))
    fixed_units = set(_string_list(policy_groups.get("fixed_units")))
    fixed_units_allow_fill = set(
        _string_list(policy_groups.get("fixed_units_allow_fill_elements"))
    )
    conflicts: list[dict[str, Any]] = []
    for element in elements:
        unit_id = str(element.get("unit_id") or "")
        policy = str(element.get("policy") or "")
        if unit_id in manual_only_units and policy == "fill":
            conflicts.append({**_element_ref(element), "expected": "manual_only", "actual": policy})
        elif unit_id in generated_units and policy not in {"generated", "fixed", "instruction_remove"}:
            conflicts.append({**_element_ref(element), "expected": "generated", "actual": policy})
        elif unit_id in fixed_units and unit_id not in fixed_units_allow_fill and policy == "fill":
            conflicts.append({**_element_ref(element), "expected": "fixed", "actual": policy})
    return conflicts


def _required_policy_field_gaps(
    elements: list[dict[str, Any]],
    required_fields: dict[str, Any],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for element in elements:
        policy = str(element.get("policy") or "")
        required = _string_list(required_fields.get(policy))
        missing = [field for field in required if _path_value(element, field) in (None, "", [])]
        if missing:
            gaps.append({**_element_ref(element), "policy": policy, "missing": missing})
    return gaps


def _t3_element_expectation_gaps(
    elements: list[dict[str, Any]],
    expectations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for expectation in expectations:
        unit_id = str(expectation.get("unit_id") or "")
        element_id = str(expectation.get("element_id") or "")
        stable_id = str(expectation.get("stable_id") or "")
        if not stable_id and unit_id and element_id:
            stable_id = f"{unit_id}.{element_id}"
        candidates = _t3_element_expectation_candidates(elements, expectation, stable_id)
        if not _t3_has_expected_element(candidates, expectation, stable_id):
            gaps.append(
                {
                    "unit_id": unit_id,
                    "element_id": element_id,
                    "stable_id": stable_id,
                    "element_ref": stable_id or element_id,
                    "expected": expectation,
                    "actual_candidates": [
                        _t3_candidate_summary(candidate) for candidate in candidates[:10]
                    ],
                }
            )
    return gaps


def _t3_element_expectation_candidates(
    elements: list[dict[str, Any]],
    expectation: dict[str, Any],
    stable_id: str,
) -> list[dict[str, Any]]:
    unit_id = str(expectation.get("unit_id") or "")
    unit_candidates = [
        element
        for element in elements
        if not unit_id or str(element.get("unit_id") or "") == unit_id
    ]
    anchors = _content_anchors(expectation)
    if anchors:
        anchor_candidates = [
            element
            for element in unit_candidates
            if all(anchor in str(element.get("content") or "") for anchor in anchors)
        ]
        if anchor_candidates:
            return anchor_candidates
    if stable_id:
        stable_candidates = [
            element
            for element in unit_candidates
            if str(element.get("stable_id") or "") == stable_id
        ]
        if stable_candidates:
            return stable_candidates
    source_seq_refs = {str(ref) for ref in expectation.get("source_seq_refs", []) or []}
    if source_seq_refs:
        source_candidates = [
            element
            for element in unit_candidates
            if source_seq_refs
            <= {str(ref) for ref in element.get("source_seq_refs", []) or []}
        ]
        if source_candidates:
            return source_candidates
    return unit_candidates


def _t3_has_expected_element(
    candidates: list[dict[str, Any]],
    expectation: dict[str, Any],
    stable_id: str,
) -> bool:
    for candidate in candidates:
        if (
            stable_id
            and str(candidate.get("stable_id") or "") != stable_id
            and _t3_requires_exact_stable_ref(expectation)
        ):
            continue
        policy = expectation.get("policy")
        if policy is not None and not _t3_candidate_or_span_policy_matches(
            candidate,
            str(policy),
            expectation,
        ):
            continue
        expected_raw_run_ids = _string_list(expectation.get("raw_run_ids"))
        if expected_raw_run_ids and not _t3_candidate_or_span_contains_runs(
            candidate,
            "raw_run_ids",
            expected_raw_run_ids,
            expectation,
        ):
            continue
        expected_logical_run_ids = _string_list(expectation.get("logical_run_ids"))
        if expected_logical_run_ids and not _t3_candidate_or_span_contains_runs(
            candidate,
            "logical_run_ids",
            expected_logical_run_ids,
            expectation,
        ):
            continue
        if not _content_matches(candidate, expectation):
            continue
        return True
    return False


def _t3_run_level_element_gaps(
    elements: list[dict[str, Any]],
    expectations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for expectation in expectations:
        unit_id = str(expectation.get("unit_id") or "")
        source_seq = str(expectation.get("source_seq") or "")
        expected_elements = _dict_items(expectation.get("expected_elements"))
        candidates = [
            element
            for element in elements
            if str(element.get("unit_id") or "") == unit_id
            and (
                not source_seq
                or source_seq
                in {str(ref) for ref in element.get("source_seq_refs", []) or []}
            )
        ]
        for expected_element in expected_elements:
            if not _t3_has_expected_run_level_element(candidates, expected_element):
                gaps.append(
                    {
                        "unit_id": unit_id,
                        "source_seq": expectation.get("source_seq"),
                        "expected": expected_element,
                        "actual_candidates": [
                            {
                                **_element_ref(candidate),
                                "policy": candidate.get("policy"),
                                "content": candidate.get("content"),
                                "raw_run_ids": candidate.get("raw_run_ids", []),
                                "logical_run_ids": candidate.get("logical_run_ids", []),
                                "source_seq_refs": candidate.get("source_seq_refs", []),
                            }
                            for candidate in candidates
                        ],
                    }
                )
    return gaps


def _t3_has_expected_run_level_element(
    candidates: list[dict[str, Any]],
    expected_element: dict[str, Any],
) -> bool:
    for candidate in candidates:
        policy = expected_element.get("policy")
        if policy is not None and not _t3_candidate_or_span_policy_matches(
            candidate,
            str(policy),
            expected_element,
        ):
            continue
        expected_raw_run_ids = _string_list(expected_element.get("raw_run_ids"))
        if expected_raw_run_ids and not _t3_candidate_or_span_runs_equal(
            candidate,
            "raw_run_ids",
            expected_raw_run_ids,
            expected_element,
        ):
            continue
        expected_logical_run_ids = _string_list(expected_element.get("logical_run_ids"))
        if expected_logical_run_ids and not _t3_candidate_or_span_runs_equal(
            candidate,
            "logical_run_ids",
            expected_logical_run_ids,
            expected_element,
        ):
            continue
        content_contains = str(expected_element.get("content_contains") or "")
        if content_contains and not _t3_candidate_or_span_contains_text(
            candidate,
            content_contains,
            expected_element,
        ):
            continue
        return True
    return False


def _t3_run_span_ledger_gaps(
    elements: list[dict[str, Any]],
    ledger: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for expectation in ledger:
        raw_run_id = str(expectation.get("raw_run_id") or "")
        logical_run_id = str(expectation.get("logical_run_id") or "")
        candidates = [
            element
            for element in elements
            if (raw_run_id and raw_run_id in _string_list(element.get("raw_run_ids")))
            or (
                logical_run_id
                and logical_run_id in _string_list(element.get("logical_run_ids"))
            )
        ]
        if not _t3_has_expected_run_span(candidates, expectation):
            gaps.append(
                {
                    "raw_run_id": raw_run_id,
                    "logical_run_id": logical_run_id,
                    "source_seq": expectation.get("source_seq"),
                    "expected": expectation,
                    "actual_candidates": [
                        _t3_candidate_summary(candidate) for candidate in candidates[:10]
                    ],
                }
            )
    return gaps


def _t3_has_expected_run_span(
    candidates: list[dict[str, Any]],
    expectation: dict[str, Any],
) -> bool:
    for candidate in candidates:
        unit_id = expectation.get("unit_id")
        if unit_id is not None and str(candidate.get("unit_id") or "") != str(unit_id):
            continue
        policy = expectation.get("expected_policy", expectation.get("policy"))
        if policy is not None and not _t3_candidate_or_span_policy_matches(
            candidate,
            str(policy),
            expectation,
        ):
            continue
        element_ref = str(
            expectation.get("expected_element_ref")
            or expectation.get("stable_id")
            or ""
        )
        if (
            element_ref
            and str(candidate.get("stable_id") or "") != element_ref
            and _t3_requires_exact_stable_ref(expectation)
        ):
            continue
        if not _content_matches(candidate, expectation):
            continue
        return True
    return False


def _t3_candidate_or_span_policy_matches(
    candidate: dict[str, Any],
    expected_policy: str,
    expectation: dict[str, Any],
) -> bool:
    if str(candidate.get("policy") or "") == expected_policy:
        return True
    return any(
        _t3_span_matches_expectation(span, expected_policy, expectation)
        for span in _dict_items(candidate.get("spans"))
    )


def _t3_candidate_or_span_contains_runs(
    candidate: dict[str, Any],
    run_key: str,
    expected_ids: list[str],
    expectation: dict[str, Any],
) -> bool:
    if _contains_all(_string_list(candidate.get(run_key)), expected_ids):
        return True
    expected_policy = str(
        expectation.get("expected_policy") or expectation.get("policy") or ""
    )
    return any(
        _contains_all(_string_list(span.get(run_key)), expected_ids)
        and (not expected_policy or _t3_span_policy_matches(span, expected_policy))
        for span in _dict_items(candidate.get("spans"))
    )


def _t3_candidate_or_span_runs_equal(
    candidate: dict[str, Any],
    run_key: str,
    expected_ids: list[str],
    expectation: dict[str, Any],
) -> bool:
    if _string_list(candidate.get(run_key)) == expected_ids:
        return True
    expected_policy = str(
        expectation.get("expected_policy") or expectation.get("policy") or ""
    )
    return any(
        _string_list(span.get(run_key)) == expected_ids
        and (not expected_policy or _t3_span_policy_matches(span, expected_policy))
        for span in _dict_items(candidate.get("spans"))
    )


def _t3_candidate_or_span_contains_text(
    candidate: dict[str, Any],
    needle: str,
    expectation: dict[str, Any],
) -> bool:
    if needle in str(candidate.get("content") or ""):
        return True
    expected_policy = str(
        expectation.get("expected_policy") or expectation.get("policy") or ""
    )
    return any(
        needle in str(span.get("text") or "")
        and (not expected_policy or _t3_span_policy_matches(span, expected_policy))
        for span in _dict_items(candidate.get("spans"))
    )


def _t3_span_matches_expectation(
    span: dict[str, Any],
    expected_policy: str,
    expectation: dict[str, Any],
) -> bool:
    if not _t3_span_policy_matches(span, expected_policy):
        return False
    expected_raw_run_ids = _t3_expected_run_ids(expectation, "raw_run_ids", "raw_run_id")
    if expected_raw_run_ids and not _contains_all(
        _string_list(span.get("raw_run_ids")),
        expected_raw_run_ids,
    ):
        return False
    expected_logical_run_ids = _t3_expected_run_ids(
        expectation,
        "logical_run_ids",
        "logical_run_id",
    )
    if expected_logical_run_ids and not _contains_all(
        _string_list(span.get("logical_run_ids")),
        expected_logical_run_ids,
    ):
        return False
    anchors = _content_anchors(expectation)
    if anchors and not all(anchor in str(span.get("text") or "") for anchor in anchors):
        return False
    return True


def _t3_span_policy_matches(span: dict[str, Any], expected_policy: str) -> bool:
    span_policy = str(span.get("policy") or "")
    span_type = str(span.get("span_type") or "")
    if span_policy == expected_policy:
        return True
    if expected_policy == "instruction_remove":
        return span_policy == "remove_instruction" or span_type in {
            "inline_instruction",
            "layout_spacer",
        }
    if expected_policy == "fill":
        return span_type == "sample_value"
    if expected_policy == "fixed":
        return span_type == "label"
    return False


def _t3_expected_run_ids(
    expectation: dict[str, Any],
    list_key: str,
    scalar_key: str,
) -> list[str]:
    values = _string_list(expectation.get(list_key))
    scalar = expectation.get(scalar_key)
    if scalar is not None:
        values.append(str(scalar))
    return _unique_preserving_order(values)


def _t3_requires_exact_stable_ref(expectation: dict[str, Any]) -> bool:
    if _content_anchors(expectation):
        return False
    if expectation.get("source_seq_refs") or expectation.get("source_seq") is not None:
        return False
    if _t3_expected_run_ids(expectation, "raw_run_ids", "raw_run_id"):
        return False
    if _t3_expected_run_ids(expectation, "logical_run_ids", "logical_run_id"):
        return False
    return True


def _content_matches(candidate: dict[str, Any], expectation: dict[str, Any]) -> bool:
    content = str(candidate.get("content") or "")
    return all(anchor in content for anchor in _content_anchors(expectation))


def _content_anchors(expectation: dict[str, Any]) -> list[str]:
    anchors: list[str] = []
    for key in ["content_contains", "content_anchor", "text_anchor"]:
        anchors.extend(_string_list(expectation.get(key)))
    return [anchor for anchor in anchors if anchor]


def _contains_all(actual: list[str], expected: list[str]) -> bool:
    actual_set = set(actual)
    return all(item in actual_set for item in expected)


def _t3_candidate_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        **_element_ref(candidate),
        "policy": candidate.get("policy"),
        "content": candidate.get("content"),
        "raw_run_ids": candidate.get("raw_run_ids", []),
        "logical_run_ids": candidate.get("logical_run_ids", []),
        "source_seq_refs": candidate.get("source_seq_refs", []),
    }


def _review_flag_gaps(
    template_spec: dict[str, Any],
    run_bundle: TemplateGenerationRunBundle,
) -> list[str]:
    upstream_flags: list[dict[str, Any]] = []
    for artifact_key in ["unit_map", "element_spec", "global_spec"]:
        payload = run_bundle.payload(artifact_key) or {}
        upstream_flags.extend(_dict_items(payload.get("flags")))
    actual_flags = _dict_items(template_spec.get("review_flags"))
    actual_ids = {_flag_identity(flag) for flag in actual_flags}
    return [
        identity
        for identity in (_flag_identity(flag) for flag in upstream_flags)
        if identity and identity not in actual_ids
    ]


def _flag_identity(flag: dict[str, Any]) -> str:
    if flag.get("flag_id"):
        return str(flag.get("flag_id"))
    parts = [
        str(flag.get("type") or ""),
        str(flag.get("reason") or ""),
        ",".join(str(item) for item in flag.get("affected_ids", []) or []),
    ]
    return "|".join(parts)


def _path_value(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _element_ref(element: dict[str, Any]) -> dict[str, Any]:
    return {
        "stable_id": element.get("stable_id"),
        "element_id": element.get("element_id"),
        "unit_id": element.get("unit_id"),
    }


def _gate_status(
    audit_status: str,
    *,
    standard: StageStandardSpec,
    existing_findings: list[Finding],
    stage_key: str,
) -> Status:
    if standard.verifier_state != "configured" or not standard.gate_enabled:
        return Status.UNKNOWN
    if any(finding.status == Status.UNKNOWN for finding in existing_findings):
        return Status.UNKNOWN
    return Status(audit_status)


def _audit_status(findings: list[Finding]) -> str:
    statuses = [finding.status for finding in findings if finding.severity == "blocking"]
    return merge_statuses(statuses).value if statuses else Status.PASS.value


def _raw_audit_finding(
    index: int,
    stage_key: str,
    raw: dict[str, Any],
    *,
    bucket: str,
) -> Finding:
    status = Status(str(raw.get("status") or Status.UNKNOWN.value))
    return _audit_finding(
        index,
        stage_key,
        status,
        str(raw.get("type") or "stage_audit_finding"),
        str(raw.get("message") or raw.get("type") or "stage audit finding"),
        raw.get("expected"),
        raw.get("actual"),
        affected_ids=[
            str(item) for item in raw.get("affected_ids", []) or []
        ],
        bucket=bucket,
    )


def _audit_finding(
    index: int,
    stage_key: str,
    status: Status,
    type_: str,
    message: str,
    expected: Any,
    actual: Any,
    *,
    affected_ids: list[str] | None = None,
    bucket: str,
) -> Finding:
    return _stage_finding(
        index,
        stage_key,
        status,
        type_,
        message,
        expected,
        actual,
        affected_ids=affected_ids,
        bucket=bucket,
        severity="blocking",
    )


def _stage_finding(
    index: int,
    stage_key: str,
    status: Status,
    type_: str,
    message: str,
    expected: Any,
    actual: Any,
    *,
    evidence_refs: list[str] | None = None,
    affected_ids: list[str] | None = None,
    bucket: str,
    severity: str = "blocking",
) -> Finding:
    return make_finding(
        index,
        stage_key,
        status,
        type_,
        message,
        _stringify(expected),
        _stringify(actual),
        evidence_refs=evidence_refs,
        affected_ids=affected_ids,
        root_cause_bucket=bucket,
        severity=severity,
    )


def _check(
    stage_key: str,
    stage_id: str,
    standard: StageStandardSpec | None,
    artifact: BoundArtifact | None,
    status: Status,
    audit_status: str | None,
    findings: list[Finding],
    audit: dict[str, Any],
) -> StageCheck:
    return StageCheck(
        stage_key=stage_key,
        stage_id=stage_id,
        verifier_state=standard.verifier_state if standard else "missing",
        gate_enabled=standard.gate_enabled if standard else False,
        standard_path=standard.path if standard else None,
        standard_sha256=standard.sha256 if standard else None,
        artifact_path=artifact.path if artifact else None,
        artifact_sha256=artifact.sha256 if artifact else None,
        status=status,
        audit_status=audit_status,
        findings=findings,
        audit=audit,
    )


def _stage_id(
    stage_key: str,
    standard: StageStandardSpec | None,
    artifact: BoundArtifact | None,
) -> str:
    if standard is not None:
        return standard.stage_id
    if artifact is not None and artifact.stage_id:
        return artifact.stage_id
    return stage_key


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [str(value)]
    return [str(item) for item in value if item is not None]


def _unique_preserving_order(values: Any) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return repr(value)
