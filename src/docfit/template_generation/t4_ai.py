"""T4 AI-only layout contract and canonical final publisher.

The model is the sole semantic authority for global layout decisions.  Code in
this module only validates observation identity, normalizes the published
shape, and binds the result to the sealed L1 input.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from docfit.core.io import now_iso

from .final_results import (
    AVAILABLE,
    NOT_AVAILABLE,
    FinalStageResult,
    candidate_ref,
    publish_final_stage_result,
)


def materialize_t4_final_global_spec(
    observation: dict[str, Any],
    *,
    packet: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a validated AI observation into the global-spec contract."""

    profiles = [
        _section_profile(item)
        for item in observation.get("items", []) or []
        if isinstance(item, dict)
    ]
    numbering_rules = observation.get("numbering_rules")
    if not isinstance(numbering_rules, dict):
        numbering_rules = {
            "definitions": (
                deepcopy(numbering_rules) if isinstance(numbering_rules, list) else []
            ),
            "refs": [],
        }
    page_numbering = observation.get("page_numbering")
    if not isinstance(page_numbering, dict):
        page_numbering = {
            "status": "unknown",
            "display": deepcopy(observation.get("page_numbering_display")),
        }
    coverage = observation.get("coverage")
    coverage = coverage if isinstance(coverage, dict) else {}
    unknown_source_seq = list(coverage.get("unknown_source_seq") or [])
    return {
        "artifact_type": "global_spec",
        "artifact_version": "2.0",
        "producer": {
            "name": "docfit-template-generate-t4-ai",
            "version": "0.4.0",
        },
        "created_at": observation.get("created_at") or now_iso(),
        "input_hashes": {
            "l1": packet.get("input_contract_hash"),
            "source_render": packet.get("source_render_hash"),
        },
        "section_profiles": profiles,
        "default_font": deepcopy(observation.get("default_font")),
        "page_numbering": deepcopy(page_numbering),
        "header_footer": deepcopy(observation.get("header_footer") or []),
        "numbering_rules": deepcopy(numbering_rules),
        "flags": (
            [
                {
                    "type": "ai_layout_unknown_source_seq",
                    "status": "unknown",
                    "source_seq_refs": unknown_source_seq,
                }
            ]
            if unknown_source_seq
            else []
        ),
        "ai_observation_ref": {
            "artifact_type": observation.get("artifact_type"),
            "source_render_hash": observation.get("source_render_hash"),
            "input_contract_hash": observation.get("input_contract_hash"),
            "coverage": deepcopy(coverage),
        },
    }


def publish_t4_ai_final(
    observation: dict[str, Any],
    *,
    packet: dict[str, Any],
) -> FinalStageResult:
    """Publish the only production T4 final from one AI layout observation."""

    availability, reason = _observation_availability(observation, packet=packet)
    trusted_observation = observation if availability == AVAILABLE else {
        **observation,
        "items": [],
    }
    global_spec = materialize_t4_final_global_spec(
        trusted_observation,
        packet=packet,
    )
    return publish_final_stage_result(
        global_spec,
        stage_id="T4",
        artifact_type="global_spec",
        artifact_name="04_global_spec.yaml",
        availability=availability,
        reason=reason,
        producer_mode="ai",
        selected_from=[
            candidate_ref(
                observation,
                route_id="ai_raw",
                artifact="04.1_t4_ai_layout_observation.yaml",
            )
        ],
        input_refs={
            "l1": {
                "stage_id": "L1",
                "artifact": "01.5_l1_input_contract.json",
                "sha256": packet.get("input_contract_hash"),
                "availability": AVAILABLE,
            }
        },
    )


def _observation_availability(
    observation: dict[str, Any],
    *,
    packet: dict[str, Any],
) -> tuple[str, str | None]:
    if observation.get("artifact_type") != "ai_layout_observation":
        return NOT_AVAILABLE, "T4 AI observation has the wrong artifact_type"
    expected_render_hash = packet.get("source_render_hash")
    if (
        not expected_render_hash
        or observation.get("source_render_hash") != expected_render_hash
    ):
        return NOT_AVAILABLE, "T4 AI observation is not bound to this source render"
    expected_l1_hash = packet.get("input_contract_hash")
    if not expected_l1_hash or observation.get("input_contract_hash") != expected_l1_hash:
        return NOT_AVAILABLE, "T4 AI observation is not bound to this sealed L1 input"
    if observation.get("_observation_error"):
        return NOT_AVAILABLE, f"T4 AI call failed: {observation['_observation_error']}"
    if observation.get("abstain") or not observation.get("items"):
        return NOT_AVAILABLE, "T4 AI abstained or produced no validated layout decisions"
    if not _items_are_bound(observation.get("items"), packet=packet):
        return NOT_AVAILABLE, "T4 AI layout decisions failed L1 identity or evidence binding"
    return AVAILABLE, None


def _items_are_bound(items: Any, *, packet: dict[str, Any]) -> bool:
    if not isinstance(items, list) or not items:
        return False
    valid_seq = {
        value
        for row in packet.get("page_text_index", []) or []
        if isinstance(row, dict)
        and (value := _as_int(row.get("source_seq"))) is not None
    }
    for item in items:
        if not isinstance(item, dict) or not item.get("source_ref"):
            return False
        boundary = item.get("boundary")
        boundary = boundary if isinstance(boundary, dict) else {}
        start = _as_int(boundary.get("start_source_seq"))
        end = _as_int(boundary.get("end_source_seq"))
        if (
            start is None
            or end is None
            or start > end
            or start not in valid_seq
            or end not in valid_seq
        ):
            return False
        refs = {
            value
            for raw in item.get("source_seq_refs", []) or []
            if (value := _as_int(raw)) is not None
        }
        if refs != set(range(start, end + 1)):
            return False
        evidence = item.get("evidence_refs")
        if not isinstance(evidence, list) or not any(
            isinstance(ref, dict)
            and _as_int(ref.get("page_no")) is not None
            and ref.get("render_target_id")
            for ref in evidence
        ):
            return False
    return True


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return None


def _section_profile(item: dict[str, Any]) -> dict[str, Any]:
    profile = deepcopy(item)
    boundary = profile.get("boundary")
    if not isinstance(boundary, dict):
        source_seq_refs = [
            int(value)
            for value in profile.get("source_seq_refs", []) or []
            if isinstance(value, int)
            or (isinstance(value, str) and value.isdigit())
        ]
        boundary = {
            "status": "detected" if source_seq_refs else "unknown",
            "start_source_seq": min(source_seq_refs) if source_seq_refs else None,
            "end_source_seq": max(source_seq_refs) if source_seq_refs else None,
        }
    else:
        boundary = deepcopy(boundary)
        boundary.setdefault("status", "detected")
    profile["boundary"] = boundary

    header_footer = profile.get("header_footer")
    if isinstance(header_footer, list):
        profile["header_footer"] = {
            "references": deepcopy(header_footer),
            "effective_references": deepcopy(header_footer),
            "parts": [],
        }
    elif not isinstance(header_footer, dict):
        profile["header_footer"] = {
            "references": [],
            "effective_references": [],
            "parts": [],
        }

    page_numbering = profile.get("page_numbering")
    if not isinstance(page_numbering, dict) or "display" not in page_numbering:
        declared = deepcopy(page_numbering) if isinstance(page_numbering, dict) else {}
        profile["page_numbering"] = {
            "declared": {
                "status": "detected" if declared else "unknown",
                **declared,
            },
            "fields": [],
            "display": {
                "status": "unknown",
                "has_page_field": None,
                "checked_scopes": {},
                "evidence_refs": list(profile.get("evidence_refs") or []),
            },
            "flags": [],
        }
    profile.setdefault("flags", [])
    profile["origin"] = "ai_layout_observation"
    return profile
