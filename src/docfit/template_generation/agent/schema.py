from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable


T2_COLLECTIONS = (
    "unit_candidates",
    "block_candidates",
    "boundary_adjustments",
    "page_policy_candidates",
)
T4_COLLECTIONS = (
    "section_profile_hints",
    "page_numbering_hints",
)
LAYER_COLLECTIONS = {
    "t2": T2_COLLECTIONS,
    "t4": T4_COLLECTIONS,
}
PROPOSAL_KIND_BY_COLLECTION = {
    "unit_candidates": "unit_candidate",
    "block_candidates": "block_candidate",
    "boundary_adjustments": "boundary_adjustment",
    "page_policy_candidates": "page_policy_candidate",
    "section_profile_hints": "section_profile_hint",
    "page_numbering_hints": "page_numbering_hint",
}


def empty_layered_submission(
    *,
    source_render_hash: str,
    round_id: str = "round_001",
    model: str = "replay",
) -> dict[str, Any]:
    return {
        "schema_version": "template-agent-layered-submission-1.0",
        "prompt_version": "template-agent-prompt-1.0",
        "source_render_hash": source_render_hash,
        "round_id": round_id,
        "model": model,
        "layers": {
            "t2": {
                "unit_candidates": [],
                "block_candidates": [],
                "boundary_adjustments": [],
                "page_policy_candidates": [],
                "open_questions": [],
            },
            "t4": {
                "section_profile_hints": [],
                "page_numbering_hints": [],
                "open_questions": [],
            },
        },
        "abstain": False,
    }


def validate_layered_submission(
    submission: dict[str, Any],
    *,
    expected_source_render_hash: str | None = None,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    normalized = deepcopy(submission) if isinstance(submission, dict) else {}
    if not isinstance(submission, dict):
        return {"valid": False, "submission": {}, "errors": [_error("$", "C-SCHEMA", "submission must be an object")]}
    if not normalized.get("source_render_hash"):
        errors.append(_error("$.source_render_hash", "C-SCHEMA", "source_render_hash is required"))
    elif (
        expected_source_render_hash is not None
        and normalized.get("source_render_hash") != expected_source_render_hash
    ):
        errors.append(_error("$.source_render_hash", "C-SCHEMA", "source_render_hash does not match packet"))
    if not normalized.get("round_id"):
        errors.append(_error("$.round_id", "C-SCHEMA", "round_id is required"))
    normalized.setdefault("schema_version", "template-agent-layered-submission-1.0")
    normalized.setdefault("prompt_version", "template-agent-prompt-1.0")
    normalized.setdefault("model", "unknown")
    layers = normalized.setdefault("layers", {})
    if not isinstance(layers, dict):
        errors.append(_error("$.layers", "C-SCHEMA", "layers must be an object"))
        layers = {}
        normalized["layers"] = layers
    for layer in sorted(set(layers) - set(LAYER_COLLECTIONS)):
        errors.append(
            _error(
                f"$.layers.{layer}",
                "C-SCHEMA",
                f"unsupported proposal layer: {layer}",
            )
        )

    for layer, collections in LAYER_COLLECTIONS.items():
        layer_value = layers.setdefault(layer, {})
        if not isinstance(layer_value, dict):
            errors.append(_error(f"$.layers.{layer}", "C-SCHEMA", "layer must be an object"))
            layer_value = {}
            layers[layer] = layer_value
        layer_value.setdefault("open_questions", [])
        if not isinstance(layer_value["open_questions"], list):
            errors.append(_error(f"$.layers.{layer}.open_questions", "C-SCHEMA", "open_questions must be a list"))
            layer_value["open_questions"] = []
        allowed_keys = {*collections, "open_questions"}
        for key in sorted(set(layer_value) - allowed_keys):
            errors.append(
                _error(
                    f"$.layers.{layer}.{key}",
                    "C-SCHEMA",
                    f"unsupported {layer} proposal collection: {key}",
                )
            )
        for collection in collections:
            value = layer_value.setdefault(collection, [])
            if not isinstance(value, list):
                errors.append(_error(f"$.layers.{layer}.{collection}", "C-SCHEMA", "proposal collection must be a list"))
                layer_value[collection] = []
                continue
            expected_kind = PROPOSAL_KIND_BY_COLLECTION[collection]
            for index, proposal in enumerate(value):
                path = f"$.layers.{layer}.{collection}[{index}]"
                if not isinstance(proposal, dict):
                    errors.append(_error(path, "C-SCHEMA", "proposal must be an object"))
                    continue
                if not proposal.get("proposal_id"):
                    errors.append(_error(f"{path}.proposal_id", "C-SCHEMA", "proposal_id is required"))
                kind = str(proposal.get("kind") or "")
                if not kind:
                    errors.append(_error(f"{path}.kind", "C-SCHEMA", "kind is required"))
                elif kind != expected_kind:
                    errors.append(_error(f"{path}.kind", "C-SCHEMA", f"kind must be {expected_kind}"))
                if not _has_evidence_binding(proposal):
                    errors.append(
                        _error(
                            path,
                            "C-EVIDENCE-EXIST",
                            "proposal requires source_seq_refs, render_target_refs, or page_no",
                        )
                    )
    return {"valid": not errors, "submission": normalized, "errors": errors}


def iter_layer_proposals(
    submission: dict[str, Any],
) -> Iterable[tuple[str, str, dict[str, Any]]]:
    layers = submission.get("layers") or {}
    for layer, collections in LAYER_COLLECTIONS.items():
        layer_value = layers.get(layer) or {}
        for collection in collections:
            for proposal in layer_value.get(collection, []) or []:
                if isinstance(proposal, dict):
                    yield layer, collection, proposal


def schema_error_decisions(
    validation_result: dict[str, Any],
    *,
    round_id: str | None = None,
) -> list[dict[str, Any]]:
    decisions = []
    for index, error in enumerate(validation_result.get("errors", []), start=1):
        decisions.append(
            {
                "proposal_id": f"schema_error_{index:03d}",
                "round_id": round_id,
                "decision": "rejected",
                "checks": [
                    {
                        "check_id": error.get("check_id", "C-SCHEMA"),
                        "status": "FAIL",
                        "path": error.get("path"),
                        "reason": error.get("message"),
                    }
                ],
                "target_path": error.get("path"),
                "before_hash": None,
                "after_hash": None,
                "reason": error.get("message"),
            }
        )
    return decisions


def _has_evidence_binding(proposal: dict[str, Any]) -> bool:
    if proposal.get("source_seq_refs"):
        return True
    if proposal.get("render_target_refs"):
        return True
    if proposal.get("page_no") is not None:
        return True
    if proposal.get("page_nos"):
        return True
    if proposal.get("source_seq") is not None:
        return True
    return False


def _error(path: str, check_id: str, message: str) -> dict[str, Any]:
    return {"path": path, "check_id": check_id, "message": message}
