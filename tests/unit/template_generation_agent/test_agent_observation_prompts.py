from __future__ import annotations

from typing import Any

import pytest

from docfit.template_generation.agent.evidence import EvidenceFirewallError
from docfit.template_generation.agent.observation_prompts import (
    OUTPUT_CONTRACT,
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


def test_build_prompt_still_firewalls_evidence() -> None:
    # 注入 glossary 不能放松 evidence 子树的防火墙。
    with pytest.raises(EvidenceFirewallError):
        build_observation_prompt(
            stage="t2",
            evidence_view={"rows": [{"source_seq": 1, "unit_map": {"unit_id": "cover"}}]},
        )


def test_t3_glossary_defines_policies() -> None:
    glossary = build_observation_prompt(stage="t3", evidence_view=clean_evidence("t3"))["glossary"]
    assert "manual_only" in glossary
    assert "fill_source" in glossary


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
