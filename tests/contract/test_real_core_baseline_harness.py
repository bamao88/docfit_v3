from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

from docfit.convert.orchestrator import run_e2e_eval
from docfit.core.io import read_json
from docfit.core.status import Status
from docfit.harness.baselines import validate_baseline_document
from docfit.harness.coverage import evaluate_profile_coverage
from docfit.harness.profiles import get_eval_cases_for_profile, get_eval_profile
from docfit.harness.word_evidence import build_word_image_evidence_manifest


ROOT = Path.cwd()


def _link_real_core_inputs(root: Path) -> None:
    for name in ["standards", "inputs", "docs"]:
        os.symlink(ROOT / name, root / name, target_is_directory=True)


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


def test_real_core_coverage_is_unknown_until_word_image_evidence_exists(tmp_path) -> None:
    _link_real_core_inputs(tmp_path)

    report, findings = evaluate_profile_coverage(tmp_path, "real-core-v0")

    assert report["status"] == Status.UNKNOWN.value
    assert report["case_counts"] == {"template": 3, "content": 3, "e2e": 9}
    assert report["source_files"]["missing"] == []
    assert "missing_profile_case_registry" not in report["missing"]
    assert report["baseline_status"] == "source_facts_signed_word_evidence_pending"
    assert report["missing"] == ["missing_word_image_evidence"]
    assert not any(finding.type == "missing_signed_standard" for finding in findings)
    assert not any(finding.type == "missing_profile_baseline" for finding in findings)
    assert sum(finding.type == "missing_word_image_evidence" for finding in findings) == 9


def test_real_core_coverage_does_not_pass_with_only_bound_word_image_evidence(tmp_path) -> None:
    _link_real_core_inputs(tmp_path)
    cases = [case for case in get_eval_cases_for_profile("real-core-v0") if case.stage == "e2e"]
    for case in cases:
        case_dir = tmp_path / "reports/real-core-v0" / case.case_id
        evidence_dir = case_dir / "evidence"
        final_docx = case_dir / "final.docx"
        page_png = evidence_dir / "page-1.png"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        final_docx.write_bytes(b"docx")
        page_png.write_bytes(b"png")
        manifest = build_word_image_evidence_manifest(
            case_id=case.case_id,
            school_id=case.school_id,
            student_id=case.student_id or "",
            final_docx=final_docx,
            image_paths=[page_png],
            word_application="Microsoft Word",
            word_version="16.test",
            platform="macOS",
            export_method="test fixture",
        )
        (evidence_dir / "word_image_evidence.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

    report, findings = evaluate_profile_coverage(tmp_path, "real-core-v0")

    assert report["status"] == Status.UNKNOWN.value
    assert report["baseline_status"] == "business_acceptance_blocked"
    assert report["missing"] == ["missing_product_quality_evidence"]
    assert report["product_quality"]["missing_cases"] == [
        case.case_id for case in cases
    ]
    assert sum(finding.type == "missing_product_quality_evidence" for finding in findings) == 9


def test_real_core_coverage_requires_checked_in_case_registry(tmp_path) -> None:
    report, findings = evaluate_profile_coverage(tmp_path, "real-core-v0")

    assert report["status"] == Status.UNKNOWN.value
    assert any(finding.type == "missing_profile_case_registry" for finding in findings)


def test_real_core_e2e_reaches_render_and_writes_bound_final_docx(tmp_path) -> None:
    result = run_e2e_eval(
        ROOT,
        "hunannongye",
        ROOT / "inputs/real-student-001-source.docx",
        tmp_path / "real_core_case",
    )

    assert result.status == Status.FAIL
    assert result.blocked_at == "template"
    assert (tmp_path / "real_core_case/final.docx").exists()
    summary = read_json(tmp_path / "real_core_case/summary.json")
    assert summary["stage_statuses"] == {
        "template": "UNKNOWN",
        "content": "UNKNOWN",
        "placement": "UNKNOWN",
        "render": "FAIL",
    }
    assert "coverage_insufficient" in [finding.type for finding in result.findings]
    assert "template_unit_tree_missing" in [finding.type for finding in result.findings]
    assert "render_append_only_insertion" in [finding.type for finding in result.findings]
    assert result.findings[0].affected_ids == ["render.word_image_evidence"]


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
