from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, read_json, sha256_file, write_json, write_text
from docfit.core.models import Finding, StageResult
from docfit.core.status import Status, merge_statuses
from docfit.template_gap.gap import evaluate_generated_template_gap
from docfit.harness.profiles import BOOTSTRAP_PROFILE, get_eval_profile
from docfit.harness.reports import write_report_bundle
from docfit.harness.standards import coverage_gate_findings, load_standard_bundle
from docfit.template_generation.agent import AgentConfig
from docfit.template_generation.runner import (
    generate_template,
    write_template_generation_outputs,
)
from docfit.template_generation.run_manifest import write_template_run_manifest


def _artifact_refs(out_dir: Path, result: StageResult) -> dict[str, str]:
    refs = {key: str(path) for key, path in result.artifact_paths.items()}
    if "final_docx" in result.artifact_paths:
        refs["final_docx"] = str(result.artifact_paths["final_docx"])
    return refs


def _write_stage_report(out_dir: Path, result: StageResult) -> dict[str, Any]:
    return write_report_bundle(
        out_dir,
        stage=result.stage,
        status=result.status,
        run_status=result.run_status,
        quality_status=result.quality_status,
        findings=result.finding_dicts(),
        artifacts=_artifact_refs(out_dir, result),
        coverage=result.coverage,
        blocked_at=result.blocked_at,
        user_message=result.user_message,
    )


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
    run_context: dict[str, Any] | None = None,
) -> StageResult:
    result = generate_template(
        template_docx,
        out_dir,
        agent_config=agent_config,
    )
    write_template_generation_outputs(out_dir, result)
    context = run_context or {}
    write_template_run_manifest(
        out_dir,
        result=result,
        entrypoint=str(context.get("entrypoint") or "python.run_template_generate_eval"),
        command=str(context.get("command") or "run_template_generate_eval"),
        stage="template_generate",
        agent_config=agent_config,
        source_template_docx=template_docx,
    )
    _write_stage_report(out_dir, result)
    return result


def run_template_generation_full_eval(
    root: Path,
    school_id: str,
    template_docx: Path,
    out_dir: Path,
    *,
    template_version: str = "v1",
    agent_config: AgentConfig | None = None,
    run_context: dict[str, Any] | None = None,
) -> StageResult:
    from docfit.harness.template_generation_standard_judge import (
        judge_template_generation_run,
    )

    eval_runs = out_dir / "eval_runs"
    template_generate_dir = eval_runs / "template_generate"
    template_gap_dir = eval_runs / "template_gap"
    judge_dir = eval_runs / "template_generation_judge"

    generate_result = run_template_generate_eval(
        root,
        template_docx,
        template_generate_dir,
        agent_config=agent_config,
        run_context={
            "entrypoint": "python.run_template_generation_full_eval.generate",
            "command": "template generate (nested in verify)",
        },
    )
    generated_template = _generated_template_from_result(
        generate_result,
        template_generate_dir,
    )
    gap_result = run_template_gap_eval(
        root,
        school_id,
        generated_template,
        template_gap_dir,
    )
    judge_result = judge_template_generation_run(
        root,
        school_id,
        template_generate_dir,
        judge_dir,
        template_version=template_version,
        derive_template_gap=True,
    )

    run_status = merge_statuses(
        [generate_result.run_status or generate_result.status]
    )
    quality_status = merge_statuses(
        [gap_result.quality_status or gap_result.status, judge_result.quality_status or judge_result.status]
    )
    status = merge_statuses([run_status, quality_status])
    full_summary = _build_template_generation_full_summary(
        school_id=school_id,
        template_version=template_version,
        out_dir=out_dir,
        template_generate_dir=template_generate_dir,
        template_gap_dir=template_gap_dir,
        judge_dir=judge_dir,
        generate_result=generate_result,
        gap_result=gap_result,
        judge_result=judge_result,
        status=status,
        run_status=run_status,
        quality_status=quality_status,
    )
    full_summary_json = out_dir / "full_summary.json"
    full_summary_md = out_dir / "full_summary.md"
    write_json(full_summary_json, full_summary)
    write_text(full_summary_md, _render_template_generation_full_summary_markdown(full_summary))

    result = StageResult(
        "template_generation_full",
        status,
        run_status=run_status,
        quality_status=quality_status,
        findings=[
            *[
                finding
                for finding in generate_result.findings
                if finding.type
                != "template_generation_school_quality_not_evaluated"
            ],
            *gap_result.findings,
            *judge_result.findings,
        ],
        artifacts={
            "template_generation_full_summary": full_summary,
            **{
                key: generate_result.artifacts[key]
                for key in (
                    "document_facts",
                    "template_generation_l1_input_contract",
                    "template_agent_render_packet",
                    "ai_observation_bundle",
                )
                if key in generate_result.artifacts
            },
        },
        artifact_paths={
            "full_summary": full_summary_json,
            "full_summary_md": full_summary_md,
            "template_generate_dir": template_generate_dir,
            "template_gap_dir": template_gap_dir,
            "template_generation_judge_dir": judge_dir,
        },
        coverage={
            "template_generate_status": generate_result.status.value,
            "template_gap_status": gap_result.status.value,
            "template_generation_judge_status": judge_result.status.value,
            "first_bad_stage": full_summary.get("first_bad_stage"),
            "route_eval_mismatch_count": full_summary.get("route_eval", {}).get(
                "mismatch_count"
            ),
        },
        blocked_at=full_summary.get("first_bad_stage") if status != Status.PASS else None,
    )
    context = run_context or {}
    write_template_run_manifest(
        out_dir,
        result=result,
        entrypoint=str(
            context.get("entrypoint") or "python.run_template_generation_full_eval"
        ),
        command=str(context.get("command") or "run_template_generation_full_eval"),
        stage="template_generation_verify",
        agent_config=agent_config,
        source_template_docx=template_docx,
        upstream_artifacts={
            "template_generate_run_manifest": str(
                template_generate_dir / "run_manifest.json"
            ),
            "template_gap_dir": str(template_gap_dir),
            "template_generation_judge_dir": str(judge_dir),
        },
        extra={"school_id": school_id, "template_version": template_version},
    )
    _write_stage_report(out_dir, result)
    return result


def _generated_template_from_result(result: StageResult, run_dir: Path) -> Path:
    for key in ("generated_template_docx", "fillable_template_docx"):
        path = result.artifact_paths.get(key)
        if path is not None:
            return path
    return run_dir / "06.1_fillable_template.docx"


def _build_template_generation_full_summary(
    *,
    school_id: str,
    template_version: str,
    out_dir: Path,
    template_generate_dir: Path,
    template_gap_dir: Path,
    judge_dir: Path,
    generate_result: StageResult,
    gap_result: StageResult,
    judge_result: StageResult,
    status: Status,
    run_status: Status,
    quality_status: Status,
) -> dict[str, Any]:
    gap_report = gap_result.artifacts.get("template_gap_report") or _read_json_if_exists(
        template_gap_dir / "artifacts" / "template_gap_report.json"
    )
    judge_report = judge_result.artifacts.get("template_generation_judge_report") or _read_json_if_exists(
        judge_dir / "template_generation_judge_report.json"
    )
    route_eval = judge_result.artifacts.get("template_generation_route_eval_report") or _read_json_if_exists(
        judge_dir / "template_generation_route_eval_report.json"
    )
    verification_report = _read_json_if_exists(
        template_generate_dir / "07_verification_report.json"
    )
    route_stage_metrics = (route_eval or {}).get("stage_metrics", {})
    route_mismatches = (route_eval or {}).get("mismatches", [])
    first_bad_stage = (
        (judge_report or {}).get("first_bad_stage")
        or _first_non_pass_stage(
            {
                "template_generate": generate_result.run_status or generate_result.status,
                "template_gap": gap_result.status,
                "template_generation_judge": judge_result.status,
            }
        )
    )
    quality_report = _build_template_generation_quality_report(
        status=status,
        first_bad_stage=first_bad_stage,
        template_generate_dir=template_generate_dir,
        template_gap_dir=template_gap_dir,
        judge_dir=judge_dir,
        judge_report=judge_report or {},
        route_eval=route_eval or {},
        gap_report=gap_report or {},
        verification_report=verification_report,
    )
    return {
        "artifact_type": "template_generation_full_summary",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "school_id": school_id,
        "template_version": template_version,
        "status": status.value,
        "run_status": run_status.value,
        "quality_status": quality_status.value,
        "run_root": str(out_dir),
        "eval_runs": {
            "template_generate": str(template_generate_dir),
            "template_gap": str(template_gap_dir),
            "template_generation_judge": str(judge_dir),
        },
        "stage_statuses": {
            "template_generate": generate_result.status.value,
            "template_gap": gap_result.status.value,
            "template_generation_judge": judge_result.status.value,
        },
        "stage_run_statuses": {
            "template_generate": (generate_result.run_status or generate_result.status).value,
            "template_gap": (gap_result.run_status or gap_result.status).value,
            "template_generation_judge": (judge_result.run_status or judge_result.status).value,
        },
        "stage_quality_statuses": {
            "template_generate": (generate_result.quality_status or generate_result.status).value,
            "template_gap": (gap_result.quality_status or gap_result.status).value,
            "template_generation_judge": (judge_result.quality_status or judge_result.status).value,
        },
        "final_gap": (gap_report or {}).get("summary", {}),
        "first_bad_stage": first_bad_stage,
        "route_eval": {
            "route_count": (route_eval or {}).get("cross_route_summary", {}).get(
                "route_count"
            ),
            "mismatch_count": len(route_mismatches),
            "mismatch_types": sorted(
                {
                    str(mismatch.get("type"))
                    for mismatch in route_mismatches
                    if mismatch.get("type")
                }
            ),
        },
        "owner_summary": (judge_report or {}).get("owner_summary", {}),
        "top_blockers": quality_report.get("top_blockers", []),
        "quality_report": quality_report,
        "next_verification": _next_template_generation_verification(
            first_bad_stage=first_bad_stage,
            route_mismatches=route_mismatches,
            status=status,
        ),
        "gates": {
            "render_l1": (route_stage_metrics.get("L1") or {}).get("coverage", {}),
            "t3_residual": (route_stage_metrics.get("T3") or {}).get(
                "residual_gate", {}
            ),
            "t4_hint_consumption": (route_stage_metrics.get("T4") or {}).get(
                "hint_consumption", {}
            ),
            "ai_primary": (route_eval or {}).get("ai_primary_gate_decision", {}),
        },
        "artifacts": {
            "template_gap_report": str(
                template_gap_dir / "artifacts" / "template_gap_report.json"
            ),
            "template_generation_judge_report": str(
                judge_dir / "template_generation_judge_report.json"
            ),
            "template_generation_route_eval_report": str(
                judge_dir / "template_generation_route_eval_report.json"
            ),
        },
    }


def _build_template_generation_quality_report(
    *,
    status: Status,
    first_bad_stage: str | None,
    template_generate_dir: Path,
    template_gap_dir: Path,
    judge_dir: Path,
    judge_report: dict[str, Any],
    route_eval: dict[str, Any],
    gap_report: dict[str, Any],
    verification_report: dict[str, Any],
) -> dict[str, Any]:
    route_mismatches = _list_of_dicts(route_eval.get("mismatches"))
    root_causes = _list_of_dicts(judge_report.get("root_causes"))
    owner_assignments = _list_of_dicts(judge_report.get("owner_assignments"))
    fix_plan = _list_of_dicts(judge_report.get("fix_plan"))
    stage_checks = {
        str(check.get("stage_id") or _stage_id_from_key(check.get("stage_key"))): check
        for check in _list_of_dicts(judge_report.get("stage_checks"))
    }
    verification_stages = {
        str(stage.get("stage")): stage
        for stage in _list_of_dicts(verification_report.get("stages"))
    }
    stage_cards = [
        _template_generation_stage_card(
            stage_id=stage_id,
            stage_key=stage_key,
            artifact_paths=artifact_paths,
            stage_check=stage_checks.get(stage_id),
            route_metrics=(route_eval.get("stage_metrics") or {}).get(stage_id, {}),
            route_mismatches=route_mismatches,
            root_causes=root_causes,
            owner_assignments=owner_assignments,
            fix_plan=fix_plan,
            verification_stage=verification_stages.get(stage_id),
            gap_report=gap_report if stage_id == "POST_T6" else {},
            evidence_refs=_template_generation_quality_evidence_refs(
                stage_id,
                template_generate_dir=template_generate_dir,
                template_gap_dir=template_gap_dir,
                judge_dir=judge_dir,
                artifact_paths=artifact_paths,
            ),
        )
        for stage_id, stage_key, artifact_paths in [
            ("T1", "t1_document_facts", ["01_document_facts.json"]),
            ("L1", "l1_input_contract", ["01.5_l1_input_contract.json"]),
            ("T2", "t2_unit_pagination", ["02_unit_map.yaml"]),
            ("T3", "t3_element_policy", ["03_element_spec.yaml"]),
            ("T4", "t4_global_layout", ["04_global_spec.yaml"]),
            ("T5", "t5_template_spec", ["05_template_spec.yaml"]),
            ("T6", "t6_fillable_template", ["06.1_fillable_template.docx", "06.2_build_manifest.json"]),
            ("T7", "t7_verification_report", ["07_verification_report.json"]),
            ("POST_T6", "post_t6_template_gap", ["artifacts/template_gap_report.json"]),
        ]
    ]
    top_blockers = _compact_items(judge_report.get("top_blockers"), limit=10)
    if not top_blockers:
        top_blockers = _top_quality_blockers_from_stage_cards(stage_cards)
    return {
        "artifact_type": "template_generation_full_quality_report",
        "artifact_version": "1.0",
        "overall_status": status.value,
        "first_bad_stage": first_bad_stage,
        "stage_cards": stage_cards,
        "top_blockers": top_blockers,
        "owner_summary": judge_report.get("owner_summary", {}),
        "next_optimization_targets": _next_optimization_targets(stage_cards),
        "evidence_refs": {
            "template_generation_judge_report": str(
                judge_dir / "template_generation_judge_report.json"
            ),
            "template_generation_route_eval_report": str(
                judge_dir / "template_generation_route_eval_report.json"
            ),
            "template_gap_report": str(
                template_gap_dir / "artifacts" / "template_gap_report.json"
            ),
        },
    }


def _template_generation_stage_card(
    *,
    stage_id: str,
    stage_key: str,
    artifact_paths: list[str],
    stage_check: dict[str, Any] | None,
    route_metrics: dict[str, Any],
    route_mismatches: list[dict[str, Any]],
    root_causes: list[dict[str, Any]],
    owner_assignments: list[dict[str, Any]],
    fix_plan: list[dict[str, Any]],
    verification_stage: dict[str, Any] | None,
    gap_report: dict[str, Any],
    evidence_refs: dict[str, str],
) -> dict[str, Any]:
    stage_mismatches = [
        mismatch for mismatch in route_mismatches if mismatch.get("stage_id") == stage_id
    ]
    stage_roots = _items_for_stage(root_causes, stage_id)
    stage_owners = _items_for_stage(owner_assignments, stage_id)
    stage_fixes = _items_for_stage(fix_plan, stage_id)
    stage_status = _stage_card_status(
        stage_id=stage_id,
        stage_check=stage_check,
        route_metrics=route_metrics,
        route_mismatches=stage_mismatches,
        verification_stage=verification_stage,
        gap_report=gap_report,
    )
    return {
        "stage_id": stage_id,
        "stage_key": stage_key,
        "status": stage_status,
        "artifact_status": (
            (stage_check or {}).get("status")
            or (verification_stage or {}).get("status")
            or _post_t6_gap_status(gap_report)
        ),
        "audit_status": (stage_check or {}).get("audit_status"),
        "route_status": _route_evaluation_status(route_metrics, stage_mismatches),
        "artifact_paths": artifact_paths,
        "standard_path": (stage_check or {}).get("standard_path"),
        "quality_checks": _quality_checks_for_stage(
            stage_check=stage_check,
            route_metrics=route_metrics,
            route_mismatches=stage_mismatches,
            verification_stage=verification_stage,
            gap_report=gap_report,
        ),
        "mismatches": _compact_items(stage_mismatches, limit=10),
        "root_causes": _compact_items(stage_roots, limit=10),
        "owner_assignments": _compact_items(stage_owners, limit=10),
        "fix_plan": _compact_items(stage_fixes, limit=10),
        "route_availability": route_metrics.get("route_availability", {}),
        "route_reasons": route_metrics.get("route_reasons", {}),
        "evidence_refs": evidence_refs,
    }


def _stage_card_status(
    *,
    stage_id: str,
    stage_check: dict[str, Any] | None,
    route_metrics: dict[str, Any],
    route_mismatches: list[dict[str, Any]],
    verification_stage: dict[str, Any] | None,
    gap_report: dict[str, Any],
) -> str:
    statuses: list[str] = []
    if stage_check and stage_check.get("status"):
        statuses.append(str(stage_check["status"]))
    if verification_stage and verification_stage.get("status"):
        statuses.append(str(verification_stage["status"]))
    if stage_id == "POST_T6":
        statuses.append(_post_t6_gap_status(gap_report))
    if route_metrics:
        statuses.append(_route_evaluation_status(route_metrics, route_mismatches))
    return _merge_status_values(statuses)


def _merge_status_values(statuses: list[str]) -> str:
    normalized = [status for status in statuses if status]
    if not normalized:
        return "UNKNOWN"
    if "FAIL" in normalized:
        return "FAIL"
    if "UNKNOWN" in normalized:
        return "UNKNOWN"
    return "PASS"


def _post_t6_gap_status(gap_report: dict[str, Any]) -> str:
    summary = gap_report.get("summary") if isinstance(gap_report.get("summary"), dict) else {}
    status = summary.get("blocking_status") or summary.get("known_status")
    return str(status or "UNKNOWN")


def _quality_checks_for_stage(
    *,
    stage_check: dict[str, Any] | None,
    route_metrics: dict[str, Any],
    route_mismatches: list[dict[str, Any]],
    verification_stage: dict[str, Any] | None,
    gap_report: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if route_metrics:
        checks.append(
            {
                "kind": "route_evaluation",
                "status": _route_evaluation_status(route_metrics, route_mismatches),
                "route_availability": route_metrics.get("route_availability", {}),
                "route_reasons": route_metrics.get("route_reasons", {}),
                "ai_availability": route_metrics.get("ai_availability"),
                "changed_from_code": route_metrics.get("changed_from_code"),
                "coverage": _compact_value(route_metrics.get("coverage", {})),
                "mismatch_count": len(route_mismatches),
            }
        )
    if stage_check:
        checks.append(
            {
                "kind": "stage_standard_audit",
                "status": stage_check.get("status"),
                "audit_status": stage_check.get("audit_status"),
                "verifier_state": stage_check.get("verifier_state"),
                "gate_enabled": stage_check.get("gate_enabled"),
                "finding_count": len(_list_of_dicts(stage_check.get("findings"))),
            }
        )
    if verification_stage:
        checks.append(
            {
                "kind": "runtime_verification",
                "status": verification_stage.get("status"),
                "artifact_type": verification_stage.get("artifact_type"),
                "output_hash": verification_stage.get("output_hash"),
            }
        )
    if gap_report:
        summary = gap_report.get("summary") if isinstance(gap_report.get("summary"), dict) else {}
        checks.append(
            {
                "kind": "final_template_gap",
                "status": _post_t6_gap_status(gap_report),
                "display_status": summary.get("display_status"),
                "failed_count": summary.get("failed_count"),
                "unknown_count": summary.get("unknown_count"),
                "passed_count": summary.get("passed_count"),
            }
        )
    return checks


def _route_evaluation_status(
    route_metrics: dict[str, Any],
    route_mismatches: list[dict[str, Any]],
) -> str:
    if route_mismatches:
        return Status.FAIL.value
    availability = route_metrics.get("route_availability")
    if not isinstance(availability, dict) or not availability:
        return Status.UNKNOWN.value
    normalized = [str(value or "") for value in availability.values()]
    allowed = {"AVAILABLE", "OUT_OF_SCOPE"}
    if (
        not normalized
        or "AVAILABLE" not in normalized
        or any(value not in allowed for value in normalized)
    ):
        return Status.UNKNOWN.value
    return Status.PASS.value


def _template_generation_quality_evidence_refs(
    stage_id: str,
    *,
    template_generate_dir: Path,
    template_gap_dir: Path,
    judge_dir: Path,
    artifact_paths: list[str],
) -> dict[str, Any]:
    artifact_root = template_gap_dir if stage_id == "POST_T6" else template_generate_dir
    refs = {
        "artifacts": str(artifact_root),
        "stage_artifacts": [
            str(artifact_root / path) for path in artifact_paths
        ],
        "route_eval_report": str(
            judge_dir / "template_generation_route_eval_report.json"
        ),
    }
    if stage_id in {"T1", "T2", "T3", "T4", "T5"}:
        refs["stage_standard_diff_report"] = str(
            judge_dir / f"{_stage_output_prefix(stage_id)}_standard_diff_report.json"
        )
        refs["stage_standard_quality_report"] = str(
            judge_dir / f"{_stage_output_prefix(stage_id)}_standard_quality_report.json"
        )
    if stage_id == "POST_T6":
        refs["template_gap_report"] = str(
            template_gap_dir / "artifacts" / "template_gap_report.json"
        )
    return refs


def _stage_output_prefix(stage_id: str) -> str:
    return {
        "T1": "01_document_facts",
        "T2": "02_unit_map",
        "T3": "03_element_spec",
        "T4": "04_global_spec",
        "T5": "05_template_spec",
    }.get(stage_id, stage_id)


def _stage_id_from_key(stage_key: Any) -> str:
    return {
        "t1_document_facts": "T1",
        "t2_unit_pagination": "T2",
        "t3_element_policy": "T3",
        "t4_global_layout": "T4",
        "t5_template_spec": "T5",
        "l1_input_contract": "L1",
        "t6_fillable_template": "T6",
        "t7_verification_report": "T7",
        "post_t6_template_gap": "POST_T6",
    }.get(str(stage_key), str(stage_key))


def _items_for_stage(items: list[dict[str, Any]], stage_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if item.get("stage_id") == stage_id
        or _stage_id_from_key(item.get("stage_key")) == stage_id
        or str(item.get("id", "")).startswith(f"{stage_id}-")
    ]


def _top_quality_blockers_from_stage_cards(stage_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for card in stage_cards:
        if card.get("status") == "PASS":
            continue
        first_mismatch = (card.get("mismatches") or [{}])[0]
        blockers.append(
            {
                "stage_id": card.get("stage_id"),
                "stage_key": card.get("stage_key"),
                "status": card.get("status"),
                "reason": (
                    first_mismatch.get("type")
                    or first_mismatch.get("reason")
                    or "stage quality check is not PASS"
                ),
            }
        )
    return blockers[:10]


def _next_optimization_targets(stage_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for card in stage_cards:
        if card.get("status") == "PASS":
            continue
        fix_plan = card.get("fix_plan") or []
        first_fix = fix_plan[0] if fix_plan else {}
        targets.append(
            {
                "stage_id": card.get("stage_id"),
                "stage_key": card.get("stage_key"),
                "status": card.get("status"),
                "owner": _owner_for_card(card),
                "action": (
                    first_fix.get("action")
                    or f"resolve {card.get('stage_id')} quality report blockers"
                ),
                "evidence_refs": card.get("evidence_refs", {}),
            }
        )
    return targets[:10]


def _owner_for_card(card: dict[str, Any]) -> str:
    root_cause = (card.get("root_causes") or [{}])[0]
    owner_assignment = (card.get("owner_assignments") or [{}])[0]
    return str(
        root_cause.get("owner")
        or owner_assignment.get("primary")
        or "template-generation"
    )


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _compact_items(value: Any, *, limit: int) -> list[dict[str, Any]]:
    return [_compact_dict(item) for item in _list_of_dicts(value)[:limit]]


def _compact_dict(item: dict[str, Any]) -> dict[str, Any]:
    keep_keys = [
        "id",
        "stage_id",
        "stage_key",
        "status",
        "type",
        "finding_type",
        "category",
        "owner",
        "primary",
        "secondary",
        "reason",
        "expected",
        "observed",
        "actual",
        "next_action",
        "action",
        "acceptance",
        "evidence_refs",
        "report_ref",
        "mismatch_id",
        "root_cause_id",
        "route_ids",
    ]
    compact: dict[str, Any] = {}
    for key in keep_keys:
        if key in item:
            compact[key] = _compact_value(item[key])
    return compact


def _compact_value(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= 300 else value[:297] + "..."
    if isinstance(value, list):
        return [_compact_value(item) for item in value[:10]]
    if isinstance(value, dict):
        return {
            str(key): _compact_value(nested)
            for key, nested in list(value.items())[:10]
        }
    return value


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = read_json(path)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _first_non_pass_stage(stage_statuses: dict[str, Status]) -> str | None:
    for stage, status in stage_statuses.items():
        if status != Status.PASS:
            return stage
    return None


def _next_template_generation_verification(
    *,
    first_bad_stage: str | None,
    route_mismatches: list[dict[str, Any]],
    status: Status,
) -> list[dict[str, Any]]:
    if status == Status.PASS and not route_mismatches:
        return [
            {
                "owner": "template-generation",
                "action": "rerun three-school template-generation-full regression before closing the issue",
            }
        ]
    actions = []
    if first_bad_stage:
        actions.append(
            {
                "owner": "template-generation",
                "action": f"fix first failing stage: {first_bad_stage}",
            }
        )
    for mismatch in route_mismatches[:10]:
        actions.append(
            {
                "owner": "template-generation",
                "stage_id": mismatch.get("stage_id"),
                "type": mismatch.get("type"),
                "action": "resolve route-eval mismatch and rerun template-generation-full",
            }
        )
    return actions


def _render_template_generation_full_summary_markdown(summary: dict[str, Any]) -> str:
    quality_report = summary.get("quality_report") or {}
    lines = [
        "# Template Generation Full Summary",
        "",
        f"- School: {summary.get('school_id')}",
        f"- Status: {summary.get('status')}",
        f"- First bad stage: {summary.get('first_bad_stage') or 'none'}",
        f"- Quality report: {quality_report.get('overall_status') or summary.get('status')}",
        "",
        "## Stage Statuses",
    ]
    for stage, status in (summary.get("stage_statuses") or {}).items():
        lines.append(f"- {stage}: {status}")
    lines.extend(["", "## Quality Stage Cards"])
    for card in quality_report.get("stage_cards") or []:
        lines.append(
            "- "
            f"{card.get('stage_id')} {card.get('stage_key')}: "
            f"status={card.get('status')}, route={card.get('route_status')}"
        )
        mismatches = card.get("mismatches") or []
        if mismatches:
            first = mismatches[0]
            lines.append(
                f"  - first issue: {first.get('type') or first.get('reason') or first.get('id')}"
            )
        fixes = card.get("fix_plan") or []
        if fixes:
            lines.append(f"  - next: {fixes[0].get('action')}")
    top_blockers = quality_report.get("top_blockers") or []
    if top_blockers:
        lines.extend(["", "## Top Blockers"])
        for blocker in top_blockers[:10]:
            lines.append(
                "- "
                f"{blocker.get('stage_id') or blocker.get('stage_key')}: "
                f"{blocker.get('finding_type') or blocker.get('type') or blocker.get('reason')}"
                f" owner={blocker.get('owner') or blocker.get('primary') or 'unknown'}"
            )
    owner_summary = quality_report.get("owner_summary") or {}
    if owner_summary:
        lines.extend(["", "## Owner Summary"])
        for owner, count in owner_summary.items():
            lines.append(f"- {owner}: {count}")
    next_targets = quality_report.get("next_optimization_targets") or []
    if next_targets:
        lines.extend(["", "## Next Optimization Targets"])
        for target in next_targets[:10]:
            lines.append(
                "- "
                f"{target.get('stage_id')}: "
                f"{target.get('action')} "
                f"(owner={target.get('owner')})"
            )
    route_eval = summary.get("route_eval") or {}
    lines.extend(
        [
            "",
            "## Route Eval",
            f"- Routes: {route_eval.get('route_count')}",
            f"- Mismatches: {route_eval.get('mismatch_count')}",
        ]
    )
    for mismatch_type in route_eval.get("mismatch_types") or []:
        lines.append(f"- {mismatch_type}")
    lines.extend(["", "## Next Verification"])
    for item in summary.get("next_verification") or []:
        lines.append(
            "- "
            f"{item.get('stage_id') or item.get('owner')}: "
            f"{item.get('action')}"
        )
    lines.append("")
    return "\n".join(lines)
