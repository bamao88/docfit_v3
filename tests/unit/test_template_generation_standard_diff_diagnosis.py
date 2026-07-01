from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.models import make_finding
from docfit.core.io import write_json
from docfit.core.status import Status
from docfit.harness.template_generation_judge_reports import (
    build_template_agent_bridge_standard_acceptance,
    build_stage_standard_diagnosis_report,
)
from docfit.harness.template_generation_run_bundle import (
    RUN_ARTIFACT_SPECS,
    BoundArtifact,
    RunArtifactSpec,
    TemplateGenerationRunBundle,
)
from docfit.harness.template_generation_stage_verifiers import StageCheck
from docfit.harness.template_generation_standard_quality import (
    StageStandardSpec,
    TemplateGenerationStandardQualityReport,
    TemplateGenerationStandardSet,
)


def test_t2_unit_order_mismatch_gets_four_layer_diagnosis_even_when_gate_disabled(
    tmp_path: Path,
) -> None:
    standard = _stage_standard(
        tmp_path,
        "t2_unit_pagination",
        "T2",
        "unit_map",
        gate_enabled=False,
    )
    artifact = _artifact(
        tmp_path,
        "unit_map",
        "t2_unit_pagination",
        "T2",
        "02_unit_map.yaml",
    )
    check = _stage_check(
        standard,
        artifact,
        Status.UNKNOWN,
        "FAIL",
        [
            make_finding(
                1,
                "t2_unit_pagination",
                Status.FAIL,
                "t2_standard_unit_order_mismatch",
                "Unit order must match the stage standard",
                repr(["cover", "toc", "body_main"]),
                repr(["cover", "body_main", "toc"]),
                root_cause_bucket="template_generation_t2_standard",
            )
        ],
    )

    report = _judge_report(tmp_path, standard, artifact, check, first_bad_stage="T2")
    diff_report = build_stage_standard_diagnosis_report(report, _spec("unit_map"))

    assert diff_report["gate_enabled"] is False
    assert diff_report["mismatches"][0]["id"] == "T2-MISMATCH-001"
    assert diff_report["mismatches"][0]["type"] == "t2_unit_order_mismatch"
    assert diff_report["mismatches"][0]["field"] == "expected.unit_order"
    assert diff_report["mismatches"][0]["problem"] == (
        "T2 unit order differs from expected.unit_order in the signed standard."
    )
    assert diff_report["mismatches"][0]["expected"] == ["cover", "toc", "body_main"]
    assert diff_report["mismatches"][0]["observed"] == ["cover", "body_main", "toc"]
    assert diff_report["root_causes"][0]["category"] == "generation_code"
    assert diff_report["owner_assignments"][0]["primary"] == (
        "template_generation_code_owner"
    )
    assert "tests/unit/test_t2_standard.py" in diff_report["fix_plan"][0]["tests"]
    assert diff_report["mismatches"][0]["root_cause"]["category"] == "generation_code"
    assert diff_report["mismatches"][0]["owner"]["primary"] == (
        "template_generation_code_owner"
    )
    assert diff_report["mismatches"][0]["fix_plan"]["action"].startswith("Fix T2")


def test_t3_policy_conflict_names_the_policy_groups(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
    )
    artifact = _artifact(
        tmp_path,
        "element_spec",
        "t3_element_policy",
        "T3",
        "03_element_spec.yaml",
    )
    check = _stage_check(
        standard,
        artifact,
        Status.FAIL,
        "FAIL",
        [
            make_finding(
                1,
                "t3_element_policy",
                Status.FAIL,
                "t3_policy_group_conflict",
                "Element policies must not conflict with unit policy groups",
                repr({"fixed_units": ["cover"]}),
                repr(
                    [
                        {
                            "stable_id": "cover.e_001",
                            "unit_id": "cover",
                            "expected": "fixed",
                            "actual": "fill",
                        }
                    ]
                ),
                affected_ids=["cover.e_001"],
                root_cause_bucket="stage_standard_mismatch",
            )
        ],
    )

    report = _judge_report(tmp_path, standard, artifact, check, first_bad_stage="T3")
    diff_report = build_stage_standard_diagnosis_report(report, _spec("element_spec"))

    mismatch = diff_report["mismatches"][0]
    assert mismatch["id"] == "T3-MISMATCH-001"
    assert mismatch["type"] == "t3_policy_group_conflict"
    assert mismatch["field"] == "expected.policy_groups"
    assert "fixed->fill" in mismatch["problem"]
    assert diff_report["root_causes"][0]["category"] == "generation_code"
    assert "policy assignment" in diff_report["fix_plan"][0]["action"]


def test_t5_symptom_points_to_upstream_first_bad_stage(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t5_template_spec",
        "T5",
        "template_spec",
    )
    artifact = _artifact(
        tmp_path,
        "template_spec",
        "t5_template_spec",
        "T5",
        "05_template_spec.yaml",
    )
    check = _stage_check(
        standard,
        artifact,
        Status.FAIL,
        "FAIL",
        [
            make_finding(
                1,
                "t5_template_spec",
                Status.FAIL,
                "t5_review_flags_dropped",
                "template_spec.review_flags must preserve upstream review flags",
                "all upstream review flags",
                repr(["t3-policy-conflict"]),
                root_cause_bucket="artifact_trace",
            )
        ],
    )

    report = _judge_report(tmp_path, standard, artifact, check, first_bad_stage="T3")
    diff_report = build_stage_standard_diagnosis_report(report, _spec("template_spec"))

    root_cause = diff_report["root_causes"][0]
    assert root_cause["category"] == "downstream_symptom"
    assert root_cause["first_bad_stage"] == "T3"
    assert diff_report["owner_assignments"][0]["primary"] == (
        "template_generation_code_owner"
    )
    assert "upstream first_bad_stage" in diff_report["fix_plan"][0]["action"]


def test_standard_missing_is_assigned_to_standard_owner(tmp_path: Path) -> None:
    artifact = _artifact(
        tmp_path,
        "unit_map",
        "t2_unit_pagination",
        "T2",
        "02_unit_map.yaml",
    )
    check = StageCheck(
        stage_key="t2_unit_pagination",
        stage_id="T2",
        verifier_state="missing",
        gate_enabled=False,
        standard_path=None,
        standard_sha256=None,
        artifact_path=artifact.path,
        artifact_sha256=artifact.sha256,
        status=Status.UNKNOWN,
        audit_status="UNKNOWN",
        findings=[
            make_finding(
                1,
                "t2_unit_pagination",
                Status.UNKNOWN,
                "template_generation_stage_standard_missing",
                "t2_unit_pagination standard is missing",
                "stage standard exists",
                "missing",
                root_cause_bucket="standard_missing",
            )
        ],
        audit={},
    )

    report = _judge_report(tmp_path, None, artifact, check, first_bad_stage="T2")
    diff_report = build_stage_standard_diagnosis_report(report, _spec("unit_map"))

    assert diff_report["root_causes"][0]["category"] == "standard_issue"
    assert diff_report["owner_assignments"][0]["primary"] == "standard_owner"
    assert diff_report["fix_plan"][0]["likely_files"] == [
        "standards/targets/*/v1/template_generation/*.standard.yaml"
    ]


def test_gate_disabled_is_comparator_issue_not_signoff_proof(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        gate_enabled=False,
    )
    artifact = _artifact(
        tmp_path,
        "element_spec",
        "t3_element_policy",
        "T3",
        "03_element_spec.yaml",
    )
    check = _stage_check(
        standard,
        artifact,
        Status.UNKNOWN,
        "PASS",
        [
            make_finding(
                1,
                "t3_element_policy",
                Status.UNKNOWN,
                "template_generation_stage_gate_disabled",
                "t3_element_policy verifier is configured but gate_enabled is false",
                "gate_enabled=true",
                "false",
                root_cause_bucket="verifier_disabled",
            )
        ],
    )

    report = _judge_report(tmp_path, standard, artifact, check, first_bad_stage="T3")
    diff_report = build_stage_standard_diagnosis_report(report, _spec("element_spec"))

    assert diff_report["root_causes"][0]["category"] == "comparator_issue"
    assert diff_report["owner_assignments"][0]["primary"] == "standard_judge_owner"
    assert diff_report["mismatches"][0]["fix_plan"]["action"].startswith(
        "Implement or configure"
    )


def test_agent_bridge_acceptance_reports_accuracy_and_diagnosis(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t2_unit_pagination",
        "T2",
        "unit_map",
    )
    artifact = _artifact(
        tmp_path,
        "unit_map",
        "t2_unit_pagination",
        "T2",
        "02_unit_map.yaml",
    )
    check = _stage_check(
        standard,
        artifact,
        Status.FAIL,
        "FAIL",
        [
            make_finding(
                1,
                "t2_unit_pagination",
                Status.FAIL,
                "t2_standard_units_missing",
                "Unit map is missing standard units",
                repr(["toc"]),
                repr(["cover", "body_main"]),
                affected_ids=["toc"],
                root_cause_bucket="template_generation_t2_standard",
            )
        ],
        audit={
            "expected_unit_ids": ["cover", "toc", "body_main"],
            "actual_unit_ids": ["cover", "body_main"],
            "missing_unit_ids": ["toc"],
            "unexpected_unit_ids": [],
            "unit_order_matches": False,
        },
    )
    run_dir = tmp_path / "eval_runs/template_generate"
    write_json(
        run_dir / "09.25_agent_observation_bridge.json",
        {
            "artifact_type": "template_agent_observation_bridge",
            "summary": {"total_proposals": 1, "manual_review_required": 0},
        },
    )

    report = _judge_report(tmp_path, standard, artifact, check, first_bad_stage="T2")
    acceptance = build_template_agent_bridge_standard_acceptance(report)

    assert acceptance["bridge_present"] is True
    assert acceptance["bridge_summary"]["total_proposals"] == 1
    assert acceptance["bridged_output_accuracy"]["aggregate_accuracy"] == 0.8
    assert acceptance["bridged_output_accuracy"]["stages"]["t2_unit_pagination"]["recall"] == round(2 / 3, 4)
    assert acceptance["mismatches"][0]["id"] == "T2-MISMATCH-001"
    assert acceptance["root_causes"][0]["category"] == "generation_code"


def _spec(artifact_key: str) -> RunArtifactSpec:
    return next(spec for spec in RUN_ARTIFACT_SPECS if spec.artifact_key == artifact_key)


def _stage_standard(
    tmp_path: Path,
    stage_key: str,
    stage_id: str,
    artifact: str,
    *,
    gate_enabled: bool = True,
) -> StageStandardSpec:
    return StageStandardSpec(
        stage_key=stage_key,
        stage_id=stage_id,
        path=tmp_path / f"{stage_key}.standard.yaml",
        sha256="sha256:standard",
        verifier_state="configured",
        gate_enabled=gate_enabled,
        artifact_under_test=artifact,
        expected={},
        raw={
            "stage_id": stage_id,
            "artifact_under_test": artifact,
            "verifier_state": "configured",
            "gate_enabled": gate_enabled,
        },
    )


def _artifact(
    tmp_path: Path,
    artifact_key: str,
    stage_key: str,
    stage_id: str,
    file_name: str,
    payload: dict[str, Any] | None = None,
) -> BoundArtifact:
    return BoundArtifact(
        artifact_key=artifact_key,
        stage_key=stage_key,
        stage_id=stage_id,
        path=tmp_path / file_name,
        sha256="sha256:artifact",
        declared_sha256="sha256:artifact",
        source_kind="ordered_top_level",
        status=Status.PASS,
        payload=payload or {},
        hash_match=True,
    )


def _stage_check(
    standard: StageStandardSpec,
    artifact: BoundArtifact,
    status: Status,
    audit_status: str,
    findings: list,
    audit: dict[str, Any] | None = None,
) -> StageCheck:
    return StageCheck(
        stage_key=standard.stage_key,
        stage_id=standard.stage_id,
        verifier_state=standard.verifier_state,
        gate_enabled=standard.gate_enabled,
        standard_path=standard.path,
        standard_sha256=standard.sha256,
        artifact_path=artifact.path,
        artifact_sha256=artifact.sha256,
        status=status,
        audit_status=audit_status,
        findings=findings,
        audit=audit or {},
    )


def _judge_report(
    tmp_path: Path,
    standard: StageStandardSpec | None,
    artifact: BoundArtifact,
    check: StageCheck,
    *,
    first_bad_stage: str,
):
    standard_set = TemplateGenerationStandardSet(
        root=tmp_path,
        school_id="demo-school",
        template_version="v1",
        target_dir=tmp_path / "standards/targets/demo-school/v1",
        target_standard_path=tmp_path / "standards/targets/demo-school/v1/target.standard.yaml",
    )
    if standard is not None:
        standard_set.stages[standard.stage_key] = standard
    run_bundle = TemplateGenerationRunBundle(
        source_run_id="template_generate",
        source_run_dir=tmp_path / "eval_runs/template_generate",
        source_run_dir_name="template_generate",
        status=Status.PASS,
        manifest_source="debug_index",
        artifacts={artifact.artifact_key: artifact},
        findings=[],
    )
    quality = TemplateGenerationStandardQualityReport(
        scope="demo-school",
        status=Status.PASS,
        target_reports=[],
        findings=[],
        stage_statuses={check.stage_key: Status.PASS.value},
    )
    from docfit.harness.template_generation_judge_reports import (
        TemplateGenerationJudgeReport,
    )

    return TemplateGenerationJudgeReport(
        status=check.status,
        first_bad_stage=first_bad_stage,
        standard_set=standard_set,
        standard_quality=quality,
        run_bundle=run_bundle,
        stage_checks=[check],
        findings=check.findings,
    )
