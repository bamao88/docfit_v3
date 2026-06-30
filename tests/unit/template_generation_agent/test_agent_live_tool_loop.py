from __future__ import annotations

import json
from types import SimpleNamespace

import openai

from docfit.core.io import write_json
from docfit.template_generation.agent import loop as loop_module
from docfit.template_generation.agent.config import AgentConfig
from docfit.template_generation.agent.loop import (
    _live_messages,
    _live_pass_specs,
    run_template_agent,
)
from docfit.template_generation.agent.tools import (
    agent_tool_schemas,
    execute_agent_tool_call,
)
from docfit.template_generation.agent.transport import KimiOpenAICompatibleTransport

from .helpers import layered_submission, packet, round0_artifacts


def test_live_messages_include_quality_contract_and_evidence_rules(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    pass_spec = {
        "pass_id": "t2_unit_scan",
        "pass_kind": "t2_unit_scan",
        "window_id": "full_document",
        "allowed_layers": ["t2"],
    }

    messages = _live_messages(
        artifacts["packet"],
        artifacts["request"],
        round_index=1,
        pass_spec=pass_spec,
    )

    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]
    payload = _prompt_payload(user_prompt)
    assert "advisory-only DocFit template agent" in system_prompt
    assert "never write final artifacts" in system_prompt
    assert "Prefer abstain over speculative proposals" in system_prompt
    assert "text_outline and query_text source_seq evidence" in system_prompt
    assert "Include a short rationale and evidence list" in user_prompt
    assert "For T2 unit boundaries" in user_prompt
    assert "duplicate existing units" in user_prompt
    assert payload["prompt_contract"]["contract_version"] == (
        "template-agent-prompt-quality-1.1"
    )
    assert "page_text_index" not in payload["packet"]
    assert payload["packet"]["text_outline"]["scope"] == "full_document_outline"
    assert payload["packet"]["tool_access"]["query_text"].startswith("Use query_text")
    assert "sufficient even if rendered page images" in (
        payload["packet"]["tool_access"]["query_text"]
    )
    assert "rationale explains why" in payload["prompt_contract"]["proposal_quality_bar"][3]
    assert "Use submit_t2 only." in payload["prompt_contract"]["pass_specific_rules"]


def test_live_pass_specs_carry_t3_window_specific_quality_context(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)

    pass_specs = _live_pass_specs(
        config=AgentConfig(enabled=True, transport="kimi", max_rounds=3),
        packet=artifacts["packet"],
        structure_candidates=artifacts["structure_candidates"],
    )
    t3_spec = next(spec for spec in pass_specs if spec["pass_kind"] == "t3_unit_elements")
    messages = _live_messages(
        artifacts["packet"],
        artifacts["request"],
        round_index=2,
        pass_spec=t3_spec,
    )
    payload = _prompt_payload(messages[1]["content"])

    assert payload["pass"]["unit_window"]["window_id"].startswith("unit:")
    assert payload["pass"]["allowed_layers"] == ["t3"]
    assert payload["packet"]["text_outline"]["scope"] == "active_unit_window"
    assert {
        item["source_seq"] for item in payload["packet"]["text_outline"]["items"]
    }.issubset(set(payload["pass"]["unit_window"]["source_seq_refs"]))
    rules = payload["prompt_contract"]["pass_specific_rules"]
    assert "Use submit_t3 only." in rules
    assert any("target_candidate_id" in rule for rule in rules)
    assert any("Never submit T2 boundary changes" in rule for rule in rules)


def test_live_messages_do_not_embed_full_large_packet(tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    large_packet = {
        **artifacts["packet"],
        "page_text_index": [
            {
                "source_seq": index,
                "page_no": 1,
                "render_target_id": f"source_seq:{index}",
                "text": "X" * 2000,
            }
            for index in range(1, 700)
        ],
        "page_layout_index": [{"large": "Y" * 2000} for _ in range(700)],
    }
    pass_spec = {
        "pass_id": "t2_unit_scan",
        "pass_kind": "t2_unit_scan",
        "window_id": "full_document",
        "allowed_layers": ["t2"],
    }

    messages = _live_messages(
        large_packet,
        artifacts["request"],
        round_index=1,
        pass_spec=pass_spec,
    )
    payload = _prompt_payload(messages[1]["content"])

    assert len(messages[1]["content"]) < 120_000
    assert payload["packet"]["text_outline"]["truncated"] is True
    assert len(payload["packet"]["text_outline"]["items"]) == 120
    assert "page_layout_index" not in payload["packet"]
    assert "X" * 500 not in messages[1]["content"]


def test_execute_agent_tool_call_queries_packet_text_and_submits_t2() -> None:
    render_packet = packet()

    query = execute_agent_tool_call(
        "query_text",
        {"source_seq_refs": [3]},
        packet=render_packet,
        round_id="round_001",
        model="fixture-model",
    )
    submit = execute_agent_tool_call(
        "submit_t2",
        {
            "unit_candidates": [
                {
                    "proposal_id": "t2_add_001",
                    "kind": "unit_candidate",
                    "operation": "add_unit",
                    "unit_id": "student_info",
                    "display_name": "学生信息",
                    "source_seq_refs": [3],
                }
            ]
        },
        packet=render_packet,
        round_id="round_001",
        model="fixture-model",
    )

    assert query["ok"] is True
    assert query["content"]["items"][0]["source_seq"] == 3
    assert submit["terminal"] is True
    submission = submit["submission"]
    assert submission["source_render_hash"] == render_packet["source_render_hash"]
    assert submission["layers"]["t2"]["unit_candidates"][0]["proposal_id"] == "t2_add_001"


def test_openai_transport_executes_tool_loop_until_submit(monkeypatch) -> None:
    render_packet = packet()
    fake_completions = _FakeCompletions(
        [
            _completion(
                _tool_call(
                    "call_query",
                    "query_text",
                    '{"source_seq_refs":[3]}',
                )
            ),
            _completion(
                _tool_call(
                    "call_submit",
                    "submit_t3",
                    '{"element_policy_candidates":[{'
                    '"proposal_id":"t3_fill_001",'
                    '"kind":"element_policy_candidate",'
                    '"policy":"fill",'
                    '"source_seq_refs":[3]'
                    "}]}",
                )
            ),
        ]
    )
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **_kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions)
        ),
    )
    transport = KimiOpenAICompatibleTransport(api_key="test-key", model="fixture-model")

    submission = transport.complete_round(
        messages=[{"role": "user", "content": "inspect then submit"}],
        tools=agent_tool_schemas(),
        response_format={"type": "json_object"},
        max_tokens=123,
        temperature=0.25,
        tool_executor=lambda name, arguments: execute_agent_tool_call(
            name,
            arguments,
            packet=render_packet,
            round_id="round_001",
            model=transport.model,
        ),
    )

    assert submission is not None
    assert submission["layers"]["t3"]["element_policy_candidates"][0]["proposal_id"] == (
        "t3_fill_001"
    )
    assert [item["tool_name"] for item in submission["_tool_trace"]] == [
        "query_text",
        "submit_t3",
    ]
    assert len(fake_completions.calls) == 2
    assert fake_completions.calls[0]["max_tokens"] == 123
    assert fake_completions.calls[0]["temperature"] == 0.25
    assert "response_format" not in fake_completions.calls[0]
    assert any(message["role"] == "tool" for message in fake_completions.calls[1]["messages"])
    assert "tool_choice" not in fake_completions.calls[1]
    assert any(
        str(message.get("content", "")).startswith("DocFit terminal tool instruction:")
        for message in fake_completions.calls[1]["messages"]
    )
    assert {
        tool["function"]["name"] for tool in fake_completions.calls[1]["tools"]
    } == {"submit_t2", "submit_t3", "submit_t4", "abstain"}


def test_openai_transport_normalizes_terminal_tool_submission(monkeypatch) -> None:
    render_packet = packet()
    fake_completions = _FakeCompletions(
        [
            _completion(
                _tool_call(
                    "call_submit",
                    "submit_t2",
                    json.dumps(
                        {
                            "boundary_adjustments": [
                                {
                                    "operation": "adjust_unit_range",
                                    "unit_id": "body_main",
                                    "new_start_seq": 2,
                                    "new_end_seq": 4,
                                    "evidence": [
                                        {
                                            "type": "source_seq",
                                            "ref": 3,
                                            "text": "学生姓名：____",
                                        }
                                    ],
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                )
            ),
        ]
    )
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **_kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions)
        ),
    )
    transport = KimiOpenAICompatibleTransport(api_key="test-key", model="fixture-model")

    submission = transport.complete_round(
        messages=[{"role": "user", "content": "submit t2"}],
        tools=agent_tool_schemas(),
        response_format=None,
        max_tokens=123,
        temperature=0.25,
        tool_executor=lambda name, arguments: execute_agent_tool_call(
            name,
            arguments,
            packet=render_packet,
            round_id="round_001",
            model=transport.model,
        ),
    )

    proposal = submission["layers"]["t2"]["boundary_adjustments"][0]
    assert proposal["proposal_id"] == "round_001_t2_boundary_adjustments_001"
    assert proposal["kind"] == "boundary_adjustment"
    assert proposal["target_unit_id"] == "body_main"
    assert proposal["source_seq_refs"] == [3]
    assert submission["model"] == "fixture-model"


def test_openai_transport_falls_back_to_terminal_json_after_reasoning_only(
    monkeypatch,
) -> None:
    render_packet = packet()
    final_submission = layered_submission(render_packet["source_render_hash"], layers={})
    fake_completions = _FakeCompletions(
        [
            _completion(
                _tool_call(
                    "call_query",
                    "query_text",
                    '{"source_seq_refs":[3]}',
                )
            ),
            _content_completion(""),
            _content_completion(json.dumps({"submission": final_submission})),
        ]
    )
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **_kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions)
        ),
    )
    transport = KimiOpenAICompatibleTransport(api_key="test-key", model="fixture-model")

    submission = transport.complete_round(
        messages=[{"role": "user", "content": "inspect then submit"}],
        tools=agent_tool_schemas(),
        response_format=None,
        max_tokens=123,
        temperature=0.25,
        tool_executor=lambda name, arguments: execute_agent_tool_call(
            name,
            arguments,
            packet=render_packet,
            round_id="round_001",
            model=transport.model,
        ),
    )

    assert submission is not None
    assert submission["source_render_hash"] == render_packet["source_render_hash"]
    assert submission["_tool_trace"][0]["tool_name"] == "query_text"
    assert fake_completions.calls[2]["response_format"] == {"type": "json_object"}
    assert "tools" not in fake_completions.calls[2]
    assert any(
        str(message.get("content", "")).startswith("DocFit terminal JSON instruction:")
        for message in fake_completions.calls[2]["messages"]
    )


def test_openai_transport_records_provider_failure_when_finalizer_is_empty(
    monkeypatch,
    tmp_path,
) -> None:
    artifacts = round0_artifacts(tmp_path)
    render_packet = artifacts["packet"]
    pass_spec = {
        "pass_id": "t2_unit_scan",
        "pass_kind": "t2_unit_scan",
        "window_id": "full_document",
        "allowed_layers": ["t2"],
    }
    fake_completions = _FakeCompletions(
        [
            _completion(
                _tool_call(
                    "call_query",
                    "query_text",
                    '{"source_seq_refs":[3]}',
                )
            ),
            _content_completion(""),
            _content_completion(""),
        ]
    )
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **_kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions)
        ),
    )
    transport = KimiOpenAICompatibleTransport(api_key="test-key", model="fixture-model")

    submission = transport.complete_round(
        messages=_live_messages(
            render_packet,
            artifacts["request"],
            round_index=1,
            pass_spec=pass_spec,
        ),
        tools=agent_tool_schemas(),
        response_format=None,
        max_tokens=123,
        temperature=0.25,
        tool_executor=lambda name, arguments: execute_agent_tool_call(
            name,
            arguments,
            packet=render_packet,
            round_id="round_001",
            model=transport.model,
        ),
    )

    assert submission is not None
    assert submission["abstain"] is False
    assert submission["source_render_hash"] == render_packet["source_render_hash"]
    assert submission["layers"]["t2"]["open_questions"][0]["blocking"] is True
    assert "provider returned no terminal JSON" in (
        submission["layers"]["t2"]["open_questions"][0]["question"]
    )
    assert submission["layers"]["t3"]["open_questions"] == []
    assert submission["_tool_trace"][0]["tool_name"] == "query_text"


def test_openai_transport_normalizes_terminal_json_submission(monkeypatch) -> None:
    render_packet = packet()
    final_submission = layered_submission(
        render_packet["source_render_hash"],
        layers={
            "t2": {
                "unit_candidates": [
                    {
                        "operation": "adjust_unit_range",
                        "unit_id": "body_main",
                        "source_seq_refs": [3, 4],
                    }
                ]
            }
        },
    )
    final_submission["model"] = "provider-model-name"
    fake_completions = _FakeCompletions(
        [
            _completion(
                _tool_call(
                    "call_query",
                    "query_text",
                    '{"source_seq_refs":[3]}',
                )
            ),
            _content_completion(""),
            _content_completion(json.dumps({"submission": final_submission})),
        ]
    )
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **_kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions)
        ),
    )
    transport = KimiOpenAICompatibleTransport(api_key="test-key", model="fixture-model")

    submission = transport.complete_round(
        messages=[{"role": "user", "content": "inspect then submit"}],
        tools=agent_tool_schemas(),
        response_format=None,
        max_tokens=123,
        temperature=0.25,
        tool_executor=lambda name, arguments: execute_agent_tool_call(
            name,
            arguments,
            packet=render_packet,
            round_id="round_001",
            model=transport.model,
        ),
    )

    assert submission is not None
    assert submission["layers"]["t2"]["unit_candidates"] == []
    proposal = submission["layers"]["t2"]["boundary_adjustments"][0]
    assert proposal["kind"] == "boundary_adjustment"
    assert proposal["proposal_id"] == "round_001_t2_boundary_adjustments_001"
    assert proposal["target_unit_id"] == "body_main"
    assert submission["model"] == "fixture-model"


def test_live_run_records_tool_trace_in_transcript(monkeypatch, tmp_path) -> None:
    artifacts = round0_artifacts(tmp_path)
    packet_path = tmp_path / "packet.json"
    write_json(packet_path, artifacts["packet"])
    submission = layered_submission(artifacts["packet"]["source_render_hash"], layers={})
    submission["_tool_trace"] = [
        {
            "tool_call_id": "call_query",
            "tool_name": "query_text",
            "arguments": {"source_seq_refs": [1]},
            "result": {"ok": True},
        }
    ]

    class FakeTransport:
        model = "fixture-model"

        def __init__(self, **_kwargs: object) -> None:
            pass

        def complete_round(self, **kwargs: object) -> dict[str, object]:
            assert kwargs["response_format"] is None
            assert kwargs["max_tokens"] == 77
            assert kwargs["temperature"] == 0.5
            return submission

    monkeypatch.setattr(loop_module, "KimiOpenAICompatibleTransport", FakeTransport)

    result = run_template_agent(
        source_template_docx=tmp_path / "template.docx",
        request=artifacts["request"],
        document_facts=artifacts["document_facts"],
        structure_candidates=artifacts["structure_candidates"],
        unit_map=artifacts["unit_map"],
        generation_model=artifacts["generation_model"],
        element_spec=artifacts["element_spec"],
        agent_config=AgentConfig(
            enabled=True,
            transport="kimi",
            max_rounds=1,
            max_tokens=77,
            temperature=0.5,
            render_packet_path=packet_path,
            allow_live_without_real_render=True,
        ),
    )

    assert result.transcript is not None
    assert result.transcript["rounds"][0]["pass_kind"] == "t2_unit_scan"
    assert result.transcript["rounds"][0]["tool_trace"][0]["tool_name"] == "query_text"


class _FakeCompletions:
    def __init__(self, completions: list[SimpleNamespace]) -> None:
        self._completions = completions
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return self._completions.pop(0)


def _completion(tool_call: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=None, tool_calls=[tool_call])
            )
        ]
    )


def _content_completion(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=[])
            )
        ]
    )


def _tool_call(call_id: str, name: str, arguments: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _prompt_payload(user_prompt: str) -> dict:
    marker = "Context JSON follows.\n"
    return json.loads(user_prompt.split(marker, 1)[1])
