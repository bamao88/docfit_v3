"""T3 优质模板示例库与按对象选择逻辑。

示例只教模型什么结果会形成可用的学校模板，不携带任何当前文档答案。选择器仅依据
当前对象的事实画像与软性 object plan 选少量同类型示例，避免把整个示例库塞进 prompt。
"""

from __future__ import annotations

import json
from typing import Any


T3_QUALITY_GOAL = (
    "目标是形成可实际复用的高质量学校模板：固定标题/标签/正式声明完整保留；"
    "学生姓名、学号、论文题目等个性化示例值变成准确填写字段；格式与填写说明被删除；"
    "空白填写区不遗漏；签名、手写意见和人工勾选保留为 manual_only；"
    "标签和值的关系及表格结构不被破坏；所有判断都能追溯到输入中的 Word 事实。"
)


_ELEMENT_EXEMPLARS: dict[str, dict[str, Any]] = {
    "two_column_field_table": {
        "name": "两列表单：固定标签与待填值分开",
        "applies_to": ["table", "metadata_form", "label_value"],
        "input": {
            "cells": [
                {"cell": "r2c1", "text": "学生姓名", "source_seq": 21},
                {"cell": "r2c2", "text": "张三", "source_seq": 22},
            ]
        },
        "bad_result": {
            "policy": "fill",
            "source_seq_refs": [21, 22],
            "why_bad": "会把固定标签‘学生姓名’也覆盖掉",
        },
        "excellent_result": [
            {
                "policy": "fixed",
                "role": "template_fixed",
                "content": "学生姓名",
                "source_seq_refs": [21],
            },
            {
                "policy": "fill",
                "role": "student_content",
                "content": "张三",
                "source_seq_refs": [22],
                "fill_source": "student_content",
            },
        ],
        "quality_reason": "最终模板保留栏目标签，同时移除示例学生姓名并留下填写位置",
    },
    "format_instruction_split": {
        "name": "同段混合内容：正文与格式说明拆开",
        "applies_to": ["text_flow", "table", "cover", "instruction"],
        "input": {
            "runs": [
                {"raw_run_id": "p_0007.r_003", "text": "论文题目"},
                {"raw_run_id": "p_0007.r_004", "text": "（小二号黑体加粗）"},
            ]
        },
        "bad_result": {
            "policy": "fill",
            "raw_run_ids": ["p_0007.r_003", "p_0007.r_004"],
            "why_bad": "格式说明会作为论文题目的一部分残留在最终模板",
        },
        "excellent_result": [
            {
                "policy": "fill",
                "role": "student_content",
                "content": "论文题目",
                "raw_run_ids": ["p_0007.r_003"],
                "fill_source": "student_content",
            },
            {
                "policy": "instruction_remove",
                "role": "template_instruction",
                "content": "（小二号黑体加粗）",
                "raw_run_ids": ["p_0007.r_004"],
            },
        ],
        "quality_reason": "填写内容与只用于指导排版的说明必须形成两个元素",
    },
    "manual_signature": {
        "name": "签名与人工意见区域",
        "applies_to": ["table", "signature", "approval", "declaration"],
        "input": {
            "cells": [
                {"cell": "r4c1", "text": "指导教师签字", "source_seq": 41},
                {"cell": "r4c2", "text": "________", "source_seq": 42},
            ]
        },
        "bad_result": {
            "policy": "fill",
            "source_seq_refs": [42],
            "why_bad": "电子内容填写不能替代真实签字或人工确认",
        },
        "excellent_result": [
            {
                "policy": "fixed",
                "role": "template_fixed",
                "content": "指导教师签字",
                "source_seq_refs": [41],
            },
            {
                "policy": "manual_only",
                "role": "manual_field",
                "content": "________",
                "source_seq_refs": [42],
                "manual_semantics": "指导教师签字",
            },
        ],
        "quality_reason": "固定标签保留，签字区域明确留给人工完成",
    },
    "fixed_heading_and_default_value": {
        "name": "固定标题与模板示例值",
        "applies_to": ["text_flow", "cover", "heading", "abstract"],
        "input": {
            "rows": [
                {"text": "本科毕业论文", "source_seq": 5},
                {"text": "人工智能在农业中的应用", "source_seq": 6},
            ]
        },
        "bad_result": {
            "policy": "fixed",
            "source_seq_refs": [5, 6],
            "why_bad": "示例论文题目会被永久保留",
        },
        "excellent_result": [
            {
                "policy": "fixed",
                "role": "template_fixed",
                "content": "本科毕业论文",
                "source_seq_refs": [5],
            },
            {
                "policy": "fill",
                "role": "student_content",
                "content": "人工智能在农业中的应用",
                "source_seq_refs": [6],
                "fill_source": "student_content",
            },
        ],
        "quality_reason": "文档类型标题属于学校模板，具体论文题目属于学生内容",
    },
}


_OBJECT_EXEMPLARS: dict[str, dict[str, Any]] = {
    "metadata_form_overview": {
        "name": "对象级识别：学生信息表",
        "overview": {
            "object_type": "table",
            "dimensions": {"rows": 6, "columns": 2},
            "row_samples": [
                ["学生姓名", "张三"],
                ["学号", "20260001"],
                ["指导教师签字", "________"],
            ],
        },
        "excellent_plan": {
            "object_hypothesis": {
                "archetype": "metadata_form",
                "purpose": "收集学生、论文和指导教师信息",
                "confidence": "high",
            },
            "regions": [
                {"region": "label_value_fields", "pattern": "左侧固定标签，右侧待填值"},
                {"region": "manual_signature", "pattern": "固定签字标签，右侧人工签字区"},
            ],
            "quality_risks": ["不要把标签和值合并", "不要把签字区判断为普通 fill"],
        },
    },
    "mixed_text_overview": {
        "name": "对象级识别：标题、示例值与格式说明混合",
        "overview": {
            "object_type": "text_flow",
            "row_samples": ["本科毕业论文", "论文题目", "（小二号黑体加粗）"],
        },
        "excellent_plan": {
            "object_hypothesis": {
                "archetype": "cover_title_block",
                "purpose": "保留封面固定标题并定位学生题目填写区",
                "confidence": "high",
            },
            "regions": [
                {"region": "fixed_heading", "pattern": "学校模板标题"},
                {"region": "student_value", "pattern": "学生论文题目"},
                {"region": "format_instruction", "pattern": "只用于排版指导"},
            ],
            "quality_risks": ["格式说明不得进入填写内容", "示例题目不得固定保留"],
        },
    },
}


def select_t3_element_exemplars(evidence: dict[str, Any], *, limit: int = 3) -> list[dict[str, Any]]:
    """按当前对象画像/规划选择少量正反例。"""

    haystack = _evidence_text(evidence)
    scores: list[tuple[int, str]] = []
    for exemplar_id, exemplar in _ELEMENT_EXEMPLARS.items():
        score = sum(1 for cue in exemplar.get("applies_to", []) if cue.lower() in haystack)
        if exemplar_id == "format_instruction_split":
            score += 1  # 混合 run 是所有 T3 对象都必须掌握的基础能力。
        scores.append((score, exemplar_id))
    selected = sorted(scores, key=lambda item: (-item[0], item[1]))[: max(1, limit)]
    return [
        {"exemplar_id": exemplar_id, **_ELEMENT_EXEMPLARS[exemplar_id]}
        for _, exemplar_id in selected
    ]


def select_t3_object_exemplars(evidence: dict[str, Any], *, limit: int = 1) -> list[dict[str, Any]]:
    overview = evidence.get("object_overview") or {}
    object_type = str(overview.get("object_type") or "")
    preferred = "metadata_form_overview" if object_type == "table" else "mixed_text_overview"
    ids = [preferred]
    return [
        {"exemplar_id": exemplar_id, **_OBJECT_EXEMPLARS[exemplar_id]}
        for exemplar_id in ids[: max(1, limit)]
    ]


def format_exemplars(exemplars: list[dict[str, Any]]) -> str:
    return json.dumps(exemplars, ensure_ascii=False, indent=2)


def _evidence_text(evidence: dict[str, Any]) -> str:
    return json.dumps(
        {
            "object_overview": evidence.get("object_overview"),
            "object_plan": evidence.get("object_plan"),
            "rows": evidence.get("rows"),
        },
        ensure_ascii=False,
        default=str,
    ).lower()
