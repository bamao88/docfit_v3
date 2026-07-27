"""Production observation runtime used by full template generation."""

from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso, read_json
from docfit.template_generation.final_results import (
    NOT_AVAILABLE,
    FinalStageResult,
)
from docfit.template_generation.t2_ai import publish_t2_ai_final

from .api_config import (
    LiveProviderConfigError,
    LiveProviderUsageLimitState,
    live_provider_policy_summary,
)
from .config import (
    AgentConfig,
    AgentConfigError,
    effective_text_provider,
    effective_vision_provider,
    live_provider_summary,
)
from .observation_config import ObservationConfig
from .observation_live import LiveObservationError
from .observation_loop import run_observation_pipeline
from .observation_providers import (
    api_trace_summary,
    build_live_text_responder,
    build_live_vision_responder,
)
from .observation_vision import MinimaxVisionError
from .t3_hierarchical_input import build_t3_hierarchical_stage_input


def run_module1_observation_for_template_generate(
    *,
    packet: dict[str, Any],
    agent_config: AgentConfig,
) -> dict[str, Any] | None:
    """Produce or load the observation bundle for full template generation."""

    mode = _effective_observation_mode(agent_config)
    if mode == "off":
        return None
    if mode == "bundle":
        assert agent_config.observation_bundle_path is not None
        bundle = read_json(agent_config.observation_bundle_path)
        if not isinstance(bundle, dict):
            raise AgentConfigError(
                "observation bundle must contain one JSON object"
            )
        bundle = dict(bundle)
        bundle.setdefault(
            "api_trace_summary",
            api_trace_summary(mode="bundle"),
        )
        t2_observation = bundle.get("ai_unit_observation")
        if not isinstance(t2_observation, dict):
            raise AgentConfigError(
                "observation bundle cannot publish T2 final without "
                "ai_unit_observation"
            )
        t2_final = publish_t2_ai_final(t2_observation, packet=packet)
        bundle["t2_final_result"] = t2_final.payload
        _require_bundle_t3_final_binding(
            bundle,
            t2_final,
            packet=packet,
        )
        return bundle
    if mode == "replay":
        assert agent_config.observation_transcript_path is not None
        transcript = read_json(agent_config.observation_transcript_path)
        bundle = run_observation_pipeline(
            packet=packet,
            transcript=transcript,
            config=ObservationConfig(
                model=agent_config.model or "replay",
            ),
            t3_concurrency=agent_config.observation_t3_concurrency,
        )
        bundle["api_trace_summary"] = api_trace_summary(mode="replay")
        return bundle
    if mode == "live":
        try:
            text_record: list[dict[str, Any]] = []
            vision_record: list[dict[str, Any]] = []
            usage_limit_state = LiveProviderUsageLimitState()
            responder, text_model = build_live_text_responder(
                provider=effective_text_provider(agent_config),
                model_override=agent_config.model,
                cache_dir=agent_config.observation_cache_dir,
                record=text_record,
                max_tokens=agent_config.max_tokens,
                temperature=agent_config.temperature,
                usage_limit_state=usage_limit_state,
            )
            vision_responder, vision_model = build_live_vision_responder(
                provider=effective_vision_provider(agent_config),
                model_override=agent_config.vision_model,
                cache_dir=agent_config.observation_cache_dir,
                record=vision_record,
                usage_limit_state=usage_limit_state,
            )
            bundle = run_observation_pipeline(
                packet=packet,
                responder=responder,
                vision_responder=vision_responder,
                config=ObservationConfig(model=text_model),
                t3_concurrency=agent_config.observation_t3_concurrency,
            )
            bundle["api_trace_summary"] = api_trace_summary(
                mode="live",
                text_record=text_record,
                vision_record=vision_record,
                providers=live_provider_summary(agent_config),
                models={"text": text_model, "vision": vision_model},
                provider_policy=live_provider_policy_summary(
                    text_primary_override=effective_text_provider(agent_config),
                    vision_primary_override=effective_vision_provider(agent_config),
                ),
            )
            return bundle
        except (
            LiveObservationError,
            MinimaxVisionError,
            LiveProviderConfigError,
        ) as exc:
            raise AgentConfigError(str(exc)) from exc
    raise ValueError(f"unsupported observation mode: {mode}")


def _effective_observation_mode(agent_config: AgentConfig) -> str:
    if agent_config.observation_bundle_path is not None:
        return "bundle"
    return str(agent_config.observation_mode or "off")


def _require_bundle_t3_final_binding(
    bundle: dict[str, Any],
    t2_final: FinalStageResult,
    *,
    packet: dict[str, Any],
) -> None:
    """Reject bundle T3 decisions that were not bound to this T2 final."""

    stage_input = bundle.get("t3_hierarchical_stage_input")
    contract = (
        stage_input.get("contract")
        if isinstance(stage_input, dict)
        and isinstance(stage_input.get("contract"), dict)
        else {}
    )
    if contract.get("t2_final_hash") == t2_final.sha256:
        return

    reason = (
        "bundle T3 evidence is not bound to this run's T2 final; "
        "candidate-derived T3 decisions are not executable"
    )
    canonical_input = build_t3_hierarchical_stage_input(
        packet,
        t2_final=t2_final,
    )
    bundle["t3_hierarchical_stage_input"] = canonical_input
    bundle["ai_element_observation"] = {
        "artifact_type": "ai_element_observation",
        "stage": "t3",
        "source_render_hash": packet.get("source_render_hash"),
        "model": bundle.get("model"),
        "created_at": now_iso(),
        "stage_input_ref": {
            "artifact_version": canonical_input.get("artifact_version"),
            "tree_hash": canonical_input.get("tree_hash"),
            "contract": canonical_input.get("contract"),
        },
        "coverage": {
            "total": len(packet.get("page_text_index", []) or []),
            "owned_source_seq": [],
            "unknown_source_seq": [
                item.get("source_seq")
                for item in packet.get("page_text_index", []) or []
                if isinstance(item, dict) and item.get("source_seq") is not None
            ],
        },
        "items": [],
        "object_items": [],
        "unknown_items": [],
        "open_questions": [
            {
                "question_id": "q_t3_bundle_final_binding",
                "blocking_level": "blocking",
                "reason": reason,
            }
        ],
        "abstain": True,
        "quality_report": {
            "availability": NOT_AVAILABLE,
            "reason": reason,
            "t2_final_hash": t2_final.sha256,
            "decision_call_count": 0,
        },
    }
