from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file, write_json
from docfit.core.models import StageResult

from .agent.config import AgentConfig, live_provider_summary
from .stage_inputs import l1_artifact_hash


def ai_mode_from_agent_config(config: AgentConfig | None) -> str:
    if config is None or not config.enabled:
        return "off"
    if config.observation_bundle_path is not None or config.observation_mode == "bundle":
        return "bundle"
    if config.observation_mode == "live":
        return "live"
    if config.observation_mode == "replay":
        return "replay"
    if config.transcript_path is not None:
        return "legacy_replay"
    return str(config.observation_mode or config.transport)


def write_template_run_manifest(
    out_dir: Path,
    *,
    result: StageResult,
    entrypoint: str,
    command: str,
    stage: str,
    agent_config: AgentConfig | None = None,
    source_template_docx: Path | None = None,
    upstream_artifacts: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    observation_bundle = result.artifacts.get("ai_observation_bundle")
    api_trace = (
        dict(observation_bundle.get("api_trace_summary") or {})
        if isinstance(observation_bundle, dict)
        else {}
    )
    l1_contract = result.artifacts.get("template_generation_l1_input_contract")
    document_facts = result.artifacts.get("document_facts")
    source_hash = None
    if source_template_docx is not None and source_template_docx.exists():
        source_hash = sha256_file(source_template_docx)
    elif isinstance(document_facts, dict):
        source_hash = (document_facts.get("metadata") or {}).get("source_template_hash")

    manifest = {
        "artifact_type": "template_generation_run_manifest",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "command": command,
        "entrypoint": entrypoint,
        "stage": stage,
        "ai_mode": ai_mode_from_agent_config(agent_config),
        "provider": _provider_summary(agent_config),
        "model": agent_config.model if agent_config is not None else None,
        "source_template_docx": (
            str(source_template_docx) if source_template_docx is not None else None
        ),
        "source_template_hash": source_hash,
        "source_render_hash": (
            (l1_contract.get("visual_page_index") or {}).get("source_render_hash")
            if isinstance(l1_contract, dict)
            else None
        ),
        "l1_contract_hash": (
            l1_artifact_hash(l1_contract) if isinstance(l1_contract, dict) else None
        ),
        "upstream_artifacts": upstream_artifacts or {},
        "api_call_count": api_trace.get("api_call_count", 0),
        "api_cache_hit_count": api_trace.get("cache_hit_count", 0),
        "api_failures": list(api_trace.get("failures") or []),
        "api_trace": api_trace,
        "status": result.status.value,
        "output_artifacts": {
            key: str(path) for key, path in sorted(result.artifact_paths.items())
        },
        **(extra or {}),
    }
    path = out_dir / "run_manifest.json"
    write_json(path, manifest)
    result.artifact_paths["run_manifest"] = path
    return path


def _provider_summary(config: AgentConfig | None) -> list[str]:
    mode = ai_mode_from_agent_config(config)
    if mode == "live":
        return live_provider_summary(config)
    if mode in {"replay", "bundle"}:
        return [mode]
    return []
