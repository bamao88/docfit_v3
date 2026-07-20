from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Literal, Mapping

from .api_config import default_live_provider


AgentTransportName = Literal["replay"]
AgentTextProviderName = Literal["kimi", "minimax"]
AgentVisionProviderName = Literal["minimax"]
ObservationMode = Literal["off", "bundle", "replay", "live"]
SUPPORTED_OBSERVATION_MODES = {"off", "bundle", "replay", "live"}
SUPPORTED_TEXT_PROVIDERS = {"kimi", "minimax"}
SUPPORTED_VISION_PROVIDERS = {"minimax"}


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
    observation_mode: ObservationMode = "off"
    observation_transcript_path: Path | None = None
    observation_cache_dir: Path | None = None
    observation_t3_concurrency: int = 1
    allow_live_without_render_packet: bool = False
    allow_live_without_real_render: bool = False
    model: str | None = None
    text_provider: AgentTextProviderName | None = None
    vision_provider: AgentVisionProviderName | None = None
    vision_model: str | None = None


def validate_agent_config(config: AgentConfig) -> list[str]:
    if not config.enabled:
        return []

    errors: list[str] = []
    errors.extend(config.parse_errors)
    if config.transport != "replay":
        errors.append(
            "legacy agent transport has been removed; use observation_mode=live, "
            "observation_mode=replay, or observation_mode=bundle"
        )
    text_provider = effective_text_provider(config)
    vision_provider = effective_vision_provider(config)
    if text_provider not in SUPPORTED_TEXT_PROVIDERS:
        errors.append(f"unsupported text live provider: {text_provider}")
    if vision_provider not in SUPPORTED_VISION_PROVIDERS:
        errors.append(f"unsupported vision live provider: {vision_provider}")
    if config.observation_mode not in SUPPORTED_OBSERVATION_MODES:
        errors.append(f"unsupported observation_mode: {config.observation_mode}")
    if config.max_rounds < 1 or config.max_rounds > 4:
        errors.append("agent max_rounds must be between 1 and 4")
    if config.max_tokens < 1:
        errors.append("agent max_tokens must be greater than 0")
    if config.temperature < 0 or config.temperature > 2:
        errors.append("agent temperature must be between 0 and 2")
    if config.observation_t3_concurrency < 1:
        errors.append("agent observation_t3_concurrency must be greater than 0")
    if (
        config.observation_mode == "off"
        and config.observation_bundle_path is None
        and config.transcript_path is None
    ):
        errors.append(
            "enabled agent requires observation_mode=live, replay, or bundle"
        )
    if config.transcript_path is not None and not config.transcript_path.exists():
        errors.append(f"agent transcript_path does not exist: {config.transcript_path}")
    if config.observation_mode == "bundle" and config.observation_bundle_path is None:
        errors.append("bundle observation mode requires observation_bundle_path")
    if config.observation_mode == "replay":
        if config.observation_transcript_path is None:
            errors.append("replay observation mode requires observation_transcript_path")
        elif not config.observation_transcript_path.exists():
            errors.append(
                "agent observation_transcript_path does not exist: "
                f"{config.observation_transcript_path}"
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
    text_provider = values.get("DOCFIT_TEMPLATE_AGENT_TEXT_PROVIDER")
    vision_provider = values.get("DOCFIT_TEMPLATE_AGENT_VISION_PROVIDER")
    transcript = values.get("DOCFIT_TEMPLATE_AGENT_TRANSCRIPT")
    render_packet = values.get("DOCFIT_TEMPLATE_AGENT_RENDER_PACKET")
    observation_bundle = values.get("DOCFIT_TEMPLATE_AGENT_OBSERVATION_BUNDLE")
    observation_mode_value = values.get("DOCFIT_TEMPLATE_AGENT_OBSERVATION_MODE")
    observation_replay = values.get("DOCFIT_TEMPLATE_AGENT_OBSERVATION_REPLAY")
    observation_cache_dir = values.get("DOCFIT_TEMPLATE_AGENT_OBSERVATION_CACHE_DIR")
    max_rounds = values.get("DOCFIT_TEMPLATE_AGENT_MAX_ROUNDS")
    max_tokens = values.get("DOCFIT_TEMPLATE_AGENT_MAX_TOKENS")
    temperature = values.get("DOCFIT_TEMPLATE_AGENT_TEMPERATURE")
    model = values.get("DOCFIT_TEMPLATE_AGENT_MODEL")
    text_model = values.get("DOCFIT_TEMPLATE_AGENT_TEXT_MODEL")
    vision_model = values.get("DOCFIT_TEMPLATE_AGENT_VISION_MODEL")
    allow_projection = values.get("DOCFIT_TEMPLATE_AGENT_ALLOW_PROJECTION_RENDER")

    if not any(
        [
            enabled_value,
            text_provider,
            vision_provider,
            transcript,
            render_packet,
            observation_bundle,
            observation_mode_value,
            observation_replay,
            observation_cache_dir,
            max_rounds,
            max_tokens,
            temperature,
            model,
            text_model,
            vision_model,
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
    observation_mode = _infer_observation_mode(
        observation_mode_value=observation_mode_value,
        observation_replay=observation_replay,
        observation_bundle=observation_bundle,
    )

    return AgentConfig(
        enabled=enabled,
        transport="replay",
        max_rounds=rounds,
        max_tokens=tokens,
        temperature=temp,
        parse_errors=tuple(parse_errors),
        transcript_path=Path(transcript) if transcript else None,
        render_packet_path=Path(render_packet) if render_packet else None,
        observation_bundle_path=Path(observation_bundle) if observation_bundle else None,
        observation_mode=observation_mode,  # type: ignore[arg-type]
        observation_transcript_path=Path(observation_replay) if observation_replay else None,
        observation_cache_dir=Path(observation_cache_dir) if observation_cache_dir else None,
        allow_live_without_real_render=str(allow_projection or "").strip().lower()
        in {"1", "true", "yes", "on"},
        model=text_model or model,
        text_provider=(
            str(text_provider).strip().lower() if text_provider else None
        ),  # type: ignore[arg-type]
        vision_provider=(
            str(vision_provider).strip().lower() if vision_provider else None
        ),  # type: ignore[arg-type]
        vision_model=vision_model,
    )


def effective_text_provider(config: AgentConfig) -> str:
    if config.text_provider:
        return str(config.text_provider).strip().lower()
    return default_live_provider("text")


def effective_vision_provider(config: AgentConfig) -> str:
    if config.vision_provider:
        return str(config.vision_provider).strip().lower()
    return default_live_provider("vision")


def live_provider_summary(config: AgentConfig | None) -> list[str]:
    if config is None:
        return []
    providers: list[str] = []
    for provider in (
        effective_text_provider(config),
        effective_vision_provider(config),
    ):
        if provider and provider not in providers:
            providers.append(provider)
    return providers


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


def _infer_observation_mode(
    *,
    observation_mode_value: str | None,
    observation_replay: str | None,
    observation_bundle: str | None,
) -> str:
    explicit = str(observation_mode_value or "").strip().lower()
    if explicit:
        return explicit
    if observation_replay:
        return "replay"
    if observation_bundle:
        return "bundle"
    return "off"
