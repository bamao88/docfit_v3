from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_json
from docfit.template_generation.input_contract import build_l1_input_contract
from docfit.template_generation.stage_inputs import build_agent_stage_packet

from .attribution import (
    build_agent_attribution,
    build_agent_decisions,
    build_agent_pass_plan,
    build_agent_t2_overlay,
    build_agent_t3_overlay,
    build_agent_t4_hints,
)
from .ai_primary import materialize_ai_primary_t3_structure
from .comparison import (
    blocking_open_questions_by_layer,
    build_submission_comparison,
    compare_blocked_by_open_questions,
    compare_proposal,
    comparison_rejection_decision,
)
from .config import AgentConfig, AgentConfigError, require_valid_agent_config
from .manual_review import build_agent_manual_review_items
from .observation_bridge import (
    build_observation_bridge,
    observation_bridge_transcript,
)
from .observation_orchestrate import run_module1_observation_for_template_generate
from .overlay import apply_t2_boundary_adjustment_batch
from .packet import build_template_agent_render_packet, load_render_packet
from .reconciler import process_proposal
from .regenerate import regenerate_from_structure_candidates
from .replay import load_agent_transcript, pass_plan_from_steps, transcript_steps
from .schema import iter_layer_proposals, schema_error_decisions, validate_layered_submission
from .windows import build_agent_unit_windows, t3_window_error, window_for_step


@dataclass
class AgentRunResult:
    enabled: bool
    changed: bool
    structure_candidates: dict[str, Any]
    unit_map: dict[str, Any]
    generation_model: dict[str, Any]
    element_spec: dict[str, Any]
    ai_unit_observation: dict[str, Any] | None = None
    ai_element_observation: dict[str, Any] | None = None
    ai_layout_observation: dict[str, Any] | None = None
    ai_observation_bundle: dict[str, Any] | None = None
    render_packet: dict[str, Any] | None = None
    pass_plan: dict[str, Any] | None = None
    post_t2_checkpoint: dict[str, Any] | None = None
    post_t2_input: dict[str, Any] | None = None
    unit_windows: dict[str, Any] | None = None
    transcript: dict[str, Any] | None = None
    observation_bridge: dict[str, Any] | None = None
    submission_comparison: dict[str, Any] | None = None
    decisions: dict[str, Any] | None = None
    manual_review_items: dict[str, Any] | None = None
    t2_overlay: dict[str, Any] | None = None
    t3_overlay: dict[str, Any] | None = None
    t4_hints: dict[str, Any] | None = None
    attribution: dict[str, Any] | None = None


def run_template_agent(
    *,
    source_template_docx: Path,
    request: dict[str, Any],
    document_facts: dict[str, Any],
    structure_candidates: dict[str, Any],
    unit_map: dict[str, Any],
    generation_model: dict[str, Any],
    element_spec: dict[str, Any],
    agent_config: AgentConfig,
    render_packet: dict[str, Any] | None = None,
    render_artifacts_dir: Path | None = None,
) -> AgentRunResult:
    if not agent_config.enabled:
        return AgentRunResult(
            enabled=False,
            changed=False,
            structure_candidates=structure_candidates,
            unit_map=unit_map,
            generation_model=generation_model,
            element_spec=element_spec,
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
                structure_candidates=structure_candidates,
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
        and not agent_config.allow_live_without_real_render
    ):
        raise AgentConfigError(
            "live agent transport requires a real_render packet; "
            f"got render_status={packet.get('render_status') or 'missing'}"
        )
    observation_bridge: dict[str, Any] | None = None
    observation_bundle = run_module1_observation_for_template_generate(
        packet=packet,
        agent_config=agent_config,
    )
    if observation_bundle is not None:
        observation_bridge = build_observation_bridge(
            observation_bundle=observation_bundle,
            packet=packet,
            structure_candidates=structure_candidates,
            t3_authority_mode=agent_config.t3_authority_mode,
        )
        ai_unit_observation = observation_bundle.get("ai_unit_observation")
        ai_element_observation = observation_bundle.get("ai_element_observation")
        ai_layout_observation = observation_bundle.get("ai_layout_observation")
        transcript = observation_bridge_transcript(observation_bridge)
        steps = transcript_steps(transcript, max_rounds=agent_config.max_rounds)
    else:
        ai_unit_observation = None
        ai_element_observation = None
        ai_layout_observation = None
        transcript, steps = _load_submissions(agent_config)
    pass_plan = build_agent_pass_plan(
        pass_plan_from_steps(
            steps,
            provider=str(transcript.get("provider") or agent_config.transport),
        )
    )

    current_structure = structure_candidates
    decisions: list[dict[str, Any]] = []
    comparison_items: list[dict[str, Any]] = []
    t2_operations: list[dict[str, Any]] = []
    t3_operations: list[dict[str, Any]] = []
    t4_hints: list[dict[str, Any]] = []
    post_t2_checkpoint: dict[str, Any] | None = None
    post_t2_input: dict[str, Any] | None = None
    unit_windows: dict[str, Any] | None = None

    expected_hash = packet.get("source_render_hash")
    for step in steps:
        if _requires_post_t2_checkpoint(step) and post_t2_checkpoint is None:
            post_t2_checkpoint = _build_post_t2_checkpoint(
                request=request,
                document_facts=document_facts,
                structure_candidates=current_structure,
                changed=bool(t2_operations),
                fallback_unit_map=unit_map,
            )
            post_t2_input = _build_post_t2_input(
                structure_candidates=current_structure,
                changed=bool(t2_operations),
            )
            unit_windows = build_agent_unit_windows(
                structure_candidates=current_structure,
                packet=packet,
            )
        submission = step["submission"]
        pass_context = _pass_context(step)
        allowed_layers = set(step.get("allowed_layers") or ["t2", "t3", "t4"])
        active_window = window_for_step(unit_windows, step)
        round_id = str(submission.get("round_id") or "")
        validation = validate_layered_submission(
            submission,
            expected_source_render_hash=str(expected_hash or ""),
        )
        if not validation["valid"]:
            for decision in schema_error_decisions(validation, round_id=round_id):
                decision.update(pass_context)
                decisions.append(decision)
            continue
        normalized = validation["submission"]
        blocking_questions = blocking_open_questions_by_layer(normalized)
        batch_processed_proposal_ids, batch_structure = _process_t2_boundary_adjustment_batch(
            normalized=normalized,
            pass_context=pass_context,
            allowed_layers=allowed_layers,
            blocking_questions=blocking_questions,
            post_t2_checkpoint=post_t2_checkpoint,
            current_structure=current_structure,
            packet=packet,
            comparison_items=comparison_items,
            decisions=decisions,
            t2_operations=t2_operations,
        )
        if batch_structure is not None:
            current_structure = batch_structure
        for layer, collection, proposal in iter_layer_proposals(normalized):
            proposal["round_id"] = proposal.get("round_id") or normalized.get("round_id")
            proposal.update(pass_context)
            if str(proposal.get("proposal_id") or "") in batch_processed_proposal_ids:
                continue
            if layer not in allowed_layers:
                decisions.append(
                    _pass_scope_decision(
                        proposal,
                        layer=layer,
                        collection=collection,
                        allowed_layers=sorted(allowed_layers),
                    )
                )
                continue
            if layer in blocking_questions:
                comparison_item = compare_blocked_by_open_questions(
                    proposal=proposal,
                    layer=layer,
                    collection=collection,
                    open_questions=blocking_questions[layer],
                )
                comparison_items.append(comparison_item)
                decisions.append(comparison_rejection_decision(comparison_item))
                continue
            if layer == "t2" and post_t2_checkpoint is not None:
                decisions.append(_pass_order_decision(proposal))
                continue
            if layer == "t3":
                window_error = t3_window_error(
                    proposal=proposal,
                    window=active_window,
                )
                if window_error is not None:
                    decisions.append(
                        _window_scope_decision(
                            proposal,
                            reason=window_error,
                        )
                    )
                    continue
                if agent_config.t3_authority_mode == "ai_primary":
                    decisions.append(
                        {
                            "proposal_id": proposal.get("proposal_id"),
                            "layer": "t3",
                            "collection": collection,
                            "decision": "accepted",
                            "reason": (
                                "AI-primary route defers this atomic policy to direct "
                                "authority materialization without Code comparison"
                            ),
                            "authority": "ai_primary",
                            "merge_enabled": False,
                            **pass_context,
                        }
                    )
                    continue
            comparison_item = compare_proposal(
                structure_candidates=current_structure,
                packet=packet,
                proposal=proposal,
                layer=layer,
                collection=collection,
            )
            comparison_items.append(comparison_item)
            if not comparison_item.get("can_auto_execute"):
                decisions.append(comparison_rejection_decision(comparison_item))
                continue
            current_structure, decision, payload = process_proposal(
                structure_candidates=current_structure,
                packet=packet,
                proposal=proposal,
                layer=layer,
                collection=collection,
            )
            if decision is not None:
                decision.update(pass_context)
                decisions.append(decision)
            if payload is None or decision is None or decision.get("decision") != "accepted":
                continue
            payload.update(pass_context)
            if layer == "t2":
                t2_operations.append(payload)
            elif layer == "t3":
                t3_operations.append(payload)
            elif layer == "t4":
                t4_hints.append(payload)

    if post_t2_checkpoint is None and t2_operations:
        post_t2_checkpoint = _build_post_t2_checkpoint(
            request=request,
            document_facts=document_facts,
            structure_candidates=current_structure,
            changed=True,
            fallback_unit_map=unit_map,
        )
        post_t2_input = _build_post_t2_input(
            structure_candidates=current_structure,
            changed=True,
        )
        unit_windows = build_agent_unit_windows(
            structure_candidates=current_structure,
            packet=packet,
        )

    if (
        agent_config.t3_authority_mode == "ai_primary"
        and isinstance(ai_element_observation, dict)
    ):
        current_structure, ai_primary_operation = materialize_ai_primary_t3_structure(
            current_structure,
            ai_element_observation,
        )
        t3_operations = [ai_primary_operation]

    changed = bool(t2_operations or t3_operations)
    regenerated = (
        regenerate_from_structure_candidates(
            request=request,
            document_facts=document_facts,
            structure_candidates=current_structure,
            include_source_instruction_heuristics=(
                agent_config.t3_authority_mode != "ai_primary"
            ),
        )
        if changed
        else {
            "unit_map": unit_map,
            "generation_model": generation_model,
            "element_spec": element_spec,
        }
    )
    decisions_artifact = build_agent_decisions(decisions)
    submission_comparison = build_submission_comparison(
        comparison_items,
        packet=packet,
        deterministic_structure=structure_candidates,
    )
    manual_review_items = build_agent_manual_review_items(
        transcript=transcript,
        comparison=submission_comparison,
        decisions=decisions_artifact,
        observation_bridge=observation_bridge,
    )
    t2_overlay = build_agent_t2_overlay(t2_operations)
    t3_overlay = build_agent_t3_overlay(t3_operations)
    t4_hints_artifact = build_agent_t4_hints(t4_hints)
    attribution = build_agent_attribution(
        transcript=transcript,
        decisions=decisions_artifact,
        round0_unit_map=unit_map,
        post_agent_unit_map=regenerated["unit_map"],
        round0_element_spec=element_spec,
        post_agent_element_spec=regenerated["element_spec"],
        t2_overlay=t2_overlay,
        t3_overlay=t3_overlay,
        t4_hints=t4_hints_artifact,
        submission_comparison=submission_comparison,
        manual_review_items=manual_review_items,
        observation_bridge=observation_bridge,
    )
    return AgentRunResult(
        enabled=True,
        changed=changed,
        structure_candidates=current_structure,
        unit_map=regenerated["unit_map"],
        generation_model=regenerated["generation_model"],
        element_spec=regenerated["element_spec"],
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
        pass_plan=pass_plan,
        post_t2_checkpoint=post_t2_checkpoint,
        post_t2_input=post_t2_input,
        unit_windows=unit_windows,
        transcript=transcript,
        observation_bridge=observation_bridge,
        submission_comparison=submission_comparison,
        decisions=decisions_artifact,
        manual_review_items=manual_review_items,
        t2_overlay=t2_overlay,
        t3_overlay=t3_overlay,
        t4_hints=t4_hints_artifact,
        attribution=attribution,
    )


def _process_t2_boundary_adjustment_batch(
    *,
    normalized: dict[str, Any],
    pass_context: dict[str, Any],
    allowed_layers: set[str],
    blocking_questions: dict[str, list[dict[str, Any]]],
    post_t2_checkpoint: dict[str, Any] | None,
    current_structure: dict[str, Any],
    packet: dict[str, Any],
    comparison_items: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    t2_operations: list[dict[str, Any]],
) -> tuple[set[str], dict[str, Any] | None]:
    proposals = [
        proposal
        for proposal in (
            normalized.get("layers", {})
            .get("t2", {})
            .get("boundary_adjustments", [])
            or []
        )
        if isinstance(proposal, dict)
    ]
    if len(proposals) < 2:
        return set(), None
    proposal_ids = {str(proposal.get("proposal_id") or "") for proposal in proposals}
    proposal_ids.discard("")
    for proposal in proposals:
        proposal["round_id"] = proposal.get("round_id") or normalized.get("round_id")
        proposal.update(pass_context)

    if "t2" not in allowed_layers:
        for proposal in proposals:
            decisions.append(
                _pass_scope_decision(
                    proposal,
                    layer="t2",
                    collection="boundary_adjustments",
                    allowed_layers=sorted(allowed_layers),
                )
            )
        return proposal_ids, None
    if "t2" in blocking_questions:
        for proposal in proposals:
            comparison_item = compare_blocked_by_open_questions(
                proposal=proposal,
                layer="t2",
                collection="boundary_adjustments",
                open_questions=blocking_questions["t2"],
            )
            comparison_items.append(comparison_item)
            decisions.append(comparison_rejection_decision(comparison_item))
        return proposal_ids, None
    if post_t2_checkpoint is not None:
        for proposal in proposals:
            decisions.append(_pass_order_decision(proposal))
        return proposal_ids, None

    batch_comparisons: list[dict[str, Any]] = []
    hard_failures: list[dict[str, Any]] = []
    for proposal in proposals:
        comparison_item = compare_proposal(
            structure_candidates=current_structure,
            packet=packet,
            proposal=proposal,
            layer="t2",
            collection="boundary_adjustments",
        )
        batch_comparisons.append(comparison_item)
        if (
            not comparison_item.get("can_auto_execute")
            and comparison_item.get("check_id") != "C-COMPARISON-CONFLICT"
        ):
            hard_failures.append(comparison_item)
    if hard_failures:
        comparison_items.extend(batch_comparisons)
        for comparison_item in batch_comparisons:
            decisions.append(comparison_rejection_decision(comparison_item))
        return proposal_ids, None

    patched, operations, reason = apply_t2_boundary_adjustment_batch(
        current_structure,
        proposals,
    )
    if patched is None:
        comparison_items.extend(batch_comparisons)
        before_hash = sha256_json(current_structure)
        for proposal in proposals:
            decisions.append(
                _t2_boundary_batch_decision(
                    proposal,
                    decision="rejected",
                    reason=reason,
                    before_hash=before_hash,
                    after_hash=before_hash,
                )
            )
        return proposal_ids, None

    for operation in operations:
        proposal = next(
            (
                item
                for item in proposals
                if item.get("proposal_id") == operation.get("proposal_id")
            ),
            {},
        )
        operation.update(pass_context)
        comparison_items.append(
            _t2_boundary_batch_comparison(proposal, operation=operation)
        )
        t2_operations.append(operation)
        decisions.append(
            _t2_boundary_batch_decision(
                proposal,
                decision="accepted",
                reason="boundary adjustment batch accepted and materialized",
                before_hash=operation.get("before_hash"),
                after_hash=operation.get("after_hash"),
                operation=operation,
            )
        )
    return proposal_ids, patched


def _t2_boundary_batch_comparison(
    proposal: dict[str, Any],
    *,
    operation: dict[str, Any],
) -> dict[str, Any]:
    proposal_id = proposal.get("proposal_id")
    source_seq_refs = list(operation.get("source_seq_refs") or [])
    return {
        "comparison_id": f"cmp_{str(proposal_id).replace('.', '_')}",
        "proposal_id": proposal_id,
        "round_id": proposal.get("round_id"),
        "layer": "t2",
        "collection": "boundary_adjustments",
        "status": "compatible",
        "check_id": "C-COMPARISON-COMPATIBLE",
        "reason": "boundary proposal is compatible within coordinated T2 batch",
        "risk_level": "low",
        "manual_review_required": False,
        "can_auto_execute": True,
        "affected_refs": {
            "source_seq_refs": source_seq_refs,
            "page_nos": [],
            "render_target_refs": [],
        },
        "ai": {
            "kind": proposal.get("kind"),
            "operation": proposal.get("operation"),
            "unit_id": proposal.get("unit_id"),
            "target_unit_id": proposal.get("target_unit_id"),
            "target_candidate_id": proposal.get("target_candidate_id"),
            "policy": proposal.get("policy") or proposal.get("candidate_policy"),
            "rationale": proposal.get("rationale"),
        },
        "deterministic": {
            "operation": operation.get("operation"),
            "target_unit_id": operation.get("target_unit_id"),
            "batch_id": operation.get("batch_id"),
            "batch_size": operation.get("batch_size"),
            "source_seq_refs": source_seq_refs,
        },
        **_pass_context(proposal),
    }


def _t2_boundary_batch_decision(
    proposal: dict[str, Any],
    *,
    decision: str,
    reason: str,
    before_hash: str | None,
    after_hash: str | None,
    operation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "round_id": proposal.get("round_id"),
        "decision": decision,
        "checks": [
            {
                "check_id": "C-OVERLAY-EXEC",
                "status": "PASS" if decision == "accepted" else "FAIL",
                "reason": reason,
            }
        ],
        "target_path": (
            f"structure_candidates.units[{operation['target_unit_id']}]"
            if operation and operation.get("target_unit_id")
            else None
        ),
        "before_hash": before_hash,
        "after_hash": after_hash,
        "reason": reason,
        **_pass_context(proposal),
    }


def _load_submissions(
    config: AgentConfig,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    assert config.transcript_path is not None
    transcript = load_agent_transcript(config.transcript_path)
    return transcript, transcript_steps(transcript, max_rounds=config.max_rounds)


def _pass_context(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "pass_id": step.get("pass_id"),
        "pass_kind": step.get("pass_kind"),
        "window_id": step.get("window_id"),
        "pass_unit_id": step.get("pass_unit_id") or step.get("unit_id"),
    }


def _pass_scope_decision(
    proposal: dict[str, Any],
    *,
    layer: str,
    collection: str,
    allowed_layers: list[str],
) -> dict[str, Any]:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "round_id": proposal.get("round_id"),
        "decision": "rejected",
        "checks": [
            {
                "check_id": "C-PASS-SCOPE",
                "status": "FAIL",
                "reason": (
                    f"pass {proposal.get('pass_id')} allows layers {allowed_layers}; "
                    f"got {layer}.{collection}"
                ),
            }
        ],
        "target_path": None,
        "before_hash": None,
        "after_hash": None,
        "reason": "proposal layer is outside pass scope",
        **_pass_context(proposal),
    }


def _window_scope_decision(
    proposal: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "round_id": proposal.get("round_id"),
        "decision": "rejected",
        "checks": [
            {
                "check_id": "C-WINDOW-BOUNDARY",
                "status": "FAIL",
                "reason": reason,
            }
        ],
        "target_path": None,
        "before_hash": None,
        "after_hash": None,
        "reason": reason,
        **_pass_context(proposal),
    }


def _pass_order_decision(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "round_id": proposal.get("round_id"),
        "decision": "rejected",
        "checks": [
            {
                "check_id": "C-PASS-ORDER",
                "status": "FAIL",
                "reason": "T2 proposals are not allowed after post-T2 checkpoint is created",
            }
        ],
        "target_path": None,
        "before_hash": None,
        "after_hash": None,
        "reason": "T2 proposal submitted after T2 checkpoint",
        **_pass_context(proposal),
    }


def _requires_post_t2_checkpoint(step: dict[str, Any]) -> bool:
    pass_kind = str(step.get("pass_kind") or "")
    return pass_kind in {"t3_unit_elements", "t4_global_layout"}


def _build_post_t2_checkpoint(
    *,
    request: dict[str, Any],
    document_facts: dict[str, Any],
    structure_candidates: dict[str, Any],
    changed: bool,
    fallback_unit_map: dict[str, Any],
) -> dict[str, Any]:
    regenerated = (
        regenerate_from_structure_candidates(
            request=request,
            document_facts=document_facts,
            structure_candidates=structure_candidates,
        )
        if changed
        else {"unit_map": fallback_unit_map}
    )
    return {
        "artifact_type": "template_agent_post_t2_checkpoint",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "changed": changed,
        "structure_candidates": structure_candidates,
        "unit_map": regenerated["unit_map"],
    }


def _build_post_t2_input(
    *,
    structure_candidates: dict[str, Any],
    changed: bool,
) -> dict[str, Any]:
    ownership: dict[int, str] = {}
    units = []
    for unit in structure_candidates.get("units", []) or []:
        if not isinstance(unit, dict):
            continue
        unit_id = str(unit.get("unit_id") or "")
        source_seq_refs = [
            int(seq)
            for seq in unit.get("source_seq_refs", []) or []
            if str(seq).isdigit()
        ]
        for seq in source_seq_refs:
            ownership[seq] = unit_id
        units.append(
            {
                "unit_id": unit_id,
                "name": unit.get("name"),
                "source_seq_refs": source_seq_refs,
                "confidence": unit.get("confidence"),
                "agent_trace_proposal_ids": [
                    trace.get("proposal_id")
                    for trace in unit.get("agent_traces", []) or []
                    if isinstance(trace, dict) and trace.get("proposal_id")
                ],
            }
        )
    source_seq_values = [
        int(entry.get("source_seq"))
        for entry in (
            structure_candidates.get("source_context", {}).get("body_flow", []) or []
        )
        if isinstance(entry, dict) and str(entry.get("source_seq") or "").isdigit()
    ]
    return {
        "artifact_type": "template_agent_post_t2_input",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "changed": changed,
        "structure_hash": sha256_json(structure_candidates),
        "unit_count": len(units),
        "units": units,
        "source_seq_ownership": {
            str(seq): ownership.get(seq)
            for seq in sorted(source_seq_values)
        },
        "unowned_source_seq_refs": [
            seq for seq in sorted(source_seq_values) if seq not in ownership
        ],
        "open_questions": structure_candidates.get("open_questions", []),
    }
