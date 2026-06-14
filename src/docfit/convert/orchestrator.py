from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from docfit.core.io import read_json
from docfit.core.models import Finding, StageResult
from docfit.core.status import StageRunState, Status, merge_statuses
from docfit.harness.coverage import coverage_gate_findings
from docfit.harness.profiles import BOOTSTRAP_PROFILE
from docfit.harness.reports import write_report_bundle
from docfit.harness.standards import load_standard_bundle
from docfit.stages.content_extract.runner import extract_student_content, write_content_outputs
from docfit.stages.placement.runner import build_placement_plan, write_placement_outputs
from docfit.stages.render.runner import render_docx, write_render_outputs
from docfit.stages.template_parse.runner import parse_template, write_template_outputs


def _artifact_refs(out_dir: Path, result: StageResult) -> dict[str, str]:
    refs = {key: str(path) for key, path in result.artifact_paths.items()}
    for key in result.artifacts:
        refs.setdefault(key, f"artifacts/{key}.json")
    if "final_docx" in result.artifact_paths:
        refs["final_docx"] = str(result.artifact_paths["final_docx"])
    return refs


def _write_stage_report(out_dir: Path, result: StageResult) -> dict[str, Any]:
    return write_report_bundle(
        out_dir,
        stage=result.stage,
        status=result.status,
        findings=result.finding_dicts(),
        artifacts=_artifact_refs(out_dir, result),
        coverage=result.coverage,
        blocked_at=result.blocked_at,
        user_message=result.user_message,
    )


def _required_capabilities(bundle: Any, contract_key: str, fallback: list[str]) -> list[str]:
    if bundle is None:
        return fallback
    contract = bundle.contracts.get(contract_key, {})
    return list(contract.get("required_capabilities") or fallback)


def _apply_coverage_gate(result: StageResult, required_capabilities: list[str]) -> StageResult:
    findings = coverage_gate_findings(
        result.stage,
        result.coverage,
        required_capabilities,
        start_index=len(result.findings) + 1,
    )
    if not findings:
        return result
    result.findings.extend(findings)
    result.status = merge_statuses([result.status] + [finding.status for finding in findings])
    return result


def run_template_eval(root: Path, school_id: str, template_docx: Path, out_dir: Path) -> StageResult:
    bundle, standard_findings = load_standard_bundle(root, school_id, finding_stage="template")
    if bundle is None:
        result = StageResult("template", Status.UNKNOWN, findings=standard_findings)
    else:
        result = parse_template(template_docx, bundle)
        result.findings = standard_findings + result.findings
        if standard_findings and result.status == Status.PASS:
            result.status = Status.UNKNOWN
        _apply_coverage_gate(
            result,
            _required_capabilities(
                bundle,
                "template_contract",
                BOOTSTRAP_PROFILE.capabilities_for_stage("template"),
            ),
        )
    write_template_outputs(out_dir, result)
    _write_stage_report(out_dir, result)
    return result


def run_content_eval(
    student_docx: Path,
    out_dir: Path,
    *,
    omit_content_id_for_test: str | None = None,
) -> StageResult:
    result = extract_student_content(
        student_docx,
        omit_content_id_for_test=omit_content_id_for_test,
    )
    _apply_coverage_gate(result, BOOTSTRAP_PROFILE.capabilities_for_stage("content"))
    write_content_outputs(out_dir, result)
    _write_stage_report(out_dir, result)
    return result


def run_placement_eval(
    root: Path,
    school_id: str,
    template_artifact_path: Path,
    content_artifact_path: Path,
    out_dir: Path,
    *,
    drop_content_id_for_test: str | None = None,
) -> StageResult:
    bundle, standard_findings = load_standard_bundle(root, school_id, finding_stage="placement")
    template_artifact = read_json(template_artifact_path)
    content_artifact = read_json(content_artifact_path)
    result = build_placement_plan(
        template_artifact,
        content_artifact,
        drop_content_id_for_test=drop_content_id_for_test,
    )
    result.findings = standard_findings + result.findings
    if standard_findings and result.status == Status.PASS:
        result.status = Status.UNKNOWN
    _apply_coverage_gate(
        result,
        _required_capabilities(
            bundle,
            "placement_contract",
            BOOTSTRAP_PROFILE.capabilities_for_stage("placement"),
        ),
    )
    write_placement_outputs(out_dir, result)
    _write_stage_report(out_dir, result)
    return result


def run_render_eval(
    root: Path,
    school_id: str,
    template_artifact_path: Path,
    placement_plan_path: Path,
    out_dir: Path,
    *,
    skip_action_id_for_test: str | None = None,
) -> StageResult:
    bundle, standard_findings = load_standard_bundle(root, school_id, finding_stage="render")
    if bundle is None:
        result = StageResult("render", Status.UNKNOWN, findings=standard_findings)
    else:
        template_artifact = read_json(template_artifact_path)
        placement_plan = read_json(placement_plan_path)
        result = render_docx(
            template_artifact,
            placement_plan,
            bundle,
            out_dir,
            skip_action_id_for_test=skip_action_id_for_test,
        )
        result.findings = standard_findings + result.findings
        if standard_findings and result.status == Status.PASS:
            result.status = Status.UNKNOWN
        _apply_coverage_gate(
            result,
            _required_capabilities(
                bundle,
                "render_contract",
                BOOTSTRAP_PROFILE.capabilities_for_stage("render"),
            ),
        )
    write_render_outputs(out_dir, result)
    _write_stage_report(out_dir, result)
    return result


def run_e2e_eval(
    root: Path,
    school_id: str,
    student_docx: Path,
    out_dir: Path,
    *,
    final_copy: Path | None = None,
) -> StageResult:
    bundle, standard_findings = load_standard_bundle(root, school_id, finding_stage="e2e")
    stage_statuses: dict[str, str] = {}
    stage_run_states = {
        "template": StageRunState.PENDING.value,
        "content": StageRunState.PENDING.value,
        "placement": StageRunState.PENDING.value,
        "render": StageRunState.PENDING.value,
    }
    all_findings: list[Finding] = list(standard_findings)
    artifacts: dict[str, Any] = {}
    artifact_paths: dict[str, Path] = {}
    coverage: dict[str, Any] = {}

    if bundle is None:
        final_status = Status.UNKNOWN
        result = StageResult("e2e", final_status, findings=all_findings, blocked_at="standards")
        write_report_bundle(
            out_dir,
            stage="e2e",
            status=final_status,
            findings=result.finding_dicts(),
            artifacts={},
            coverage={},
            stage_statuses=stage_statuses,
            stage_run_states=stage_run_states,
            blocked_at="standards",
        )
        return result

    template_result = parse_template(bundle.template_docx, bundle)
    template_result.findings = standard_findings + template_result.findings
    write_template_outputs(out_dir, template_result)
    _apply_coverage_gate(
        template_result,
        _required_capabilities(
            bundle,
            "template_contract",
            BOOTSTRAP_PROFILE.capabilities_for_stage("template"),
        ),
    )
    stage_statuses["template"] = template_result.status.value
    stage_run_states["template"] = StageRunState.RAN.value
    all_findings = template_result.findings
    artifacts.update(template_result.artifacts)
    artifact_paths.update(template_result.artifact_paths)
    coverage.update(template_result.coverage)
    if template_result.status != Status.PASS:
        return _finish_e2e(
            out_dir,
            stage_statuses,
            stage_run_states,
            all_findings,
            artifacts,
            artifact_paths,
            coverage,
            "template",
        )

    content_result = extract_student_content(student_docx)
    _apply_coverage_gate(
        content_result,
        _required_capabilities(
            bundle,
            "student_content_contract",
            BOOTSTRAP_PROFILE.capabilities_for_stage("content"),
        ),
    )
    write_content_outputs(out_dir, content_result)
    stage_statuses["content"] = content_result.status.value
    stage_run_states["content"] = StageRunState.RAN.value
    all_findings.extend(content_result.findings)
    artifacts.update(content_result.artifacts)
    artifact_paths.update(content_result.artifact_paths)
    coverage.update(content_result.coverage)
    if content_result.status != Status.PASS:
        return _finish_e2e(
            out_dir,
            stage_statuses,
            stage_run_states,
            all_findings,
            artifacts,
            artifact_paths,
            coverage,
            "content",
        )

    placement_result = build_placement_plan(
        template_result.artifacts["template_artifact"],
        content_result.artifacts["student_content_artifact"],
    )
    _apply_coverage_gate(
        placement_result,
        _required_capabilities(
            bundle,
            "placement_contract",
            BOOTSTRAP_PROFILE.capabilities_for_stage("placement"),
        ),
    )
    write_placement_outputs(out_dir, placement_result)
    stage_statuses["placement"] = placement_result.status.value
    stage_run_states["placement"] = StageRunState.RAN.value
    all_findings.extend(placement_result.findings)
    artifacts.update(placement_result.artifacts)
    artifact_paths.update(placement_result.artifact_paths)
    coverage.update(placement_result.coverage)
    if placement_result.status != Status.PASS:
        return _finish_e2e(
            out_dir,
            stage_statuses,
            stage_run_states,
            all_findings,
            artifacts,
            artifact_paths,
            coverage,
            "placement",
        )

    render_result = render_docx(
        template_result.artifacts["template_artifact"],
        placement_result.artifacts["placement_plan"],
        bundle,
        out_dir,
    )
    _apply_coverage_gate(
        render_result,
        _required_capabilities(
            bundle,
            "render_contract",
            BOOTSTRAP_PROFILE.capabilities_for_stage("render"),
        ),
    )
    write_render_outputs(out_dir, render_result)
    stage_statuses["render"] = render_result.status.value
    stage_run_states["render"] = StageRunState.RAN.value
    all_findings.extend(render_result.findings)
    artifacts.update(render_result.artifacts)
    artifact_paths.update(render_result.artifact_paths)
    coverage.update(render_result.coverage)
    if final_copy and render_result.status == Status.PASS:
        final_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(render_result.artifact_paths["final_docx"], final_copy)
    blocked_at = None if render_result.status == Status.PASS else "render"
    return _finish_e2e(
        out_dir,
        stage_statuses,
        stage_run_states,
        all_findings,
        artifacts,
        artifact_paths,
        coverage,
        blocked_at,
    )


def _finish_e2e(
    out_dir: Path,
    stage_statuses: dict[str, str],
    stage_run_states: dict[str, str],
    findings: list[Finding],
    artifacts: dict[str, Any],
    artifact_paths: dict[str, Path],
    coverage: dict[str, Any],
    blocked_at: str | None,
) -> StageResult:
    completed_statuses = [Status(status) for status in stage_statuses.values()]
    final_status = merge_statuses(completed_statuses)
    if findings and final_status == Status.PASS:
        final_status = merge_statuses([Status(finding.status) for finding in findings])
    result = StageResult(
        "e2e",
        final_status,
        findings=findings,
        artifacts=artifacts,
        artifact_paths=artifact_paths,
        coverage=coverage,
        blocked_at=blocked_at,
    )
    artifact_refs = {key: f"artifacts/{key}.json" for key in artifacts}
    if "final_docx" in artifact_paths:
        artifact_refs["final_docx"] = str(artifact_paths["final_docx"])
    write_report_bundle(
        out_dir,
        stage="e2e",
        status=final_status,
        findings=result.finding_dicts(),
        artifacts=artifact_refs,
        coverage=coverage,
        stage_statuses=stage_statuses,
        stage_run_states=stage_run_states,
        blocked_at=blocked_at,
    )
    return result
