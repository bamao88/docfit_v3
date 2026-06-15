from __future__ import annotations

import importlib.util
from pathlib import Path

from docfit.core.status import Status
from docfit.harness.baselines import validate_baseline_document
from docfit.harness.coverage import evaluate_profile_coverage
from docfit.harness.profiles import get_eval_cases_for_profile, get_eval_profile


ROOT = Path.cwd()


def test_real_core_profile_declares_fixed_case_matrix() -> None:
    profile = get_eval_profile("real-core-v0")
    cases = get_eval_cases_for_profile("real-core-v0")

    assert profile is not None
    assert len([case for case in cases if case.stage == "template"]) == 3
    assert len([case for case in cases if case.stage == "content"]) == 3
    assert len([case for case in cases if case.stage == "e2e"]) == 9
    assert {
        case.school_id for case in cases if case.stage in {"template", "e2e"}
    } == {"hunannongye", "nannong-undergraduate", "pku-graduate"}
    assert {
        case.student_id for case in cases if case.stage in {"content", "e2e"}
    } == {"real-student-001", "real-student-002", "real-student-003"}


def test_real_core_coverage_is_unknown_until_word_image_evidence_exists() -> None:
    report, findings = evaluate_profile_coverage(ROOT, "real-core-v0")

    assert report["status"] == Status.UNKNOWN.value
    assert report["case_counts"] == {"template": 3, "content": 3, "e2e": 9}
    assert report["source_files"]["missing"] == []
    assert "missing_profile_case_registry" not in report["missing"]
    assert report["baseline_status"] == "source_facts_signed_word_evidence_pending"
    assert report["missing"] == ["missing_word_image_evidence"]
    assert not any(finding.type == "missing_signed_standard" for finding in findings)
    assert not any(finding.type == "missing_profile_baseline" for finding in findings)
    assert sum(finding.type == "missing_word_image_evidence" for finding in findings) == 9


def test_real_core_coverage_requires_checked_in_case_registry(tmp_path) -> None:
    report, findings = evaluate_profile_coverage(tmp_path, "real-core-v0")

    assert report["status"] == Status.UNKNOWN.value
    assert any(finding.type == "missing_profile_case_registry" for finding in findings)


def test_required_dimension_without_comparator_policy_is_unknown() -> None:
    baseline = {
        "baseline_type": "student_content_tree",
        "review_metadata": {
            "reviewed_by": "product-owner",
            "review_source": "inputs/review.md",
            "source_docx_sha256": "sha256:abc",
            "change_reason": "initial baseline",
            "auto_update_allowed": False,
        },
        "dimensions": [{"dimension_id": "body.flow", "required": True}],
    }

    findings = validate_baseline_document(baseline, stage="standards")

    assert any(finding.status == Status.UNKNOWN for finding in findings)
    assert any(finding.type == "missing_comparator_mode" for finding in findings)


def test_numeric_dimension_requires_explicit_tolerance() -> None:
    baseline = {
        "baseline_type": "template_unit_contract",
        "review_metadata": {
            "reviewed_by": "product-owner",
            "review_source": "inputs/review.txt",
            "source_docx_sha256": "sha256:abc",
            "change_reason": "initial baseline",
            "auto_update_allowed": False,
        },
        "dimensions": [
            {
                "dimension_id": "body.font_size",
                "required": True,
                "comparator_mode": "numeric_tolerance",
            }
        ],
    }

    findings = validate_baseline_document(baseline, stage="standards")

    assert any(finding.type == "missing_numeric_tolerance" for finding in findings)


def test_baseline_cannot_allow_auto_update() -> None:
    baseline = {
        "baseline_type": "render_feature_snapshot",
        "review_metadata": {
            "reviewed_by": "product-owner",
            "review_source": "inputs/review.txt",
            "source_docx_sha256": "sha256:abc",
            "change_reason": "initial baseline",
            "auto_update_allowed": True,
        },
        "dimensions": [
            {
                "dimension_id": "content.hashes",
                "required": True,
                "comparator_mode": "subset",
            }
        ],
    }

    findings = validate_baseline_document(baseline, stage="standards")

    assert any(finding.type == "baseline_auto_update_not_allowed" for finding in findings)


def test_review_packet_generator_writes_drafts_outside_standards(tmp_path) -> None:
    module_path = Path("scripts/create_real_core_baseline_review_packet.py")
    spec = importlib.util.spec_from_file_location("create_real_core_baseline_review_packet", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.main(["--out", str(tmp_path / "packet")])

    assert (tmp_path / "packet/review_packet.md").exists()
    assert len(list((tmp_path / "packet/drafts/template_unit_contracts").glob("*.yaml"))) == 3
    assert len(list((tmp_path / "packet/drafts/student_content_trees").glob("*.yaml"))) == 3
    assert len(list((tmp_path / "packet/drafts/render_plans").glob("*.yaml"))) == 9
    assert not (tmp_path / "standards").exists()
