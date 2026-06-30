from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_json

from .attribution import (
    build_agent_attribution,
    build_agent_decisions,
    build_agent_pass_plan,
    build_agent_t2_overlay,
    build_agent_t3_overlay,
    build_agent_t4_hints,
)
from .comparison import (
    blocking_open_questions_by_layer,
    build_submission_comparison,
    compare_blocked_by_open_questions,
    compare_proposal,
    comparison_rejection_decision,
)
from .config import AgentConfig, AgentConfigError, LIVE_TRANSPORTS, require_valid_agent_config
from .manual_review import build_agent_manual_review_items
from .packet import build_template_agent_render_packet, load_render_packet
from .reconciler import process_proposal
from .regenerate import regenerate_from_structure_candidates
from .replay import load_agent_transcript, pass_plan_from_steps, transcript_steps
from .schema import iter_layer_proposals, schema_error_decisions, validate_layered_submission
from .tools import agent_tool_schemas, execute_agent_tool_call
from .transport import KimiOpenAICompatibleTransport, MinimaxOpenAICompatibleTransport
from .windows import build_agent_unit_windows, t3_window_error, window_for_step


@dataclass
class AgentRunResult:
    enabled: bool
    changed: bool
    structure_candidates: dict[str, Any]
    unit_map: dict[str, Any]
    generation_model: dict[str, Any]
    element_spec: dict[str, Any]
    render_packet: dict[str, Any] | None = None
    pass_plan: dict[str, Any] | None = None
    post_t2_checkpoint: dict[str, Any] | None = None
    post_t2_input: dict[str, Any] | None = None
    unit_windows: dict[str, Any] | None = None
    transcript: dict[str, Any] | None = None
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
    packet = (
        load_render_packet(agent_config.render_packet_path)
        if agent_config.render_packet_path is not None
        else build_template_agent_render_packet(
            document_facts=document_facts,
            structure_candidates=structure_candidates,
            source_template_docx=source_template_docx,
            render_artifacts_dir=render_artifacts_dir,
        )
    )
    if (
        agent_config.transport in LIVE_TRANSPORTS
        and packet.get("render_status") != "real_render"
        and not agent_config.allow_live_without_real_render
    ):
        raise AgentConfigError(
            "live agent transport requires a real_render packet; "
            f"got render_status={packet.get('render_status') or 'missing'}"
        )
    transcript, steps = _load_submissions(
        agent_config,
        packet=packet,
        request=request,
        structure_candidates=structure_candidates,
    )
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
        for layer, collection, proposal in iter_layer_proposals(normalized):
            proposal["round_id"] = proposal.get("round_id") or normalized.get("round_id")
            proposal.update(pass_context)
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

    changed = bool(t2_operations or t3_operations)
    regenerated = (
        regenerate_from_structure_candidates(
            request=request,
            document_facts=document_facts,
            structure_candidates=current_structure,
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
    )
    return AgentRunResult(
        enabled=True,
        changed=changed,
        structure_candidates=current_structure,
        unit_map=regenerated["unit_map"],
        generation_model=regenerated["generation_model"],
        element_spec=regenerated["element_spec"],
        render_packet=packet,
        pass_plan=pass_plan,
        post_t2_checkpoint=post_t2_checkpoint,
        post_t2_input=post_t2_input,
        unit_windows=unit_windows,
        transcript=transcript,
        submission_comparison=submission_comparison,
        decisions=decisions_artifact,
        manual_review_items=manual_review_items,
        t2_overlay=t2_overlay,
        t3_overlay=t3_overlay,
        t4_hints=t4_hints_artifact,
        attribution=attribution,
    )


def _load_submissions(
    config: AgentConfig,
    *,
    packet: dict[str, Any],
    request: dict[str, Any],
    structure_candidates: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if config.transport == "replay":
        assert config.transcript_path is not None
        transcript = load_agent_transcript(config.transcript_path)
        return transcript, transcript_steps(transcript, max_rounds=config.max_rounds)

    if config.transport in {"kimi", "minimax"}:
        if config.transport == "kimi":
            transport = KimiOpenAICompatibleTransport(
                model=config.model or "kimi-for-coding",
            )
        else:
            transport = MinimaxOpenAICompatibleTransport(
                model=config.model or "minimax-text-01",
            )
        rounds: list[dict[str, Any]] = []
        pass_specs = _live_pass_specs(
            config=config,
            packet=packet,
            structure_candidates=structure_candidates,
        )
        for round_index, pass_spec in enumerate(pass_specs, start=1):
            round_id = f"round_{round_index:03d}"
            submission = transport.complete_round(
                messages=_live_messages(
                    packet,
                    request,
                    round_index=round_index,
                    pass_spec=pass_spec,
                ),
                tools=agent_tool_schemas(),
                response_format=None,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                tool_executor=lambda name, arguments, round_id=round_id: execute_agent_tool_call(
                    name,
                    arguments,
                    packet=packet,
                    round_id=round_id,
                    model=transport.model,
                ),
            )
            if submission is None:
                break
            tool_trace = submission.pop("_tool_trace", [])
            rounds.append(
                {
                    **pass_spec,
                    "round_id": submission.get("round_id") or round_id,
                    "provider": config.transport,
                    "tool_trace": tool_trace,
                    "submission": submission,
                }
            )
            if submission.get("abstain"):
                break
        transcript = _transcript(rounds, provider=config.transport)
        return transcript, transcript_steps(transcript, max_rounds=config.max_rounds)

    raise ValueError(f"unsupported live agent transport: {config.transport}")


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


def _live_messages(
    packet: dict[str, Any],
    request: dict[str, Any],
    *,
    round_index: int,
    pass_spec: dict[str, Any],
) -> list[dict[str, Any]]:
    payload = {
        "round_index": round_index,
        "pass": pass_spec,
        "prompt_contract": _prompt_contract(pass_spec),
        "request": request,
        "packet": _prompt_packet_view(packet, pass_spec=pass_spec),
    }
    return [
        {
            "role": "system",
            "content": _system_prompt(),
        },
        {
            "role": "user",
            "content": _user_prompt(payload),
        },
    ]


def _system_prompt() -> str:
    return "\n".join(
        [
            "You are an advisory-only DocFit template agent.",
            "Your job is to propose precise, evidence-bound improvements to a school thesis template parse.",
            "You never write final artifacts and never decide PASS/FAIL; deterministic DocFit code will accept or reject every proposal.",
            "Use the provided tools to inspect packet evidence, then call exactly one submit_t2, submit_t3, submit_t4, or abstain tool.",
            "Do not read or infer signed school standards; use only the packet, pass context, tool results, and optional canonical unit id reference.",
            "Prefer abstain over speculative proposals when evidence is weak, ambiguous, or outside the active pass/window.",
        ]
    )


def _user_prompt(payload: dict[str, Any]) -> str:
    return (
        "\n".join(
            [
                "Run the requested pass with the quality contract below.",
                "Workflow:",
                "1. Inspect relevant evidence with query_text and, for layout/page reasoning, view_pages.",
                "2. Propose only changes that are directly supported by visible packet evidence.",
                "3. Submit only proposals from pass.allowed_layers.",
                "4. Bind every proposal to source_seq_refs, page_no/page_nos, or render_target_refs from packet evidence.",
                "5. Include a short rationale and evidence list on every proposal so humans can audit the decision.",
                "6. If no high-confidence proposal exists, call abstain with open_questions instead of sending weak guesses.",
                "Quality pitfalls to avoid: duplicate existing units, broad source ranges, cross-window T3 edits, unsupported policy values, unbound page hints, and claims based on school standards.",
                "Context JSON follows.",
            ]
        )
        + "\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )


def _prompt_packet_view(
    packet: dict[str, Any],
    *,
    pass_spec: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": packet.get("artifact_type"),
        "artifact_version": packet.get("artifact_version"),
        "source_template_docx": packet.get("source_template_docx"),
        "render_status": packet.get("render_status"),
        "source_render_hash": packet.get("source_render_hash"),
        "status_authority": packet.get("status_authority"),
        "advisory_only": packet.get("advisory_only"),
        "allowed_ai_tasks": packet.get("allowed_ai_tasks"),
        "forbidden_ai_tasks": packet.get("forbidden_ai_tasks"),
        "tool_access": {
            "query_text": (
                "Use query_text for exact visible text by source_seq_refs, "
                "page_nos, or text_query. The tool sees the full packet."
            ),
            "view_pages": (
                "Use view_pages for clean or annotated render references. "
                "The tool sees the full packet."
            ),
        },
        "render_artifacts": _prompt_render_artifact_summary(
            packet.get("render_artifacts") or {}
        ),
        "page_index_summary": _prompt_page_index_summary(packet),
        "text_outline": _prompt_text_outline(packet, pass_spec=pass_spec),
        "optional_reference": packet.get("optional_reference"),
        "round0_snapshot_id": packet.get("round0_snapshot_id"),
    }


def _prompt_render_artifact_summary(render_artifacts: dict[str, Any]) -> dict[str, Any]:
    return {
        "render_status": render_artifacts.get("render_status"),
        "render_engine": render_artifacts.get("render_engine"),
        "render_version": render_artifacts.get("render_version"),
        "page_count": render_artifacts.get("page_count"),
        "text_binding_summary": render_artifacts.get("text_binding_summary"),
        "render_error": render_artifacts.get("render_error"),
        "clean_page_images": _prompt_page_artifacts(
            render_artifacts.get("clean_page_images")
        ),
        "annotated_page_images": _prompt_page_artifacts(
            render_artifacts.get("annotated_page_images")
        ),
    }


def _prompt_page_artifacts(value: Any) -> list[dict[str, Any]]:
    result = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "page_no": item.get("page_no"),
                "path": item.get("path"),
                "sha256": item.get("sha256"),
                "width_px": item.get("width_px"),
                "height_px": item.get("height_px"),
                "image_type": item.get("image_type"),
            }
        )
    return result


def _prompt_page_index_summary(packet: dict[str, Any]) -> list[dict[str, Any]]:
    full_pass = (packet.get("input_windows") or {}).get("full_pass") or {}
    summary = full_pass.get("page_index_summary")
    if isinstance(summary, list):
        return [item for item in summary if isinstance(item, dict)]

    counts: dict[int, int] = {}
    for item in packet.get("page_text_index", []) or []:
        if not isinstance(item, dict):
            continue
        page_no = _int_or_none(item.get("page_no")) or 1
        counts[page_no] = counts.get(page_no, 0) + 1
    return [
        {"page_no": page_no, "text_items": counts[page_no]}
        for page_no in sorted(counts)
    ]


def _prompt_text_outline(
    packet: dict[str, Any],
    *,
    pass_spec: dict[str, Any],
) -> dict[str, Any]:
    pass_kind = str(pass_spec.get("pass_kind") or "")
    wanted_refs = _prompt_source_ref_filter(pass_spec)
    max_items = 180 if wanted_refs else 520
    max_text_chars = 140 if pass_kind == "t2_unit_scan" else 180
    items: list[dict[str, Any]] = []
    total_matching = 0
    for item in packet.get("page_text_index", []) or []:
        if not isinstance(item, dict):
            continue
        source_seq = _int_or_none(item.get("source_seq"))
        if wanted_refs and source_seq not in wanted_refs:
            continue
        total_matching += 1
        if len(items) >= max_items:
            continue
        items.append(
            {
                "source_seq": source_seq,
                "page_no": item.get("page_no"),
                "render_target_id": item.get("render_target_id"),
                "text": _truncate_prompt_text(item.get("text"), max_text_chars),
            }
        )
    return {
        "scope": "active_unit_window" if wanted_refs else "full_document_outline",
        "total_matching_items": total_matching,
        "items": items,
        "truncated": total_matching > len(items),
        "note": (
            "Outline text is truncated for prompt size. Use query_text for exact "
            "full packet evidence before submitting proposals."
        ),
    }


def _prompt_source_ref_filter(pass_spec: dict[str, Any]) -> set[int]:
    unit_window = pass_spec.get("unit_window")
    if not isinstance(unit_window, dict):
        return set()
    return {
        parsed
        for value in unit_window.get("source_seq_refs", []) or []
        if (parsed := _int_or_none(value)) is not None
    }


def _truncate_prompt_text(value: Any, limit: int) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _prompt_contract(pass_spec: dict[str, Any]) -> dict[str, Any]:
    pass_kind = str(pass_spec.get("pass_kind") or "")
    return {
        "contract_version": "template-agent-prompt-quality-1.1",
        "pass_goal": _pass_goal(pass_kind),
        "allowed_operations": {
            "t2": ["add_unit", "relabel_unit", "adjust_unit_range", "replace_unit_elements"],
            "t3": ["set_candidate_policy"],
            "t4": ["advisory_hints_only"],
        },
        "policy_values": ["fixed", "fill", "manual_only", "generated", "remove_instruction"],
        "proposal_quality_bar": [
            "proposal_id is stable and unique within the pass",
            "kind matches the submit tool collection",
            "source_seq_refs are minimal and directly visible in packet evidence",
            "rationale explains why the current deterministic parse is likely wrong or incomplete",
            "evidence lists source_seq/page/render target references used for the proposal",
            "do not use standards/targets or expected school-specific gold answers",
        ],
        "pass_specific_rules": _pass_specific_rules(pass_kind),
        "abstain_when": [
            "the evidence is ambiguous",
            "the required source_seq or target_candidate_id is outside the active window",
            "the desired operation is not represented by an allowed submit tool",
            "the proposal would require writing final artifacts directly",
        ],
    }


def _pass_goal(pass_kind: str) -> str:
    return {
        "t2_unit_scan": (
            "Find missing, mislabeled, or incorrectly bounded template units using "
            "visible source text and source_seq evidence."
        ),
        "t3_unit_elements": (
            "Within the active unit window, improve element candidate_policy choices "
            "for existing candidate targets."
        ),
        "t4_global_layout": (
            "Submit advisory-only layout hints based on real rendered pages, page "
            "numbers, and visible layout evidence."
        ),
    }.get(pass_kind, "Submit advisory proposals for the active pass only.")


def _pass_specific_rules(pass_kind: str) -> list[str]:
    if pass_kind == "t2_unit_scan":
        return [
            "Use submit_t2 only.",
            "Prefer canonical unit_id values from optional_reference when the visible text supports them.",
            "Use add_unit for source_seq ranges that are unowned or wrongly absorbed by another unit.",
            "Use adjust_unit_range only when the new range is minimal and does not cross multiple unrelated units.",
            "Do not duplicate an existing unit_id; relabel only when evidence names the unit more precisely.",
        ]
    if pass_kind == "t3_unit_elements":
        return [
            "Use submit_t3 only.",
            "Stay inside pass.unit_window.source_seq_refs and pass.unit_window.candidate_targets.",
            "Prefer target_candidate_id from the active unit window when available.",
            "Use fixed for literal template text, fill for user-filled placeholders, manual_only for content that needs human authoring, generated only for deterministic generated content.",
            "Never submit T2 boundary changes from a T3 pass.",
        ]
    if pass_kind == "t4_global_layout":
        return [
            "Use submit_t4 only.",
            "Submit hints only; do not request direct global_spec/template_spec patches.",
            "Use page_no/page_nos or render_target_refs from real_render evidence.",
            "Abstain if render_status is not real_render or page evidence is missing.",
        ]
    return ["Use only the submit tool matching pass.allowed_layers."]


def _live_pass_specs(
    *,
    config: AgentConfig,
    packet: dict[str, Any],
    structure_candidates: dict[str, Any],
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = [
        {
            "pass_id": "t2_unit_scan",
            "pass_kind": "t2_unit_scan",
            "window_id": "full_document",
            "unit_id": None,
            "allowed_layers": ["t2"],
            "attempt_index": 1,
            "checkpoint_summary": _structure_summary(structure_candidates),
        }
    ]
    if config.max_rounds <= 1:
        return specs[: config.max_rounds]

    windows = build_agent_unit_windows(
        structure_candidates=structure_candidates,
        packet=packet,
    )
    reserve_t4 = config.max_rounds > 2
    t3_capacity = max(0, config.max_rounds - len(specs) - (1 if reserve_t4 else 0))
    for window in windows.get("windows", [])[:t3_capacity]:
        unit_id = str(window.get("unit_id") or "")
        specs.append(
            {
                "pass_id": f"t3_unit_elements_{unit_id}",
                "pass_kind": "t3_unit_elements",
                "window_id": window.get("window_id"),
                "unit_id": unit_id,
                "allowed_layers": ["t3"],
                "attempt_index": 1,
                "unit_window": window,
                "checkpoint_summary": _structure_summary(structure_candidates),
            }
        )
    if len(specs) < config.max_rounds:
        specs.append(
            {
                "pass_id": "t4_global_layout",
                "pass_kind": "t4_global_layout",
                "window_id": "full_document",
                "unit_id": None,
                "allowed_layers": ["t4"],
                "attempt_index": 1,
                "checkpoint_summary": _structure_summary(structure_candidates),
            }
        )
    return specs[: config.max_rounds]


def _structure_summary(structure_candidates: dict[str, Any]) -> dict[str, Any]:
    units = []
    for unit in structure_candidates.get("units", []) or []:
        if not isinstance(unit, dict):
            continue
        units.append(
            {
                "unit_id": unit.get("unit_id"),
                "name": unit.get("name"),
                "source_seq_refs": unit.get("source_seq_refs", []),
                "element_count": len(unit.get("elements", []) or []),
            }
        )
    return {
        "unit_count": len(units),
        "units": units,
    }


def _transcript(rounds: list[dict[str, Any]], *, provider: str) -> dict[str, Any]:
    return {
        "artifact_type": "template_agent_transcript",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "provider": provider,
        "rounds": rounds,
        "stop_reason": "max_rounds_or_abstain",
    }
