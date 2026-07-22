from __future__ import annotations

from docfit.template_generation.agent.t3_input import (
    build_t3_local_evidence,
    build_t3_local_tasks,
)
from docfit.template_generation.agent.t3_safety import (
    guard_t3_payload,
    preservation_fallback_items,
    restrict_tasks_to_unit_plan,
)

from .test_agent_t3_input import table_packet, unit_window


def test_t3_delete_gate_accepts_only_high_confidence_exact_pure_format_run() -> None:
    packet = table_packet()
    # 给一个真实可精确绑定的纯格式 run。
    row = packet["page_text_index"][2]
    row["text"] = "（小四号宋体）"
    row["style_details"]["runs"][0]["text"] = "（小四号宋体）"
    task = build_t3_local_tasks(packet, unit_windows=[unit_window()])[0]
    local = next(window for window in task["local_windows"] if 3 in window["source_seq_refs"])
    plan = {
        "route": "full_local_analysis",
        "default_preservation_policy": "fixed",
        "protected_source_seq_refs": [],
        "inspect_source_seq_refs": list(range(1, 8)),
    }
    evidence = build_t3_local_evidence(
        packet,
        task=task,
        local_window=local,
        unit_plan=plan,
    )
    raw_id = row["raw_run_ids"][0]
    payload, demotions = guard_t3_payload(
        {
            "items": [
                {
                    "element_id": "cover.remove_1",
                    "policy": "instruction_remove",
                    "confidence": "high",
                    "source_seq_refs": [3],
                    "raw_run_ids": [raw_id],
                    "removal_reason": "独立 run 只描述字号字体",
                }
            ]
        },
        evidence=evidence,
        unit_plan=plan,
    )

    assert payload["items"][0]["policy"] == "instruction_remove"
    assert payload["items"][0]["transformation"] == "remove_exact_span"
    assert demotions == []


def test_t3_delete_gate_converts_mixed_or_protected_content_to_preservation() -> None:
    packet = table_packet()
    task = build_t3_local_tasks(packet, unit_windows=[unit_window()])[0]
    local = task["local_windows"][0]
    plan = {
        "route": "preserve_structure_classify_fields",
        "default_preservation_policy": "fixed",
        "protected_source_seq_refs": list(range(1, 8)),
        "inspect_source_seq_refs": list(range(1, 8)),
    }
    evidence = build_t3_local_evidence(
        packet,
        task=task,
        local_window=local,
        unit_plan=plan,
    )
    payload, demotions = guard_t3_payload(
        {
            "items": [
                {
                    "element_id": "cover.remove_unsafe",
                    "policy": "instruction_remove",
                    "confidence": "medium",
                    "source_seq_refs": [1],
                    "raw_run_ids": packet["page_text_index"][0]["raw_run_ids"],
                    "removal_reason": "模型认为可以删",
                }
            ]
        },
        evidence=evidence,
        unit_plan=plan,
    )

    assert payload["items"][0]["policy"] == "fixed"
    assert payload["items"][0]["transformation"] == "preserve"
    assert demotions[0]["check_id"] == "C-T3-CONSERVATIVE-DELETE"


def test_inspect_route_calls_only_selected_regions_and_fallback_preserves_rest() -> None:
    packet = table_packet()
    tasks = build_t3_local_tasks(packet, unit_windows=[unit_window()], max_table_items=2)
    plan = {
        "route": "inspect_suspected_regions",
        "default_preservation_policy": "fixed",
        "inspect_source_seq_refs": [3, 4],
    }

    routed = restrict_tasks_to_unit_plan(tasks, plan)
    assert len(routed) == 1
    assert routed[0]["local_windows"][0]["source_seq_refs"] == [3, 4]
    fallback = preservation_fallback_items(
        packet,
        unit_window=unit_window(),
        unit_plan=plan,
        existing_items=[],
    )
    assert {item["source_seq_refs"][0] for item in fallback} == set(range(1, 8))
    assert all(item["policy"] == "fixed" for item in fallback)


def test_inspect_route_selects_claimable_source_ref_object_window() -> None:
    from .test_agent_t3_input import toc_object_packet, toc_object_window

    packet = toc_object_packet()
    window = toc_object_window()
    tasks = build_t3_local_tasks(packet, unit_windows=[window])
    routed = restrict_tasks_to_unit_plan(
        tasks,
        {
            "route": "inspect_suspected_regions",
            "inspect_source_seq_refs": [],
            "inspect_source_ref_refs": window["source_ref_refs"],
        },
    )

    assert len(routed) == 1
    assert routed[0]["local_windows"][0]["source_ref_refs"] == window[
        "source_ref_refs"
    ]
