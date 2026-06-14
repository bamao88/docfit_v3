from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.ai_rca.packets import build_advisory_stub, build_diagnosis_packet
from docfit.core.io import ensure_dir, now_iso, write_json, write_text
from docfit.core.status import Status
from docfit.harness.issue_clusters import build_issue_clusters


def _run_id(out_dir: Path) -> str:
    return out_dir.name or "run"


def write_report_bundle(
    out_dir: Path,
    *,
    stage: str,
    status: Status,
    findings: list[dict[str, Any]],
    artifacts: dict[str, str] | None = None,
    coverage: dict[str, Any] | None = None,
    stage_statuses: dict[str, str] | None = None,
    blocked_at: str | None = None,
    user_message: str | None = None,
) -> dict[str, Any]:
    ensure_dir(out_dir)
    ensure_dir(out_dir / "artifacts")
    ensure_dir(out_dir / "ai")

    blocking_findings = [
        finding for finding in findings if finding.get("severity") == "blocking"
    ]
    unknown_findings = [
        finding for finding in findings if finding.get("status") == Status.UNKNOWN.value
    ]
    silent_drop_count = sum(1 for finding in findings if finding.get("type") == "unplaced_content")
    primary_bucket = (
        blocking_findings[0].get("root_cause_bucket", "none")
        if blocking_findings
        else "none"
    )
    clusters = build_issue_clusters(findings)
    run_id = _run_id(out_dir)
    summary = {
        "run_id": run_id,
        "stage": stage,
        "status": status.value,
        "stage_statuses": stage_statuses or {stage: status.value},
        "blocked_at": blocked_at,
        "blocking_findings": len(blocking_findings),
        "unknown_findings": len(unknown_findings),
        "silent_drop_count": silent_drop_count,
        "primary_failure_bucket": primary_bucket,
        "coverage": coverage or {},
        "artifacts": artifacts or {},
        "reports": {
            "pm_report": "pm_report.md",
            "findings": "findings.json",
            "issue_clusters": "issue_clusters.json",
            "diagnosis_packet": "ai/diagnosis_packet.json",
        },
        "user_message": user_message,
        "created_at": now_iso(),
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "findings.json", findings)
    write_json(out_dir / "issue_clusters.json", clusters)
    write_json(
        out_dir / "ai" / "diagnosis_packet.json",
        build_diagnosis_packet(run_id, status.value, clusters),
    )
    write_json(out_dir / "ai" / "advisory.json", build_advisory_stub(status.value))
    write_text(out_dir / "pm_report.md", build_pm_report(summary, findings))
    return summary


def build_pm_report(summary: dict[str, Any], findings: list[dict[str, Any]]) -> str:
    lines = [
        f"# DocFit Eval Report: {summary['run_id']}",
        "",
        f"- Status: {summary['status']}",
        f"- Stage: {summary['stage']}",
        f"- Blocked at: {summary.get('blocked_at') or 'none'}",
        f"- Blocking findings: {summary['blocking_findings']}",
        f"- Unknown findings: {summary['unknown_findings']}",
        f"- Silent drop count: {summary['silent_drop_count']}",
        f"- Primary bucket: {summary['primary_failure_bucket']}",
        "- AI role: advisory packet generated; AI cannot change gate status.",
    ]
    if summary.get("user_message"):
        lines.extend(["", f"User message: {summary['user_message']}"])
    if findings:
        lines.extend(["", "## Findings"])
        for finding in findings:
            lines.append(
                f"- [{finding.get('status')}] {finding.get('type')}: {finding.get('message')}"
            )
    else:
        lines.extend(["", "No findings."])
    lines.append("")
    return "\n".join(lines)
