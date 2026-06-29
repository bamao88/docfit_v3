from __future__ import annotations

from copy import deepcopy
import shutil
from pathlib import Path
from typing import Any

from docfit.core.io import read_json, sha256_file
from docfit.core.models import Finding, StageResult
from docfit.core.status import StageRunState, Status, merge_statuses
from docfit.harness.coverage import coverage_gate_findings
from docfit.template_gap.gap import evaluate_generated_template_gap
from docfit.harness.profiles import BOOTSTRAP_PROFILE, get_eval_profile
from docfit.harness.product_quality import (
    BUSINESS_ACCEPTANCE_STAGES,
    audit_e2e_case,
    business_acceptance_coverage,
)
from docfit.harness.real_core import (
    case_id_for,
    is_real_core_bundle,
    student_id_for_docx,
)
from docfit.harness.reports import write_report_bundle
from docfit.harness.standards import load_standard_bundle
from docfit.stages.content_extract.runner import extract_student_content, write_content_outputs
from docfit.stages.placement.runner import build_placement_plan, write_placement_outputs
from docfit.stages.render.runner import render_docx, write_render_outputs
from docfit.template_generation.agent import AgentConfig
from docfit.template_generation.runner import (
    generate_template,
    write_template_generation_outputs,
)
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


def _bundle_root_from_output_dir(out_dir: Path) -> Path:
    resolved = out_dir.resolve()
    parts = resolved.parts
    for marker in ("eval_runs", "human"):
        if marker in parts:
            index = parts.index(marker)
            if index > 0:
                return Path(*parts[:index])
    return resolved


def _template_generation_project_dir(
    root: Path,
    *,
    template_docx: Path | None = None,
    out_dir: Path | None = None,
) -> Path:
    if out_dir is not None:
        return _bundle_root_from_output_dir(out_dir) / "human"
    if template_docx is not None:
        return (
            root
            / "test_outputs"
            / "debug"
            / "template_generation"
            / template_docx.stem
            / "human"
        )
    return root / "test_outputs" / "debug" / "template_generation" / "manual" / "human"


def _required_capabilities(
    bundle: Any,
    contract_key: str,
    fallback: list[str],
) -> list[str]:
    if bundle is None:
        return fallback
    stage_by_contract = {
        "template_contract": "template",
        "student_content_contract": "content",
        "placement_contract": "placement",
        "render_contract": "render",
    }
    profile_id = bundle.signed_standard.get("coverage_requirements", {}).get("profile")
    profile = get_eval_profile(profile_id or "")
    stage = stage_by_contract.get(contract_key)
    if profile is not None and stage is not None:
        return profile.capabilities_for_stage(stage)
    contract = bundle.contracts.get(contract_key, {})
    if "required_capabilities" in contract:
        return list(contract.get("required_capabilities") or [])
    return fallback


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


def _renumber_findings(findings: list[Finding], *, start_index: int) -> list[Finding]:
    for offset, finding in enumerate(findings):
        finding.finding_id = f"f_{start_index + offset:03d}"
    return findings


def _merge_generated_template_gap(
    template_result: StageResult,
    gap_result: StageResult,
) -> None:
    gap_findings = _renumber_findings(
        gap_result.findings,
        start_index=len(template_result.findings) + 1,
    )
    template_result.findings.extend(gap_findings)
    template_result.status = merge_statuses([template_result.status, gap_result.status])
    template_result.artifacts.update(gap_result.artifacts)
    template_result.artifact_paths.update(gap_result.artifact_paths)
    template_result.coverage.update(gap_result.coverage)
    if template_result.blocked_at is None and gap_result.blocked_at is not None:
        template_result.blocked_at = gap_result.blocked_at


def _run_template_generation_for_pipeline(
    template_docx: Path,
    out_dir: Path,
    *,
    debug_root: Path | None = None,
    agent_config: AgentConfig | None = None,
) -> StageResult:
    generation_out_dir = out_dir / "template_generation"
    result = generate_template(
        template_docx,
        generation_out_dir,
        debug_root=debug_root,
        agent_config=agent_config,
    )
    write_template_generation_outputs(generation_out_dir, result)
    _write_stage_report(generation_out_dir, result)
    return result


def _merge_template_generation_result(
    template_result: StageResult,
    generation_result: StageResult,
) -> None:
    generation_findings = _renumber_findings(
        generation_result.findings,
        start_index=len(template_result.findings) + 1,
    )
    template_result.findings.extend(generation_findings)
    template_result.status = merge_statuses(
        [template_result.status, generation_result.status]
    )
    template_result.coverage.update(generation_result.coverage)
    for key, path in generation_result.artifact_paths.items():
        template_result.artifact_paths[f"template_generate.{key}"] = path
    if template_result.blocked_at is None and generation_result.blocked_at is not None:
        template_result.blocked_at = generation_result.blocked_at


def _bind_fillable_template_to_artifact(
    template_artifact: dict[str, Any],
    fillable_template_docx: Path,
    generation_result: StageResult,
) -> dict[str, Any]:
    bound = deepcopy(template_artifact)
    provenance = bound.setdefault("provenance", {})
    source_template_docx = provenance.get("template_docx")
    if source_template_docx is not None:
        provenance["source_template_docx"] = source_template_docx
    provenance["template_docx"] = str(fillable_template_docx)
    provenance["fillable_template_docx"] = str(fillable_template_docx)
    provenance["generated_template_docx"] = str(fillable_template_docx)
    manifest_path = generation_result.artifact_paths.get("build_manifest")
    if manifest_path is not None:
        provenance["build_manifest"] = str(manifest_path)
    input_hashes = bound.setdefault("input_hashes", {})
    if fillable_template_docx.exists():
        input_hashes["fillable_template_docx"] = sha256_file(fillable_template_docx)
    status_notes = bound.setdefault("status_notes", [])
    status_notes.append(
        "e2e/render use fillable_template.docx from the template generation stage"
    )
    return bound


def _merge_findings_into_stage_statuses(
    stage_statuses: dict[str, str],
    findings: list[Finding],
) -> None:
    for stage in BUSINESS_ACCEPTANCE_STAGES:
        stage_findings = [
            finding
            for finding in findings
            if finding.stage == stage and finding.severity == "blocking"
        ]
        if not stage_findings:
            continue
        existing_status = stage_statuses.get(stage)
        statuses = [finding.status for finding in stage_findings]
        if existing_status is not None:
            statuses.insert(0, Status(existing_status))
        stage_statuses[stage] = merge_statuses(statuses).value


def _first_non_pass_stage(stage_statuses: dict[str, str]) -> str | None:
    for stage in BUSINESS_ACCEPTANCE_STAGES:
        status = stage_statuses.get(stage)
        if status is not None and Status(status) != Status.PASS:
            return stage
    return None


def run_template_eval(root: Path, school_id: str, template_docx: Path, out_dir: Path) -> StageResult:
    bundle, standard_findings = load_standard_bundle(root, school_id, finding_stage="template")
    if bundle is None:
        result = StageResult("template", Status.UNKNOWN, findings=standard_findings)
    else:
        result = parse_template(template_docx, bundle)
        result.findings = standard_findings + result.findings
        if standard_findings and result.status == Status.PASS:
            result.status = Status.UNKNOWN
        if is_real_core_bundle(bundle):
            generation_result = _run_template_generation_for_pipeline(
                template_docx,
                out_dir,
                debug_root=_template_generation_project_dir(
                    root,
                    template_docx=template_docx,
                    out_dir=out_dir,
                ),
            )
            _merge_template_generation_result(result, generation_result)
            fillable_template_docx = generation_result.artifact_paths.get(
                "fillable_template_docx"
            )
            if fillable_template_docx is not None and fillable_template_docx.exists():
                result.artifacts["template_artifact"] = _bind_fillable_template_to_artifact(
                    result.artifacts["template_artifact"],
                    fillable_template_docx,
                    generation_result,
                )
            gap_result = evaluate_generated_template_gap(
                bundle,
                fillable_template_docx
                or root
                / "inputs"
                / "targets"
                / school_id
                / "fixtures"
                / "template_gap"
                / "generated_template.input.docx",
                out_dir,
            )
            _merge_generated_template_gap(result, gap_result)
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


def run_template_gap_eval(
    root: Path,
    school_id: str,
    generated_template_docx: Path,
    out_dir: Path,
) -> StageResult:
    bundle, standard_findings = load_standard_bundle(root, school_id, finding_stage="template")
    if bundle is None:
        result = StageResult("template", Status.UNKNOWN, findings=standard_findings)
    else:
        result = evaluate_generated_template_gap(bundle, generated_template_docx, out_dir)
        result.findings = standard_findings + _renumber_findings(
            result.findings,
            start_index=len(standard_findings) + 1,
        )
        result.status = merge_statuses(
            [result.status] + [finding.status for finding in standard_findings]
        )
        _apply_coverage_gate(
            result,
            _required_capabilities(
                bundle,
                "template_quality_contract",
                BOOTSTRAP_PROFILE.capabilities_for_stage("template"),
            ),
        )
    _write_stage_report(out_dir, result)
    return result


def run_template_generate_eval(
    root: Path,
    template_docx: Path,
    out_dir: Path,
    *,
    agent_config: AgentConfig | None = None,
) -> StageResult:
    result = generate_template(
        template_docx,
        out_dir,
        debug_root=_template_generation_project_dir(
            root,
            template_docx=template_docx,
            out_dir=out_dir,
        ),
        agent_config=agent_config,
    )
    write_template_generation_outputs(out_dir, result)
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
    profile_id = (
        bundle.signed_standard.get("coverage_requirements", {}).get("profile")
        if bundle is not None
        else None
    )
    student_id = content_artifact.get("student_id")
    case_id = case_id_for(school_id, student_id)
    result = build_placement_plan(
        template_artifact,
        content_artifact,
        drop_content_id_for_test=drop_content_id_for_test,
        root=root,
        profile_id=profile_id,
        case_id=case_id,
        school_id=school_id,
        student_id=student_id,
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

    real_core_run = is_real_core_bundle(bundle)
    profile_id = (
        bundle.signed_standard.get("coverage_requirements", {}).get("profile")
        if real_core_run
        else BOOTSTRAP_PROFILE.profile_id
    )
    student_id = student_id_for_docx(root, student_docx) if real_core_run else None
    case_id = case_id_for(school_id, student_id) if real_core_run else None

    template_result = parse_template(bundle.template_docx, bundle)
    template_result.findings = standard_findings + template_result.findings
    if standard_findings and template_result.status == Status.PASS:
        template_result.status = Status.UNKNOWN
    if real_core_run:
        generation_result = _run_template_generation_for_pipeline(
            bundle.template_docx,
            out_dir,
            debug_root=_template_generation_project_dir(
                root,
                template_docx=bundle.template_docx,
                out_dir=out_dir,
            ),
        )
        _merge_template_generation_result(template_result, generation_result)
        fillable_template_docx = generation_result.artifact_paths.get(
            "fillable_template_docx"
        )
        if fillable_template_docx is not None and fillable_template_docx.exists():
            template_result.artifacts["template_artifact"] = (
                _bind_fillable_template_to_artifact(
                    template_result.artifacts["template_artifact"],
                    fillable_template_docx,
                    generation_result,
                )
            )
        gap_result = evaluate_generated_template_gap(
            bundle,
            fillable_template_docx
            or root
            / "inputs"
            / "targets"
            / school_id
            / "fixtures"
            / "template_gap"
            / "generated_template.input.docx",
            out_dir,
        )
        _merge_generated_template_gap(template_result, gap_result)
    _apply_coverage_gate(
        template_result,
        _required_capabilities(
            bundle,
            "template_contract",
            BOOTSTRAP_PROFILE.capabilities_for_stage("template"),
        ),
    )
    write_template_outputs(out_dir, template_result)
    stage_statuses["template"] = template_result.status.value
    stage_run_states["template"] = StageRunState.RAN.value
    all_findings = template_result.findings
    artifacts.update(template_result.artifacts)
    artifact_paths.update(template_result.artifact_paths)
    coverage.update(template_result.coverage)
    if template_result.status != Status.PASS and not real_core_run:
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

    content_result = extract_student_content(
        student_docx,
        root=root,
        profile_id=profile_id,
        student_id=student_id,
    )
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
        root=root,
        profile_id=profile_id,
        case_id=case_id,
        school_id=school_id,
        student_id=student_id,
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

    product_quality_findings: list[Finding] = []
    if real_core_run:
        product_quality_findings = _renumber_findings(
            audit_e2e_case(out_dir),
            start_index=len(all_findings) + 1,
        )
        all_findings.extend(product_quality_findings)
        coverage.update(business_acceptance_coverage(product_quality_findings))
        _merge_findings_into_stage_statuses(stage_statuses, product_quality_findings)

    blocked_at = _first_non_pass_stage(stage_statuses)
    if final_copy and blocked_at is None:
        final_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(render_result.artifact_paths["final_docx"], final_copy)
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
    blocking_finding_statuses = [
        finding.status
        for finding in findings
        if finding.severity == "blocking"
    ]
    final_status = merge_statuses(completed_statuses + blocking_finding_statuses)
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
    for key, path in artifact_paths.items():
        artifact_refs[key] = str(path)
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
