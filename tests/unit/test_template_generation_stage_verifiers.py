from __future__ import annotations

from pathlib import Path

from docfit.core.status import Status
from docfit.harness.template_generation_run_bundle import (
    BoundArtifact,
    TemplateGenerationRunBundle,
)
from docfit.harness.template_generation_stage_verifiers import (
    judge_template_generation_stage,
)
from docfit.harness.template_generation_standard_quality import (
    StageStandardSpec,
    TemplateGenerationStandardQualityReport,
)


def test_t1_stage_check_blocks_forbidden_semantic_fields_even_when_gate_is_audit_only(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t1_document_facts",
        "T1",
        "document_facts",
        expected={
            "artifact_type": "document_facts",
            "source_fact_contract": {
                "required_top_level_fields": [
                    "artifact_type",
                    "metadata",
                    "body_flow",
                    "runs",
                    "data",
                    "indexes",
                    "warnings",
                ],
                "required_data_groups": ["sections"],
                "locator_contract": {
                    "source_seq_required_for_visible_body_flow": True,
                    "source_ref_required_for_visible_body_flow": True,
                },
            },
            "forbidden_semantic_fields": ["unit_id", "policy"],
        },
    )
    artifact = BoundArtifact(
        artifact_key="document_facts",
        stage_key="t1_document_facts",
        stage_id="T1",
        path=tmp_path / "01_document_facts.json",
        sha256="sha256:artifact",
        declared_sha256="sha256:artifact",
        source_kind="ordered_top_level",
        status=Status.PASS,
        payload={
            "artifact_type": "document_facts",
            "metadata": {},
            "body_flow": [
                {
                    "node_id": "body_1",
                    "text": "目录",
                    "source_seq": 1,
                    "source_ref": "word/document.xml#p1",
                    "unit_id": "toc",
                }
            ],
            "runs": [],
            "data": {"sections": []},
            "indexes": {},
            "warnings": [],
        },
        hash_match=True,
    )

    check = judge_template_generation_stage(
        "t1_document_facts",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t1_document_facts"),
        run_bundle=_bundle(Status.PASS, {"document_facts": artifact}),
    )

    assert check.audit_status == "FAIL"
    assert check.status == Status.UNKNOWN
    assert {
        finding.type for finding in check.findings
    } >= {
        "t1_forbidden_semantic_fields_present",
        "template_generation_stage_verifier_not_configured",
    }


def test_configured_t1_stage_can_pass_when_gate_enabled(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t1_document_facts",
        "T1",
        "document_facts",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "artifact_type": "document_facts",
            "source_fact_contract": {
                "required_top_level_fields": ["artifact_type", "body_flow", "data"],
                "required_data_groups": ["sections"],
                "locator_contract": {
                    "source_seq_required_for_visible_body_flow": True,
                    "source_ref_required_for_visible_body_flow": True,
                },
            },
            "forbidden_semantic_fields": ["unit_id"],
        },
    )
    artifact = BoundArtifact(
        artifact_key="document_facts",
        stage_key="t1_document_facts",
        stage_id="T1",
        path=tmp_path / "01_document_facts.json",
        sha256="sha256:artifact",
        declared_sha256="sha256:artifact",
        source_kind="ordered_top_level",
        status=Status.PASS,
        payload={
            "artifact_type": "document_facts",
            "body_flow": [
                {
                    "node_id": "body_1",
                    "text": "正文",
                    "source_seq": 1,
                    "source_ref": "word/document.xml#p1",
                }
            ],
            "data": {"sections": []},
        },
        hash_match=True,
    )

    check = judge_template_generation_stage(
        "t1_document_facts",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t1_document_facts"),
        run_bundle=_bundle(Status.PASS, {"document_facts": artifact}),
    )

    assert check.audit_status == "PASS"
    assert check.status == Status.PASS
    assert check.findings == []


def test_stage_check_marks_run_bundle_dependency_unknown(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={"unit_order": []},
    )
    artifact = BoundArtifact(
        artifact_key="element_spec",
        stage_key="t3_element_policy",
        stage_id="T3",
        path=tmp_path / "03_element_spec.yaml",
        sha256="sha256:artifact",
        declared_sha256="sha256:artifact",
        source_kind="ordered_top_level",
        status=Status.PASS,
        payload={"artifact_type": "element_spec", "elements": []},
        hash_match=True,
    )

    check = judge_template_generation_stage(
        "t3_element_policy",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t3_element_policy"),
        run_bundle=_bundle(Status.UNKNOWN, {"element_spec": artifact}),
    )

    assert check.status == Status.UNKNOWN
    assert any(
        finding.type == "template_generation_run_bundle_not_pass"
        for finding in check.findings
    )


def test_t3_fixed_units_reject_fill_elements_by_default(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["cover"],
            "policy_groups": {"fixed_units": ["cover"]},
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_001",
                "element_id": "e_001",
                "unit_id": "cover",
                "policy": "fill",
                "fill_source": "student_input",
                "source_refs": ["word/document.xml:p[1]"],
                "source_seq_refs": [1],
            }
        ],
    )

    check = judge_template_generation_stage(
        "t3_element_policy",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t3_element_policy"),
        run_bundle=_bundle(Status.PASS, {"element_spec": artifact}),
    )

    assert check.audit_status == "FAIL"
    assert check.status == Status.FAIL
    assert any(finding.type == "t3_policy_group_conflict" for finding in check.findings)


def test_t3_fixed_units_can_explicitly_allow_fill_elements(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["cover"],
            "policy_groups": {
                "fixed_units": ["cover"],
                "fixed_units_allow_fill_elements": ["cover"],
            },
            "element_policy_contract": {
                "required_fields_by_policy": {
                    "fill": ["fill_source", "source_refs", "source_seq_refs"],
                }
            },
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_001",
                "element_id": "e_001",
                "unit_id": "cover",
                "policy": "fill",
                "fill_source": "student_input",
                "source_refs": ["word/document.xml:p[1]"],
                "source_seq_refs": [1],
            }
        ],
    )

    check = judge_template_generation_stage(
        "t3_element_policy",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t3_element_policy"),
        run_bundle=_bundle(Status.PASS, {"element_spec": artifact}),
    )

    assert check.audit_status == "PASS"
    assert check.status == Status.PASS
    assert check.audit["policy_group_conflicts"] == []


def test_t3_run_level_element_expectations_can_pass(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["cover"],
            "run_level_elements": [
                {
                    "unit_id": "cover",
                    "source_seq": 6,
                    "expected_elements": [
                        {
                            "policy": "fixed",
                            "content_contains": "毕业论文（设计）中文题目",
                            "raw_run_ids": ["p_0007.r_002", "p_0007.r_003"],
                            "logical_run_ids": ["p_0007.lr_002"],
                        },
                        {
                            "policy": "instruction_remove",
                            "raw_run_ids": ["p_0007.r_004"],
                            "logical_run_ids": ["p_0007.lr_003"],
                        },
                    ],
                }
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_011",
                "element_id": "e_011",
                "unit_id": "cover",
                "policy": "fixed",
                "content": "毕业论文（设计）中文题目",
                "source_refs": ["word/document.xml:p[7]"],
                "source_seq_refs": [6],
                "raw_run_ids": ["p_0007.r_002", "p_0007.r_003"],
                "logical_run_ids": ["p_0007.lr_002"],
            },
            {
                "stable_id": "cover.e_012",
                "element_id": "e_012",
                "unit_id": "cover",
                "policy": "instruction_remove",
                "source_refs": ["word/document.xml:p[7]"],
                "source_seq_refs": [6],
                "raw_run_ids": ["p_0007.r_004"],
                "logical_run_ids": ["p_0007.lr_003"],
            },
        ],
    )

    check = judge_template_generation_stage(
        "t3_element_policy",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t3_element_policy"),
        run_bundle=_bundle(Status.PASS, {"element_spec": artifact}),
    )

    assert check.audit_status == "PASS"
    assert check.status == Status.PASS
    assert check.audit["run_level_element_gaps"] == []


def test_t3_run_level_element_expectations_fail_when_instruction_run_is_missing(
    tmp_path: Path,
) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["cover"],
            "run_level_elements": [
                {
                    "unit_id": "cover",
                    "source_seq": 6,
                    "expected_elements": [
                        {
                            "policy": "instruction_remove",
                            "raw_run_ids": ["p_0007.r_004"],
                            "logical_run_ids": ["p_0007.lr_003"],
                        },
                    ],
                }
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_011",
                "element_id": "e_011",
                "unit_id": "cover",
                "policy": "fixed",
                "content": "毕业论文（设计）中文题目（小二黑体加粗）",
                "source_refs": ["word/document.xml:p[7]"],
                "source_seq_refs": [6],
                "raw_run_ids": ["p_0007.r_002", "p_0007.r_003", "p_0007.r_004"],
                "logical_run_ids": ["p_0007.lr_002", "p_0007.lr_003"],
            },
        ],
    )

    check = judge_template_generation_stage(
        "t3_element_policy",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t3_element_policy"),
        run_bundle=_bundle(Status.PASS, {"element_spec": artifact}),
    )

    assert check.audit_status == "FAIL"
    assert check.status == Status.FAIL
    assert check.audit["run_level_element_gaps"]
    assert any(
        finding.type == "t3_run_level_element_mismatch"
        for finding in check.findings
    )


def test_t3_element_expectations_and_run_span_ledger_can_pass(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["abstract_cn"],
            "element_expectations": [
                {
                    "unit_id": "abstract_cn",
                    "element_id": "e_001",
                    "policy": "fixed",
                    "content_contains": "摘要",
                    "raw_run_ids": ["p_0036.r_001"],
                    "logical_run_ids": ["p_0036.lr_001"],
                }
            ],
            "run_span_ledger": [
                {
                    "unit_id": "abstract_cn",
                    "raw_run_id": "p_0036.r_001",
                    "logical_run_id": "p_0036.lr_001",
                    "expected_policy": "fixed",
                    "expected_element_ref": "abstract_cn.e_001",
                    "text_anchor": "摘要",
                }
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "abstract_cn.e_001",
                "element_id": "e_001",
                "unit_id": "abstract_cn",
                "policy": "fixed",
                "content": "摘要",
                "source_refs": ["word/document.xml:p[36]"],
                "source_seq_refs": [20],
                "raw_run_ids": ["p_0036.r_001"],
                "logical_run_ids": ["p_0036.lr_001"],
            }
        ],
    )

    check = judge_template_generation_stage(
        "t3_element_policy",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t3_element_policy"),
        run_bundle=_bundle(Status.PASS, {"element_spec": artifact}),
    )

    assert check.audit_status == "PASS"
    assert check.status == Status.PASS
    assert check.audit["element_expectation_gaps"] == []
    assert check.audit["run_span_ledger_gaps"] == []


def test_t3_element_expectations_and_run_span_ledger_fail_on_policy_gap(
    tmp_path: Path,
) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["abstract_cn"],
            "element_expectations": [
                {
                    "unit_id": "abstract_cn",
                    "element_id": "e_001",
                    "policy": "fixed",
                    "content_contains": "摘要",
                    "raw_run_ids": ["p_0036.r_001"],
                    "logical_run_ids": ["p_0036.lr_001"],
                }
            ],
            "run_span_ledger": [
                {
                    "unit_id": "abstract_cn",
                    "raw_run_id": "p_0036.r_001",
                    "logical_run_id": "p_0036.lr_001",
                    "expected_policy": "fixed",
                    "expected_element_ref": "abstract_cn.e_001",
                    "text_anchor": "摘要",
                }
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "abstract_cn.e_001",
                "element_id": "e_001",
                "unit_id": "abstract_cn",
                "policy": "fill",
                "content": "摘要",
                "source_refs": ["word/document.xml:p[36]"],
                "source_seq_refs": [20],
                "raw_run_ids": ["p_0036.r_001"],
                "logical_run_ids": ["p_0036.lr_001"],
            }
        ],
    )

    check = judge_template_generation_stage(
        "t3_element_policy",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t3_element_policy"),
        run_bundle=_bundle(Status.PASS, {"element_spec": artifact}),
    )

    assert check.audit_status == "FAIL"
    assert check.status == Status.FAIL
    assert check.audit["element_expectation_gaps"]
    assert check.audit["run_span_ledger_gaps"]
    assert {
        finding.type for finding in check.findings
    } >= {
        "t3_element_expectation_mismatch",
        "t3_run_span_ledger_mismatch",
    }


def _stage_standard(
    tmp_path: Path,
    stage_key: str,
    stage_id: str,
    artifact: str,
    *,
    verifier_state: str = "not_configured",
    gate_enabled: bool = False,
    expected: dict,
) -> StageStandardSpec:
    return StageStandardSpec(
        stage_key=stage_key,
        stage_id=stage_id,
        path=tmp_path / f"{stage_key}.standard.yaml",
        sha256="sha256:standard",
        verifier_state=verifier_state,
        gate_enabled=gate_enabled,
        artifact_under_test=artifact,
        expected=expected,
        raw={
            "stage_id": stage_id,
            "artifact_under_test": artifact,
            "verifier_state": verifier_state,
            "gate_enabled": gate_enabled,
            "expected": expected,
        },
    )


def _element_spec_artifact(
    tmp_path: Path,
    elements: list[dict],
) -> BoundArtifact:
    return BoundArtifact(
        artifact_key="element_spec",
        stage_key="t3_element_policy",
        stage_id="T3",
        path=tmp_path / "03_element_spec.yaml",
        sha256="sha256:artifact",
        declared_sha256="sha256:artifact",
        source_kind="ordered_top_level",
        status=Status.PASS,
        payload={"artifact_type": "element_spec", "elements": elements},
        hash_match=True,
    )


def _quality(stage_key: str) -> TemplateGenerationStandardQualityReport:
    return TemplateGenerationStandardQualityReport(
        scope="demo-school",
        status=Status.PASS,
        target_reports=[],
        findings=[],
        stage_statuses={stage_key: Status.PASS.value},
    )


def _bundle(
    status: Status,
    artifacts: dict[str, BoundArtifact],
) -> TemplateGenerationRunBundle:
    return TemplateGenerationRunBundle(
        source_run_id="run",
        source_run_dir=Path("run"),
        source_run_dir_name="run",
        status=status,
        manifest_source="debug_index",
        artifacts=artifacts,
        findings=[],
    )
