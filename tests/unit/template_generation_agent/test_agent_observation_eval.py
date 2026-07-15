from __future__ import annotations

from typing import Any

from docfit.harness.template_generation_judge_reports import (
    _evaluate_ai_element_accuracy,
    _evaluate_ai_layout_accuracy,
    _evaluate_ai_unit_accuracy,
)


def t2_standard(unit_order: list[str]) -> dict[str, Any]:
    return {"expected": {"unit_order": unit_order}}


def t3_standard(groups: dict[str, list[str]]) -> dict[str, Any]:
    return {"expected": {"policy_groups": groups}}


def unit_obs(unit_ids: list[str]) -> dict[str, Any]:
    return {"items": [{"unit_id": u} for u in unit_ids]}


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


def test_unit_stage_ignores_unknown_unit() -> None:
    gold = ["cover", "toc"]
    result = _evaluate_ai_unit_accuracy(
        unit_obs(["cover", "toc", "unknown_unit"]),
        t2_standard(gold)["expected"],
    )
    assert result["precision"] == 1.0
    assert result["extra_units"] == []


def test_element_stage_dominant_policy_accuracy() -> None:
    standard = t3_standard({"manual_only_units": ["grade_form"], "fill_units": ["abstract_cn"]})
    # grade_form 主策略应 manual_only（给 2 manual_only + 1 fixed → 众数 manual_only，对）
    # abstract_cn 应 fill，但 AI 给 instruction_remove（错）
    obs = element_obs(
        [
            {"unit_id": "grade_form", "policy": "manual_only"},
            {"unit_id": "grade_form", "policy": "manual_only"},
            {"unit_id": "grade_form", "policy": "fixed"},
            {"unit_id": "abstract_cn", "policy": "instruction_remove"},
        ]
    )
    result = _evaluate_ai_element_accuracy(obs, standard["expected"])
    assert result["units_evaluated"] == 2
    assert result["unit_dominant_policy_accuracy"] == 0.5  # 1/2 众数对
    # grade_form 有 manual_only（定性策略出现）；abstract_cn 只有 instruction_remove（fill 没出现）
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
                    "policy": "manual_only",
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
    assert element_eval["policy_match_count"] == 1
    assert element_eval["policy_mismatch_count"] == 2
    assert element_eval["missing_count"] == 0
    assert element_eval["source_policy_overlap_accuracy"] == round(1 / 3, 4)


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
