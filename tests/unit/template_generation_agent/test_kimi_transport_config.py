from __future__ import annotations

import pytest

from docfit.template_generation.agent.transport import (
    AgentTransportError,
    KimiOpenAICompatibleTransport,
    strip_think,
)


def test_strip_think_removes_kimi_reasoning_prefix() -> None:
    assert strip_think("<think>hidden</think>\n{\"ok\": true}") == "{\"ok\": true}"


def test_kimi_transport_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("KIMI_API_KEY", raising=False)

    with pytest.raises(AgentTransportError):
        KimiOpenAICompatibleTransport()
