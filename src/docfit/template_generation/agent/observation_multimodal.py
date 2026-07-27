"""把 T3 evidence 中的分层视觉附件转换为 provider 的多模态消息。"""

from __future__ import annotations

import base64
from pathlib import Path
import json
from typing import Any


def anthropic_user_content(user_text: str, evidence: dict[str, Any]) -> str | list[dict[str, Any]]:
    attachments = _attachments(evidence)
    if not attachments:
        return user_text
    if evidence.get("scope") == "t2_page_groups":
        return _t2_anthropic_content(evidence, attachments)
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
    if evidence.get("scope") == "t2_page_groups":
        return _t2_openai_content(evidence, attachments)
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
    limit = _attachment_limit(evidence)
    if limit <= 0:
        return []
    return [
        item
        for item in visual[:limit]
        if isinstance(item, dict) and item.get("_attachment_path")
    ]


def _attachment_limit(evidence: dict[str, Any]) -> int:
    value = evidence.get("_visual_attachment_limit")
    if isinstance(value, bool):
        return 4
    if isinstance(value, int):
        return max(0, min(value, 64))
    if isinstance(value, str) and value.strip().isdigit():
        return max(0, min(int(value), 64))
    return 4


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def _t2_anthropic_content(
    evidence: dict[str, Any],
    attachments: list[dict[str, str]],
) -> list[dict[str, Any]]:
    by_ref = {item["visual_ref"]: item for item in attachments}
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": "以下输入严格按页排列：每页图片之后紧跟该页客观事实。",
        }
    ]
    for packet in evidence.get("page_packets", []) or []:
        if not isinstance(packet, dict):
            continue
        page_ref = str(packet.get("page_ref") or "")
        attachment = by_ref.get(page_ref)
        content.append({"type": "text", "text": f"{page_ref} 图片"})
        if attachment is not None:
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
        content.append(
            {
                "type": "text",
                "text": _page_packet_text(packet),
            }
        )
    return content


def _t2_openai_content(
    evidence: dict[str, Any],
    attachments: list[dict[str, str]],
) -> list[dict[str, Any]]:
    by_ref = {item["visual_ref"]: item for item in attachments}
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": "以下输入严格按页排列：每页图片之后紧跟该页客观事实。",
        }
    ]
    for packet in evidence.get("page_packets", []) or []:
        if not isinstance(packet, dict):
            continue
        page_ref = str(packet.get("page_ref") or "")
        attachment = by_ref.get(page_ref)
        content.append({"type": "text", "text": f"{page_ref} 图片"})
        if attachment is not None:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            f"data:{attachment['media_type']};base64,"
                            f"{attachment['base64']}"
                        ),
                        "detail": "low",
                    },
                }
            )
        content.append({"type": "text", "text": _page_packet_text(packet)})
    return content


def _page_packet_text(packet: dict[str, Any]) -> str:
    public = {
        key: value
        for key, value in packet.items()
        if key != "image" and not str(key).startswith("_")
    }
    image = packet.get("image")
    if isinstance(image, dict):
        public["image_facts"] = {
            key: value
            for key, value in image.items()
            if not str(key).startswith("_")
        }
    return "本页客观事实：" + json.dumps(public, ensure_ascii=False)
