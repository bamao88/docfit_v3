from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_json
from docfit.core.models import StageResult, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.ooxml.package import is_valid_docx

from .agent import AgentConfig, AgentConfigError, run_template_agent
from .agent.packet import build_template_agent_render_packet, load_render_packet
from .agent.t3_hierarchical_input import build_t3_hierarchical_stage_input
from .constants import DEFAULT_TEMPLATE_GENERATION_STRATEGY
from .executor import execute_template_generation_plan
from .final_results import (
    AVAILABLE,
    NOT_AVAILABLE,
    FinalStageResult,
    candidate_ref,
    publish_final_stage_result,
    require_final_stage_result,
)
from .input_contract import build_l1_input_contract
from .manifest import build_template_generation_manifest
from .artifacts import build_template_spec
from .agent.evidence import build_t2_evidence
from .outputs import write_template_generation_outputs
from .plan import build_template_generation_plan
from .request import build_template_generation_request
from .source_tree import inspect_document_facts_docx
from .stage_inputs import (
    build_agent_stage_packet,
    build_t2_stage_input,
    build_t4_stage_input,
    l1_artifact_hash,
)
from .t2_ai import T2AIContractError
from .t4_ai import publish_t4_ai_final
from .verifier import verify_template_parse_build


def generate_template(
    source_template_docx: Path,
    out_dir: Path,
    *,
    strategy: str = DEFAULT_TEMPLATE_GENERATION_STRATEGY,
    agent_config: AgentConfig | None = None,
) -> StageResult:
    if not source_template_docx.exists():
        return StageResult(
            "template_generate",
            Status.UNKNOWN,
            findings=[
                make_finding(
                    1,
                    "template_generate",
                    Status.UNKNOWN,
                    "template_generation_source_missing",
                    "缺少学校原始模板 Word，无法生成可填写模板",
                    "existing source template DOCX",
                    str(source_template_docx),
                    root_cause_bucket="input_missing",
                )
            ],
            coverage=_coverage(input_exists=False),
            blocked_at="template_generate",
        )
    if not is_valid_docx(source_template_docx):
        return StageResult(
            "template_generate",
            Status.FAIL,
            findings=[
                make_finding(
                    1,
                    "template_generate",
                    Status.FAIL,
                    "template_generation_source_invalid",
                    "学校原始模板不是有效 DOCX 包，无法生成可填写模板",
                    "valid source template DOCX",
                    str(source_template_docx),
                    evidence_refs=[str(source_template_docx)],
                    root_cause_bucket="input_invalid",
                )
            ],
            coverage=_coverage(input_exists=True, input_valid_docx=False),
            blocked_at="template_generate",
        )

    request = build_template_generation_request(
        source_template_docx,
        out_dir,
        strategy=strategy,
    )
    document_facts_result = publish_final_stage_result(
        inspect_document_facts_docx(source_template_docx),
        stage_id="T1",
        artifact_type="document_facts",
        artifact_name="01_document_facts.json",
        availability=AVAILABLE,
        producer_mode="code",
    )
    document_facts = document_facts_result.payload
    effective_agent_config = agent_config or AgentConfig(enabled=False)
    render_facts = (
        load_render_packet(effective_agent_config.render_packet_path)
        if effective_agent_config.render_packet_path is not None
        else build_template_agent_render_packet(
            document_facts=document_facts,
            source_template_docx=source_template_docx,
            render_artifacts_dir=out_dir / "agent_render_artifacts",
        )
    )
    l1_result = publish_final_stage_result(
        build_l1_input_contract(
            document_facts=document_facts,
            render_packet=render_facts,
        ),
        stage_id="L1",
        artifact_type="template_generation_l1_input_contract",
        artifact_name="01.5_l1_input_contract.json",
        availability=AVAILABLE,
        producer_mode="sealed_facts",
        input_refs={"t1": document_facts_result.input_ref()},
    )
    l1_input_contract = l1_result.payload
    l1_hash = l1_artifact_hash(l1_input_contract)
    t2_stage_input = build_t2_stage_input(l1_input_contract)
    t4_stage_input = build_t4_stage_input(l1_input_contract)
    agent_stage_packet = build_agent_stage_packet(l1_input_contract)
    source_tree = t2_stage_input["source_tree"]
    t2_input = build_t2_evidence(agent_stage_packet)
    try:
        agent_run = run_template_agent(
            source_template_docx=source_template_docx,
            request=request,
            document_facts=t2_stage_input["facts"],
            source_tree=source_tree,
            agent_config=effective_agent_config,
            render_packet=agent_stage_packet,
            render_artifacts_dir=out_dir / "agent_render_artifacts",
        )
    except (AgentConfigError, T2AIContractError) as exc:
        return StageResult(
            "template_generate",
            Status.FAIL,
            findings=[
                make_finding(
                    1,
                    "template_generate",
                    Status.FAIL,
                    "template_generation_agent_config_invalid",
                    "模板生成 Agent 配置无效",
                    "valid MiniMax live, replay, or bundle AI configuration",
                    str(exc),
                    root_cause_bucket="agent_config_invalid",
                )
            ],
            coverage=_coverage(
                input_exists=True,
                input_valid_docx=True,
                document_facts=bool(document_facts.get("body_flow")),
            ),
                blocked_at="template_generate",
        )
    t2_final_result = require_final_stage_result(
        agent_run.t2_final_result or agent_run.unit_map,
        stage_id="T2",
        artifact_type="unit_map",
        artifact_name="02_unit_map.yaml",
        expected_l1_hash=l1_hash,
    )
    unit_map = t2_final_result.payload
    generation_model = agent_run.generation_model
    t2_ai_unit_observation = agent_run.ai_unit_observation
    t3_ai_element_observation = _route_t3_ai_observation(
        agent_run.ai_element_observation,
        document_facts=t2_stage_input["facts"],
        l1_hash=l1_hash,
    )
    t3_stage_input = _t3_stage_input_for_final(
        agent_run=agent_run,
        packet=agent_stage_packet,
        t2_final=t2_final_result,
    )
    t3_route_element_spec = _route_t3_element_spec(
        agent_run.element_spec,
        observation_available=bool(
            isinstance(agent_run.ai_element_observation, dict)
            and agent_run.ai_element_observation.get("items")
        ),
        l1_hash=l1_hash,
    )
    t3_route = t3_route_element_spec.get("route") or {}
    t3_availability = str(t3_route.get("availability") or NOT_AVAILABLE)
    t3_reason_value = t3_route.get("reason")
    t3_reason = (
        str(t3_reason_value) if t3_reason_value not in (None, "") else None
    )
    element_result = publish_final_stage_result(
        t3_route_element_spec,
        stage_id="T3",
        artifact_type="element_spec",
        artifact_name="03_element_spec.yaml",
        availability=t3_availability,
        reason=t3_reason,
        producer_mode="ai",
        selected_from=[
            candidate_ref(
                t3_ai_element_observation,
                route_id="ai_raw",
                artifact="03.1_t3_ai_element_observation.yaml",
            )
        ],
        input_refs={
            "l1": l1_result.input_ref(),
            "t2_final": t2_final_result.input_ref(),
            "t3_stage_input": {
                "stage_id": "T3_INPUT",
                "artifact": "03.0_t3_hierarchical_stage_input.json",
                "sha256": sha256_json(t3_stage_input),
                "availability": t2_final_result.availability,
            },
        },
    )
    element_spec = element_result.payload
    t4_ai_layout_observation = (
        agent_run.ai_layout_observation
        if isinstance(agent_run.ai_layout_observation, dict)
        else {}
    )
    global_result = publish_t4_ai_final(
        t4_ai_layout_observation,
        packet=agent_stage_packet,
    )
    global_spec = global_result.payload
    template_result = build_template_spec(
        l1_result,
        t2_final_result,
        element_result,
        global_result,
    )
    template_spec = template_result.payload
    plan = build_template_generation_plan(
        request,
        template_final=template_result,
    )
    fillable_template_docx = out_dir / "06.1_fillable_template.docx"
    execution = execute_template_generation_plan(
        source_template_docx,
        fillable_template_docx,
        plan,
        l1_input_contract=l1_input_contract,
    )
    raw_build_manifest = build_template_generation_manifest(
        request=request,
        l1_input_contract=l1_input_contract,
        template_final=template_result,
        plan=plan,
        fillable_template_docx=fillable_template_docx,
        execution=execution,
    )
    build_result = publish_final_stage_result(
        raw_build_manifest,
        stage_id="T6",
        artifact_type="build_manifest",
        artifact_name="06.2_build_manifest.json",
        availability=template_result.availability,
        reason=template_result.reason,
        producer_mode="code",
        input_refs={
            "l1": l1_result.input_ref(),
            "t5_final": template_result.input_ref(),
        },
    )
    build_manifest = build_result.payload
    verification_status, verification_findings, verification_report, verification_coverage = (
        verify_template_parse_build(
            document_facts=document_facts,
            l1_input_contract=l1_input_contract,
            unit_map=unit_map,
            element_spec=element_spec,
            global_spec=global_spec,
            template_spec=template_spec,
            build_manifest=build_manifest,
            fillable_template_docx=fillable_template_docx,
        )
    )
    verification_result = publish_final_stage_result(
        verification_report,
        stage_id="T7",
        artifact_type="verification_report",
        artifact_name="07_verification_report.json",
        availability=build_result.availability,
        reason=build_result.reason,
        producer_mode="code",
        input_refs={
            "l1": l1_result.input_ref(),
            "t5_final": template_result.input_ref(),
            "t6_final": build_result.input_ref(),
        },
    )
    verification_report = verification_result.payload
    artifact_paths = {
        "fillable_template_docx": fillable_template_docx,
        "generated_template_docx": fillable_template_docx,
    }
    artifacts = {
        "template_generation_request": request,
        "document_facts": document_facts,
        "template_generation_l1_input_contract": l1_input_contract,
        "t2_l1_stage_input": t2_stage_input,
        "t4_l1_stage_input": t4_stage_input,
        "unit_map": unit_map,
        "t3_hierarchical_stage_input": t3_stage_input,
        "element_spec": element_spec,
        "global_spec": global_spec,
        "template_spec": template_spec,
        "build_manifest": build_manifest,
        "verification_report": verification_report,
        "source_template_tree": source_tree,
        "template_generation_model": generation_model,
        "template_generation_plan": plan,
        "t2_ai_unit_observation": t2_ai_unit_observation,
        "t3_ai_element_observation": t3_ai_element_observation,
        "t4_ai_layout_observation": t4_ai_layout_observation,
    }
    artifacts["t2_input"] = t2_input
    if agent_run.ai_observation_bundle is not None:
        artifacts["ai_observation_bundle"] = agent_run.ai_observation_bundle
        if isinstance(agent_run.ai_element_observation, dict) and agent_run.ai_element_observation.get(
            "sparse_decision_contract_version"
        ):
            artifacts["t3_sparse_decision_trace"] = {
                "artifact_type": "t3_sparse_decision_trace",
                "artifact_version": agent_run.ai_element_observation.get(
                    "sparse_decision_contract_version"
                ),
                "stage_input_ref": agent_run.ai_element_observation.get("stage_input_ref"),
                "decisions": agent_run.ai_element_observation.get("sparse_decisions", []),
                "atomic_coverage": agent_run.ai_element_observation.get("atomic_coverage", []),
                "call_records": agent_run.ai_element_observation.get("sparse_call_records", []),
                "validation": (
                    agent_run.ai_element_observation.get("quality_report", {}).get(
                        "coverage_validation", {}
                    )
                ),
                "resolution_counts": (
                    agent_run.ai_element_observation.get("quality_report", {}).get(
                        "resolution_counts", {}
                    )
                ),
            }
    if agent_run.t3_materialization_trace is not None:
        artifacts["t3_materialization_trace"] = agent_run.t3_materialization_trace

    run_status = verification_status
    quality_status = Status.UNKNOWN
    overall_status = merge_statuses([run_status, quality_status])
    quality_finding = make_finding(
        len(verification_findings) + 1,
        "template_generate",
        Status.UNKNOWN,
        "template_generation_school_quality_not_evaluated",
        "模板生成阶段只验证结构与执行结果，不能替代学校标准质量裁判",
        "template gap and school standard judge completed",
        "not evaluated in template_generate",
        root_cause_bucket="quality_judge_not_run",
    )
    verification_report["run_status"] = run_status.value
    verification_report["quality_status"] = quality_status.value
    verification_report["status"] = overall_status.value
    verification_report["quality_blocked_at"] = "template_gap_and_school_standard_judge"

    return StageResult(
        "template_generate",
        overall_status,
        run_status=run_status,
        quality_status=quality_status,
        findings=[*verification_findings, quality_finding],
        artifacts=artifacts,
        artifact_paths=artifact_paths,
        coverage=_coverage(
            input_exists=True,
            input_valid_docx=True,
            document_facts=bool(document_facts.get("body_flow")),
            unit_map=bool(unit_map.get("units")),
            element_spec=bool(element_spec.get("elements")),
            global_spec=bool(global_spec.get("section_profiles")),
            template_spec=bool(template_spec.get("units")),
            generation_plan=bool(plan.get("actions")),
            output_docx=fillable_template_docx.exists(),
            manifest=True,
            body_slot=bool(build_manifest.get("slots")),
            **verification_coverage,
        ),
        blocked_at=(
            "template_generate"
            if run_status == Status.FAIL
            else "template_gap_and_school_standard_judge"
        ),
        user_message=(
            "template_generate produced document_facts, template_spec, "
            "06.1_fillable_template.docx and deterministic run verification evidence; "
            "school quality remains UNKNOWN until the downstream judges run."
        ),
    )


def _coverage(
    *,
    input_exists: bool,
    input_valid_docx: bool | None = None,
    document_facts: bool = False,
    unit_map: bool = False,
    element_spec: bool = False,
    global_spec: bool = False,
    template_spec: bool = False,
    generation_plan: bool = False,
    output_docx: bool = False,
    manifest: bool = False,
    body_slot: bool = False,
    **extra: bool,
) -> dict[str, bool]:
    coverage = {
        "template_generation.input_exists": input_exists,
        "template_generation.input_valid_docx": bool(input_valid_docx),
        "template_generation.document_facts": document_facts,
        "template_generation.unit_map": unit_map,
        "template_generation.element_spec": element_spec,
        "template_generation.global_spec": global_spec,
        "template_generation.template_spec": template_spec,
        "template_generation.plan": generation_plan,
        "template_generation.fillable_template_docx": output_docx,
        "template_generation.build_manifest": manifest,
        "template_generation.body_slot": body_slot,
    }
    coverage.update(extra)
    return coverage


def _t3_stage_input_for_final(
    *,
    agent_run: Any,
    packet: dict[str, Any],
    t2_final: FinalStageResult,
) -> dict[str, Any]:
    bundle = agent_run.ai_observation_bundle
    stage_input = (
        bundle.get("t3_hierarchical_stage_input")
        if isinstance(bundle, dict)
        else None
    )
    contract = (
        stage_input.get("contract")
        if isinstance(stage_input, dict)
        and isinstance(stage_input.get("contract"), dict)
        else {}
    )
    if (
        isinstance(stage_input, dict)
        and contract.get("l1_hash") == packet.get("input_contract_hash")
        and contract.get("t2_final_hash") == t2_final.sha256
    ):
        return stage_input
    return build_t3_hierarchical_stage_input(
        packet,
        t2_final=t2_final,
    )


def _route_t3_element_spec(
    element_spec: dict[str, object],
    *,
    observation_available: bool,
    l1_hash: str,
) -> dict[str, object]:
    routed = _route_stage_artifact(
        element_spec,
        route_id="ai",
        stage_id="T3",
        stage_key="t3_element_policy",
        origin=(
            "hierarchical_ai_decisions_materialized"
            if observation_available
            else "ai_unavailable_safe_keep_materialization"
        ),
        l1_hash=l1_hash,
    )
    if not observation_available:
        route = routed["route"]
        assert isinstance(route, dict)
        route["availability"] = "NOT_AVAILABLE"
        route["reason"] = (
            "T3 AI observation was not produced; downstream receives conservative "
            "safe Keep materialization instead of a Code decision route"
        )
    return routed


def _route_stage_artifact(
    payload: dict[str, object],
    *,
    route_id: str,
    stage_id: str,
    stage_key: str,
    origin: str,
    l1_hash: str,
) -> dict[str, object]:
    routed = deepcopy(payload)
    routed["route"] = {
        "route_id": route_id,
        "stage_id": stage_id,
        "stage_key": stage_key,
        "availability": "AVAILABLE",
        "origin": origin,
        "l1_hash": l1_hash,
    }
    return routed


def _route_t3_ai_observation(
    ai_element_observation: dict[str, object] | None,
    *,
    document_facts: dict[str, object],
    l1_hash: str,
) -> dict[str, object]:
    if isinstance(ai_element_observation, dict):
        routed = deepcopy(ai_element_observation)
        routed["route"] = {
            "route_id": "ai_raw",
            "stage_id": "T3",
            "stage_key": "t3_element_policy",
            "availability": "AVAILABLE",
            "origin": "module1_ai_element_observation",
            "l1_hash": l1_hash,
        }
        return routed
    return _unavailable_ai_observation(
        artifact_type="ai_element_observation",
        stage="t3",
        stage_id="T3",
        stage_key="t3_element_policy",
        origin="module1_ai_element_observation",
        document_facts=document_facts,
        l1_hash=l1_hash,
    )


def _unavailable_ai_observation(
    *,
    artifact_type: str,
    stage: str,
    stage_id: str,
    stage_key: str,
    origin: str,
    document_facts: dict[str, object],
    l1_hash: str,
) -> dict[str, object]:
    source_seq_refs = _document_source_seq_refs(document_facts)
    return {
        "artifact_type": artifact_type,
        "stage": stage,
        "created_at": now_iso(),
        "schema_version": None,
        "model": None,
        "route": {
            "route_id": "ai_raw",
            "stage_id": stage_id,
            "stage_key": stage_key,
            "availability": "NOT_AVAILABLE",
            "origin": origin,
            "l1_hash": l1_hash,
            "reason": "no AI observation bundle was supplied for this run",
        },
        "items": [],
        "unknown_items": [],
        "open_questions": [],
        "coverage": {
            "owned_source_seq": [],
            "unknown_source_seq": [],
            "total": len(source_seq_refs),
        },
    }


def _document_source_seq_refs(document_facts: dict[str, object]) -> list[int]:
    return [
        int(item["source_seq"])
        for item in document_facts.get("body_flow", [])
        if isinstance(item, dict) and item.get("source_seq") is not None
    ]
