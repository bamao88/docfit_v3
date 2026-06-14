from __future__ import annotations

from typing import Any


def build_diagnosis_packet(
    run_id: str,
    status: str,
    clusters: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "packet_id": f"diag_{run_id}",
        "run_id": run_id,
        "harness_status": status,
        "advisory_only": True,
        "status_authority": "deterministic_harness_only",
        "summary_status_mutation_allowed": False,
        "clusters": clusters,
        "input_scope": "findings_and_issue_clusters_only",
        "allowed_ai_tasks": [
            "summarize_root_cause",
            "suggest_generic_fix",
            "suggest_tests",
        ],
        "forbidden_ai_tasks": [
            "judge_pass_fail",
            "mutate_summary_status",
            "override_fail_or_unknown",
            "update_expected",
            "create_school_patch",
            "declare_school_exception_without_signed_evidence",
            "use_visual_impression_as_gate",
        ],
    }


def build_advisory_stub(status: str) -> dict[str, Any]:
    return {
        "advisory_only": True,
        "likely_root_cause": "No AI diagnosis was run in the bootstrap harness.",
        "recommended_generic_fix": "Inspect blocking findings and add deterministic verifier coverage.",
        "recommended_tests": [],
        "final_status": "NOT_PROVIDED_BY_AI",
        "harness_status": status,
    }
