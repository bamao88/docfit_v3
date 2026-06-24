from __future__ import annotations

from docfit.ai_rca.packets import build_advisory_stub, build_diagnosis_packet
from docfit.core.status import Status, merge_statuses
from docfit.harness.audit import reject_golden_auto_update


def test_status_merge_order() -> None:
    assert list(Status) == [Status.PASS, Status.FAIL, Status.UNKNOWN]
    assert merge_statuses([]) == Status.UNKNOWN
    assert merge_statuses([Status.PASS, Status.UNKNOWN]) == Status.UNKNOWN
    assert merge_statuses([Status.PASS, Status.FAIL, Status.UNKNOWN]) == Status.FAIL
    assert merge_statuses([Status.PASS, Status.PASS]) == Status.PASS


def test_signed_standard_cannot_auto_update(tmp_path) -> None:
    event = reject_golden_auto_update(
        tmp_path,
        "standards/targets/demo/v1/golden/features.json",
    )
    assert event["allowed"] is False
    assert event["event_type"] == "golden_auto_update_attempt"


def test_ai_advisory_does_not_claim_final_status() -> None:
    advisory = build_advisory_stub(Status.FAIL.value)
    assert advisory["advisory_only"] is True
    assert advisory["final_status"] == "NOT_PROVIDED_BY_AI"
    assert advisory["harness_status"] == "FAIL"


def test_ai_diagnosis_packet_is_advisory_only() -> None:
    packet = build_diagnosis_packet(
        "run_001",
        Status.UNKNOWN.value,
        [{"cluster_id": "cluster_001", "status": "UNKNOWN"}],
    )

    assert packet["advisory_only"] is True
    assert packet["harness_status"] == "UNKNOWN"
    assert packet["status_authority"] == "deterministic_harness_only"
    assert packet["summary_status_mutation_allowed"] is False
    assert "mutate_summary_status" in packet["forbidden_ai_tasks"]
    assert "override_fail_or_unknown" in packet["forbidden_ai_tasks"]
