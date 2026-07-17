from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import (
    ensure_dir,
    now_iso,
    read_json,
    read_yaml,
    sha256_file,
    write_json,
    write_yaml,
)
from docfit.template_generation.source_tree import inspect_document_facts_docx
from docfit.template_generation.input_contract import build_l1_input_contract
from docfit.template_generation.stage_inputs import build_agent_stage_packet

from .api_config import (
    LiveProviderConfigError,
    resolve_live_provider_config,
)
from .config import (
    AgentConfig,
    AgentConfigError,
    agent_config_from_env,
    effective_text_provider,
    effective_vision_provider,
    live_provider_summary,
)
from .observation_config import ObservationConfig
from .observation_live import (
    LiveObservationError,
    LiveResponder,
    build_openai_chat_client,
)
from .observation_loop import (
    ReplayResponder,
    run_observation_pipeline,
    run_t2_observation,
    run_t3_observation,
    run_t4_observation,
)
from .observation_vision import (
    MinimaxTextResponder,
    MinimaxVisionError,
    MinimaxVisionResponder,
)
from .packet import build_template_agent_render_packet


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
        bundle = read_json(agent_config.observation_bundle_path)
        if isinstance(bundle, dict):
            bundle = dict(bundle)
            bundle.setdefault(
                "api_trace_summary",
                _api_trace_summary(mode="bundle"),
            )
        return bundle
    if mode == "replay":
        assert agent_config.observation_transcript_path is not None
        transcript = read_json(agent_config.observation_transcript_path)
        bundle = run_observation_pipeline(
            packet=packet,
            transcript=transcript,
            config=ObservationConfig(
                enabled=True,
                self_consistency_samples=1,
                model=agent_config.model or "replay",
            ),
            t3_concurrency=agent_config.observation_t3_concurrency,
        )
        bundle["api_trace_summary"] = _api_trace_summary(mode="replay")
        return bundle
    if mode == "live":
        try:
            text_record: list[dict[str, Any]] = []
            vision_record: list[dict[str, Any]] = []
            responder, text_model = _build_live_text_responder(
                provider=effective_text_provider(agent_config),
                model_override=agent_config.model,
                cache_dir=agent_config.observation_cache_dir,
                record=text_record,
                max_tokens=agent_config.max_tokens,
                temperature=agent_config.temperature,
            )
            vision_responder, vision_model = _build_live_vision_responder(
                provider=effective_vision_provider(agent_config),
                model_override=agent_config.vision_model,
                cache_dir=agent_config.observation_cache_dir,
                record=vision_record,
            )
            bundle = run_observation_pipeline(
                packet=packet,
                responder=responder,
                vision_responder=vision_responder,
                config=ObservationConfig(enabled=True, model=text_model),
                t3_concurrency=agent_config.observation_t3_concurrency,
            )
            bundle["api_trace_summary"] = _api_trace_summary(
                mode="live",
                text_record=text_record,
                vision_record=vision_record,
                providers=live_provider_summary(agent_config),
                models={"text": text_model, "vision": vision_model},
            )
            return bundle
        except (LiveObservationError, MinimaxVisionError, LiveProviderConfigError) as exc:
            raise AgentConfigError(str(exc)) from exc
    raise ValueError(f"unsupported observation mode: {mode}")


def run_live_template_observation_stage(
    *,
    source_template_docx: Path,
    out_dir: Path,
    stage: str,
    t2_observation_path: Path | None = None,
    max_tokens: int = 8000,
    temperature: float = 0.4,
    t3_concurrency: int = 4,
) -> dict[str, Any]:
    """Compatibility wrapper for the old always-live, template-backed command."""

    return run_template_observation_stage(
        source_template_docx=source_template_docx,
        out_dir=out_dir,
        stage=stage,
        ai_mode="live",
        t2_artifact_path=t2_observation_path,
        with_upstream=stage.strip().lower() == "t3" and t2_observation_path is None,
        max_tokens=max_tokens,
        temperature=temperature,
        t3_concurrency=t3_concurrency,
        entrypoint="compat.eval.template-observe",
    )


def run_template_observation_stage(
    *,
    out_dir: Path,
    stage: str,
    ai_mode: str = "live",
    source_run_dir: Path | None = None,
    source_template_docx: Path | None = None,
    replay_path: Path | None = None,
    bundle_path: Path | None = None,
    t2_route: str = "ai_raw",
    t2_artifact_path: Path | None = None,
    with_upstream: bool = False,
    max_tokens: int = 8000,
    temperature: float = 0.4,
    t3_concurrency: int = 4,
    entrypoint: str = "python.run_template_observation_stage",
) -> dict[str, Any]:
    """Run one reproducible T2/T3/T4 observation stage.

    Existing template-generate runs are preferred and never modified. Template
    input is an explicit bootstrap route. T3 requires a pinned upstream unless
    ``with_upstream`` explicitly authorizes a new T2 pass.
    """

    normalized_stage = stage.strip().lower()
    normalized_mode = ai_mode.strip().lower()
    if normalized_stage not in {"t2", "t3", "t4"}:
        raise AgentConfigError("template observation stage must be one of: t2, t3, t4")
    if normalized_mode not in {"live", "replay", "bundle"}:
        raise AgentConfigError("template stage --ai must be live, replay, or bundle")
    if (source_run_dir is None) == (source_template_docx is None):
        raise AgentConfigError("pass exactly one of source_run_dir or source_template_docx")
    if normalized_mode == "replay" and replay_path is None:
        raise AgentConfigError("--ai replay requires --replay")
    if normalized_mode == "bundle" and bundle_path is None:
        raise AgentConfigError("--ai bundle requires --bundle")
    if t2_artifact_path is not None and normalized_stage != "t3":
        raise AgentConfigError("--t2-artifact is only valid for T3")

    ensure_dir(out_dir)
    cache_dir = ensure_dir(out_dir / "cache")
    packet, source_template_docx, resolved_run_dir, packet_source = _stage_packet(
        source_run_dir=source_run_dir,
        source_template_docx=source_template_docx,
        out_dir=out_dir,
    )
    packet_path = out_dir / "l1_agent_stage_packet.json"
    write_json(packet_path, packet)
    source_template_hash = _stage_source_template_hash(
        source_template_docx=source_template_docx,
        run_dir=resolved_run_dir,
    )
    artifacts: dict[str, Path] = {"l1_agent_stage_packet": packet_path}
    if packet_source is not None and packet_source.name == "01.5_l1_input_contract.json":
        artifacts["l1_input_contract"] = packet_source
    upstream_artifacts: dict[str, Any] = {
        "l1_input_contract": _artifact_ref(packet_source or packet_path),
    }
    api_record: list[dict[str, Any]] = []
    ran_upstream_t2 = False
    providers: list[str] = []
    models: dict[str, str] = {}
    env_agent_config = agent_config_from_env() or AgentConfig(enabled=True)
    stage_text_provider = effective_text_provider(env_agent_config)
    stage_vision_provider = effective_vision_provider(env_agent_config)
    stage_text_model = env_agent_config.model
    stage_vision_model = env_agent_config.vision_model

    if normalized_mode == "bundle":
        assert bundle_path is not None
        bundle = _read_mapping(bundle_path)
        observation_key = {
            "t2": "ai_unit_observation",
            "t3": "ai_element_observation",
            "t4": "ai_layout_observation",
        }[normalized_stage]
        observation = bundle.get(observation_key)
        if not isinstance(observation, dict):
            raise AgentConfigError(
                f"observation bundle has no {observation_key}: {bundle_path}"
            )
        _require_render_hash(observation, packet, label=observation_key)
        artifact_path = _write_stage_observation(
            out_dir,
            normalized_stage,
            observation,
        )
        artifacts[observation_key] = artifact_path
        upstream_artifacts["observation_bundle"] = _artifact_ref(bundle_path)
        providers = ["bundle"]
    else:
        if normalized_stage == "t4" and normalized_mode == "live":
            responder = ReplayResponder({})
            config = ObservationConfig(enabled=True, model="minimax")
        else:
            responder, config, providers, models = _stage_text_runtime(
                mode=normalized_mode,
                replay_path=replay_path,
                cache_dir=cache_dir,
                api_record=api_record,
                max_tokens=max_tokens,
                temperature=temperature,
                text_provider=stage_text_provider,
                model_override=stage_text_model,
            )
        try:
            if normalized_stage == "t2":
                observation, _consistency, _evidence = run_t2_observation(
                    packet=packet,
                    responder=responder,
                    config=config,
                )
                artifacts["ai_unit_observation"] = _write_stage_observation(
                    out_dir,
                    "t2",
                    observation,
                )
            elif normalized_stage == "t3":
                t2_observation, t2_source = _resolve_t2_upstream(
                    packet=packet,
                    run_dir=resolved_run_dir,
                    route=t2_route,
                    explicit_path=t2_artifact_path,
                )
                if t2_observation is None:
                    if not with_upstream:
                        raise AgentConfigError(
                            "T3 requires a pinned T2 artifact; pass --t2-artifact, "
                            "use a run containing the selected --t2-route, or add --with-upstream"
                        )
                    t2_observation, _consistency, _evidence = run_t2_observation(
                        packet=packet,
                        responder=responder,
                        config=config,
                    )
                    t2_source = out_dir / "02.2_t2_ai_unit_observation.yaml"
                    write_yaml(t2_source, t2_observation)
                    artifacts["ai_unit_observation"] = t2_source
                    ran_upstream_t2 = True
                assert t2_source is not None
                upstream_artifacts["t2"] = _artifact_ref(t2_source)
                observation, windows = run_t3_observation(
                    packet=packet,
                    ai_unit_observation=t2_observation,
                    responder=responder,
                    config=config,
                    concurrency=t3_concurrency,
                )
                windows_path = out_dir / "03.0_t3_unit_windows.json"
                write_json(windows_path, windows)
                artifacts["t3_unit_windows"] = windows_path
                artifacts["ai_element_observation"] = _write_stage_observation(
                    out_dir,
                    "t3",
                    observation,
                )
            else:
                raw_payload = None
                vision_responder = None
                if normalized_mode == "live":
                    if packet.get("render_status") != "real_render":
                        raise AgentConfigError(
                            "standalone T4 requires real rendered page images before its vision API call; "
                            f"got render_status={packet.get('render_status') or 'missing'}"
                        )
                    vision_responder, vision_model = _build_live_vision_responder(
                        provider=stage_vision_provider,
                        model_override=stage_vision_model,
                        cache_dir=cache_dir,
                        record=api_record,
                    )
                    config = ObservationConfig(enabled=True, model=vision_model)
                    providers = [stage_vision_provider]
                    models = {"vision": vision_model}
                else:
                    raw_payload = responder.fetch_layout(
                        evidence={"source_render_hash": packet.get("source_render_hash")}
                    )
                observation, _evidence = run_t4_observation(
                    packet=packet,
                    config=config,
                    vision_responder=vision_responder,
                    raw_payload=raw_payload,
                )
                artifacts["ai_layout_observation"] = _write_stage_observation(
                    out_dir,
                    "t4",
                    observation,
                )
        except (LiveObservationError, MinimaxVisionError, LiveProviderConfigError) as exc:
            raise AgentConfigError(str(exc)) from exc

    if normalized_mode == "live":
        _require_successful_live_stage_call(
            stage=normalized_stage,
            api_record=api_record,
        )
    trace = _api_trace_summary(
        mode=normalized_mode,
        text_record=api_record if normalized_stage in {"t2", "t3"} else [],
        vision_record=api_record if normalized_stage == "t4" else [],
        providers=providers,
        models=models,
    )
    summary = {
        "artifact_type": "template_observation_stage_run",
        "artifact_version": "1.1",
        "created_at": now_iso(),
        "entrypoint": entrypoint,
        "stage": normalized_stage.upper(),
        "ai_mode": normalized_mode,
        "llm_mode": "live_api" if normalized_mode == "live" else normalized_mode,
        "providers": providers,
        "models": models,
        "ran_upstream_t2": ran_upstream_t2,
        "auto_ran_t2": ran_upstream_t2,
        "source_kind": "run" if resolved_run_dir is not None else "template",
        "source_run_dir": str(resolved_run_dir) if resolved_run_dir is not None else None,
        "source_template_docx": (
            str(source_template_docx) if source_template_docx is not None else None
        ),
        "source_template_hash": source_template_hash,
        "source_render_hash": packet.get("source_render_hash"),
        "upstream_artifacts": upstream_artifacts,
        "api_call_count": trace["api_call_count"],
        "api_cache_hit_count": trace["cache_hit_count"],
        "api_failures": trace["failures"],
        "artifacts": {name: str(path) for name, path in artifacts.items()},
    }
    write_json(out_dir / "summary.json", summary)
    run_manifest = {
        **summary,
        "artifact_type": "template_generation_run_manifest",
        "artifact_version": "1.0",
        "command": f"template stage {normalized_stage}",
        "output_artifacts": {
            name: _artifact_ref(path) for name, path in artifacts.items()
        },
    }
    write_json(out_dir / "run_manifest.json", run_manifest)
    return summary


def _effective_observation_mode(agent_config: AgentConfig) -> str:
    if agent_config.observation_bundle_path is not None:
        return "bundle"
    return str(agent_config.observation_mode or "off")


def _stage_packet(
    *,
    source_run_dir: Path | None,
    source_template_docx: Path | None,
    out_dir: Path,
) -> tuple[dict[str, Any], Path | None, Path | None, Path | None]:
    if source_run_dir is not None:
        run_dir = source_run_dir.resolve()
        nested = run_dir / "eval_runs" / "template_generate"
        if nested.is_dir():
            run_dir = nested
        l1_path = run_dir / "01.5_l1_input_contract.json"
        if not l1_path.exists():
            raise AgentConfigError(
                f"stage --run has no sealed 01.5_l1_input_contract.json: {run_dir}"
            )
        l1_input_contract = _read_mapping(l1_path)
        if l1_input_contract.get("source_structure_index") is None:
            raise AgentConfigError(
                f"stage --run has a legacy L1 contract that cannot drive stages: {l1_path}"
            )
        packet = build_agent_stage_packet(l1_input_contract)
        packet_source = l1_path
        if not packet:
            raise AgentConfigError(
                f"stage --run has no usable L1 stage input: {run_dir}"
            )
        request_path = run_dir / "00_template_generation_request.json"
        template_path = None
        if request_path.exists():
            request = _read_mapping(request_path)
            raw_template = request.get("source_template_docx")
            if raw_template:
                candidate = Path(str(raw_template))
                template_path = candidate if candidate.exists() else None
        return packet, template_path, run_dir, packet_source

    assert source_template_docx is not None
    document_facts = inspect_document_facts_docx(source_template_docx)
    render_facts = build_template_agent_render_packet(
        document_facts=document_facts,
        structure_candidates={},
        source_template_docx=source_template_docx,
        render_artifacts_dir=out_dir / "render_artifacts",
    )
    l1_input_contract = build_l1_input_contract(
        document_facts=document_facts,
        render_packet=render_facts,
    )
    l1_path = out_dir / "01.5_l1_input_contract.json"
    write_json(l1_path, l1_input_contract)
    packet = build_agent_stage_packet(l1_input_contract)
    return packet, source_template_docx, None, l1_path


def _build_live_text_responder(
    *,
    provider: str,
    model_override: str | None,
    cache_dir: Path | None,
    record: list[dict[str, Any]],
    max_tokens: int,
    temperature: float,
) -> tuple[Any, str]:
    provider_config = resolve_live_provider_config(
        role="text",
        provider=provider,
        model_override=model_override,
    )
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
        ),
        provider_config.model,
    )


def _build_live_vision_responder(
    *,
    provider: str,
    model_override: str | None,
    cache_dir: Path | None,
    record: list[dict[str, Any]],
) -> tuple[Any, str]:
    provider_config = resolve_live_provider_config(
        role="vision",
        provider=provider,
        model_override=model_override,
    )
    return (
        MinimaxVisionResponder(
            api_key=provider_config.api_key,
            base_url=provider_config.base_url,
            model=provider_config.model,
            cache_dir=cache_dir,
            record=record,
        ),
        provider_config.model,
    )


def _stage_text_runtime(
    *,
    mode: str,
    replay_path: Path | None,
    cache_dir: Path,
    api_record: list[dict[str, Any]],
    max_tokens: int,
    temperature: float,
    text_provider: str,
    model_override: str | None,
) -> tuple[Any, ObservationConfig, list[str], dict[str, str]]:
    if mode == "live":
        try:
            responder, model = _build_live_text_responder(
                provider=text_provider,
                model_override=model_override,
                cache_dir=cache_dir,
                record=api_record,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except (LiveObservationError, LiveProviderConfigError) as exc:
            raise AgentConfigError(str(exc)) from exc
        return (
            responder,
            ObservationConfig(enabled=True, model=model),
            [text_provider],
            {"text": model},
        )
    assert replay_path is not None
    transcript = _read_mapping(replay_path)
    return (
        ReplayResponder(transcript),
        ObservationConfig(enabled=True, model="replay"),
        ["replay"],
        {"text": "replay"},
    )


def _resolve_t2_upstream(
    *,
    packet: dict[str, Any],
    run_dir: Path | None,
    route: str,
    explicit_path: Path | None,
) -> tuple[dict[str, Any] | None, Path | None]:
    path = explicit_path
    normalized_route = route.strip().lower()
    if path is None and run_dir is not None:
        names = {
            "ai_raw": "02.2_t2_ai_unit_observation.yaml",
            "code_raw": "02.0_t2_code_unit_map.yaml",
            "merged": "02.3_t2_merged_unit_map.yaml",
        }
        if normalized_route not in names:
            raise AgentConfigError("--t2-route must be ai_raw, code_raw, or merged")
        candidate = run_dir / names[normalized_route]
        if candidate.exists():
            path = candidate
    if path is None:
        return None, None
    payload = _read_mapping(path)
    artifact_type = str(payload.get("artifact_type") or "")
    if artifact_type == "ai_unit_observation":
        route_state = payload.get("route") or {}
        if isinstance(route_state, dict) and route_state.get("availability") == "NOT_AVAILABLE":
            return None, None
        _require_render_hash(payload, packet, label="T2 observation")
        return payload, path
    units = payload.get("units")
    if not isinstance(units, list):
        raise AgentConfigError(f"T3 upstream is neither AI unit observation nor unit_map: {path}")
    return (
        {
            "artifact_type": "route_unit_observation",
            "artifact_version": "1.0",
            "route_id": normalized_route,
            "source_render_hash": packet.get("source_render_hash"),
            "items": [
                {
                    "unit_id": item.get("unit_id"),
                    "source_seq_refs": list(item.get("source_seq_refs") or []),
                    "page_start": item.get("page_start"),
                    "confidence": item.get("confidence") or "low",
                }
                for item in units
                if isinstance(item, dict)
            ],
        },
        path,
    )


def _write_stage_observation(
    out_dir: Path,
    stage: str,
    observation: dict[str, Any],
) -> Path:
    name = {
        "t2": "02.2_t2_ai_unit_observation.yaml",
        "t3": "03.1_t3_ai_element_observation.yaml",
        "t4": "04.1_t4_ai_layout_observation.yaml",
    }[stage]
    path = out_dir / name
    write_yaml(path, observation)
    return path


def _read_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AgentConfigError(f"artifact does not exist: {path}")
    try:
        payload = (
            read_yaml(path)
            if path.suffix.lower() in {".yaml", ".yml"}
            else read_json(path)
        )
    except Exception as exc:
        raise AgentConfigError(f"artifact cannot be parsed: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AgentConfigError(f"artifact must contain an object: {path}")
    return payload


def _require_render_hash(
    artifact: dict[str, Any],
    packet: dict[str, Any],
    *,
    label: str,
) -> None:
    expected = packet.get("source_render_hash")
    observed = artifact.get("source_render_hash")
    if not observed or observed != expected:
        raise AgentConfigError(
            f"{label} source_render_hash does not match the selected run/template"
        )


def _artifact_ref(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"path": None, "sha256": None}
    return {
        "path": str(path),
        "sha256": sha256_file(path) if path.exists() else None,
    }


def _stage_source_template_hash(
    *,
    source_template_docx: Path | None,
    run_dir: Path | None,
) -> str | None:
    if source_template_docx is not None and source_template_docx.exists():
        return sha256_file(source_template_docx)
    if run_dir is None:
        return None
    facts_path = run_dir / "01_document_facts.json"
    if not facts_path.exists():
        return None
    facts = _read_mapping(facts_path)
    metadata = facts.get("metadata") or {}
    return (
        str(metadata.get("source_template_hash"))
        if isinstance(metadata, dict) and metadata.get("source_template_hash")
        else None
    )


def _read_observation(path: Path) -> dict[str, Any]:
    payload = read_yaml(path) if path.suffix.lower() in {".yaml", ".yml"} else read_json(path)
    if not isinstance(payload, dict) or payload.get("artifact_type") != "ai_unit_observation":
        raise AgentConfigError(
            f"T3 --t2-observation must contain an ai_unit_observation artifact: {path}"
        )
    return payload


def _require_successful_live_stage_call(
    *,
    stage: str,
    api_record: list[dict[str, Any]],
) -> None:
    if stage in {"t2", "t3"}:
        target_records = [item for item in api_record if item.get("stage") == stage]
    else:
        target_records = list(api_record)
    if not target_records:
        raise AgentConfigError(
            f"standalone {stage.upper()} produced no live API call; check its input evidence"
        )
    if all(item.get("error") for item in target_records):
        errors = "; ".join(str(item.get("error")) for item in target_records)
        raise AgentConfigError(
            f"all standalone {stage.upper()} live API calls failed: {errors}"
        )


def _api_trace_summary(
    *,
    mode: str,
    text_record: list[dict[str, Any]] | None = None,
    vision_record: list[dict[str, Any]] | None = None,
    providers: list[str] | None = None,
    models: dict[str, str] | None = None,
) -> dict[str, Any]:
    text_record = text_record or []
    vision_record = vision_record or []
    records = [*text_record, *vision_record]
    if providers is None:
        providers = ["kimi", "minimax"] if mode == "live" else [mode] if mode != "off" else []
    return {
        "mode": mode,
        "api_call_count": len(records),
        "cache_hit_count": sum(1 for item in records if item.get("from_cache")),
        "failures": [
            {
                "stage": item.get("stage") or "t4",
                "page_no": item.get("page_no"),
                "error": str(item.get("error")),
            }
            for item in records
            if item.get("error")
        ],
        "providers": providers,
        "models": models or {},
    }
