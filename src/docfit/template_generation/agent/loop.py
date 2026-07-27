from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docfit.template_generation.final_results import (
    FinalStageResult,
    require_final_stage_result,
)
from docfit.template_generation.artifacts import build_element_spec
from docfit.template_generation.generation_model import (
    build_template_generation_model,
)
from docfit.template_generation.input_contract import build_l1_input_contract
from docfit.template_generation.stage_inputs import build_agent_stage_packet

from .attribution import build_t3_materialization_trace
from .t3_ai_materialize import (
    build_t3_source_structure,
    materialize_ai_t3_structure,
)
from .config import (
    AgentConfig,
    AgentConfigError,
    require_valid_agent_config,
)
from .observation_runtime import run_module1_observation_for_template_generate
from .packet import build_template_agent_render_packet, load_render_packet


@dataclass
class AgentRunResult:
    enabled: bool
    changed: bool
    downstream_structure: dict[str, Any]
    unit_map: dict[str, Any]
    generation_model: dict[str, Any]
    element_spec: dict[str, Any]
    ai_unit_observation: dict[str, Any] | None = None
    ai_element_observation: dict[str, Any] | None = None
    ai_layout_observation: dict[str, Any] | None = None
    ai_observation_bundle: dict[str, Any] | None = None
    render_packet: dict[str, Any] | None = None
    t3_materialization_trace: dict[str, Any] | None = None
    t2_final_result: FinalStageResult | None = None


def run_template_agent(
    *,
    source_template_docx: Path,
    request: dict[str, Any],
    document_facts: dict[str, Any],
    source_tree: dict[str, Any],
    agent_config: AgentConfig,
    render_packet: dict[str, Any] | None = None,
    render_artifacts_dir: Path | None = None,
) -> AgentRunResult:
    if not agent_config.enabled:
        raise AgentConfigError(
            "T2 is AI-only; configure observation_mode=live, replay, or bundle"
        )

    require_valid_agent_config(agent_config)
    if render_packet is not None:
        packet = render_packet
    else:
        render_facts = (
            load_render_packet(agent_config.render_packet_path)
            if agent_config.render_packet_path is not None
            else build_template_agent_render_packet(
                document_facts=document_facts,
                source_template_docx=source_template_docx,
                render_artifacts_dir=render_artifacts_dir,
            )
        )
        packet = build_agent_stage_packet(
            build_l1_input_contract(
                document_facts=document_facts,
                render_packet=render_facts,
            )
        )
    if (
        agent_config.observation_mode == "live"
        and packet.get("render_status") != "real_render"
    ):
        raise AgentConfigError(
            "live agent transport requires a real_render packet; "
            f"got render_status={packet.get('render_status') or 'missing'}"
        )
    observation_bundle = run_module1_observation_for_template_generate(
        packet=packet,
        agent_config=agent_config,
    )
    if observation_bundle is None:
        raise AgentConfigError(
            "T2 AI-only pipeline produced no observation bundle"
        )
    ai_unit_observation = observation_bundle.get("ai_unit_observation")
    ai_element_observation = observation_bundle.get("ai_element_observation")
    ai_layout_observation = observation_bundle.get("ai_layout_observation")
    t2_final_payload = observation_bundle.get("t2_final_result")
    t2_final_result = require_final_stage_result(
        t2_final_payload if isinstance(t2_final_payload, dict) else {},
        stage_id="T2",
        artifact_type="unit_map",
        artifact_name="02_unit_map.yaml",
        expected_l1_hash=packet.get("input_contract_hash") or None,
    )
    downstream_structure = build_t3_source_structure(
        source_tree,
        t2_final_result.payload,
    )
    downstream_structure, ai_operation = materialize_ai_t3_structure(
        downstream_structure,
        ai_element_observation if isinstance(ai_element_observation, dict) else {},
    )

    changed = bool(
        isinstance(ai_element_observation, dict)
        and bool(ai_element_observation.get("items"))
    )
    generation_model = build_template_generation_model(
        request,
        t3_source_structure=downstream_structure,
        include_source_instruction_heuristics=False,
    )
    element_spec = build_element_spec(generation_model)
    t3_materialization_trace = build_t3_materialization_trace(ai_operation)
    return AgentRunResult(
        enabled=True,
        changed=changed,
        downstream_structure=downstream_structure,
        unit_map=t2_final_result.payload,
        generation_model=generation_model,
        element_spec=element_spec,
        ai_unit_observation=(
            ai_unit_observation if isinstance(ai_unit_observation, dict) else None
        ),
        ai_element_observation=(
            ai_element_observation if isinstance(ai_element_observation, dict) else None
        ),
        ai_layout_observation=(
            ai_layout_observation if isinstance(ai_layout_observation, dict) else None
        ),
        ai_observation_bundle=(
            observation_bundle if isinstance(observation_bundle, dict) else None
        ),
        render_packet=packet,
        t3_materialization_trace=t3_materialization_trace,
        t2_final_result=t2_final_result,
    )
