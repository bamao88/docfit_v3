from __future__ import annotations

from docfit.template_generation.agent.overlay import apply_t2_proposal

from .helpers import structure_candidates


def test_overlay_gap_claim_can_assign_source_seq_that_round0_left_unowned() -> None:
    candidates = structure_candidates()
    body = next(unit for unit in candidates["units"] if unit["unit_id"] == "body_main")
    body["source_seq_refs"] = [2, 3]
    body["source_refs"] = body["source_refs"][:2]
    body["source_range"]["source_refs"] = body["source_refs"]
    body["source_seq_range"]["source_seq_refs"] = [2, 3]
    body["elements"] = body["elements"][:2]

    patched, operation, reason = apply_t2_proposal(
        candidates,
        {
            "proposal_id": "t2_claim_gap_001",
            "kind": "unit_candidate",
            "operation": "add_unit",
            "unit_id": "appendix_gap",
            "display_name": "未归属附录",
            "source_seq_refs": [4],
        },
        collection="unit_candidates",
    )

    assert reason == ""
    assert patched is not None
    assert operation is not None
    assert operation["round0_unassigned_source_seq_refs"] == [4]
    assert operation["round0_reassigned_source_seq_refs"] == []
    assert any(unit["unit_id"] == "appendix_gap" for unit in patched["units"])
    owned = {
        seq
        for unit in patched["units"]
        for seq in unit.get("source_seq_refs", [])
    }
    assert {1, 2, 3, 4}.issubset(owned)


def test_overlay_gap_claim_rejects_spanning_multiple_existing_units() -> None:
    patched, operation, reason = apply_t2_proposal(
        structure_candidates(),
        {
            "proposal_id": "t2_bad_cross_unit",
            "kind": "unit_candidate",
            "operation": "add_unit",
            "unit_id": "cross_unit",
            "display_name": "跨单元抢占",
            "source_seq_refs": [1, 2],
        },
        collection="unit_candidates",
    )

    assert patched is None
    assert operation is None
    assert "multiple existing units" in reason
