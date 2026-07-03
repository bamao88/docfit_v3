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

        assert report.status.value == "PASS"
        assert set(standard_set.stages) == set(TEMPLATE_GENERATION_STAGE_KEYS)
        assert report.findings == []
        assert all(status == "PASS" for status in report.stage_statuses.values())
        final_element_count = sum(
            len(unit.get("elements", []))
            for unit in standard_set.final_template["expected"]["units"]
        )
        t3_expected = standard_set.stages["t3_element_policy"].expected
        assert len(t3_expected["element_expectations"]) == final_element_count
        assert len(t3_expected["run_span_ledger"]) >= final_element_count
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
    assert report.status.value == "PASS"
    assert report.findings == []
