from __future__ import annotations

from typing import Any

from docfit.template_generation.agent.observation_eval import (
    evaluate_element_stage,
    evaluate_layout_stage,
    evaluate_unit_stage,
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
    result = evaluate_unit_stage(unit_obs(gold), t2_standard(gold))
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0
    assert result["order_exact_match"] is True
    assert result["missing_units"] == [] and result["extra_units"] == []


def test_unit_stage_missing_and_extra() -> None:
    gold = ["cover", "toc", "body_main"]
    ai = ["cover", "body_main", "appendix"]  # 漏 toc，多 appendix
    result = evaluate_unit_stage(unit_obs(ai), t2_standard(gold))
    assert result["missing_units"] == ["toc"]
    assert result["extra_units"] == ["appendix"]
    assert result["recall"] == round(2 / 3, 4)
    assert result["order_exact_match"] is False


def test_unit_stage_ignores_unknown_unit() -> None:
    gold = ["cover", "toc"]
    result = evaluate_unit_stage(unit_obs(["cover", "toc", "unknown_unit"]), t2_standard(gold))
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
    result = evaluate_element_stage(obs, standard)
    assert result["units_evaluated"] == 2
    assert result["unit_dominant_policy_accuracy"] == 0.5  # 1/2 众数对
    # grade_form 有 manual_only（定性策略出现）；abstract_cn 只有 instruction_remove（fill 没出现）
    assert result["distinguishing_policy_recall"] == 0.5
    assert [m["unit_id"] for m in result["policy_mismatches"]] == ["abstract_cn"]


def test_element_stage_required_field_compliance() -> None:
    standard = t3_standard({"fill_units": ["abstract_cn"]})
    obs = element_obs([{"unit_id": "abstract_cn", "policy": "fill"}] * 3, demotions=1)
    # 3 accepted + 1 required-field 降级 → 合规率 3/4
    result = evaluate_element_stage(obs, standard)
    assert result["required_field_compliance"] == 0.75


def test_layout_stage_reports_abstain() -> None:
    assert evaluate_layout_stage({"abstain": True}, {})["evaluable"] is False
    assert evaluate_layout_stage({"abstain": False, "items": [{}]}, {})["evaluable"] is True
