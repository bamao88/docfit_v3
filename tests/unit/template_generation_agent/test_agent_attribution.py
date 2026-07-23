from __future__ import annotations

from docfit.template_generation.agent.attribution import build_agent_attribution


def test_attribution_records_round0_and_post_hashes() -> None:
    attribution = build_agent_attribution(
        transcript={"rounds": [{"round_id": "round_001"}]},
        decisions={
            "accepted_proposal_ids": ["p1"],
            "rejected_proposal_ids": ["p2"],
        },
        round0_unit_map={"units": [{"unit_id": "body_main"}]},
        post_agent_unit_map={"units": [{"unit_id": "body_main"}, {"unit_id": "toc"}]},
        round0_element_spec={"elements": []},
        post_agent_element_spec={"elements": []},
        t2_overlay={"operations": [{"proposal_id": "p1"}]},
        t3_materialization_trace={"materialization": {"availability": "AVAILABLE"}},
        t4_hints={"section_profile_hints": [], "page_numbering_hints": []},
    )

    assert attribution["artifact_type"] == "agent_attribution"
    assert attribution["applied_proposal_ids"] == ["p1"]
    assert attribution["rejected_proposal_ids"] == ["p2"]
    assert attribution["field_diffs"]
    assert attribution["materialization_traces"]["t3"]["availability"] == "AVAILABLE"
