from __future__ import annotations

from pathlib import Path

import yaml

from docfit.core.status import Status
from docfit.harness.baselines import validate_baseline_document


ROOT = Path.cwd()
REAL_CORE_SCHOOL_IDS = (
    "hunannongye",
    "nannong-undergraduate",
    "pku-graduate",
)


def test_real_core_template_generation_stage_standards_are_registered() -> None:
    expected_stage_refs = {
        "t1_document_facts": "template_generation/t1_document_facts.standard.yaml",
        "t2_unit_pagination": "template_generation/t2_unit_pagination.standard.yaml",
        "t3_element_policy": "template_generation/t3_element_policy.standard.yaml",
        "t4_global_layout": "template_generation/t4_global_layout.standard.yaml",
        "t5_template_spec": "template_generation/t5_template_spec.standard.yaml",
    }
    expected_stage_metadata = {
        "t1_document_facts": (
            "template_generation_t1_document_facts",
            "T1",
            "document_facts",
        ),
        "t2_unit_pagination": (
            "template_generation_t2_unit_pagination",
            "T2",
            "unit_map",
        ),
        "t3_element_policy": (
            "template_generation_t3_element_policy",
            "T3",
            "element_spec",
        ),
        "t4_global_layout": (
            "template_generation_t4_global_layout",
            "T4",
            "global_spec",
        ),
        "t5_template_spec": (
            "template_generation_t5_template_spec",
            "T5",
            "template_spec",
        ),
    }

    for school_id in REAL_CORE_SCHOOL_IDS:
        school_dir = ROOT / "standards/targets" / school_id / "v1"
        signed_standard = yaml.safe_load(
            (school_dir / "target.standard.yaml").read_text(encoding="utf-8")
        )
        stage_contract_refs = signed_standard["evidence_baselines"][
            "template_generation_stages"
        ]
        template_generation_final = yaml.safe_load(
            (school_dir / "template_quality/final_template.expected.yaml").read_text(
                encoding="utf-8"
            )
        )

        assert stage_contract_refs == expected_stage_refs
        assert not (school_dir / "template_generation_stage_contract.yaml").exists()
        assert not (
            school_dir / "template_generation/02_structure_discovery.expected.yaml"
        ).exists()
        for legacy_stage in [
            "01_source_parse.expected.yaml",
            "03_generation_model.expected.yaml",
            "04_plan_build.expected.yaml",
            "05_action_execution.expected.yaml",
        ]:
            assert not (school_dir / "template_generation" / legacy_stage).exists()

        for stage_id, stage_contract_ref in expected_stage_refs.items():
            stage_contract_path = school_dir / stage_contract_ref
            stage_contract = yaml.safe_load(
                stage_contract_path.read_text(encoding="utf-8")
            )

            if stage_id in expected_stage_metadata:
                expected_baseline_type, expected_stage_id, expected_artifact = (
                    expected_stage_metadata[stage_id]
                )
                assert stage_contract["baseline_type"] == expected_baseline_type
                assert stage_contract["stage_id"] == expected_stage_id
                assert stage_contract["artifact_under_test"] == expected_artifact
                assert stage_contract["legacy_compatibility"] is False
                if stage_id == "t1_document_facts":
                    assert stage_contract["expected"]["artifact_type"] == "document_facts"
                    assert "unit_id" in stage_contract["expected"][
                        "forbidden_semantic_fields"
                    ]
                    assert "policy" in stage_contract["expected"][
                        "forbidden_semantic_fields"
                    ]
                    assert "confidence" in stage_contract["expected"][
                        "forbidden_semantic_fields"
                    ]
                else:
                    assert stage_contract["expected"]["unit_order"] == [
                        unit["unit_id"] for unit in template_generation_final["expected"]["units"]
                    ]
            assert stage_contract["school_id"] == school_id
            assert stage_contract["verifier_state"] == "configured"
            assert stage_contract["gate_enabled"] is True
            assert validate_baseline_document(stage_contract, stage="standards") == []


def test_required_dimension_without_comparator_policy_is_unknown() -> None:
    baseline = {
        "baseline_type": "student_content_tree",
        "review_metadata": {
            "reviewed_by": "product-owner",
            "review_source": "inputs/students/review.md",
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
        "baseline_type": "template_generation_final",
        "review_metadata": {
            "reviewed_by": "product-owner",
            "review_source": "inputs/targets/review.md",
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
            "review_source": "inputs/targets/review.md",
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
