from __future__ import annotations

import json
from typing import Any

from .schema import empty_layered_submission


SUBMIT_TOOL_COLLECTIONS = {
    "submit_t2": ("t2", ["unit_candidates", "block_candidates", "boundary_adjustments"]),
    "submit_t3": ("t3", ["element_policy_candidates"]),
    "submit_t4": (
        "t4",
        ["section_profile_hints", "page_numbering_hints"],
    ),
}


def agent_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "view_pages",
                "description": "Inspect clean or annotated page render references.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page_nos": {"type": "array", "items": {"type": "integer"}},
                        "mode": {"type": "string", "enum": ["clean", "annotated"]},
                    },
                    "required": ["page_nos"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_text",
                "description": "Query visible source text by source_seq_refs, page_nos, or text_query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_seq_refs": {"type": "array", "items": {"type": "integer"}},
                        "page_nos": {"type": "array", "items": {"type": "integer"}},
                        "text_query": {"type": "string"},
                    },
                },
            },
        },
        _submit_tool("submit_t2", ["unit_candidates", "block_candidates", "boundary_adjustments"]),
        _submit_tool("submit_t3", ["element_policy_candidates"]),
        _submit_tool(
            "submit_t4",
            ["section_profile_hints", "page_numbering_hints"],
        ),
        {
            "type": "function",
            "function": {
                "name": "abstain",
                "description": "Abstain when evidence cannot be bound deterministically.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string"},
                        "open_questions": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["reason"],
                },
            },
        },
    ]


def _submit_tool(name: str, fields: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Submit structured {name} proposals.",
            "parameters": {
                "type": "object",
                "properties": {
                    field: {"type": "array", "items": {"type": "object"}}
                    for field in fields
                },
            },
        },
    }


def execute_agent_tool_call(
    name: str,
    arguments: dict[str, Any] | str | None,
    *,
    packet: dict[str, Any],
    round_id: str,
    model: str,
) -> dict[str, Any]:
    args = _decode_arguments(arguments)
    if args is None:
        return _tool_error(name, "tool arguments must be a JSON object")
    if name == "view_pages":
        return _tool_result(name, _view_pages(packet, args))
    if name == "query_text":
        return _tool_result(name, _query_text(packet, args))
    if name in SUBMIT_TOOL_COLLECTIONS:
        return _submission_result(
            name,
            _submission_from_submit_tool(
                name,
                args,
                packet=packet,
                round_id=round_id,
                model=model,
            ),
        )
    if name == "abstain":
        return _submission_result(
            name,
            _abstain_submission(
                args,
                packet=packet,
                round_id=round_id,
                model=model,
            ),
        )
    return _tool_error(name, f"unsupported tool: {name}")


def _decode_arguments(arguments: dict[str, Any] | str | None) -> dict[str, Any] | None:
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return arguments
    try:
        decoded = json.loads(arguments)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _view_pages(packet: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    page_nos = _int_set(args.get("page_nos")) or _packet_pages(packet)
    mode = str(args.get("mode") or "annotated")
    if mode not in {"clean", "annotated"}:
        mode = "annotated"
    key = "clean_page_images" if mode == "clean" else "annotated_page_images"
    by_page = {
        int(item.get("page_no") or 0): item
        for item in packet.get("render_artifacts", {}).get(key, [])
        if isinstance(item, dict)
    }
    return {
        "render_status": packet.get("render_status"),
        "mode": mode,
        "pages": [
            {
                "page_no": page_no,
                "artifact": by_page.get(page_no),
                "available": page_no in by_page,
            }
            for page_no in sorted(page_nos)
        ],
    }


def _query_text(packet: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    source_seq_refs = _int_set(args.get("source_seq_refs"))
    page_nos = _int_set(args.get("page_nos"))
    text_query = str(args.get("text_query") or "").strip().casefold()
    matches: list[dict[str, Any]] = []
    for item in packet.get("page_text_index", []):
        if not isinstance(item, dict):
            continue
        source_seq = _int_or_none(item.get("source_seq"))
        page_no = _int_or_none(item.get("page_no"))
        if source_seq_refs and source_seq not in source_seq_refs:
            continue
        if page_nos and page_no not in page_nos:
            continue
        if text_query and text_query not in str(item.get("text") or "").casefold():
            continue
        matches.append(
            {
                "source_seq": source_seq,
                "source_ref": item.get("source_ref"),
                "text": item.get("text"),
                "page_no": page_no,
                "bbox": item.get("bbox"),
                "render_target_id": item.get("render_target_id"),
                "render_binding_status": item.get("render_binding_status"),
            }
        )
    return {
        "match_count": len(matches),
        "items": matches[:50],
        "truncated": len(matches) > 50,
    }


def _submission_from_submit_tool(
    name: str,
    args: dict[str, Any],
    *,
    packet: dict[str, Any],
    round_id: str,
    model: str,
) -> dict[str, Any]:
    layer, collections = SUBMIT_TOOL_COLLECTIONS[name]
    submission = empty_layered_submission(
        source_render_hash=str(packet.get("source_render_hash") or ""),
        round_id=round_id,
        model=model,
    )
    for collection in collections:
        value = args.get(collection, [])
        submission["layers"][layer][collection] = value if isinstance(value, list) else []
    return submission


def _abstain_submission(
    args: dict[str, Any],
    *,
    packet: dict[str, Any],
    round_id: str,
    model: str,
) -> dict[str, Any]:
    submission = empty_layered_submission(
        source_render_hash=str(packet.get("source_render_hash") or ""),
        round_id=round_id,
        model=model,
    )
    open_questions = args.get("open_questions", [])
    if not isinstance(open_questions, list):
        open_questions = []
    for layer in ("t2", "t3", "t4"):
        submission["layers"][layer]["open_questions"] = open_questions
    submission["abstain"] = True
    submission["abstain_reason"] = str(args.get("reason") or "")
    return submission


def _tool_result(name: str, content: dict[str, Any]) -> dict[str, Any]:
    return {"tool": name, "ok": True, "terminal": False, "content": content}


def _submission_result(name: str, submission: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool": name,
        "ok": True,
        "terminal": True,
        "content": {"submitted": True, "round_id": submission.get("round_id")},
        "submission": submission,
    }


def _tool_error(name: str, message: str) -> dict[str, Any]:
    return {
        "tool": name,
        "ok": False,
        "terminal": False,
        "content": {"error": message},
    }


def _packet_pages(packet: dict[str, Any]) -> set[int]:
    pages = {
        page_no
        for item in packet.get("page_text_index", [])
        if isinstance(item, dict)
        for page_no in [_int_or_none(item.get("page_no"))]
        if page_no is not None
    }
    return pages or {1}


def _int_set(value: Any) -> set[int]:
    if not isinstance(value, list):
        return set()
    result: set[int] = set()
    for item in value:
        parsed = _int_or_none(item)
        if parsed is not None:
            result.add(parsed)
    return result


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
