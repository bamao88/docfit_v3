from __future__ import annotations

from docfit.template_generation.agent.windows import (
    build_agent_unit_windows,
    t3_window_error,
    window_for_step,
)

from .helpers import packet, structure_candidates


def test_unit_windows_bind_pages_render_targets_and_neighbors() -> None:
    candidates = structure_candidates()
    render_packet = packet()
    for item in render_packet["page_text_index"]:
        if item["source_seq"] == 4:
            item["page_no"] = 2

    windows = build_agent_unit_windows(
        structure_candidates=candidates,
        packet=render_packet,
    )

    cover = window_for_step(windows, {"unit_id": "cover"})
    body = window_for_step(windows, {"window_id": "unit:body_main"})
    assert cover is not None
    assert body is not None
    assert cover["neighbor_context"]["next_unit_id"] == "body_main"
    assert body["neighbor_context"]["previous_unit_id"] == "cover"
    assert body["page_nos"] == [1, 2]
    assert body["candidate_targets"][0]["target_candidate_id"] == "body_main.e_001"
    assert body["candidate_targets"][0]["render_target_refs"] == ["source_seq:2"]


def test_t3_window_error_rejects_source_and_target_outside_active_window() -> None:
    windows = build_agent_unit_windows(
        structure_candidates=structure_candidates(),
        packet=packet(),
    )
    cover = window_for_step(windows, {"unit_id": "cover"})

    assert cover is not None
    assert t3_window_error(
        proposal={
            "proposal_id": "inside",
            "source_seq_refs": [1],
            "target_candidate_id": "cover.e_001",
        },
        window=cover,
    ) is None
    assert "source_seq_refs outside unit window" in str(
        t3_window_error(
            proposal={"proposal_id": "outside_source", "source_seq_refs": [2]},
            window=cover,
        )
    )
    assert "target_candidate_id outside unit window" in str(
        t3_window_error(
            proposal={
                "proposal_id": "outside_target",
                "source_seq_refs": [1],
                "target_candidate_id": "body_main.e_001",
            },
            window=cover,
        )
    )
