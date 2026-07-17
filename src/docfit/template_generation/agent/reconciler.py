from __future__ import annotations

from typing import Any

from docfit.core.io import sha256_json

from .overlay import (
    apply_t2_proposal,
    apply_t3_proposal,
    _proposal_source_seq_refs,
)
from .packet import packet_page_set, packet_render_target_set, packet_source_seq_set


def process_proposal(
    *,
    structure_candidates: dict[str, Any],
    packet: dict[str, Any],
    proposal: dict[str, Any],
    layer: str,
    collection: str,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    before_hash = sha256_json(structure_candidates)
    source_error = _source_binding_error(packet, proposal)
    if source_error is not None:
        return (
            structure_candidates,
            _decision(
                proposal,
                decision="rejected",
                check_id="C-EVIDENCE-EXIST",
                reason=source_error,
                before_hash=before_hash,
                after_hash=before_hash,
            ),
            None,
        )

    if layer == "t2":
        patched, operation, reason = apply_t2_proposal(
            structure_candidates,
            proposal,
            collection=collection,
        )
        if patched is None or operation is None:
            return (
                structure_candidates,
                _decision(
                    proposal,
                    decision="rejected",
                    check_id=_check_for_t2_reason(reason),
                    reason=reason,
                    before_hash=before_hash,
                    after_hash=before_hash,
                ),
                None,
            )
        return (
            patched,
            _decision(
                proposal,
                decision="accepted",
                check_id="C-OVERLAY-EXEC",
                reason="proposal accepted and materialized",
                before_hash=before_hash,
                after_hash=sha256_json(patched),
                target_path=_target_path(operation),
            ),
            operation,
        )

    if layer == "t3":
        patched, operation, reason = apply_t3_proposal(structure_candidates, proposal)
        if patched is None or operation is None:
            return (
                structure_candidates,
                _decision(
                    proposal,
                    decision="rejected",
                    check_id=_check_for_t3_reason(reason),
                    reason=reason,
                    before_hash=before_hash,
                    after_hash=before_hash,
                ),
                None,
            )
        return (
            patched,
            _decision(
                proposal,
                decision="accepted",
                check_id="C-TARGET-BIND",
                reason="candidate policy patched",
                before_hash=before_hash,
                after_hash=sha256_json(patched),
                target_path=_target_path(operation),
            ),
            operation,
        )

    if layer == "t4":
        if packet.get("render_status") != "real_render":
            return (
                structure_candidates,
                _decision(
                    proposal,
                    decision="rejected",
                    check_id="C-RENDER-REQUIRED",
                    reason="T4 layout hints require a real_render packet",
                    before_hash=before_hash,
                    after_hash=before_hash,
                    target_path=f"agent_t4_hints.{collection}",
                ),
                None,
            )
        hint = {
            **proposal,
            "collection": collection,
            "accepted": True,
        }
        return (
            structure_candidates,
            _decision(
                proposal,
                decision="accepted",
                check_id="C-EVIDENCE-EXIST",
                reason="hint accepted as advisory artifact",
                before_hash=before_hash,
                after_hash=before_hash,
                target_path=f"agent_t4_hints.{collection}",
            ),
            hint,
        )

    return (
        structure_candidates,
        _decision(
            proposal,
            decision="rejected",
            check_id="C-SCHEMA",
            reason=f"unsupported layer: {layer}",
            before_hash=before_hash,
            after_hash=before_hash,
        ),
        None,
    )


def _source_binding_error(packet: dict[str, Any], proposal: dict[str, Any]) -> str | None:
    valid_source_seq = packet_source_seq_set(packet)
    valid_render_targets = packet_render_target_set(packet)
    valid_pages = packet_page_set(packet)

    source_seq_refs = _proposal_source_seq_refs(proposal)
    invalid_seq = [
        source_seq for source_seq in source_seq_refs if source_seq not in valid_source_seq
    ]
    if invalid_seq:
        return f"source_seq_refs not present in render packet: {invalid_seq}"

    render_target_refs = proposal.get("render_target_refs") or []
    if isinstance(render_target_refs, list) and render_target_refs:
        invalid_targets = [
            str(target)
            for target in render_target_refs
            if str(target) not in valid_render_targets
        ]
        if invalid_targets:
            return f"render_target_refs not present in render packet: {invalid_targets}"

    page_values: list[int] = []
    if proposal.get("page_no") is not None:
        page_values.append(int(proposal.get("page_no")))
    if isinstance(proposal.get("page_nos"), list):
        page_values.extend(int(page_no) for page_no in proposal["page_nos"])
    invalid_pages = [page_no for page_no in page_values if page_no not in valid_pages]
    if invalid_pages:
        return f"page_nos not present in render packet: {invalid_pages}"
    return None


def _decision(
    proposal: dict[str, Any],
    *,
    decision: str,
    check_id: str,
    reason: str,
    before_hash: str | None,
    after_hash: str | None,
    target_path: str | None = None,
) -> dict[str, Any]:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "round_id": proposal.get("round_id"),
        "decision": decision,
        "checks": [
            {
                "check_id": check_id,
                "status": "PASS" if decision == "accepted" else "FAIL",
                "reason": reason,
            }
        ],
        "target_path": target_path,
        "before_hash": before_hash,
        "after_hash": after_hash,
        "reason": reason,
    }


def _check_for_t2_reason(reason: str) -> str:
    if "operation" in reason:
        return "C-EXECUTABLE-ENUM"
    if "gap" in reason or "overlap" in reason or "body_main" in reason:
        return "C-OVERLAY-EXEC"
    return "C-TARGET-BIND"


def _check_for_t3_reason(reason: str) -> str:
    if "policy" in reason:
        return "C-EXECUTABLE-ENUM"
    return "C-TARGET-BIND"


def _target_path(operation: dict[str, Any]) -> str | None:
    if operation.get("target_candidate_id"):
        return f"structure_candidates.units[].elements[{operation['target_candidate_id']}].candidate_policy"
    if operation.get("operation") == "set_page_policy" and operation.get("target_unit_id"):
        return f"structure_candidates.units[{operation['target_unit_id']}].page"
    if operation.get("target_unit_id"):
        return f"structure_candidates.units[{operation['target_unit_id']}]"
    return None
