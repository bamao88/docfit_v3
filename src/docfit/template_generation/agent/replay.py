from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import read_json

PASS_KIND_ALLOWED_LAYERS = {
    "t2_unit_scan": ["t2"],
    "t4_global_layout": ["t4"],
    "legacy_layered_submission": ["t2", "t4"],
}


def load_agent_transcript(path: Path) -> dict[str, Any]:
    transcript = read_json(path)
    if not isinstance(transcript, dict):
        raise ValueError(f"agent transcript must be a JSON object: {path}")
    return transcript


def transcript_submissions(
    transcript: dict[str, Any],
    *,
    max_rounds: int,
) -> list[dict[str, Any]]:
    return [
        step["submission"]
        for step in transcript_steps(transcript, max_rounds=max_rounds)
    ]


def transcript_steps(
    transcript: dict[str, Any],
    *,
    max_rounds: int,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for round_index, round_item in enumerate(transcript.get("rounds", []), start=1):
        if len(steps) >= max_rounds:
            break
        if not isinstance(round_item, dict):
            continue
        round_submissions = round_item.get("submissions")
        if isinstance(round_submissions, list):
            for submission in round_submissions:
                if len(steps) >= max_rounds:
                    break
                if isinstance(submission, dict):
                    steps.append(_step(round_item, submission, round_index=round_index))
            continue
        submission = round_item.get("submission")
        if isinstance(submission, dict):
            steps.append(_step(round_item, submission, round_index=round_index))
    if not steps:
        for index, submission in enumerate(transcript.get("submissions", []), start=1):
            if len(steps) >= max_rounds:
                break
            if isinstance(submission, dict):
                steps.append(_step({}, submission, round_index=index))
    return steps[:max_rounds]


def _step(
    round_item: dict[str, Any],
    submission: dict[str, Any],
    *,
    round_index: int,
) -> dict[str, Any]:
    round_id = str(
        submission.get("round_id")
        or round_item.get("round_id")
        or f"round_{round_index:03d}"
    )
    pass_kind = str(
        round_item.get("pass_kind")
        or submission.get("pass_kind")
        or "legacy_layered_submission"
    )
    allowed_layers = _allowed_layers(round_item, submission, pass_kind=pass_kind)
    pass_id = str(round_item.get("pass_id") or submission.get("pass_id") or round_id)
    window_id = str(
        round_item.get("window_id")
        or submission.get("window_id")
        or ("full_document" if pass_kind == "t2_unit_scan" else pass_id)
    )
    metadata = {
        "round_id": round_id,
        "pass_id": pass_id,
        "pass_kind": pass_kind,
        "window_id": window_id,
        "unit_id": round_item.get("unit_id") or submission.get("unit_id"),
        "allowed_layers": allowed_layers,
        "attempt_index": int(round_item.get("attempt_index") or 1),
    }
    return {
        **metadata,
        "submission": submission,
    }


def _allowed_layers(
    round_item: dict[str, Any],
    submission: dict[str, Any],
    *,
    pass_kind: str,
) -> list[str]:
    raw = round_item.get("allowed_layers") or submission.get("allowed_layers")
    if isinstance(raw, list):
        values = [str(value) for value in raw if str(value) in {"t2", "t4"}]
        if values:
            return values
    return list(PASS_KIND_ALLOWED_LAYERS.get(pass_kind, ["t2", "t4"]))


def pass_plan_from_steps(
    steps: list[dict[str, Any]],
    *,
    provider: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "template_agent_pass_plan",
        "artifact_version": "1.0",
        "provider": provider,
        "passes": [
            {
                key: step.get(key)
                for key in (
                    "pass_id",
                    "pass_kind",
                    "window_id",
                    "unit_id",
                    "round_id",
                    "attempt_index",
                    "allowed_layers",
                )
            }
            for step in steps
        ],
    }
