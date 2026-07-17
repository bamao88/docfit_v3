"""T3 优质模板示例库与按单元/局部事实选择逻辑。

示例只教模型什么结果会形成可用的学校模板，不携带任何当前文档答案。选择器仅依据
当前单元路由与局部事实画像选少量同类型示例，避免把整个示例库塞进 prompt。
"""

from __future__ import annotations

import json
from typing import Any


T3_QUALITY_GOAL = (
    "目标是形成可实际复用的高质量学校模板：固定标题/标签/正式声明完整保留；"
    "学生姓名、学号、论文题目等个性化示例值变成准确填写字段；只有能精确绑定 run 的纯格式批注才删除；"
    "空白填写区不遗漏；签名、手写意见和人工勾选保留为 manual_only；"
    "标签和值的关系、完整声明及表格结构不被破坏；不确定时宁可保留并复核，避免误删正式内容；"
    "所有判断都能追溯到输入中的 Word 事实。"
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
                "semantic_role": "format_annotation",
                "transformation": "remove_exact_span",
                "confidence": "high",
                "content": "（小二号黑体加粗）",
                "raw_run_ids": ["p_0007.r_004"],
                "removal_reason": "该独立 run 只描述字体字号，不属于成稿内容",
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


_UNIT_EXEMPLARS: dict[str, dict[str, Any]] = {
    "declaration_preserve_whole": {
        "name": "正式声明页：整体保护",
        "input_summary": {
            "objects": ["声明标题", "完整声明正文", "签名和日期区域"],
            "visual_pattern": "正式连续文本，末尾带人工签署区域",
        },
        "bad_plan": {
            "route": "full_local_analysis",
            "why_bad": "逐句判断容易把声明条款误当填写说明删掉，破坏法律/学术诚信文本完整性",
        },
        "excellent_plan": {
            "route": "inspect_suspected_regions",
            "default_preservation_policy": "manual_only",
            "protected_source_seq_refs": [101, 102, 103, 104, 105],
            "inspect_source_seq_refs": [106],
            "confidence": "high",
            "rationale": "声明正文与签署区构成需人工确认的完整页面；只检查独立纯格式批注",
            "quality_risks": ["必须保持声明正文整体性"],
        },
    },
    "form_inspect_regions": {
        "name": "结构化表单：保结构，只检查候选字段",
        "input_summary": {
            "objects": ["多行两列表格"],
            "candidate_regions": ["标签-值行", "签名日期行", "纯格式批注行"],
        },
        "bad_plan": {
            "route": "full_local_analysis",
            "why_bad": "无差别下钻增加调用和标签/内容被割裂的风险",
        },
        "excellent_plan": {
            "route": "preserve_whole",
            "default_preservation_policy": "manual_only",
            "protected_source_seq_refs": [201, 202, 203, 204, 205, 206],
            "inspect_source_seq_refs": [],
            "confidence": "high",
            "rationale": "整张行政表单都是后续人工填写、签署和评审的工作区，整体保留并停止下钻",
            "quality_risks": ["表格骨架不可破坏", "固定栏目文字也是人工工作流的一部分"],
        },
    },
    "generated_toc": {
        "name": "自动目录：整体为生成字段，只检查独立格式批注",
        "input_summary": {
            "objects": ["目录标题", "多级目录示例行", "引导点和页码"],
            "visual_pattern": "连续目录条目骨架，最终应由系统根据正文标题生成",
        },
        "bad_plan": {
            "route": "preserve_structure_classify_fields",
            "default_preservation_policy": "fixed",
            "why_bad": "会把示例目录条目固定进最终模板，阻止系统重建真实目录",
        },
        "excellent_plan": {
            "route": "inspect_suspected_regions",
            "default_preservation_policy": "generated",
            "protected_source_seq_refs": [401, 402, 403, 404],
            "inspect_source_seq_refs": [405],
            "confidence": "high",
            "rationale": "目录主体整体由系统生成；只检查独立字体字号/空行批注",
            "quality_risks": ["不能把示例目录条目当成 fixed", "格式批注仍需精确 raw run 才可删除"],
        },
    },
    "mixed_content_full": {
        "name": "混合内容块：确需完整局部判断",
        "input_summary": {
            "objects": ["固定标题", "学生示例值", "自动目录", "独立格式批注"],
            "visual_pattern": "多种用途交错，整体默认策略不足以表达",
        },
        "excellent_plan": {
            "route": "full_local_analysis",
            "default_preservation_policy": "fixed",
            "protected_source_seq_refs": [],
            "inspect_source_seq_refs": [301, 302, 303, 304],
            "confidence": "high",
            "rationale": "同一单元存在 fixed/fill/generated/remove 多种变换，需要逐 run 判断",
            "quality_risks": ["删除仍需高置信度和精确 raw_run_ids"],
        },
    },
}


def select_t3_element_exemplars(evidence: dict[str, Any], *, limit: int = 3) -> list[dict[str, Any]]:
    """按当前局部事实选择少量正反例。"""

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


def select_t3_unit_exemplars(evidence: dict[str, Any], *, limit: int = 4) -> list[dict[str, Any]]:
    """整单元规划固定提供三类路由正反例，不含当前文档答案。"""

    del evidence
    return [
        {"exemplar_id": exemplar_id, **exemplar}
        for exemplar_id, exemplar in list(_UNIT_EXEMPLARS.items())[: max(1, limit)]
    ]


def format_exemplars(exemplars: list[dict[str, Any]]) -> str:
    return json.dumps(exemplars, ensure_ascii=False, indent=2)


def _evidence_text(evidence: dict[str, Any]) -> str:
    return json.dumps(
        {
            "object_overview": evidence.get("object_overview"),
            "unit_plan": evidence.get("unit_plan"),
            "rows": evidence.get("rows"),
        },
        ensure_ascii=False,
        default=str,
    ).lower()
