from __future__ import annotations

from copy import deepcopy

from docfit.template_generation.agent.t3_atomic_compare import (
    build_t3_atomic_route_comparison,
)
from docfit.template_generation.agent.t3_hierarchical_input import (
    build_t3_hierarchical_stage_input,
    nodes_by_ref,
)

from .test_agent_t3_hierarchical_input import _windows
from .test_agent_t3_input import table_packet, unit_window


def test_atomic_comparison_aligns_code_ai_and_merged_by_member_ref() -> None:
    stage_input = build_t3_hierarchical_stage_input(
        table_packet(),
        unit_windows=_windows(unit_window()),
    )
    nodes = nodes_by_ref(stage_input)
    leaves = [nodes[ref] for ref in nodes["unit:cover"]["member_leaf_refs"]]
    code_elements = [
        {
            "element_id": f"e_{index:03d}",
            "stable_id": f"cover.e_{index:03d}",
            "unit_id": "cover",
            "policy": "fixed",
            "source_seq_refs": leaf["source_seq_refs"],
            "raw_run_ids": [leaf["facts"]["raw_run_id"]],
        }
        for index, leaf in enumerate(leaves, start=1)
    ]
    changed_ref = leaves[0]["ref"]
    ai_coverage = [
        {
            "member_ref": leaf["ref"],
            "resolved_result": "fill" if leaf["ref"] == changed_ref else "keep",
            "resolution": "direct",
            "decision_status": "accepted",
            "decision_ref": f"decision:{index}",
            "decision_target_ref": leaf["ref"],
        }
        for index, leaf in enumerate(leaves, start=1)
    ]
    merged_elements = deepcopy(code_elements)
    next(
        element
        for element in merged_elements
        if element["raw_run_ids"] == [leaves[0]["facts"]["raw_run_id"]]
    )["policy"] = "fill"

    comparison = build_t3_atomic_route_comparison(
        stage_input=stage_input,
        code_element_spec={"elements": code_elements},
        ai_observation={"atomic_coverage": ai_coverage},
        merged_element_spec={"elements": merged_elements},
    )

    assert comparison["validation"]["valid"] is True
    assert comparison["summary"]["atomic_member_count"] == len(leaves)
    assert comparison["summary"]["code_ai_different"] == 1
    assert comparison["summary"]["merged_from_ai"] == 1
    changed = next(row for row in comparison["rows"] if row["member_ref"] == changed_ref)
    assert changed["code"]["resolved_action"] == "keep"
    assert changed["ai"]["resolved_action"] == "fill"
    assert changed["merged"]["resolved_action"] == "fill"
    assert changed["merged_resolution"] == "ai"


def test_atomic_comparison_keeps_fallback_distinct_from_accepted_ai() -> None:
    stage_input = build_t3_hierarchical_stage_input(
        table_packet(),
        unit_windows=_windows(unit_window()),
    )
    nodes = nodes_by_ref(stage_input)
    leaves = [nodes[ref] for ref in nodes["unit:cover"]["member_leaf_refs"]]
    elements = [
        {
            "element_id": f"e_{index:03d}",
            "policy": "fixed",
            "source_seq_refs": leaf["source_seq_refs"],
            "raw_run_ids": [leaf["facts"]["raw_run_id"]],
        }
        for index, leaf in enumerate(leaves, start=1)
    ]
    coverage = [
        {
            "member_ref": leaf["ref"],
            "resolved_result": "keep",
            "resolution": "fallback" if index == 1 else "direct",
            "decision_status": "failed" if index == 1 else "accepted",
        }
        for index, leaf in enumerate(leaves, start=1)
    ]

    comparison = build_t3_atomic_route_comparison(
        stage_input=stage_input,
        code_element_spec={"elements": elements},
        ai_observation={"atomic_coverage": coverage},
        merged_element_spec={"elements": elements},
    )

    fallback = next(row for row in comparison["rows"] if row["ai"]["status"] == "fallback")
    assert fallback["ai"]["decision_status"] == "failed"
    assert fallback["merged_resolution"] == "code"


def test_atomic_comparison_resolves_element_spans_on_exact_char_ranges() -> None:
    packet = table_packet()
    row = packet["page_text_index"][-1]
    row["text"] = "学号：20XX"
    row["style_details"]["runs"][0]["text"] = row["text"]
    stage_input = build_t3_hierarchical_stage_input(
        packet,
        unit_windows=_windows({**unit_window(), "source_seq_refs": [7]}),
    )
    nodes = nodes_by_ref(stage_input)
    leaves = [nodes[ref] for ref in nodes["unit:cover"]["member_leaf_refs"]]
    element = {
        "element_id": "e_001",
        "policy": "fixed",
        "source_seq_refs": [7],
        "raw_run_ids": ["p_0099.r_001"],
        "spans": [
            {
                "span_id": "label",
                "policy": "fixed",
                "raw_run_ids": ["p_0099.r_001"],
                "char_ranges": [
                    {"raw_run_id": "p_0099.r_001", "start": 0, "end": 3}
                ],
            },
            {
                "span_id": "value",
                "policy": "fill",
                "raw_run_ids": ["p_0099.r_001"],
                "char_ranges": [
                    {"raw_run_id": "p_0099.r_001", "start": 3, "end": 7}
                ],
            },
        ],
    }
    ai_coverage = [
        {
            "member_ref": leaf["ref"],
            "resolved_result": "keep" if leaf["facts"]["start"] == 0 else "fill",
            "resolution": "direct",
            "decision_status": "accepted",
        }
        for leaf in leaves
    ]

    comparison = build_t3_atomic_route_comparison(
        stage_input=stage_input,
        code_element_spec={"elements": [element]},
        ai_observation={"atomic_coverage": ai_coverage},
        merged_element_spec={"elements": [element]},
    )

    assert comparison["validation"]["valid"] is True
    assert [row["code"]["resolved_action"] for row in comparison["rows"]] == [
        "keep",
        "fill",
    ]
    assert all(row["code_ai_relation"] == "same" for row in comparison["rows"])
