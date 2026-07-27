"""Stable final-result boundary between template-generation stages.

Stage implementations may keep any number of code, AI, merged, replay, or
diagnostic candidates.  Cross-stage business code receives only
``FinalStageResult`` and therefore cannot accidentally consume one of those
internal candidates.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from docfit.core.io import sha256_json


FINAL_RESULT_ROLE = "final"
AVAILABLE = "AVAILABLE"
NOT_AVAILABLE = "NOT_AVAILABLE"
_AVAILABILITY_VALUES = frozenset({AVAILABLE, NOT_AVAILABLE})


class FinalStageResultError(ValueError):
    """Raised when a stage attempts to consume a non-final upstream result."""


@dataclass(frozen=True)
class FinalStageResult:
    """Validated in-memory handle for one stage's canonical published result."""

    stage_id: str
    artifact_type: str
    artifact_name: str
    availability: str
    reason: str | None
    payload: dict[str, Any]
    path: Path | None = None

    @property
    def sha256(self) -> str:
        return sha256_json(self.payload)

    def input_ref(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "artifact": self.artifact_name,
            "sha256": self.sha256,
            "availability": self.availability,
        }


def publish_final_stage_result(
    payload: dict[str, Any],
    *,
    stage_id: str,
    artifact_type: str,
    artifact_name: str,
    availability: str = AVAILABLE,
    reason: str | None = None,
    producer_mode: str,
    selected_from: Iterable[dict[str, Any]] = (),
    input_refs: dict[str, dict[str, Any]] | None = None,
) -> FinalStageResult:
    """Publish a stable final artifact without exposing route choice to consumers."""

    _require_availability(availability)
    if str(payload.get("artifact_type") or "") != artifact_type:
        raise FinalStageResultError(
            f"{stage_id} final artifact_type must be {artifact_type}; "
            f"got {payload.get('artifact_type')!r}"
        )
    published = deepcopy(payload)
    published.update(
        {
            "stage_id": stage_id,
            "result_role": FINAL_RESULT_ROLE,
            "availability": {
                "status": availability,
                "reason": reason,
            },
            "input_refs": deepcopy(input_refs or {}),
            "lineage": {
                "producer_mode": producer_mode,
                "selected_from": [deepcopy(item) for item in selected_from],
            },
        }
    )
    return FinalStageResult(
        stage_id=stage_id,
        artifact_type=artifact_type,
        artifact_name=artifact_name,
        availability=availability,
        reason=reason,
        payload=published,
    )


def require_final_stage_result(
    value: FinalStageResult | dict[str, Any],
    *,
    stage_id: str,
    artifact_type: str,
    artifact_name: str,
    expected_l1_hash: str | None = None,
) -> FinalStageResult:
    """Validate a final handle at the consumer boundary.

    A raw mapping is accepted only when it already carries the complete final
    metadata.  Candidate artifacts such as AI observations and merged route
    evidence fail immediately.
    """

    if isinstance(value, FinalStageResult):
        result = value
    elif isinstance(value, dict):
        availability = value.get("availability")
        availability = availability if isinstance(availability, dict) else {}
        result = FinalStageResult(
            stage_id=str(value.get("stage_id") or ""),
            artifact_type=str(value.get("artifact_type") or ""),
            artifact_name=artifact_name,
            availability=str(availability.get("status") or ""),
            reason=(
                str(availability.get("reason"))
                if availability.get("reason") not in (None, "")
                else None
            ),
            payload=value,
        )
    else:
        raise FinalStageResultError(
            f"{stage_id} consumer requires FinalStageResult, got {type(value).__name__}"
        )

    errors: list[str] = []
    if result.stage_id != stage_id:
        errors.append(f"stage_id={result.stage_id!r}")
    if result.artifact_type != artifact_type:
        errors.append(f"artifact_type={result.artifact_type!r}")
    if result.artifact_name != artifact_name:
        errors.append(f"artifact_name={result.artifact_name!r}")
    if result.payload.get("result_role") != FINAL_RESULT_ROLE:
        errors.append(f"result_role={result.payload.get('result_role')!r}")
    if result.availability not in _AVAILABILITY_VALUES:
        errors.append(f"availability={result.availability!r}")
    if expected_l1_hash is not None:
        l1_ref = (result.payload.get("input_refs") or {}).get("l1") or {}
        if l1_ref.get("sha256") != expected_l1_hash:
            errors.append(f"l1.sha256={l1_ref.get('sha256')!r}")
    if errors:
        raise FinalStageResultError(
            f"{stage_id} consumer rejected non-final or mismatched upstream: "
            + ", ".join(errors)
        )
    return result


def conservative_availability(*results: FinalStageResult) -> tuple[str, str | None]:
    unavailable = [result for result in results if result.availability != AVAILABLE]
    if not unavailable:
        return AVAILABLE, None
    reasons = [
        f"{result.stage_id}: {result.reason or result.availability}"
        for result in unavailable
    ]
    return NOT_AVAILABLE, "; ".join(reasons)


def candidate_ref(
    payload: dict[str, Any],
    *,
    route_id: str,
    artifact: str,
) -> dict[str, Any]:
    return {
        "route_id": route_id,
        "artifact": artifact,
        "sha256": sha256_json(payload),
    }


def _require_availability(value: str) -> None:
    if value not in _AVAILABILITY_VALUES:
        raise FinalStageResultError(
            f"final availability must be one of {sorted(_AVAILABILITY_VALUES)}; "
            f"got {value!r}"
        )
