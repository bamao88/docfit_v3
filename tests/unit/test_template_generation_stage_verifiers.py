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
