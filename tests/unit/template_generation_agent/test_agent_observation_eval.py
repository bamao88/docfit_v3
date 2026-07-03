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


def test_layout_page_policy_not_evaluable_without_render() -> None:
    r = evaluate_layout_stage(
        {"items": [{"source": "deterministic_facts"}]}, {"items": []}, {}
    )
    assert r["global_profile_present"] is True
    assert r["page_policy_evaluable"] is False


def test_layout_page_isolation_accuracy_vs_gold() -> None:
    # cover 独占 page1；abstract_cn + abstract_en 共享 page2（flowing）。
    layout = {
        "items": [{"source": "deterministic_facts"}],
        "page_map": {"1": 1, "2": 1, "3": 2, "4": 2},
        "page_count": 2,
    }
    units = {
        "items": [
            {"unit_id": "cover", "source_seq_refs": [1, 2]},
            {"unit_id": "abstract_cn", "source_seq_refs": [3]},
            {"unit_id": "abstract_en", "source_seq_refs": [4]},
        ]
    }
    std = {
        "expected": {
            "layout_policy": {
                "standalone_units": ["cover"],
                "flowing_units": ["abstract_cn", "abstract_en"],
            }
        }
    }
    r = evaluate_layout_stage(layout, units, std)
    assert r["page_policy_evaluable"] is True
    assert r["units_evaluated"] == 3
    assert r["page_isolation_accuracy"] == 1.0
    assert r["page_policy_mismatches"] == []


def test_layout_page_isolation_from_vision_units_no_t2() -> None:
    # 视觉逐页 unit_hint(中文) → unit_id，独立于 Kimi 的 T2 算页隔离。
    layout = {
        "items": [{"source": "deterministic_facts"}],
        "page_count": 3,
        "page_observations": [
            {"page_no": 1, "unit_hint": "封面"},
            {"page_no": 2, "unit_hint": "目录"},
            {"page_no": 3, "unit_hint": "目录"},
        ],
    }
    std = {"expected": {"layout_policy": {"standalone_units": ["cover", "toc"], "flowing_units": []}}}
    r = evaluate_layout_stage(layout, {"items": []}, std)  # 无 T2 单元
    assert r["unit_pages_source"] == "vision_page_units"
    assert r["page_policy_evaluable"] is True
    assert r["page_isolation_accuracy"] == 1.0  # cover 独占 p1，toc 独占 p2-3


def test_layout_page_policy_mismatch_becomes_open_question() -> None:
    # cover 与 toc 挤在 page1 → cover 实测 flowing，但 gold 要 standalone → mismatch + open_question。
    layout = {"items": [{"source": "deterministic_facts"}], "page_map": {"1": 1, "2": 1}}
    units = {
        "items": [
            {"unit_id": "cover", "source_seq_refs": [1]},
            {"unit_id": "toc", "source_seq_refs": [2]},
        ]
    }
    std = {"expected": {"layout_policy": {"standalone_units": ["cover", "toc"], "flowing_units": []}}}
    r = evaluate_layout_stage(layout, units, std)
    assert r["page_isolation_accuracy"] == 0.0
    assert {q["check_id"] for q in r["open_questions"]} == {"C-LAYOUT-PAGE-POLICY"}
