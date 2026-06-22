from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import yaml

from docfit.convert.orchestrator import run_e2e_eval, run_template_eval
from docfit.core.io import read_json
from docfit.core.status import Status
from docfit.harness.baselines import validate_baseline_document
from docfit.harness.coverage import evaluate_profile_coverage
from docfit.harness.product_quality import audit_template_artifact
from docfit.harness.profiles import (
    REAL_CORE_SCHOOLS,
    get_eval_cases_for_profile,
    get_eval_profile,
)
from docfit.harness.word_evidence import build_word_image_evidence_manifest


ROOT = Path.cwd()


def _link_real_core_inputs(root: Path) -> None:
    for name in ["standards", "test_inputs", "docs"]:
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


def test_real_core_template_generation_stage_standards_are_registered() -> None:
    expected_stage_ids = {
        "01_source_parse",
        "02_structure_discovery",
        "03_generation_model",
        "04_plan_build",
        "05_action_execution",
    }

    for school in REAL_CORE_SCHOOLS:
        school_id = str(school["school_id"])
        school_dir = ROOT / "standards/schools" / school_id / "v1"
        signed_standard = yaml.safe_load(
            (school_dir / "signed_standard.yaml").read_text(encoding="utf-8")
        )
        stage_contract_ref = signed_standard["evidence_baselines"][
            "template_generation_stage_contract"
        ]
        stage_contract_path = school_dir / stage_contract_ref
        stage_contract = yaml.safe_load(stage_contract_path.read_text(encoding="utf-8"))
        template_unit_contract = yaml.safe_load(
            (school_dir / "template_unit_contract.yaml").read_text(encoding="utf-8")
        )

        assert stage_contract_ref == "template_generation_stage_contract.yaml"
        assert stage_contract["baseline_type"] == "template_generation_stage_contract"
        assert stage_contract["school_id"] == school_id
        assert stage_contract["gate_policy"]["not_configured_is_not_pass"] is True
        assert stage_contract["accepted_source_facts"][
            "upstream_template_unit_contract"
        ] == "template_unit_contract.yaml"
        assert stage_contract["expected"]["unit_order"] == [
            unit["unit_id"] for unit in template_unit_contract["expected"]["units"]
        ]
        assert set(stage_contract["expected"]["stage_standards"]) == expected_stage_ids
        assert all(
            stage["verifier_state"] == "not_configured"
            and stage["gate_enabled"] is False
            for stage in stage_contract["expected"]["stage_standards"].values()
        )
        assert validate_baseline_document(stage_contract, stage="standards") == []


def test_real_core_coverage_is_unknown_until_word_image_evidence_exists(tmp_path) -> None:
    _link_real_core_inputs(tmp_path)

    report, findings = evaluate_profile_coverage(tmp_path, "real-core-v0")

    assert report["status"] == Status.UNKNOWN.value
    assert report["case_counts"] == {"template": 3, "content": 3, "e2e": 9}
    assert report["source_files"]["missing"] == []
    assert "missing_profile_case_registry" not in report["missing"]
    assert report["baseline_status"] == "generated_template_gap_pending"
    assert report["missing"] == [
        "missing_generated_template_gap_evidence",
        "missing_word_image_evidence",
    ]
    assert not any(finding.type == "missing_signed_standard" for finding in findings)
    assert not any(finding.type == "missing_profile_baseline" for finding in findings)
    assert sum(finding.type == "missing_word_image_evidence" for finding in findings) == 9
    assert (
        sum(finding.type == "missing_generated_template_gap_evidence" for finding in findings)
        == 3
    )


def test_real_core_coverage_does_not_pass_with_only_bound_word_image_evidence(tmp_path) -> None:
    _link_real_core_inputs(tmp_path)
    cases = [case for case in get_eval_cases_for_profile("real-core-v0") if case.stage == "e2e"]
    for case in cases:
        case_dir = tmp_path / "test_outputs/debug/template_eval_runs/real-core-v0" / case.case_id
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
    assert report["baseline_status"] == "generated_template_gap_pending"
    assert report["missing"] == [
        "missing_generated_template_gap_evidence",
        "missing_product_quality_evidence",
    ]
    assert report["product_quality"]["missing_cases"] == [
        case.case_id for case in cases
    ]
    assert sum(finding.type == "missing_product_quality_evidence" for finding in findings) == 9
    assert (
        sum(finding.type == "missing_generated_template_gap_evidence" for finding in findings)
        == 3
    )


def test_real_core_coverage_requires_checked_in_case_registry(tmp_path) -> None:
    report, findings = evaluate_profile_coverage(tmp_path, "real-core-v0")

    assert report["status"] == Status.UNKNOWN.value
    assert any(finding.type == "missing_profile_case_registry" for finding in findings)


def test_real_core_template_parse_outputs_reviewed_unit_tree_for_all_schools(tmp_path) -> None:
    for school in REAL_CORE_SCHOOLS:
        school_id = str(school["school_id"])
        result = run_template_eval(
            ROOT,
            school_id,
            ROOT / school["template_docx"],
            tmp_path / school_id,
        )

        assert result.status == Status.FAIL
        artifact = read_json(tmp_path / school_id / "artifacts/template_artifact.json")
        gap_report = read_json(tmp_path / school_id / "artifacts/template_gap_report.json")
        generated_from_stage = (
            tmp_path / school_id / "template_generation/generated_template.docx"
        )
        units = artifact["data"]["units"]
        slots = artifact["data"]["slots"]
        paragraphs = artifact["data"]["paragraphs"]
        instruction_paragraphs = artifact["data"]["instruction_paragraphs"]

        assert gap_report["summary"]["blocking_status"] == Status.FAIL.value
        assert generated_from_stage.exists()
        assert (
            tmp_path
            / school_id
            / "template_generation/artifacts/template_generation_manifest.json"
        ).exists()
        assert gap_report["generated_template"]["source_path"] == str(generated_from_stage)
        assert "test_inputs/template_gap" not in gap_report[
            "generated_template"
        ]["source_path"]
        assert artifact["provenance"]["source_template_docx"] == str(
            ROOT / school["template_docx"]
        )
        assert artifact["provenance"]["template_docx"] == str(generated_from_stage)
        assert artifact["provenance"]["generated_template_docx"] == str(
            generated_from_stage
        )
        assert (tmp_path / school_id / "artifacts/generated_template.docx").exists()
        assert (tmp_path / school_id / "artifacts/generated_template_tree.json").exists()
        assert (tmp_path / school_id / "artifacts/template_gap_report.md").exists()
        assert (tmp_path / school_id / "artifacts/template_gap_report.docx").exists()
        assert len(units) >= 10
        assert all(unit["unit_id"] for unit in units)
        assert all(unit["elements"] for unit in units)
        assert any(slot["slot_id"] != "slot_body_start" for slot in slots)
        assert instruction_paragraphs
        assert all(item["policy"] == "strip" for item in instruction_paragraphs)
        assert all(
            paragraph.get("template_policy") == "strip"
            for paragraph in paragraphs
            if paragraph["index"]
            in {item["paragraph_index"] for item in instruction_paragraphs}
        )
        assert audit_template_artifact(artifact) == []

        if school_id == "hunannongye":
            elements = {
                (unit["unit_id"], element["name"]): element
                for unit in units
                for element in unit["elements"]
            }
            assert elements[("cover", "学校名称")]["policy"] == "fixed"
            assert elements[("cover", "学校名称")]["style"] == (
                "华文行楷；26pt（一号）；加粗；居中；单倍行距。"
            )
            assert elements[("cover", "中文题名")]["policy"] == "fill"
            assert elements[("cover", "英文题名")]["policy"] == "fill"
            assert elements[("cover", "学生基本信息")]["policy"] == "manual_only"
            assert elements[("abstract_cn", "摘  要标签")]["policy"] == "fixed"
            assert elements[("abstract_cn", "中文摘要正文")]["policy"] == "fill"


def test_real_core_template_contract_verifier_reports_element_style_mismatch(
    tmp_path,
) -> None:
    result = run_template_eval(
        ROOT,
        "hunannongye",
        ROOT / "test_inputs/template_generation/school-hunannongye-requirement.docx",
        tmp_path / "hunannongye",
    )
    assert result.status == Status.FAIL
    artifact = read_json(tmp_path / "hunannongye/artifacts/template_artifact.json")

    artifact["data"]["units"][0]["elements"][0]["style"] = "宋体；12pt；左对齐。"

    findings = audit_template_artifact(artifact)

    assert any(
        finding.type == "template_element_style_mismatch"
        and finding.affected_ids == ["cover.e_001.style"]
        and "华文行楷" in finding.expected
        and "宋体" in finding.actual
        for finding in findings
    )


def test_real_core_template_contract_requires_structured_expected_units(
    tmp_path,
) -> None:
    result = run_template_eval(
        ROOT,
        "hunannongye",
        ROOT / "test_inputs/template_generation/school-hunannongye-requirement.docx",
        tmp_path / "hunannongye",
    )
    assert result.status == Status.FAIL
    artifact = read_json(tmp_path / "hunannongye/artifacts/template_artifact.json")
    artifact["real_core_source_facts"].pop("units")

    findings = audit_template_artifact(artifact)

    assert any(
        finding.type == "template_structured_expected_missing"
        and finding.status == Status.UNKNOWN
        for finding in findings
    )


def test_real_core_e2e_reaches_render_and_writes_bound_final_docx(tmp_path) -> None:
    result = run_e2e_eval(
        ROOT,
        "hunannongye",
        ROOT / "test_inputs/content_extraction/real-student-001-source.docx",
        tmp_path / "real_core_case",
    )

    assert result.status == Status.FAIL
    assert result.blocked_at == "template"
    assert (tmp_path / "real_core_case/final.docx").exists()
    summary = read_json(tmp_path / "real_core_case/summary.json")
    artifact = read_json(tmp_path / "real_core_case/artifacts/template_artifact.json")
    gap_report = read_json(tmp_path / "real_core_case/artifacts/template_gap_report.json")
    generated_from_stage = (
        tmp_path / "real_core_case/template_generation/generated_template.docx"
    )
    assert summary["stage_statuses"] == {
        "template": "FAIL",
        "content": "UNKNOWN",
        "placement": "PASS",
        "render": "UNKNOWN",
    }
    assert generated_from_stage.exists()
    assert (
        tmp_path
        / "real_core_case/template_generation/artifacts/template_generation_manifest.json"
    ).exists()
    assert artifact["provenance"]["template_docx"] == str(generated_from_stage)
    assert artifact["provenance"]["generated_template_docx"] == str(generated_from_stage)
    assert gap_report["generated_template"]["source_path"] == str(generated_from_stage)
    assert "coverage_insufficient" in [finding.type for finding in result.findings]
    assert "template_unit_tree_missing" not in [
        finding.type for finding in result.findings
    ]
    finding_types = [finding.type for finding in result.findings]
    assert "render_append_only_insertion" not in finding_types
    assert "placement_actions_collapsed_to_virtual_body_slot" not in finding_types
    assert any(
        finding.type == "template_generation_page_rule_unverified"
        for finding in result.findings
    )
    assert any(
        finding.type == "coverage_insufficient"
        and finding.affected_ids == ["render.word_image_evidence"]
        for finding in result.findings
    )


def test_required_dimension_without_comparator_policy_is_unknown() -> None:
    baseline = {
        "baseline_type": "student_content_tree",
        "review_metadata": {
            "reviewed_by": "product-owner",
            "review_source": "test_inputs/content_extraction/review.md",
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
            "review_source": "test_inputs/template_generation/review.txt",
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
            "review_source": "test_inputs/template_generation/review.txt",
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
