"""Module 1 独立同形产物（ai-observation）的信封与形状校验。

Module 1 让 AI 只看干净 Word 事实，独立产出与代码同形的三份完整文件：

  ai_unit_observation     镜像 unit_map     stage=t2
  ai_element_observation  镜像 element_spec stage=t3
  ai_layout_observation   镜像 global_spec  stage=t4

本模块只负责信封 / 形状校验 / 覆盖不变量（Phase 1）。
越界标签降级、证据绑定、必填规则等物化闸门在 observation_materialize 落地（Phase 3）。

允许标签集（unit_id / policy / field_type / fill_source / role）来自运行时
``UNIT_DEFINITIONS`` 与 ``ontology.yaml``，不在此硬编码——这样产物校验永远与真实
taxonomy 同步（历史 A.3 写“22 单元”，现已 24，硬编码会立刻失配）。
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, read_yaml

from ..constants import UNIT_DEFINITIONS

OBSERVATION_SCHEMA_VERSION = "ai-observation-1.0"
PROMPT_CONTRACT_VERSION = "ai-observation-prompt-1.0"

UNKNOWN_UNIT_ID = "unknown_unit"
CONFIDENCE_LEVELS = ("low", "medium", "high")

# artifact_type -> stage。三份产物同信封、按 stage 区分 item 形状。
OBSERVATION_STAGES = {
    "ai_unit_observation": "t2",
    "ai_element_observation": "t3",
    "ai_layout_observation": "t4",
}

_ONTOLOGY_PATH = Path(__file__).resolve().parent.parent / "ontology.yaml"
_ONTOLOGY: dict[str, Any] = read_yaml(_ONTOLOGY_PATH) or {}

# 单一真相：允许标签集从运行时 taxonomy / ontology 派生。
ALLOWED_UNIT_IDS = frozenset(unit_id for unit_id, *_ in UNIT_DEFINITIONS) | {UNKNOWN_UNIT_ID}
ALLOWED_POLICIES = frozenset(_ONTOLOGY.get("policies", ()))
ALLOWED_ROLES = frozenset(_ONTOLOGY.get("roles", ()))
ALLOWED_FILL_SOURCES = frozenset(_ONTOLOGY.get("fill_sources", ()))
ALLOWED_FIELD_TYPES = frozenset(_ONTOLOGY.get("generated_field_types", ()))


def empty_observation(
    artifact_type: str,
    *,
    source_render_hash: str,
    all_source_seq: set[int],
    model: str = "replay",
    abstain: bool = True,
) -> dict[str, Any]:
    """空/弃权产物：schema-valid，全 unknown，abstain=true。

    弃权语义是“认领不了，全部 unknown”——而非“缺失”。所以每个 source_seq 都进
    ``unknown_source_seq``，覆盖不变量 ``owned ∪ unknown == total`` 由构造成立，
    即便模型给空响应或垃圾响应也不会 silent gap。
    """

    if artifact_type not in OBSERVATION_STAGES:
        raise ValueError(f"unknown observation artifact_type: {artifact_type!r}")
    source_seq = {s for s in (_as_int(x) for x in all_source_seq) if s is not None}
    return {
        "artifact_type": artifact_type,
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "stage": OBSERVATION_STAGES[artifact_type],
        "source_render_hash": source_render_hash,
        "model": model,
        "created_at": now_iso(),
        "coverage": {
            "owned_source_seq": [],
            "unknown_source_seq": sorted(source_seq),
            "total": len(source_seq),
        },
        "items": [],
        "unknown_items": [],
        "open_questions": [],
        "abstain": bool(abstain),
        "self_consistency": None,
    }


def compute_coverage(
    items: list[dict[str, Any]],
    *,
    all_source_seq: set[int],
) -> dict[str, Any]:
    """owned = ∪ item.source_seq_refs（裁剪到 packet 内）；unknown = total − owned。"""

    owned: set[int] = set()
    for item in items:
        for ref in item.get("source_seq_refs", []) or []:
            ref_int = _as_int(ref)
            if ref_int is not None and ref_int in all_source_seq:
                owned.add(ref_int)
    unknown = set(all_source_seq) - owned
    return {
        "owned_source_seq": sorted(owned),
        "unknown_source_seq": sorted(unknown),
        "total": len(all_source_seq),
    }


def coverage_invariant_errors(
    coverage: dict[str, Any],
    *,
    all_source_seq: set[int],
) -> list[dict[str, Any]]:
    """覆盖不变量：owned ∪ unknown == total，且 owned ∩ unknown == ∅。

    返回错误列表（空列表表示不变量成立），供测试与运行时闸门统一消费。
    """

    errors: list[dict[str, Any]] = []
    owned = {v for v in (_as_int(x) for x in coverage.get("owned_source_seq", [])) if v is not None}
    unknown = {
        v for v in (_as_int(x) for x in coverage.get("unknown_source_seq", [])) if v is not None
    }
    total = coverage.get("total")

    overlap = owned & unknown
    if overlap:
        errors.append(
            _error(
                "$.coverage",
                "C-COVERAGE-OVERLAP",
                f"owned and unknown overlap on source_seq: {sorted(overlap)}",
            )
        )
    if owned | unknown != set(all_source_seq):
        missing = sorted(set(all_source_seq) - (owned | unknown))
        extra = sorted((owned | unknown) - set(all_source_seq))
        errors.append(
            _error(
                "$.coverage",
                "C-COVERAGE-GAP",
                f"owned ∪ unknown != total source_seq; missing={missing} extra={extra}",
            )
        )
    if total != len(all_source_seq):
        errors.append(
            _error(
                "$.coverage.total",
                "C-COVERAGE-TOTAL",
                f"coverage.total {total} != source_seq count {len(all_source_seq)}",
            )
        )
    return errors


def validate_observation(
    observation: Any,
    *,
    expected_source_render_hash: str | None = None,
    all_source_seq: set[int] | None = None,
) -> dict[str, Any]:
    """信封形状 + 覆盖不变量校验（Phase 1）。

    返回 ``{"valid": bool, "observation": normalized, "errors": [...]}``。
    item 级别的标签闭合 / 证据绑定 / 必填规则属物化闸门（Phase 3），不在此判定。
    """

    if not isinstance(observation, dict):
        return {
            "valid": False,
            "observation": {},
            "errors": [_error("$", "C-SCHEMA", "observation must be an object")],
        }

    errors: list[dict[str, Any]] = []
    normalized = deepcopy(observation)

    artifact_type = normalized.get("artifact_type")
    if artifact_type not in OBSERVATION_STAGES:
        errors.append(
            _error(
                "$.artifact_type",
                "C-SCHEMA",
                f"artifact_type must be one of {sorted(OBSERVATION_STAGES)}",
            )
        )
    else:
        expected_stage = OBSERVATION_STAGES[artifact_type]
        if normalized.setdefault("stage", expected_stage) != expected_stage:
            errors.append(
                _error("$.stage", "C-SCHEMA", f"stage must be {expected_stage}")
            )

    if normalized.setdefault("schema_version", OBSERVATION_SCHEMA_VERSION) != (
        OBSERVATION_SCHEMA_VERSION
    ):
        errors.append(
            _error(
                "$.schema_version",
                "C-SCHEMA",
                f"schema_version must be {OBSERVATION_SCHEMA_VERSION}",
            )
        )

    if not normalized.get("source_render_hash"):
        errors.append(
            _error("$.source_render_hash", "C-SCHEMA", "source_render_hash is required")
        )
    elif (
        expected_source_render_hash is not None
        and normalized.get("source_render_hash") != expected_source_render_hash
    ):
        errors.append(
            _error(
                "$.source_render_hash",
                "C-SCHEMA",
                "source_render_hash does not match packet",
            )
        )

    normalized.setdefault("prompt_contract_version", PROMPT_CONTRACT_VERSION)
    normalized.setdefault("model", "unknown")
    normalized.setdefault("abstain", False)
    for list_field in ("items", "unknown_items", "open_questions"):
        value = normalized.setdefault(list_field, [])
        if not isinstance(value, list):
            errors.append(_error(f"$.{list_field}", "C-SCHEMA", f"{list_field} must be a list"))
            normalized[list_field] = []

    coverage = normalized.setdefault(
        "coverage",
        {"owned_source_seq": [], "unknown_source_seq": [], "total": 0},
    )
    if not isinstance(coverage, dict):
        errors.append(_error("$.coverage", "C-SCHEMA", "coverage must be an object"))
    elif all_source_seq is not None:
        errors.extend(coverage_invariant_errors(coverage, all_source_seq=all_source_seq))

    return {"valid": not errors, "observation": normalized, "errors": errors}


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def _error(path: str, check_id: str, message: str) -> dict[str, Any]:
    return {"path": path, "check_id": check_id, "message": message}
