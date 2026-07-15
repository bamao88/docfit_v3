from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Protocol


ToolExecutor = Callable[[str, dict[str, Any] | str | None], dict[str, Any]]
TERMINAL_TOOL_NAMES = {"submit_t2", "submit_t3", "submit_t4", "abstain"}
TERMINAL_TOOL_INSTRUCTION = (
    "DocFit terminal tool instruction: evidence inspection is complete for this "
    "round. Call exactly one available terminal tool now: submit_t2, submit_t3, "
    "submit_t4, or abstain. Do not write prose or continue analysis."
)
TERMINAL_JSON_INSTRUCTION = (
    "DocFit terminal JSON instruction: return exactly one JSON object matching "
    "the template-agent-layered-submission-1.0 schema now. Include "
    "source_render_hash and round_id from the current context. If there is no "
    "high-confidence evidence-bound proposal for the active pass, set abstain "
    "to true and include an abstain_reason. Do not write prose."
)
PROPOSAL_KIND_BY_COLLECTION = {
    "unit_candidates": "unit_candidate",
    "block_candidates": "block_candidate",
    "boundary_adjustments": "boundary_adjustment",
    "element_policy_candidates": "element_policy_candidate",
    "section_profile_hints": "section_profile_hint",
    "page_numbering_hints": "page_numbering_hint",
}
T2_COLLECTION_BY_OPERATION = {
    "add_unit": "unit_candidates",
    "relabel_unit": "unit_candidates",
    "adjust_unit_range": "boundary_adjustments",
    "replace_unit_elements": "block_candidates",
}


class AgentTransport(Protocol):
    def complete_round(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        response_format: dict[str, Any] | None,
        max_tokens: int,
        temperature: float,
        tool_executor: ToolExecutor | None = None,
    ) -> dict[str, Any] | None:
        ...


class AgentTransportError(RuntimeError):
    pass


def strip_think(content: str) -> str:
    return re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL | re.I).strip()


class OpenAICompatibleTransport:
    def __init__(
        self,
        *,
        provider: str,
        api_key_env: str,
        default_base_url: str,
        default_model: str,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int = 120,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self.provider = provider
        self.api_key = api_key or os.environ.get(api_key_env)
        self.model = model or os.environ.get(f"{provider.upper()}_MODEL") or default_model
        self.base_url = (
            base_url
            or os.environ.get(f"{provider.upper()}_BASE_URL")
            or default_base_url
        )
        self.timeout = timeout
        self.default_headers = default_headers or {}
        if not self.api_key:
            raise AgentTransportError(f"{api_key_env} is required for {provider} live transport")

    def complete_round(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        response_format: dict[str, Any] | None,
        max_tokens: int,
        temperature: float = 1,
        tool_executor: ToolExecutor | None = None,
    ) -> dict[str, Any] | None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AgentTransportError(
                "openai package is required for live agent transport"
            ) from exc

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            default_headers=self.default_headers,
        )
        conversation = list(messages)
        tool_trace: list[dict[str, Any]] = []
        max_tool_steps = 12
        for _step_index in range(max_tool_steps + 1):
            active_tools = _active_tools_for_step(tools, tool_trace=tool_trace)
            if tool_trace:
                _ensure_terminal_tool_instruction(conversation)
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": conversation,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if active_tools:
                kwargs["tools"] = active_tools
            elif response_format is not None:
                kwargs["response_format"] = response_format
            completion = client.chat.completions.create(**kwargs)
            choice = completion.choices[0]
            message = choice.message
            tool_calls = _message_tool_calls(message)
            if tool_calls:
                if tool_executor is None:
                    raise AgentTransportError(
                        f"{self.provider} returned tool_calls without a tool executor"
                    )
                conversation.append(_assistant_tool_call_message(message, tool_calls))
                for call in tool_calls:
                    name = _tool_call_name(call)
                    arguments = _tool_call_arguments(call)
                    result = tool_executor(name, arguments)
                    tool_trace.append(
                        {
                            "tool_call_id": _tool_call_id(call),
                            "tool_name": name,
                            "arguments": _decode_trace_arguments(arguments),
                            "result": _trace_result(result),
                        }
                    )
                    if result.get("submission"):
                        submission = result["submission"]
                        if isinstance(submission, dict):
                            submission = _normalize_submission(
                                submission,
                                model=self.model,
                            )
                            submission["_tool_trace"] = tool_trace
                        return submission
                    conversation.append(
                        {
                            "role": "tool",
                            "tool_call_id": _tool_call_id(call),
                            "content": json.dumps(
                                result.get("content", result),
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ),
                        }
                    )
                continue

            content = strip_think(_message_content(message) or "")
            if not content:
                if tool_trace:
                    return self._complete_terminal_json(
                        client=client,
                        conversation=conversation,
                        response_format=response_format,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        tool_trace=tool_trace,
                    )
                return None
            try:
                decoded = json.loads(content)
            except json.JSONDecodeError as exc:
                if tool_trace:
                    conversation.append({"role": "assistant", "content": content})
                    return self._complete_terminal_json(
                        client=client,
                        conversation=conversation,
                        response_format=response_format,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        tool_trace=tool_trace,
                    )
                raise AgentTransportError(
                    f"{self.provider} response was not valid JSON after <think> cleanup"
                ) from exc
            if not isinstance(decoded, dict):
                raise AgentTransportError(f"{self.provider} response JSON must be an object")
            decoded = _unwrap_submission_object(decoded)
            decoded = _normalize_submission(decoded, model=self.model)
            if tool_trace:
                decoded["_tool_trace"] = tool_trace
            return decoded
        raise AgentTransportError(
            f"{self.provider} exceeded max tool loop steps without a submission"
        )

    def _complete_terminal_json(
        self,
        *,
        client: Any,
        conversation: list[dict[str, Any]],
        response_format: dict[str, Any] | None,
        max_tokens: int,
        temperature: float,
        tool_trace: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        final_messages = _terminal_json_messages(
            conversation,
            tool_trace=tool_trace,
        )
        completion = client.chat.completions.create(
            model=self.model,
            messages=final_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format or {"type": "json_object"},
        )
        message = completion.choices[0].message
        content = strip_think(_message_content(message) or "")
        if not content:
            fallback = _provider_failure_submission(
                conversation,
                model=self.model,
                reason="provider returned no terminal JSON content",
            )
            fallback["_tool_trace"] = tool_trace
            return fallback
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError as exc:
            fallback = _provider_failure_submission(
                conversation,
                model=self.model,
                reason=(
                    f"{self.provider} terminal JSON fallback was not valid JSON: "
                    f"{exc.msg}"
                ),
            )
            fallback["_tool_trace"] = tool_trace
            return fallback
        if not isinstance(decoded, dict):
            fallback = _provider_failure_submission(
                conversation,
                model=self.model,
                reason=f"{self.provider} terminal JSON fallback was not an object",
            )
            fallback["_tool_trace"] = tool_trace
            return fallback
        decoded = _unwrap_submission_object(decoded)
        decoded = _normalize_submission(decoded, model=self.model)
        decoded["_tool_trace"] = tool_trace
        return decoded


def _normalize_submission(
    submission: dict[str, Any],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    if model and (
        not submission.get("model")
        or submission.get("model") == "provider-model-name"
    ):
        submission["model"] = model
    layers = submission.get("layers")
    if not isinstance(layers, dict):
        return submission
    _normalize_t2_collections(layers)
    for layer_name, layer_value in layers.items():
        if not isinstance(layer_value, dict):
            continue
        for collection, expected_kind in PROPOSAL_KIND_BY_COLLECTION.items():
            proposals = layer_value.get(collection)
            if not isinstance(proposals, list):
                continue
            for index, proposal in enumerate(proposals, start=1):
                if not isinstance(proposal, dict):
                    continue
                proposal.setdefault("kind", expected_kind)
                if not proposal.get("proposal_id"):
                    proposal["proposal_id"] = (
                        f"{submission.get('round_id') or 'round'}_"
                        f"{layer_name}_{collection}_{index:03d}"
                    )
                operation = str(proposal.get("operation") or "").strip()
                if (
                    layer_name == "t2"
                    and operation
                    and operation != "add_unit"
                    and not proposal.get("target_unit_id")
                    and proposal.get("unit_id")
                ):
                    proposal["target_unit_id"] = proposal.get("unit_id")
                if not proposal.get("source_seq_refs"):
                    source_seq_refs = _source_seq_refs_from_evidence(proposal)
                    if source_seq_refs:
                        proposal["source_seq_refs"] = source_seq_refs
    return submission


def _normalize_t2_collections(layers: dict[str, Any]) -> None:
    t2 = layers.get("t2")
    if not isinstance(t2, dict):
        return
    relocated: dict[str, list[dict[str, Any]]] = {
        "unit_candidates": [],
        "block_candidates": [],
        "boundary_adjustments": [],
    }
    changed = False
    for collection in relocated:
        proposals = t2.get(collection)
        if not isinstance(proposals, list):
            t2[collection] = []
            continue
        for proposal in proposals:
            if not isinstance(proposal, dict):
                relocated[collection].append(proposal)
                continue
            operation = str(proposal.get("operation") or "").strip()
            target_collection = T2_COLLECTION_BY_OPERATION.get(operation, collection)
            if target_collection != collection:
                changed = True
            relocated[target_collection].append(proposal)
    if changed:
        for collection, proposals in relocated.items():
            t2[collection] = proposals


def _terminal_json_messages(
    conversation: list[dict[str, Any]],
    *,
    tool_trace: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    payload = _prompt_payload_from_conversation(conversation)
    final_payload = {
        "round_index": payload.get("round_index"),
        "pass": payload.get("pass"),
        "prompt_contract": payload.get("prompt_contract"),
        "request": payload.get("request"),
        "packet": _finalizer_packet_summary(payload.get("packet")),
        "tool_evidence": _summarize_tool_trace(tool_trace),
        "required_output": _layered_submission_shape(
            source_render_hash=str(
                (payload.get("packet") or {}).get("source_render_hash") or ""
            )
        ),
    }
    return [
        {
            "role": "system",
            "content": (
                "You are a DocFit terminal submission writer. Return compact "
                "JSON only. Do not reason in prose."
            ),
        },
        {
            "role": "user",
            "content": (
                TERMINAL_JSON_INSTRUCTION
                + "\nFinalizer JSON context follows.\n"
                + json.dumps(final_payload, ensure_ascii=False, separators=(",", ":"))
            ),
        },
    ]


def _prompt_payload_from_conversation(
    conversation: list[dict[str, Any]],
) -> dict[str, Any]:
    marker = "Context JSON follows.\n"
    for message in conversation:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str) or marker not in content:
            continue
        raw = content.split(marker, 1)[1]
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded
    return {}


def _provider_failure_submission(
    conversation: list[dict[str, Any]],
    *,
    model: str,
    reason: str,
) -> dict[str, Any]:
    payload = _prompt_payload_from_conversation(conversation)
    packet = payload.get("packet") if isinstance(payload.get("packet"), dict) else {}
    pass_spec = payload.get("pass") if isinstance(payload.get("pass"), dict) else {}
    round_index = _int_or_none(payload.get("round_index")) or 1
    allowed_layers = [
        str(layer)
        for layer in pass_spec.get("allowed_layers", []) or []
        if str(layer) in {"t2", "t3", "t4"}
    ] or ["t2", "t3", "t4"]
    submission = _layered_submission_shape(
        source_render_hash=str(packet.get("source_render_hash") or "")
    )
    submission["round_id"] = f"round_{round_index:03d}"
    submission["model"] = model
    question = {
        "question_id": f"provider_failure_{round_index:03d}",
        "blocking": True,
        "question": reason,
        "required_human_action": (
            "Review provider reasoning-only failure before accepting this "
            "agent pass as having no proposals."
        ),
    }
    for layer in allowed_layers:
        layer_value = submission["layers"].get(layer)
        if isinstance(layer_value, dict):
            layer_value["open_questions"] = [question]
    return submission


def _finalizer_packet_summary(packet: Any) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {}
    return {
        "source_render_hash": packet.get("source_render_hash"),
        "render_status": packet.get("render_status"),
        "page_index_summary": packet.get("page_index_summary"),
        "text_outline": {
            "scope": (packet.get("text_outline") or {}).get("scope")
            if isinstance(packet.get("text_outline"), dict)
            else None,
            "total_matching_items": (packet.get("text_outline") or {}).get(
                "total_matching_items"
            )
            if isinstance(packet.get("text_outline"), dict)
            else None,
            "truncated": (packet.get("text_outline") or {}).get("truncated")
            if isinstance(packet.get("text_outline"), dict)
            else None,
        },
        "optional_reference": packet.get("optional_reference"),
    }


def _layered_submission_shape(*, source_render_hash: str) -> dict[str, Any]:
    return {
        "schema_version": "template-agent-layered-submission-1.0",
        "prompt_version": "template-agent-prompt-1.0",
        "source_render_hash": source_render_hash,
        "round_id": "round_001",
        "model": "provider-model-name",
        "layers": {
            "t2": {
                "unit_candidates": [],
                "block_candidates": [],
                "boundary_adjustments": [],
                "open_questions": [],
            },
            "t3": {
                "element_policy_candidates": [],
                "open_questions": [],
            },
            "t4": {
                "section_profile_hints": [],
                "page_numbering_hints": [],
                "open_questions": [],
            },
        },
        "abstain": False,
    }


def _summarize_tool_trace(tool_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remaining_items = 80
    summaries = []
    for item in tool_trace:
        result = item.get("result") if isinstance(item, dict) else {}
        content = result.get("content") if isinstance(result, dict) else {}
        if not isinstance(content, dict):
            content = {}
        summary = {
            "tool_name": item.get("tool_name"),
            "arguments": item.get("arguments"),
            "ok": result.get("ok") if isinstance(result, dict) else None,
            "terminal": result.get("terminal") if isinstance(result, dict) else None,
        }
        if item.get("tool_name") == "query_text":
            items = []
            for match in content.get("items", []) or []:
                if remaining_items <= 0 or not isinstance(match, dict):
                    break
                items.append(
                    {
                        "source_seq": match.get("source_seq"),
                        "page_no": match.get("page_no"),
                        "render_target_id": match.get("render_target_id"),
                        "text": _truncate(str(match.get("text") or ""), 180),
                    }
                )
                remaining_items -= 1
            summary["content"] = {
                "match_count": content.get("match_count"),
                "truncated": content.get("truncated"),
                "items": items,
            }
        elif item.get("tool_name") == "view_pages":
            pages = []
            for page in content.get("pages", []) or []:
                if remaining_items <= 0 or not isinstance(page, dict):
                    break
                artifact = page.get("artifact") if isinstance(page.get("artifact"), dict) else {}
                pages.append(
                    {
                        "page_no": page.get("page_no"),
                        "available": page.get("available"),
                        "artifact_path": artifact.get("path"),
                        "artifact_sha256": artifact.get("sha256"),
                    }
                )
                remaining_items -= 1
            summary["content"] = {
                "render_status": content.get("render_status"),
                "mode": content.get("mode"),
                "pages": pages,
            }
        else:
            summary["content_keys"] = sorted(content.keys())
        summaries.append(summary)
    return summaries


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _source_seq_refs_from_evidence(proposal: dict[str, Any]) -> list[int]:
    refs: list[int] = []
    for evidence in proposal.get("evidence", []) or []:
        if not isinstance(evidence, dict):
            continue
        evidence_type = str(evidence.get("type") or "").strip()
        if evidence_type and evidence_type != "source_seq":
            continue
        ref = _int_or_none(evidence.get("source_seq"))
        if ref is None:
            ref = _int_or_none(evidence.get("ref"))
        if ref is not None and ref not in refs:
            refs.append(ref)
    return refs


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _unwrap_submission_object(decoded: dict[str, Any]) -> dict[str, Any]:
    submission = decoded.get("submission")
    if isinstance(submission, dict):
        return submission
    return decoded


def _active_tools_for_step(
    tools: list[dict[str, Any]],
    *,
    tool_trace: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not tool_trace:
        return tools
    terminal_tools = [
        tool
        for tool in tools
        if _tool_schema_name(tool) in TERMINAL_TOOL_NAMES
    ]
    return terminal_tools or tools


def _ensure_terminal_tool_instruction(conversation: list[dict[str, Any]]) -> None:
    for message in reversed(conversation):
        content = message.get("content")
        if isinstance(content, str) and content.startswith(
            "DocFit terminal tool instruction:"
        ):
            return
    conversation.append({"role": "user", "content": TERMINAL_TOOL_INSTRUCTION})


def _tool_schema_name(tool: dict[str, Any]) -> str:
    function = tool.get("function") if isinstance(tool, dict) else None
    if not isinstance(function, dict):
        return ""
    return str(function.get("name") or "")


class KimiOpenAICompatibleTransport(OpenAICompatibleTransport):
    provider = "kimi"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "kimi-for-coding",
        base_url: str = "https://api.kimi.com/coding/v1",
        timeout: int = 120,
    ) -> None:
        super().__init__(
            provider="kimi",
            api_key_env="KIMI_API_KEY",
            default_base_url=base_url,
            default_model=model,
            api_key=api_key,
            timeout=timeout,
            default_headers={
                "User-Agent": "claude-cli/2.0.0 (external, darwin)",
                "X-Client-Type": "claude-code",
            },
        )


class MinimaxOpenAICompatibleTransport(OpenAICompatibleTransport):
    provider = "minimax"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "minimax-text-01",
        base_url: str = "",
        timeout: int = 120,
    ) -> None:
        super().__init__(
            provider="minimax",
            api_key_env="MINIMAX_API_KEY",
            default_base_url=base_url,
            default_model=model,
            api_key=api_key,
            timeout=timeout,
        )
        if not self.base_url:
            raise AgentTransportError(
                "MINIMAX_BASE_URL is required for Minimax OpenAI-compatible transport"
            )


def _message_content(message: Any) -> str | None:
    value = _get(message, "content")
    return value if isinstance(value, str) else None


def _message_tool_calls(message: Any) -> list[Any]:
    tool_calls = _get(message, "tool_calls") or []
    return list(tool_calls) if isinstance(tool_calls, list) else []


def _assistant_tool_call_message(message: Any, tool_calls: list[Any]) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": _message_content(message) or "",
        "tool_calls": [
            {
                "id": _tool_call_id(call),
                "type": _get(call, "type") or "function",
                "function": {
                    "name": _tool_call_name(call),
                    "arguments": _tool_call_arguments(call) or "{}",
                },
            }
            for call in tool_calls
        ],
    }


def _tool_call_id(call: Any) -> str:
    return str(_get(call, "id") or "tool_call")


def _tool_call_name(call: Any) -> str:
    function = _get(call, "function") or {}
    return str(_get(function, "name") or "")


def _tool_call_arguments(call: Any) -> str | None:
    function = _get(call, "function") or {}
    value = _get(function, "arguments")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return None


def _get(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _decode_trace_arguments(arguments: str | None) -> dict[str, Any] | str | None:
    if not arguments:
        return {}
    try:
        decoded = json.loads(arguments)
    except json.JSONDecodeError:
        return arguments
    return decoded


def _trace_result(result: dict[str, Any]) -> dict[str, Any]:
    trace = dict(result)
    if "submission" in trace:
        submission = trace.pop("submission")
        if isinstance(submission, dict):
            trace["submission_round_id"] = submission.get("round_id")
            trace["submission_abstain"] = submission.get("abstain", False)
    return trace
