"""Module 1 终止工具定义（live 路径用；replay 不调用）。

关键：Module 1 用自己的 submit 工具产出三份**独立同形产物**，绝不复用 Module 2 的
``submit_t2/t3/t4``——后者喂的是 layered-submission「建议清单」，语义是“在代码结果上改”，
会把 AI 从“独立认出”拉回“提修改建议”。

阶段化工具策略（A.3）：T2 query_text 必 / view_pages 选；T3 query_text 必；T4 view_pages 必。
"""

from __future__ import annotations

from typing import Any

OBSERVATION_TERMINAL_TOOLS = {
    "ai_unit_observation": "submit_unit_observation",
    "ai_element_observation": "submit_element_observation",
    "ai_layout_observation": "submit_layout_observation",
}
ABSTAIN_TOOL = "abstain"

# 每阶段允许的取证工具（query_text=文本检索，view_pages=看页图）。
STAGE_TOOL_POLICY = {
    "t2": {"required": ("query_text",), "optional": ("view_pages",)},
    "t3": {"required": ("query_text",), "optional": ()},
    "t4": {"required": ("view_pages",), "optional": ()},
}


def terminal_tools_for_stage(stage: str) -> list[dict[str, Any]]:
    """返回该阶段可调用的终止工具 spec（submit_* + abstain）。"""

    artifact_type = _ARTIFACT_BY_STAGE.get(stage)
    if artifact_type is None:
        raise ValueError(f"unknown observation stage: {stage!r}")
    submit = OBSERVATION_TERMINAL_TOOLS[artifact_type]
    return [
        {
            "type": "function",
            "function": {
                "name": submit,
                "description": f"提交 {artifact_type}（独立同形产物，非 layered-submission 建议）。",
            },
        },
        {
            "type": "function",
            "function": {
                "name": ABSTAIN_TOOL,
                "description": "本阶段无高置信、可绑定证据的判断时弃权。",
            },
        },
    ]


_ARTIFACT_BY_STAGE = {
    "t2": "ai_unit_observation",
    "t3": "ai_element_observation",
    "t4": "ai_layout_observation",
}
