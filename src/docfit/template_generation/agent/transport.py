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
                return None
            try:
                decoded = json.loads(content)
            except json.JSONDecodeError as exc:
                raise AgentTransportError(
                    f"{self.provider} response was not valid JSON after <think> cleanup"
                ) from exc
            if not isinstance(decoded, dict):
                raise AgentTransportError(f"{self.provider} response JSON must be an object")
            if tool_trace:
                decoded["_tool_trace"] = tool_trace
            return decoded
        raise AgentTransportError(
            f"{self.provider} exceeded max tool loop steps without a submission"
        )


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
