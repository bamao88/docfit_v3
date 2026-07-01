from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Literal, Mapping


AgentTransportName = Literal["replay", "kimi", "minimax"]
LIVE_TRANSPORTS = {"kimi", "minimax"}
SUPPORTED_TRANSPORTS = {"replay", *LIVE_TRANSPORTS}


class AgentConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AgentConfig:
    enabled: bool = False
    transport: AgentTransportName = "replay"
    max_rounds: int = 4
    max_tokens: int = 4000
    temperature: float = 1
    parse_errors: tuple[str, ...] = ()
    transcript_path: Path | None = None
    render_packet_path: Path | None = None
    observation_bundle_path: Path | None = None
    allow_live_without_render_packet: bool = False
    allow_live_without_real_render: bool = False
    model: str | None = None


def validate_agent_config(config: AgentConfig) -> list[str]:
    if not config.enabled:
        return []

    errors: list[str] = []
    errors.extend(config.parse_errors)
    if config.transport not in SUPPORTED_TRANSPORTS:
        errors.append(f"unsupported agent transport: {config.transport}")
    if config.max_rounds < 1 or config.max_rounds > 4:
        errors.append("agent max_rounds must be between 1 and 4")
    if config.max_tokens < 1:
        errors.append("agent max_tokens must be greater than 0")
    if config.temperature < 0 or config.temperature > 2:
        errors.append("agent temperature must be between 0 and 2")
    if config.transport == "replay" and config.observation_bundle_path is None:
        if config.transcript_path is None:
            errors.append("replay agent requires transcript_path")
        elif not config.transcript_path.exists():
            errors.append(f"agent transcript_path does not exist: {config.transcript_path}")
    if config.transport in LIVE_TRANSPORTS:
        if (
            config.render_packet_path is None
            and not config.allow_live_without_render_packet
        ):
            errors.append(
                "live agent transport requires render_packet_path or "
                "allow_live_without_render_packet=true for auto-generated real_render input"
            )
    if config.render_packet_path is not None and not config.render_packet_path.exists():
        errors.append(f"agent render_packet_path does not exist: {config.render_packet_path}")
    if config.observation_bundle_path is not None and not config.observation_bundle_path.exists():
        errors.append(f"agent observation_bundle_path does not exist: {config.observation_bundle_path}")
    return errors


def require_valid_agent_config(config: AgentConfig) -> None:
    errors = validate_agent_config(config)
    if errors:
        raise AgentConfigError("; ".join(errors))


def agent_config_from_env(env: Mapping[str, str] | None = None) -> AgentConfig | None:
    values = env or os.environ
    enabled_value = values.get("DOCFIT_TEMPLATE_AGENT_ENABLED")
    provider = values.get("DOCFIT_TEMPLATE_AGENT_PROVIDER")
    transcript = values.get("DOCFIT_TEMPLATE_AGENT_TRANSCRIPT")
    render_packet = values.get("DOCFIT_TEMPLATE_AGENT_RENDER_PACKET")
    observation_bundle = values.get("DOCFIT_TEMPLATE_AGENT_OBSERVATION_BUNDLE")
    max_rounds = values.get("DOCFIT_TEMPLATE_AGENT_MAX_ROUNDS")
    max_tokens = values.get("DOCFIT_TEMPLATE_AGENT_MAX_TOKENS")
    temperature = values.get("DOCFIT_TEMPLATE_AGENT_TEMPERATURE")
    model = values.get("DOCFIT_TEMPLATE_AGENT_MODEL")
    allow_projection = values.get("DOCFIT_TEMPLATE_AGENT_ALLOW_PROJECTION_RENDER")

    if not any(
        [
            enabled_value,
            provider,
            transcript,
            render_packet,
            observation_bundle,
            max_rounds,
            max_tokens,
            temperature,
            model,
            allow_projection,
        ]
    ):
        return None

    enabled = str(enabled_value or "").strip().lower() in {"1", "true", "yes", "on"}
    parse_errors: list[str] = []
    rounds = _parse_int_setting(
        max_rounds,
        default=4,
        name="DOCFIT_TEMPLATE_AGENT_MAX_ROUNDS",
        errors=parse_errors,
    )
    tokens = _parse_int_setting(
        max_tokens,
        default=4000,
        name="DOCFIT_TEMPLATE_AGENT_MAX_TOKENS",
        errors=parse_errors,
    )
    temp = _parse_float_setting(
        temperature,
        default=1.0,
        name="DOCFIT_TEMPLATE_AGENT_TEMPERATURE",
        errors=parse_errors,
    )
    transport = str(provider or "replay").strip().lower()

    return AgentConfig(
        enabled=enabled,
        transport=transport,  # type: ignore[arg-type]
        max_rounds=rounds,
        max_tokens=tokens,
        temperature=temp,
        parse_errors=tuple(parse_errors),
        transcript_path=Path(transcript) if transcript else None,
        render_packet_path=Path(render_packet) if render_packet else None,
        observation_bundle_path=Path(observation_bundle) if observation_bundle else None,
        allow_live_without_real_render=str(allow_projection or "").strip().lower()
        in {"1", "true", "yes", "on"},
        model=model,
    )


def _parse_int_setting(
    value: str | None,
    *,
    default: int,
    name: str,
    errors: list[str],
) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except ValueError:
        errors.append(f"{name} must be an integer")
        return default


def _parse_float_setting(
    value: str | None,
    *,
    default: float,
    name: str,
    errors: list[str],
) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except ValueError:
        errors.append(f"{name} must be a number")
        return default
