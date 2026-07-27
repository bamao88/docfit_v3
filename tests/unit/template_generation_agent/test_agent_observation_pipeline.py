from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

import pytest

from docfit.core.io import read_json, sha256_file, sha256_json, write_json, write_yaml
from docfit.template_generation.agent.api_config import LiveProviderUsageLimitState
from docfit.template_generation.agent.config import AgentConfig, AgentConfigError
from docfit.template_generation.agent import (
    observation_loop,
    observation_providers,
    observation_runtime,
    observation_stage,
    observation_vision,
)
from docfit.template_generation.agent.observation_config import ObservationConfig
from docfit.template_generation.agent.observation_loop import (
    run_observation_pipeline,
    run_t2_observation,
    run_t4_observation,
)
from docfit.template_generation.agent.observation_schema import (
    coverage_invariant_errors,
)
from docfit.template_generation.agent.packet import (
    build_template_agent_render_packet,
    packet_source_seq_set,
)
from docfit.template_generation.final_results import publish_final_stage_result
from docfit.template_generation.input_contract import build_l1_input_contract
from docfit.template_generation.stage_inputs import l1_artifact_hash
from docfit.template_generation.t2_ai import T2AIContractError

from .helpers import document_facts


def clean_packet() -> dict[str, Any]:
    packet = build_template_agent_render_packet(
        document_facts=document_facts(),
    )
    image_path = Path(tempfile.mkdtemp()) / "page-1.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    packet["render_status"] = "real_render"
    packet["source_render_hash"] = "sha256:render"
    packet["render_artifacts"] = {
        "page_count": 1,
        "clean_page_images": [
            {
                "page_no": 1,
                "path": str(image_path),
                "sha256": sha256_file(image_path),
            }
        ],
    }
    for row in packet.get("page_text_index", []):
        row["page_no"] = 1
        row["render_binding_status"] = "exact"
    return packet


def write_l1_stage_input(run_dir, packet: dict[str, Any]) -> None:
    write_json(
        run_dir / "01.5_l1_input_contract.json",
        build_l1_input_contract(
            document_facts=document_facts(),
            render_packet=packet,
        ),
    )


def transcript_three_samples() -> dict[str, Any]:
    sample = {
        "units": [
            {
                "unit_id": "cover_and_template_content",
                "unit_name": "封面及模板内容",
                "boundary": {"start_page": 1, "end_page": 1},
            }
        ]
    }
    return {
        "t2": [sample],
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
        config=ObservationConfig(),
    )
    assert bundle["ai_unit_observation"]["artifact_type"] == "ai_unit_observation"
    assert bundle["ai_element_observation"]["artifact_type"] == "ai_element_observation"
    assert bundle["ai_layout_observation"]["artifact_type"] == "ai_layout_observation"


def test_pipeline_t2_uses_one_page_native_ai_output() -> None:
    packet = clean_packet()
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(),
    )
    assert bundle["ai_unit_observation"]["units"] == (
        transcript_three_samples()["t2"][0]["units"]
    )
    assert bundle["quality_report"]["self_consistency"] == {
        "samples": 1,
        "mode": "single_ai_output",
    }


def test_t2_rejects_unresolved_page_binding_before_responder_call() -> None:
    packet = clean_packet()
    packet["page_text_index"][0]["render_binding_status"] = "ambiguous"
    calls = 0

    class CountingResponder:
        def fetch_units(self, *, evidence, n_samples):
            nonlocal calls
            del evidence, n_samples
            calls += 1
            return []

    with pytest.raises(T2AIContractError, match="page binding is unresolved"):
        run_t2_observation(
            packet=packet,
            responder=CountingResponder(),
            config=ObservationConfig(),
        )

    assert calls == 0


def test_pipeline_coverage_invariants_hold_for_all_stages() -> None:
    packet = clean_packet()
    all_seq = packet_source_seq_set(packet)
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(),
    )
    assert bundle["ai_unit_observation"]["validation"][
        "complete_page_coverage"
    ]
    for key in ("ai_element_observation", "ai_layout_observation"):
        coverage = bundle[key]["coverage"]
        assert coverage_invariant_errors(coverage, all_source_seq=all_seq) == [], key


def test_pipeline_t3_stage_input_binds_the_single_final_t2_result() -> None:
    packet = clean_packet()
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(),
    )
    stage_input = bundle["t3_hierarchical_stage_input"]
    assert stage_input["contract"]["t2_final_hash"] == sha256_json(
        bundle["t2_final_result"]
    )
    assert bundle["t2_final_result"]["result_role"] == "final"
    assert "unit_windows" not in bundle
    # T3 元素挂在 AI 最终页面组上。
    element_units = {item["unit_id"] for item in bundle["ai_element_observation"]["items"]}
    assert element_units <= {"cover_and_template_content"}


def test_pipeline_t3_uses_published_t2_final_when_ai_candidate_differs(
    monkeypatch,
) -> None:
    packet = clean_packet()

    def publish_different_final(
        _observation: dict[str, Any],
        *,
        packet: dict[str, Any],
    ):
        del packet
        return publish_final_stage_result(
            {
                "artifact_type": "unit_map",
                "units": [
                    {
                        "unit_id": "body_main",
                        "source_seq_refs": [4],
                    }
                ],
            },
            stage_id="T2",
            artifact_type="unit_map",
            artifact_name="02_unit_map.yaml",
            producer_mode="fixture_finalizer",
        )

    monkeypatch.setattr(
        observation_loop,
        "publish_t2_ai_final",
        publish_different_final,
    )
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(),
    )

    assert {
        item["unit_id"] for item in bundle["ai_unit_observation"]["units"]
    } != {"body_main"}
    assert [
        root["unit_id"]
        for root in bundle["t3_hierarchical_stage_input"]["unit_roots"]
    ] == ["body_main"]


def test_live_capable_t3_responder_routes_from_unit_to_direct_children() -> None:
    packet = clean_packet()
    calls = []

    class UnitRoutedResponder:
        def fetch_units(self, *, evidence, n_samples):
            del evidence, n_samples
            return [
                {
                    "units": [
                        {
                            "unit_id": "cover",
                            "unit_name": "封面",
                            "boundary": {"start_page": 1, "end_page": 1},
                        }
                    ]
                }
            ]

        def fetch_t3_decision(self, *, evidence, node, unit_id):
            calls.append((node["source_kind"], evidence["scope"], unit_id))
            if node["child_refs"]:
                return {
                    "target_ref": node["ref"],
                    "result": "split",
                    "default_child_result": "keep",
                    "inspect_child_refs": node["child_refs"],
                    "confidence": "high",
                    "reason": "inspect every direct child in this fixture",
                }
            return {
                "target_ref": node["ref"],
                "result": "keep",
                "confidence": "high",
                "reason": "atomic fixed content",
            }

        def fetch_layout(self, *, evidence):
            del evidence
            return {"section_profiles": []}

    bundle = run_observation_pipeline(
        packet=packet,
        responder=UnitRoutedResponder(),
        config=ObservationConfig(),
    )

    assert calls[0] == ("unit", "t3_hierarchical_node", "cover")
    assert calls[1][0] == "paragraph"
    t3 = bundle["ai_element_observation"]
    assert t3["quality_report"]["input_mode"] == "hierarchical_sparse_stop_or_descend"
    assert t3["quality_report"]["decision_call_count"] == len(calls)
    assert t3["quality_report"]["resolution_counts"]["direct"] == 4


def test_hierarchical_t3_records_failed_node_as_fallback_without_descending() -> None:
    packet = clean_packet()
    attempted = []

    class RetryResponder:
        def fetch_units(self, *, evidence, n_samples):
            del evidence, n_samples
            return [
                {
                    "units": [
                        {
                            "unit_id": "cover",
                            "unit_name": "封面",
                            "boundary": {"start_page": 1, "end_page": 1},
                        }
                    ]
                }
            ]

        def fetch_t3_decision(self, *, evidence, node, unit_id):
            del evidence, unit_id
            attempted.append(node["ref"])
            if node["source_kind"] == "unit":
                return {
                    "target_ref": node["ref"],
                    "result": "split",
                    "default_child_result": "keep",
                    "inspect_child_refs": node["child_refs"],
                    "confidence": "high",
                    "reason": "inspect paragraph children",
                }
            return {
                "_observation_error": "invalid JSON",
            }

        def fetch_layout(self, *, evidence):
            del evidence
            return {"section_profiles": []}

    bundle = run_observation_pipeline(
        packet=packet,
        responder=RetryResponder(),
        config=ObservationConfig(),
    )

    assert attempted == [
        "unit:cover",
        "unit:cover/paragraph:p_0001",
        "unit:cover/paragraph:p_0002",
        "unit:cover/paragraph:p_0003",
        "unit:cover/paragraph:p_0004",
    ]
    t3 = bundle["ai_element_observation"]
    assert t3["quality_report"]["resolution_counts"]["fallback"] == 4
    assert any(record["status"] == "failed" for record in t3["sparse_call_records"])
    assert bundle["ai_element_observation"]["coverage"]["owned_source_seq"] == [1, 2, 3, 4]


def test_unit_routed_t3_short_circuits_local_calls_and_preserves_complete_unit() -> None:
    packet = clean_packet()
    calls = []

    class UnitRoutedResponder:
        def fetch_units(self, *, evidence, n_samples):
            del evidence, n_samples
            return [
                {
                    "units": [
                        {
                            "unit_id": "cover",
                            "unit_name": "封面",
                            "boundary": {"start_page": 1, "end_page": 1},
                        }
                    ]
                }
            ]

        def fetch_t3_decision(self, *, evidence, node, unit_id):
            calls.append((node["source_kind"], evidence["scope"], unit_id))
            return {
                "target_ref": node["ref"],
                "result": "keep",
                "confidence": "high",
                "reason": "整个测试单元作为完整内容保留",
            }

        def fetch_layout(self, *, evidence):
            del evidence
            return {"section_profiles": []}

    bundle = run_observation_pipeline(
        packet=packet,
        responder=UnitRoutedResponder(),
        config=ObservationConfig(),
    )

    t3 = bundle["ai_element_observation"]
    assert calls == [("unit", "t3_hierarchical_node", "cover")]
    assert t3["quality_report"]["input_mode"] == "hierarchical_sparse_stop_or_descend"
    assert t3["quality_report"]["resolution_counts"] == {
        "direct": 0,
        "inherited": 4,
        "fallback": 0,
        "contested": 0,
    }
    assert t3["coverage"]["owned_source_seq"] == [1, 2, 3, 4]
    assert all(item["policy"] == "fixed" for item in t3["items"])


def test_pipeline_t4_abstains_when_ai_returns_no_layout_decision() -> None:
    packet = clean_packet()
    bundle = run_observation_pipeline(
        packet=packet,
        transcript=transcript_three_samples(),
        config=ObservationConfig(),
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
        config=ObservationConfig(model="minimax-test"),
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
    provider_states = {}

    def fake_build_text(**kwargs):
        provider_states["text"] = kwargs["usage_limit_state"]
        return text_responder, "minimax-text-test"

    def fake_build_vision(**kwargs):
        provider_states["vision"] = kwargs["usage_limit_state"]
        return vision_responder, "minimax-test"

    monkeypatch.setattr(
        observation_runtime,
        "build_live_text_responder",
        fake_build_text,
    )
    monkeypatch.setattr(
        observation_runtime,
        "build_live_vision_responder",
        fake_build_vision,
    )

    def fake_run_observation_pipeline(**kwargs):
        captured.update(kwargs)
        return {"artifact_type": "ai_observation_bundle"}

    monkeypatch.setattr(
        observation_runtime,
        "run_observation_pipeline",
        fake_run_observation_pipeline,
    )

    result = observation_runtime.run_module1_observation_for_template_generate(
        packet=packet,
        agent_config=AgentConfig(enabled=True, observation_mode="live"),
    )

    assert result["artifact_type"] == "ai_observation_bundle"
    assert result["api_trace_summary"]["mode"] == "live"
    assert result["api_trace_summary"]["providers"] == ["minimax"]
    assert result["api_trace_summary"]["models"] == {
        "text": "minimax-text-test",
        "vision": "minimax-test",
    }
    assert captured["responder"] is text_responder
    assert captured["vision_responder"] is vision_responder
    assert provider_states["text"] is provider_states["vision"]


def test_minimax_usage_limit_falls_back_to_kimi_for_t3() -> None:
    calls: list[tuple[str, str]] = []

    class Primary:
        def fetch_t3_decision(self, *, evidence, node, unit_id):
            del evidence, node, unit_id
            calls.append(("minimax", "t3_hierarchy"))
            return {
                "_observation_error": (
                    "MinimaxVisionError: minimax 403: usage limit exhausted"
                ),
            }

    class Fallback:
        def fetch_t3_decision(self, *, evidence, node, unit_id):
            del evidence, unit_id
            calls.append(("kimi", "t3_hierarchy"))
            return {
                "target_ref": node["ref"],
                "result": "keep",
                "confidence": "medium",
                "reason": "fallback",
            }

    responder = observation_providers.UsageLimitFallbackTextResponder(
        Primary(),
        Fallback(),
    )

    assert responder.fetch_t3_decision(
        evidence={},
        node={"ref": "unit:cover"},
        unit_id="cover",
    ) == {
        "target_ref": "unit:cover",
        "result": "keep",
        "confidence": "medium",
        "reason": "fallback",
    }
    assert calls == [
        ("minimax", "t3_hierarchy"),
        ("kimi", "t3_hierarchy"),
    ]


def test_non_quota_minimax_error_does_not_switch_provider() -> None:
    calls: list[str] = []

    class Primary:
        def fetch_t3_decision(self, *, evidence, node, unit_id):
            del evidence, node, unit_id
            calls.append("minimax")
            return {
                "_observation_error": "JSONDecodeError: invalid response",
            }

    class Fallback:
        def fetch_t3_decision(self, *, evidence, node, unit_id):
            del evidence, node, unit_id
            calls.append("kimi")
            return {"result": "keep"}

    responder = observation_providers.UsageLimitFallbackTextResponder(
        Primary(),
        Fallback(),
    )

    payload = responder.fetch_t3_decision(
        evidence={},
        node={"ref": "unit:cover"},
        unit_id="cover",
    )

    assert payload["_observation_error"].startswith("JSONDecodeError")
    assert calls == ["minimax"]


def test_minimax_usage_limit_stops_internal_retries(monkeypatch) -> None:
    calls = 0
    record: list[dict[str, Any]] = []

    def fail_with_quota(**_kwargs):
        nonlocal calls
        calls += 1
        raise observation_vision.MinimaxVisionError(
            "minimax 403: usage limit exhausted for billing cycle"
        )

    monkeypatch.setattr(
        observation_vision,
        "post_anthropic_messages",
        fail_with_quota,
    )
    responder = observation_vision.MinimaxTextResponder(
        api_key="test",
        base_url="https://example.invalid",
        model="MiniMax-M3",
        max_attempts=3,
        retry_backoff=0,
        record=record,
        progress=False,
    )

    payload = responder.fetch_t3_decision(
        evidence={},
        node={"ref": "unit:toc"},
        unit_id="toc",
    )
    second_payload = responder.fetch_t3_decision(
        evidence={},
        node={"ref": "unit:body_main"},
        unit_id="body_main",
    )

    assert calls == 1
    assert "usage limit exhausted" in payload["_observation_error"]
    assert second_payload["_observation_error"] == (
        "minimax usage limit already exhausted"
    )
    assert record[0]["provider"] == "minimax"


def test_t4_usage_limit_opens_circuit_and_returns_unknown_pages(
    monkeypatch,
    tmp_path,
) -> None:
    calls = 0
    record: list[dict[str, Any]] = []
    page_1 = tmp_path / "page-1.png"
    page_2 = tmp_path / "page-2.png"
    page_1.write_bytes(b"page-1")
    page_2.write_bytes(b"page-2")

    def fail_with_quota(_prompt, _img_b64):
        nonlocal calls
        calls += 1
        raise observation_vision.MinimaxVisionError(
            "minimax quota exceeded for billing cycle"
        )

    responder = observation_vision.MinimaxVisionResponder(
        api_key="test",
        base_url="https://example.invalid",
        model="MiniMax-M3",
        concurrency=1,
        max_attempts=3,
        retry_backoff=0,
        record=record,
        progress=False,
    )
    monkeypatch.setattr(responder, "_call", fail_with_quota)

    observations = responder.observe_pages(
        [
            {"page_no": 1, "path": str(page_1), "sha256": "sha256:1"},
            {"page_no": 2, "path": str(page_2), "sha256": "sha256:2"},
        ]
    )

    assert calls == 1
    assert observations[0]["has_header"] is None
    assert observations[1]["has_header"] is None
    assert "quota exceeded" in observations[0]["error"]
    assert observations[1]["error"] == "minimax usage limit already exhausted"
    assert record[1]["skipped_due_usage_limit"] is True


def test_t4_uses_cache_before_shared_minimax_circuit(monkeypatch, tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    state = LiveProviderUsageLimitState()
    page = tmp_path / "page.png"
    page.write_bytes(b"page")
    page_input = {"page_no": 1, "path": str(page), "sha256": "sha256:page"}

    warm_responder = observation_vision.MinimaxVisionResponder(
        api_key="test",
        base_url="https://example.invalid",
        model="MiniMax-M3",
        concurrency=1,
        cache_dir=cache_dir,
        usage_limit_state=state,
        progress=False,
    )
    monkeypatch.setattr(
        warm_responder,
        "_call",
        lambda _prompt, _img_b64: '{"has_header": true}',
    )
    assert warm_responder.observe_pages([page_input])[0]["has_header"] is True
    state.mark_exhausted("minimax")

    cached_responder = observation_vision.MinimaxVisionResponder(
        api_key="test",
        base_url="https://example.invalid",
        model="MiniMax-M3",
        concurrency=1,
        cache_dir=cache_dir,
        usage_limit_state=state,
        progress=False,
    )
    monkeypatch.setattr(
        cached_responder,
        "_call",
        lambda _prompt, _img_b64: pytest.fail("cached page must not call API"),
    )

    assert cached_responder.observe_pages([page_input])[0]["has_header"] is True


def test_api_trace_reports_usage_limit_fallback() -> None:
    summary = observation_providers.api_trace_summary(
        mode="live",
        text_record=[
            {
                "stage": "t3",
                "provider": "minimax",
                "error": "usage limit exhausted",
            },
            {
                "stage": "t3",
                "provider": "kimi",
                "fallback_from": "minimax",
                "error": None,
            },
        ],
        providers=["minimax"],
    )

    assert summary["providers"] == ["minimax", "kimi"]
    assert summary["fallback_used"] is True
    assert summary["failures"][0]["provider"] == "minimax"
    assert summary["request_count"] == 2
    assert summary["api_call_count"] == 2


def test_api_trace_does_not_count_cache_or_circuit_skip_as_network_call() -> None:
    summary = observation_providers.api_trace_summary(
        mode="live",
        text_record=[
            {"stage": "t3", "provider": "minimax", "from_cache": True},
            {
                "stage": "t3",
                "provider": "minimax",
                "skipped_due_usage_limit": True,
                "error": "minimax usage limit already exhausted",
            },
            {"stage": "t3", "provider": "kimi", "error": None},
        ],
        providers=["minimax"],
    )

    assert summary["request_count"] == 3
    assert summary["api_call_count"] == 1
    assert summary["cache_hit_count"] == 1
    assert summary["skipped_usage_limit_count"] == 1


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
                    "units": [
                        {
                            "unit_id": "cover_and_template_content",
                            "unit_name": "封面及模板内容",
                            "boundary": {"start_page": 1, "end_page": 1},
                        }
                    ]
                }
            ]

        def fetch_t3_decision(self, *, evidence, node, unit_id):
            calls.append(("t3", unit_id, evidence["scope"]))
            self._record.append({"stage": "t3_hierarchy", "payload": {}, "error": None})
            return {
                "target_ref": node["ref"],
                "result": "keep",
                "confidence": "high",
                "reason": "fixed unit fixture",
            }

    monkeypatch.setattr(
        observation_stage,
        "inspect_document_facts_docx",
        lambda _path: {},
    )
    monkeypatch.setattr(
        observation_stage,
        "build_template_agent_render_packet",
        lambda **_kwargs: packet,
    )
    monkeypatch.setattr(
        observation_stage,
        "build_agent_stage_packet",
        lambda _l1: packet,
    )
    monkeypatch.setattr(
        observation_stage,
        "build_live_text_responder",
        lambda **kwargs: (FakeTextResponder(kwargs["record"]), "kimi-test"),
    )

    source = tmp_path / "template.docx"
    source.touch()
    out_dir = tmp_path / "observe-t3"
    summary = observation_stage.run_live_template_observation_stage(
        source_template_docx=source,
        out_dir=out_dir,
        stage="t3",
    )

    assert summary["llm_mode"] == "live_api"
    assert summary["auto_ran_t2"] is True
    assert calls[0][0] == "t2"
    assert [call[0] for call in calls[1:]] == ["t3"]
    assert (out_dir / "02.2_t2_ai_unit_observation.yaml").exists()
    assert (out_dir / "03.0_t3_hierarchical_stage_input.json").exists()
    assert (out_dir / "03.1_t3_ai_element_observation.yaml").exists()
    assert (out_dir / "summary.json").exists()


def test_standalone_t4_fails_before_api_when_real_render_is_missing(
    monkeypatch,
    tmp_path,
) -> None:
    packet = clean_packet()
    packet["render_status"] = "projection_fallback"
    packet["render_artifacts"]["clean_page_images"] = []
    monkeypatch.setattr(
        observation_stage,
        "inspect_document_facts_docx",
        lambda _path: {},
    )
    monkeypatch.setattr(
        observation_stage,
        "build_template_agent_render_packet",
        lambda **_kwargs: packet,
    )
    monkeypatch.setattr(
        observation_stage,
        "build_live_vision_responder",
        lambda **_kwargs: pytest.fail(
            "T4 must not claim an API call without real page images"
        ),
    )

    source = tmp_path / "template.docx"
    source.touch()
    with pytest.raises(AgentConfigError, match="requires real rendered page images"):
        observation_stage.run_live_template_observation_stage(
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

    with pytest.raises(AgentConfigError, match="requires a pinned T2 final"):
        observation_stage.run_template_observation_stage(
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
        run_dir / "02_unit_map.yaml",
        publish_final_stage_result(
            {
                "artifact_type": "unit_map",
                "units": [
                    {"unit_id": "cover", "source_seq_refs": [1]},
                    {"unit_id": "body_main", "source_seq_refs": [2, 3, 4]},
                ],
            },
            stage_id="T2",
            artifact_type="unit_map",
            artifact_name="02_unit_map.yaml",
            producer_mode="fixture",
            input_refs={
                "l1": {
                    "sha256": l1_artifact_hash(
                        read_json(run_dir / "01.5_l1_input_contract.json")
                    )
                }
            },
        ).payload,
    )
    write_yaml(
        run_dir / "02.2_t2_ai_unit_observation.yaml",
        {
            "artifact_type": "ai_unit_observation",
            "source_render_hash": packet["source_render_hash"],
            "route": {"route_id": "ai_raw", "availability": "AVAILABLE"},
            "items": [{"unit_id": "wrong_candidate", "source_seq_refs": [4]}],
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

    summary = observation_stage.run_template_observation_stage(
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
        "02_unit_map.yaml"
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

    summary = observation_stage.run_template_observation_stage(
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


def test_t3_gold_mode_blocks_before_model_when_atomic_input_is_incomplete(
    monkeypatch,
    tmp_path,
) -> None:
    packet = clean_packet()
    run_dir = tmp_path / "template-run"
    run_dir.mkdir()
    write_l1_stage_input(run_dir, packet)
    write_json(
        run_dir / "01_document_facts.json",
        {"metadata": {"source_template_hash": "sha256:test-template"}},
    )
    standard_path = tmp_path / "t2.standard.yaml"
    write_yaml(
        standard_path,
        {
            "stage_id": "T2",
            "standard_id": "fixture-t2",
            "standard_state": "signed_active",
            "accepted_source_facts": {
                "template_docx_sha256": "sha256:test-template"
            },
            "expected": {
                "unit_order": ["cover", "body_main"],
                "units": [
                    {
                        "unit_id": "cover",
                        "boundary": {
                            "source_seq_range": {"start": 1, "end": 1}
                        },
                    },
                    {
                        "unit_id": "body_main",
                        "boundary": {
                            "source_seq_range": {"start": 2, "end": 4}
                        },
                    },
                ],
            },
        },
    )
    monkeypatch.setattr(
        observation_stage,
        "_stage_text_runtime",
        lambda **_kwargs: pytest.fail("gold input gate must run before the model"),
    )

    with pytest.raises(AgentConfigError, match="complete atomic run facts"):
        observation_stage.run_template_observation_stage(
            source_run_dir=run_dir,
            out_dir=tmp_path / "t3-gold",
            stage="t3",
            ai_mode="replay",
            replay_path=tmp_path / "unused-replay.json",
            t2_gold_standard_path=standard_path,
        )
