from __future__ import annotations

from enum import StrEnum


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_RUN = "NOT_RUN"


def merge_statuses(statuses: list[Status]) -> Status:
    if not statuses:
        return Status.NOT_RUN
    if any(status == Status.FAIL for status in statuses):
        return Status.FAIL
    if any(status == Status.UNKNOWN for status in statuses):
        return Status.UNKNOWN
    if any(status == Status.NOT_RUN for status in statuses):
        return Status.NOT_RUN
    return Status.PASS


def status_from_findings(findings: list[dict], default: Status = Status.PASS) -> Status:
    statuses = [
        Status(finding["status"])
        for finding in findings
        if finding.get("severity") == "blocking"
    ]
    return merge_statuses(statuses) if statuses else default
