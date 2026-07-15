from __future__ import annotations

from typing import Any

from docfit.template_generation.agent.observation_config import ObservationConfig
from docfit.template_generation.agent.observation_loop import run_observation_pipeline
from docfit.template_generation.agent.observation_schema import (
    coverage_invariant_errors,
)
from docfit.template_generation.agent.packet import (
    build_template_agent_render_packet,
    packet_source_seq_set,
)

from .helpers import document_facts


def clean_packet() -> dict[str, Any]:
    # 防火墙：structure_candidates={} → round0 结论不进渲染包。
    return build_template_agent_render_packet(
        document_facts=document_facts(),
        structure_candidates={},
    )


def transcript_three_samples() -> dict[str, Any]:
    # helpers 文档 source_seq: 1=封面 2=承诺书 3=学生姓名:____ 4=正文
    # 三样本对 seq1/seq4 一致；seq2 多数 integrity_statement；seq3 分歧→unknown。
    sample_a = {
        "items": [
            {"unit_id": "cover", "source_seq_refs": [1]},
            {"unit_id": "integrity_statement", "source_seq_refs": [2]},
            {"unit_id": "body_main", "source_seq_refs": [3, 4]},
        ]
    }
    sample_b = {
        "items": [
            {"unit_id": "cover", "source_seq_refs": [1]},
            {"unit_id": "integrity_statement", "source_seq_refs": [2]},
            {"unit_id": "body_main", "source_seq_refs": [4]},
        ]
    }
    sample_c = {
        "items": [
            {"unit_id": "cover", "source_seq_refs": [1]},
            {"unit_id": "cover", "source_seq_refs": [2]},
            {"unit_id": "body_main", "source_seq_refs": [4]},
        ]
    }
    return {
        "t2": [sample_a, sample_b, sample_c],
        "t3": {
            "cover": {
                "items": [
                    {
                        "element_id": "cover.001",
                        "policy": "fixed",
                        "role": "template_fixed",
                        "content": "封面",
                        "source_seq_refs": [1],
                    }
                ]
            },
            "body_main": {
                "items": [
                    {
                        "element_id": "body_main.001",
                        "policy": "fill",
                        "fill_source": "student_content",
                        "source_seq_refs": [4],
                    }
                ]
            },
        },
        "t4": {"section_profiles": []},
    }


def test_pipeline_produces_three_observations() -> None:
    packet = clean_packet()
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(enabled=True, self_consistency_samples=3),
    )
    assert bundle["ai_unit_observation"]["artifact_type"] == "ai_unit_observation"
    assert bundle["ai_element_observation"]["artifact_type"] == "ai_element_observation"
    assert bundle["ai_layout_observation"]["artifact_type"] == "ai_layout_observation"


def test_pipeline_self_consistency_resolves_votes() -> None:
    packet = clean_packet()
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(enabled=True, self_consistency_samples=3),
    )
    units = {
        seq: item["unit_id"]
        for item in bundle["ai_unit_observation"]["items"]
        for seq in item["source_seq_refs"]
    }
    assert units.get(1) == "cover"  # 3/3 一致
    assert units.get(2) == "integrity_statement"  # 2/3 多数
    # seq3 分歧（仅 sample_a 给 body_main, 1/3 < 0.5）→ unknown，不进 items。
    assert 3 not in units
    assert 3 in bundle["ai_unit_observation"]["coverage"]["unknown_source_seq"]


def test_pipeline_coverage_invariants_hold_for_all_stages() -> None:
    packet = clean_packet()
    all_seq = packet_source_seq_set(packet)
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(enabled=True, self_consistency_samples=3),
    )
    for key in ("ai_unit_observation", "ai_element_observation", "ai_layout_observation"):
        coverage = bundle[key]["coverage"]
        assert coverage_invariant_errors(coverage, all_source_seq=all_seq) == [], key


def test_pipeline_t3_windows_come_from_ai_units() -> None:
    packet = clean_packet()
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(enabled=True, self_consistency_samples=3),
    )
    assert bundle["unit_windows"]["window_source"] == "ai_unit_observation"
    # T3 元素挂在 AI 自己认出的 cover / body_main 单元上。
    element_units = {item["unit_id"] for item in bundle["ai_element_observation"]["items"]}
    assert element_units <= {"cover", "body_main", "integrity_statement"}


def test_live_capable_t3_responder_plans_object_before_local_elements() -> None:
    packet = clean_packet()
    calls = []

    class HierarchicalResponder:
        def fetch_units(self, *, evidence, n_samples):
            del evidence, n_samples
            return [{"items": [{"unit_id": "cover", "source_seq_refs": [1, 2, 3, 4]}]}]

        def fetch_element_plan(self, *, evidence, task):
            calls.append(("plan", evidence["scope"], task["object_type"]))
            return {
                "object_hypothesis": {
                    "archetype": "cover_title_block",
                    "purpose": "封面内容",
                    "confidence": "high",
                },
                "regions": [],
                "relationship_patterns": [],
                "quality_risks": ["不要保留示例学生内容"],
            }

        def fetch_elements(self, *, evidence, window):
            calls.append(("elements", evidence["scope"], evidence["object_plan"]["object_hypothesis"]["archetype"]))
            return {
                "items": [
                    {
                        "element_id": "cover.001",
                        "policy": "fixed",
                        "source_seq_refs": window["source_seq_refs"],
                        "confidence": "high",
                    }
                ]
            }

        def fetch_layout(self, *, evidence):
            del evidence
            return {"section_profiles": []}

    bundle = run_observation_pipeline(
        packet=packet,
        responder=HierarchicalResponder(),
        config=ObservationConfig(enabled=True, self_consistency_samples=1),
    )

    assert calls[0] == ("plan", "t3_object_overview", "text_flow")
    assert calls[1] == ("elements", "t3_object_local_window", "cover_title_block")
    t3 = bundle["ai_element_observation"]
    assert t3["quality_report"]["input_mode"] == "object_plan_then_local"
    assert t3["quality_report"]["object_count"] == 1
    assert t3["object_analysis"][0]["object_plan"]["object_hypothesis"]["archetype"] == "cover_title_block"


def test_hierarchical_t3_splits_failed_json_window_and_retries_smaller_scopes() -> None:
    packet = clean_packet()
    attempted = []

    class RetryResponder:
        def fetch_units(self, *, evidence, n_samples):
            del evidence, n_samples
            return [{"items": [{"unit_id": "cover", "source_seq_refs": [1, 2, 3, 4]}]}]

        def fetch_element_plan(self, *, evidence, task):
            del evidence, task
            return {"object_hypothesis": {"archetype": "cover", "confidence": "high"}}

        def fetch_elements(self, *, evidence, window):
            del evidence
            attempted.append((window["window_id"], list(window["source_seq_refs"])))
            if ":retry_" not in window["window_id"]:
                return {"items": [], "_observation_error": "invalid JSON"}
            return {
                "items": [
                    {
                        "element_id": window["window_id"],
                        "policy": "fixed",
                        "source_seq_refs": window["source_seq_refs"],
                        "confidence": "high",
                    }
                ]
            }

        def fetch_layout(self, *, evidence):
            del evidence
            return {"section_profiles": []}

    bundle = run_observation_pipeline(
        packet=packet,
        responder=RetryResponder(),
        config=ObservationConfig(enabled=True, self_consistency_samples=1),
    )

    assert attempted[0][1] == [1, 2, 3, 4]
    assert attempted[1][1] == [1, 2]
    assert attempted[2][1] == [3, 4]
    analysis = bundle["ai_element_observation"]["object_analysis"][0]
    assert len(analysis["executed_local_windows"]) == 2
    assert bundle["ai_element_observation"]["coverage"]["owned_source_seq"] == [1, 2, 3, 4]


def test_pipeline_t4_abstains_without_real_render() -> None:
    packet = clean_packet()
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(enabled=True, self_consistency_samples=3),
    )
    assert bundle["ai_layout_observation"]["abstain"] is True
