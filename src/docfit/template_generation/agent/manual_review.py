from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso


def build_agent_manual_review_items(
    *,
    transcript: dict[str, Any],
    comparison: dict[str, Any],
    decisions: dict[str, Any],
    observation_bridge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    items.extend(_open_question_items(transcript))
    items.extend(_bridge_items(observation_bridge or {}))
    represented_by_comparison: set[str] = set()
    for item in comparison.get("items", []) or []:
        if not isinstance(item, dict) or not item.get("manual_review_required"):
            continue
        proposal_id = str(item.get("proposal_id") or "")
        if proposal_id:
            represented_by_comparison.add(proposal_id)
        items.append(_comparison_item(item))
    for decision in decisions.get("decisions", []) or []:
        if not isinstance(decision, dict):
            continue
        if decision.get("decision") != "rejected":
            continue
        if decision.get("origin") == "comparison":
            continue
        proposal_id = str(decision.get("proposal_id") or "")
        if proposal_id and proposal_id in represented_by_comparison:
            continue
        items.append(_decision_item(decision))

    normalized = []
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        review_item_id = item.get("review_item_id") or _stable_review_id(item, index)
        if review_item_id in seen:
            review_item_id = f"{review_item_id}_{index:03d}"
        seen.add(review_item_id)
        normalized.append({"review_item_id": review_item_id, **item})
    return {
        "artifact_type": "template_agent_manual_review_items",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "items": normalized,
        "blocking_item_ids": [
            item["review_item_id"]
            for item in normalized
            if item.get("blocking_level") == "blocking"
        ],
        "non_blocking_item_ids": [
            item["review_item_id"]
            for item in normalized
            if item.get("blocking_level") != "blocking"
        ],
        "summary": {
            "total": len(normalized),
            "blocking": sum(
                1 for item in normalized if item.get("blocking_level") == "blocking"
            ),
            "non_blocking": sum(
                1 for item in normalized if item.get("blocking_level") != "blocking"
            ),
        },
    }


def _open_question_items(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for round_item in transcript.get("rounds", []) or []:
        if not isinstance(round_item, dict):
            continue
        submission = round_item.get("submission") or {}
        if not isinstance(submission, dict):
            continue
        round_id = submission.get("round_id") or round_item.get("round_id")
        layers = submission.get("layers") or {}
        if not isinstance(layers, dict):
            continue
        for layer, layer_value in layers.items():
            if not isinstance(layer_value, dict):
                continue
            for question in layer_value.get("open_questions", []) or []:
                if not isinstance(question, dict):
                    question = {"question": str(question)}
                items.append(
                    {
                        "source": "open_question",
                        "round_id": round_id,
                        "layer": str(layer),
                        "blocking_level": _blocking_level(question),
                        "reason_code": "OPEN-QUESTION",
                        "summary": (
                            question.get("question")
                            or question.get("summary")
                            or question.get("required_human_action")
                            or "agent reported an open question"
                        ),
                        "affected_refs": question.get("affected_refs", {}),
                        "agent_submission_summary": question.get(
                            "agent_submission_summary"
                        ),
                        "deterministic_summary": question.get("deterministic_summary"),
                        "suggested_candidate_policies": question.get(
                            "suggested_candidate_policies", []
                        ),
                        "required_human_action": question.get(
                            "required_human_action",
                            "Resolve the open question before accepting related agent proposals.",
                        ),
                        "question_id": question.get("question_id") or question.get("id"),
                    }
                )
    return items


def _bridge_items(bridge: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in bridge.get("manual_review_items", []) or []:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "source": item.get("source") or "observation_bridge",
                "round_id": None,
                "layer": item.get("layer"),
                "blocking_level": item.get("blocking_level") or "blocking",
                "reason_code": item.get("reason_code") or "OBSERVATION-BRIDGE",
                "summary": item.get("summary") or "AI observation bridge requires manual review",
                "affected_refs": item.get("affected_refs", {}),
                "agent_submission_summary": item.get("agent_submission_summary"),
                "deterministic_summary": item.get("deterministic_summary"),
                "suggested_candidate_policies": item.get("suggested_candidate_policies", []),
                "required_human_action": item.get(
                    "required_human_action",
                    "Review the AI observation before allowing it into code generation.",
                ),
            }
        )
    return items


def _comparison_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "comparison",
        "proposal_id": item.get("proposal_id"),
        "round_id": item.get("round_id"),
        "layer": item.get("layer"),
        "collection": item.get("collection"),
        "blocking_level": "blocking",
        "reason_code": item.get("check_id"),
        "summary": item.get("reason"),
        "affected_refs": item.get("affected_refs", {}),
        "agent_submission_summary": item.get("ai", {}),
        "deterministic_summary": item.get("deterministic", {}),
        "suggested_candidate_policies": [],
        "required_human_action": _required_action_for_comparison(item),
        "comparison_id": item.get("comparison_id"),
    }


def _decision_item(decision: dict[str, Any]) -> dict[str, Any]:
    checks = [check for check in decision.get("checks", []) or [] if isinstance(check, dict)]
    first_check = checks[0] if checks else {}
    return {
        "source": "validation_failure",
        "proposal_id": decision.get("proposal_id"),
        "round_id": decision.get("round_id"),
        "layer": _layer_from_context(decision),
        "collection": None,
        "blocking_level": "blocking",
        "reason_code": first_check.get("check_id") or "REJECTED",
        "summary": decision.get("reason") or first_check.get("reason"),
        "affected_refs": {},
        "agent_submission_summary": {
            "target_path": decision.get("target_path"),
            "checks": checks,
        },
        "deterministic_summary": {
            "decision": decision.get("decision"),
            "before_hash": decision.get("before_hash"),
            "after_hash": decision.get("after_hash"),
        },
        "suggested_candidate_policies": [],
        "required_human_action": "Review the rejected proposal and decide whether code, prompt, or human fixture input should change.",
    }


def _required_action_for_comparison(item: dict[str, Any]) -> str:
    check_id = str(item.get("check_id") or "")
    if check_id == "C-COMPARISON-CONFLICT":
        return "Choose whether the deterministic structure or the agent proposal owns the affected refs."
    if check_id == "C-HIGH-RISK":
        return "Review the high-risk change before allowing it into the executable proposal path."
    if check_id == "C-EVIDENCE-EXIST":
        return "Provide valid source_seq/page/render refs or reject the proposal."
    if check_id == "C-OPEN-QUESTION":
        return "Resolve the blocking open question before accepting proposals from this layer."
    return "Review the agent proposal before it can be executed."


def _blocking_level(question: dict[str, Any]) -> str:
    value = str(question.get("blocking_level") or question.get("severity") or "").lower()
    if not value:
        return "non_blocking" if question.get("blocking") is False else "blocking"
    if value in {"non_blocking", "non-blocking", "info", "low"}:
        return "non_blocking"
    return "blocking"


def _layer_from_context(decision: dict[str, Any]) -> str | None:
    pass_kind = str(decision.get("pass_kind") or "")
    if pass_kind.startswith("t2"):
        return "t2"
    if pass_kind.startswith("t4"):
        return "t4"
    return None


def _stable_review_id(item: dict[str, Any], index: int) -> str:
    source = _slug(str(item.get("source") or "item"))
    for key in ("question_id", "comparison_id", "proposal_id"):
        value = str(item.get(key) or "").strip()
        if value:
            return f"mr_{source}_{_slug(value)}"
    return f"mr_{source}_{index:03d}"


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value)
