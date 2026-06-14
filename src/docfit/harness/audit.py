from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, read_json, write_json


def append_audit_event(
    root: Path,
    event_type: str,
    *,
    allowed: bool,
    reason: str,
    affected_files: list[str] | None = None,
    actor: str = "docfit-harness",
) -> dict[str, Any]:
    audit_path = root / "reports" / "audit_log.json"
    if audit_path.exists():
        events = read_json(audit_path)
    else:
        events = []
    event = {
        "event_id": f"audit_{len(events) + 1:03d}",
        "event_type": event_type,
        "actor": actor,
        "timestamp": now_iso(),
        "allowed": allowed,
        "reason": reason,
        "affected_files": affected_files or [],
    }
    events.append(event)
    write_json(audit_path, events)
    return event


def reject_golden_auto_update(root: Path, affected_file: str) -> dict[str, Any]:
    return append_audit_event(
        root,
        "golden_auto_update_attempt",
        allowed=False,
        reason="golden files require signed review and cannot be auto-updated by a failing run",
        affected_files=[affected_file],
    )
