from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docfit.core.io import read_json, read_yaml, sha256_file, sha256_json, write_json, write_text
from docfit.core.models import Finding, StageResult
from docfit.core.status import Status, merge_statuses
from docfit.harness.reports import write_report_bundle
from docfit.harness.template_generation_run_bundle import (
    RUN_ARTIFACT_SPECS,
    RunArtifactSpec,
    TemplateGenerationRunBundle,
)
from docfit.harness.template_generation_stage_verifiers import StageCheck
from docfit.harness.template_generation_standard_quality import (
    TemplateGenerationStandardQualityReport,
    TemplateGenerationStandardSet,
)


@dataclass
class TemplateGenerationJudgeReport:
    status: Status
    first_bad_stage: str | None
    standard_set: TemplateGenerationStandardSet
    standard_quality: TemplateGenerationStandardQualityReport
    run_bundle: TemplateGenerationRunBundle
    stage_checks: list[StageCheck]
    findings: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        stage_standard_diffs = build_stage_standard_diffs(self)
        mismatches = build_mismatches(self)
        root_causes = build_diagnosis_root_causes(self, mismatches)
        owner_assignments = build_owner_assignments(root_causes)
        fix_plan = build_fix_plans(root_causes)
        _attach_diagnosis_layers(mismatches, root_causes, owner_assignments, fix_plan)
        acceptance = build_standard_acceptance_summary(
            self,
            stage_standard_diffs=stage_standard_diffs,
            root_causes=root_causes,
        )
        return {
            "artifact_type": "template_generation_judge_report",
            "artifact_version": "1.0",
            "status": self.status.value,
            "standard_acceptance_status": acceptance["standard_acceptance_status"],
            "signoff_status": acceptance["signoff_status"],
            "signoff_blockers": acceptance["signoff_blockers"],
            "first_bad_stage": self.first_bad_stage,
            "source_run_id": self.run_bundle.source_run_id,
            "source_run_dir": str(self.run_bundle.source_run_dir),
            "source_run_dir_name": self.run_bundle.source_run_dir_name,
            "standard_set": self.standard_set.to_dict(),
            "standard_quality": self.standard_quality.to_dict(),
            "run_bundle": self.run_bundle.to_dict(),
            "stage_checks": [check.to_dict() for check in self.stage_checks],
            "stage_standard_quality_reports": _stage_standard_quality_report_refs(self),
            "stage_standard_diff_reports": _stage_standard_diff_report_refs(self),
            "mismatches": mismatches,
            "stage_standard_diffs": stage_standard_diffs,
            "root_causes": root_causes,
            "owner_assignments": owner_assignments,
            "fix_plan": fix_plan,
            "owner_summary": acceptance["owner_summary"],
            "top_blockers": acceptance["top_blockers"],
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def to_stage_result(self) -> StageResult:
        report_dict = self.to_dict()
        return StageResult(
            "template_generation_judge",
            self.status,
            findings=self.findings,
            artifacts={
                "template_generation_judge_report": report_dict,
                "template_generation_run_bundle": self.run_bundle.to_dict(),
                "template_generation_stage_checks": [
                    check.to_dict() for check in self.stage_checks
                ],
                "template_generation_stage_standard_quality_report": (
                    self.standard_quality.to_dict()
                ),
                "stage_standard_quality_reports": _stage_standard_quality_report_refs(self),
                "stage_standard_diff_reports": _stage_standard_diff_report_refs(self),
                "mismatches": report_dict["mismatches"],
                "stage_standard_diffs": report_dict["stage_standard_diffs"],
                "root_causes": report_dict["root_causes"],
                "owner_assignments": report_dict["owner_assignments"],
                "fix_plan": report_dict["fix_plan"],
                "owner_summary": report_dict["owner_summary"],
            },
            coverage={
                "template_generation_judge.standard_quality": (
                    self.standard_quality.status == Status.PASS
                ),
                "template_generation_judge.run_bundle": self.run_bundle.status == Status.PASS,
                "template_generation_judge.stage_checks": bool(self.stage_checks),
                "template_generation_judge.standard_acceptance_status": report_dict[
                    "standard_acceptance_status"
                ],
                "template_generation_judge.signoff_status": report_dict["signoff_status"],
            },
            blocked_at=self.first_bad_stage,
        )


def aggregate_template_generation_judgement(
    *,
    standard_set: TemplateGenerationStandardSet,
    standard_quality: TemplateGenerationStandardQualityReport,
    run_bundle: TemplateGenerationRunBundle,
    stage_checks: list[StageCheck],
) -> TemplateGenerationJudgeReport:
    findings = [
        *standard_quality.findings,
        *run_bundle.findings,
        *[
            finding
            for check in stage_checks
            for finding in check.findings
        ],
    ]
    status = merge_statuses(
        [standard_quality.status, run_bundle.status]
        + [check.status for check in stage_checks]
    )
    first_bad_stage = _first_bad_stage(stage_checks)
    if first_bad_stage is None and standard_quality.status != Status.PASS:
        first_bad_stage = "standard_quality"
    if first_bad_stage is None and run_bundle.status != Status.PASS:
        first_bad_stage = "run_bundle"
    return TemplateGenerationJudgeReport(
        status=status,
        first_bad_stage=first_bad_stage,
        standard_set=standard_set,
        standard_quality=standard_quality,
        run_bundle=run_bundle,
        stage_checks=stage_checks,
        findings=findings,
    )


def write_template_generation_standard_quality_outputs(
    out_dir: Path,
    report: TemplateGenerationStandardQualityReport,
) -> StageResult:
    json_path = out_dir / "template_generation_stage_standard_quality_report.json"
    md_path = out_dir / "template_generation_stage_standard_quality_report.md"
    write_json(json_path, report.to_dict())
    write_text(md_path, build_standard_quality_markdown(report))
    write_report_bundle(
        out_dir,
        stage="template_generation_standard_quality",
        status=report.status,
        findings=[finding.to_dict() for finding in report.findings],
        artifacts={
            "template_generation_stage_standard_quality_report": json_path.name,
            "template_generation_stage_standard_quality_report_md": md_path.name,
        },
        stage_statuses=report.stage_statuses,
        blocked_at=_blocked_at_from_findings(report.findings),
    )
    return StageResult(
        "template_generation_standard_quality",
        report.status,
        findings=report.findings,
        artifacts={"report": report.to_dict()},
        artifact_paths={
            "template_generation_stage_standard_quality_report": json_path,
            "template_generation_stage_standard_quality_report_md": md_path,
        },
        blocked_at=_blocked_at_from_findings(report.findings),
    )


def write_template_generation_judge_outputs(
    out_dir: Path,
    report: TemplateGenerationJudgeReport,
) -> StageResult:
    run_bundle_path = out_dir / "template_generation_run_bundle.json"
    stage_checks_path = out_dir / "template_generation_stage_checks.json"
    quality_path = out_dir / "template_generation_stage_standard_quality_report.json"
    quality_md_path = out_dir / "template_generation_stage_standard_quality_report.md"
    judge_path = out_dir / "template_generation_judge_report.json"
    judge_md_path = out_dir / "template_generation_judge_report.md"
    stage_quality_paths = write_stage_standard_quality_reports(out_dir, report)
    stage_diff_paths = write_stage_standard_diff_reports(out_dir, report)
    root_cause_path = out_dir / "template_generation_root_cause_report.json"
    root_cause_md_path = out_dir / "template_generation_root_cause_report.md"
    bridge_acceptance_path = out_dir / "template_agent_bridge_standard_acceptance.json"
    bridge_acceptance_md_path = out_dir / "template_agent_bridge_standard_acceptance.md"
    route_eval_path = out_dir / "template_generation_route_eval_report.json"
    route_eval_md_path = out_dir / "template_generation_route_eval_report.md"

    write_json(run_bundle_path, report.run_bundle.to_dict())
    write_json(stage_checks_path, [check.to_dict() for check in report.stage_checks])
    write_json(quality_path, report.standard_quality.to_dict())
    write_text(quality_md_path, build_standard_quality_markdown(report.standard_quality))
    report_dict = report.to_dict()
    root_cause_report = build_template_generation_root_cause_report(report, report_dict)
    bridge_acceptance = build_template_agent_bridge_standard_acceptance(report, report_dict)
    route_eval = build_template_generation_route_eval_report(report, report_dict)
    write_json(root_cause_path, root_cause_report)
    write_text(root_cause_md_path, build_template_generation_root_cause_markdown(root_cause_report))
    write_json(bridge_acceptance_path, bridge_acceptance)
    write_text(
        bridge_acceptance_md_path,
        build_template_agent_bridge_standard_acceptance_markdown(bridge_acceptance),
    )
    write_json(route_eval_path, route_eval)
    write_text(route_eval_md_path, build_template_generation_route_eval_markdown(route_eval))
    write_json(judge_path, report_dict)
    write_text(judge_md_path, build_judge_markdown(report))

    stage_statuses = {
        check.stage_key: check.status.value for check in report.stage_checks
    }
    stage_quality_artifacts = {
        report_id: paths["json"].name
        for report_id, paths in stage_quality_paths.items()
    }
    stage_quality_artifacts.update(
        {
            f"{report_id}_md": paths["md"].name
            for report_id, paths in stage_quality_paths.items()
        }
    )
    stage_diff_artifacts = {
        report_id: paths["json"].name
        for report_id, paths in stage_diff_paths.items()
    }
    stage_diff_artifacts.update(
        {
            f"{report_id}_md": paths["md"].name
            for report_id, paths in stage_diff_paths.items()
        }
    )
    summary = write_report_bundle(
        out_dir,
        stage="template_generation_judge",
        status=report.status,
        findings=[finding.to_dict() for finding in report.findings],
        artifacts={
            "template_generation_run_bundle": run_bundle_path.name,
            "template_generation_stage_checks": stage_checks_path.name,
            "template_generation_stage_standard_quality_report": quality_path.name,
            "template_generation_stage_standard_quality_report_md": quality_md_path.name,
            "template_generation_judge_report": judge_path.name,
            "template_generation_judge_report_md": judge_md_path.name,
            "template_generation_root_cause_report": root_cause_path.name,
            "template_generation_root_cause_report_md": root_cause_md_path.name,
            "template_agent_bridge_standard_acceptance": bridge_acceptance_path.name,
            "template_agent_bridge_standard_acceptance_md": bridge_acceptance_md_path.name,
            "template_generation_route_eval_report": route_eval_path.name,
            "template_generation_route_eval_report_md": route_eval_md_path.name,
            **stage_quality_artifacts,
            **stage_diff_artifacts,
        },
        coverage={
            "standard_quality_status": report.standard_quality.status.value,
            "run_bundle_status": report.run_bundle.status.value,
            "source_run_id": report.run_bundle.source_run_id,
            "first_bad_stage": report.first_bad_stage,
            "standard_acceptance_status": report_dict["standard_acceptance_status"],
            "signoff_status": report_dict["signoff_status"],
            "mismatch_count": len(report_dict["mismatches"]),
            "root_cause_count": len(report_dict["root_causes"]),
            "owner_summary": report_dict["owner_summary"],
            "bridge_present": bridge_acceptance["bridge_present"],
            "bridged_output_accuracy": bridge_acceptance["bridged_output_accuracy"][
                "aggregate_accuracy"
            ],
            "route_eval_mismatch_count": len(route_eval["mismatches"]),
        },
        stage_statuses=stage_statuses,
        blocked_at=report.first_bad_stage,
    )
    result = report.to_stage_result()
    result.artifact_paths.update(
        {
            "summary": out_dir / "summary.json",
            "findings": out_dir / "findings.json",
            "template_generation_run_bundle": run_bundle_path,
            "template_generation_stage_checks": stage_checks_path,
            "template_generation_stage_standard_quality_report": quality_path,
            "template_generation_stage_standard_quality_report_md": quality_md_path,
            "template_generation_judge_report": judge_path,
            "template_generation_judge_report_md": judge_md_path,
            "template_generation_root_cause_report": root_cause_path,
            "template_generation_root_cause_report_md": root_cause_md_path,
            "template_agent_bridge_standard_acceptance": bridge_acceptance_path,
            "template_agent_bridge_standard_acceptance_md": bridge_acceptance_md_path,
            "template_generation_route_eval_report": route_eval_path,
            "template_generation_route_eval_report_md": route_eval_md_path,
        }
    )
    for report_id, paths in stage_quality_paths.items():
        result.artifact_paths[report_id] = paths["json"]
        result.artifact_paths[f"{report_id}_md"] = paths["md"]
    for report_id, paths in stage_diff_paths.items():
        result.artifact_paths[report_id] = paths["json"]
        result.artifact_paths[f"{report_id}_md"] = paths["md"]
    result.artifacts["summary"] = summary
    result.artifacts["template_agent_bridge_standard_acceptance"] = bridge_acceptance
    result.artifacts["template_generation_route_eval_report"] = route_eval
    return result


def write_stage_standard_quality_reports(
    out_dir: Path,
    report: TemplateGenerationJudgeReport,
) -> dict[str, dict[str, Path]]:
    paths: dict[str, dict[str, Path]] = {}
    for spec in RUN_ARTIFACT_SPECS:
        stage_report = build_stage_standard_quality_report(report, spec)
        report_id = stage_report["report_id"]
        json_path = out_dir / f"{report_id}.json"
        md_path = out_dir / f"{report_id}.md"
        write_json(json_path, stage_report)
        write_text(md_path, build_stage_standard_quality_markdown(stage_report))
        paths[report_id] = {"json": json_path, "md": md_path}
    return paths


def write_stage_standard_diff_reports(
    out_dir: Path,
    report: TemplateGenerationJudgeReport,
) -> dict[str, dict[str, Path]]:
    paths: dict[str, dict[str, Path]] = {}
    for spec in RUN_ARTIFACT_SPECS:
        stage_report = build_stage_standard_diagnosis_report(report, spec)
        report_id = stage_report["report_id"]
        json_path = out_dir / f"{report_id}.json"
        md_path = out_dir / f"{report_id}.md"
        write_json(json_path, stage_report)
        write_text(md_path, build_stage_standard_diagnosis_markdown(stage_report))
        paths[report_id] = {"json": json_path, "md": md_path}
    return paths


def build_stage_standard_diffs(
    report: TemplateGenerationJudgeReport,
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    for finding in report.standard_quality.findings:
        stage_id, stage_key, report_id = _standard_quality_finding_stage_context(
            report,
            finding,
        )
        owner, owner_detail, next_action = _owner_for_finding(finding)
        diffs.append(
            {
                "diff_id": f"diff_{len(diffs) + 1:03d}",
                "stage_id": stage_id,
                "stage_key": stage_key,
                "report_ref": f"{report_id}.json" if report_id else None,
                "status": finding.status.value,
                "diff_kind": _diff_kind(finding),
                "finding_type": finding.type,
                "message": finding.message,
                "expected": finding.expected,
                "observed": finding.actual,
                "affected_ids": finding.affected_ids,
                "evidence_refs": finding.evidence_refs,
                "root_cause_bucket": finding.root_cause_bucket,
                "owner": owner,
                "owner_detail": owner_detail,
                "next_action": next_action,
            }
        )
    for check in report.stage_checks:
        report_id = _stage_quality_report_id_for_stage(check.stage_key)
        for finding in check.findings:
            owner, owner_detail, next_action = _owner_for_finding(finding)
            diffs.append(
                {
                    "diff_id": f"diff_{len(diffs) + 1:03d}",
                    "stage_id": check.stage_id,
                    "stage_key": check.stage_key,
                    "report_ref": f"{report_id}.json" if report_id else None,
                    "status": finding.status.value,
                    "diff_kind": _diff_kind(finding),
                    "finding_type": finding.type,
                    "message": finding.message,
                    "expected": finding.expected,
                    "observed": finding.actual,
                    "affected_ids": finding.affected_ids,
                    "evidence_refs": finding.evidence_refs,
                    "root_cause_bucket": finding.root_cause_bucket,
                    "owner": owner,
                    "owner_detail": owner_detail,
                    "next_action": next_action,
                }
            )
    return diffs


def build_root_causes(
    stage_standard_diffs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    root_causes: list[dict[str, Any]] = []
    for diff in stage_standard_diffs:
        root_causes.append(
            {
                "root_cause_id": f"rc_{len(root_causes) + 1:03d}",
                "diff_id": diff["diff_id"],
                "stage_id": diff["stage_id"],
                "stage_key": diff["stage_key"],
                "status": diff["status"],
                "finding_type": diff["finding_type"],
                "root_cause_bucket": diff["root_cause_bucket"],
                "owner": diff["owner"],
                "owner_detail": diff["owner_detail"],
                "reason": _root_cause_reason(diff),
                "next_action": diff["next_action"],
            }
        )
    return root_causes


def build_mismatches(
    report: TemplateGenerationJudgeReport,
    *,
    stage_key: str | None = None,
) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    counters: dict[str, int] = {}
    for finding in report.standard_quality.findings:
        stage_id, quality_stage_key, _report_id = _standard_quality_finding_stage_context(
            report,
            finding,
        )
        if stage_key is not None and quality_stage_key != stage_key:
            continue
        standard = report.standard_set.stages.get(quality_stage_key)
        counters[stage_id] = counters.get(stage_id, 0) + 1
        mismatch_id = f"{stage_id}-MISMATCH-{counters[stage_id]:03d}"
        finding_type = _normalized_mismatch_type(finding.type)
        mismatches.append(
            {
                "id": mismatch_id,
                "mismatch_id": mismatch_id,
                "stage_id": stage_id,
                "stage_key": quality_stage_key,
                "status": finding.status.value,
                "finding_type": finding.type,
                "type": finding_type,
                "field": _mismatch_field(finding_type, finding),
                "expected": _parse_finding_value(finding.expected),
                "observed": _parse_finding_value(finding.actual),
                "problem": _mismatch_problem(finding_type, finding),
                "affected_ids": finding.affected_ids,
                "evidence": {
                    "artifact_path": None,
                    "standard_path": str(standard.path) if standard is not None else None,
                    "source_seq_refs": _source_seq_refs_from_finding(finding),
                    "evidence_refs": finding.evidence_refs,
                },
                "root_cause_bucket": finding.root_cause_bucket,
                "message": finding.message,
            }
        )
    for check in report.stage_checks:
        if stage_key is not None and check.stage_key != stage_key:
            continue
        standard = report.standard_set.stages.get(check.stage_key)
        artifact = report.run_bundle.artifact_for_stage(check.stage_key)
        for finding in check.findings:
            stage_id = check.stage_id
            counters[stage_id] = counters.get(stage_id, 0) + 1
            mismatch_id = f"{stage_id}-MISMATCH-{counters[stage_id]:03d}"
            finding_type = _normalized_mismatch_type(finding.type)
            field = _mismatch_field(finding_type, finding)
            expected = _parse_finding_value(finding.expected)
            observed = _parse_finding_value(finding.actual)
            mismatches.append(
                {
                    "id": mismatch_id,
                    "mismatch_id": mismatch_id,
                    "stage_id": stage_id,
                    "stage_key": check.stage_key,
                    "status": finding.status.value,
                    "finding_type": finding.type,
                    "type": finding_type,
                    "field": field,
                    "expected": expected,
                    "observed": observed,
                    "problem": _mismatch_problem(finding_type, finding),
                    "affected_ids": finding.affected_ids,
                    "evidence": {
                        "artifact_path": str(artifact.path)
                        if artifact is not None and artifact.path is not None
                        else None,
                        "standard_path": str(standard.path) if standard is not None else None,
                        "source_seq_refs": _source_seq_refs_from_finding(finding),
                        "evidence_refs": finding.evidence_refs,
                    },
                    "root_cause_bucket": finding.root_cause_bucket,
                    "message": finding.message,
                }
            )
    return mismatches


def build_diagnosis_root_causes(
    report: TemplateGenerationJudgeReport,
    mismatches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    root_causes: list[dict[str, Any]] = []
    for mismatch in mismatches:
        category = _root_cause_category(report, mismatch)
        legacy_owner, owner_detail, next_action = _legacy_owner_for_mismatch(mismatch)
        root_causes.append(
            {
                "id": _derived_id(mismatch["id"], "ROOT-CAUSE"),
                "root_cause_id": f"rc_{len(root_causes) + 1:03d}",
                "mismatch_id": mismatch["id"],
                "stage_id": mismatch["stage_id"],
                "stage_key": mismatch["stage_key"],
                "status": mismatch["status"],
                "finding_type": mismatch["finding_type"],
                "category": category,
                "first_bad_stage": _diagnosis_first_bad_stage(report, mismatch),
                "reason": _diagnosis_reason(category, mismatch),
                "root_cause_bucket": mismatch["root_cause_bucket"],
                "owner": legacy_owner,
                "owner_detail": owner_detail,
                "next_action": next_action,
            }
        )
    return root_causes


def build_owner_assignments(
    root_causes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    for root_cause in root_causes:
        primary, secondary = _owner_assignment_for_category(root_cause["category"])
        assignments.append(
            {
                "id": _derived_id(root_cause["mismatch_id"], "OWNER"),
                "mismatch_id": root_cause["mismatch_id"],
                "root_cause_id": root_cause["id"],
                "primary": primary,
                "secondary": secondary,
                "rationale": _owner_assignment_rationale(root_cause, primary, secondary),
            }
        )
    return assignments


def build_fix_plans(
    root_causes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for root_cause in root_causes:
        plans.append(
            {
                "id": _derived_id(root_cause["mismatch_id"], "FIX"),
                "mismatch_id": root_cause["mismatch_id"],
                "root_cause_id": root_cause["id"],
                **_fix_plan_for_root_cause(root_cause),
            }
        )
    return plans


def build_stage_standard_diagnosis_report(
    report: TemplateGenerationJudgeReport,
    spec: RunArtifactSpec,
) -> dict[str, Any]:
    artifact = report.run_bundle.artifacts.get(spec.artifact_key)
    check = _stage_check_for_spec(report, spec)
    standard = (
        report.standard_set.stages.get(spec.stage_key)
        if spec.stage_key is not None
        else None
    )
    stage_key = spec.stage_key or _implicit_stage_key(spec)
    stage_id = spec.stage_id or "T0"
    status = check.status if check is not None else (
        artifact.status if artifact is not None else Status.UNKNOWN
    )
    report_id = _stage_diff_report_id(spec)
    mismatches = build_mismatches(report, stage_key=spec.stage_key) if spec.stage_key else []
    root_causes = build_diagnosis_root_causes(report, mismatches)
    owner_assignments = build_owner_assignments(root_causes)
    fix_plan = build_fix_plans(root_causes)
    _attach_diagnosis_layers(mismatches, root_causes, owner_assignments, fix_plan)
    stage_diffs = [
        diff
        for diff in build_stage_standard_diffs(report)
        if diff["stage_key"] == stage_key
    ]
    return {
        "artifact_type": "template_generation_stage_standard_diff_report",
        "artifact_version": "1.0",
        "report_kind": "standard_diff_report",
        "report_id": report_id,
        "status": status.value,
        "source_run_id": report.run_bundle.source_run_id,
        "source_run_dir": str(report.run_bundle.source_run_dir),
        "stage_id": stage_id,
        "stage_key": stage_key,
        "artifact_key": spec.artifact_key,
        "artifact_name": spec.top_level_name,
        "artifact_under_test": (
            standard.artifact_under_test if standard is not None else spec.artifact_key
        ),
        "artifact_path": str(artifact.path) if artifact and artifact.path else None,
        "artifact_sha256": artifact.sha256 if artifact is not None else None,
        "standard_path": str(standard.path) if standard is not None else None,
        "standard_sha256": standard.sha256 if standard is not None else None,
        "verifier_state": (
            check.verifier_state
            if check is not None
            else (standard.verifier_state if standard is not None else "not_applicable")
        ),
        "gate_enabled": (
            check.gate_enabled
            if check is not None
            else (standard.gate_enabled if standard is not None else None)
        ),
        "audit_status": check.audit_status if check is not None else None,
        "mismatches": mismatches,
        "root_causes": root_causes,
        "owner_assignments": owner_assignments,
        "fix_plan": fix_plan,
        "stage_standard_diffs": stage_diffs,
    }


def build_template_generation_root_cause_report(
    report: TemplateGenerationJudgeReport,
    report_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_dict = report_dict or report.to_dict()
    return {
        "artifact_type": "template_generation_root_cause_report",
        "artifact_version": "1.0",
        "report_kind": "root_cause_report",
        "status": report_dict["status"],
        "standard_acceptance_status": report_dict["standard_acceptance_status"],
        "signoff_status": report_dict["signoff_status"],
        "first_bad_stage": report_dict["first_bad_stage"],
        "source_run_id": report_dict["source_run_id"],
        "mismatches": report_dict["mismatches"],
        "root_causes": report_dict["root_causes"],
        "owner_assignments": report_dict["owner_assignments"],
        "fix_plan": report_dict["fix_plan"],
        "owner_summary": report_dict["owner_summary"],
        "top_blockers": report_dict["top_blockers"],
    }


def build_template_agent_bridge_standard_acceptance(
    report: TemplateGenerationJudgeReport,
    report_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_dict = report_dict or report.to_dict()
    bridge = _load_run_json(
        report.run_bundle.source_run_dir,
        "09.25_agent_observation_bridge.json",
        "artifacts/template_agent_observation_bridge.json",
    )
    attribution = _load_run_json(
        report.run_bundle.source_run_dir,
        "14_agent_attribution.json",
        "artifacts/agent_attribution.json",
    )
    stage_metrics = {
        check.stage_key: _stage_accuracy_metric(report, check)
        for check in report.stage_checks
    }
    numeric_scores = [
        metric["primary_accuracy"]
        for metric in stage_metrics.values()
        if isinstance(metric.get("primary_accuracy"), (int, float))
    ]
    aggregate_accuracy = (
        round(sum(numeric_scores) / len(numeric_scores), 4)
        if numeric_scores
        else None
    )
    return {
        "artifact_type": "template_agent_bridge_standard_acceptance",
        "artifact_version": "1.0",
        "report_kind": "agent_bridge_standard_acceptance",
        "status": report_dict["status"],
        "standard_acceptance_status": report_dict["standard_acceptance_status"],
        "signoff_status": report_dict["signoff_status"],
        "source_run_id": report.run_bundle.source_run_id,
        "source_run_dir": str(report.run_bundle.source_run_dir),
        "bridge_present": bridge is not None,
        "attribution_present": attribution is not None,
        "bridge_summary": (bridge or {}).get("summary", {}),
        "attribution_summary": {
            "applied_proposal_ids": (attribution or {}).get("applied_proposal_ids", []),
            "rejected_proposal_ids": (attribution or {}).get("rejected_proposal_ids", []),
            "comparison_summary": (attribution or {}).get("comparison_summary", {}),
            "manual_review": (attribution or {}).get("manual_review", {}),
            "observation_bridge": (attribution or {}).get("observation_bridge", {}),
        },
        "bridged_output_accuracy": {
            "aggregate_accuracy": aggregate_accuracy,
            "metric_note": (
                "Accuracy is derived from stage standard verifier audits after AI-to-code "
                "bridge execution. Stages without signed fine-grained gold expose null "
                "metrics instead of inferred precision."
            ),
            "stages": stage_metrics,
        },
        "mismatches": report_dict["mismatches"],
        "root_causes": report_dict["root_causes"],
        "owner_assignments": report_dict["owner_assignments"],
        "fix_plan": report_dict["fix_plan"],
    }


def build_template_agent_bridge_standard_acceptance_markdown(report: dict[str, Any]) -> str:
    accuracy = report.get("bridged_output_accuracy", {})
    lines = [
        "# Template Agent Bridge Standard Acceptance",
        "",
        f"- Status: {report['status']}",
        f"- Standard acceptance: {report['standard_acceptance_status']}",
        f"- Sign-off: {report['signoff_status']}",
        f"- Bridge present: {report['bridge_present']}",
        f"- Aggregate accuracy: {accuracy.get('aggregate_accuracy')}",
        "",
        "## Stage Accuracy",
    ]
    for stage_key, metric in (accuracy.get("stages") or {}).items():
        lines.append(
            "- "
            f"{stage_key}: primary={metric.get('primary_accuracy')}, "
            f"status={metric.get('status')}, audit={metric.get('audit_status')}"
        )
    lines.extend(["", "## Diagnosis"])
    if report.get("mismatches"):
        for mismatch in report["mismatches"]:
            lines.append(
                "- "
                f"{mismatch.get('id')} {mismatch.get('field')}: "
                f"{mismatch.get('problem')}"
            )
    else:
        lines.append("- mismatches: none")
    return "\n".join(lines) + "\n"


def _stage_accuracy_metric(
    report: TemplateGenerationJudgeReport,
    check: StageCheck,
) -> dict[str, Any]:
    dispatch = {
        "t2_unit_pagination": _t2_accuracy_metric,
        "t3_element_policy": _t3_accuracy_metric,
        "t4_global_layout": _t4_accuracy_metric,
        "t5_template_spec": _t5_accuracy_metric,
    }
    builder = dispatch.get(check.stage_key)
    if builder is None:
        return _base_accuracy_metric(check, primary_accuracy=None)
    return builder(report, check)


def _base_accuracy_metric(
    check: StageCheck,
    *,
    primary_accuracy: float | None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "stage_id": check.stage_id,
        "stage_key": check.stage_key,
        "status": check.status.value,
        "audit_status": check.audit_status,
        "primary_accuracy": primary_accuracy,
        **extra,
    }


def _t2_accuracy_metric(
    report: TemplateGenerationJudgeReport,
    check: StageCheck,
) -> dict[str, Any]:
    del report
    audit = check.audit
    expected = [str(item) for item in audit.get("expected_unit_ids", []) or []]
    actual = [str(item) for item in audit.get("actual_unit_ids", []) or []]
    precision, recall, f1 = _set_prf(actual, expected)
    return _base_accuracy_metric(
        check,
        primary_accuracy=f1,
        precision=precision,
        recall=recall,
        f1=f1,
        order_exact_match=bool(audit.get("unit_order_matches")),
        missing_units=audit.get("missing_unit_ids", []),
        unexpected_units=audit.get("unexpected_unit_ids", []),
    )


def _t3_accuracy_metric(
    report: TemplateGenerationJudgeReport,
    check: StageCheck,
) -> dict[str, Any]:
    standard = report.standard_set.stages.get(check.stage_key)
    expected_policy_units = _expected_policy_units(standard.expected if standard else {})
    conflicts = [
        item
        for item in check.audit.get("policy_group_conflicts", []) or []
        if isinstance(item, dict)
    ]
    conflict_units = {
        str(item.get("unit_id") or "")
        for item in conflicts
        if item.get("unit_id") not in (None, "")
    }
    policy_conformance = (
        round((len(expected_policy_units) - len(conflict_units)) / len(expected_policy_units), 4)
        if expected_policy_units
        else None
    )
    artifact = report.run_bundle.artifact_for_stage(check.stage_key)
    elements = (
        artifact.payload.get("elements", [])
        if artifact is not None and isinstance(artifact.payload, dict)
        else []
    )
    element_count = len(elements) if isinstance(elements, list) else 0
    required_gaps = check.audit.get("required_policy_field_gaps", []) or []
    required_field_compliance = (
        round(max(element_count - len(required_gaps), 0) / element_count, 4)
        if element_count
        else (1.0 if not required_gaps else 0.0)
    )
    primary = _avg_numbers([policy_conformance, required_field_compliance])
    return _base_accuracy_metric(
        check,
        primary_accuracy=primary,
        policy_group_conformance=policy_conformance,
        required_field_compliance=required_field_compliance,
        policy_conflict_count=len(conflicts),
        policy_conflict_units=sorted(conflict_units),
        required_policy_field_gap_count=len(required_gaps),
    )


def _t4_accuracy_metric(
    report: TemplateGenerationJudgeReport,
    check: StageCheck,
) -> dict[str, Any]:
    del report
    audit = check.audit
    missing_fields = audit.get("missing_evidence_fields", []) or []
    components = [
        1.0 if audit.get("has_global_layout_contract") else 0.0,
        1.0 if not missing_fields else 0.0,
        1.0 if int(audit.get("section_profile_count") or 0) > 0 else 0.0,
        1.0 if audit.get("page_numbering_status") not in (None, "", "missing") else 0.0,
    ]
    return _base_accuracy_metric(
        check,
        primary_accuracy=round(sum(components) / len(components), 4),
        layout_contract_completeness=round(sum(components) / len(components), 4),
        missing_evidence_fields=missing_fields,
        section_profile_count=audit.get("section_profile_count"),
        page_numbering_status=audit.get("page_numbering_status"),
        metric_note="T4 standard currently exposes contract completeness, not visual layout precision.",
    )


def _t5_accuracy_metric(
    report: TemplateGenerationJudgeReport,
    check: StageCheck,
) -> dict[str, Any]:
    del report
    audit = check.audit
    expected = [str(item) for item in audit.get("expected_unit_order", []) or []]
    actual = [str(item) for item in audit.get("actual_unit_order", []) or []]
    precision, recall, f1 = _set_prf(actual, expected)
    missing_section_refs = audit.get("missing_section_profile_refs", []) or []
    section_ref_compliance = (
        round(max(len(actual) - len(missing_section_refs), 0) / len(actual), 4)
        if actual
        else None
    )
    primary = _avg_numbers([f1, section_ref_compliance])
    return _base_accuracy_metric(
        check,
        primary_accuracy=primary,
        precision=precision,
        recall=recall,
        f1=f1,
        section_ref_compliance=section_ref_compliance,
        missing_section_profile_refs=missing_section_refs,
        missing_input_hashes=audit.get("missing_input_hashes", []),
        missing_review_flags=audit.get("missing_review_flags", []),
    )


def _set_prf(actual: list[str], expected: list[str]) -> tuple[float, float, float]:
    actual_set = set(actual)
    expected_set = set(expected)
    hit = actual_set & expected_set
    precision = len(hit) / len(actual_set) if actual_set else 0.0
    recall = len(hit) / len(expected_set) if expected_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return round(precision, 4), round(recall, 4), round(f1, 4)


def _expected_policy_units(expected: dict[str, Any]) -> set[str]:
    groups = expected.get("policy_groups", {}) if isinstance(expected, dict) else {}
    if not isinstance(groups, dict):
        return set()
    result: set[str] = set()
    for values in groups.values():
        if isinstance(values, list):
            result.update(str(value) for value in values if value not in (None, ""))
    return result


def _avg_numbers(values: list[float | None]) -> float | None:
    numeric = [value for value in values if isinstance(value, (int, float))]
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 4)


def _load_run_json(run_dir: Path, *relative_paths: str) -> dict[str, Any] | None:
    for relative_path in relative_paths:
        path = run_dir / relative_path
        if not path.exists():
            continue
        try:
            value = read_json(path)
        except Exception:
            continue
        if isinstance(value, dict):
            return value
    return None


def build_standard_acceptance_summary(
    report: TemplateGenerationJudgeReport,
    *,
    stage_standard_diffs: list[dict[str, Any]] | None = None,
    root_causes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    stage_standard_diffs = (
        stage_standard_diffs
        if stage_standard_diffs is not None
        else build_stage_standard_diffs(report)
    )
    root_causes = (
        root_causes
        if root_causes is not None
        else build_root_causes(stage_standard_diffs)
    )
    owner_summary = _owner_summary(root_causes)
    has_fail = any(diff["status"] == Status.FAIL.value for diff in stage_standard_diffs)
    has_unknown = (
        report.standard_quality.status != Status.PASS
        or report.run_bundle.status != Status.PASS
        or any(diff["status"] == Status.UNKNOWN.value for diff in stage_standard_diffs)
        or any(check.status == Status.UNKNOWN for check in report.stage_checks)
    )
    if has_fail:
        standard_acceptance_status = Status.FAIL.value
    elif has_unknown:
        standard_acceptance_status = Status.UNKNOWN.value
    else:
        standard_acceptance_status = Status.PASS.value

    signoff_blockers = _signoff_blockers(
        report,
        standard_acceptance_status=standard_acceptance_status,
        stage_standard_diffs=stage_standard_diffs,
    )
    signoff_status = "SIGNABLE" if not signoff_blockers else "NOT_SIGNABLE"
    top_blockers = _top_blockers(root_causes)
    return {
        "standard_acceptance_status": standard_acceptance_status,
        "signoff_status": signoff_status,
        "signoff_blockers": signoff_blockers,
        "owner_summary": owner_summary,
        "top_blockers": top_blockers,
    }


def build_stage_standard_quality_report(
    report: TemplateGenerationJudgeReport,
    spec: RunArtifactSpec,
) -> dict[str, Any]:
    artifact = report.run_bundle.artifacts.get(spec.artifact_key)
    check = _stage_check_for_spec(report, spec)
    standard = (
        report.standard_set.stages.get(spec.stage_key)
        if spec.stage_key is not None
        else None
    )
    findings = check.findings if check is not None else _run_bundle_findings_for_spec(report, spec)
    status = check.status if check is not None else (
        artifact.status if artifact is not None else Status.UNKNOWN
    )
    stage_key = spec.stage_key or _implicit_stage_key(spec)
    stage_id = spec.stage_id or "T0"
    report_id = _stage_quality_report_id(spec)
    stage_diffs = [
        diff
        for diff in build_stage_standard_diffs(report)
        if diff["stage_key"] == stage_key
    ]
    mismatches = build_mismatches(report, stage_key=spec.stage_key) if spec.stage_key else []
    root_causes = build_diagnosis_root_causes(report, mismatches)
    owner_assignments = build_owner_assignments(root_causes)
    fix_plan = build_fix_plans(root_causes)
    _attach_diagnosis_layers(mismatches, root_causes, owner_assignments, fix_plan)
    acceptance = _artifact_acceptance_summary(
        status=status,
        check=check,
        stage_diffs=stage_diffs,
        artifact_status=artifact.status if artifact is not None else Status.UNKNOWN,
    )
    return {
        "artifact_type": "template_generation_artifact_standard_quality_report",
        "artifact_version": "1.0",
        "report_kind": "standard_quality_report",
        "report_id": report_id,
        "status": status.value,
        "standard_acceptance_status": acceptance["standard_acceptance_status"],
        "signoff_status": acceptance["signoff_status"],
        "signoff_blockers": acceptance["signoff_blockers"],
        "source_run_id": report.run_bundle.source_run_id,
        "source_run_dir": str(report.run_bundle.source_run_dir),
        "stage_id": stage_id,
        "stage_key": stage_key,
        "artifact_key": spec.artifact_key,
        "artifact_name": spec.top_level_name,
        "artifact_under_test": (
            standard.artifact_under_test if standard is not None else spec.artifact_key
        ),
        "artifact_path": str(artifact.path) if artifact and artifact.path else None,
        "artifact_sha256": artifact.sha256 if artifact is not None else None,
        "artifact_status": artifact.status.value if artifact is not None else Status.UNKNOWN.value,
        "artifact_source_kind": artifact.source_kind if artifact is not None else "missing",
        "artifact_hash_match": artifact.hash_match if artifact is not None else None,
        "standard_path": str(standard.path) if standard is not None else None,
        "standard_sha256": standard.sha256 if standard is not None else None,
        "standard_quality_status": (
            report.standard_quality.stage_statuses.get(spec.stage_key, Status.UNKNOWN.value)
            if spec.stage_key is not None
            else "not_applicable"
        ),
        "verifier_state": (
            check.verifier_state
            if check is not None
            else (standard.verifier_state if standard is not None else "not_applicable")
        ),
        "gate_enabled": (
            check.gate_enabled
            if check is not None
            else (standard.gate_enabled if standard is not None else None)
        ),
        "audit_status": check.audit_status if check is not None else None,
        "audit": check.audit if check is not None else {},
        "comparison_scope": (
            "stage_standard"
            if spec.stage_key is not None
            else "run_bundle_artifact_binding"
        ),
        "mismatches": mismatches,
        "stage_standard_diffs": stage_diffs,
        "root_causes": root_causes,
        "owner_assignments": owner_assignments,
        "fix_plan": fix_plan,
        "owner_summary": _owner_summary(root_causes),
        "top_blockers": _top_blockers(root_causes),
        "findings": [finding.to_dict() for finding in findings],
    }


def build_stage_standard_quality_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['report_id']}",
        "",
        f"- Status: {report['status']}",
        f"- Standard acceptance: {report['standard_acceptance_status']}",
        f"- Sign-off: {report['signoff_status']}",
        f"- Stage: {report['stage_id']} / {report['stage_key']}",
        f"- Artifact: {report['artifact_name']}",
        f"- Artifact path: {report.get('artifact_path') or 'missing'}",
        f"- Artifact sha256: {report.get('artifact_sha256') or 'missing'}",
        f"- Artifact status: {report['artifact_status']}",
        f"- Standard path: {report.get('standard_path') or 'not_applicable'}",
        f"- Standard quality: {report['standard_quality_status']}",
        f"- Verifier state: {report['verifier_state']}",
        f"- Gate enabled: {report.get('gate_enabled')}",
        f"- Audit status: {report.get('audit_status') or 'not_applicable'}",
        "",
    ]
    if report.get("signoff_blockers"):
        lines.append("## Sign-off Blockers")
        for blocker in report["signoff_blockers"]:
            lines.append(f"- {blocker}")
        lines.append("")
    if report.get("top_blockers"):
        lines.append("## Top Blockers")
        for blocker in report["top_blockers"]:
            lines.append(
                "- "
                f"{blocker.get('stage_id')} {blocker.get('finding_type')}: "
                f"owner={blocker.get('owner')}, category={blocker.get('category')}, "
                f"next={blocker.get('next_action')}"
            )
        lines.append("")
    lines.append("## Diagnosis")
    if report.get("mismatches"):
        for mismatch in report["mismatches"]:
            lines.append(
                "- "
                f"{mismatch.get('id')} {mismatch.get('field')}: "
                f"{mismatch.get('problem')}"
            )
    else:
        lines.append("- mismatches: none")
    lines.append("")
    findings = report.get("findings") or []
    if findings:
        lines.append("## Findings")
        for finding in findings:
            lines.append(
                "- "
                f"[{finding.get('status')}] "
                f"{finding.get('stage')}/{finding.get('type')}: "
                f"{finding.get('message')}"
            )
    else:
        lines.append("No findings.")
    lines.append("")
    return "\n".join(lines)


def build_stage_standard_diagnosis_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['report_id']}",
        "",
        f"- Status: {report['status']}",
        f"- Stage: {report['stage_id']} / {report['stage_key']}",
        f"- Artifact: {report['artifact_name']}",
        f"- Artifact path: {report.get('artifact_path') or 'missing'}",
        f"- Standard path: {report.get('standard_path') or 'not_applicable'}",
        f"- Verifier state: {report['verifier_state']}",
        f"- Gate enabled: {report.get('gate_enabled')}",
        "",
        "## Mismatches",
    ]
    if report["mismatches"]:
        for mismatch in report["mismatches"]:
            lines.append(
                "- "
                f"{mismatch['id']} {mismatch['field']}: {mismatch['problem']}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Root Causes"])
    if report["root_causes"]:
        for root_cause in report["root_causes"]:
            lines.append(
                "- "
                f"{root_cause['mismatch_id']}: {root_cause['category']} "
                f"(first_bad_stage={root_cause['first_bad_stage']})"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Owner Assignments"])
    if report["owner_assignments"]:
        for assignment in report["owner_assignments"]:
            lines.append(
                "- "
                f"{assignment['mismatch_id']}: primary={assignment['primary']}, "
                f"secondary={assignment.get('secondary') or 'none'}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Fix Plan"])
    if report["fix_plan"]:
        for plan in report["fix_plan"]:
            lines.append(f"- {plan['mismatch_id']}: {plan['action']}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def build_template_generation_root_cause_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Template Generation Root Cause Report",
        "",
        f"- Status: {report['status']}",
        f"- Standard acceptance: {report['standard_acceptance_status']}",
        f"- Sign-off: {report['signoff_status']}",
        f"- First bad stage: {report.get('first_bad_stage') or 'none'}",
        f"- Source run id: {report['source_run_id']}",
        "",
        "## Root Causes",
    ]
    if report["root_causes"]:
        for root_cause in report["root_causes"]:
            lines.append(
                "- "
                f"{root_cause['mismatch_id']}: {root_cause['category']} "
                f"owner={root_cause['owner']} reason={root_cause['reason']}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Fix Plan"])
    if report["fix_plan"]:
        for plan in report["fix_plan"]:
            lines.append(f"- {plan['mismatch_id']}: {plan['action']}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _stage_standard_quality_report_refs(
    report: TemplateGenerationJudgeReport,
) -> list[dict[str, Any]]:
    refs = []
    checks = {check.stage_key: check for check in report.stage_checks}
    for spec in RUN_ARTIFACT_SPECS:
        artifact = report.run_bundle.artifacts.get(spec.artifact_key)
        check = checks.get(spec.stage_key) if spec.stage_key else None
        status = check.status if check is not None else (
            artifact.status if artifact is not None else Status.UNKNOWN
        )
        report_id = _stage_quality_report_id(spec)
        refs.append(
            {
                "report_id": report_id,
                "json_report": f"{report_id}.json",
                "markdown_report": f"{report_id}.md",
                "stage_id": spec.stage_id or "T0",
                "stage_key": spec.stage_key or _implicit_stage_key(spec),
                "artifact_key": spec.artifact_key,
                "artifact_name": spec.top_level_name,
                "status": status.value,
            }
        )
    return refs


def _stage_standard_diff_report_refs(
    report: TemplateGenerationJudgeReport,
) -> list[dict[str, Any]]:
    refs = []
    checks = {check.stage_key: check for check in report.stage_checks}
    for spec in RUN_ARTIFACT_SPECS:
        artifact = report.run_bundle.artifacts.get(spec.artifact_key)
        check = checks.get(spec.stage_key) if spec.stage_key else None
        status = check.status if check is not None else (
            artifact.status if artifact is not None else Status.UNKNOWN
        )
        report_id = _stage_diff_report_id(spec)
        refs.append(
            {
                "report_id": report_id,
                "json_report": f"{report_id}.json",
                "markdown_report": f"{report_id}.md",
                "stage_id": spec.stage_id or "T0",
                "stage_key": spec.stage_key or _implicit_stage_key(spec),
                "artifact_key": spec.artifact_key,
                "artifact_name": spec.top_level_name,
                "status": status.value,
            }
        )
    return refs


def _artifact_acceptance_summary(
    *,
    status: Status,
    check: StageCheck | None,
    stage_diffs: list[dict[str, Any]],
    artifact_status: Status,
) -> dict[str, Any]:
    has_fail = (
        status == Status.FAIL
        or artifact_status == Status.FAIL
        or any(diff["status"] == Status.FAIL.value for diff in stage_diffs)
    )
    has_unknown = (
        status == Status.UNKNOWN
        or artifact_status == Status.UNKNOWN
        or any(diff["status"] == Status.UNKNOWN.value for diff in stage_diffs)
        or (
            check is not None
            and (check.verifier_state != "configured" or not check.gate_enabled)
        )
    )
    if has_fail:
        standard_acceptance_status = Status.FAIL.value
    elif has_unknown:
        standard_acceptance_status = Status.UNKNOWN.value
    else:
        standard_acceptance_status = Status.PASS.value
    signoff_blockers: list[str] = []
    if standard_acceptance_status != Status.PASS.value:
        signoff_blockers.append(
            f"standard_acceptance_status={standard_acceptance_status}"
        )
    if check is not None and check.verifier_state != "configured":
        signoff_blockers.append(f"verifier_state={check.verifier_state}")
    if check is not None and not check.gate_enabled:
        signoff_blockers.append("gate_enabled=false")
    signoff_status = "SIGNABLE" if not signoff_blockers else "NOT_SIGNABLE"
    return {
        "standard_acceptance_status": standard_acceptance_status,
        "signoff_status": signoff_status,
        "signoff_blockers": signoff_blockers,
    }


def _signoff_blockers(
    report: TemplateGenerationJudgeReport,
    *,
    standard_acceptance_status: str,
    stage_standard_diffs: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if standard_acceptance_status != Status.PASS.value:
        blockers.append(f"standard_acceptance_status={standard_acceptance_status}")
    if report.standard_quality.status != Status.PASS:
        blockers.append(f"standard_quality={report.standard_quality.status.value}")
    if report.run_bundle.status != Status.PASS:
        blockers.append(f"run_bundle={report.run_bundle.status.value}")
    for check in report.stage_checks:
        if check.verifier_state != "configured":
            blockers.append(f"{check.stage_key}.verifier_state={check.verifier_state}")
        if not check.gate_enabled:
            blockers.append(f"{check.stage_key}.gate_enabled=false")
    if any(diff["status"] == Status.FAIL.value for diff in stage_standard_diffs):
        blockers.append("stage_standard_diffs contain FAIL")
    return sorted(set(blockers))


def _owner_summary(root_causes: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "code": 0,
        "verifier": 0,
        "standard": 0,
        "ai_prompt": 0,
        "unknown": 0,
    }
    for root_cause in root_causes:
        owner = str(root_cause.get("owner") or "unknown")
        summary[owner if owner in summary else "unknown"] += 1
    return summary


def _top_blockers(root_causes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {
        Status.FAIL.value: 0,
        Status.UNKNOWN.value: 1,
        Status.PASS.value: 2,
    }
    ordered = sorted(
        root_causes,
        key=lambda item: (
            priority.get(str(item.get("status")), 9),
            str(item.get("stage_id")),
            str(item.get("finding_type")),
        ),
    )
    return ordered[:20]


def _attach_diagnosis_layers(
    mismatches: list[dict[str, Any]],
    root_causes: list[dict[str, Any]],
    owner_assignments: list[dict[str, Any]],
    fix_plan: list[dict[str, Any]],
) -> None:
    root_by_mismatch = {item["mismatch_id"]: item for item in root_causes}
    owner_by_mismatch = {item["mismatch_id"]: item for item in owner_assignments}
    fix_by_mismatch = {item["mismatch_id"]: item for item in fix_plan}
    for mismatch in mismatches:
        root_cause = root_by_mismatch.get(mismatch["id"])
        owner = owner_by_mismatch.get(mismatch["id"])
        plan = fix_by_mismatch.get(mismatch["id"])
        if root_cause is not None:
            mismatch["root_cause"] = {
                "category": root_cause["category"],
                "first_bad_stage": root_cause["first_bad_stage"],
                "reason": root_cause["reason"],
            }
        if owner is not None:
            mismatch["owner"] = {
                "primary": owner["primary"],
                "secondary": owner["secondary"],
                "rationale": owner["rationale"],
            }
        if plan is not None:
            mismatch["fix_plan"] = {
                "action": plan["action"],
                "likely_files": plan["likely_files"],
                "tests": plan["tests"],
                "acceptance": plan["acceptance"],
            }


def _normalized_mismatch_type(finding_type: str) -> str:
    mapping = {
        "t2_standard_unit_order_mismatch": "t2_unit_order_mismatch",
        "t2_standard_units_missing": "t2_expected_unit_missing",
        "t2_standard_units_unexpected": "t2_unexpected_unit_present",
        "t2_standard_custom_units_present": "t2_unexpected_unit_present",
        "t2_standard_anchor_owner_mismatch": "t2_anchor_owner_mismatch",
        "t5_required_input_hashes_missing": "t5_input_hash_missing",
        "t5_unit_section_profile_refs_missing": "t5_section_profile_refs_missing",
    }
    return mapping.get(finding_type, finding_type)


def _mismatch_field(finding_type: str, finding: Finding) -> str:
    field_by_type = {
        "t1_artifact_type_mismatch": "artifact_type",
        "t1_required_top_level_fields_missing": "required_top_level_fields",
        "t1_required_data_groups_missing": "data",
        "t1_visible_body_flow_locator_missing": "body_flow[].source_seq/source_ref",
        "t1_forbidden_semantic_fields_present": "forbidden_semantic_fields",
        "t2_unit_order_mismatch": "expected.unit_order",
        "t2_expected_unit_missing": "expected.units[].unit_id",
        "t2_unexpected_unit_present": "units[].unit_id",
        "t2_anchor_owner_mismatch": "expected.units[].anchors",
        "t2_source_range_mismatch": "units[].source_seq_refs",
        "t2_page_policy_mismatch": "units[].page_policy",
        "t2_standard_schema_invalid": "standard.expected",
        "t2_artifact_type_mismatch": "artifact_type",
        "t3_artifact_type_mismatch": "artifact_type",
        "t3_unit_order_mismatch": "expected.unit_order",
        "t3_policy_group_conflict": "expected.policy_groups",
        "t3_required_policy_fields_missing": (
            "expected.element_policy_contract.required_fields_by_policy"
        ),
        "t3_standard_element_expectations_missing": (
            "expected.element_expectations"
        ),
        "t3_standard_run_span_ledger_missing": "expected.run_span_ledger",
        "t4_artifact_type_mismatch": "artifact_type",
        "t4_global_layout_contract_missing": "expected.global_layout_contract",
        "t4_global_spec_evidence_fields_missing": "global_spec",
        "t4_section_profiles_missing": "section_profiles",
        "t4_page_numbering_missing": "page_numbering",
        "t5_artifact_type_mismatch": "artifact_type",
        "t5_unit_order_mismatch": "expected.unit_order",
        "t5_input_hash_missing": "input_hashes",
        "t5_review_flags_dropped": "review_flags",
        "t5_section_profile_refs_missing": "units[].section_profile_refs",
        "template_generation_stage_standard_missing": "stage_standard",
        "template_generation_stage_artifact_missing": "artifact",
        "template_generation_stage_standard_quality_not_pass": "standard_quality",
        "template_generation_run_bundle_not_pass": "run_bundle",
        "template_generation_stage_verifier_not_configured": "verifier_state",
        "template_generation_stage_gate_disabled": "gate_enabled",
    }
    return field_by_type.get(finding_type, finding.type)


def _mismatch_problem(finding_type: str, finding: Finding) -> str:
    problem_by_type = {
        "t2_unit_order_mismatch": (
            "T2 unit order differs from expected.unit_order in the signed standard."
        ),
        "t2_expected_unit_missing": "T2 is missing one or more units required by the standard.",
        "t2_unexpected_unit_present": "T2 emitted units that are not allowed by the standard.",
        "t2_anchor_owner_mismatch": (
            "T2 assigned a standard anchor to the wrong unit owner."
        ),
        "t2_source_range_mismatch": "T2 source ranges differ from the signed standard.",
        "t2_page_policy_mismatch": "T2 page policy differs from the signed standard.",
        "t2_standard_schema_invalid": "The signed T2 standard schema is invalid.",
        "t3_unit_order_mismatch": (
            "T3 element unit order differs from expected.unit_order in the signed standard."
        ),
        "t3_required_policy_fields_missing": (
            "T3 elements are missing fields required by their assigned policy."
        ),
        "t3_standard_element_expectations_missing": (
            "T3 standard lacks element/run-span expectations for the "
            "human-reviewed final_template element list."
        ),
        "t3_standard_run_span_ledger_missing": (
            "T3 standard lacks a run/span handling ledger for source runs."
        ),
        "t5_unit_order_mismatch": (
            "T5 template_spec unit order differs from expected.unit_order."
        ),
    }
    if finding_type == "t3_policy_group_conflict":
        return _t3_policy_conflict_problem(finding)
    if finding_type == "t5_review_flags_dropped":
        return "T5 dropped review_flags that upstream stages emitted."
    if finding_type == "t5_section_profile_refs_missing":
        return "T5 units are missing section_profile_refs required for layout traceability."
    if finding_type == "t5_input_hash_missing":
        return "T5 template_spec does not bind all required upstream input hashes."
    if finding_type in problem_by_type:
        return problem_by_type[finding_type]
    return finding.message


def _t3_policy_conflict_problem(finding: Finding) -> str:
    conflicts = _parse_finding_value(finding.actual)
    if not isinstance(conflicts, list) or not conflicts:
        return finding.message
    groups = sorted(
        {
            f"{item.get('expected')}->{item.get('actual')}"
            for item in conflicts
            if isinstance(item, dict)
            and item.get("expected") is not None
            and item.get("actual") is not None
        }
    )
    if not groups:
        return finding.message
    return f"Element policy group conflict: {', '.join(groups)}."


def _parse_finding_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value


def _source_seq_refs_from_finding(finding: Finding) -> list[int]:
    refs: list[int] = []
    for value in [_parse_finding_value(finding.actual), _parse_finding_value(finding.expected)]:
        refs.extend(_collect_source_seq_refs(value))
    return sorted(set(refs))


def _collect_source_seq_refs(value: Any) -> list[int]:
    refs: list[int] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"source_seq", "source_seq_ref"}:
                parsed = _int_or_none(child)
                if parsed is not None:
                    refs.append(parsed)
            elif key == "source_seq_refs" and isinstance(child, list):
                refs.extend(
                    item
                    for item in (_int_or_none(item) for item in child)
                    if item is not None
                )
            else:
                refs.extend(_collect_source_seq_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(_collect_source_seq_refs(child))
    return refs


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _root_cause_category(
    report: TemplateGenerationJudgeReport,
    mismatch: dict[str, Any],
) -> str:
    text = (
        f"{mismatch['stage_key']} {mismatch['finding_type']} "
        f"{mismatch['root_cause_bucket']} {mismatch['problem']}"
    ).lower()
    if "agent" in text or "ai" in text:
        return "ai_overlay"
    if "not_configured" in text or "gate_disabled" in text or "verifier" in text:
        return "comparator_issue"
    if _standard_document_problem(text):
        return "standard_issue"
    if "artifact_missing" in text or "run_bundle_missing" in text or "hash" in text:
        return "evidence_missing"
    if "input" in text and "hash" not in text:
        return "input_issue"
    if mismatch["stage_id"] == "T5" and report.first_bad_stage not in {None, "T5"}:
        return "downstream_symptom"
    if mismatch["status"] == Status.FAIL.value:
        return "generation_code"
    if "artifact_trace" in text or "missing" in text:
        return "evidence_missing"
    return "generation_code"


def _diagnosis_first_bad_stage(
    report: TemplateGenerationJudgeReport,
    mismatch: dict[str, Any],
) -> str:
    if mismatch["stage_id"] == "T5" and report.first_bad_stage not in {None, "T5"}:
        return str(report.first_bad_stage)
    return str(mismatch["stage_id"])


def _diagnosis_reason(category: str, mismatch: dict[str, Any]) -> str:
    if category == "generation_code":
        return (
            f"{mismatch['stage_id']} artifact field {mismatch['field']} differs from "
            "the signed stage standard."
        )
    if category == "ai_overlay":
        return (
            f"{mismatch['stage_id']} mismatch is tied to AI overlay or attribution "
            "evidence and needs deterministic reconciliation."
        )
    if category == "standard_issue":
        return (
            f"{mismatch['stage_id']} standard evidence is missing, invalid, or "
            "internally inconsistent."
        )
    if category == "comparator_issue":
        return (
            f"{mismatch['stage_id']} deterministic comparator/gate configuration "
            "cannot produce a signable judgement."
        )
    if category == "input_issue":
        return f"{mismatch['stage_id']} input data does not satisfy the stage contract."
    if category == "evidence_missing":
        return (
            f"{mismatch['stage_id']} lacks artifact, hash, or trace evidence needed "
            "to compare against the standard."
        )
    if category == "downstream_symptom":
        return (
            f"{mismatch['stage_id']} symptom likely propagates from an earlier stage; "
            "fix the first bad upstream stage before changing this output."
        )
    return f"{mismatch['stage_id']} mismatch needs human review."


def _legacy_owner_for_mismatch(mismatch: dict[str, Any]) -> tuple[str, str, str]:
    finding = Finding(
        finding_id=mismatch["id"],
        stage=mismatch["stage_key"],
        severity="blocking",
        status=Status(mismatch["status"]),
        type=mismatch["finding_type"],
        message=mismatch["message"],
        expected=repr(mismatch["expected"]),
        actual=repr(mismatch["observed"]),
        evidence_refs=mismatch["evidence"].get("evidence_refs") or [],
        affected_ids=mismatch["affected_ids"],
        root_cause_bucket=mismatch["root_cause_bucket"],
    )
    return _owner_for_finding(finding)


def _owner_assignment_for_category(category: str) -> tuple[str, str | None]:
    mapping = {
        "generation_code": ("template_generation_code_owner", "standard_judge_owner"),
        "ai_overlay": ("ai_integration_owner", "template_generation_code_owner"),
        "standard_issue": ("standard_owner", "standard_judge_owner"),
        "comparator_issue": ("standard_judge_owner", None),
        "input_issue": ("input_data_owner", "template_generation_code_owner"),
        "evidence_missing": ("input_data_owner", "standard_judge_owner"),
        "downstream_symptom": ("template_generation_code_owner", "standard_judge_owner"),
    }
    return mapping.get(category, ("human_review_owner", "standard_judge_owner"))


def _owner_assignment_rationale(
    root_cause: dict[str, Any],
    primary: str,
    secondary: str | None,
) -> str:
    secondary_text = f", with {secondary} confirming the diagnosis" if secondary else ""
    return (
        f"{root_cause['stage_id']} {root_cause['finding_type']} is classified as "
        f"{root_cause['category']}; {primary} should resolve it{secondary_text}."
    )


def _fix_plan_for_root_cause(root_cause: dict[str, Any]) -> dict[str, Any]:
    stage_id = root_cause["stage_id"]
    finding_type = root_cause["finding_type"]
    if root_cause["category"] == "standard_issue":
        return {
            "action": "Fix or complete the signed stage standard through standard review.",
            "likely_files": ["standards/targets/*/v1/template_generation/*.standard.yaml"],
            "tests": ["tests/contract/test_template_generation_standard_judge.py"],
            "acceptance": [
                "standard_quality_status becomes PASS",
                "standard_diff_report retains evidence for any remaining mismatch",
            ],
        }
    if root_cause["category"] == "comparator_issue":
        return {
            "action": "Implement or configure the deterministic stage comparator/gate.",
            "likely_files": [
                "src/docfit/harness/template_generation_stage_verifiers.py",
                "standards/targets/*/v1/template_generation/*.standard.yaml",
            ],
            "tests": ["tests/unit/test_template_generation_stage_verifiers.py"],
            "acceptance": [
                "verifier_state is configured where the comparator exists",
                "gate status no longer hides mismatches/root_causes/owner/fix_plan",
            ],
        }
    if stage_id == "T2":
        return {
            "action": _t2_fix_action(finding_type),
            "likely_files": [
                "src/docfit/template_generation/structure_candidates.py",
                "src/docfit/template_generation/t2_standard.py",
            ],
            "tests": [
                "tests/unit/test_t2_standard.py",
                "tests/unit/test_template_generation_standard_diff_diagnosis.py",
            ],
            "acceptance": [
                "02_unit_map_standard_diff_report.json no longer contains this mismatch",
                "T2 audit_status changes from FAIL/UNKNOWN to PASS",
                "No new T3/T5 mismatch is introduced",
            ],
        }
    if stage_id == "T3":
        return {
            "action": _t3_fix_action(finding_type),
            "likely_files": [
                "src/docfit/template_generation/structure_candidates.py",
                "src/docfit/template_generation/artifacts.py",
                "src/docfit/harness/template_generation_stage_verifiers.py",
            ],
            "tests": [
                "tests/unit/test_template_generation_stage_verifiers.py",
                "tests/unit/test_template_generation_standard_diff_diagnosis.py",
            ],
            "acceptance": [
                "03_element_spec_standard_diff_report.json explains no policy conflict",
                "T3 audit_status changes from FAIL/UNKNOWN to PASS",
                "Fixed units only allow fill when the standard explicitly permits it",
            ],
        }
    if stage_id == "T5":
        return {
            "action": _t5_fix_action(finding_type, root_cause["category"]),
            "likely_files": [
                "src/docfit/template_generation/outputs.py",
                "src/docfit/template_generation/runner.py",
                "src/docfit/harness/template_generation_stage_verifiers.py",
            ],
            "tests": [
                "tests/contract/test_template_generate.py",
                "tests/unit/test_template_generation_standard_diff_diagnosis.py",
            ],
            "acceptance": [
                "05_template_spec_standard_diff_report.json no longer contains this mismatch",
                "T5 preserves upstream hashes, review_flags, and section_profile_refs",
                "If upstream caused the symptom, first_bad_stage points upstream",
            ],
        }
    return {
        "action": "Inspect the stage artifact and signed standard, then fix the owning stage.",
        "likely_files": ["src/docfit/template_generation/"],
        "tests": ["tests/contract/test_template_generation_standard_judge.py"],
        "acceptance": ["The mismatch disappears from the stage standard diff report"],
    }


def _t2_fix_action(finding_type: str) -> str:
    actions = {
        "t2_standard_unit_order_mismatch": "Fix T2 unit discovery ordering rules.",
        "t2_standard_units_missing": "Fix T2 unit discovery so all expected units are emitted.",
        "t2_standard_units_unexpected": "Remove unexpected non-standard units from T2 output.",
        "t2_standard_custom_units_present": "Map custom T2 units to signed standard units.",
        "t2_standard_anchor_owner_mismatch": "Fix T2 anchor ownership and source range assignment.",
    }
    return actions.get(finding_type, "Fix T2 unit pagination output against the signed standard.")


def _t3_fix_action(finding_type: str) -> str:
    actions = {
        "t3_unit_order_mismatch": "Fix T3 element ordering to follow expected.unit_order.",
        "t3_policy_group_conflict": (
            "Fix T3 policy assignment so fixed/manual/generated/fill groups do not conflict."
        ),
        "t3_required_policy_fields_missing": (
            "Emit all required fields for each T3 element policy."
        ),
    }
    return actions.get(finding_type, "Fix T3 element policy output against the signed standard.")


def _t5_fix_action(finding_type: str, category: str) -> str:
    if category == "downstream_symptom":
        return "Fix the upstream first_bad_stage, then rerun T5 to clear the propagated symptom."
    actions = {
        "t5_required_input_hashes_missing": "Bind all required upstream input hashes in T5.",
        "t5_review_flags_dropped": "Preserve upstream review_flags in template_spec.",
        "t5_unit_order_mismatch": "Fix T5 unit ordering to follow expected.unit_order.",
        "t5_unit_section_profile_refs_missing": (
            "Carry section_profile_refs from global layout into each T5 unit."
        ),
    }
    return actions.get(finding_type, "Fix T5 template_spec output against the signed standard.")


def _derived_id(mismatch_id: str, suffix: str) -> str:
    return mismatch_id.replace("MISMATCH", suffix)


def _diff_kind(finding: Finding) -> str:
    if finding.type in {
        "template_generation_stage_verifier_not_configured",
        "template_generation_stage_gate_disabled",
    }:
        return "gate_blocker"
    if finding.status == Status.FAIL:
        return "standard_mismatch"
    if "missing" in finding.type or "hash" in finding.type:
        return "evidence_gap"
    return "audit_observation"


def _owner_for_finding(finding: Finding) -> tuple[str, str, str]:
    finding_type = finding.type
    bucket = finding.root_cause_bucket
    text = f"{finding.stage} {finding_type} {bucket}".lower()
    if "agent" in text or "ai" in text:
        return (
            "ai_prompt",
            "AI proposal or attribution touched this path",
            "Review accepted AI proposal and deterministic reconciler behavior.",
        )
    if "verifier" in text or "gate_disabled" in text or "not_configured" in text:
        return (
            "verifier",
            "Stage standard verifier is not configured as a blocking gate",
            "Implement or configure the deterministic verifier before sign-off.",
        )
    if finding.status == Status.FAIL and not _standard_document_problem(text):
        return (
            "code",
            "Run artifact disagrees with signed standard under deterministic audit",
            "Fix template-generation deterministic logic for the first bad stage.",
        )
    if "standard" in text or "baseline" in text:
        return (
            "standard",
            "Signed standard or standard registry is missing or inconsistent",
            "Fix the signed standard through the review process, not from this run.",
        )
    if "run_bundle" in text or "hash" in text or "artifact" in text:
        return (
            "code",
            "Run evidence package is incomplete or internally inconsistent",
            "Fix artifact production or run bundle binding before sign-off.",
        )
    return (
        "unknown",
        "Current evidence is insufficient to assign ownership",
        "Add deterministic evidence or human review before changing code or standards.",
    )


def _standard_document_problem(text: str) -> bool:
    return any(
        marker in text
        for marker in [
            "standard_missing",
            "standard_invalid",
            "standard_quality_not_pass",
            "standard_incomplete",
            "standard_registry",
            "baseline_missing",
            "baseline_invalid",
        ]
    )


def _root_cause_reason(diff: dict[str, Any]) -> str:
    owner = diff["owner"]
    if owner == "verifier":
        return "The stage cannot be signed because the standard verifier is not an enabled gate."
    if owner == "standard":
        return "The signed standard or its registry is incomplete or inconsistent."
    if owner == "code":
        return "The generated stage artifact does not match the signed standard evidence."
    if owner == "ai_prompt":
        return "The mismatch is tied to AI proposal or attribution evidence."
    return "The report does not yet contain enough evidence to assign a precise owner."


def _stage_quality_report_id_for_stage(stage_key: str) -> str | None:
    for spec in RUN_ARTIFACT_SPECS:
        if spec.stage_key == stage_key:
            return _stage_quality_report_id(spec)
    return None


def _standard_quality_finding_stage_context(
    report: TemplateGenerationJudgeReport,
    finding: Finding,
) -> tuple[str, str, str | None]:
    stage_key = finding.stage
    stage = report.standard_set.stages.get(stage_key)
    if stage is not None:
        return stage.stage_id, stage_key, _stage_quality_report_id_for_stage(stage_key)
    return "STANDARD_QUALITY", stage_key, None


def _stage_check_for_spec(
    report: TemplateGenerationJudgeReport,
    spec: RunArtifactSpec,
) -> StageCheck | None:
    if spec.stage_key is None:
        return None
    for check in report.stage_checks:
        if check.stage_key == spec.stage_key:
            return check
    return None


def _run_bundle_findings_for_spec(
    report: TemplateGenerationJudgeReport,
    spec: RunArtifactSpec,
) -> list[Finding]:
    findings = []
    for finding in report.run_bundle.findings:
        if spec.artifact_key in finding.affected_ids:
            findings.append(finding)
        elif spec.artifact_key == "template_generation_request" and "source_hash" in finding.type:
            findings.append(finding)
        elif spec.artifact_key == "fillable_template_docx" and "fillable" in finding.type:
            findings.append(finding)
    return findings


def _stage_quality_report_id(spec: RunArtifactSpec) -> str:
    return f"{Path(spec.top_level_name).stem}_standard_quality_report"


def _stage_diff_report_id(spec: RunArtifactSpec) -> str:
    return f"{Path(spec.top_level_name).stem}_standard_diff_report"


def _implicit_stage_key(spec: RunArtifactSpec) -> str:
    if spec.artifact_key == "template_generation_request":
        return "template_generation_request"
    if spec.artifact_key == "fillable_template_docx":
        return "t6_fillable_template"
    if spec.artifact_key == "build_manifest":
        return "t6_build_manifest"
    if spec.artifact_key == "verification_report":
        return "t7_verification_report"
    return spec.artifact_key


def build_standard_quality_markdown(
    report: TemplateGenerationStandardQualityReport,
) -> str:
    lines = [
        "# Template Generation Stage Standard Quality",
        "",
        f"- Scope: {report.scope}",
        f"- Status: {report.status.value}",
        f"- Targets: {len(report.target_reports)}",
        f"- Findings: {len(report.findings)}",
        "",
        "## Stage Statuses",
    ]
    for stage_key, status in sorted(report.stage_statuses.items()):
        lines.append(f"- {stage_key}: {status}")
    if report.findings:
        lines.extend(["", "## Findings"])
        for finding in report.findings:
            lines.append(f"- [{finding.status.value}] {finding.type}: {finding.message}")
    else:
        lines.extend(["", "No findings."])
    lines.append("")
    return "\n".join(lines)


def build_judge_markdown(report: TemplateGenerationJudgeReport) -> str:
    report_dict = report.to_dict()
    lines = [
        "# Template Generation Judge Report",
        "",
        f"- Status: {report.status.value}",
        f"- Standard acceptance: {report_dict['standard_acceptance_status']}",
        f"- Sign-off: {report_dict['signoff_status']}",
        f"- First bad stage: {report.first_bad_stage or 'none'}",
        f"- Source run id: {report.run_bundle.source_run_id}",
        f"- Source run dir: {report.run_bundle.source_run_dir}",
        f"- Standard quality: {report.standard_quality.status.value}",
        f"- Run bundle: {report.run_bundle.status.value}",
        "",
    ]
    if report_dict["signoff_blockers"]:
        lines.append("## Sign-off Blockers")
        for blocker in report_dict["signoff_blockers"]:
            lines.append(f"- {blocker}")
        lines.append("")
    lines.append("## Owner Summary")
    for owner, count in report_dict["owner_summary"].items():
        lines.append(f"- {owner}: {count}")
    lines.extend(["", "## Top Blockers"])
    if report_dict["top_blockers"]:
        for blocker in report_dict["top_blockers"]:
            lines.append(
                "- "
                f"{blocker.get('stage_id')} {blocker.get('finding_type')}: "
                f"status={blocker.get('status')}, owner={blocker.get('owner')}, "
                f"next={blocker.get('next_action')}"
            )
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Stage Checks",
    ])
    for check in report.stage_checks:
        lines.append(
            "- "
            f"{check.stage_id} {check.stage_key}: "
            f"status={check.status.value}, audit={check.audit_status}, "
            f"verifier_state={check.verifier_state}, gate_enabled={check.gate_enabled}"
        )
    if report.findings:
        lines.extend(["", "## Findings"])
        for finding in report.findings[:100]:
            lines.append(
                f"- [{finding.status.value}] "
                f"{finding.stage}/{finding.type}: {finding.message}"
            )
        if len(report.findings) > 100:
            lines.append(f"- ... {len(report.findings) - 100} more findings")
    else:
        lines.extend(["", "No findings."])
    lines.append("")
    return "\n".join(lines)


_ROUTE_STAGE_FILES = {
    "T1": {
        "stage_key": "t1_document_facts",
        "routes": {
            "shared_input": {"filename": "01_document_facts.json", "payload_type": "json"},
        },
    },
    "L1": {
        "stage_key": "l1_input_contract",
        "routes": {
            "shared_input": {
                "filename": "01.5_l1_input_contract.json",
                "payload_type": "json",
            },
        },
    },
    "T2": {
        "stage_key": "t2_unit_pagination",
        "routes": {
            "code_raw": {"filename": "02.0_t2_code_unit_map.yaml", "payload_type": "yaml"},
            "ai_raw": {"filename": "02.2_t2_ai_unit_observation.yaml", "payload_type": "yaml"},
            "merged": {"filename": "02.3_t2_merged_unit_map.yaml", "payload_type": "yaml"},
        },
    },
    "T3": {
        "stage_key": "t3_element_policy",
        "routes": {
            "code_raw": {"filename": "03.0_t3_code_element_spec.yaml", "payload_type": "yaml"},
            "ai_raw": {"filename": "03.1_t3_ai_element_observation.yaml", "payload_type": "yaml"},
            "merged": {"filename": "03.2_t3_merged_element_spec.yaml", "payload_type": "yaml"},
        },
    },
    "T4": {
        "stage_key": "t4_global_layout",
        "routes": {
            "code_raw": {"filename": "04.0_t4_code_global_spec.yaml", "payload_type": "yaml"},
            "ai_raw": {"filename": "04.1_t4_ai_layout_observation.yaml", "payload_type": "yaml"},
            "merged": {"filename": "04.2_t4_merged_global_spec.yaml", "payload_type": "yaml"},
        },
    },
    "T5": {
        "stage_key": "t5_template_spec",
        "routes": {
            "code_raw": {"not_evaluable_reason": "T5 code_raw replay is not materialized"},
            "ai_raw": {"not_evaluable_reason": "T5 ai_raw replay is not materialized"},
            "merged": {"filename": "05_template_spec.yaml", "payload_type": "yaml"},
        },
    },
    "T6": {
        "stage_key": "t6_fillable_template",
        "routes": {
            "code_raw": {"not_evaluable_reason": "T6 code_raw replay is not materialized"},
            "ai_raw": {"not_evaluable_reason": "T6 ai_raw replay is not materialized"},
            "merged": {
                "filename": ["06.1_fillable_template.docx", "06.2_build_manifest.json"],
                "payload_type": "composite",
                "artifact_type": "t6_execution_bundle",
            },
        },
    },
    "T7": {
        "stage_key": "t7_verification_report",
        "routes": {
            "code_raw": {"not_evaluable_reason": "T7 code_raw replay is not materialized"},
            "ai_raw": {"not_evaluable_reason": "T7 ai_raw replay is not materialized"},
            "merged": {"filename": "07_verification_report.json", "payload_type": "json"},
        },
    },
    "POST_T6": {
        "stage_key": "post_t6_template_gap",
        "routes": {
            "code_raw": {"not_evaluable_reason": "post-T6 code_raw gap replay is not materialized"},
            "ai_raw": {"not_evaluable_reason": "post-T6 ai_raw gap replay is not materialized"},
            "merged": {"filename": "template_gap_report.json", "payload_type": "json"},
        },
    },
}


def build_template_generation_route_eval_report(
    report: TemplateGenerationJudgeReport,
    report_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    routes: list[dict[str, Any]] = []
    stage_metrics: dict[str, dict[str, Any]] = {}
    mismatches: list[dict[str, Any]] = []
    run_dir = report.run_bundle.source_run_dir
    for stage_id, spec in _ROUTE_STAGE_FILES.items():
        stage_routes = {
            route_id: _route_candidate(
                run_dir,
                stage_id=stage_id,
                stage_key=str(spec["stage_key"]),
                route_id=route_id,
                filename=route_spec.get("filename"),
                payload_type=str(route_spec.get("payload_type") or "yaml"),
                artifact_type=route_spec.get("artifact_type"),
                not_evaluable_reason=route_spec.get("not_evaluable_reason"),
            )
            for route_id, route_spec in (spec.get("routes") or {}).items()
        }
        routes.extend(stage_routes.values())
        code_hash = (stage_routes.get("code_raw") or {}).get("payload_hash")
        ai_hash = (stage_routes.get("ai_raw") or {}).get("payload_hash")
        merged_hash = (stage_routes.get("merged") or {}).get("payload_hash")
        ai_availability = (stage_routes.get("ai_raw") or {}).get("availability", "NOT_APPLICABLE")
        changed_from_code = bool(
            code_hash and merged_hash and code_hash != merged_hash
        )
        stage_metrics[stage_id] = {
            "stage_key": spec["stage_key"],
            "ai_availability": ai_availability,
            "changed_from_code": changed_from_code,
            "code_raw_hash": code_hash,
            "ai_raw_hash": ai_hash,
            "merged_hash": merged_hash,
            "route_availability": {
                route_id: route.get("availability")
                for route_id, route in stage_routes.items()
            },
            "route_hashes": {
                route_id: route.get("payload_hash")
                for route_id, route in stage_routes.items()
            },
        }
        if stage_id == "L1":
            stage_metrics[stage_id]["coverage"] = _l1_route_coverage(
                stage_routes.get("shared_input")
            )
            mismatches.extend(
                _l1_route_mismatches(stage_routes.get("shared_input"))
            )
        if stage_id == "T4":
            hint_consumption = _t4_hint_consumption(report)
            stage_metrics[stage_id]["hint_consumption"] = hint_consumption
            mismatches.extend(_t4_hint_consumption_mismatches(hint_consumption))
        if ai_availability == "AVAILABLE" and not changed_from_code:
            mismatches.append(
                {
                    "id": f"{stage_id}-ROUTE-MISMATCH-001",
                    "stage_id": stage_id,
                    "stage_key": spec["stage_key"],
                    "type": "ai_available_but_merged_equals_code",
                    "expected": "merged route changes from code_raw or records explicit noop",
                    "observed": "ai_raw is AVAILABLE but merged hash equals code_raw",
                    "route_ids": ["code_raw", "ai_raw", "merged"],
                }
            )
        if ai_availability == "NOT_AVAILABLE":
            mismatches.append(
                {
                    "id": f"{stage_id}-ROUTE-MISMATCH-001",
                    "stage_id": stage_id,
                    "stage_key": spec["stage_key"],
                    "type": "ai_raw_not_available",
                    "expected": "ai_raw route available for route comparison",
                    "observed": "ai_raw route is NOT_AVAILABLE",
                    "route_ids": ["ai_raw"],
                }
            )
        for route_id, route in stage_routes.items():
            if route.get("availability") != "NOT_EVALUABLE":
                continue
            mismatches.append(
                {
                    "id": f"{stage_id}-{route_id.upper()}-ROUTE-MISMATCH-001",
                    "stage_id": stage_id,
                    "stage_key": spec["stage_key"],
                    "type": "route_replay_not_materialized",
                    "expected": f"{route_id} route can be evaluated or explicitly skipped by stage contract",
                    "observed": str(route.get("not_evaluable_reason") or "route is not evaluable"),
                    "route_ids": [route_id],
                }
            )
        merged_route = stage_routes.get("merged")
        if stage_id in {"T5", "T6", "T7", "POST_T6"} and merged_route is not None:
            if merged_route.get("availability") == "NOT_AVAILABLE":
                mismatches.append(
                    {
                        "id": f"{stage_id}-MERGED-ROUTE-MISMATCH-001",
                        "stage_id": stage_id,
                        "stage_key": spec["stage_key"],
                        "type": "merged_route_not_available",
                        "expected": "merged route artifact exists for downstream diagnosis",
                        "observed": f"{stage_id} merged route artifact is NOT_AVAILABLE",
                        "route_ids": ["merged"],
                    }
                )
    root_causes = [
        {
            "id": mismatch["id"].replace("MISMATCH", "ROOT-CAUSE"),
            "mismatch_id": mismatch["id"],
            "stage_id": mismatch["stage_id"],
            "stage_key": mismatch["stage_key"],
            "category": _route_mismatch_root_cause_category(mismatch),
            "reason": mismatch["observed"],
        }
        for mismatch in mismatches
    ]
    owner_assignments = [
        {
            "id": mismatch["id"].replace("MISMATCH", "OWNER"),
            "mismatch_id": mismatch["id"],
            "primary": _route_mismatch_owner(mismatch),
            "secondary": ["standard_judge_owner"],
        }
        for mismatch in mismatches
    ]
    fix_plan = [
        {
            "id": mismatch["id"].replace("MISMATCH", "FIX"),
            "mismatch_id": mismatch["id"],
            "action": _route_mismatch_fix_action(mismatch),
            "verification": "rerun template_generation_route_eval_report and confirm mismatch is gone",
        }
        for mismatch in mismatches
    ]
    return {
        "artifact_type": "template_generation_route_eval_report",
        "artifact_version": "1.0",
        "profile_id": report.standard_set.target_standard.get("coverage_requirements", {}).get("profile"),
        "school_id": report.standard_set.school_id,
        "run_id": report.run_bundle.source_run_id,
        "routes": routes,
        "shared_inputs": {"t1_document_facts": "01_document_facts.json"},
        "stage_metrics": stage_metrics,
        "cross_route_summary": {
            "route_count": len(routes),
            "mismatch_count": len(mismatches),
        },
        "mismatches": mismatches,
        "root_causes": root_causes,
        "owner_assignments": owner_assignments,
        "fix_plan": fix_plan,
    }


def _route_mismatch_root_cause_category(mismatch: dict[str, Any]) -> str:
    mismatch_type = str(mismatch.get("type") or "")
    if mismatch_type == "ai_available_but_merged_equals_code":
        return "merge_bridge_no_effect"
    if mismatch_type == "route_replay_not_materialized":
        return "route_replay_missing"
    if mismatch_type == "merged_route_not_available":
        return "downstream_evidence_missing"
    if mismatch_type.startswith("l1_"):
        return "l1_input_contract_gap"
    if mismatch_type.startswith("t4_"):
        return "t4_layout_hint_consumption_gap"
    return "ai_route_missing"


def _route_mismatch_owner(mismatch: dict[str, Any]) -> str:
    mismatch_type = str(mismatch.get("type") or "")
    if mismatch_type == "ai_available_but_merged_equals_code":
        return "template_generation_agent_bridge_owner"
    if mismatch_type == "route_replay_not_materialized":
        return "template_generation_route_eval_owner"
    if mismatch_type == "merged_route_not_available":
        return "template_generation_downstream_evidence_owner"
    if mismatch_type.startswith("l1_"):
        return "template_generation_input_contract_owner"
    if mismatch_type.startswith("t4_"):
        return "template_generation_t4_layout_owner"
    return "template_generation_observation_owner"


def _route_mismatch_fix_action(mismatch: dict[str, Any]) -> str:
    mismatch_type = str(mismatch.get("type") or "")
    if mismatch_type == "ai_available_but_merged_equals_code":
        return (
            "Patch bridge/reconciler so accepted AI observation changes merged output "
            "or records explicit noop."
        )
    if mismatch_type == "route_replay_not_materialized":
        return (
            "Implement isolated route replay or mark the route explicitly out of scope "
            "in the stage contract."
        )
    if mismatch_type == "merged_route_not_available":
        return "Persist or generate the downstream evidence artifact before running route eval."
    if mismatch_type.startswith("l1_"):
        return (
            "Patch L1 input projection, render binding, or bundle gate coverage until "
            "the contract is explicit."
        )
    if mismatch_type.startswith("t4_"):
        return (
            "Promote accepted T4 layout hints from advisory observations into "
            "first-class global_spec/T5/T6 consumption fields."
        )
    return "Run Module 1 observation or provide replay bundle before judging AI-primary readiness."


def _route_candidate(
    run_dir: Path,
    *,
    stage_id: str,
    stage_key: str,
    route_id: str,
    filename: Any,
    payload_type: str,
    artifact_type: Any = None,
    not_evaluable_reason: Any = None,
) -> dict[str, Any]:
    if not_evaluable_reason:
        return {
            "route_id": route_id,
            "stage_key": stage_key,
            "stage_id": stage_id,
            "artifact_type": artifact_type,
            "payload_path": None,
            "payload_paths": [],
            "payload_hash": None,
            "availability": "NOT_EVALUABLE",
            "origin": "route_eval_contract",
            "not_evaluable_reason": str(not_evaluable_reason),
        }
    filenames = (
        [str(item) for item in filename]
        if isinstance(filename, list)
        else [str(filename)]
    )
    paths = [_route_artifact_path(run_dir, item) for item in filenames]
    found_paths = [path for path in paths if path is not None]
    path = found_paths[0] if found_paths else None
    payload: dict[str, Any] = {}
    payload_hash = None
    availability = "NOT_AVAILABLE"
    if found_paths and len(found_paths) == len(filenames):
        payload_hash = (
            sha256_file(path)
            if len(found_paths) == 1 and path is not None
            else sha256_json({item.name: sha256_file(item) for item in found_paths})
        )
        payload = _read_route_payload(found_paths, payload_type)
        availability = str(
            (payload.get("route") or {}).get("availability")
            or ("AVAILABLE" if payload else "UNKNOWN")
        )
    return {
        "route_id": route_id,
        "stage_key": stage_key,
        "stage_id": stage_id,
        "artifact_type": artifact_type or payload.get("artifact_type"),
        "payload_path": str(path) if path is not None else None,
        "payload_paths": [str(item) for item in found_paths],
        "payload_hash": payload_hash,
        "availability": availability,
        "origin": (payload.get("route") or {}).get("origin"),
    }


def _read_route_payload(paths: list[Path], payload_type: str) -> dict[str, Any]:
    if payload_type == "json":
        loaded = read_json(paths[0])
        return loaded if isinstance(loaded, dict) else {}
    if payload_type == "yaml":
        loaded = read_yaml(paths[0])
        return loaded if isinstance(loaded, dict) else {}
    if payload_type == "composite":
        payload: dict[str, Any] = {"artifact_type": "composite_route_artifact", "parts": []}
        for path in paths:
            part: dict[str, Any] = {
                "name": path.name,
                "path": str(path),
                "sha256": sha256_file(path),
            }
            if path.suffix == ".json":
                loaded = read_json(path)
                if isinstance(loaded, dict):
                    part["artifact_type"] = loaded.get("artifact_type")
                    part["status"] = loaded.get("status")
            payload["parts"].append(part)
        return payload
    return {"artifact_type": payload_type}


def _route_artifact_path(run_dir: Path, filename: str) -> Path | None:
    candidates = [
        run_dir / filename,
        run_dir / "artifacts" / _compat_route_filename(filename),
    ]
    if filename == "template_gap_report.json":
        candidates.extend(
            [
                run_dir.parent / "template_gap" / filename,
                run_dir.parent / "template_gap" / "artifacts" / filename,
                run_dir.parent.parent / "template_gap" / "artifacts" / filename,
            ]
        )
    for path in candidates:
        if path.exists():
            return path
    return None


def _compat_route_filename(filename: str) -> str:
    return {
        "01.5_l1_input_contract.json": "template_generation_l1_input_contract.json",
        "02.0_t2_code_unit_map.yaml": "t2_code_unit_map.yaml",
        "02.2_t2_ai_unit_observation.yaml": "t2_ai_unit_observation.yaml",
        "02.3_t2_merged_unit_map.yaml": "t2_merged_unit_map.yaml",
        "03.0_t3_code_element_spec.yaml": "t3_code_element_spec.yaml",
        "03.1_t3_ai_element_observation.yaml": "t3_ai_element_observation.yaml",
        "03.2_t3_merged_element_spec.yaml": "t3_merged_element_spec.yaml",
        "04.0_t4_code_global_spec.yaml": "t4_code_global_spec.yaml",
        "04.1_t4_ai_layout_observation.yaml": "t4_ai_layout_observation.yaml",
        "04.2_t4_merged_global_spec.yaml": "t4_merged_global_spec.yaml",
        "05_template_spec.yaml": "template_spec.yaml",
        "06.2_build_manifest.json": "build_manifest.json",
        "07_verification_report.json": "verification_report.json",
        "template_gap_report.json": "template_gap_report.json",
    }.get(filename, filename)


def _l1_route_coverage(route: dict[str, Any] | None) -> dict[str, Any]:
    if not route or route.get("availability") != "AVAILABLE" or not route.get("payload_path"):
        return {"available": False}
    payload = read_json(Path(str(route["payload_path"])))
    coverage = payload.get("coverage", {}) if isinstance(payload, dict) else {}
    return {"available": True, **coverage}


def _l1_route_mismatches(route: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not route or route.get("availability") != "AVAILABLE" or not route.get("payload_path"):
        return [
            {
                "id": "L1-ROUTE-MISMATCH-001",
                "stage_id": "L1",
                "stage_key": "l1_input_contract",
                "type": "l1_input_contract_not_available",
                "expected": "L1 input contract artifact exists",
                "observed": "template_generation_l1_input_contract route is not AVAILABLE",
                "route_ids": ["shared_input"],
            }
        ]
    payload = read_json(Path(str(route["payload_path"])))
    coverage = payload.get("coverage", {}) if isinstance(payload, dict) else {}
    mismatches: list[dict[str, Any]] = []
    if coverage.get("render_status") in {None, "", "not_available", "projection_fallback"}:
        mismatches.append(
            {
                "id": "L1-ROUTE-MISMATCH-002",
                "stage_id": "L1",
                "stage_key": "l1_input_contract",
                "type": "l1_visual_render_not_real",
                "expected": "visual_page_index binds a real render or records why it cannot",
                "observed": f"render_status={coverage.get('render_status')}",
                "route_ids": ["shared_input"],
            }
        )
    if int(coverage.get("source_object_unbound_count") or 0) > 0:
        mismatches.append(
            {
                "id": "L1-ROUTE-MISMATCH-003",
                "stage_id": "L1",
                "stage_key": "l1_input_contract",
                "type": "l1_object_binding_gaps",
                "expected": "source_object_index entries have explicit page/bbox binding or reason",
                "observed": f"{coverage.get('source_object_unbound_count')} object(s) unbound",
                "route_ids": ["shared_input"],
            }
        )
    invalid = coverage.get("bundle_gate_invalid_stages") or []
    if invalid:
        mismatches.append(
            {
                "id": "L1-ROUTE-MISMATCH-004",
                "stage_id": "L1",
                "stage_key": "l1_input_contract",
                "type": "l1_bundle_gate_invalid",
                "expected": "AI observation bundle passes hash/schema/coverage gate",
                "observed": f"invalid bundle stages: {invalid}",
                "route_ids": ["shared_input"],
            }
        )
    return mismatches


def _t4_hint_consumption(report: TemplateGenerationJudgeReport) -> dict[str, Any]:
    run_dir = report.run_bundle.source_run_dir
    hints = _load_run_json(
        run_dir,
        "13_agent_t4_hints.json",
        "artifacts/agent_t4_hints.json",
    ) or {}
    unit_map = report.run_bundle.payload("unit_map") or {}
    global_spec = report.run_bundle.payload("global_spec") or {}
    template_spec = report.run_bundle.payload("template_spec") or {}
    build_manifest = report.run_bundle.payload("build_manifest") or {}
    page_hint_ids = {
        str(item.get("proposal_id"))
        for item in hints.get("page_policy_hints", []) or []
        if isinstance(item, dict) and item.get("proposal_id")
    }
    page_ids_in_units = {
        str((unit.get("page") or {}).get("agent_proposal_id"))
        for unit in unit_map.get("units", []) or []
        if isinstance(unit, dict) and (unit.get("page") or {}).get("agent_proposal_id")
    }
    page_ids_in_actions = {
        str(action.get("agent_proposal_id"))
        for action in build_manifest.get("actions_executed", []) or []
        if isinstance(action, dict) and action.get("agent_proposal_id")
    }
    global_page_ids = page_hint_ids & (page_ids_in_units | page_ids_in_actions)
    section_hints = [
        item for item in hints.get("section_profile_hints", []) or [] if isinstance(item, dict)
    ]
    page_numbering_hints = [
        item for item in hints.get("page_numbering_hints", []) or [] if isinstance(item, dict)
    ]
    section_observation_count = sum(
        len(profile.get("ai_observations") or [])
        for profile in global_spec.get("section_profiles", []) or []
        if isinstance(profile, dict)
    )
    template_section_observation_count = sum(
        len(profile.get("ai_observations") or [])
        for profile in (template_spec.get("global", {}) or {}).get("section_profiles", []) or []
        if isinstance(profile, dict)
    )
    page_numbering_observation_count = len(
        (global_spec.get("page_numbering", {}) or {}).get("ai_observations", []) or []
    )
    return {
        "hints_present": bool(hints),
        "page_policy_hint_count": len(page_hint_ids),
        "page_policy_consumed_count": len(global_page_ids),
        "page_policy_consumed_proposal_ids": sorted(global_page_ids),
        "section_profile_hint_count": len(section_hints),
        "section_profile_recorded_in_global_spec_count": section_observation_count,
        "section_profile_recorded_in_template_spec_count": template_section_observation_count,
        "section_profile_effective_action_count": 0,
        "page_numbering_hint_count": len(page_numbering_hints),
        "page_numbering_recorded_in_global_spec_count": page_numbering_observation_count,
        "page_numbering_effective_action_count": 0,
    }


def _t4_hint_consumption_mismatches(consumption: dict[str, Any]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    if consumption.get("page_policy_hint_count") and (
        consumption.get("page_policy_consumed_count") != consumption.get("page_policy_hint_count")
    ):
        mismatches.append(
            {
                "id": "T4-HINT-MISMATCH-001",
                "stage_id": "T4",
                "stage_key": "t4_global_layout",
                "type": "t4_page_policy_hint_not_consumed",
                "expected": "accepted page_policy_hints patch unit page policy and T6 page actions",
                "observed": (
                    f"{consumption.get('page_policy_consumed_count')} of "
                    f"{consumption.get('page_policy_hint_count')} page hints consumed"
                ),
                "route_ids": ["merged"],
            }
        )
    if consumption.get("section_profile_hint_count") and not consumption.get(
        "section_profile_effective_action_count"
    ):
        mismatches.append(
            {
                "id": "T4-HINT-MISMATCH-002",
                "stage_id": "T4",
                "stage_key": "t4_global_layout",
                "type": "t4_section_profile_hint_advisory_only",
                "expected": "accepted section_profile_hints become first-class layout fields consumed by T5/T6",
                "observed": "section_profile_hints are recorded as ai_observations without effective T6 action",
                "route_ids": ["merged"],
            }
        )
    if consumption.get("page_numbering_hint_count") and not consumption.get(
        "page_numbering_effective_action_count"
    ):
        mismatches.append(
            {
                "id": "T4-HINT-MISMATCH-003",
                "stage_id": "T4",
                "stage_key": "t4_global_layout",
                "type": "t4_page_numbering_hint_advisory_only",
                "expected": "accepted page_numbering_hints become first-class page numbering fields consumed by T5/T6",
                "observed": "page_numbering_hints are recorded as ai_observations without effective T6 action",
                "route_ids": ["merged"],
            }
        )
    return mismatches


def build_template_generation_route_eval_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Template Generation Route Eval Report",
        "",
        f"- Run: {report.get('run_id')}",
        f"- Routes: {report.get('cross_route_summary', {}).get('route_count', 0)}",
        f"- Mismatches: {report.get('cross_route_summary', {}).get('mismatch_count', 0)}",
        "",
        "## Stage Metrics",
    ]
    for stage_id, metrics in (report.get("stage_metrics") or {}).items():
        lines.append(
            "- "
            f"{stage_id} {metrics.get('stage_key')}: "
            f"ai={metrics.get('ai_availability')}, "
            f"changed_from_code={metrics.get('changed_from_code')}"
        )
    lines.extend(["", "## Mismatches"])
    if report.get("mismatches"):
        for mismatch in report["mismatches"]:
            lines.append(
                f"- {mismatch['id']} {mismatch['type']}: {mismatch['observed']}"
            )
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _first_bad_stage(stage_checks: list[StageCheck]) -> str | None:
    for check in stage_checks:
        if check.status in {Status.FAIL, Status.UNKNOWN}:
            return check.stage_id
    return None


def _blocked_at_from_findings(findings: list[Finding]) -> str | None:
    for finding in findings:
        if finding.severity == "blocking":
            return finding.stage
    return None
