"""Module 1 prompt 装配：阶段任务说明 + 必要枚举接地 + 防火墙复核。

把 clean evidence 视图与阶段 prompt 拼成 payload，帮模型在干净事实上做分割与
策略判断。装配后对 evidence 子树再跑一次 ``assert_firewall_clean``——确保送进
模型的证据没有代码结论字段。

T2 不注入单元别名字典，避免退化成关键词分类；只保留输出枚举。T3 接地材料来自
既有单一真相：``constants`` 的标记元组、``ontology.yaml`` 的枚举与定义。T3 主提示词的必填规则与
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
    KEEP_ONLY_MARKERS,
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
    select_t3_unit_exemplars,
)

PROMPT_OUTPUT_POLICIES = frozenset(ALLOWED_POLICIES) - {"unknown"}

ALLOWED_LABELS = {
    "unit_ids": sorted(ALLOWED_UNIT_IDS),
    "core_actions": ["keep", "fill", "delete"],
    # unknown 是 Gold/审计层标签，不是模型输出策略。模型不确定时应选 fixed，
    # 也就是一级动作 keep。
    "policies": sorted(PROMPT_OUTPUT_POLICIES),
    "generated_field_types": sorted(ALLOWED_FIELD_TYPES),
}
_PROMPT_TEMPLATE_DIR = "prompt_templates"
_STAGES = ("t2", "t3_unit", "t3", "t4")


def _allowed_labels_for_stage(stage: str) -> dict[str, list[str]]:
    """只向各阶段暴露它实际需要输出的标签，避免无关 unknown 干扰 T3。"""

    if stage == "t2":
        return {"unit_ids": list(ALLOWED_LABELS["unit_ids"])}
    if stage == "t3_unit":
        return {
            "routes": [
                "preserve_whole",
                "preserve_structure_classify_fields",
                "inspect_suspected_regions",
                "full_local_analysis",
            ],
            "default_preservation_policies": ["fixed", "generated"],
        }
    if stage == "t3":
        return {
            "core_actions": list(ALLOWED_LABELS["core_actions"]),
            "policies": list(ALLOWED_LABELS["policies"]),
            "generated_field_types": list(ALLOWED_LABELS["generated_field_types"]),
        }
    return {}


@dataclass(frozen=True)
class ObservationPromptTemplates:
    system: str
    rubrics: Mapping[str, str]
    output_contracts: Mapping[str, str]
    t4_page_vision: str
    # 兼容旧的自定义模板调用；默认 T3 已改为从 t3_prompt.txt 读取，不再消费此字段。
    policy_decision_tree: str | None = None
    blocks: Mapping[str, str] = field(default_factory=dict)


@lru_cache(maxsize=1)
def default_observation_prompt_templates() -> ObservationPromptTemplates:
    base = resources.files(__package__).joinpath(_PROMPT_TEMPLATE_DIR)
    t3_prompt = _read_sectioned_prompt_resource(
        base,
        "t3_prompt.txt",
        sections=("rubric", "output_contract"),
    )
    return ObservationPromptTemplates(
        system=_read_prompt_resource(base, "system.txt"),
        rubrics={
            "t2": _read_prompt_resource(base, "t2_rubric.txt"),
            "t3_unit": _read_prompt_resource(base, "t3_unit_rubric.txt"),
            "t3": t3_prompt["rubric"],
            "t4": _read_prompt_resource(base, "t4_rubric.txt"),
        },
        output_contracts={
            "t2": _read_prompt_resource(base, "t2_output_contract.txt"),
            "t3_unit": _read_prompt_resource(base, "t3_unit_output_contract.txt"),
            "t3": t3_prompt["output_contract"],
            "t4": _read_prompt_resource(base, "t4_output_contract.txt"),
        },
        t4_page_vision=_read_prompt_resource(base, "t4_page_vision_prompt.txt"),
        blocks={
            "quality": _read_prompt_resource(base, "quality_block.txt"),
            "glossary": _read_prompt_resource(base, "glossary_block.txt"),
            "exemplar": _read_prompt_resource(base, "exemplar_block.txt"),
        },
    )


def _markers(markers: tuple[str, ...], limit: int = 6) -> str:
    return "、".join(markers[:limit])


def _policy_glossary() -> str:
    """C3：policy / field_type / fill_source 的一行定义，给 T3 做策略接地。"""

    lines = ["policy 含义："]
    lines += [
        f"- {p}: {POLICY_DEFINITIONS.get(p, '')}"
        for p in sorted(PROMPT_OUTPUT_POLICIES)
    ]
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


def _read_sectioned_prompt_resource(
    base: resources.abc.Traversable,
    filename: str,
    *,
    sections: tuple[str, ...],
) -> dict[str, str]:
    """从一个可直接审阅的主 prompt 文件中读取具名片段。"""

    text = _read_prompt_resource(base, filename)
    result: dict[str, str] = {}
    for section in sections:
        begin = f"--- BEGIN {section} ---"
        end = f"--- END {section} ---"
        if text.count(begin) != 1 or text.count(end) != 1:
            raise ValueError(
                f"prompt resource {filename!r} must contain exactly one {section!r} section"
            )
        before, _, remainder = text.partition(begin)
        content, separator, after = remainder.partition(end)
        if before.strip() and section == sections[0]:
            raise ValueError(f"prompt resource {filename!r} has text before first section")
        if not separator or not content.strip():
            raise ValueError(f"prompt resource {filename!r} has empty {section!r} section")
        if section == sections[-1] and after.strip():
            raise ValueError(f"prompt resource {filename!r} has text after last section")
        result[section] = content.strip()
    return result


# 模型必须严格返回的 JSON 形状（live 路径解析依据）。
OUTPUT_CONTRACT = dict(default_observation_prompt_templates().output_contracts)

# 每阶段注入的词典。T2 明确不注入单元词典；T3 保留 policy 词典。
_GLOSSARY_BY_STAGE = {
    "t2": lambda: "",
    "t3_unit": _policy_glossary,
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
    if stage == "t3_unit":
        exemplars = select_t3_unit_exemplars(evidence_view)
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
                "fillable_markers": _markers(FILLABLE_MARKERS),
                "fillable_labels": _markers(FILLABLE_LABELS),
                "generated_markers": _markers(GENERATED_MARKERS),
                "keep_only_markers": _markers(KEEP_ONLY_MARKERS),
                "action_refinement_instruction": _action_refinement_instruction(
                    evidence_view
                ),
            },
        ),
        "glossary": _GLOSSARY_BY_STAGE[stage](),
        "quality_goal": quality_goal,
        "exemplars": exemplars,
        "allowed_labels": _allowed_labels_for_stage(stage),
        "output_contract": templates.output_contracts[stage],
        "abstain_is_valid": stage != "t3",
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
            "abstain_instruction": _abstain_instruction(stage),
        },
    )
    user = json.dumps(prompt["evidence"], ensure_ascii=False)
    return system, user


def _abstain_instruction(stage: str) -> str:
    if stage == "t3":
        return (
            "T3 对当前窗口内已经绑定的 run 不得弃权：不确定或混合时按 rubric 输出 "
            "core_action=keep、policy=fixed，不输出 unknown。"
        )
    return "弃权是合法输出：没有证据支撑就少认领。"


def _action_refinement_instruction(evidence: dict[str, Any]) -> str:
    action = str(evidence.get("refinement_action") or "").strip()
    if action not in {"fill", "delete"}:
        return ""
    if action == "delete":
        return (
            "\n这是 Delete 候选的第二层复核。只复核 candidate_items：通过删除测试后保留 "
            "delete；若它其实是内容要求、混合 run、定位不足或无法判断空间效果，必须降级为 "
            "keep。不要因为进入 Delete 分支就强行确认删除。\n"
        )
    return (
        "\n这是 Fill 候选的第二层复核。只复核 candidate_items：确认真正需要替换的最小范围，"
        "不得吞掉固定标签、前后缀、单位或标点；无法精确定位时降级为 keep。\n"
    )


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
