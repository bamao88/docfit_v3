from __future__ import annotations

from pathlib import Path

from docfit.core.models import StageResult
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
) -> StageResult:
    standard_set = load_template_generation_standard_set(
        root,
        school_id,
        template_version,
    )
    standard_quality = evaluate_template_generation_standard_quality(standard_set)
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
