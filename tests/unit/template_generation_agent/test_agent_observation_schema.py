from __future__ import annotations

from docfit.template_generation.agent.observation_schema import (
    ALLOWED_POLICIES,
    OBSERVATION_STAGES,
    compute_coverage,
    coverage_invariant_errors,
    empty_observation,
    validate_observation,
)
def test_allowed_policy_set_tracks_runtime_ontology() -> None:
    assert {"fixed", "fill", "fixed", "generated", "unknown"} <= ALLOWED_POLICIES


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
        "ai_layout_observation",
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
