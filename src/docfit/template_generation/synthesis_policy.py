from __future__ import annotations

from typing import Any

from .text_utils import _normalize_for_match


def should_synthesize_visible_text(element: dict[str, Any]) -> bool:
    """Return whether a source-less first element is safe to insert as text."""

    order = element.get("order") or element.get("element_order")
    if order not in {1, "1"}:
        return False
    text = str(element.get("content") or element.get("name") or "").strip()
    if not text or len(text) > 120:
        return False
    normalized = _normalize_for_match(text)
    return bool(normalized and not _looks_like_nonvisible_requirement(normalized))


def _looks_like_nonvisible_requirement(normalized: str) -> bool:
    markers = (
        "页眉",
        "页脚",
        "页码",
        "页边距",
        "装订线",
        "纸张",
        "section",
        "schoolyaml",
        "ooxml",
        "审查口径",
        "全局规则",
        "源模板",
        "源文件",
        "当前阶段",
        "目标输出",
        "生成机制",
        "标题编号体系",
        "样式",
        "字体",
        "字号",
        "行距",
        "大纲级别",
        "保留学校封面本体",
        "不属于模板的说明文字",
        "markdown",
        "自动化测试",
        "渲染测试",
        "验收",
    )
    return any(marker in normalized for marker in markers)
