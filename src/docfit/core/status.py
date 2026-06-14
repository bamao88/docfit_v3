from __future__ import annotations

from enum import StrEnum


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class StageRunState(StrEnum):
    PENDING = "not_run"
    RAN = "ran"


def merge_statuses(statuses: list[Status]) -> Status:
    if not statuses:
        return Status.UNKNOWN
    if any(status == Status.FAIL for status in statuses):
        return Status.FAIL
    if any(status == Status.UNKNOWN for status in statuses):
        return Status.UNKNOWN
    return Status.PASS


def status_from_findings(findings: list[dict], default: Status = Status.PASS) -> Status:
    statuses = [
        Status(finding["status"])
        for finding in findings
        if finding.get("severity") == "blocking"
    ]
    return merge_statuses(statuses) if statuses else default
