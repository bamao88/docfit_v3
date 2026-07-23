from __future__ import annotations

import pytest

from docfit.template_generation.agent.t3_eval import (
    T3GoldUpstreamError,
    build_t3_gold_upstream,
    evaluate_t3_gold_accuracy,
    validate_t3_gold_upstream,
)


def packet() -> dict:
    return {"page_text_index": [{"source_seq": 1}, {"source_seq": 2}, {"source_seq": 3}]}


def test_t3_eval_accepts_only_human_confirmed_exact_t2_partition() -> None:
    result = validate_t3_gold_upstream(
        {
            "items": [
                {"unit_id": "cover", "source_seq_refs": [1]},
                {"unit_id": "body_main", "source_seq_refs": [2, 3]},
            ]
        },
        packet=packet(),
        human_confirmed=True,
        gold_source="signed/t2.standard.yaml",
    )

    assert result["status"] == "PASS"
    assert result["exact_packet_partition"] is True


@pytest.mark.parametrize(
    ("observation", "human_confirmed"),
    [
        ({"items": [{"unit_id": "cover", "source_seq_refs": [1, 2, 3]}]}, False),
        ({"items": [{"unit_id": "cover", "source_seq_refs": [1, 2]}]}, True),
        (
            {
                "items": [
                    {"unit_id": "cover", "source_seq_refs": [1, 2]},
                    {"unit_id": "body_main", "source_seq_refs": [2, 3]},
                ]
            },
            True,
        ),
    ],
)
def test_t3_eval_rejects_live_or_inexact_upstream(observation, human_confirmed) -> None:
    with pytest.raises(T3GoldUpstreamError):
        validate_t3_gold_upstream(
            observation,
            packet=packet(),
            human_confirmed=human_confirmed,
            gold_source="signed/t2.standard.yaml",
        )


def atomic_packet() -> dict:
    return {
        "source_render_hash": "sha256:render",
        "input_contract_hash": "sha256:l1",
        "page_text_index": [
            {
                "source_seq": 1,
                "structure_layer": "body_flow",
                "raw_run_ids": ["p_0001.r_001"],
                "style_details": {
                    "runs": [
                        {
                            "raw_run_id": "p_0001.r_001",
                            "logical_run_id": "p_0001.lr_001",
                            "text": "封面",
                            "source_ref": "word/document.xml:p[1]/r[1]",
                            "effective_style": {"font_size_pt": 16.0},
                        }
                    ]
                },
            },
            {
                "source_seq": 2,
                "structure_layer": "body_flow",
                "raw_run_ids": ["p_0002.r_001"],
                "style_details": {
                    "runs": [
                        {
                            "raw_run_id": "p_0002.r_001",
                            "logical_run_id": "p_0002.lr_001",
                            "text": "正文",
                            "source_ref": "word/document.xml:p[2]/r[1]",
                            "effective_style": {},
                        }
                    ]
                },
            },
            {
                "source_seq": 3,
                "structure_layer": "header_footer",
                "raw_run_ids": ["word_header1_xml.p_0001.r_001"],
                "style_details": {"runs": []},
            },
        ],
    }


def test_t3_gold_atomic_audit_reads_canonical_l1_run_index() -> None:
    source = atomic_packet()
    raw_runs = [
        run
        for row in source["page_text_index"][:2]
        for run in row["style_details"]["runs"]
    ]
    for row in source["page_text_index"]:
        row.pop("style_details", None)
    source["run_index"] = {"raw_runs": raw_runs}

    result = validate_t3_gold_upstream(
        {
            "items": [
                {"unit_id": "cover", "source_seq_refs": [1]},
                {"unit_id": "body_main", "source_seq_refs": [2]},
            ]
        },
        packet=source,
        human_confirmed=True,
        gold_source="signed/t2.standard.yaml",
        owned_structure_layers={"body_flow"},
        require_atomic_run_facts=True,
    )

    assert result["atomic_run_fact_count"] == 2
    assert result["atomic_run_facts_complete"] is True


def signed_t2_standard() -> dict:
    return {
        "stage_id": "T2",
        "standard_id": "school-v1-t2",
        "standard_state": "signed_active",
        "accepted_source_facts": {
            "template_docx_sha256": "sha256:template",
        },
        "expected": {
            "unit_order": ["cover", "body_main"],
            "units": [
                {
                    "unit_id": "cover",
                    "boundary": {"source_seq_range": {"start": 1, "end": 1}},
                },
                {
                    "unit_id": "body_main",
                    "boundary": {"source_seq_range": {"start": 2, "end": 2}},
                },
            ],
        },
    }


def core_action_contract() -> dict:
    return {
        "primary_metric": "exact_action_accuracy",
        "scored_ledger": "run_span_ledger",
        "gold_granularity": "raw_run",
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


def test_t3_gold_builder_uses_signed_body_partition_and_atomic_run_facts() -> None:
    observation, audit = build_t3_gold_upstream(
        signed_t2_standard(),
        packet=atomic_packet(),
        gold_source="standards/school/t2.standard.yaml",
        source_template_hash="sha256:template",
    )

    assert [item["unit_id"] for item in observation["items"]] == [
        "cover",
        "body_main",
    ]
    assert audit["exact_packet_partition"] is True
    assert audit["source_seq_count"] == 2
    assert audit["atomic_run_fact_count"] == 2
    assert audit["atomic_run_facts_complete"] is True
    assert audit["owned_structure_layers"] == ["body_flow"]


def test_t3_gold_builder_rejects_incomplete_atomic_run_facts() -> None:
    packet_with_gap = atomic_packet()
    packet_with_gap["page_text_index"][1]["style_details"]["runs"] = []

    with pytest.raises(T3GoldUpstreamError, match="complete atomic run facts"):
        build_t3_gold_upstream(
            signed_t2_standard(),
            packet=packet_with_gap,
            gold_source="standards/school/t2.standard.yaml",
            source_template_hash="sha256:template",
        )


def _standard_with_source_ref_toc() -> dict:
    standard = signed_t2_standard()
    standard["expected"]["unit_order"].insert(1, "toc")
    standard["expected"]["units"].insert(
        1,
        {
            "unit_id": "toc",
            "boundary": {
                "source_ref_range": {
                    "start": "word/document.xml:p[9]/field[1]",
                    "end": "word/document.xml:p[9]/field[1]",
                }
            },
        },
    )
    return standard


def _packet_with_toc_object() -> dict:
    packet = atomic_packet()
    packet["object_fact_index"] = [
        {
            "object_id": "field:word/document.xml:p[9]/field[1]",
            "object_type": "field",
            "source_ref": "word/document.xml:p[9]/field[1]",
            "kind": "complexField",
            "field_type": "TOC",
            "instruction": "TOC \\o \"1-3\" \\h \\z",
            "end_source_ref": "word/document.xml:p[12]",
        }
    ]
    return packet


def test_t3_gold_builder_rejects_source_ref_unit_without_object_fact() -> None:
    standard = _standard_with_source_ref_toc()

    with pytest.raises(T3GoldUpstreamError, match="object_fact_missing"):
        build_t3_gold_upstream(
            standard,
            packet=atomic_packet(),
            gold_source="standards/school/t2.standard.yaml",
            source_template_hash="sha256:template",
        )


def test_t3_gold_builder_accepts_source_ref_unit_with_complete_object_fact() -> None:
    observation, audit = build_t3_gold_upstream(
        _standard_with_source_ref_toc(),
        packet=_packet_with_toc_object(),
        gold_source="standards/school/t2.standard.yaml",
        source_template_hash="sha256:template",
    )

    toc = next(item for item in observation["items"] if item["unit_id"] == "toc")
    assert toc["source_seq_refs"] == []
    assert toc["source_ref_refs"] == ["word/document.xml:p[9]/field[1]"]
    assert audit["source_ref_object_count"] == 1
    assert audit["object_fact_count"] == 1
    assert audit["object_facts_complete"] is True


def test_t3_gold_accuracy_scores_only_t3_owned_core_action() -> None:
    gold_units, audit = build_t3_gold_upstream(
        signed_t2_standard(),
        packet=atomic_packet(),
        gold_source="standards/school/t2.standard.yaml",
        source_template_hash="sha256:template",
    )
    report = evaluate_t3_gold_accuracy(
        {
            "source_render_hash": "sha256:render",
            "input_contract_hash": "sha256:l1",
            "items": [
                {
                    "unit_id": "cover",
                    "policy": "fixed",
                    "raw_run_ids": ["p_0001.r_001"],
                },
                {
                    "unit_id": "body_main",
                    "policy": "fill",
                    "raw_run_ids": ["p_0002.r_001"],
                },
                {
                    "unit_id": "body_main",
                    "policy": "instruction_remove",
                    "raw_run_ids": ["word_header1_xml.p_0001.r_001"],
                },
            ]
        },
        t3_standard={
            "stage_id": "T3",
            "standard_id": "school-v1-t3",
            "standard_state": "signed_active",
            "accepted_source_facts": {
                "template_docx_sha256": "sha256:template"
            },
            "expected": {
                "core_action_contract": core_action_contract(),
                "run_span_ledger": [
                    {
                        "raw_run_id": "p_0001.r_001",
                        "source_seq": 1,
                        "unit_id": "cover",
                        "expected_action": "keep",
                    },
                    {
                        "raw_run_id": "p_0002.r_001",
                        "source_seq": 2,
                        "unit_id": "body_main",
                        "expected_action": "delete",
                    },
                    {
                        "raw_run_id": "word_header1_xml.p_0001.r_001",
                        "source_seq": 3,
                        "expected_action": "delete",
                    },
                ]
            },
        },
        packet=atomic_packet(),
        gold_unit_observation=gold_units,
        gold_input_audit=audit,
        source_template_hash="sha256:template",
    )

    assert report["metrics"]["gold_run_count"] == 2
    assert report["metrics"]["coverage"] == 1.0
    assert report["primary_metric"] == "exact_action_accuracy"
    assert report["metrics"]["exact_action_accuracy"] == 0.5
    assert report["metrics"]["per_action"]["keep"]["f1"] == 1.0
    assert report["metrics"]["per_action"]["fill"]["f1"] == 0.0
    assert report["metrics"]["per_action"]["delete"]["f1"] == 0.0
    assert report["metrics"]["deletion_safety"]["expected_delete_runs"] == 1
    assert report["metrics"]["deletion_safety"]["predicted_delete_runs"] == 0
    assert report["scope"]["excluded_non_body_raw_run_count"] == 1


def test_t3_gold_accuracy_ignores_subtype_and_same_action_grouping() -> None:
    gold_units, audit = build_t3_gold_upstream(
        signed_t2_standard(),
        packet=atomic_packet(),
        gold_source="standards/school/t2.standard.yaml",
        source_template_hash="sha256:template",
    )
    report = evaluate_t3_gold_accuracy(
        {
            "source_render_hash": "sha256:render",
            "input_contract_hash": "sha256:l1",
            "items": [
                {
                    "unit_id": "renamed_cover_group",
                    "policy": "template_default",
                    "raw_run_ids": ["p_0001.r_001"],
                },
                {
                    "unit_id": "first_fill_group",
                    "policy": "fill",
                    "raw_run_ids": ["p_0002.r_001"],
                },
                {
                    "unit_id": "second_fill_group",
                    "policy": "generated",
                    "raw_run_ids": ["p_0002.r_001"],
                },
            ],
        },
        t3_standard={
            "stage_id": "T3",
            "standard_id": "school-v1-t3",
            "standard_state": "signed_active",
            "accepted_source_facts": {
                "template_docx_sha256": "sha256:template",
            },
            "expected": {
                "core_action_contract": core_action_contract(),
                "run_span_ledger": [
                    {
                        "raw_run_id": "p_0001.r_001",
                        "source_seq": 1,
                        "unit_id": "cover",
                        "expected_action": "keep",
                    },
                    {
                        "raw_run_id": "p_0002.r_001",
                        "source_seq": 2,
                        "unit_id": "body_main",
                        "expected_action": "fill",
                    },
                ],
            },
        },
        packet=atomic_packet(),
        gold_unit_observation=gold_units,
        gold_input_audit=audit,
        source_template_hash="sha256:template",
    )

    assert report["metrics"]["exact_action_accuracy"] == 1.0
    assert report["metrics"]["conflicted_run_count"] == 0
    assert report["metrics"]["per_unit"]["cover"]["action_accuracy"] == 1.0
    assert report["metrics"]["per_unit"]["body_main"]["action_accuracy"] == 1.0


def test_t3_gold_accuracy_excludes_unknown_but_treats_delete_as_unsafe() -> None:
    gold_units, audit = build_t3_gold_upstream(
        signed_t2_standard(),
        packet=atomic_packet(),
        gold_source="standards/school/t2.standard.yaml",
        source_template_hash="sha256:template",
    )
    report = evaluate_t3_gold_accuracy(
        {
            "source_render_hash": "sha256:render",
            "input_contract_hash": "sha256:l1",
            "items": [
                {
                    "unit_id": "cover",
                    "policy": "fixed",
                    "raw_run_ids": ["p_0001.r_001"],
                },
                {
                    "unit_id": "body_main",
                    "policy": "instruction_remove",
                    "raw_run_ids": ["p_0002.r_001"],
                },
            ],
        },
        t3_standard={
            "stage_id": "T3",
            "standard_id": "school-v1-t3",
            "standard_state": "signed_active",
            "accepted_source_facts": {
                "template_docx_sha256": "sha256:template",
            },
            "expected": {
                "core_action_contract": core_action_contract(),
                "run_span_ledger": [
                    {
                        "raw_run_id": "p_0001.r_001",
                        "source_seq": 1,
                        "unit_id": "cover",
                        "expected_action": "keep",
                    },
                    {
                        "raw_run_id": "p_0002.r_001",
                        "source_seq": 2,
                        "unit_id": "body_main",
                        "expected_action": "unknown",
                    },
                ],
            },
        },
        packet=atomic_packet(),
        gold_unit_observation=gold_units,
        gold_input_audit=audit,
        source_template_hash="sha256:template",
    )

    assert report["metrics"]["gold_ledger_run_count"] == 2
    assert report["metrics"]["gold_run_count"] == 1
    assert report["metrics"]["excluded_unknown_gold_run_count"] == 1
    assert report["metrics"]["exact_action_accuracy"] == 1.0
    assert report["metrics"]["deletion_safety"]["false_delete_runs"] == 1
    assert report["metrics"]["deletion_safety"]["hard_gate_zero_false_delete"] is False
    assert report["scope"]["unknown_execution_fallback"] == "keep"


def test_t3_gold_accuracy_reports_mixed_span_actions_as_run_conflict() -> None:
    gold_units, audit = build_t3_gold_upstream(
        signed_t2_standard(),
        packet=atomic_packet(),
        gold_source="standards/school/t2.standard.yaml",
        source_template_hash="sha256:template",
    )
    report = evaluate_t3_gold_accuracy(
        {
            "source_render_hash": "sha256:render",
            "input_contract_hash": "sha256:l1",
            "items": [
                {
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
                                    "end": 1,
                                }
                            ],
                        },
                        {
                            "policy": "fill",
                            "char_ranges": [
                                {
                                    "raw_run_id": "p_0001.r_001",
                                    "start": 1,
                                    "end": 2,
                                }
                            ],
                        },
                    ],
                },
                {
                    "unit_id": "body_main",
                    "policy": "fill",
                    "raw_run_ids": ["p_0002.r_001"],
                },
            ],
        },
        t3_standard={
            "stage_id": "T3",
            "standard_id": "school-v1-t3",
            "standard_state": "signed_active",
            "accepted_source_facts": {
                "template_docx_sha256": "sha256:template",
            },
            "expected": {
                "core_action_contract": core_action_contract(),
                "run_span_ledger": [
                    {
                        "raw_run_id": "p_0001.r_001",
                        "source_seq": 1,
                        "unit_id": "cover",
                        "expected_action": "keep",
                    },
                    {
                        "raw_run_id": "p_0002.r_001",
                        "source_seq": 2,
                        "unit_id": "body_main",
                        "expected_action": "fill",
                    },
                ],
            },
        },
        packet=atomic_packet(),
        gold_unit_observation=gold_units,
        gold_input_audit=audit,
        source_template_hash="sha256:template",
    )

    assert report["scope"]["prediction_projection"] == "span_preferred_raw_run"
    assert report["metrics"]["exact_action_accuracy"] == 0.5
    assert report["metrics"]["conflicted_run_count"] == 1
    assert report["metrics"]["mixed_span_run_count"] == 1
    assert report["metrics"]["mixed_span_raw_run_ids"] == ["p_0001.r_001"]


def test_t3_gold_accuracy_rejects_without_passing_input_audit() -> None:
    with pytest.raises(T3GoldUpstreamError, match="passing gold input audit"):
        evaluate_t3_gold_accuracy(
            {"items": []},
            t3_standard={"stage_id": "T3", "standard_state": "signed_active"},
            packet=atomic_packet(),
            gold_unit_observation={"items": []},
            gold_input_audit={"status": "FAIL"},
            source_template_hash="sha256:template",
        )
