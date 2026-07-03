from __future__ import annotations

from typing import Any

from docfit.core.io import read_json

from .config import AgentConfig
from .observation_config import ObservationConfig
from .observation_live import LiveResponder, build_kimi_client
from .observation_loop import run_observation_pipeline


def run_module1_observation_for_template_generate(
    *,
    packet: dict[str, Any],
    agent_config: AgentConfig,
) -> dict[str, Any] | None:
    """Produce or load a Module 1 observation bundle for the current run packet."""

    mode = _effective_observation_mode(agent_config)
    if mode == "off":
        return None
    if mode == "bundle":
        assert agent_config.observation_bundle_path is not None
        return read_json(agent_config.observation_bundle_path)
    if mode == "replay":
        assert agent_config.observation_transcript_path is not None
        transcript = read_json(agent_config.observation_transcript_path)
        return run_observation_pipeline(
            packet=packet,
            transcript=transcript,
            config=ObservationConfig(
                enabled=True,
                self_consistency_samples=1,
                model=agent_config.model or "replay",
            ),
            t3_concurrency=agent_config.observation_t3_concurrency,
        )
    if mode == "live":
        client, default_model = build_kimi_client()
        model = agent_config.model or default_model
        responder = LiveResponder(
            client=client,
            model=model,
            temperature=agent_config.temperature,
            max_tokens=agent_config.max_tokens,
            cache_dir=agent_config.observation_cache_dir,
        )
        return run_observation_pipeline(
            packet=packet,
            responder=responder,
            config=ObservationConfig(enabled=True, model=model),
            t3_concurrency=agent_config.observation_t3_concurrency,
        )
    raise ValueError(f"unsupported observation mode: {mode}")


def _effective_observation_mode(agent_config: AgentConfig) -> str:
    if agent_config.observation_bundle_path is not None:
        return "bundle"
    return str(agent_config.observation_mode or "off")
