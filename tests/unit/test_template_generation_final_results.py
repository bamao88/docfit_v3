from __future__ import annotations

import pytest

from docfit.template_generation.final_results import (
    AVAILABLE,
    NOT_AVAILABLE,
    FinalStageResultError,
    conservative_availability,
    publish_final_stage_result,
    require_final_stage_result,
)
from docfit.template_generation.verifier import _verify_final_result_chain


def _t2_final(*, availability: str = AVAILABLE):
    return publish_final_stage_result(
        {
            "artifact_type": "unit_map",
            "units": [{"unit_id": "body_main", "source_seq_refs": [1]}],
        },
        stage_id="T2",
        artifact_type="unit_map",
        artifact_name="02_unit_map.yaml",
        availability=availability,
        reason=None if availability == AVAILABLE else "fixture unavailable",
        producer_mode="fixture",
        input_refs={"l1": {"sha256": "sha256:l1"}},
    )


def test_candidate_observation_cannot_cross_final_stage_boundary() -> None:
    with pytest.raises(FinalStageResultError, match="rejected non-final"):
        require_final_stage_result(
            {
                "artifact_type": "ai_unit_observation",
                "items": [{"unit_id": "wrong_candidate"}],
            },
            stage_id="T2",
            artifact_type="unit_map",
            artifact_name="02_unit_map.yaml",
        )


def test_published_final_exposes_stable_hash_ref_and_validates_l1() -> None:
    result = _t2_final()

    accepted = require_final_stage_result(
        result.payload,
        stage_id="T2",
        artifact_type="unit_map",
        artifact_name="02_unit_map.yaml",
        expected_l1_hash="sha256:l1",
    )

    assert accepted.input_ref() == {
        "stage_id": "T2",
        "artifact": "02_unit_map.yaml",
        "sha256": result.sha256,
        "availability": AVAILABLE,
    }
    assert accepted.payload["result_role"] == "final"


def test_availability_is_conservatively_propagated() -> None:
    available = _t2_final()
    unavailable = _t2_final(availability=NOT_AVAILABLE)

    assert conservative_availability(available) == (AVAILABLE, None)
    status, reason = conservative_availability(available, unavailable)

    assert status == NOT_AVAILABLE
    assert reason == "T2: fixture unavailable"


def test_final_chain_verifier_rejects_hash_mismatch_and_availability_upgrade() -> None:
    t1 = publish_final_stage_result(
        {"artifact_type": "document_facts"},
        stage_id="T1",
        artifact_type="document_facts",
        artifact_name="01_document_facts.json",
        producer_mode="fixture",
    )
    l1 = publish_final_stage_result(
        {"artifact_type": "template_generation_l1_input_contract"},
        stage_id="L1",
        artifact_type="template_generation_l1_input_contract",
        artifact_name="01.5_l1_input_contract.json",
        producer_mode="fixture",
        input_refs={"t1": t1.input_ref()},
    )
    t2 = publish_final_stage_result(
        {"artifact_type": "unit_map"},
        stage_id="T2",
        artifact_type="unit_map",
        artifact_name="02_unit_map.yaml",
        producer_mode="fixture",
        input_refs={"l1": l1.input_ref()},
    )
    t3 = publish_final_stage_result(
        {"artifact_type": "element_spec"},
        stage_id="T3",
        artifact_type="element_spec",
        artifact_name="03_element_spec.yaml",
        availability=NOT_AVAILABLE,
        reason="fixture unavailable",
        producer_mode="fixture",
        input_refs={"l1": l1.input_ref(), "t2_final": t2.input_ref()},
    )
    t4 = publish_final_stage_result(
        {"artifact_type": "global_spec"},
        stage_id="T4",
        artifact_type="global_spec",
        artifact_name="04_global_spec.yaml",
        producer_mode="fixture",
        input_refs={"l1": l1.input_ref()},
    )
    t5 = publish_final_stage_result(
        {"artifact_type": "template_spec"},
        stage_id="T5",
        artifact_type="template_spec",
        artifact_name="05_template_spec.yaml",
        availability=NOT_AVAILABLE,
        reason="T3 unavailable",
        producer_mode="fixture",
        input_refs={
            "l1": l1.input_ref(),
            "t2_final": t2.input_ref(),
            "t3_final": t3.input_ref(),
            "t4_final": t4.input_ref(),
        },
    )
    t6 = publish_final_stage_result(
        {"artifact_type": "build_manifest"},
        stage_id="T6",
        artifact_type="build_manifest",
        artifact_name="06.2_build_manifest.json",
        producer_mode="fixture",
        input_refs={
            "l1": l1.input_ref(),
            "t5_final": {**t5.input_ref(), "sha256": "wrong"},
        },
    )

    findings, _statuses = _verify_final_result_chain(
        document_facts=t1.payload,
        l1_input_contract=l1.payload,
        unit_map=t2.payload,
        element_spec=t3.payload,
        global_spec=t4.payload,
        template_spec=t5.payload,
        build_manifest=t6.payload,
        start_index=1,
    )
    finding_types = {finding.type for finding in findings}

    assert "stage_final_input_hash_mismatch" in finding_types
    assert "stage_final_availability_upgrade" in finding_types
