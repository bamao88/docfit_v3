from __future__ import annotations

from docfit.template_generation.agent.t3_hierarchical_input import (
    build_t3_hierarchical_stage_input,
    nodes_by_ref,
)
from docfit.template_generation.agent.t3_sparse_decisions import (
    run_t3_sparse_traversal,
    validate_t3_sparse_decision,
)
from docfit.template_generation.agent.t3_sparse_materialize import (
    materialize_sparse_t3_observation,
)

from .test_agent_t3_input import table_packet, unit_window


def _stage_input(window: dict | None = None) -> dict:
    return build_t3_hierarchical_stage_input(
        table_packet(),
        unit_windows={
            "post_t2_observation_hash": "sha256:t2",
            "windows": [window or unit_window()],
        },
    )


def test_terminal_unit_keep_stops_descending_and_expands_inherited_coverage() -> None:
    stage_input = _stage_input()
    calls: list[str] = []

    def decide(_evidence: dict, node: dict, _unit_id: str) -> dict:
        calls.append(node["ref"])
        return {
            "target_ref": node["ref"],
            "result": "keep",
            "confidence": "high",
            "reason": "entire unit is fixed content",
        }

    trace = run_t3_sparse_traversal(stage_input, decide=decide)

    assert calls == ["unit:cover"]
    assert trace["validation"] == {"valid": True, "errors": []}
    assert len(trace["atomic_coverage"]) == len(nodes_by_ref(stage_input)["unit:cover"]["member_leaf_refs"])
    assert {row["resolution"] for row in trace["atomic_coverage"]} == {"inherited"}
    assert {row["resolved_result"] for row in trace["atomic_coverage"]} == {"keep"}


def test_split_visits_only_direct_exceptions_and_defaults_other_children_to_keep() -> None:
    stage_input = _stage_input()
    calls: list[str] = []
    selected_row = "table:tbl_0001/row:002"
    selected_cell = f"{selected_row}/cell:002"

    def decide(_evidence: dict, node: dict, _unit_id: str) -> dict:
        ref = node["ref"]
        calls.append(ref)
        if ref == "unit:cover":
            return _split(ref, ["table:tbl_0001"])
        if ref == "table:tbl_0001":
            return _split(ref, [selected_row])
        if ref == selected_row:
            return _split(ref, [selected_cell])
        return {
            "target_ref": ref,
            "result": "fill",
            "confidence": "high",
            "reason": "the complete cell is one student value",
            "fill": {"source": "student_content", "field": "student_name"},
        }

    trace = run_t3_sparse_traversal(stage_input, decide=decide)

    assert calls == ["unit:cover", "table:tbl_0001", selected_row, selected_cell]
    filled = [row for row in trace["atomic_coverage"] if row["resolved_result"] == "fill"]
    assert len(filled) == 1
    assert filled[0]["raw_run_ids"] == ["p_0004.r_001"]
    assert filled[0]["member_kind"] == "span"
    assert filled[0]["resolution"] == "inherited"
    assert all(
        row["resolved_result"] == "keep"
        for row in trace["atomic_coverage"]
        if row not in filled
    )


def test_split_can_resolve_complete_direct_child_without_another_provider_call() -> None:
    stage_input = _stage_input()
    calls: list[str] = []
    paragraph_ref = "unit:cover/paragraph:p_0099"

    def decide(_evidence: dict, node: dict, _unit_id: str) -> dict:
        calls.append(node["ref"])
        return {
            "target_ref": node["ref"],
            "result": "split",
            "default_child_result": "keep",
            "inspect_child_refs": [paragraph_ref],
            "child_decisions": [
                {
                    "target_ref": paragraph_ref,
                    "result": "fill",
                    "confidence": "high",
                    "reason": "complete direct paragraph is one student field",
                    "fill": {"source": "student_content", "field": "note"},
                }
            ],
            "confidence": "high",
            "reason": "only the direct paragraph is fillable",
        }

    trace = run_t3_sparse_traversal(stage_input, decide=decide)

    assert calls == ["unit:cover"]
    assert trace["call_count"] == 1
    filled = [row for row in trace["atomic_coverage"] if row["resolved_result"] == "fill"]
    assert [row["raw_run_ids"] for row in filled] == [["p_0099.r_001"]]
    assert filled[0]["resolution"] == "inherited"
    assert any(
        record.get("source") == "parent_inline_child_decision"
        for record in trace["call_records"]
    )


def test_inline_child_decision_must_reference_an_inspected_direct_child() -> None:
    stage_input = _stage_input()
    root = nodes_by_ref(stage_input)["unit:cover"]

    decision, errors = validate_t3_sparse_decision(
        {
            "target_ref": root["ref"],
            "result": "split",
            "default_child_result": "keep",
            "inspect_child_refs": ["table:tbl_0001"],
            "child_decisions": [
                {
                    "target_ref": "unit:cover/paragraph:p_0099",
                    "result": "fill",
                    "confidence": "high",
                    "fill": {"source": "student_content"},
                }
            ],
            "confidence": "high",
        },
        node=root,
        by_ref=nodes_by_ref(stage_input),
    )

    assert decision["decision_status"] == "manual_review"
    assert any("must also appear" in error["message"] for error in errors)


def test_invalid_cross_level_child_ref_becomes_manual_review_fallback_keep() -> None:
    stage_input = _stage_input()

    def decide(_evidence: dict, node: dict, _unit_id: str) -> dict:
        return _split(node["ref"], ["run:p_0001.r_001"])

    trace = run_t3_sparse_traversal(stage_input, decide=decide)

    decision = trace["decisions"][0]
    assert decision["result"] == "keep"
    assert decision["decision_status"] == "manual_review"
    assert any("not direct children" in error["message"] for error in decision["validation_errors"])
    assert {row["resolution"] for row in trace["atomic_coverage"]} == {"fallback"}


def test_incomplete_table_cannot_terminal_or_split_as_accepted() -> None:
    window = {
        **unit_window(),
        "source_seq_refs": [1, 2],
    }
    stage_input = _stage_input(window)

    def decide(_evidence: dict, node: dict, _unit_id: str) -> dict:
        if node["source_kind"] == "unit":
            return _split(node["ref"], ["table:tbl_0001"])
        return _split(node["ref"], node["child_refs"][:1])

    trace = run_t3_sparse_traversal(stage_input, decide=decide)
    table_decision = next(
        decision for decision in trace["decisions"] if decision["target_ref"] == "table:tbl_0001"
    )

    assert table_decision["decision_status"] == "manual_review"
    assert table_decision["result"] == "keep"
    assert any("children are incomplete" in error["message"] for error in table_decision["validation_errors"])


def test_provider_failure_is_failed_fallback_not_normal_inheritance() -> None:
    stage_input = _stage_input()

    def decide(_evidence: dict, node: dict, _unit_id: str) -> dict:
        if node["source_kind"] == "unit":
            return _split(node["ref"], ["table:tbl_0001"])
        raise TimeoutError("provider timeout")

    trace = run_t3_sparse_traversal(stage_input, decide=decide)
    failure = next(decision for decision in trace["decisions"] if decision["decision_status"] == "failed")
    failed_rows = [row for row in trace["atomic_coverage"] if row["decision_ref"] == failure["decision_ref"]]

    assert "provider timeout" in failure["reason"]
    assert failed_rows
    assert {row["resolution"] for row in failed_rows} == {"fallback"}


def test_call_budget_falls_back_without_a_silent_gap() -> None:
    stage_input = _stage_input()

    trace = run_t3_sparse_traversal(
        stage_input,
        decide=lambda _evidence, node, _unit_id: _split(node["ref"], node["child_refs"]),
        max_calls=1,
    )

    assert trace["validation"]["valid"] is True
    assert trace["call_count"] == 1
    assert any("maximum decision call budget" in decision["reason"] for decision in trace["decisions"])
    assert set(row["member_ref"] for row in trace["atomic_coverage"]) == set(
        nodes_by_ref(stage_input)["unit:cover"]["member_leaf_refs"]
    )


def test_exact_run_delete_requires_high_confidence_and_reason() -> None:
    stage_input = _stage_input()
    by_ref = nodes_by_ref(stage_input)
    run = by_ref["run:p_0001.r_001"]

    decision, errors = validate_t3_sparse_decision(
        {
            "target_ref": run["ref"],
            "result": "delete",
            "confidence": "high",
            "reason": "pure format annotation",
            "delete": {"reason": "independent run only describes formatting"},
        },
        node=run,
        by_ref=by_ref,
    )

    assert errors == []
    assert decision["decision_status"] == "accepted"
    assert decision["result"] == "delete"


def test_run_can_split_to_exact_spans_and_materialize_mixed_run_without_loss() -> None:
    packet = table_packet()
    row = packet["page_text_index"][-1]
    row["text"] = "学号：20XX（填写说明）"
    row["style_details"]["runs"][0]["text"] = row["text"]
    stage_input = build_t3_hierarchical_stage_input(
        packet,
        unit_windows={
            "post_t2_observation_hash": "sha256:t2",
            "windows": [{**unit_window(), "source_seq_refs": [7]}],
        },
    )
    by_ref = nodes_by_ref(stage_input)

    def decide(_evidence: dict, node: dict, _unit_id: str) -> dict:
        if node["source_kind"] in {"unit", "paragraph"}:
            return _split(node["ref"], node["child_refs"])
        if node["source_kind"] == "run":
            child_decisions = []
            for child_ref in node["child_refs"]:
                text = by_ref[child_ref]["facts"]["text"]
                if text == "学号：":
                    child_decisions.append(
                        {"target_ref": child_ref, "result": "keep", "confidence": "high"}
                    )
                elif text == "20XX":
                    child_decisions.append(
                        {
                            "target_ref": child_ref,
                            "result": "fill",
                            "confidence": "high",
                            "fill": {"source": "student_content", "field": "student_id"},
                        }
                    )
                else:
                    child_decisions.append(
                        {
                            "target_ref": child_ref,
                            "result": "delete",
                            "confidence": "high",
                            "delete": {"reason": "inline formatting instruction"},
                        }
                    )
            return {
                **_split(node["ref"], node["child_refs"]),
                "child_decisions": child_decisions,
            }
        raise AssertionError(f"unexpected provider call for {node['ref']}")

    trace = run_t3_sparse_traversal(stage_input, decide=decide)
    observation = materialize_sparse_t3_observation(
        trace,
        packet=packet,
        model="fixture",
        unit_windows={"post_t2_observation_hash": "sha256:t2"},
    )

    assert trace["validation"] == {"valid": True, "errors": []}
    assert {row["resolved_result"] for row in trace["atomic_coverage"]} == {
        "keep",
        "fill",
        "delete",
    }
    assert [row["char_ranges"][0] for row in trace["atomic_coverage"]] == [
        {"raw_run_id": "p_0099.r_001", "start": 0, "end": 3},
        {"raw_run_id": "p_0099.r_001", "start": 3, "end": 7},
        {"raw_run_id": "p_0099.r_001", "start": 7, "end": 13},
    ]
    assert len(observation["items"]) == 1
    item = observation["items"][0]
    assert item["projection_status"] == "mixed_span_actions"
    assert item["core_action"] == "mixed"
    assert item["merge_eligible"] is False
    assert [span["core_action"] for span in item["spans"]] == [
        "keep",
        "fill",
        "delete",
    ]
    assert observation["quality_report"]["mixed_span_run_count"] == 1


def test_sparse_trace_materializes_legacy_items_without_losing_resolution_trace() -> None:
    stage_input = _stage_input()
    trace = run_t3_sparse_traversal(
        stage_input,
        decide=lambda _evidence, node, _unit_id: {
            "target_ref": node["ref"],
            "result": "keep",
            "confidence": "high",
            "reason": "fixed unit",
        },
    )

    observation = materialize_sparse_t3_observation(
        trace,
        packet=table_packet(),
        model="replay",
        unit_windows={"window_source": "gold", "post_t2_observation_hash": "sha256:t2"},
    )

    assert observation["quality_report"]["input_mode"] == "hierarchical_sparse_stop_or_descend"
    assert observation["quality_report"]["resolution_counts"]["inherited"] == 7
    assert len(observation["items"]) == 7
    assert all(item["decision_status"] == "accepted" for item in observation["items"])
    assert all(item["resolution"] == "inherited" for item in observation["items"])
    assert all(item["merge_eligible"] is True for item in observation["items"])
    assert observation["atomic_coverage"] == trace["atomic_coverage"]


def test_manual_review_fallback_is_not_merge_eligible() -> None:
    stage_input = _stage_input()
    trace = run_t3_sparse_traversal(
        stage_input,
        decide=lambda _evidence, _node, _unit_id: {
            "target_ref": "outside:tree",
            "result": "delete",
            "confidence": "low",
        },
    )

    observation = materialize_sparse_t3_observation(
        trace,
        packet=table_packet(),
        model="replay",
        unit_windows={},
    )

    assert observation["quality_report"]["demotions"]
    assert all(item["policy"] == "fixed" for item in observation["items"])
    assert all(item["merge_eligible"] is False for item in observation["items"])


def _split(target_ref: str, child_refs: list[str]) -> dict:
    return {
        "target_ref": target_ref,
        "result": "split",
        "default_child_result": "keep",
        "inspect_child_refs": child_refs,
        "confidence": "high",
        "reason": "mixed actions are limited to selected direct children",
    }
