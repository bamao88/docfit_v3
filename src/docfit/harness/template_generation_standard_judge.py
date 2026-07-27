from __future__ import annotations

from pathlib import Path

from docfit.core.io import read_json
from docfit.core.models import StageResult
from docfit.core.status import Status, merge_statuses
from docfit.harness.reports import write_report_bundle
from docfit.harness.standards import load_standard_bundle
from docfit.template_gap.gap import evaluate_generated_template_gap
from docfit.harness.template_generation_judge_reports import (
    aggregate_template_generation_judgement,
    write_template_generation_judge_outputs,
    write_template_generation_standard_quality_outputs,
)
from docfit.harness.template_generation_run_bundle import (
    bind_template_generation_run_bundle,
)
from docfit.harness.template_generation_stage_verifiers import (
    run_template_generation_stage_verifiers,
)
from docfit.harness.template_generation_standard_quality import (
    evaluate_template_generation_standard_quality,
    evaluate_template_generation_standard_quality_for_profile,
    load_template_generation_standard_set,
)


def evaluate_template_generation_standard_quality_command(
    root: Path,
    out_dir: Path,
    *,
    school_id: str | None = None,
    profile_id: str | None = None,
    template_version: str = "v1",
) -> StageResult:
    if bool(school_id) == bool(profile_id):
        raise ValueError("Exactly one of school_id or profile_id is required")
    if school_id is not None:
        standard_set = load_template_generation_standard_set(
            root,
            school_id,
            template_version,
        )
        report = evaluate_template_generation_standard_quality(standard_set)
    else:
        report = evaluate_template_generation_standard_quality_for_profile(
            root,
            str(profile_id),
            template_version,
        )
    return write_template_generation_standard_quality_outputs(out_dir, report)


def judge_template_generation_run(
    root: Path,
    school_id: str,
    run_dir: Path,
    out_dir: Path,
    template_version: str = "v1",
    run_id: str | None = None,
    derive_template_gap: bool = True,
) -> StageResult:
    standard_set = load_template_generation_standard_set(
        root,
        school_id,
        template_version,
    )
    standard_quality = evaluate_template_generation_standard_quality(standard_set)
    if derive_template_gap:
        _derive_template_gap_if_missing(
            root,
            school_id,
            run_dir,
            template_version=template_version,
        )
    run_bundle = bind_template_generation_run_bundle(
        run_dir,
        standard_set=standard_set,
        source_run_id=run_id,
    )
    stage_checks = run_template_generation_stage_verifiers(
        standard_set=standard_set,
        standard_quality=standard_quality,
        run_bundle=run_bundle,
    )
    report = aggregate_template_generation_judgement(
        standard_set=standard_set,
        standard_quality=standard_quality,
        run_bundle=run_bundle,
        stage_checks=stage_checks,
    )
    return write_template_generation_judge_outputs(out_dir, report)


def _derive_template_gap_if_missing(
    root: Path,
    school_id: str,
    run_dir: Path,
    *,
    template_version: str,
) -> None:
    if _template_gap_report_exists(run_dir):
        return
    generated_template = _generated_template_for_run(run_dir)
    if generated_template is None:
        return
    bundle, standard_findings = load_standard_bundle(
        root,
        school_id,
        template_version,
        finding_stage="template",
    )
    if bundle is None:
        return
    out_dir = _derived_template_gap_dir(run_dir)
    result = evaluate_generated_template_gap(bundle, generated_template, out_dir)
    if standard_findings:
        result.findings = standard_findings + result.findings
        result.status = merge_statuses(
            [result.status] + [finding.status for finding in standard_findings]
        )
    write_report_bundle(
        out_dir,
        stage=result.stage,
        status=result.status,
        run_status=result.run_status,
        quality_status=result.quality_status,
        findings=result.finding_dicts(),
        artifacts={key: str(path) for key, path in result.artifact_paths.items()},
        coverage=result.coverage,
        blocked_at=result.blocked_at,
        user_message=result.user_message,
    )


def _template_gap_report_exists(run_dir: Path) -> bool:
    return any(
        path.exists()
        for path in (
            run_dir / "template_gap_report.json",
            run_dir / "artifacts" / "template_gap_report.json",
            run_dir.parent / "template_gap" / "template_gap_report.json",
            run_dir.parent / "template_gap" / "artifacts" / "template_gap_report.json",
            run_dir.parent.parent / "template_gap" / "artifacts" / "template_gap_report.json",
        )
    )


def _generated_template_for_run(run_dir: Path) -> Path | None:
    candidates = [
        run_dir / "06.1_fillable_template.docx",
    ]
    manifest_path = run_dir / "06.2_build_manifest.json"
    if manifest_path.exists():
        try:
            manifest = read_json(manifest_path)
            output_docx = (
                manifest.get("output_docx")
                or manifest.get("generated_template_docx")
                or manifest.get("fillable_template_docx")
            )
            if output_docx:
                candidates.append(Path(str(output_docx)))
        except Exception:
            pass
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _derived_template_gap_dir(run_dir: Path) -> Path:
    if run_dir.parent.name == "eval_runs":
        return run_dir.parent / "template_gap"
    return run_dir.parent / "template_gap"
