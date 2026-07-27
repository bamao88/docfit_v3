from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file, sha256_json

from .final_results import FinalStageResult, require_final_stage_result
from .stage_inputs import l1_artifact_hash
from .docx_effects import inspect_docx_layout_effects


def build_template_generation_manifest(
    *,
    request: dict[str, Any],
    l1_input_contract: dict[str, Any],
    template_final: FinalStageResult,
    plan: dict[str, Any],
    fillable_template_docx: Path,
    execution: dict[str, Any],
) -> dict[str, Any]:
    template_result = require_final_stage_result(
        template_final,
        stage_id="T5",
        artifact_type="template_spec",
        artifact_name="05_template_spec.yaml",
    )
    template_spec = template_result.payload
    manifest = {
        "artifact_type": "build_manifest",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "strategy": request.get("strategy"),
        "input_hashes": {
            "source_template_docx": request.get("source_template_hash"),
            "l1": l1_artifact_hash(l1_input_contract),
            "template_spec": template_result.sha256,
            "template_generation_plan": sha256_json(plan),
        },
        "input_refs": {"t5_final": template_result.input_ref()},
        "upstream_availability": {
            "status": template_result.availability,
            "reason": template_result.reason,
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
        "layout_hint_consumption": (
            template_spec.get("global", {}) or {}
        ).get("layout_hint_consumption", {}),
        "synthesized_texts": execution.get("synthesized_texts", []),
        "actions_executed": execution.get("actions_executed", []),
        "actions_requiring_review": execution.get("actions_requiring_review", []),
        "identity_resolution": execution.get("identity_resolution", {}),
        "observed_layout_effects": inspect_docx_layout_effects(
            fillable_template_docx
        ),
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
