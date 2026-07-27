"""Shared MiniMax/Kimi responder construction and API trace accounting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .api_config import (
    LiveProviderConfig,
    LiveProviderConfigError,
    LiveProviderUsageLimitState,
    is_provider_usage_limit_error,
    live_provider_policy_summary,
    resolve_live_provider_config,
    resolve_live_provider_policy,
)
from .observation_live import (
    LiveObservationError,
    LiveResponder,
    build_openai_chat_client,
)
from .observation_vision import MinimaxTextResponder, MinimaxVisionResponder


def build_live_text_responder(
    *,
    provider: str,
    model_override: str | None,
    cache_dir: Path | None,
    record: list[dict[str, Any]],
    max_tokens: int,
    temperature: float,
    usage_limit_state: LiveProviderUsageLimitState | None = None,
) -> tuple[Any, str]:
    usage_limit_state = usage_limit_state or LiveProviderUsageLimitState()
    provider_policy = resolve_live_provider_policy(
        role="text",
        primary_override=provider,
    )
    provider_config = resolve_live_provider_config(
        role="text",
        provider=provider_policy.primary,
        model_override=model_override,
    )
    primary, model = _build_single_live_text_responder(
        provider_config=provider_config,
        cache_dir=cache_dir,
        record=record,
        max_tokens=max_tokens,
        temperature=temperature,
        usage_limit_state=usage_limit_state,
    )
    if not provider_policy.usage_limit_fallbacks:
        return primary, model
    for fallback_provider in provider_policy.usage_limit_fallbacks:
        try:
            fallback_config = resolve_live_provider_config(
                role="text",
                provider=fallback_provider,
            )
            fallback, _fallback_model = _build_single_live_text_responder(
                provider_config=fallback_config,
                cache_dir=cache_dir,
                record=record,
                max_tokens=max_tokens,
                temperature=temperature,
                usage_limit_state=usage_limit_state,
                record_metadata={
                    "fallback_from": provider_policy.primary,
                    "fallback_trigger": "usage_limit",
                },
            )
        except (LiveObservationError, LiveProviderConfigError):
            continue
        return UsageLimitFallbackTextResponder(primary, fallback), model
    return primary, model


def _build_single_live_text_responder(
    *,
    provider_config: LiveProviderConfig,
    cache_dir: Path | None,
    record: list[dict[str, Any]],
    max_tokens: int,
    temperature: float,
    record_metadata: dict[str, Any] | None = None,
    usage_limit_state: LiveProviderUsageLimitState,
) -> tuple[Any, str]:
    if provider_config.provider == "kimi":
        client, model = build_openai_chat_client(provider_config)
        return (
            LiveResponder(
                client=client,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                cache_dir=cache_dir,
                record=record,
                record_metadata=record_metadata,
                usage_limit_state=usage_limit_state,
            ),
            model,
        )
    return (
        MinimaxTextResponder(
            api_key=provider_config.api_key,
            base_url=provider_config.base_url,
            model=provider_config.model,
            max_tokens=max_tokens,
            temperature=temperature,
            cache_dir=cache_dir,
            record=record,
            usage_limit_state=usage_limit_state,
        ),
        provider_config.model,
    )


class UsageLimitFallbackTextResponder:
    """Use the fallback responder only when MiniMax reports exhausted quota."""

    def __init__(self, primary: Any, fallback: Any) -> None:
        self._primary = primary
        self._fallback = fallback

    def fetch_units(
        self,
        *,
        evidence: dict[str, Any],
        n_samples: int,
    ) -> list[dict[str, Any]]:
        payloads = self._primary.fetch_units(
            evidence=evidence,
            n_samples=n_samples,
        )
        if any(_is_usage_limit_payload(payload) for payload in payloads):
            return self._fallback.fetch_units(
                evidence=evidence,
                n_samples=n_samples,
            )
        return payloads

    def fetch_t3_decision(
        self,
        *,
        evidence: dict[str, Any],
        node: dict[str, Any],
        unit_id: str,
    ) -> dict[str, Any]:
        payload = self._primary.fetch_t3_decision(
            evidence=evidence,
            node=node,
            unit_id=unit_id,
        )
        if _is_usage_limit_payload(payload):
            return self._fallback.fetch_t3_decision(
                evidence=evidence,
                node=node,
                unit_id=unit_id,
            )
        return payload

    def fetch_layout(self, *, evidence: dict[str, Any]) -> dict[str, Any]:
        payload = self._primary.fetch_layout(evidence=evidence)
        if _is_usage_limit_payload(payload):
            return self._fallback.fetch_layout(evidence=evidence)
        return payload


def _is_usage_limit_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    return is_provider_usage_limit_error(payload.get("_observation_error"))


def build_live_vision_responder(
    *,
    provider: str,
    model_override: str | None,
    cache_dir: Path | None,
    record: list[dict[str, Any]],
    usage_limit_state: LiveProviderUsageLimitState | None = None,
) -> tuple[Any, str]:
    usage_limit_state = usage_limit_state or LiveProviderUsageLimitState()
    provider_policy = resolve_live_provider_policy(
        role="vision",
        primary_override=provider,
    )
    provider_config = resolve_live_provider_config(
        role="vision",
        provider=provider_policy.primary,
        model_override=model_override,
    )
    return (
        MinimaxVisionResponder(
            api_key=provider_config.api_key,
            base_url=provider_config.base_url,
            model=provider_config.model,
            cache_dir=cache_dir,
            record=record,
            usage_limit_state=usage_limit_state,
        ),
        provider_config.model,
    )


def api_trace_summary(
    *,
    mode: str,
    text_record: list[dict[str, Any]] | None = None,
    vision_record: list[dict[str, Any]] | None = None,
    providers: list[str] | None = None,
    models: dict[str, str] | None = None,
    provider_policy: dict[str, dict[str, object]] | None = None,
) -> dict[str, Any]:
    text_record = text_record or []
    vision_record = vision_record or []
    records = [*text_record, *vision_record]
    if providers is None:
        providers = (
            ["kimi", "minimax"]
            if mode == "live"
            else [mode]
            if mode != "off"
            else []
        )
    actual_providers = [
        str(item.get("provider")) for item in records if item.get("provider")
    ]
    providers = list(dict.fromkeys([*providers, *actual_providers]))
    cache_hit_count = sum(1 for item in records if item.get("from_cache"))
    skipped_usage_limit_count = sum(
        1 for item in records if item.get("skipped_due_usage_limit")
    )
    return {
        "mode": mode,
        "request_count": len(records),
        "api_call_count": len(records)
        - cache_hit_count
        - skipped_usage_limit_count,
        "cache_hit_count": cache_hit_count,
        "skipped_usage_limit_count": skipped_usage_limit_count,
        "failures": [
            {
                "stage": item.get("stage") or "t4",
                "page_no": item.get("page_no"),
                "provider": item.get("provider"),
                "error": str(item.get("error")),
            }
            for item in records
            if item.get("error")
        ],
        "providers": providers,
        "models": models or {},
        "provider_policy": provider_policy or live_provider_policy_summary(),
        "fallback_used": any(item.get("fallback_from") for item in text_record),
    }
