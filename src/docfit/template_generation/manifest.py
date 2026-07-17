from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file, sha256_json

from .stage_inputs import l1_artifact_hash


def build_template_generation_manifest(
    *,
    request: dict[str, Any],
    l1_input_contract: dict[str, Any],
    unit_map: dict[str, Any],
    element_spec: dict[str, Any],
    global_spec: dict[str, Any],
    template_spec: dict[str, Any],
    plan: dict[str, Any],
    fillable_template_docx: Path,
    execution: dict[str, Any],
) -> dict[str, Any]:
    manifest = {
        "artifact_type": "build_manifest",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "strategy": request.get("strategy"),
        "input_hashes": {
            "source_template_docx": request.get("source_template_hash"),
            "l1": l1_artifact_hash(l1_input_contract),
            "unit_map": sha256_json(unit_map),
            "element_spec": sha256_json(element_spec),
            "global_spec": sha256_json(global_spec),
            "template_spec": sha256_json(template_spec),
            "template_generation_plan": sha256_json(plan),
        },
        "output": {
            "fillable_template_docx": str(fillable_template_docx),
            "fillable_template_docx_hash": sha256_file(fillable_template_docx),
        },
        "slots": execution.get("slots", []),
        "generated_fields": execution.get("generated_fields", []),
        "page_breaks": execution.get("page_breaks", []),
        "section_breaks": execution.get("section_breaks", []),
        "keep_together": execution.get("keep_together", []),
        "page_policy_results": _merge_page_policy_results(
            plan.get("page_policy_results", []),
            execution.get("actions_executed", []),
            execution.get("actions_requiring_review", []),
        ),
        "layout_hint_consumption": global_spec.get("layout_hint_consumption", {}),
        "synthesized_texts": execution.get("synthesized_texts", []),
        "actions_executed": execution.get("actions_executed", []),
        "actions_requiring_review": execution.get("actions_requiring_review", []),
        "identity_resolution": execution.get("identity_resolution", {}),
    }
    return manifest


def _merge_page_policy_results(
    planned_results: list[dict[str, Any]],
    executed_actions: list[dict[str, Any]],
    review_actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    executed_by_id = {
        str(action.get("action_id")): action
        for action in executed_actions
        if action.get("action_id")
    }
    review_by_id = {
        str(action.get("action_id")): action
        for action in review_actions
        if action.get("action_id")
    }
    merged: list[dict[str, Any]] = []
    for result in planned_results or []:
        action_ids = [str(action_id) for action_id in result.get("planned_action_ids", [])]
        executed = [executed_by_id[action_id] for action_id in action_ids if action_id in executed_by_id]
        review = [review_by_id[action_id] for action_id in action_ids if action_id in review_by_id]
        if review:
            status = "manual_review"
        elif action_ids and len(executed) == len(action_ids):
            status = "executed"
        else:
            status = result.get("status")
        merged.append(
            {
                **result,
                "status": status,
                "executed_action_ids": [action.get("action_id") for action in executed],
                "review_action_ids": [action.get("action_id") for action in review],
                "output_refs": [
                    action.get("output_ref")
                    for action in executed
                    if action.get("output_ref")
                ],
            }
        )
    return merged
