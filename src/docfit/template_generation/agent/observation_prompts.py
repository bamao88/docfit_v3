"""Module 1 prompt 装配：taxonomy/枚举接地 + 分解式决策树 + 防火墙复核。

把 clean evidence 视图与**领域词典**（单元名+别名、policy 定义、决策树）拼成 payload，
帮模型在干净事实上做分割与策略判断（领域先验，非 gold）。装配后对 evidence 子树
再跑一次 ``assert_firewall_clean``——确保送进模型的证据没有代码结论字段。

接地材料全部来自既有单一真相：``UNIT_DEFINITIONS`` 的中文名+别名、``constants`` 的
标记元组、``ontology.yaml`` 的枚举与定义。T3 决策树的必填规则与
``observation_materialize._required_field_error`` 逐字对齐，prompt 与闸门同口径。
"""

from __future__ import annotations

import json
from typing import Any

from ..constants import (
    FILLABLE_LABELS,
    FILLABLE_MARKERS,
    GENERATED_MARKERS,
    INSTRUCTION_MARKERS,
    MANUAL_ONLY_MARKERS,
    UNIT_DEFINITIONS,
)
from .evidence import assert_firewall_clean
from .observation_schema import (
    ALLOWED_FIELD_TYPES,
    ALLOWED_POLICIES,
    ALLOWED_UNIT_IDS,
    FIELD_TYPE_DEFINITIONS,
    FILL_SOURCE_DEFINITIONS,
    POLICY_DEFINITIONS,
    PROMPT_CONTRACT_VERSION,
    ROLE_DEFINITIONS,
)

ALLOWED_LABELS = {
    "unit_ids": sorted(ALLOWED_UNIT_IDS),
    "policies": sorted(ALLOWED_POLICIES),
    "generated_field_types": sorted(ALLOWED_FIELD_TYPES),
}


def _markers(markers: tuple[str, ...], limit: int = 6) -> str:
    return "、".join(markers[:limit])


def _unit_glossary() -> str:
    """C1：每个单元的中文名 + 别名关键词，给 T2 做分割接地。"""

    return "\n".join(
        f"- {unit_id} ({name}): {' | '.join(aliases)}"
        for unit_id, name, aliases in UNIT_DEFINITIONS
    )


def _policy_glossary() -> str:
    """C3：policy / field_type / fill_source 的一行定义，给 T3 做策略接地。"""

    lines = ["policy 含义："]
    lines += [f"- {p}: {POLICY_DEFINITIONS.get(p, '')}" for p in sorted(ALLOWED_POLICIES)]
    lines.append(
        "fill_source ∈ " + " / ".join(f"{k}({v})" for k, v in FILL_SOURCE_DEFINITIONS.items())
    )
    lines.append(
        "generated.field_type ∈ "
        + " / ".join(f"{k}({v})" for k, v in FIELD_TYPE_DEFINITIONS.items())
    )
    lines.append("role ∈ " + " / ".join(f"{k}({v})" for k, v in ROLE_DEFINITIONS.items()))
    return "\n".join(lines)


def _policy_decision_tree() -> str:
    """C2：按顺序的 cue→policy 决策树，必填规则放在每个叶子（与闸门同口径）。"""

    return (
        "在本单元窗口内，逐个元素**按顺序**判断 policy（命中即停）：\n"
        f"1) 含格式/排版说明（如 {_markers(INSTRUCTION_MARKERS)}…）→ instruction_remove\n"
        "2) 原样保留的模板固定文字（校名、声明标题、固定样板）→ fixed\n"
        "3) 模板自带的标题/标签等默认内容 → template_default\n"
        f"4) 留空待填（如 {_markers(FILLABLE_MARKERS)} 或 {_markers(FILLABLE_LABELS)}）→ fill"
        "  ⇒ 必给 fill_source ∈ {student_content | manual | generated_field}\n"
        f"5) 系统自动生成（如 {_markers(GENERATED_MARKERS)}）→ generated"
        "  ⇒ 必给 generated.field_type ∈ {TOC | PAGE | SEQ | FIELD_PLACEHOLDER}\n"
        f"6) 只能人工手写（如 {_markers(MANUAL_ONLY_MARKERS)}）→ manual_only"
        "  ⇒ 必给 manual_semantics\n"
        "都不匹配/没把握 → 降低 confidence、少认领。回报 ai_decision_path 说明命中哪一支。"
    )


_RUBRIC = {
    "t2": (
        "只依据给定的 Word 事实，把每个 source_seq 归到一个 unit_id（或 unknown_unit）。"
        "参考下方单元词典的中文名与别名关键词做匹配；不确定就用 unknown_unit 并降低 confidence。"
        "每个判断必须给 source_seq_refs。"
    ),
    "t3": _policy_decision_tree(),
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
        '"source_seq_refs":[<int>],"fill_source":"...","generated":{"field_type":"..."},'
        '"manual_semantics":"...","ai_decision_path":"<命中哪一支>"}]}。\n'
        "发射每个 item 前自检（缺条件字段的 item 会被拒收并丢失）：\n"
        "  policy==fill ⇒ 必有 fill_source；policy==generated ⇒ 必有 generated.field_type；"
        "policy==manual_only ⇒ 必有 manual_semantics。\n"
        "其余 policy 不需要这些条件字段。只输出 JSON；source_seq_refs 必须落在本窗口内。"
    ),
    "t4": (
        '返回 JSON 对象：{"section_profiles":[...],"default_font":...,"page_numbering":...,'
        '"header_footer":[...]}。拿不到真实页图时返回 {"section_profiles":[]} 表示弃权。'
    ),
}

# 每阶段注入的词典（C1 单元词典给 t2；C3 policy 词典给 t3）。
_GLOSSARY_BY_STAGE = {
    "t2": _unit_glossary,
    "t3": _policy_glossary,
    "t4": lambda: "",
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
        "glossary": _GLOSSARY_BY_STAGE[stage](),
        "allowed_labels": ALLOWED_LABELS,
        "abstain_is_valid": True,
        "evidence": evidence_view,
    }


def assemble_observation_messages(
    stage: str,
    evidence_view: dict[str, Any],
) -> tuple[str, str]:
    """把单阶段 prompt 装配成 (system, user) 文本——Kimi/MiniMax 等 provider 共用，
    保证不同模型拿到**完全相同**的 prompt。evidence 子树已在 build_observation_prompt 过防火墙。"""

    prompt = build_observation_prompt(stage=stage, evidence_view=evidence_view)
    glossary = prompt.get("glossary") or ""
    glossary_block = f"词典（领域先验，非答案）：\n{glossary}\n" if glossary else ""
    system = (
        "你是 DocFit 模板结构观察器。只依据给定的 Word 事实独立判断，"
        "看不到也不要假设任何代码已有结论。\n"
        f"任务：{prompt['rubric']}\n"
        f"{glossary_block}"
        f"允许标签集：{json.dumps(ALLOWED_LABELS, ensure_ascii=False)}\n"
        f"输出契约：{OUTPUT_CONTRACT[stage]}\n"
        "弃权是合法输出：没有证据支撑就少认领、留 unknown。"
    )
    user = json.dumps(prompt["evidence"], ensure_ascii=False)
    return system, user
