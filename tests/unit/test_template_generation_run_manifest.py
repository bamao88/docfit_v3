from __future__ import annotations

from docfit.core.io import read_json
from docfit.core.models import StageResult
from docfit.core.status import Status
from docfit.template_generation.agent import AgentConfig
from docfit.template_generation.run_manifest import write_template_run_manifest


def test_run_manifest_preserves_live_api_trace_and_l1_hash(tmp_path) -> None:
    result = StageResult(
        "template_generation_full",
        Status.UNKNOWN,
        artifacts={
            "template_generation_l1_input_contract": {
                "artifact_type": "template_generation_l1_input_contract",
                "visual_page_index": {"source_render_hash": "sha256:render"},
            },
            "ai_observation_bundle": {
                "artifact_type": "ai_observation_bundle",
                "api_trace_summary": {
                    "mode": "live",
                    "api_call_count": 7,
                    "cache_hit_count": 2,
                    "failures": [{"stage": "t4", "error": "timeout"}],
                },
            },
        },
    )

    path = write_template_run_manifest(
        tmp_path,
        result=result,
        entrypoint="cli.template.verify",
        command="docfit template verify",
        stage="template_generation_verify",
        agent_config=AgentConfig(enabled=True, observation_mode="live"),
    )

    manifest = read_json(path)
    assert manifest["ai_mode"] == "live"
    assert manifest["provider"] == ["kimi", "minimax"]
    assert manifest["source_render_hash"] == "sha256:render"
    assert manifest["l1_contract_hash"]
    assert manifest["api_call_count"] == 7
    assert manifest["api_cache_hit_count"] == 2
    assert manifest["api_failures"] == [{"stage": "t4", "error": "timeout"}]
