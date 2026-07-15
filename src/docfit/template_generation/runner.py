from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from docfit.core.io import now_iso
from docfit.core.models import StageResult, make_finding
from docfit.core.status import Status
from docfit.ooxml.package import is_valid_docx

from .agent import AgentConfig, AgentConfigError, run_template_agent
from .constants import BODY_SLOT_MARKER, DEFAULT_TEMPLATE_GENERATION_STRATEGY
from .executor import execute_template_generation_plan
from .generation_model import build_template_generation_model
from .input_contract import build_l1_input_contract
from .manifest import build_template_generation_manifest
from .artifacts import (
    build_element_spec,
    build_global_spec,
    build_template_spec,
    build_unit_map,
    source_tree_from_document_facts,
    template_artifact_view_from_template_spec,
)
from .outputs import (
    _new_template_generation_debug_dir,
    write_template_generation_debug_snapshot,
    write_template_generation_outputs,
)
from .plan import build_template_generation_plan
from .request import build_template_generation_request
from .source_tree import inspect_document_facts_docx
from .structure_candidates import build_template_structure_candidates
from .verifier import verify_template_parse_build


def generate_template(
    source_template_docx: Path,
    out_dir: Path,
    *,
    strategy: str = DEFAULT_TEMPLATE_GENERATION_STRATEGY,
    debug_root: Path | None = None,
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

    debug_dir = _new_template_generation_debug_dir(debug_root)
    copy_source_snapshot_docx = (
        debug_dir / "06.0_copy_source_docx.docx" if debug_dir is not None else None
    )

    request = build_template_generation_request(
        source_template_docx,
        out_dir,
        strategy=strategy,
    )
    document_facts = inspect_document_facts_docx(source_template_docx)
    source_tree = source_tree_from_document_facts(document_facts)
    structure_candidates = build_template_structure_candidates(source_tree)
    t2_input = structure_candidates.get("t2_input")
    unit_map = build_unit_map(document_facts, structure_candidates)
    code_raw_unit_map = _route_t2_unit_map(
        unit_map,
        route_id="code_raw",
        origin="deterministic_code_before_agent_bridge",
    )
    global_spec = build_global_spec(document_facts)
    code_raw_global_spec = _route_t4_global_spec(
        global_spec,
        route_id="code_raw",
        origin="deterministic_code_before_agent_bridge",
    )
    generation_model = build_template_generation_model(
        request,
        structure_candidates=structure_candidates,
    )
    element_spec = build_element_spec(generation_model)
    code_raw_element_spec = _route_t3_element_spec(
        element_spec,
        route_id="code_raw",
        origin="deterministic_code_before_agent_bridge",
    )
    effective_agent_config = agent_config or AgentConfig(enabled=False)
    try:
        agent_run = run_template_agent(
            source_template_docx=source_template_docx,
            request=request,
            document_facts=document_facts,
            structure_candidates=structure_candidates,
            unit_map=unit_map,
            generation_model=generation_model,
            element_spec=element_spec,
            agent_config=effective_agent_config,
            render_artifacts_dir=out_dir / "agent_render_artifacts",
        )
    except AgentConfigError as exc:
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
                    "valid default-off, replay, or live agent configuration",
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
    structure_candidates = agent_run.structure_candidates
    t2_input = structure_candidates.get("t2_input")
    unit_map = agent_run.unit_map
    generation_model = agent_run.generation_model
    global_spec = _merge_t4_agent_hints(global_spec, agent_run.t4_hints)
    t2_ai_unit_observation = _route_t2_ai_observation(
        agent_run.ai_unit_observation,
        document_facts=document_facts,
    )
    t2_merged_unit_map = _route_t2_unit_map(
        unit_map,
        route_id="merged",
        origin="agent_bridge_reconciled_final_t2",
    )
    element_spec = agent_run.element_spec
    t3_ai_element_observation = _route_t3_ai_observation(
        agent_run.ai_element_observation,
        document_facts=document_facts,
    )
    t3_merged_element_spec = _route_t3_element_spec(
        element_spec,
        route_id="merged",
        origin="agent_bridge_reconciled_final_t3",
    )
    t4_ai_layout_observation = _route_t4_ai_observation(
        agent_run.ai_layout_observation,
        document_facts=document_facts,
    )
    t4_merged_global_spec = _route_t4_global_spec(
        global_spec,
        route_id="merged",
        origin="agent_bridge_reconciled_final_t4",
    )
    l1_input_contract = build_l1_input_contract(
        document_facts=document_facts,
        render_packet=agent_run.render_packet,
        ai_observation_bundle=agent_run.ai_observation_bundle,
        observation_bridge=agent_run.observation_bridge,
    )
    template_spec = build_template_spec(
        document_facts,
        unit_map,
        element_spec,
        global_spec,
    )
    plan = build_template_generation_plan(
        request,
        generation_model=generation_model,
    )
    fillable_template_docx = out_dir / "fillable_template.docx"
    execution = execute_template_generation_plan(
        source_template_docx,
        fillable_template_docx,
        plan,
        copy_source_snapshot_docx=copy_source_snapshot_docx,
    )
    build_manifest = build_template_generation_manifest(
        request=request,
        document_facts=document_facts,
        unit_map=unit_map,
        element_spec=element_spec,
        global_spec=global_spec,
        template_spec=template_spec,
        plan=plan,
        fillable_template_docx=fillable_template_docx,
        execution=execution,
        debug_snapshot_dir=debug_dir,
        copy_source_snapshot_docx=copy_source_snapshot_docx,
    )
    template_artifact = template_artifact_view_from_template_spec(
        request,
        template_spec,
        fillable_template_docx=str(fillable_template_docx),
        build_manifest="build_manifest.json",
    )
    verification_status, verification_findings, verification_report, verification_coverage = (
        verify_template_parse_build(
            document_facts=document_facts,
            unit_map=unit_map,
            element_spec=element_spec,
            global_spec=global_spec,
            template_spec=template_spec,
            build_manifest=build_manifest,
            fillable_template_docx=fillable_template_docx,
        )
    )
    if debug_dir is not None:
        write_template_generation_debug_snapshot(
            debug_dir,
            source_template_docx=source_template_docx,
            request=request,
            document_facts=document_facts,
            l1_input_contract=l1_input_contract,
            unit_map=unit_map,
            element_spec=element_spec,
            global_spec=global_spec,
            template_spec=template_spec,
            source_tree=source_tree,
            structure_candidates=structure_candidates,
            generation_model=generation_model,
            plan=plan,
            copy_source_snapshot_docx=copy_source_snapshot_docx,
            fillable_template_docx=fillable_template_docx,
            build_manifest=build_manifest,
            verification_report=verification_report,
            t2_input=t2_input if isinstance(t2_input, dict) else None,
            t2_code_unit_map=code_raw_unit_map,
            t2_ai_unit_observation=t2_ai_unit_observation,
            t2_merged_unit_map=t2_merged_unit_map,
            t3_code_element_spec=code_raw_element_spec,
            t3_ai_element_observation=t3_ai_element_observation,
            t3_merged_element_spec=t3_merged_element_spec,
            t4_code_global_spec=code_raw_global_spec,
            t4_ai_layout_observation=t4_ai_layout_observation,
            t4_merged_global_spec=t4_merged_global_spec,
            agent_render_packet=agent_run.render_packet,
            agent_pass_plan=agent_run.pass_plan,
            agent_post_t2_checkpoint=agent_run.post_t2_checkpoint,
            agent_post_t2_input=agent_run.post_t2_input,
            agent_unit_windows=agent_run.unit_windows,
            agent_transcript=agent_run.transcript,
            agent_observation_bundle=agent_run.ai_observation_bundle,
            agent_observation_bridge=agent_run.observation_bridge,
            agent_submission_comparison=agent_run.submission_comparison,
            agent_decisions=agent_run.decisions,
            agent_manual_review_items=agent_run.manual_review_items,
            agent_t2_overlay=agent_run.t2_overlay,
            agent_t3_overlay=agent_run.t3_overlay,
            agent_t4_hints=agent_run.t4_hints,
            agent_attribution=agent_run.attribution,
        )

    artifact_paths = {
        "fillable_template_docx": fillable_template_docx,
        "generated_template_docx": fillable_template_docx,
    }
    if debug_dir is not None:
        artifact_paths["template_generation_debug_dir"] = debug_dir

    artifacts = {
        "template_generation_request": request,
        "document_facts": document_facts,
        "template_generation_l1_input_contract": l1_input_contract,
        "unit_map": unit_map,
        "element_spec": element_spec,
        "global_spec": global_spec,
        "template_spec": template_spec,
        "build_manifest": build_manifest,
        "verification_report": verification_report,
        "template_artifact": template_artifact,
        "source_template_tree": source_tree,
        "template_structure_candidates": structure_candidates,
        "template_generation_model": generation_model,
        "template_generation_plan": plan,
        "t2_code_unit_map": code_raw_unit_map,
        "t2_ai_unit_observation": t2_ai_unit_observation,
        "t2_merged_unit_map": t2_merged_unit_map,
        "t3_code_element_spec": code_raw_element_spec,
        "t3_ai_element_observation": t3_ai_element_observation,
        "t3_merged_element_spec": t3_merged_element_spec,
        "t4_code_global_spec": code_raw_global_spec,
        "t4_ai_layout_observation": t4_ai_layout_observation,
        "t4_merged_global_spec": t4_merged_global_spec,
    }
    if isinstance(t2_input, dict):
        artifacts["t2_input"] = t2_input
    if agent_run.render_packet is not None:
        artifacts["template_agent_render_packet"] = agent_run.render_packet
    if agent_run.pass_plan is not None:
        artifacts["template_agent_pass_plan"] = agent_run.pass_plan
    if agent_run.post_t2_checkpoint is not None:
        artifacts["template_agent_post_t2_checkpoint"] = agent_run.post_t2_checkpoint
    if agent_run.post_t2_input is not None:
        artifacts["template_agent_post_t2_input"] = agent_run.post_t2_input
    if agent_run.unit_windows is not None:
        artifacts["template_agent_unit_windows"] = agent_run.unit_windows
    if agent_run.transcript is not None:
        artifacts["template_agent_transcript"] = agent_run.transcript
    if agent_run.ai_observation_bundle is not None:
        artifacts["ai_observation_bundle"] = agent_run.ai_observation_bundle
    if agent_run.observation_bridge is not None:
        artifacts["template_agent_observation_bridge"] = agent_run.observation_bridge
    if agent_run.submission_comparison is not None:
        artifacts["template_agent_submission_comparison"] = (
            agent_run.submission_comparison
        )
    if agent_run.decisions is not None:
        artifacts["template_agent_decisions"] = agent_run.decisions
    if agent_run.manual_review_items is not None:
        artifacts["template_agent_manual_review_items"] = agent_run.manual_review_items
    if agent_run.t2_overlay is not None:
        artifacts["agent_t2_overlay"] = agent_run.t2_overlay
    if agent_run.t3_overlay is not None:
        artifacts["agent_t3_overlay"] = agent_run.t3_overlay
    if agent_run.t4_hints is not None:
        artifacts["agent_t4_hints"] = agent_run.t4_hints
    if agent_run.attribution is not None:
        artifacts["agent_attribution"] = agent_run.attribution

    return StageResult(
        "template_generate",
        verification_status,
        findings=verification_findings,
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
        user_message=(
            "template_generate produced document_facts, template_spec, "
            "fillable_template.docx, and deterministic verification evidence."
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


def _route_t2_unit_map(
    unit_map: dict[str, object],
    *,
    route_id: str,
    origin: str,
) -> dict[str, object]:
    return _route_stage_artifact(
        unit_map,
        route_id=route_id,
        stage_id="T2",
        stage_key="t2_unit_recognition",
        origin=origin,
    )


def _route_t3_element_spec(
    element_spec: dict[str, object],
    *,
    route_id: str,
    origin: str,
) -> dict[str, object]:
    return _route_stage_artifact(
        element_spec,
        route_id=route_id,
        stage_id="T3",
        stage_key="t3_element_policy",
        origin=origin,
    )


def _route_t4_global_spec(
    global_spec: dict[str, object],
    *,
    route_id: str,
    origin: str,
) -> dict[str, object]:
    return _route_stage_artifact(
        global_spec,
        route_id=route_id,
        stage_id="T4",
        stage_key="t4_global_layout",
        origin=origin,
    )


def _merge_t4_agent_hints(
    global_spec: dict[str, object],
    t4_hints: dict[str, Any] | None,
) -> dict[str, object]:
    if not isinstance(t4_hints, dict):
        return global_spec
    collections = (
        "section_profile_hints",
        "page_numbering_hints",
    )
    hints_by_collection = {
        collection: deepcopy(t4_hints.get(collection) or [])
        for collection in collections
        if t4_hints.get(collection)
    }
    accepted_count = sum(len(hints) for hints in hints_by_collection.values())
    if accepted_count == 0:
        return global_spec

    merged = deepcopy(global_spec)
    consumption = merged.setdefault("layout_hint_consumption", {})
    if not isinstance(consumption, dict):
        consumption = {}
        merged["layout_hint_consumption"] = consumption
    consumption.setdefault("section_profile_hints", [])
    consumption.setdefault("page_numbering_hints", [])
    section_profile_hints = hints_by_collection.get("section_profile_hints", [])
    if section_profile_hints:
        profiles = merged.get("section_profiles")
        if isinstance(profiles, list) and profiles:
            profile = profiles[0]
            if isinstance(profile, dict):
                observations = profile.setdefault("ai_observations", [])
                if isinstance(observations, list):
                    observations.extend(section_profile_hints)
                profile["origin"] = "deterministic_with_ai_observation"
                profile["changed_from_code"] = False
                profile["explicit_noop_with_reason"] = (
                    "accepted T4 section_profile_hint confirms deterministic section profile; "
                    "field-level AI override is not required"
                )
                effective = profile.setdefault("effective_ai_layout_actions", [])
                if isinstance(effective, list):
                    for hint in section_profile_hints:
                        effective.append(
                            _layout_hint_effective_record(
                                hint,
                                action="explicit_noop_confirm_section_profile",
                                reason=profile["explicit_noop_with_reason"],
                            )
                        )
                if isinstance(consumption.get("section_profile_hints"), list):
                    for hint in section_profile_hints:
                        consumption["section_profile_hints"].append(
                            _layout_hint_effective_record(
                                hint,
                                action="explicit_noop_confirm_section_profile",
                                reason=profile["explicit_noop_with_reason"],
                            )
                        )
    page_numbering_hints = hints_by_collection.get("page_numbering_hints", [])
    if page_numbering_hints:
        page_numbering = merged.setdefault("page_numbering", {})
        if isinstance(page_numbering, dict):
            page_numbering["origin"] = "deterministic_with_ai_observation"
            page_numbering["ai_observations"] = page_numbering_hints
            page_numbering["changed_from_code"] = False
            page_numbering["explicit_noop_with_reason"] = (
                "accepted T4 page_numbering_hint recorded as field evidence"
            )
            effective = page_numbering.setdefault("effective_ai_layout_actions", [])
            if isinstance(effective, list):
                for hint in page_numbering_hints:
                    effective.append(
                        _layout_hint_effective_record(
                            hint,
                            action="explicit_noop_record_page_numbering_evidence",
                            reason=page_numbering["explicit_noop_with_reason"],
                        )
                    )
            if isinstance(consumption.get("page_numbering_hints"), list):
                for hint in page_numbering_hints:
                    consumption["page_numbering_hints"].append(
                        _layout_hint_effective_record(
                            hint,
                            action="explicit_noop_record_page_numbering_evidence",
                            reason=page_numbering["explicit_noop_with_reason"],
                        )
                    )
    merge_trace = merged.setdefault("merge_trace", [])
    if isinstance(merge_trace, list):
        merge_trace.append(
            {
                "stage_id": "T4",
                "source_artifact": "agent_t4_hints",
                "operation": "merge_accepted_layout_hints_into_fields",
                "accepted_count": accepted_count,
                "collections": sorted(hints_by_collection),
            }
        )
    return merged


def _layout_hint_effective_record(
    hint: dict[str, Any],
    *,
    action: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "proposal_id": hint.get("proposal_id"),
        "kind": hint.get("kind"),
        "effective_action": action,
        "reason": reason,
        "source_seq_refs": hint.get("source_seq_refs", []),
        "page_nos": hint.get("page_nos", []),
        "render_target_refs": hint.get("render_target_refs", []),
        "changed_authoritative_field": False,
    }


def _route_stage_artifact(
    payload: dict[str, object],
    *,
    route_id: str,
    stage_id: str,
    stage_key: str,
    origin: str,
) -> dict[str, object]:
    routed = deepcopy(payload)
    routed["route"] = {
        "route_id": route_id,
        "stage_id": stage_id,
        "stage_key": stage_key,
        "availability": "AVAILABLE",
        "origin": origin,
    }
    return routed


def _route_t2_ai_observation(
    ai_unit_observation: dict[str, object] | None,
    *,
    document_facts: dict[str, object],
) -> dict[str, object]:
    if isinstance(ai_unit_observation, dict):
        routed = deepcopy(ai_unit_observation)
        routed["route"] = {
            "route_id": "ai_raw",
            "stage_id": "T2",
            "stage_key": "t2_unit_recognition",
            "availability": "AVAILABLE",
            "origin": "module1_ai_unit_observation",
        }
        return routed
    return _unavailable_ai_observation(
        artifact_type="ai_unit_observation",
        stage="t2",
        stage_id="T2",
        stage_key="t2_unit_recognition",
        origin="module1_ai_unit_observation",
        document_facts=document_facts,
    )


def _route_t3_ai_observation(
    ai_element_observation: dict[str, object] | None,
    *,
    document_facts: dict[str, object],
) -> dict[str, object]:
    if isinstance(ai_element_observation, dict):
        routed = deepcopy(ai_element_observation)
        routed["route"] = {
            "route_id": "ai_raw",
            "stage_id": "T3",
            "stage_key": "t3_element_policy",
            "availability": "AVAILABLE",
            "origin": "module1_ai_element_observation",
        }
        return routed
    return _unavailable_ai_observation(
        artifact_type="ai_element_observation",
        stage="t3",
        stage_id="T3",
        stage_key="t3_element_policy",
        origin="module1_ai_element_observation",
        document_facts=document_facts,
    )


def _route_t4_ai_observation(
    ai_layout_observation: dict[str, object] | None,
    *,
    document_facts: dict[str, object],
) -> dict[str, object]:
    if isinstance(ai_layout_observation, dict):
        routed = deepcopy(ai_layout_observation)
        routed["route"] = {
            "route_id": "ai_raw",
            "stage_id": "T4",
            "stage_key": "t4_global_layout",
            "availability": "AVAILABLE",
            "origin": "module1_ai_layout_observation",
        }
        return routed
    routed = _unavailable_ai_observation(
        artifact_type="ai_layout_observation",
        stage="t4",
        stage_id="T4",
        stage_key="t4_global_layout",
        origin="module1_ai_layout_observation",
        document_facts=document_facts,
    )
    routed["default_font"] = None
    routed["page_numbering"] = None
    routed["header_footer"] = []
    routed["numbering_rules"] = []
    return routed


def _unavailable_ai_observation(
    *,
    artifact_type: str,
    stage: str,
    stage_id: str,
    stage_key: str,
    origin: str,
    document_facts: dict[str, object],
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
