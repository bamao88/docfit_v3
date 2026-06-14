from __future__ import annotations

from docfit.core.status import Status
from docfit.harness.comparators import compare_dimensions


def test_ordered_sequence_mismatch_fails() -> None:
    findings = compare_dimensions(
        {"units": ["cover", "abstract", "body"]},
        {"units": ["cover", "body", "abstract"]},
        [
            {
                "dimension_id": "template.unit_order",
                "comparator_mode": "ordered_sequence",
                "expected_path": "units",
                "actual_path": "units",
            }
        ],
        stage="template",
    )

    assert findings[0].status == Status.FAIL
    assert findings[0].type == "ordered_sequence_mismatch"


def test_subset_comparator_proves_rendered_hash_coverage() -> None:
    findings = compare_dimensions(
        {"hashes": ["sha256:a", "sha256:b"]},
        {"hashes": ["sha256:a", "sha256:b", "sha256:c"]},
        [
            {
                "dimension_id": "render.content_hashes",
                "comparator_mode": "subset",
                "expected_path": "hashes",
                "actual_path": "hashes",
            }
        ],
        stage="render",
    )

    assert findings == []


def test_missing_actual_dimension_is_unknown() -> None:
    findings = compare_dimensions(
        {"object": "textbox"},
        {},
        [
            {
                "dimension_id": "content.visible_object",
                "comparator_mode": "exact",
                "expected_path": "object",
                "actual_path": "object",
            }
        ],
        stage="content",
    )

    assert findings[0].status == Status.UNKNOWN
    assert findings[0].type == "dimension_unreadable"


def test_numeric_tolerance_distinguishes_fail_and_pass() -> None:
    dimensions = [
        {
            "dimension_id": "template.margin_top",
            "comparator_mode": "numeric_tolerance",
            "expected_path": "margin",
            "actual_path": "margin",
            "tolerance": 0.1,
        }
    ]

    assert compare_dimensions({"margin": 2.0}, {"margin": 2.05}, dimensions, stage="template") == []
    findings = compare_dimensions({"margin": 2.0}, {"margin": 2.2}, dimensions, stage="template")

    assert findings[0].status == Status.FAIL
    assert findings[0].type == "numeric_tolerance_mismatch"


def test_numeric_percent_tolerance_uses_expected_value() -> None:
    dimensions = [
        {
            "dimension_id": "template.margin_top",
            "comparator_mode": "numeric_tolerance",
            "expected_path": "margin",
            "actual_path": "margin",
            "tolerance_percent": 5,
        }
    ]

    assert (
        compare_dimensions({"margin": 20}, {"margin": 20.9}, dimensions, stage="template")
        == []
    )
    findings = compare_dimensions(
        {"margin": 20},
        {"margin": 21.2},
        dimensions,
        stage="template",
    )

    assert findings[0].status == Status.FAIL


def test_oracle_required_unknown_remains_blocking() -> None:
    findings = compare_dimensions(
        {"same_page": True},
        {"same_page": {"status": "UNKNOWN"}},
        [
            {
                "dimension_id": "render.figure_caption_same_page",
                "comparator_mode": "oracle_required",
                "expected_path": "same_page",
                "actual_path": "same_page",
            }
        ],
        stage="render",
    )

    assert findings[0].status == Status.UNKNOWN
    assert findings[0].type == "oracle_required_unknown"
