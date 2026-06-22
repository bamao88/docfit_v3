from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.harness.baselines import (
    BaselineComparisonResult,
    compare_baseline_to_artifact,
    load_baseline_file,
)
from docfit.harness.profiles import REAL_CORE_PROFILE, REAL_CORE_STUDENTS
from docfit.harness.standards import StandardBundle


def is_real_core_bundle(bundle: StandardBundle | None) -> bool:
    if bundle is None:
        return False
    return (
        bundle.signed_standard.get("coverage_requirements", {}).get("profile")
        == REAL_CORE_PROFILE.profile_id
    )


def root_from_bundle(bundle: StandardBundle) -> Path:
    return bundle.school_dir.parents[3]


def student_id_for_docx(root: Path, student_docx: Path) -> str | None:
    resolved = student_docx.resolve()
    for student in REAL_CORE_STUDENTS:
        expected = (root / student["student_docx"]).resolve()
        if expected == resolved:
            return str(student["student_id"])
    return None


def case_id_for(school_id: str, student_id: str | None) -> str | None:
    if not student_id:
        return None
    return f"real_core_v0_{school_id}_{student_id}"


def load_template_unit_baseline(
    bundle: StandardBundle,
    *,
    stage: str,
    start_index: int = 1,
) -> tuple[dict[str, Any] | None, list]:
    rel_path = bundle.signed_standard.get("evidence_baselines", {}).get(
        "template_generation_final",
        "template_generation_final.yaml",
    )
    return load_baseline_file(
        bundle.school_dir / rel_path,
        stage=stage,
        start_index=start_index,
    )


def load_student_content_baseline(
    root: Path,
    student_id: str,
    *,
    stage: str,
    start_index: int = 1,
) -> tuple[dict[str, Any] | None, list]:
    return load_baseline_file(
        root
        / REAL_CORE_PROFILE.expected_dir
        / "student_content_trees"
        / f"{student_id}.yaml",
        stage=stage,
        start_index=start_index,
    )


def load_render_plan_baseline(
    root: Path,
    case_id: str,
    *,
    stage: str,
    start_index: int = 1,
) -> tuple[dict[str, Any] | None, list]:
    return load_baseline_file(
        root / REAL_CORE_PROFILE.expected_placement_plan / f"{case_id}.yaml",
        stage=stage,
        start_index=start_index,
    )


def load_render_feature_snapshot_baseline(
    root: Path,
    case_id: str,
    *,
    stage: str,
    start_index: int = 1,
) -> tuple[dict[str, Any] | None, list]:
    return load_baseline_file(
        root / REAL_CORE_PROFILE.expected_feature_snapshot / f"{case_id}.json",
        stage=stage,
        start_index=start_index,
    )


def accepted_expected_artifact(baseline: dict[str, Any]) -> dict[str, Any]:
    expected = baseline.get("expected")
    return expected if isinstance(expected, dict) else {}


def compare_to_accepted_expected(
    baseline: dict[str, Any],
    *,
    stage: str,
    baseline_ref: str | None = None,
    start_index: int = 1,
) -> BaselineComparisonResult:
    return compare_baseline_to_artifact(
        baseline,
        accepted_expected_artifact(baseline),
        stage=stage,
        start_index=start_index,
        baseline_ref=baseline_ref,
    )
