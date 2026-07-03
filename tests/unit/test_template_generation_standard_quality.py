from __future__ import annotations

from pathlib import Path

from docfit.harness.template_generation_standard_quality import (
    TEMPLATE_GENERATION_STAGE_KEYS,
    evaluate_template_generation_standard_quality,
    evaluate_template_generation_standard_quality_for_profile,
    load_template_generation_standard_set,
)


ROOT = Path(__file__).resolve().parents[2]


def test_standard_quality_loads_three_school_stage_standards() -> None:
    for school_id in ["hunannongye", "nannong-undergraduate", "pku-graduate"]:
        standard_set = load_template_generation_standard_set(ROOT, school_id)
        report = evaluate_template_generation_standard_quality(standard_set)

        assert report.status.value == "UNKNOWN"
        assert set(standard_set.stages) == set(TEMPLATE_GENERATION_STAGE_KEYS)
        assert [finding.type for finding in report.findings] == [
            "t3_standard_element_expectations_missing"
        ]
        assert report.stage_statuses["t3_element_policy"] == "UNKNOWN"
        assert all(
            status == "PASS"
            for stage, status in report.stage_statuses.items()
            if stage != "t3_element_policy"
        )
        assert standard_set.source_template_docx_sha256
        assert all(
            str(stage.path).endswith(f"template_generation/{stage.stage_key}.standard.yaml")
            for stage in standard_set.stages.values()
        )


def test_standard_quality_profile_aggregates_real_core_targets() -> None:
    report = evaluate_template_generation_standard_quality_for_profile(
        ROOT,
        "real-core-v0",
    )

    target_ids = {target["school_id"] for target in report.target_reports}
    assert {"hunannongye", "nannong-undergraduate", "pku-graduate"} <= target_ids
    assert report.status.value == "UNKNOWN"
    assert [
        finding.type for finding in report.findings
    ] == [
        "t3_standard_element_expectations_missing",
        "t3_standard_element_expectations_missing",
        "t3_standard_element_expectations_missing",
    ]
