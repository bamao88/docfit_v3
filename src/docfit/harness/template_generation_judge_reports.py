from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docfit.core.io import write_json, write_text
from docfit.core.models import Finding, StageResult
from docfit.core.status import Status, merge_statuses
from docfit.harness.reports import write_report_bundle
from docfit.harness.template_generation_run_bundle import TemplateGenerationRunBundle
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
        return {
            "artifact_type": "template_generation_judge_report",
            "artifact_version": "1.0",
            "status": self.status.value,
            "first_bad_stage": self.first_bad_stage,
            "source_run_id": self.run_bundle.source_run_id,
            "source_run_dir": str(self.run_bundle.source_run_dir),
            "source_run_dir_name": self.run_bundle.source_run_dir_name,
            "standard_set": self.standard_set.to_dict(),
            "standard_quality": self.standard_quality.to_dict(),
            "run_bundle": self.run_bundle.to_dict(),
            "stage_checks": [check.to_dict() for check in self.stage_checks],
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def to_stage_result(self) -> StageResult:
        return StageResult(
            "template_generation_judge",
            self.status,
            findings=self.findings,
            artifacts={
                "template_generation_judge_report": self.to_dict(),
                "template_generation_run_bundle": self.run_bundle.to_dict(),
                "template_generation_stage_checks": [
                    check.to_dict() for check in self.stage_checks
                ],
                "template_generation_stage_standard_quality_report": (
                    self.standard_quality.to_dict()
                ),
            },
            coverage={
                "template_generation_judge.standard_quality": (
                    self.standard_quality.status == Status.PASS
                ),
                "template_generation_judge.run_bundle": self.run_bundle.status == Status.PASS,
                "template_generation_judge.stage_checks": bool(self.stage_checks),
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

    write_json(run_bundle_path, report.run_bundle.to_dict())
    write_json(stage_checks_path, [check.to_dict() for check in report.stage_checks])
    write_json(quality_path, report.standard_quality.to_dict())
    write_text(quality_md_path, build_standard_quality_markdown(report.standard_quality))
    write_json(judge_path, report.to_dict())
    write_text(judge_md_path, build_judge_markdown(report))

    stage_statuses = {
        check.stage_key: check.status.value for check in report.stage_checks
    }
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
        },
        coverage={
            "standard_quality_status": report.standard_quality.status.value,
            "run_bundle_status": report.run_bundle.status.value,
            "source_run_id": report.run_bundle.source_run_id,
            "first_bad_stage": report.first_bad_stage,
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
        }
    )
    result.artifacts["summary"] = summary
    return result


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
    lines = [
        "# Template Generation Judge Report",
        "",
        f"- Status: {report.status.value}",
        f"- First bad stage: {report.first_bad_stage or 'none'}",
        f"- Source run id: {report.run_bundle.source_run_id}",
        f"- Source run dir: {report.run_bundle.source_run_dir}",
        f"- Standard quality: {report.standard_quality.status.value}",
        f"- Run bundle: {report.run_bundle.status.value}",
        "",
        "## Stage Checks",
    ]
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
            lines.append(f"- [{finding.status.value}] {finding.stage}/{finding.type}: {finding.message}")
        if len(report.findings) > 100:
            lines.append(f"- ... {len(report.findings) - 100} more findings")
    else:
        lines.extend(["", "No findings."])
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
