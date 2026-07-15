"""Module 1 prompt 装配：taxonomy/枚举接地 + 分解式决策树 + 防火墙复核。

把 clean evidence 视图与**领域词典**（单元名+别名、policy 定义、决策树）拼成 payload，
帮模型在干净事实上做分割与策略判断（领域先验，非 gold）。装配后对 evidence 子树
再跑一次 ``assert_firewall_clean``——确保送进模型的证据没有代码结论字段。

接地材料全部来自既有单一真相：``UNIT_DEFINITIONS`` 的中文名+别名、``constants`` 的
标记元组、``ontology.yaml`` 的枚举与定义。T3 决策树的必填规则与
``observation_materialize._required_field_error`` 逐字对齐，prompt 与闸门同口径。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
import json
from string import Template
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
from .t3_exemplars import (
    T3_QUALITY_GOAL,
    format_exemplars,
    select_t3_element_exemplars,
    select_t3_object_exemplars,
)

ALLOWED_LABELS = {
    "unit_ids": sorted(ALLOWED_UNIT_IDS),
    "policies": sorted(ALLOWED_POLICIES),
    "generated_field_types": sorted(ALLOWED_FIELD_TYPES),
}
_PROMPT_TEMPLATE_DIR = "prompt_templates"
_STAGES = ("t2", "t3_object", "t3", "t4")


@dataclass(frozen=True)
class ObservationPromptTemplates:
    system: str
    rubrics: Mapping[str, str]
    output_contracts: Mapping[str, str]
    policy_decision_tree: str
    t4_page_vision: str
    blocks: Mapping[str, str] = field(default_factory=dict)


@lru_cache(maxsize=1)
def default_observation_prompt_templates() -> ObservationPromptTemplates:
    base = resources.files(__package__).joinpath(_PROMPT_TEMPLATE_DIR)
    return ObservationPromptTemplates(
        system=_read_prompt_resource(base, "system.txt"),
        rubrics={
            "t2": _read_prompt_resource(base, "t2_rubric.txt"),
            "t3_object": _read_prompt_resource(base, "t3_object_rubric.txt"),
            "t3": _read_prompt_resource(base, "t3_rubric.txt"),
            "t4": _read_prompt_resource(base, "t4_rubric.txt"),
        },
        output_contracts={
            "t2": _read_prompt_resource(base, "t2_output_contract.txt"),
            "t3_object": _read_prompt_resource(base, "t3_object_output_contract.txt"),
            "t3": _read_prompt_resource(base, "t3_output_contract.txt"),
            "t4": _read_prompt_resource(base, "t4_output_contract.txt"),
        },
        policy_decision_tree=_read_prompt_resource(base, "t3_policy_decision_tree.txt"),
        t4_page_vision=_read_prompt_resource(base, "t4_page_vision_prompt.txt"),
        blocks={
            "quality": _read_prompt_resource(base, "quality_block.txt"),
            "glossary": _read_prompt_resource(base, "glossary_block.txt"),
            "exemplar": _read_prompt_resource(base, "exemplar_block.txt"),
        },
    )


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


def _read_prompt_resource(base: resources.abc.Traversable, filename: str) -> str:
    return base.joinpath(filename).read_text(encoding="utf-8").strip()


def _policy_decision_tree(templates: ObservationPromptTemplates) -> str:
    """C2：按顺序的 cue→policy 决策树，必填规则放在每个叶子（与闸门同口径）。"""

    return _render_prompt_template(
        templates.policy_decision_tree,
        {
            "instruction_markers": _markers(INSTRUCTION_MARKERS),
            "fillable_markers": _markers(FILLABLE_MARKERS),
            "fillable_labels": _markers(FILLABLE_LABELS),
            "generated_markers": _markers(GENERATED_MARKERS),
            "manual_only_markers": _markers(MANUAL_ONLY_MARKERS),
        },
    )


# 模型必须严格返回的 JSON 形状（live 路径解析依据）。
OUTPUT_CONTRACT = dict(default_observation_prompt_templates().output_contracts)

# 每阶段注入的词典（C1 单元词典给 t2；C3 policy 词典给 t3）。
_GLOSSARY_BY_STAGE = {
    "t2": _unit_glossary,
    "t3_object": lambda: "",
    "t3": _policy_glossary,
    "t4": lambda: "",
}


def build_observation_prompt(
    *,
    stage: str,
    evidence_view: dict[str, Any],
    prompt_templates: ObservationPromptTemplates | None = None,
) -> dict[str, Any]:
    """装配单阶段 prompt payload，并在 evidence 子树上复核防火墙。"""

    templates = prompt_templates or default_observation_prompt_templates()
    if stage not in _STAGES:
        raise ValueError(f"unknown observation stage: {stage!r}")
    assert_firewall_clean(evidence_view)
    if stage not in templates.rubrics or stage not in templates.output_contracts:
        raise ValueError(f"prompt templates missing stage: {stage!r}")
    exemplars: list[dict[str, Any]] = []
    quality_goal = ""
    if stage == "t3_object":
        exemplars = select_t3_object_exemplars(evidence_view)
        quality_goal = T3_QUALITY_GOAL
    elif stage == "t3":
        exemplars = select_t3_element_exemplars(evidence_view)
        quality_goal = T3_QUALITY_GOAL
    return {
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "stage": stage,
        "rubric": _render_prompt_template(
            templates.rubrics[stage],
            {
                "quality_goal": T3_QUALITY_GOAL,
                "policy_decision_tree": _policy_decision_tree(templates),
            },
        ),
        "glossary": _GLOSSARY_BY_STAGE[stage](),
        "quality_goal": quality_goal,
        "exemplars": exemplars,
        "allowed_labels": ALLOWED_LABELS,
        "output_contract": templates.output_contracts[stage],
        "abstain_is_valid": True,
        "evidence": _strip_private_fields(evidence_view),
    }


def assemble_observation_messages(
    stage: str,
    evidence_view: dict[str, Any],
    prompt_templates: ObservationPromptTemplates | None = None,
) -> tuple[str, str]:
    """把单阶段 prompt 装配成 (system, user) 文本——Kimi/MiniMax 等 provider 共用，
    保证不同模型拿到**完全相同**的 prompt。evidence 子树已在 build_observation_prompt 过防火墙。"""

    templates = prompt_templates or default_observation_prompt_templates()
    prompt = build_observation_prompt(
        stage=stage,
        evidence_view=evidence_view,
        prompt_templates=templates,
    )
    glossary = prompt.get("glossary") or ""
    glossary_block = _optional_prompt_block(templates, "glossary", glossary)
    quality_block = _optional_prompt_block(templates, "quality", prompt.get("quality_goal"))
    exemplar_block = (
        _optional_prompt_block(templates, "exemplar", format_exemplars(prompt["exemplars"]))
        if prompt.get("exemplars")
        else ""
    )
    system = _render_prompt_template(
        templates.system,
        {
            "rubric": str(prompt["rubric"]),
            "quality_block": quality_block,
            "glossary_block": glossary_block,
            "exemplar_block": exemplar_block,
            "allowed_labels_json": json.dumps(prompt["allowed_labels"], ensure_ascii=False),
            "output_contract": str(prompt["output_contract"]),
        },
    )
    user = json.dumps(prompt["evidence"], ensure_ascii=False)
    return system, user


def _render_prompt_template(template: str, values: Mapping[str, Any]) -> str:
    return Template(template).safe_substitute(
        {key: str(value) for key, value in values.items()}
    )


def _optional_prompt_block(
    templates: ObservationPromptTemplates,
    block_name: str,
    content: Any,
) -> str:
    text = str(content or "")
    if not text:
        return ""
    template = templates.blocks.get(block_name, "$content\n")
    return _render_prompt_template(template, {"content": text}) + "\n"


def _strip_private_fields(value: Any) -> Any:
    """附件路径只给 responder 读取，不把本机路径和实现细节塞进模型文本。"""

    if isinstance(value, dict):
        return {
            key: _strip_private_fields(item)
            for key, item in value.items()
            if not str(key).startswith("_")
        }
    if isinstance(value, list):
        return [_strip_private_fields(item) for item in value]
    return value
