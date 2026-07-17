from __future__ import annotations

from typing import Any

import pytest

from docfit.core.io import read_json, write_json, write_yaml
from docfit.template_generation.agent.config import AgentConfig, AgentConfigError
from docfit.template_generation.agent import observation_orchestrate
from docfit.template_generation.agent.observation_config import ObservationConfig
from docfit.template_generation.agent.observation_loop import (
    run_observation_pipeline,
    run_t4_observation,
)
from docfit.template_generation.agent.observation_schema import (
    coverage_invariant_errors,
)
from docfit.template_generation.agent.packet import (
    build_template_agent_render_packet,
    packet_source_seq_set,
)
from docfit.template_generation.input_contract import build_l1_input_contract

from .helpers import document_facts


def clean_packet() -> dict[str, Any]:
    # 防火墙：structure_candidates={} → round0 结论不进渲染包。
    return build_template_agent_render_packet(
        document_facts=document_facts(),
        structure_candidates={},
    )


def write_l1_stage_input(run_dir, packet: dict[str, Any]) -> None:
    write_json(
        run_dir / "01.5_l1_input_contract.json",
        build_l1_input_contract(
            document_facts=document_facts(),
            render_packet=packet,
        ),
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


def test_live_capable_t3_responder_routes_unit_before_local_elements() -> None:
    packet = clean_packet()
    calls = []

    class UnitRoutedResponder:
        def fetch_units(self, *, evidence, n_samples):
            del evidence, n_samples
            return [{"items": [{"unit_id": "cover", "source_seq_refs": [1, 2, 3, 4]}]}]

        def fetch_unit_plan(self, *, evidence, window):
            calls.append(("unit", evidence["scope"], window["unit_id"]))
            return {
                "route": "full_local_analysis",
                "default_preservation_policy": "fixed",
                "inspect_source_seq_refs": [1, 2, 3, 4],
                "confidence": "high",
            }

        def fetch_elements(self, *, evidence, window):
            calls.append(("elements", evidence["scope"], evidence["unit_plan"]["route"]))
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
        responder=UnitRoutedResponder(),
        config=ObservationConfig(enabled=True, self_consistency_samples=1),
    )

    assert calls[0] == ("unit", "t3_unit_overview", "cover")
    assert calls[1] == ("elements", "t3_local_window", "full_local_analysis")
    t3 = bundle["ai_element_observation"]
    assert t3["quality_report"]["input_mode"] == "unit_route_then_conditional_local"
    assert t3["quality_report"]["local_task_count"] == 1
    assert t3["local_task_analysis"][0]["object_type"] == "text_flow"


def test_hierarchical_t3_splits_failed_json_window_and_retries_smaller_scopes() -> None:
    packet = clean_packet()
    attempted = []

    class RetryResponder:
        def fetch_units(self, *, evidence, n_samples):
            del evidence, n_samples
            return [{"items": [{"unit_id": "cover", "source_seq_refs": [1, 2, 3, 4]}]}]

        def fetch_unit_plan(self, *, evidence, window):
            del evidence, window
            return {
                "route": "full_local_analysis",
                "default_preservation_policy": "fixed",
                "confidence": "high",
            }

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
    analysis = bundle["ai_element_observation"]["local_task_analysis"][0]
    assert len(analysis["executed_local_windows"]) == 2
    assert bundle["ai_element_observation"]["coverage"]["owned_source_seq"] == [1, 2, 3, 4]


def test_unit_routed_t3_short_circuits_local_calls_and_preserves_complete_unit() -> None:
    packet = clean_packet()
    calls = []

    class UnitRoutedResponder:
        def fetch_units(self, *, evidence, n_samples):
            del evidence, n_samples
            return [{"items": [{"unit_id": "cover", "source_seq_refs": [1, 2, 3, 4]}]}]

        def fetch_unit_plan(self, *, evidence, window):
            calls.append(("unit", evidence["scope"], window["unit_id"]))
            return {
                "route": "preserve_whole",
                "default_preservation_policy": "fixed",
                "confidence": "high",
                "rationale": "整个测试单元作为完整内容保留",
            }

        def fetch_elements(self, *, evidence, window):
            raise AssertionError("preserve_whole must not call local element model")

    bundle = run_observation_pipeline(
        packet=packet,
        responder=UnitRoutedResponder(),
        config=ObservationConfig(enabled=True, self_consistency_samples=1),
    )

    t3 = bundle["ai_element_observation"]
    assert calls == [("unit", "t3_unit_overview", "cover")]
    assert t3["quality_report"]["input_mode"] == "unit_route_then_conditional_local"
    assert t3["quality_report"]["route_counts"] == {"preserve_whole": 1}
    assert t3["coverage"]["owned_source_seq"] == [1, 2, 3, 4]
    assert all(item["policy"] == "fixed" for item in t3["items"])


def test_pipeline_t4_abstains_without_real_render() -> None:
    packet = clean_packet()
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(enabled=True, self_consistency_samples=3),
    )
    assert bundle["ai_layout_observation"]["abstain"] is True


def test_t4_stage_calls_vision_responder_when_real_render_is_available() -> None:
    packet = clean_packet()
    packet["render_status"] = "real_render"
    packet["render_artifacts"]["clean_page_images"] = [
        {"page_no": 1, "path": "/tmp/page-1.png", "sha256": "sha256:test"}
    ]
    calls = []

    class FakeVisionResponder:
        def observe_pages(self, pages):
            calls.extend(pages)
            return [
                {
                    "page_no": 1,
                    "has_header": False,
                    "has_footer": True,
                    "page_number_visible": True,
                    "page_number_text": "1",
                }
            ]

    observation, evidence = run_t4_observation(
        packet=packet,
        config=ObservationConfig(enabled=True, model="minimax-test"),
        vision_responder=FakeVisionResponder(),
    )

    assert evidence["render_available"] is True
    assert len(calls) == 1
    assert "layout_context" in calls[0]
    assert observation["vision_source"] == "minimax_m3"
    assert observation["page_observations"][0]["page_number_text"] == "1"


def test_full_live_observation_wires_text_and_vision_apis(monkeypatch) -> None:
    packet = clean_packet()
    text_responder = object()
    vision_responder = object()
    captured = {}

    monkeypatch.setattr(
        observation_orchestrate,
        "_build_live_text_responder",
        lambda **_kwargs: (text_responder, "kimi-test"),
    )
    monkeypatch.setattr(
        observation_orchestrate,
        "_build_live_vision_responder",
        lambda **_kwargs: (vision_responder, "minimax-test"),
    )

    def fake_run_observation_pipeline(**kwargs):
        captured.update(kwargs)
        return {"artifact_type": "ai_observation_bundle"}

    monkeypatch.setattr(
        observation_orchestrate,
        "run_observation_pipeline",
        fake_run_observation_pipeline,
    )

    result = observation_orchestrate.run_module1_observation_for_template_generate(
        packet=packet,
        agent_config=AgentConfig(enabled=True, observation_mode="live"),
    )

    assert result["artifact_type"] == "ai_observation_bundle"
    assert result["api_trace_summary"]["mode"] == "live"
    assert result["api_trace_summary"]["providers"] == ["kimi", "minimax"]
    assert result["api_trace_summary"]["models"] == {
        "text": "kimi-test",
        "vision": "minimax-test",
    }
    assert captured["responder"] is text_responder
    assert captured["vision_responder"] is vision_responder


def test_standalone_t3_auto_runs_live_t2_before_t3(monkeypatch, tmp_path) -> None:
    packet = clean_packet()
    calls = []

    class FakeTextResponder:
        def __init__(self, record):
            self._record = record

        def fetch_units(self, *, evidence, n_samples):
            calls.append(("t2", evidence["scope"], n_samples))
            self._record.append({"stage": "t2", "payload": {}, "error": None})
            return [
                {
                    "items": [
                        {"unit_id": "cover", "source_seq_refs": [1]},
                        {"unit_id": "body_main", "source_seq_refs": [2, 3, 4]},
                    ]
                }
            ]

        def fetch_unit_plan(self, *, evidence, window):
            del evidence
            return {
                "route": "full_local_analysis",
                "default_preservation_policy": "fixed",
                "inspect_source_seq_refs": list(window["source_seq_refs"]),
                "confidence": "high",
            }

        def fetch_elements(self, *, evidence, window):
            calls.append(("t3", window["unit_id"], evidence["scope"]))
            self._record.append({"stage": "t3", "payload": {}, "error": None})
            return {
                "items": [
                    {
                        "element_id": f"{window['unit_id']}.001",
                        "policy": "fixed",
                        "source_seq_refs": window["source_seq_refs"],
                    }
                ]
            }

    monkeypatch.setattr(
        observation_orchestrate,
        "inspect_document_facts_docx",
        lambda _path: {},
    )
    monkeypatch.setattr(
        observation_orchestrate,
        "build_template_agent_render_packet",
        lambda **_kwargs: packet,
    )
    monkeypatch.setattr(
        observation_orchestrate,
        "build_agent_stage_packet",
        lambda _l1: packet,
    )
    monkeypatch.setattr(
        observation_orchestrate,
        "_build_live_text_responder",
        lambda **kwargs: (FakeTextResponder(kwargs["record"]), "kimi-test"),
    )

    source = tmp_path / "template.docx"
    source.touch()
    out_dir = tmp_path / "observe-t3"
    summary = observation_orchestrate.run_live_template_observation_stage(
        source_template_docx=source,
        out_dir=out_dir,
        stage="t3",
    )

    assert summary["llm_mode"] == "live_api"
    assert summary["auto_ran_t2"] is True
    assert calls[0][0] == "t2"
    assert [call[0] for call in calls[1:]] == ["t3", "t3"]
    assert (out_dir / "02.2_t2_ai_unit_observation.yaml").exists()
    assert (out_dir / "03.1_t3_ai_element_observation.yaml").exists()
    assert (out_dir / "summary.json").exists()


def test_standalone_t4_fails_before_api_when_real_render_is_missing(
    monkeypatch,
    tmp_path,
) -> None:
    packet = clean_packet()
    monkeypatch.setattr(
        observation_orchestrate,
        "inspect_document_facts_docx",
        lambda _path: {},
    )
    monkeypatch.setattr(
        observation_orchestrate,
        "build_template_agent_render_packet",
        lambda **_kwargs: packet,
    )
    monkeypatch.setattr(
        observation_orchestrate,
        "_build_live_vision_responder",
        lambda: pytest.fail("T4 must not claim an API call without real page images"),
    )

    source = tmp_path / "template.docx"
    source.touch()
    with pytest.raises(AgentConfigError, match="requires real rendered page images"):
        observation_orchestrate.run_live_template_observation_stage(
            source_template_docx=source,
            out_dir=tmp_path / "observe-t4",
            stage="t4",
        )


def test_run_backed_t3_requires_pinned_upstream_without_explicit_bootstrap(
    tmp_path,
) -> None:
    run_dir = tmp_path / "template-run"
    run_dir.mkdir()
    write_l1_stage_input(run_dir, clean_packet())
    replay_path = tmp_path / "replay.json"
    write_json(replay_path, transcript_three_samples())

    with pytest.raises(AgentConfigError, match="requires a pinned T2 artifact"):
        observation_orchestrate.run_template_observation_stage(
            source_run_dir=run_dir,
            out_dir=tmp_path / "t3-debug",
            stage="t3",
            ai_mode="replay",
            replay_path=replay_path,
        )


def test_run_backed_t3_reuses_pinned_t2_and_writes_provenance(tmp_path) -> None:
    packet = clean_packet()
    run_dir = tmp_path / "template-run"
    run_dir.mkdir()
    write_l1_stage_input(run_dir, packet)
    write_json(
        run_dir / "01_document_facts.json",
        {"metadata": {"source_template_hash": "sha256:source-template"}},
    )
    write_yaml(
        run_dir / "02.2_t2_ai_unit_observation.yaml",
        {
            "artifact_type": "ai_unit_observation",
            "source_render_hash": packet["source_render_hash"],
            "route": {"route_id": "ai_raw", "availability": "AVAILABLE"},
            "items": [
                {"unit_id": "cover", "source_seq_refs": [1]},
                {"unit_id": "body_main", "source_seq_refs": [2, 3, 4]},
            ],
        },
    )
    replay_path = tmp_path / "replay.json"
    write_json(replay_path, transcript_three_samples())
    before = {
        path.name: path.read_bytes()
        for path in run_dir.iterdir()
        if path.is_file()
    }
    out_dir = tmp_path / "t3-debug"

    summary = observation_orchestrate.run_template_observation_stage(
        source_run_dir=run_dir,
        out_dir=out_dir,
        stage="t3",
        ai_mode="replay",
        replay_path=replay_path,
    )

    assert summary["source_kind"] == "run"
    assert summary["ran_upstream_t2"] is False
    assert summary["api_call_count"] == 0
    assert summary["upstream_artifacts"]["t2"]["sha256"]
    manifest = read_json(out_dir / "run_manifest.json")
    assert manifest["command"] == "template stage t3"
    assert manifest["source_render_hash"] == packet["source_render_hash"]
    assert manifest["source_template_hash"] == "sha256:source-template"
    assert manifest["upstream_artifacts"]["t2"]["path"].endswith(
        "02.2_t2_ai_unit_observation.yaml"
    )
    after = {
        path.name: path.read_bytes()
        for path in run_dir.iterdir()
        if path.is_file()
    }
    assert after == before


def test_t3_with_upstream_makes_bootstrap_explicit_in_manifest(tmp_path) -> None:
    packet = clean_packet()
    run_dir = tmp_path / "template-run"
    run_dir.mkdir()
    write_l1_stage_input(run_dir, packet)
    replay_path = tmp_path / "replay.json"
    write_json(replay_path, transcript_three_samples())
    out_dir = tmp_path / "t3-debug"

    summary = observation_orchestrate.run_template_observation_stage(
        source_run_dir=run_dir,
        out_dir=out_dir,
        stage="t3",
        ai_mode="replay",
        replay_path=replay_path,
        with_upstream=True,
    )

    assert summary["ran_upstream_t2"] is True
    assert (out_dir / "02.2_t2_ai_unit_observation.yaml").exists()
    manifest = read_json(out_dir / "run_manifest.json")
    assert manifest["ran_upstream_t2"] is True
    assert manifest["upstream_artifacts"]["t2"]["sha256"]
