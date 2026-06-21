from __future__ import annotations

import re
from typing import Any


def _dedupe_by_key(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        value = str(item.get(key))
        if value in seen:
            continue
        deduped.append(item)
        seen.add(value)
    return deduped


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _normalize_for_match(value: Any) -> str:
    text = _strip_format_annotations(str(value or ""))
    text = re.sub(r"[□×Xx_＿]+", "", text)
    text = re.sub(r"[…·•.。．]{2,}", "", text)
    text = re.sub(r"[\s:：;；,，.。!！?？、（）()《》<>“”\"'‘’\[\]【】]", "", text)
    return text.strip().lower()


def _strip_format_annotations(text: str) -> str:
    format_markers = (
        "号",
        "黑体",
        "宋体",
        "楷体",
        "仿宋",
        "Times",
        "居中",
        "加粗",
        "行距",
        "字号",
        "字体",
        "页边距",
        "厘米",
        "空格",
        "格式",
        "pt",
        "表示",
    )

    def replace_annotation(match: re.Match[str]) -> str:
        content = match.group(1)
        if any(marker in content for marker in format_markers):
            return ""
        return match.group(0)

    text = re.sub(r"（([^（）]*)）", replace_annotation, text)
    text = re.sub(r"\(([^()]*)\)", replace_annotation, text)
    return text


def _dedupe(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        deduped.append(item)
        seen.add(item)
    return deduped
