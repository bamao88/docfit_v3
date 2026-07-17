from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Literal, Mapping


LiveProviderRole = Literal["text", "vision"]
LiveProviderName = Literal["kimi", "minimax"]
LiveEndpointFamily = Literal["openai_chat", "anthropic_messages"]

TEXT_PROVIDERS: set[str] = {"kimi", "minimax"}
VISION_PROVIDERS: set[str] = {"minimax"}

KIMI_DEFAULT_BASE_URL = "https://api.kimi.com/coding/v1"
KIMI_DEFAULT_MODEL = "kimi-for-coding"
KIMI_DEFAULT_HEADERS = {
    "User-Agent": "claude-cli/2.0.0 (external, darwin)",
    "X-Client-Type": "claude-code",
}

MINIMAX_DEFAULT_BASE_URL = "https://api.minimaxi.com/anthropic"
MINIMAX_DEFAULT_MODEL = "MiniMax-M3"


class LiveProviderConfigError(ValueError):
    pass


@dataclass(frozen=True)
class LiveProviderConfig:
    role: LiveProviderRole
    provider: LiveProviderName
    api_key: str
    api_key_env: str
    base_url: str
    base_url_env: str
    model: str
    model_env: str
    endpoint_family: LiveEndpointFamily
    default_headers: Mapping[str, str]


def resolve_live_provider_config(
    *,
    role: LiveProviderRole,
    provider: str,
    model_override: str | None = None,
    env: Mapping[str, str] | None = None,
) -> LiveProviderConfig:
    values = env or os.environ
    normalized_role = role.strip().lower()
    normalized_provider = provider.strip().lower()
    if normalized_role not in {"text", "vision"}:
        raise LiveProviderConfigError(f"unsupported live provider role: {role}")
    supported = TEXT_PROVIDERS if normalized_role == "text" else VISION_PROVIDERS
    if normalized_provider not in supported:
        allowed = ", ".join(sorted(supported))
        raise LiveProviderConfigError(
            f"unsupported {normalized_role} live provider: {provider}; expected {allowed}"
        )

    if normalized_provider == "kimi":
        return _resolve_kimi(
            role=normalized_role,  # type: ignore[arg-type]
            model_override=model_override,
            env=values,
        )
    return _resolve_minimax(
        role=normalized_role,  # type: ignore[arg-type]
        model_override=model_override,
        env=values,
    )


def _resolve_kimi(
    *,
    role: LiveProviderRole,
    model_override: str | None,
    env: Mapping[str, str],
) -> LiveProviderConfig:
    if role != "text":
        raise LiveProviderConfigError("kimi is only supported for text live observation")
    api_key_env = "KIMI_API_KEY"
    api_key = env.get(api_key_env)
    if not api_key:
        raise LiveProviderConfigError(f"{api_key_env} is required for Kimi text observation")
    return LiveProviderConfig(
        role=role,
        provider="kimi",
        api_key=api_key,
        api_key_env=api_key_env,
        base_url=env.get("KIMI_BASE_URL") or KIMI_DEFAULT_BASE_URL,
        base_url_env="KIMI_BASE_URL",
        model=model_override or env.get("KIMI_MODEL") or KIMI_DEFAULT_MODEL,
        model_env="KIMI_MODEL",
        endpoint_family="openai_chat",
        default_headers=KIMI_DEFAULT_HEADERS,
    )


def _resolve_minimax(
    *,
    role: LiveProviderRole,
    model_override: str | None,
    env: Mapping[str, str],
) -> LiveProviderConfig:
    api_key_env = "MINIMAX_API_KEY"
    api_key = env.get(api_key_env)
    if not api_key:
        raise LiveProviderConfigError(
            f"{api_key_env} is required for MiniMax {role} observation"
        )
    return LiveProviderConfig(
        role=role,
        provider="minimax",
        api_key=api_key,
        api_key_env=api_key_env,
        base_url=_normalize_anthropic_base_url(
            env.get("MINIMAX_BASE_URL") or MINIMAX_DEFAULT_BASE_URL
        ),
        base_url_env="MINIMAX_BASE_URL",
        model=model_override or env.get("MINIMAX_MODEL") or MINIMAX_DEFAULT_MODEL,
        model_env="MINIMAX_MODEL",
        endpoint_family="anthropic_messages",
        default_headers={},
    )


def _normalize_anthropic_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    for suffix in ("/v1/messages", "/messages", "/v1"):
        if value.endswith(suffix):
            return value[: -len(suffix)].rstrip("/")
    return value
