from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_issue_clusters(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        key = (
            finding.get("stage", "unknown"),
            finding.get("status", "UNKNOWN"),
            finding.get("root_cause_bucket", finding.get("type", "uncategorized")),
        )
        grouped[key].append(finding)

    clusters: list[dict[str, Any]] = []
    for index, ((stage, status, bucket), items) in enumerate(grouped.items(), start=1):
        affected_ids = sorted(
            {
                affected_id
                for item in items
                for affected_id in item.get("affected_ids", [])
            }
        )
        clusters.append(
            {
                "cluster_id": f"cluster_{stage}_{index:03d}",
                "stage": stage,
                "status": status,
                "title": items[0].get("message", bucket),
                "invariant": items[0].get("expected", ""),
                "affected_content_ids": affected_ids,
                "affected_slots": [],
                "evidence": [
                    {"finding_id": item.get("finding_id"), "message": item.get("message")}
                    for item in items
                ],
                "likely_root_cause_bucket": bucket,
                "ai_allowed": True,
            }
        )
    return clusters
