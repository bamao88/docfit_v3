from __future__ import annotations

from typing import Any

import pytest

from docfit.template_generation.agent.evidence import EvidenceFirewallError
from docfit.template_generation.agent.observation_prompts import (
    ObservationPromptTemplates,
    OUTPUT_CONTRACT,
    assemble_observation_messages,
    build_observation_prompt,
)
from docfit.template_generation.agent.observation_multimodal import attachment_refs
from docfit.template_generation.agent.observation_schema import open_questions_from


def clean_evidence(stage: str) -> dict[str, Any]:
    return {"scope": stage, "source_render_hash": "sha256:x", "rows": []}


def test_t2_prompt_does_not_inject_unit_dictionary() -> None:
    prompt = build_observation_prompt(stage="t2", evidence_view=clean_evidence("t2"))
    system, _ = assemble_observation_messages("t2", clean_evidence("t2"))

    assert prompt["glossary"] == ""
    assert "词典（领域先验" not in system
    assert "参考下方单元词典" not in system
    assert "- cover (封面)" not in system
    assert "你在做 T2" not in system
    assert "不要把任务做成关键词分类" not in system
    assert "T2 的目标" in system
    assert "执行流程" in system
    assert "不需要输出 order" in system
    assert "拆分/合并工作流" in system
    assert "典型正确标准" in system
    assert "典型错误标准" in system
    assert "目录条目" in system
    assert "格式说明" in system
    assert "允许标签集" in system


def test_t3_rubric_is_decision_tree_with_required_fields_at_leaf() -> None:
    # C2：决策树必须把可执行 policy 和必填规则都写到叶子。
    rubric = build_observation_prompt(stage="t3", evidence_view=clean_evidence("t3"))["rubric"]
    for policy in ("instruction_remove", "fixed", "template_default", "fill", "generated"):
        assert policy in rubric, policy
    assert "fill_source" in rubric
    assert "field_type" in rubric
    assert "manual_only" not in rubric


def test_t3_prompt_required_fields_mirror_the_gate() -> None:
    # 防 prompt 与物化闸门漂移：闸门 _required_field_error 强制的 (policy, field)
    # 必须在 prompt（rubric+contract）里成对出现，否则模型被要求做闸门会拒的事。
    prompt = build_observation_prompt(stage="t3", evidence_view=clean_evidence("t3"))
    text = prompt["rubric"] + OUTPUT_CONTRACT["t3"]
    for policy, field in (("fill", "fill_source"), ("generated", "field_type")):
        assert policy in text and field in text, (policy, field)
    assert "raw_run_ids" in text
    assert "logical_run_ids" in text
    assert "不要整段合并" in text


def test_build_prompt_still_firewalls_evidence() -> None:
    # 注入 glossary 不能放松 evidence 子树的防火墙。
    with pytest.raises(EvidenceFirewallError):
        build_observation_prompt(
            stage="t2",
            evidence_view={"rows": [{"source_seq": 1, "unit_map": {"unit_id": "cover"}}]},
        )


def test_prompt_templates_are_explicit_parameters() -> None:
    templates = ObservationPromptTemplates(
        system="SYSTEM $rubric :: $output_contract :: $allowed_labels_json",
        rubrics={"t2": "CUSTOM T2 RUBRIC"},
        output_contracts={"t2": "CUSTOM T2 CONTRACT"},
        t4_page_vision="PAGE $page_no $layout_context",
    )
    prompt = build_observation_prompt(
        stage="t2",
        evidence_view=clean_evidence("t2"),
        prompt_templates=templates,
    )
    system, user = assemble_observation_messages(
        "t2",
        clean_evidence("t2"),
        prompt_templates=templates,
    )

    assert prompt["rubric"] == "CUSTOM T2 RUBRIC"
    assert prompt["output_contract"] == "CUSTOM T2 CONTRACT"
    assert "CUSTOM T2 RUBRIC" in system
    assert "CUSTOM T2 CONTRACT" in system
    assert user.startswith("{")


def test_t3_glossary_defines_policies() -> None:
    prompt = build_observation_prompt(stage="t3", evidence_view=clean_evidence("t3"))
    glossary = prompt["glossary"]
    assert "manual_only" not in glossary
    assert "fill_source" in glossary
    assert "unknown" not in prompt["allowed_labels"]["policies"]
    assert "- unknown:" not in glossary


def test_t3_prompt_maps_mixed_or_uncertain_run_to_keep_not_unknown() -> None:
    evidence = clean_evidence("t3")
    prompt = build_observation_prompt(stage="t3", evidence_view=evidence)
    system, _ = assemble_observation_messages("t3", evidence)

    assert prompt["allowed_labels"]["core_actions"] == ["keep", "fill", "delete"]
    assert "unit_ids" not in prompt["allowed_labels"]
    assert "unknown_unit" not in system
    assert prompt["abstain_is_valid"] is False
    assert "run 是最小判断单位" in prompt["rubric"]
    assert "元素如何分组、合并或统一执行不属于本次判断" in prompt["rubric"]
    assert "core_action=keep、policy=fixed" in prompt["output_contract"]
    assert "不得输出 unknown" in prompt["output_contract"]
    assert "preserve → core_action=keep → policy=fixed" in prompt["rubric"]
    assert "T3 对当前窗口内已经绑定的 run 不得弃权" in system


def test_t3_prompt_classifies_independent_fill_runs_inside_protected_structure() -> None:
    prompt = build_observation_prompt(stage="t3", evidence_view=clean_evidence("t3"))

    assert "固定标签和相邻占位属于不同 raw run 时，标签 keep、占位 fill" in prompt["rubric"]
    assert "不能机械复制默认 policy" in prompt["rubric"]


def test_t3_unit_prompt_descends_when_form_contains_electronic_fields() -> None:
    prompt = build_observation_prompt(
        stage="t3_unit",
        evidence_view=clean_evidence("t3_unit"),
    )

    assert "必须使用 preserve_structure_classify_fields" in prompt["rubric"]
    assert "没有任何需要电子替换或系统生成的独立 raw run" in prompt["rubric"]


def test_t3_specific_prompt_has_one_source_file() -> None:
    from importlib import resources

    prompt_dir = resources.files(
        "docfit.template_generation.agent"
    ).joinpath("prompt_templates")

    assert prompt_dir.joinpath("t3_prompt.txt").is_file()
    assert not prompt_dir.joinpath("t3_rubric.txt").is_file()
    assert not prompt_dir.joinpath("t3_policy_decision_tree.txt").is_file()
    assert not prompt_dir.joinpath("t3_output_contract.txt").is_file()


def test_t3_prompt_teaches_quality_with_selected_positive_and_negative_examples() -> None:
    evidence = {
        "scope": "t3_local_window",
        "source_render_hash": "sha256:x",
        "object_overview": {"object_type": "table", "object_id": "tbl_001"},
        "unit_plan": {"route": "inspect_suspected_regions"},
        "rows": [{"source_seq": 1, "text": "学生姓名"}],
    }
    prompt = build_observation_prompt(stage="t3", evidence_view=evidence)
    system, _ = assemble_observation_messages("t3", evidence)

    assert "高质量学校模板" in prompt["quality_goal"]
    assert 1 <= len(prompt["exemplars"]) <= 3
    assert any(item["exemplar_id"] == "two_column_field_table" for item in prompt["exemplars"])
    assert any(item["exemplar_id"] == "indivisible_mixed_run_keep" for item in prompt["exemplars"])
    assert "bad_result" in system and "excellent_result" in system
    assert '"core_action": "keep"' in system
    assert "不要把标签和值合并" in system or "固定标签" in system


def test_t3_delete_refinement_loads_only_delete_examples_with_near_miss() -> None:
    evidence = {
        **clean_evidence("t3"),
        "scope": "t3_action_refinement",
        "refinement_action": "delete",
        "candidate_items": [{"element_id": "cover.1", "core_action": "delete"}],
    }
    prompt = build_observation_prompt(stage="t3", evidence_view=evidence)
    system, _ = assemble_observation_messages("t3", evidence)

    assert prompt["exemplars"]
    assert all(item["example_id"].startswith("delete.") for item in prompt["exemplars"])
    assert any(item["example_id"] == "delete.near_miss_content_guidance" for item in prompt["exemplars"])
    assert "不要因为进入 Delete 分支就强行确认删除" in system
    assert "fill.placeholder_minimum_span" not in system


def test_t3_fill_refinement_loads_only_fill_examples() -> None:
    evidence = {
        **clean_evidence("t3"),
        "scope": "t3_action_refinement",
        "refinement_action": "fill",
        "candidate_items": [{"element_id": "cover.1", "core_action": "fill"}],
    }
    prompt = build_observation_prompt(stage="t3", evidence_view=evidence)
    system, _ = assemble_observation_messages("t3", evidence)

    assert prompt["exemplars"]
    assert all(item["example_id"].startswith("fill.") for item in prompt["exemplars"])
    assert "真正需要替换的最小范围" in system
    assert "delete.inline_format_annotation" not in system
def test_t3_unit_prompt_routes_whole_unit_before_local_policy() -> None:
    evidence = {
        "scope": "t3_unit_overview",
        "source_render_hash": "sha256:x",
        "unit_scope": {"t2_scope_label": "integrity_statement", "source_seq_refs": [1, 2]},
        "unit_overview": {"objects": []},
        "routing_options": [],
    }
    system, user = assemble_observation_messages("t3_unit", evidence)

    assert "preserve_whole" in system
    assert "inspect_suspected_regions" in system
    assert "错误删除比漏删更严重" in system
    assert "bad_plan" in system and "excellent_plan" in system
    assert '"t2_scope_label": "integrity_statement"' in user


def test_prompt_hides_private_visual_attachment_paths() -> None:
    evidence = {
        "scope": "t3_unit_overview",
        "source_render_hash": "sha256:x",
        "unit_scope": {"t2_scope_label": "cover"},
        "visual_evidence": [
            {
                "visual_ref": "page:1",
                "page_no": 1,
                "_attachment_path": "/private/tmp/page.png",
            }
        ],
    }
    _, user = assemble_observation_messages("t3_unit", evidence)
    assert "page:1" in user
    assert "_attachment_path" not in user
    assert "/private/tmp/page.png" not in user


def test_t2_prompt_hides_visual_attachment_paths_and_keeps_refs() -> None:
    evidence = {
        "scope": "t2_full_document",
        "source_render_hash": "sha256:x",
        "_visual_attachment_limit": 2,
        "visual_evidence": [
            {
                "visual_ref": "page:1",
                "page_no": 1,
                "sha256": "sha256:page-1",
                "_attachment_path": "/private/tmp/page-01.png",
            },
            {
                "visual_ref": "page:2",
                "page_no": 2,
                "sha256": "sha256:page-2",
                "_attachment_path": "/private/tmp/page-02.png",
            },
        ],
    }

    _, user = assemble_observation_messages("t2", evidence)

    assert "page:1" in user and "page:2" in user
    assert "_attachment_path" not in user
    assert "_visual_attachment_limit" not in user
    assert "/private/tmp" not in user
    assert attachment_refs(evidence) == ["page:1", "page:2"]


def test_assemble_messages_shared_by_providers() -> None:
    # Kimi/MiniMax 共用同一份 (system, user)；system 含 rubric+词典+契约，user 是 evidence。
    system, user = assemble_observation_messages("t3", clean_evidence("t3"))
    assert "决策树" not in system  # 只检查结构：任务/词典/契约都在
    assert "任务：" in system and "词典" in system and "输出契约：" in system
    assert "fill_source" in system  # T3 契约的必填规则
    assert user.startswith("{") and "t3" in user


def test_assemble_messages_firewalls_evidence() -> None:
    with pytest.raises(EvidenceFirewallError):
        assemble_observation_messages("t2", {"rows": [{"unit_map": {"unit_id": "cover"}}]})


def test_open_questions_surface_contested_unknown_and_low_consistency() -> None:
    oq = open_questions_from(
        demotions=[
            {"item_id": "94", "check_id": "C-COVERAGE-CONTESTED", "reason": "tie"},
            {"item_id": "x.1", "check_id": "C-REQUIRED-FIELD", "reason": "noise; should be ignored"},
        ],
        coverage={"unknown_source_seq": [5, 6, 7, 20]},
        self_consistency={"agreement": {"16": 0.4, "17": 1.0}},
    )
    checks = {q["check_id"] for q in oq}
    assert "C-COVERAGE-CONTESTED" in checks
    assert "C-SELF-CONSISTENCY" in checks
    assert "C-COVERAGE-UNKNOWN" in checks
    # routine 的 required-field 降级不应制造 open_question。
    assert "C-REQUIRED-FIELD" not in checks
    # 未认领簇按连续段聚合：5-7 一条 + 20 一条。
    unknown_q = [q for q in oq if q["check_id"] == "C-COVERAGE-UNKNOWN"]
    assert len(unknown_q) == 2


def test_open_questions_empty_when_clean() -> None:
    oq = open_questions_from(
        demotions=[{"item_id": "x.1", "check_id": "C-LABEL-CLOSURE", "reason": "fixed by gate"}],
        coverage={"unknown_source_seq": []},
        self_consistency={"agreement": {"1": 1.0}},
    )
    assert oq == []
