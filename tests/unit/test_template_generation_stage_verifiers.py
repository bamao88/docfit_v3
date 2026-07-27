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


def test_t3_run_level_element_expectations_can_pass_from_spans(tmp_path: Path) -> None:
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
                            "content_contains": "小二黑体加粗",
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
                "spans": [
                    {
                        "span_id": "cover.e_011.s_001",
                        "span_type": "label",
                        "policy": "fixed",
                        "text": "毕业论文（设计）中文题目",
                        "raw_run_ids": ["p_0007.r_002", "p_0007.r_003"],
                        "logical_run_ids": ["p_0007.lr_002"],
                    },
                    {
                        "span_id": "cover.e_011.s_002",
                        "span_type": "inline_instruction",
                        "policy": "remove_instruction",
                        "text": "（小二黑体加粗）",
                        "raw_run_ids": ["p_0007.r_004"],
                        "logical_run_ids": ["p_0007.lr_003"],
                    },
                ],
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


def test_t3_element_expectations_can_pass_with_content_anchor_stable_id_drift(
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
            "element_expectations": [
                {
                    "unit_id": "cover",
                    "stable_id": "cover.e_003",
                    "policy": "fill",
                    "content_contains": "毕业论文（设计）中文题目",
                    "raw_run_ids": ["p_0007.r_002", "p_0007.r_003"],
                    "logical_run_ids": ["p_0007.lr_002"],
                }
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_006",
                "element_id": "e_006",
                "unit_id": "cover",
                "policy": "fill",
                "content": "毕业论文（设计）中文题目（小二黑体加粗）",
                "source_refs": ["word/document.xml:p[7]"],
                "source_seq_refs": [6],
                "raw_run_ids": ["p_0007.r_002", "p_0007.r_003", "p_0007.r_004"],
                "logical_run_ids": ["p_0007.lr_002", "p_0007.lr_003"],
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
    assert check.audit["element_expectation_gaps"] == []


def test_t3_run_span_ledger_can_pass_from_spans(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["cover"],
            "run_span_ledger": [
                {
                    "unit_id": "cover",
                    "raw_run_id": "p_0003.r_003",
                    "logical_run_id": "p_0003.lr_003",
                    "expected_policy": "fill",
                    "expected_element_ref": "cover.e_003",
                    "text_anchor": "20××××",
                }
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_003",
                "element_id": "e_003",
                "unit_id": "cover",
                "policy": "fill",
                "content": "□□□□□□学□□号：20××××××××××（四号Times New Roman）",
                "source_refs": ["word/document.xml:p[3]"],
                "source_seq_refs": [3],
                "raw_run_ids": ["p_0003.r_001", "p_0003.r_002", "p_0003.r_003"],
                "logical_run_ids": [
                    "p_0003.lr_001",
                    "p_0003.lr_002",
                    "p_0003.lr_003",
                ],
                "spans": [
                    {
                        "span_id": "cover.e_003.s_001",
                        "span_type": "layout_spacer",
                        "policy": "remove_instruction",
                        "text": "□□□□□□",
                        "raw_run_ids": ["p_0003.r_001"],
                        "logical_run_ids": ["p_0003.lr_001"],
                    },
                    {
                        "span_id": "cover.e_003.s_002",
                        "span_type": "label",
                        "policy": "fixed",
                        "text": "学□□号：",
                        "raw_run_ids": ["p_0003.r_002"],
                        "logical_run_ids": ["p_0003.lr_002"],
                    },
                    {
                        "span_id": "cover.e_003.s_003",
                        "span_type": "sample_value",
                        "policy": "fill",
                        "text": "20××××××××××",
                        "raw_run_ids": ["p_0003.r_003"],
                        "logical_run_ids": ["p_0003.lr_003"],
                    },
                ],
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
    assert check.audit["run_span_ledger_gaps"] == []


def test_t3_run_span_ledger_can_pass_with_stable_id_drift(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["cover"],
            "run_span_ledger": [
                {
                    "unit_id": "cover",
                    "raw_run_id": "p_0007.r_003",
                    "logical_run_id": "p_0007.lr_002",
                    "expected_policy": "fill",
                    "expected_element_ref": "cover.e_003",
                    "text_anchor": "毕业论文（设计）中文题目",
                }
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_006",
                "element_id": "e_006",
                "unit_id": "cover",
                "policy": "fill",
                "content": "毕业论文（设计）中文题目（小二黑体加粗）",
                "source_refs": ["word/document.xml:p[7]"],
                "source_seq_refs": [6],
                "raw_run_ids": ["p_0007.r_002", "p_0007.r_003", "p_0007.r_004"],
                "logical_run_ids": ["p_0007.lr_002", "p_0007.lr_003"],
                "spans": [
                    {
                        "span_id": "cover.e_006.s_001",
                        "span_type": "sample_value",
                        "policy": "fill",
                        "text": "毕业论文（设计）中文题目",
                        "raw_run_ids": ["p_0007.r_003"],
                        "logical_run_ids": ["p_0007.lr_002"],
                    }
                ],
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


def test_t3_core_action_gold_ignores_policy_subtype_and_element_grouping(
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
            "core_action_contract": _t3_core_action_contract(),
            "element_policy_contract": {
                "allowed_policies": [
                    "template_default",
                    "fill",
                    "fixed",
                    "generated",
                    "instruction_remove",
                ],
            },
            "run_span_ledger": [
                {
                    "raw_run_id": "p_0001.r_001",
                    "logical_run_id": "p_0001.lr_001",
                    "unit_id": "original_gold_unit",
                    "expected_action": "keep",
                },
                {
                    "raw_run_id": "p_0002.r_001",
                    "logical_run_id": "p_0002.lr_001",
                    "unit_id": "original_gold_unit",
                    "expected_action": "fill",
                },
                {
                    "raw_run_id": "p_0003.r_001",
                    "logical_run_id": "p_0003.lr_001",
                    "unit_id": "original_gold_unit",
                    "expected_action": "unknown",
                    "execution_fallback_action": "keep",
                },
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_001",
                "element_id": "e_001",
                "unit_id": "cover",
                "policy": "template_default",
                "raw_run_ids": ["p_0001.r_001"],
                "logical_run_ids": ["p_0001.lr_001"],
            },
            {
                "stable_id": "cover.e_002",
                "element_id": "e_002",
                "unit_id": "cover",
                "policy": "fill",
                "raw_run_ids": ["p_0002.r_001"],
                "logical_run_ids": ["p_0002.lr_001"],
            },
            {
                "stable_id": "cover.e_003",
                "element_id": "e_003",
                "unit_id": "cover",
                "policy": "generated",
                "raw_run_ids": ["p_0002.r_001"],
                "logical_run_ids": ["p_0002.lr_001"],
            },
            {
                "stable_id": "cover.e_004",
                "element_id": "e_004",
                "unit_id": "cover",
                "policy": "fixed",
                "raw_run_ids": ["p_0003.r_001"],
                "logical_run_ids": ["p_0003.lr_001"],
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

    assert check.status == Status.PASS
    assert check.audit["core_action_accuracy"] == 1.0
    assert check.audit["core_action_gold_count"] == 2
    assert check.audit["core_action_unknown_gold_count"] == 1
    assert check.audit["unknown_execution_fallback_gaps"] == []
    assert check.audit["core_action_match_count"] == 2
    assert check.audit["run_span_ledger_gaps"] == []


def test_t3_core_action_gold_scores_adaptive_spans_by_exact_range(
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
            "core_action_contract": _t3_core_action_contract(),
            "element_policy_contract": {
                "allowed_policies": ["fixed", "fill"],
            },
            "run_span_ledger": [
                {
                    "target_kind": "span",
                    "raw_run_id": "p_0001.r_001",
                    "start": 0,
                    "end": 2,
                    "text": "标签",
                    "expected_action": "keep",
                },
                {
                    "target_kind": "span",
                    "raw_run_id": "p_0001.r_001",
                    "start": 2,
                    "end": 4,
                    "text": "示例",
                    "expected_action": "fill",
                },
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_001",
                "element_id": "e_001",
                "unit_id": "cover",
                "policy": "fixed",
                "raw_run_ids": ["p_0001.r_001"],
                "spans": [
                    {
                        "policy": "fixed",
                        "char_ranges": [
                            {
                                "raw_run_id": "p_0001.r_001",
                                "start": 0,
                                "end": 2,
                            }
                        ],
                    },
                    {
                        "policy": "fill",
                        "char_ranges": [
                            {
                                "raw_run_id": "p_0001.r_001",
                                "start": 2,
                                "end": 4,
                            }
                        ],
                    },
                ],
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

    assert check.status == Status.PASS
    assert check.audit["core_action_gold_count"] == 2
    assert check.audit["core_action_accuracy"] == 1.0
    assert check.audit["run_span_ledger_gaps"] == []


def test_t3_core_action_gold_fails_only_when_core_action_is_wrong(
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
            "core_action_contract": _t3_core_action_contract(),
            "element_policy_contract": {
                "allowed_policies": ["fixed", "instruction_remove"],
            },
            "run_span_ledger": [
                {
                    "raw_run_id": "p_0001.r_001",
                    "logical_run_id": "p_0001.lr_001",
                    "expected_action": "delete",
                }
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_001",
                "element_id": "e_001",
                "unit_id": "cover",
                "policy": "fixed",
                "raw_run_ids": ["p_0001.r_001"],
                "logical_run_ids": ["p_0001.lr_001"],
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

    assert check.status == Status.FAIL
    assert check.audit["core_action_accuracy"] == 0.0
    assert check.audit["run_span_ledger_gaps"]


def test_t3_unknown_gold_fails_if_execution_policy_is_delete(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["cover"],
            "core_action_contract": _t3_core_action_contract(),
            "element_policy_contract": {
                "allowed_policies": ["fixed", "instruction_remove"],
            },
            "run_span_ledger": [
                {
                    "raw_run_id": "p_0001.r_001",
                    "logical_run_id": "p_0001.lr_001",
                    "expected_action": "unknown",
                    "execution_fallback_action": "keep",
                }
            ],
        },
    )
    artifact = _element_spec_artifact(
        tmp_path,
        [
            {
                "stable_id": "cover.e_001",
                "element_id": "e_001",
                "unit_id": "cover",
                "policy": "instruction_remove",
                "raw_run_ids": ["p_0001.r_001"],
                "logical_run_ids": ["p_0001.lr_001"],
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

    assert check.status == Status.FAIL
    assert check.audit["core_action_gold_count"] == 0
    assert check.audit["core_action_unknown_gold_count"] == 1
    assert check.audit["unknown_execution_fallback_gaps"]
    assert "t3_unknown_execution_fallback_mismatch" in {
        finding.type for finding in check.findings
    }


def test_t1_empty_fact_containers_cannot_pass_required_check_ledger(tmp_path: Path) -> None:
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
                "required_top_level_fields": ["artifact_type", "body_flow", "runs", "data"],
                "required_data_groups": ["sections"],
                "ooxml_fact_policy": {
                    "preserve_visible_text": True,
                    "preserve_run_boundaries": True,
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
            "body_flow": [],
            "runs": [],
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

    assert check.audit_status == "UNKNOWN"
    assert check.status == Status.UNKNOWN
    assert check.audit["required_check_ledger"]["status"] == "UNKNOWN"
    assert any(finding.type == "t1_required_fact_evidence_missing" for finding in check.findings)


def test_t3_rejects_policy_outside_signed_ontology(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["cover"],
            "element_policy_contract": {
                "allowed_policies": ["fixed", "fill", "instruction_remove"],
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
                "policy": "totally_invalid",
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
    assert any(finding.type == "t3_policy_not_allowed" for finding in check.findings)


def test_unconsumed_standard_field_forces_unknown(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t3_element_policy",
        "T3",
        "element_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={"unit_order": [], "future_requirement": {"must_be_checked": True}},
    )
    artifact = _element_spec_artifact(tmp_path, [])

    check = judge_template_generation_stage(
        "t3_element_policy",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t3_element_policy"),
        run_bundle=_bundle(Status.PASS, {"element_spec": artifact}),
    )

    assert check.audit_status == "UNKNOWN"
    assert check.status == Status.UNKNOWN
    assert check.audit["required_check_ledger"]["unconsumed_standard_paths"] == [
        "expected.future_requirement.must_be_checked"
    ]


def test_t4_rejects_bogus_layout_semantics(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t4_global_layout",
        "T4",
        "global_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["cover"],
            "layout_policy": {
                "page_policy_source": "t2.standard.yaml",
                "document_start_units": ["cover"],
                "standalone_units": ["cover"],
                "flowing_units": [],
            },
            "global_layout_contract": {
                "artifact_type": "global_spec",
                "section_profiles_required": True,
                "section_profile_ids_unique": True,
                "section_boundaries_must_trace_to_source_seq": True,
                "page_numbering_display_status_required": True,
                "detected_page_numbering_requires_page_field_evidence": True,
                "no_page_field_requires_checked_scope": True,
                "header_footer_refs_must_resolve_to_parsed_parts": True,
                "numbering_rules_must_be_preserved_from_document_facts": True,
                "must_not_change_t2_unit_order": True,
            },
        },
    )
    payload = {
        "artifact_type": "global_spec",
        "section_profiles": [
            {
                "section_profile_id": "duplicate",
                "source_ref": "word/document.xml:p[1]/sectPr",
                "boundary": {"status": "detected"},
                "page_numbering": {"display": {"status": "detected"}, "fields": []},
                "header_footer": {"effective_references": []},
            },
            {
                "section_profile_id": "duplicate",
                "source_ref": "word/document.xml:body/sectPr",
                "boundary": {"status": "detected"},
                "page_numbering": {"display": {"status": "detected"}, "fields": []},
                "header_footer": {"effective_references": []},
            },
        ],
        "page_numbering": {"status": "bogus"},
        "header_footer": [],
        "numbering_rules": {"definitions": ["bogus"], "refs": []},
    }
    artifact = _bound_artifact(tmp_path, "global_spec", "t4_global_layout", "T4", payload)
    unit_map = _bound_artifact(
        tmp_path,
        "unit_map",
        "t2_unit_pagination",
        "T2",
        {"artifact_type": "unit_map", "units": [{"unit_id": "cover"}]},
    )
    document_facts = _bound_artifact(
        tmp_path,
        "document_facts",
        "t1_document_facts",
        "T1",
        {"artifact_type": "document_facts", "data": {"numbering_definitions": [], "numbering_refs": []}},
    )

    check = judge_template_generation_stage(
        "t4_global_layout",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t4_global_layout"),
        run_bundle=_bundle(
            Status.PASS,
            {"global_spec": artifact, "unit_map": unit_map, "document_facts": document_facts},
        ),
    )

    assert check.audit_status == "FAIL"
    assert check.status == Status.FAIL
    assert {finding.type for finding in check.findings} >= {
        "global_spec_duplicate_section_profile_id",
        "global_spec_page_numbering_detected_without_page_field",
        "t4_numbering_rules_not_preserved",
    }


def test_t5_rejects_wrong_hashes_and_unresolved_section_refs(tmp_path: Path) -> None:
    standard = _stage_standard(
        tmp_path,
        "t5_template_spec",
        "T5",
        "template_spec",
        verifier_state="configured",
        gate_enabled=True,
        expected={
            "unit_order": ["cover"],
            "template_spec_contract": {
                "artifact_type": "template_spec",
                "merge_inputs": ["document_facts", "unit_map", "element_spec", "global_spec"],
                "required_input_hashes": ["document_facts", "unit_map", "element_spec", "global_spec"],
                "must_preserve_unit_order": True,
                "unit_ids_must_be_unique_except_reviewed_other": True,
                "every_unit_must_have_section_profile_refs": True,
                "unit_section_refs_must_resolve_to_global_section_profiles": True,
                "unit_section_ranges_must_overlap_unit_source_seq_range": True,
                "fill_elements_must_preserve_fill_source": True,
                "review_flags_must_not_be_dropped": True,
                "no_word_action_execution": True,
                "downstream_owner_for_docx_build": "T6",
            },
        },
    )
    document_facts = _bound_artifact(tmp_path, "document_facts", "t1_document_facts", "T1", {"artifact_type": "document_facts"})
    unit_map = _bound_artifact(
        tmp_path,
        "unit_map",
        "t2_unit_pagination",
        "T2",
        {
            "artifact_type": "unit_map",
            "units": [
                {
                    "unit_id": "cover",
                    "page_policy": {
                        "start": "document_start",
                        "scope": "page_range_exclusive",
                    },
                }
            ],
            "flags": [],
        },
    )
    element_spec = _bound_artifact(
        tmp_path,
        "element_spec",
        "t3_element_policy",
        "T3",
        {"artifact_type": "element_spec", "elements": [{"stable_id": "cover.e_001", "unit_id": "cover", "policy": "fill", "fill_source": "student_input"}], "flags": []},
    )
    global_payload = {"artifact_type": "global_spec", "section_profiles": [{"section_profile_id": "section_001"}], "flags": []}
    global_spec = _bound_artifact(tmp_path, "global_spec", "t4_global_layout", "T4", global_payload)
    payload = {
        "artifact_type": "template_spec",
        "input_hashes": {key: "sha256:wrong" for key in ("document_facts", "unit_map", "element_spec", "global_spec")},
        "global": global_payload,
        "units": [
            {
                "unit_id": "cover",
                "page_policy": {
                    "start": "document_start",
                    "scope": "page_range_exclusive",
                },
                "source_seq_refs": [1],
                "section_profile_refs": [{"section_profile_id": "missing", "overlap_source_seq_range": {"start": 1, "end": 1}}],
                "elements": [],
            }
        ],
        "review_flags": [],
    }
    artifact = _bound_artifact(tmp_path, "template_spec", "t5_template_spec", "T5", payload)

    check = judge_template_generation_stage(
        "t5_template_spec",
        standard=standard,
        artifact=artifact,
        standard_quality=_quality("t5_template_spec"),
        run_bundle=_bundle(
            Status.PASS,
            {
                "template_spec": artifact,
                "document_facts": document_facts,
                "unit_map": unit_map,
                "element_spec": element_spec,
                "global_spec": global_spec,
            },
        ),
    )

    assert check.audit_status == "FAIL"
    assert check.status == Status.FAIL
    assert {finding.type for finding in check.findings} >= {
        "t5_input_hash_mismatch",
        "template_spec_unit_section_profile_ref_missing",
        "t5_element_binding_mismatch",
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


def _t3_core_action_contract() -> dict:
    return {
        "primary_metric": "exact_action_accuracy",
        "scored_ledger": "run_span_ledger",
        "gold_granularity": "adaptive_run_or_span",
        "gold_source_field": "expected_action",
        "owned_structure_layers": ["body_flow"],
        "allowed_actions": ["keep", "fill", "delete"],
        "policy_to_action": {
            "fixed": "keep",
            "template_default": "keep",
            "template_default_optional": "keep",
            "fill": "fill",
            "generated": "fill",
            "instruction_remove": "delete",
            "remove_instruction": "delete",
        },
        "grouping_invariant": True,
        "subtype_policy_accuracy": "out_of_scope",
        "unknown_action": "unknown",
        "unknown_scoring": "excluded_from_primary",
        "unknown_execution_fallback": "keep",
        "uncertain_delete_forbidden": True,
    }


def _bound_artifact(
    tmp_path: Path,
    artifact_key: str,
    stage_key: str,
    stage_id: str,
    payload: dict,
) -> BoundArtifact:
    return BoundArtifact(
        artifact_key=artifact_key,
        stage_key=stage_key,
        stage_id=stage_id,
        path=tmp_path / f"{artifact_key}.json",
        sha256=f"sha256:{artifact_key}",
        declared_sha256=f"sha256:{artifact_key}",
        source_kind="ordered_top_level",
        status=Status.PASS,
        payload=payload,
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
