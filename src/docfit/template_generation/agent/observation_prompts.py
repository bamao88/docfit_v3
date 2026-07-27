"""Module 1 prompt assembly for T2, hierarchical T3, and T4.

把 clean evidence 视图与阶段 prompt 拼成 payload，帮模型在干净事实上做分割与
策略判断。装配后对 evidence 子树再跑一次 ``assert_firewall_clean``——确保送进
模型的证据没有代码结论字段。

T2 不注入单元别名字典，避免退化成关键词分类；T3 只使用
``t3_hierarchical_prompt.txt`` 的节点决策契约。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
import json
from string import Template
from typing import Any

from .evidence import assert_firewall_clean
from .observation_schema import PROMPT_CONTRACT_VERSION
from docfit.template_generation.t2_ai import T2_PROMPT_CONTRACT_VERSION
from .t3_hierarchical_input import assert_t3_stage_input_clean

_PROMPT_TEMPLATE_DIR = "prompt_templates"
_STAGES = ("t2", "t3_hierarchy", "t4")


def _allowed_labels_for_stage(stage: str) -> dict[str, list[str]]:
    """只向各阶段暴露它实际需要输出的标签，避免无关 unknown 干扰 T3。"""

    if stage == "t2":
        return {}
    if stage == "t3_hierarchy":
        return {
            "results": ["keep", "fill", "delete", "split"],
            "default_child_results": ["keep"],
            "fill_sources": ["student_content", "generated_field"],
        }
    return {}


@dataclass(frozen=True)
class ObservationPromptTemplates:
    system: str
    rubrics: Mapping[str, str]
    output_contracts: Mapping[str, str]
    t4_page_vision: str
    blocks: Mapping[str, str] = field(default_factory=dict)


@lru_cache(maxsize=1)
def default_observation_prompt_templates() -> ObservationPromptTemplates:
    base = resources.files(__package__).joinpath(_PROMPT_TEMPLATE_DIR)
    t3_hierarchical_prompt = _read_sectioned_prompt_resource(
        base,
        "t3_hierarchical_prompt.txt",
        sections=("rubric", "output_contract"),
    )
    return ObservationPromptTemplates(
        system=_read_prompt_resource(base, "system.txt"),
        rubrics={
            "t2": _read_prompt_resource(base, "t2_rubric.txt"),
            "t3_hierarchy": t3_hierarchical_prompt["rubric"],
            "t4": _read_prompt_resource(base, "t4_rubric.txt"),
        },
        output_contracts={
            "t2": _read_prompt_resource(base, "t2_output_contract.txt"),
            "t3_hierarchy": t3_hierarchical_prompt["output_contract"],
            "t4": _read_prompt_resource(base, "t4_output_contract.txt"),
        },
        t4_page_vision=_read_prompt_resource(base, "t4_page_vision_prompt.txt"),
        blocks={
            "quality": _read_prompt_resource(base, "quality_block.txt"),
            "glossary": _read_prompt_resource(base, "glossary_block.txt"),
            "exemplar": _read_prompt_resource(base, "exemplar_block.txt"),
        },
    )


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

_GLOSSARY_BY_STAGE = {
    "t2": lambda: "",
    "t3_hierarchy": lambda: "",
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
    if stage == "t3_hierarchy":
        assert_t3_stage_input_clean(evidence_view)
    else:
        assert_firewall_clean(evidence_view)
    if stage not in templates.rubrics or stage not in templates.output_contracts:
        raise ValueError(f"prompt templates missing stage: {stage!r}")
    return {
        "prompt_contract_version": (
            T2_PROMPT_CONTRACT_VERSION
            if stage == "t2"
            else PROMPT_CONTRACT_VERSION
        ),
        "stage": stage,
        "rubric": templates.rubrics[stage],
        "glossary": _GLOSSARY_BY_STAGE[stage](),
        "quality_goal": "",
        "exemplars": [],
        "allowed_labels": _allowed_labels_for_stage(stage),
        "output_contract": templates.output_contracts[stage],
        "abstain_is_valid": stage != "t3_hierarchy",
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
    exemplar_block = ""
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
    if stage == "t2":
        return (
            "T2 不允许遗漏页面；语义确实无法判断时使用 unknown_unit，"
            "但仍必须输出完整、连续的页面边界。"
        )
    if stage == "t3_hierarchy":
        return (
            "T3 分层决策不输出 unknown：证据不足但能安全下钻时输出 split；"
            "不能安全下钻时输出低置信 keep 并在 reason 中说明人工复核原因。"
        )
    return "弃权是合法输出：没有证据支撑就少认领。"


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
