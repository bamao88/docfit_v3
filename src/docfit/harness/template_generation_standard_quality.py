from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from docfit.core.io import sha256_file
from docfit.core.models import Finding, make_finding
from docfit.core.status import Status, merge_statuses


TEMPLATE_GENERATION_STAGE_KEYS = [
    "t1_document_facts",
    "t2_unit_pagination",
    "t3_element_policy",
    "t4_global_layout",
    "t5_template_spec",
]

STAGE_IDS_BY_KEY = {
    "t1_document_facts": "T1",
    "t2_unit_pagination": "T2",
    "t3_element_policy": "T3",
    "t4_global_layout": "T4",
    "t5_template_spec": "T5",
}

EXPECTED_ARTIFACT_BY_STAGE = {
    "t1_document_facts": "document_facts",
    "t2_unit_pagination": "unit_map",
    "t3_element_policy": "element_spec",
    "t4_global_layout": "global_spec",
    "t5_template_spec": "template_spec",
}


@dataclass
class StageStandardSpec:
    stage_key: str
    stage_id: str
    path: Path
    sha256: str
    verifier_state: str
    gate_enabled: bool
    artifact_under_test: str
    expected: dict[str, Any]
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_key": self.stage_key,
            "stage_id": self.stage_id,
            "path": str(self.path),
            "sha256": self.sha256,
            "verifier_state": self.verifier_state,
            "gate_enabled": self.gate_enabled,
            "artifact_under_test": self.artifact_under_test,
            "standard_id": self.raw.get("standard_id"),
            "standard_state": self.raw.get("standard_state"),
            "school_id": self.raw.get("school_id"),
        }


@dataclass
class TemplateGenerationStandardSet:
    root: Path
    school_id: str
    template_version: str
    target_dir: Path
    target_standard_path: Path
    target_standard: dict[str, Any] = field(default_factory=dict)
    target_standard_sha256: str | None = None
    final_template_path: Path | None = None
    final_template: dict[str, Any] = field(default_factory=dict)
    final_template_sha256: str | None = None
    stages: dict[str, StageStandardSpec] = field(default_factory=dict)
    load_findings: list[Finding] = field(default_factory=list)

    @property
    def source_template_docx_sha256(self) -> str | None:
        value = self.target_standard.get("source", {}).get("template_docx_sha256")
        if value:
            return str(value)
        for stage in self.stages.values():
            value = stage.raw.get("accepted_source_facts", {}).get("template_docx_sha256")
            if value:
                return str(value)
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "school_id": self.school_id,
            "template_version": self.template_version,
            "target_dir": str(self.target_dir),
            "target_standard_path": str(self.target_standard_path),
            "target_standard_sha256": self.target_standard_sha256,
            "final_template_path": str(self.final_template_path)
            if self.final_template_path is not None
            else None,
            "final_template_sha256": self.final_template_sha256,
            "source_template_docx_sha256": self.source_template_docx_sha256,
            "stages": {
                stage_key: stage.to_dict()
                for stage_key, stage in self.stages.items()
            },
        }


@dataclass
class TemplateGenerationStandardQualityReport:
    scope: str
    status: Status
    target_reports: list[dict[str, Any]]
    findings: list[Finding]
    stage_statuses: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": "template_generation_stage_standard_quality_report",
            "artifact_version": "1.0",
            "scope": self.scope,
            "status": self.status.value,
            "stage_statuses": self.stage_statuses,
            "targets": self.target_reports,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def load_template_generation_standard_set(
    root: Path,
    school_id: str,
    template_version: str = "v1",
) -> TemplateGenerationStandardSet:
    target_dir = root / "standards" / "targets" / school_id / template_version
    target_standard_path = target_dir / "target.standard.yaml"
    standard_set = TemplateGenerationStandardSet(
        root=root,
        school_id=school_id,
        template_version=template_version,
        target_dir=target_dir,
        target_standard_path=target_standard_path,
    )
    if not target_standard_path.exists():
        standard_set.load_findings.append(
            _quality_finding(
                len(standard_set.load_findings) + 1,
                "missing_target_standard",
                f"target.standard.yaml is missing for {school_id}/{template_version}",
                "target.standard.yaml exists",
                str(target_standard_path),
                bucket="standard_missing",
            )
        )
        return standard_set

    try:
        target_standard = _load_yaml_dict(target_standard_path)
    except Exception as exc:
        standard_set.load_findings.append(
            _quality_finding(
                len(standard_set.load_findings) + 1,
                "invalid_target_standard_yaml",
                "target.standard.yaml is not valid YAML",
                "valid YAML",
                repr(exc),
                bucket="standard_invalid",
            )
        )
        return standard_set

    standard_set.target_standard = target_standard
    standard_set.target_standard_sha256 = sha256_file(target_standard_path)
    _load_final_template_expected(standard_set)
    _load_stage_standards(standard_set)
    return standard_set


def evaluate_template_generation_standard_quality(
    standard_set: TemplateGenerationStandardSet,
) -> TemplateGenerationStandardQualityReport:
    findings = list(standard_set.load_findings)
    stage_statuses: dict[str, str] = {}
    target_report = standard_set.to_dict()

    if not standard_set.target_standard:
        status = Status.UNKNOWN
        for stage_key in TEMPLATE_GENERATION_STAGE_KEYS:
            stage_statuses[stage_key] = Status.UNKNOWN.value
        return TemplateGenerationStandardQualityReport(
            scope=standard_set.school_id,
            status=status,
            target_reports=[target_report],
            findings=findings,
            stage_statuses=stage_statuses,
        )

    stage_findings_by_key: dict[str, list[Finding]] = {
        stage_key: [] for stage_key in TEMPLATE_GENERATION_STAGE_KEYS
    }
    baselines = standard_set.target_standard.get("evidence_baselines", {})
    stage_refs = baselines.get("template_generation_stages")
    if not isinstance(stage_refs, dict):
        findings.append(
            _quality_finding(
                len(findings) + 1,
                "missing_template_generation_stage_registry",
                "target.standard.yaml does not register template_generation_stages",
                "evidence_baselines.template_generation_stages maps T1-T5 standards",
                "missing",
                bucket="standard_registry",
            )
        )

    if standard_set.final_template_path is None or not standard_set.final_template:
        findings.append(
            _quality_finding(
                len(findings) + 1,
                "missing_final_template_expected",
                "Final template expected standard is missing",
                "template_quality/final_template.expected.yaml exists and is registered",
                str(standard_set.final_template_path),
                bucket="standard_missing",
            )
        )

    expected_source_hash = standard_set.target_standard.get("source", {}).get(
        "template_docx_sha256"
    )
    if not expected_source_hash:
        findings.append(
            _quality_finding(
                len(findings) + 1,
                "missing_source_template_hash",
                "target.standard.yaml does not bind the source template hash",
                "source.template_docx_sha256 is present",
                "missing",
                bucket="standard_missing",
            )
        )

    for stage_key in TEMPLATE_GENERATION_STAGE_KEYS:
        stage_findings = stage_findings_by_key[stage_key]
        stage = standard_set.stages.get(stage_key)
        registered_path = (
            stage_refs.get(stage_key)
            if isinstance(stage_refs, dict)
            else None
        )
        if not registered_path:
            stage_findings.append(
                _quality_finding(
                    len(findings) + len(stage_findings) + 1,
                    "missing_stage_standard_registry_entry",
                    f"{stage_key} is not registered in target.standard.yaml",
                    f"evidence_baselines.template_generation_stages.{stage_key}",
                    "missing",
                    stage=stage_key,
                    bucket="standard_registry",
                )
            )
        elif not str(registered_path).startswith("template_generation/"):
            stage_findings.append(
                _quality_finding(
                    len(findings) + len(stage_findings) + 1,
                    "legacy_stage_standard_registry_entry",
                    f"{stage_key} is registered outside template_generation/",
                    "template_generation/<stage>.standard.yaml",
                    str(registered_path),
                    stage=stage_key,
                    bucket="standard_registry",
                )
            )

        if stage is None:
            stage_findings.append(
                _quality_finding(
                    len(findings) + len(stage_findings) + 1,
                    "missing_stage_standard",
                    f"{stage_key} standard is missing",
                    f"{stage_key}.standard.yaml exists",
                    str(_stage_path(standard_set.target_dir, stage_key, registered_path)),
                    stage=stage_key,
                    bucket="standard_missing",
                )
            )
        else:
            stage_findings.extend(
                _stage_standard_schema_findings(
                    stage,
                    expected_source_hash=str(expected_source_hash)
                    if expected_source_hash
                    else None,
                    final_template=standard_set.final_template,
                    start_index=len(findings) + len(stage_findings) + 1,
                )
            )

        findings.extend(stage_findings)
        stage_statuses[stage_key] = (
            Status.UNKNOWN.value if stage_findings else Status.PASS.value
        )

    unit_order_findings = _cross_stage_unit_order_findings(
        standard_set,
        start_index=len(findings) + 1,
    )
    findings.extend(unit_order_findings)
    for finding in unit_order_findings:
        for affected in finding.affected_ids:
            if affected in stage_statuses:
                stage_statuses[affected] = Status.UNKNOWN.value

    status = merge_statuses([Status(value) for value in stage_statuses.values()])
    if any(finding.severity == "blocking" for finding in findings):
        status = merge_statuses([status] + [finding.status for finding in findings])
    target_report = standard_set.to_dict()
    target_report["stage_quality_statuses"] = stage_statuses
    return TemplateGenerationStandardQualityReport(
        scope=standard_set.school_id,
        status=status,
        target_reports=[target_report],
        findings=findings,
        stage_statuses=stage_statuses,
    )


def evaluate_template_generation_standard_quality_for_profile(
    root: Path,
    profile_id: str,
    template_version: str = "v1",
) -> TemplateGenerationStandardQualityReport:
    sets = list(
        iter_template_generation_standard_sets_for_profile(
            root,
            profile_id,
            template_version,
        )
    )
    if not sets:
        finding = _quality_finding(
            1,
            "profile_targets_missing",
            f"No targets are registered for profile {profile_id}",
            "at least one target.standard.yaml with coverage_requirements.profile",
            profile_id,
            bucket="standard_missing",
        )
        return TemplateGenerationStandardQualityReport(
            scope=profile_id,
            status=Status.UNKNOWN,
            target_reports=[],
            findings=[finding],
            stage_statuses={},
        )

    child_reports = [
        evaluate_template_generation_standard_quality(standard_set)
        for standard_set in sets
    ]
    findings = [
        finding
        for report in child_reports
        for finding in report.findings
    ]
    stage_statuses = {
        f"{target['school_id']}.{stage_key}": status
        for report in child_reports
        for target in report.target_reports
        for stage_key, status in report.stage_statuses.items()
    }
    status = merge_statuses([report.status for report in child_reports])
    return TemplateGenerationStandardQualityReport(
        scope=profile_id,
        status=status,
        target_reports=[
            target
            for report in child_reports
            for target in report.target_reports
        ],
        findings=findings,
        stage_statuses=stage_statuses,
    )


def iter_template_generation_standard_sets_for_profile(
    root: Path,
    profile_id: str,
    template_version: str = "v1",
) -> list[TemplateGenerationStandardSet]:
    targets_root = root / "standards" / "targets"
    if not targets_root.exists():
        return []
    standard_sets: list[TemplateGenerationStandardSet] = []
    for target_dir in sorted(path for path in targets_root.iterdir() if path.is_dir()):
        standard_set = load_template_generation_standard_set(
            root,
            target_dir.name,
            template_version,
        )
        if (
            standard_set.target_standard.get("coverage_requirements", {}).get("profile")
            == profile_id
        ):
            standard_sets.append(standard_set)
    return standard_sets


def _load_final_template_expected(standard_set: TemplateGenerationStandardSet) -> None:
    baselines = standard_set.target_standard.get("evidence_baselines", {})
    rel_path = baselines.get("template_generation_final")
    path = (
        standard_set.target_dir / str(rel_path)
        if rel_path
        else standard_set.target_dir / "template_quality" / "final_template.expected.yaml"
    )
    standard_set.final_template_path = path
    if not path.exists():
        return
    try:
        standard_set.final_template = _load_yaml_dict(path)
        standard_set.final_template_sha256 = sha256_file(path)
    except Exception as exc:
        standard_set.load_findings.append(
            _quality_finding(
                len(standard_set.load_findings) + 1,
                "invalid_final_template_expected_yaml",
                "final_template.expected.yaml is not valid YAML",
                "valid YAML",
                repr(exc),
                bucket="standard_invalid",
            )
        )


def _load_stage_standards(standard_set: TemplateGenerationStandardSet) -> None:
    stage_refs = standard_set.target_standard.get("evidence_baselines", {}).get(
        "template_generation_stages",
        {},
    )
    if not isinstance(stage_refs, dict):
        stage_refs = {}
    for stage_key in TEMPLATE_GENERATION_STAGE_KEYS:
        path = _stage_path(standard_set.target_dir, stage_key, stage_refs.get(stage_key))
        if not path.exists():
            continue
        try:
            raw = _load_yaml_dict(path)
        except Exception as exc:
            standard_set.load_findings.append(
                _quality_finding(
                    len(standard_set.load_findings) + 1,
                    "invalid_stage_standard_yaml",
                    f"{stage_key} standard is not valid YAML",
                    "valid YAML",
                    repr(exc),
                    stage=stage_key,
                    bucket="standard_invalid",
                )
            )
            continue
        standard_set.stages[stage_key] = StageStandardSpec(
            stage_key=stage_key,
            stage_id=str(raw.get("stage_id") or STAGE_IDS_BY_KEY[stage_key]),
            path=path,
            sha256=sha256_file(path),
            verifier_state=str(raw.get("verifier_state") or "not_configured"),
            gate_enabled=bool(raw.get("gate_enabled")),
            artifact_under_test=str(raw.get("artifact_under_test") or ""),
            expected=raw.get("expected") if isinstance(raw.get("expected"), dict) else {},
            raw=raw,
        )


def _stage_path(target_dir: Path, stage_key: str, registered_path: Any) -> Path:
    if registered_path:
        return target_dir / str(registered_path)
    return target_dir / "template_generation" / f"{stage_key}.standard.yaml"


def _stage_standard_schema_findings(
    stage: StageStandardSpec,
    *,
    expected_source_hash: str | None,
    final_template: dict[str, Any],
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []

    def add(type_: str, message: str, expected: str, actual: str, bucket: str) -> None:
        findings.append(
            _quality_finding(
                start_index + len(findings),
                type_,
                message,
                expected,
                actual,
                stage=stage.stage_key,
                bucket=bucket,
            )
        )

    if stage.stage_id != STAGE_IDS_BY_KEY[stage.stage_key]:
        add(
            "stage_id_mismatch",
            f"{stage.stage_key} has an unexpected stage_id",
            STAGE_IDS_BY_KEY[stage.stage_key],
            stage.stage_id,
            "standard_invalid",
        )
    expected_artifact = EXPECTED_ARTIFACT_BY_STAGE[stage.stage_key]
    if stage.artifact_under_test != expected_artifact:
        add(
            "artifact_under_test_mismatch",
            f"{stage.stage_key} points at the wrong artifact",
            expected_artifact,
            stage.artifact_under_test,
            "standard_invalid",
        )
    if not stage.verifier_state:
        add(
            "missing_verifier_state",
            f"{stage.stage_key} does not declare verifier_state",
            "verifier_state is present",
            "missing",
            "standard_invalid",
        )
    if "gate_enabled" not in stage.raw:
        add(
            "missing_gate_enabled",
            f"{stage.stage_key} does not declare gate_enabled",
            "gate_enabled is present",
            "missing",
            "standard_invalid",
        )
    if not stage.expected:
        add(
            "missing_stage_expected",
            f"{stage.stage_key} does not declare expected",
            "expected is a non-empty mapping",
            "missing",
            "standard_invalid",
        )
    source_hash = stage.raw.get("accepted_source_facts", {}).get("template_docx_sha256")
    if expected_source_hash and source_hash and str(source_hash) != expected_source_hash:
        add(
            "stage_source_hash_mismatch",
            f"{stage.stage_key} accepted source hash differs from target.standard.yaml",
            expected_source_hash,
            str(source_hash),
            "standard_drift",
        )
    elif expected_source_hash and not source_hash:
        add(
            "missing_stage_source_hash",
            f"{stage.stage_key} does not bind accepted_source_facts.template_docx_sha256",
            expected_source_hash,
            "missing",
            "standard_missing",
        )
    if stage.stage_key == "t3_element_policy":
        findings.extend(
            _t3_element_expectation_findings(
                stage,
                final_template=final_template,
                start_index=start_index + len(findings),
            )
        )
        if (
            stage.gate_enabled
            or stage.raw.get("gold_contract_version")
            or stage.expected.get("run_span_ledger")
        ):
            findings.extend(
                _t3_gold_contract_findings(
                    stage,
                    start_index=start_index + len(findings),
                )
            )
    return findings


def _t3_element_expectation_findings(
    stage: StageStandardSpec,
    *,
    final_template: dict[str, Any],
    start_index: int,
) -> list[Finding]:
    final_elements = _final_template_element_refs(final_template)
    if not final_elements:
        return []
    findings: list[Finding] = []
    declared_refs = _declared_t3_element_expectation_refs(stage.expected)
    missing_refs = [
        f"{item['unit_id']}.{item['element_id']}"
        for item in final_elements
        if f"{item['unit_id']}.{item['element_id']}" not in declared_refs
    ]
    if missing_refs:
        declared_count = _declared_t3_element_expectation_count(stage.expected)
        sample_missing = missing_refs[:10]
        findings.append(
            _quality_finding(
                start_index + len(findings),
                "t3_standard_element_expectations_missing",
                (
                    "T3 standard does not cover the human-reviewed final_template "
                    "element list with element/run-span expectations"
                ),
                (
                    f"all {len(final_elements)} final_template element refs in "
                    "expected.element_expectations[]"
                ),
                (
                    f"{declared_count} declared element/run-span expectations; "
                    f"missing final_template elements: {sample_missing}"
                ),
                stage=stage.stage_key,
                affected_ids=sample_missing,
                bucket="standard_incomplete",
            )
        )
    run_span_ledger = stage.expected.get("run_span_ledger")
    if not isinstance(run_span_ledger, list) or not run_span_ledger:
        findings.append(
            _quality_finding(
                start_index + len(findings),
                "t3_standard_run_span_ledger_missing",
                "T3 standard does not declare run/span handling coverage",
                "expected.run_span_ledger[] with raw_run_id/logical_run_id coverage",
                "missing or empty expected.run_span_ledger",
                stage=stage.stage_key,
                bucket="standard_incomplete",
            )
        )
    return findings


def _t3_gold_contract_findings(
    stage: StageStandardSpec,
    *,
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []

    def add(type_: str, message: str, expected: Any, actual: Any) -> None:
        findings.append(
            _quality_finding(
                start_index + len(findings),
                type_,
                message,
                expected,
                actual,
                stage=stage.stage_key,
                bucket="t3_gold_contract",
            )
        )

    if stage.raw.get("gold_contract_version") != "t3-adaptive-run-span-gold-1.0":
        add(
            "t3_gold_contract_version_invalid",
            "T3 gold must declare the adaptive run/span contract version",
            "t3-adaptive-run-span-gold-1.0",
            stage.raw.get("gold_contract_version"),
        )
    gold_status = str(stage.raw.get("gold_status") or "")
    if gold_status not in {"VERIFIED", "PARTIAL", "DISPUTED", "MISSING"}:
        add(
            "t3_gold_status_invalid",
            "T3 gold_status must use the canonical gold lifecycle",
            ["VERIFIED", "PARTIAL", "DISPUTED", "MISSING"],
            gold_status or "missing",
        )
    elif gold_status != "VERIFIED":
        add(
            "t3_gold_not_verified",
            "T3 gold is not fully human-reviewed for the declared scored universe",
            "VERIFIED",
            gold_status,
        )
    review = stage.raw.get("review_metadata")
    review = review if isinstance(review, dict) else {}
    for field in ("reviewed_by", "reviewed_at", "review_source", "change_reason"):
        if not review.get(field):
            add(
                "t3_gold_review_metadata_incomplete",
                f"T3 gold review_metadata.{field} is required",
                f"non-empty review_metadata.{field}",
                review.get(field),
            )
    if review.get("auto_update_allowed") is not False:
        add(
            "t3_gold_auto_update_not_forbidden",
            "T3 gold must forbid automatic candidate-to-gold updates",
            False,
            review.get("auto_update_allowed"),
        )
    accepted = stage.raw.get("accepted_source_facts")
    accepted = accepted if isinstance(accepted, dict) else {}
    upstream_hash = str(accepted.get("upstream_t2_standard_sha256") or "")
    if not upstream_hash.startswith("sha256:") or len(upstream_hash) != 71:
        add(
            "t3_gold_upstream_hash_missing",
            "T3 isolated gold must bind the frozen upstream T2 standard hash",
            "sha256:<64 hex>",
            upstream_hash or "missing",
        )
    contract = stage.expected.get("core_action_contract")
    contract = contract if isinstance(contract, dict) else {}
    if contract.get("gold_granularity") != "adaptive_run_or_span":
        add(
            "t3_gold_granularity_invalid",
            "T3 gold must use adaptive run-or-span identities",
            "adaptive_run_or_span",
            contract.get("gold_granularity"),
        )

    ledger = stage.expected.get("run_span_ledger")
    if not isinstance(ledger, list):
        return findings
    grouped: dict[str, list[dict[str, Any]]] = {}
    item_errors: list[dict[str, Any]] = []
    for index, item in enumerate(ledger):
        if not isinstance(item, dict):
            item_errors.append({"index": index, "error": "item is not a mapping"})
            continue
        raw_run_id = str(item.get("raw_run_id") or "")
        target_kind = str(item.get("target_kind") or "")
        text = item.get("text")
        action = str(item.get("expected_action") or "")
        if (
            not raw_run_id
            or target_kind not in {"run", "span"}
            or not isinstance(text, str)
            or action not in {"keep", "fill", "delete", "unknown"}
        ):
            item_errors.append(
                {
                    "index": index,
                    "raw_run_id": raw_run_id,
                    "target_kind": target_kind,
                    "expected_action": action,
                    "error": "missing or invalid required adaptive gold fields",
                }
            )
            continue
        if action == "unknown" and (
            not item.get("unknown_reason")
            or item.get("execution_fallback_action") != "keep"
        ):
            item_errors.append(
                {
                    "index": index,
                    "raw_run_id": raw_run_id,
                    "error": "unknown gold requires a reason and keep fallback",
                }
            )
        grouped.setdefault(raw_run_id, []).append(item)

    shape_errors: list[dict[str, Any]] = []
    for raw_run_id, items in grouped.items():
        run_items = [item for item in items if item.get("target_kind") == "run"]
        span_items = [item for item in items if item.get("target_kind") == "span"]
        if run_items:
            if len(run_items) != 1 or span_items:
                shape_errors.append(
                    {
                        "raw_run_id": raw_run_id,
                        "error": "one run item or multiple span items are allowed, not both",
                    }
                )
            continue
        if len(span_items) < 2:
            shape_errors.append(
                {
                    "raw_run_id": raw_run_id,
                    "error": "span-shaped gold requires at least two items",
                }
            )
            continue
        cursor = 0
        for item in sorted(
            span_items,
            key=lambda value: (
                value.get("start") if isinstance(value.get("start"), int) else -1,
                value.get("end") if isinstance(value.get("end"), int) else -1,
            ),
        ):
            start = item.get("start")
            end = item.get("end")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or start != cursor
                or end <= start
                or len(str(item.get("text") or "")) != end - start
            ):
                shape_errors.append(
                    {
                        "raw_run_id": raw_run_id,
                        "start": start,
                        "end": end,
                        "error": "span items must be contiguous and text-length exact",
                    }
                )
                break
            cursor = end
    if item_errors or shape_errors:
        add(
            "t3_gold_adaptive_ledger_invalid",
            "T3 run_span_ledger does not satisfy the adaptive identity contract",
            "all run/span items are complete, unique, and structurally valid",
            (item_errors + shape_errors)[:100],
        )
    return findings


def _declared_t3_element_expectation_refs(expected: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    element_expectations = expected.get("element_expectations")
    if not isinstance(element_expectations, list):
        return refs
    for item in element_expectations:
        if not isinstance(item, dict):
            continue
        stable_id = str(item.get("stable_id") or "")
        if stable_id:
            refs.add(stable_id)
            continue
        unit_id = str(item.get("unit_id") or "")
        element_id = str(item.get("element_id") or "")
        if unit_id and element_id:
            refs.add(f"{unit_id}.{element_id}")
    return refs


def _final_template_element_refs(final_template: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    units = final_template.get("expected", {}).get("units")
    if not isinstance(units, list):
        return refs
    for unit in units:
        if not isinstance(unit, dict):
            continue
        unit_id = str(unit.get("unit_id") or "")
        elements = unit.get("elements")
        if not unit_id or not isinstance(elements, list):
            continue
        for element in elements:
            if not isinstance(element, dict):
                continue
            element_id = str(element.get("element_id") or "")
            if not element_id:
                continue
            refs.append({"unit_id": unit_id, "element_id": element_id})
    return refs


def _declared_t3_element_expectation_count(expected: dict[str, Any]) -> int:
    count = 0
    for key in ["element_expectations", "element_ledger", "run_span_ledger"]:
        value = expected.get(key)
        if isinstance(value, list):
            count += sum(1 for item in value if isinstance(item, dict))
    run_level = expected.get("run_level_elements")
    if isinstance(run_level, list):
        for item in run_level:
            if not isinstance(item, dict):
                continue
            expected_elements = item.get("expected_elements")
            if isinstance(expected_elements, list):
                count += sum(1 for element in expected_elements if isinstance(element, dict))
    return count


def _cross_stage_unit_order_findings(
    standard_set: TemplateGenerationStandardSet,
    *,
    start_index: int,
) -> list[Finding]:
    orders = {
        stage_key: stage.expected.get("unit_order")
        for stage_key, stage in standard_set.stages.items()
        if stage_key in {"t2_unit_pagination", "t3_element_policy", "t4_global_layout", "t5_template_spec"}
    }
    normalized = {
        stage_key: [str(item) for item in value]
        for stage_key, value in orders.items()
        if isinstance(value, list)
    }
    if len(normalized) < 2:
        return []
    reference_key, reference_order = next(iter(normalized.items()))
    findings: list[Finding] = []
    for stage_key, order in normalized.items():
        if order == reference_order:
            continue
        findings.append(
            _quality_finding(
                start_index + len(findings),
                "stage_unit_order_mismatch",
                f"{stage_key} unit_order differs from {reference_key}",
                f"{reference_key}: {reference_order}",
                f"{stage_key}: {order}",
                stage=stage_key,
                affected_ids=[stage_key, reference_key],
                bucket="standard_conflict",
            )
        )
    final_units = standard_set.final_template.get("expected", {}).get("units")
    if isinstance(final_units, list):
        final_order = [
            str(unit.get("unit_id"))
            for unit in final_units
            if isinstance(unit, dict) and unit.get("unit_id") is not None
        ]
        if final_order and final_order != reference_order:
            findings.append(
                _quality_finding(
                    start_index + len(findings),
                    "final_template_unit_order_mismatch",
                    "final_template.expected.yaml unit order differs from T2-T5 standards",
                    reference_order,
                    final_order,
                    stage="template_generation_standard_quality",
                    affected_ids=list(normalized),
                    bucket="standard_conflict",
                )
            )
    return findings


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _quality_finding(
    index: int,
    type_: str,
    message: str,
    expected: Any,
    actual: Any,
    *,
    stage: str = "template_generation_standard_quality",
    affected_ids: list[str] | None = None,
    bucket: str,
) -> Finding:
    return make_finding(
        index,
        stage,
        Status.UNKNOWN,
        type_,
        message,
        _stringify(expected),
        _stringify(actual),
        affected_ids=affected_ids,
        root_cause_bucket=bucket,
    )


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return repr(value)
