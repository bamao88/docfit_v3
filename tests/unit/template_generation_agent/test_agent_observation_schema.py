from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.template_generation.agent.observation_config import (
    ObservationConfig,
    validate_observation_config,
)
from docfit.template_generation.agent.observation_schema import (
    ALLOWED_POLICIES,
    ALLOWED_UNIT_IDS,
    OBSERVATION_SCHEMA_VERSION,
    OBSERVATION_STAGES,
    UNKNOWN_UNIT_ID,
    compute_coverage,
    coverage_invariant_errors,
    empty_observation,
    validate_observation,
)
from docfit.template_generation.agent.packet import (
    build_template_agent_render_packet,
    packet_source_seq_set,
)

from .helpers import document_facts


def clean_packet() -> dict[str, Any]:
    # Module 1 防火墙：structure_candidates={} → round0 结论不进渲染包。
    return build_template_agent_render_packet(
        document_facts=document_facts(),
        structure_candidates={},
    )


def unit_observation(source_render_hash: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_type": "ai_unit_observation",
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "stage": "t2",
        "source_render_hash": source_render_hash,
        "model": "fixture",
        "items": items,
        "unknown_items": [],
        "open_questions": [],
        "abstain": False,
    }


def test_allowed_label_sets_track_runtime_taxonomy() -> None:
    # 历史 A.3 写“22 单元”，实际已 24；标签集必须从运行时派生而非硬编码。
    assert "cover" in ALLOWED_UNIT_IDS
    assert UNKNOWN_UNIT_ID in ALLOWED_UNIT_IDS
    assert len(ALLOWED_UNIT_IDS) >= 24
    assert {"fixed", "fill", "manual_only", "generated"} <= ALLOWED_POLICIES


def test_empty_observation_is_schema_valid_and_abstains() -> None:
    for artifact_type in OBSERVATION_STAGES:
        observation = empty_observation(
            artifact_type,
            source_render_hash="sha256:x",
            all_source_seq={1, 2, 3, 4},
        )
        result = validate_observation(observation, all_source_seq={1, 2, 3, 4})
        assert result["valid"] is True, result["errors"]
        assert observation["abstain"] is True
        assert observation["coverage"]["total"] == 4
        # 弃权 = 全部 unknown，不能 silent gap。
        assert observation["coverage"]["unknown_source_seq"] == [1, 2, 3, 4]
        assert observation["coverage"]["owned_source_seq"] == []


def test_observation_roundtrip_full_coverage() -> None:
    packet = clean_packet()
    all_source_seq = packet_source_seq_set(packet)
    assert all_source_seq, "fixture packet must expose source_seq"

    items = [
        {"unit_id": "cover", "order": 10, "source_seq_refs": sorted(all_source_seq)},
    ]
    coverage = compute_coverage(items, all_source_seq=all_source_seq)
    observation = unit_observation(packet["source_render_hash"], items)
    observation["coverage"] = coverage

    result = validate_observation(
        observation,
        expected_source_render_hash=packet["source_render_hash"],
        all_source_seq=all_source_seq,
    )
    assert result["valid"] is True, result["errors"]
    assert coverage["unknown_source_seq"] == []
    assert set(coverage["owned_source_seq"]) == all_source_seq


def test_coverage_splits_owned_and_unknown_without_overlap() -> None:
    all_source_seq = {1, 2, 3, 4}
    items = [{"unit_id": "cover", "source_seq_refs": [1, 2]}]
    coverage = compute_coverage(items, all_source_seq=all_source_seq)

    assert coverage["owned_source_seq"] == [1, 2]
    assert coverage["unknown_source_seq"] == [3, 4]
    assert coverage_invariant_errors(coverage, all_source_seq=all_source_seq) == []


def test_coverage_invariant_catches_silent_gap() -> None:
    # 模型声称全覆盖（unknown 空）但只认领了一部分 → 不变量必须报 gap。
    all_source_seq = {1, 2, 3, 4}
    tampered = {"owned_source_seq": [1, 2], "unknown_source_seq": [], "total": 4}
    errors = coverage_invariant_errors(tampered, all_source_seq=all_source_seq)
    assert any(e["check_id"] == "C-COVERAGE-GAP" for e in errors)


def test_coverage_invariant_catches_overlap() -> None:
    all_source_seq = {1, 2, 3}
    tampered = {"owned_source_seq": [1, 2], "unknown_source_seq": [2, 3], "total": 3}
    errors = coverage_invariant_errors(tampered, all_source_seq=all_source_seq)
    assert any(e["check_id"] == "C-COVERAGE-OVERLAP" for e in errors)


def test_validate_rejects_unknown_artifact_type() -> None:
    result = validate_observation({"artifact_type": "ai_unknown_observation"})
    assert result["valid"] is False
    assert any(e["path"] == "$.artifact_type" for e in result["errors"])


def test_validate_flags_source_render_hash_mismatch() -> None:
    observation = empty_observation(
        "ai_unit_observation",
        source_render_hash="sha256:wrong",
        all_source_seq=set(),
    )
    result = validate_observation(
        observation,
        expected_source_render_hash="sha256:right",
        all_source_seq=set(),
    )
    assert result["valid"] is False
    assert any(e["path"] == "$.source_render_hash" for e in result["errors"])


def test_validate_rejects_non_dict() -> None:
    result = validate_observation(["not", "a", "dict"])
    assert result["valid"] is False


def test_observation_config_default_off_skips_validation() -> None:
    assert validate_observation_config(ObservationConfig()) == []


def test_enabled_replay_config_requires_transcript(tmp_path: Path) -> None:
    missing = ObservationConfig(enabled=True, transcript_path=tmp_path / "missing.json")
    errors = validate_observation_config(missing)
    assert any("transcript_path does not exist" in e for e in errors)


def test_enabled_config_rejects_zero_samples() -> None:
    transcript = ObservationConfig(enabled=True, self_consistency_samples=0)
    errors = validate_observation_config(transcript)
    assert any("self_consistency_samples" in e for e in errors)
