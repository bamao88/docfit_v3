from __future__ import annotations

from typing import Any

from docfit.harness.template_generation_judge_reports import (
    _add_common_route_accuracy,
    _evaluate_ai_element_accuracy,
    _evaluate_ai_layout_accuracy,
    _evaluate_ai_unit_accuracy,
    _evaluate_t3_route_accuracy,
    _evaluate_t4_route_output_contract,
)


def t2_standard(unit_order: list[str]) -> dict[str, Any]:
    return {
        "expected": {
            "unit_order": unit_order,
            "units": [
                {
                    "unit_id": unit_id,
                    "boundary": {"start_page": index, "end_page": index},
                }
                for index, unit_id in enumerate(unit_order, start=1)
            ],
        }
    }


def t3_standard(groups: dict[str, list[str]]) -> dict[str, Any]:
    return {"expected": {"policy_groups": groups}}


def unit_obs(unit_ids: list[str]) -> dict[str, Any]:
    return {
        "units": [
            {
                "unit_id": unit_id,
                "unit_name": unit_id,
                "boundary": {"start_page": index, "end_page": index},
            }
            for index, unit_id in enumerate(unit_ids, start=1)
        ]
    }


def element_obs(items: list[dict[str, Any]], demotions: int = 0) -> dict[str, Any]:
    return {
        "items": items,
        "quality_report": {"demotions": [{"check_id": "C-REQUIRED-FIELD"}] * demotions},
    }


def test_unit_stage_perfect_match() -> None:
    gold = ["cover", "toc", "body_main"]
    result = _evaluate_ai_unit_accuracy(unit_obs(gold), t2_standard(gold)["expected"])
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0
    assert result["order_exact_match"] is True
    assert result["missing_units"] == [] and result["extra_units"] == []


def test_unit_stage_missing_and_extra() -> None:
    gold = ["cover", "toc", "body_main"]
    ai = ["cover", "body_main", "appendix"]  # 漏 toc，多 appendix
    result = _evaluate_ai_unit_accuracy(unit_obs(ai), t2_standard(gold)["expected"])
    assert result["missing_units"] == ["toc"]
    assert result["extra_units"] == ["appendix"]
    assert result["recall"] == round(2 / 3, 4)
    assert result["order_exact_match"] is False


def test_unit_stage_keeps_unknown_unit_visible_in_accuracy() -> None:
    gold = ["cover", "toc"]
    result = _evaluate_ai_unit_accuracy(
        unit_obs(["cover", "toc", "unknown_unit"]),
        t2_standard(gold)["expected"],
    )
    assert result["precision"] == round(2 / 3, 4)
    assert result["extra_units"] == ["unknown_unit"]


def test_unit_stage_evaluates_page_boundary_accuracy() -> None:
    standard = {
        "unit_order": ["cover", "toc"],
        "units": [
            {
                "unit_id": "cover",
                "boundary": {"start_page": 1, "end_page": 2},
            },
            {
                "unit_id": "toc",
                "boundary": {"start_page": 3, "end_page": 4},
            },
        ],
    }
    obs = {
        "units": [
            {
                "unit_id": "cover",
                "unit_name": "封面",
                "boundary": {"start_page": 1, "end_page": 2},
            },
            {
                "unit_id": "toc",
                "unit_name": "目录",
                "boundary": {"start_page": 3, "end_page": 4},
            },
        ]
    }

    result = _evaluate_ai_unit_accuracy(obs, standard)
    page_eval = result["page_boundary_accuracy"]

    assert page_eval["page_boundary_evaluable"] is True
    assert page_eval["coverage"] == 1.0
    assert page_eval["exact_match_accuracy"] == 1.0
    assert page_eval["exact_match_count"] == 2
    assert page_eval["mismatch_count"] == 0


def test_element_stage_dominant_policy_accuracy() -> None:
    standard = t3_standard({"fixed_units": ["grade_form"], "fill_units": ["abstract_cn"]})
    # grade_form 主策略应 fixed（给 2 fixed + 1 fixed → 众数 fixed，对）
    # abstract_cn 应 fill，但 AI 给 instruction_remove（错）
    obs = element_obs(
        [
            {"unit_id": "grade_form", "policy": "fixed"},
            {"unit_id": "grade_form", "policy": "fixed"},
            {"unit_id": "grade_form", "policy": "fixed"},
            {"unit_id": "abstract_cn", "policy": "instruction_remove"},
        ]
    )
    result = _evaluate_ai_element_accuracy(obs, standard["expected"])
    assert result["units_evaluated"] == 2
    assert result["unit_dominant_policy_accuracy"] == 0.5  # 1/2 众数对
    # grade_form 有 fixed（定性策略出现）；abstract_cn 只有 instruction_remove（fill 没出现）
    assert result["distinguishing_policy_recall"] == 0.5
    assert [m["unit_id"] for m in result["policy_mismatches"]] == ["abstract_cn"]
    assert result["element_expectation_eval"]["status"] == "NOT_AVAILABLE"


def test_element_stage_reports_element_expectation_overlap_metrics() -> None:
    standard = {
        "expected": {
            "policy_groups": {"fill_units": ["cover"]},
            "element_expectations": [
                {
                    "unit_id": "cover",
                    "name": "中文题名",
                    "policy": "fill",
                    "source_seq_refs": [6],
                },
                {
                    "unit_id": "cover",
                    "name": "格式说明",
                    "policy": "instruction_remove",
                    "source_seq_refs": [6],
                },
                {
                    "unit_id": "cover",
                    "name": "提交日期",
                    "policy": "fixed",
                    "source_seq_refs": [16],
                },
            ],
        }
    }
    obs = element_obs(
        [
            {
                "element_id": "cover.1",
                "unit_id": "cover",
                "policy": "fill",
                "source_seq_refs": [6],
            },
            {
                "element_id": "cover.2",
                "unit_id": "cover",
                "policy": "fixed",
                "source_seq_refs": [16],
            },
        ]
    )

    result = _evaluate_ai_element_accuracy(obs, standard["expected"])
    element_eval = result["element_expectation_eval"]
    assert element_eval["status"] == "AVAILABLE"
    assert element_eval["expectation_count"] == 3
    assert element_eval["source_overlap_count"] == 3
    assert element_eval["policy_match_count"] == 2
    assert element_eval["policy_mismatch_count"] == 1
    assert element_eval["missing_count"] == 0
    assert element_eval["source_policy_overlap_accuracy"] == round(2 / 3, 4)


def test_element_stage_required_field_compliance() -> None:
    standard = t3_standard({"fill_units": ["abstract_cn"]})
    obs = element_obs([{"unit_id": "abstract_cn", "policy": "fill"}] * 3, demotions=1)
    # 3 accepted + 1 required-field 降级 → 合规率 3/4
    result = _evaluate_ai_element_accuracy(obs, standard["expected"])
    assert result["required_field_compliance"] == 0.75


def test_layout_stage_does_not_evaluate_unit_page_policy() -> None:
    r = _evaluate_ai_layout_accuracy(
        {
            "items": [{"source": "deterministic_facts"}],
            "page_map": {"1": 1, "2": 2},
            "page_count": 2,
            "page_structure_source": "deterministic_pdf_layout",
            "page_observations": [{"page_no": 1, "page_number_visible": True}],
        },
        {"items": [{"unit_id": "cover", "source_seq_refs": [1]}]},
        {"layout_policy": {"standalone_units": ["cover"]}},
    )
    assert r["global_profile_present"] is True
    assert r["page_policy_evaluable"] is False
    assert r["page_policy_owner"] == "T2"
    assert r["vision_page_observation_count"] == 1


def test_t2_route_evaluator_scores_only_canonical_ai_final(tmp_path) -> None:
    path = tmp_path / "ai.yaml"
    import yaml

    path.write_text(
        yaml.safe_dump({"units": [{"unit_id": "cover"}, {"unit_id": "toc"}]}),
        encoding="utf-8",
    )
    paths = {
        "ai": {
            "availability": "AVAILABLE",
            "payload_path": str(path),
            "payload_type": "yaml",
        }
    }

    metrics = {}
    _add_common_route_accuracy(
        metrics,
        paths,
        stage_id="T2",
        expected={"unit_order": ["cover", "toc"]},
    )

    assert metrics["ai_accuracy"]["scoring_contract"] == "t2_common_route_v1"
    assert metrics["ai_accuracy"]["f1"] == 1.0
    assert "code_raw_accuracy" not in metrics
    assert "merged_accuracy" not in metrics


def test_t3_common_evaluator_penalizes_missing_gold_for_every_route() -> None:
    expected = {
        "run_span_ledger": [
            {"raw_run_id": "r1", "expected_action": "keep"},
            {"raw_run_id": "r2", "expected_action": "delete"},
        ]
    }
    ai = {
        "items": [
            {
                "core_action": "keep",
                "policy": "fixed",
                "raw_run_ids": ["r1"],
            },
        ]
    }
    canonical = {
        "elements": [
            {"policy": "fixed", "raw_run_ids": ["r1"]},
            {"policy": "instruction_remove", "raw_run_ids": ["r2"]},
        ]
    }

    ai_result = _evaluate_t3_route_accuracy(ai, expected)
    canonical_result = _evaluate_t3_route_accuracy(canonical, expected)

    assert ai_result["gold_count"] == canonical_result["gold_count"] == 2
    assert ai_result["coverage"] == 0.5
    assert ai_result["exact_action_accuracy"] == 0.5
    assert canonical_result["coverage"] == 1.0
    assert canonical_result["exact_action_accuracy"] == 1.0


def test_t3_common_evaluator_collapses_same_action_spans_for_one_raw_run() -> None:
    expected = {
        "run_span_ledger": [
            {"raw_run_id": "r1", "expected_action": "fill"},
        ]
    }
    candidate = {
        "elements": [
            {
                "policy": "fixed",
                "raw_run_ids": ["r1"],
                "run_text_length": 6,
                "spans": [
                    {
                        "span_type": "sample_value",
                        "policy": "fill",
                        "raw_run_ids": ["r1"],
                        "char_ranges": [
                            {"raw_run_id": "r1", "start": 0, "end": 2},
                        ],
                    },
                    {
                        "span_type": "sample_value",
                        "policy": "fill",
                        "raw_run_ids": ["r1"],
                        "char_ranges": [
                            {"raw_run_id": "r1", "start": 2, "end": 6},
                        ],
                    },
                ],
            }
        ]
    }

    result = _evaluate_t3_route_accuracy(candidate, expected)

    assert result["exact_action_accuracy"] == 1.0
    assert result["match_count"] == 1
    assert result["mixed_action_count"] == 0
    assert result["mismatch_samples"] == []


def test_t3_common_evaluator_reports_mixed_span_actions_for_one_raw_run() -> None:
    expected = {
        "run_span_ledger": [
            {"raw_run_id": "r1", "expected_action": "fill"},
        ]
    }
    candidate = {
        "elements": [
            {
                "policy": "fixed",
                "raw_run_ids": ["r1"],
                "spans": [
                    {
                        "span_type": "label",
                        "policy": "fixed",
                        "raw_run_ids": ["r1"],
                    },
                    {
                        "span_type": "sample_value",
                        "policy": "fill",
                        "raw_run_ids": ["r1"],
                    },
                ],
            }
        ]
    }

    result = _evaluate_t3_route_accuracy(candidate, expected)

    assert result["exact_action_accuracy"] == 0.0
    assert result["match_count"] == 0
    assert result["mismatch_count"] == 1
    assert result["mixed_action_count"] == 1
    assert result["conflicted_run_count"] == 1
    assert result["mixed_action_samples"] == [
        {
            "expected_action": "fill",
            "actual_actions": ["fill", "keep"],
                "status": "mixed",
                "raw_run_id": "r1",
                "target_kind": "run",
            }
    ]


def test_t3_common_evaluator_does_not_expand_partial_span_to_whole_run() -> None:
    expected = {
        "run_span_ledger": [
            {"raw_run_id": "r1", "expected_action": "fill"},
        ]
    }
    candidate = {
        "elements": [
            {
                "policy": "fixed",
                "raw_run_ids": ["r1"],
                "run_text_length": 6,
                "spans": [
                    {
                        "policy": "fill",
                        "raw_run_ids": ["r1"],
                        "char_ranges": [
                            {"raw_run_id": "r1", "start": 0, "end": 2},
                        ],
                    }
                ],
            }
        ]
    }

    result = _evaluate_t3_route_accuracy(candidate, expected)

    assert result["exact_action_accuracy"] == 0.0
    assert result["conflicted_run_count"] == 1
    assert result["mixed_action_samples"][0]["actual_actions"] == ["fill", "keep"]


def test_t3_common_evaluator_scores_adaptive_span_gold_independently() -> None:
    expected = {
        "run_span_ledger": [
            {
                "target_kind": "span",
                "raw_run_id": "r1",
                "start": 0,
                "end": 2,
                "text": "标签",
                "expected_action": "keep",
            },
            {
                "target_kind": "span",
                "raw_run_id": "r1",
                "start": 2,
                "end": 4,
                "text": "示例",
                "expected_action": "fill",
            },
        ]
    }
    candidate = {
        "elements": [
            {
                "policy": "fixed",
                "raw_run_ids": ["r1"],
                "run_text_length": 4,
                "spans": [
                    {
                        "policy": "fixed",
                        "char_ranges": [
                            {"raw_run_id": "r1", "start": 0, "end": 2},
                        ],
                    },
                    {
                        "policy": "fill",
                        "char_ranges": [
                            {"raw_run_id": "r1", "start": 2, "end": 4},
                        ],
                    },
                ],
            }
        ]
    }

    result = _evaluate_t3_route_accuracy(candidate, expected)

    assert result["gold_count"] == 2
    assert result["match_count"] == 2
    assert result["coverage"] == 1.0
    assert result["exact_action_accuracy"] == 1.0


def test_t4_ai_final_requires_the_global_spec_contract(tmp_path) -> None:
    import yaml

    path = tmp_path / "ai.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "artifact_type": "global_spec",
                "section_profiles": [],
                "default_font": None,
                "page_numbering": {"status": "unknown"},
                "header_footer": [],
                "numbering_rules": {"definitions": [], "refs": []},
                "flags": [],
            }
        ),
        encoding="utf-8",
    )
    routes = {
        "ai": {
            "availability": "AVAILABLE",
            "payload_path": str(path),
        }
    }

    contract, mismatches = _evaluate_t4_route_output_contract(routes)

    assert contract["status"] == "PASS"
    assert {result["artifact_type"] for result in contract["routes"].values()} == {
        "global_spec"
    }
    assert mismatches == []
