from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from docfit.core.status import Status


@dataclass
class Finding:
    finding_id: str
    stage: str
    severity: str
    status: Status
    type: str
    message: str
    expected: str
    actual: str
    evidence_refs: list[str] = field(default_factory=list)
    affected_ids: list[str] = field(default_factory=list)
    root_cause_bucket: str = "uncategorized"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class StageResult:
    stage: str
    status: Status
    run_status: Status | None = None
    quality_status: Status | None = None
    findings: list[Finding] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    artifact_paths: dict[str, Path] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)
    blocked_at: str | None = None
    user_message: str | None = None

    def __post_init__(self) -> None:
        if self.run_status is None:
            self.run_status = self.status
        if self.quality_status is None:
            self.quality_status = self.status

    def finding_dicts(self) -> list[dict[str, Any]]:
        return [finding.to_dict() for finding in self.findings]


def make_finding(
    index: int,
    stage: str,
    status: Status,
    type_: str,
    message: str,
    expected: str,
    actual: str,
    *,
    evidence_refs: list[str] | None = None,
    affected_ids: list[str] | None = None,
    root_cause_bucket: str | None = None,
    severity: str = "blocking",
) -> Finding:
    return Finding(
        finding_id=f"f_{index:03d}",
        stage=stage,
        severity=severity,
        status=status,
        type=type_,
        message=message,
        expected=expected,
        actual=actual,
        evidence_refs=evidence_refs or [],
        affected_ids=affected_ids or [],
        root_cause_bucket=root_cause_bucket or type_,
    )
