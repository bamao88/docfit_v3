"""Module 1 prompt 装配：taxonomy/枚举接地 + 分解式 rubric + 防火墙复核。

replay 路径不调模型，但 prompt 装配仍是架构的一等部分：它把 clean evidence 视图与
允许标签集（24 unit / 6 policy，作为领域先验注入，非 gold）拼成 payload，并在装配后
再跑一次 ``assert_firewall_clean``——确保送进模型的 evidence 子树没有代码结论字段。
"""

from __future__ import annotations

from typing import Any

from .evidence import assert_firewall_clean
from .observation_schema import (
    ALLOWED_FIELD_TYPES,
    ALLOWED_POLICIES,
    ALLOWED_UNIT_IDS,
    PROMPT_CONTRACT_VERSION,
)

ALLOWED_LABELS = {
    "unit_ids": sorted(ALLOWED_UNIT_IDS),
    "policies": sorted(ALLOWED_POLICIES),
    "generated_field_types": sorted(ALLOWED_FIELD_TYPES),
}

_RUBRIC = {
    "t2": (
        "只依据给定的 Word 事实，把每个 source_seq 归到一个 unit_id（或 unknown_unit）。"
        "不确定就用 unknown_unit 并降低 confidence。每个判断必须给 source_seq_refs。"
    ),
    "t3": (
        "在本单元窗口内，为每个元素判定 policy（6 枚举之一）。"
        "fill 必给 fill_source；generated 必给 field_type；manual_only 必给 manual_semantics。"
        "回报 ai_decision_path 说明判定依据。"
    ),
    "t4": (
        "只在拿到真实页图时判定 section/页眉脚/页码/版式；拿不到页图就 abstain，不要猜。"
        "每条 section 边界必须带 page_no + render_target 的 evidence_refs。"
    ),
}

# 模型必须严格返回的 JSON 形状（live 路径解析依据）。
OUTPUT_CONTRACT = {
    "t2": (
        '返回 JSON 对象：{"items":[{"unit_id":"<taxonomy 之一或 unknown_unit>",'
        '"source_seq_refs":[<int>],"confidence":"low|medium|high",'
        '"name":"<可选>","ai_rationale":"<可选>"}]}。'
        "只输出 JSON，不要解释文字。无把握的 source_seq 不要硬塞，留给 unknown_unit。"
    ),
    "t3": (
        '返回 JSON 对象：{"items":[{"element_id":"<unit_id>.<序号>",'
        '"policy":"<policies 之一>","role":"<roles 之一或省略>","content":"<文本>",'
        '"source_seq_refs":[<int>],"fill_source":"<fill 必填>",'
        '"generated":{"field_type":"<generated 必填>"},'
        '"manual_semantics":"<manual_only 必填>","ai_decision_path":"<判定依据>"}]}。'
        "只输出 JSON。source_seq_refs 必须落在本窗口内。"
    ),
    "t4": (
        '返回 JSON 对象：{"section_profiles":[...],"default_font":...,"page_numbering":...,'
        '"header_footer":[...]}。拿不到真实页图时返回 {"section_profiles":[]} 表示弃权。'
    ),
}


def build_observation_prompt(
    *,
    stage: str,
    evidence_view: dict[str, Any],
) -> dict[str, Any]:
    """装配单阶段 prompt payload，并在 evidence 子树上复核防火墙。"""

    if stage not in _RUBRIC:
        raise ValueError(f"unknown observation stage: {stage!r}")
    assert_firewall_clean(evidence_view)
    return {
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "stage": stage,
        "rubric": _RUBRIC[stage],
        "allowed_labels": ALLOWED_LABELS,
        "abstain_is_valid": True,
        "evidence": evidence_view,
    }
