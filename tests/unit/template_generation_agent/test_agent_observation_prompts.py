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
from docfit.template_generation.agent.observation_schema import open_questions_from
from docfit.template_generation.constants import UNIT_DEFINITIONS


def clean_evidence(stage: str) -> dict[str, Any]:
    return {"scope": stage, "source_render_hash": "sha256:x", "rows": []}


def test_t2_glossary_carries_unit_names_and_aliases() -> None:
    # C1：欠分割的根因是 prompt 只给裸 unit_id；glossary 必须带名+别名。
    glossary = build_observation_prompt(stage="t2", evidence_view=clean_evidence("t2"))["glossary"]
    # 之前 thinking-off 漏掉的单元，其别名关键词必须出现在词典里。
    for unit_id in ("abstract_cn", "references", "acknowledgement", "appendix", "body_title_block"):
        assert unit_id in glossary, unit_id
    names = {definition[1] for definition in UNIT_DEFINITIONS}
    assert "中文摘要" in names and "中文摘要" in glossary
    # 别名样例
    assert "参考文献" in glossary


def test_t3_rubric_is_decision_tree_with_required_fields_at_leaf() -> None:
    # C2：决策树必须把 6 个 policy 和必填规则都写到叶子。
    rubric = build_observation_prompt(stage="t3", evidence_view=clean_evidence("t3"))["rubric"]
    for policy in ("instruction_remove", "fixed", "template_default", "fill", "generated", "manual_only"):
        assert policy in rubric, policy
    assert "fill_source" in rubric
    assert "field_type" in rubric
    assert "manual_semantics" in rubric


def test_t3_prompt_required_fields_mirror_the_gate() -> None:
    # 防 prompt 与物化闸门漂移：闸门 _required_field_error 强制的 (policy, field)
    # 必须在 prompt（rubric+contract）里成对出现，否则模型被要求做闸门会拒的事。
    prompt = build_observation_prompt(stage="t3", evidence_view=clean_evidence("t3"))
    text = prompt["rubric"] + OUTPUT_CONTRACT["t3"]
    for policy, field in (("fill", "fill_source"), ("generated", "field_type"), ("manual_only", "manual_semantics")):
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
        policy_decision_tree="CUSTOM TREE",
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
    glossary = build_observation_prompt(stage="t3", evidence_view=clean_evidence("t3"))["glossary"]
    assert "manual_only" in glossary
    assert "fill_source" in glossary


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
    assert "bad_result" in system and "excellent_result" in system
    assert "不要把标签和值合并" in system or "固定标签" in system
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
