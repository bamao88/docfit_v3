from __future__ import annotations

import pytest

from docfit.core.io import write_json
from docfit.template_generation.agent.config import (
    AgentConfig,
    agent_config_from_env,
    live_provider_summary,
    validate_agent_config,
)
from docfit.template_generation.agent.loop import run_template_agent

from .helpers import round0_artifacts


def test_agent_config_default_disabled_passes() -> None:
    assert validate_agent_config(AgentConfig()) == []


def test_legacy_live_transport_is_rejected() -> None:
    errors = validate_agent_config(AgentConfig(enabled=True, transport="kimi"))

    assert any("legacy agent transport has been removed" in error for error in errors)


def test_replay_transport_requires_transcript(tmp_path) -> None:
    missing = tmp_path / "missing.json"
    errors = validate_agent_config(
        AgentConfig(enabled=True, transport="replay", transcript_path=missing)
    )

    assert any("transcript_path does not exist" in error for error in errors)


def test_observation_replay_satisfies_replay_transport(tmp_path) -> None:
    observation_transcript = tmp_path / "observation_replay.json"
    observation_transcript.write_text("{}", encoding="utf-8")

    errors = validate_agent_config(
        AgentConfig(
            enabled=True,
            observation_mode="replay",
            observation_transcript_path=observation_transcript,
        )
    )

    assert errors == []


def test_max_rounds_is_limited(tmp_path) -> None:
    transcript = tmp_path / "transcript.json"
    transcript.write_text("{}", encoding="utf-8")

    errors = validate_agent_config(
        AgentConfig(enabled=True, transcript_path=transcript, max_rounds=5)
    )

    assert any("max_rounds" in error for error in errors)


def test_live_generation_knobs_are_validated(tmp_path) -> None:
    transcript = tmp_path / "transcript.json"
    transcript.write_text("{}", encoding="utf-8")

    errors = validate_agent_config(
        AgentConfig(
            enabled=True,
            transcript_path=transcript,
            max_tokens=0,
            temperature=3,
        )
    )

    assert any("max_tokens" in error for error in errors)
    assert any("temperature" in error for error in errors)


def test_agent_config_from_env_reads_live_generation_knobs(tmp_path) -> None:
    render_packet = tmp_path / "packet.json"
    render_packet.write_text("{}", encoding="utf-8")

    config = agent_config_from_env(
        {
            "DOCFIT_TEMPLATE_AGENT_ENABLED": "1",
            "DOCFIT_TEMPLATE_AGENT_OBSERVATION_MODE": "live",
            "DOCFIT_TEMPLATE_AGENT_RENDER_PACKET": str(render_packet),
            "DOCFIT_TEMPLATE_AGENT_MAX_TOKENS": "2048",
            "DOCFIT_TEMPLATE_AGENT_TEMPERATURE": "0.25",
        }
    )

    assert config is not None
    assert config.max_tokens == 2048
    assert config.temperature == 0.25


def test_agent_config_from_env_reads_provider_orchestration_knobs() -> None:
    config = agent_config_from_env(
        {
            "DOCFIT_TEMPLATE_AGENT_ENABLED": "1",
            "DOCFIT_TEMPLATE_AGENT_OBSERVATION_MODE": "live",
            "DOCFIT_TEMPLATE_AGENT_TEXT_PROVIDER": "minimax",
            "DOCFIT_TEMPLATE_AGENT_TEXT_MODEL": "MiniMax-M3",
            "DOCFIT_TEMPLATE_AGENT_VISION_PROVIDER": "minimax",
            "DOCFIT_TEMPLATE_AGENT_VISION_MODEL": "MiniMax-M3-Vision",
        }
    )

    assert config is not None
    assert config.text_provider == "minimax"
    assert config.model == "MiniMax-M3"
    assert config.vision_provider == "minimax"
    assert config.vision_model == "MiniMax-M3-Vision"
    assert live_provider_summary(config) == ["minimax"]


def test_agent_config_from_env_does_not_enable_without_enabled_flag(tmp_path) -> None:
    render_packet = tmp_path / "packet.json"
    render_packet.write_text("{}", encoding="utf-8")

    config = agent_config_from_env(
        {
            "DOCFIT_TEMPLATE_AGENT_OBSERVATION_MODE": "live",
            "DOCFIT_TEMPLATE_AGENT_RENDER_PACKET": str(render_packet),
        }
    )

    assert config is not None
    assert config.enabled is False


def test_agent_config_from_env_reports_parse_errors_when_enabled() -> None:
    config = agent_config_from_env(
        {
            "DOCFIT_TEMPLATE_AGENT_ENABLED": "1",
            "DOCFIT_TEMPLATE_AGENT_MAX_ROUNDS": "many",
        }
    )

    assert config is not None
    errors = validate_agent_config(config)
    assert any("DOCFIT_TEMPLATE_AGENT_MAX_ROUNDS must be an integer" in error for error in errors)


def test_agent_config_from_env_reports_unsupported_provider_when_enabled() -> None:
    config = agent_config_from_env(
        {
            "DOCFIT_TEMPLATE_AGENT_ENABLED": "1",
            "DOCFIT_TEMPLATE_AGENT_OBSERVATION_MODE": "live",
            "DOCFIT_TEMPLATE_AGENT_TEXT_PROVIDER": "unknown-ai",
        }
    )

    assert config is not None
    errors = validate_agent_config(config)
    assert any("unsupported text live provider: unknown-ai" in error for error in errors)


def test_observation_live_can_request_auto_generated_render_packet() -> None:
    errors = validate_agent_config(
        AgentConfig(
            enabled=True,
            observation_mode="live",
            allow_live_without_render_packet=True,
        )
    )

    assert not any("render_packet_path" in error for error in errors)


def test_live_transport_rejects_projection_fallback_packet_before_sdk(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    packet_path = tmp_path / "packet.json"
    write_json(packet_path, artifacts["packet"])

    with pytest.raises(ValueError, match="real_render packet"):
        run_template_agent(
            source_template_docx=tmp_path / "template.docx",
            request=artifacts["request"],
            document_facts=artifacts["document_facts"],
            structure_candidates=artifacts["structure_candidates"],
            unit_map=artifacts["unit_map"],
            generation_model=artifacts["generation_model"],
            element_spec=artifacts["element_spec"],
            agent_config=AgentConfig(
                enabled=True,
                observation_mode="live",
                render_packet_path=packet_path,
            ),
        )
