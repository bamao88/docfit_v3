from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_json, write_json
from docfit.core.models import Finding, StageResult, make_finding
from docfit.core.status import Status, merge_statuses


def build_placement_plan(
    template_artifact: dict[str, Any],
    content_artifact: dict[str, Any],
    *,
    simulate_drop: str | None = None,
) -> StageResult:
    slots = template_artifact.get("data", {}).get("slots", [])
    slot_by_id = {slot["slot_id"]: slot for slot in slots}
    default_slot = "slot_body_start"
    actions: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for item in content_artifact.get("data", {}).get("visible_content_ledger", []):
        content_id = item["content_id"]
        if simulate_drop == content_id:
            continue
        if default_slot not in slot_by_id:
            unresolved.append(
                {
                    "content_id": content_id,
                    "disposition": "unsupported",
                    "reason": "target slot slot_body_start does not exist",
                    "blocking": True,
                }
            )
            continue
        render_kind = item.get("kind", "paragraph")
        actions.append(
            {
                "action_id": f"a_{len(actions) + 1:03d}",
                "content_ids": [content_id],
                "disposition": "place",
                "target_slot_id": default_slot,
                "target_region_id": "body",
                "render_kind": render_kind,
                "style_ref": _style_for_item(item),
                "evidence": _evidence_for_item(item),
                "confidence": 0.9,
                "payload": item.get("payload", {"type": "text", "text": item.get("text", "")}),
                "content_hashes": [item.get("text_hash")],
            }
        )
    for item in content_artifact.get("unsupported", []):
        unresolved.append(
            {
                "content_id": item.get("content_id"),
                "disposition": "unsupported",
                "reason": item.get("reason", "unsupported visible object"),
                "blocking": item.get("blocking", True),
            }
        )

    plan = {
        "artifact_type": "placement_plan",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-placement", "version": "0.1.0"},
        "created_at": now_iso(),
        "input_hashes": {
            "template_artifact": sha256_json(template_artifact),
            "student_content_artifact": sha256_json(content_artifact),
        },
        "provenance": {
            "template_artifact_hash": sha256_json(template_artifact),
            "student_content_artifact_hash": sha256_json(content_artifact),
        },
        "status_notes": [],
        "unsupported": [],
        "data": {
            "actions": actions,
            "unresolved": unresolved,
            "school_exception_refs": [],
        },
    }
    findings = verify_placement_plan(plan, template_artifact, content_artifact)
    status = merge_statuses([Status(f.status) for f in findings]) if findings else Status.PASS
    return StageResult(
        "placement",
        status,
        findings=findings,
        artifacts={"placement_plan": plan},
        coverage={
            "placement.no_silent_drop": not any(f.type == "unplaced_content" for f in findings),
            "placement.slot_compatibility": not any(f.type == "slot_incompatible" for f in findings),
            "placement.required_slots": bool(slots),
        },
        user_message=(
            "转换失败：系统已提取到文档中的内容，但部分内容无法匹配到目标模板中的位置。"
            if status == Status.FAIL
            else None
        ),
    )


def _style_for_item(item: dict[str, Any]) -> str:
    if item.get("kind") == "heading":
        for candidate in item.get("semantic_candidates", []):
            if candidate.get("kind") == "heading":
                return f"Heading {candidate.get('level_candidate', 1)}"
        return "Heading 1"
    if item.get("kind") == "table":
        return "Table Grid"
    return "Normal"


def _evidence_for_item(item: dict[str, Any]) -> list[str]:
    evidence = [item.get("source_ref", "")]
    for candidate in item.get("semantic_candidates", []):
        evidence.extend(candidate.get("evidence", []))
    return [entry for entry in evidence if entry]


def verify_placement_plan(
    plan: dict[str, Any],
    template_artifact: dict[str, Any],
    content_artifact: dict[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    ledger_ids = [
        item["content_id"]
        for item in content_artifact.get("data", {}).get("visible_content_ledger", [])
    ]
    actions = plan.get("data", {}).get("actions", [])
    unresolved = plan.get("data", {}).get("unresolved", [])
    slot_by_id = {
        slot["slot_id"]: slot
        for slot in template_artifact.get("data", {}).get("slots", [])
    }
    planned_ids = [
        content_id
        for action in actions
        for content_id in action.get("content_ids", [])
    ]
    unresolved_ids = [item.get("content_id") for item in unresolved]
    next_index = 1
    for content_id in ledger_ids:
        occurrences = planned_ids.count(content_id) + unresolved_ids.count(content_id)
        if occurrences == 0:
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.FAIL,
                    "unplaced_content",
                    f"content block {content_id} has no placement action",
                    "every visible content block has exactly one disposition",
                    f"{content_id} missing from placement plan",
                    affected_ids=[content_id],
                    root_cause_bucket="placement_gap",
                )
            )
            next_index += 1
        elif occurrences > 1:
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.FAIL,
                    "duplicate_disposition",
                    f"content block {content_id} has multiple dispositions",
                    "one disposition per content block",
                    str(occurrences),
                    affected_ids=[content_id],
                    root_cause_bucket="placement_gap",
                )
            )
            next_index += 1
    for action in actions:
        slot = slot_by_id.get(action.get("target_slot_id"))
        if slot is None:
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.FAIL,
                    "target_slot_missing",
                    f"target slot {action.get('target_slot_id')} does not exist",
                    "target slot exists",
                    action.get("target_slot_id", "missing"),
                    affected_ids=action.get("content_ids", []),
                    root_cause_bucket="placement_slot_gap",
                )
            )
            next_index += 1
            continue
        accepted = slot.get("accepted_content_kinds", [])
        if action.get("render_kind") not in accepted:
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.FAIL,
                    "slot_incompatible",
                    f"content kind {action.get('render_kind')} is not accepted by slot",
                    ", ".join(accepted),
                    action.get("render_kind", "missing"),
                    affected_ids=action.get("content_ids", []),
                    root_cause_bucket="placement_slot_gap",
                )
            )
            next_index += 1
        if not action.get("evidence"):
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.UNKNOWN,
                    "placement_action_missing_evidence",
                    "Placement action has no evidence",
                    "evidence list is non-empty",
                    action.get("action_id", "missing"),
                    affected_ids=action.get("content_ids", []),
                    root_cause_bucket="placement_evidence_gap",
                )
            )
            next_index += 1
    for item in unresolved:
        if item.get("blocking", True):
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.UNKNOWN,
                    "blocking_unresolved_content",
                    f"Unresolved content {item.get('content_id')} blocks placement",
                    "content is placeable or explicitly rejected by contract",
                    item.get("reason", "unresolved"),
                    affected_ids=[item.get("content_id", "")],
                    root_cause_bucket="placement_unresolved",
                )
            )
            next_index += 1
    return findings


def write_placement_outputs(out_dir: Path, result: StageResult) -> None:
    artifact = result.artifacts.get("placement_plan")
    if artifact is not None:
        path = out_dir / "artifacts" / "placement_plan.json"
        write_json(path, artifact)
        result.artifact_paths["placement_plan"] = path
