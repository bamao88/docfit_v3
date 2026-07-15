from __future__ import annotations

from docfit.template_generation.agent.attribution import build_agent_attribution


def test_keyed_attribution_ignores_reordered_unit_lists() -> None:
    attribution = _attribution(
        round0_unit_map={
            "units": [
                {"unit_id": "cover", "order": 10},
                {"unit_id": "body_main", "order": 20},
            ]
        },
        post_agent_unit_map={
            "units": [
                {"unit_id": "body_main", "order": 20},
                {"unit_id": "cover", "order": 10},
            ]
        },
    )

    assert attribution["field_diffs"] == []


def test_keyed_attribution_reports_added_and_removed_items_by_stable_key() -> None:
    attribution = _attribution(
        round0_unit_map={
            "units": [
                {"unit_id": "cover", "order": 10},
                {"unit_id": "obsolete", "order": 20},
            ]
        },
        post_agent_unit_map={
            "units": [
                {"unit_id": "cover", "order": 10},
                {"unit_id": "toc", "order": 20},
            ]
        },
    )

    paths = {diff["path"]: diff["change"] for diff in attribution["field_diffs"]}
    assert paths["$.unit_map.units[unit_id=obsolete]"] == "removed"
    assert paths["$.unit_map.units[unit_id=toc]"] == "added"


def _attribution(
    *,
    round0_unit_map: dict,
    post_agent_unit_map: dict,
) -> dict:
    return build_agent_attribution(
        transcript={"rounds": []},
        decisions={"accepted_proposal_ids": [], "rejected_proposal_ids": []},
        round0_unit_map=round0_unit_map,
        post_agent_unit_map=post_agent_unit_map,
        round0_element_spec={"elements": []},
        post_agent_element_spec={"elements": []},
        t2_overlay={"operations": []},
        t3_overlay={"operations": []},
        t4_hints={
            "section_profile_hints": [],
            "page_numbering_hints": [],
        },
    )
