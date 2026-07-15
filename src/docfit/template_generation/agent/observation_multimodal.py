"""把 T3 evidence 中的分层视觉附件转换为 provider 的多模态消息。"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any


def anthropic_user_content(user_text: str, evidence: dict[str, Any]) -> str | list[dict[str, Any]]:
    attachments = _attachments(evidence)
    if not attachments:
        return user_text
    content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
    for attachment in attachments:
        content.append(
            {
                "type": "text",
                "text": f"视觉附件 {attachment['visual_ref']}（仅作布局辅助，Word 文字仍是真源）。",
            }
        )
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": attachment["media_type"],
                    "data": attachment["base64"],
                },
            }
        )
    return content


def openai_user_content(user_text: str, evidence: dict[str, Any]) -> str | list[dict[str, Any]]:
    attachments = _attachments(evidence)
    if not attachments:
        return user_text
    content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
    for attachment in attachments:
        content.append(
            {
                "type": "text",
                "text": f"视觉附件 {attachment['visual_ref']}（仅作布局辅助，Word 文字仍是真源）。",
            }
        )
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{attachment['media_type']};base64,{attachment['base64']}",
                    "detail": "low",
                },
            }
        )
    return content


def attachment_refs(evidence: dict[str, Any]) -> list[str]:
    return [str(item.get("visual_ref")) for item in _attachment_entries(evidence)]


def _attachments(evidence: dict[str, Any]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for entry in _attachment_entries(evidence):
        path = Path(str(entry.get("_attachment_path") or ""))
        if not path.is_file():
            continue
        result.append(
            {
                "visual_ref": str(entry.get("visual_ref") or path.name),
                "media_type": _media_type(path),
                "base64": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
        )
    return result


def _attachment_entries(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    visual = evidence.get("visual_evidence") or []
    if not isinstance(visual, list):
        return []
    return [item for item in visual[:4] if isinstance(item, dict) and item.get("_attachment_path")]


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"
