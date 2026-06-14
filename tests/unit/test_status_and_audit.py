from __future__ import annotations

from docfit.ai_rca.packets import build_advisory_stub
from docfit.core.status import Status, merge_statuses
from docfit.harness.audit import reject_golden_auto_update


def test_status_merge_order() -> None:
    assert merge_statuses([Status.PASS, Status.UNKNOWN]) == Status.UNKNOWN
    assert merge_statuses([Status.PASS, Status.FAIL, Status.UNKNOWN]) == Status.FAIL
    assert merge_statuses([Status.PASS, Status.PASS]) == Status.PASS


def test_signed_standard_cannot_auto_update(tmp_path) -> None:
    event = reject_golden_auto_update(tmp_path, "standards/schools/demo/golden/features.json")
    assert event["allowed"] is False
    assert event["event_type"] == "golden_auto_update_attempt"


def test_ai_advisory_does_not_claim_final_status() -> None:
    advisory = build_advisory_stub(Status.FAIL.value)
    assert advisory["advisory_only"] is True
    assert advisory["final_status"] == "NOT_PROVIDED_BY_AI"
    assert advisory["harness_status"] == "FAIL"
