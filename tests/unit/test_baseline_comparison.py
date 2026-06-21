from __future__ import annotations

from docfit.core.status import Status
from docfit.harness.baselines import compare_baseline_to_artifact


def _baseline() -> dict:
    return {
        "baseline_type": "template_unit_contract",
        "review_metadata": {
            "reviewed_by": "product-owner",
            "review_source": "test_inputs/template_generation/review.txt",
            "source_docx_sha256": "sha256:abc",
            "change_reason": "test baseline",
            "auto_update_allowed": False,
        },
        "expected": {"units": ["cover", "abstract", "body"]},
        "dimensions": [
            {
                "dimension_id": "template.unit_order",
                "required": True,
                "comparator_mode": "ordered_sequence",
                "expected_path": "units",
                "actual_path": "units",
            }
        ],
    }


def test_compare_baseline_to_artifact_passes_when_dimensions_match() -> None:
    result = compare_baseline_to_artifact(
        _baseline(),
        {"units": ["cover", "abstract", "body"]},
        stage="template",
    )

    assert result.status == Status.PASS
    assert result.findings == []


def test_compare_baseline_to_artifact_fails_on_dimension_mismatch() -> None:
    result = compare_baseline_to_artifact(
        _baseline(),
        {"units": ["cover", "body", "abstract"]},
        stage="template",
    )

    assert result.status == Status.FAIL
    assert result.findings[0].type == "ordered_sequence_mismatch"


def test_compare_baseline_to_artifact_unknown_when_expected_missing() -> None:
    baseline = _baseline()
    baseline.pop("expected")

    result = compare_baseline_to_artifact(
        baseline,
        {"units": ["cover", "abstract", "body"]},
        stage="template",
    )

    assert result.status == Status.UNKNOWN
    assert result.findings[0].type == "missing_expected_artifact"
