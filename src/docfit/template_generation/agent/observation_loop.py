"""Module 1 独立观察流水线（responder 驱动；replay 与 live 共用编排）。

三阶段 pass，每阶段产物即终稿（不 patch 代码结构）：

  Pass-T2 : 真实页图 + 逐页客观事实 → 单次 AI 页面分组 → 严格校验
  Pass-T3 : 从【T2 Final Publisher 的唯一结果】构建分层输入 → 稀疏判断 → ai_element_observation
  Pass-T4 : 真实页图 + sealed L1 事实 → 单次 AI 布局判断 → 严格物化

编排只认一个 ``responder`` 抽象：

  - ``ReplayResponder``（确定性回归护栏）从 transcript 取原始 payload；
  - ``LiveResponder``（真实模型，见 observation_live）逐阶段调用 OpenAI 兼容端点。

关键：T3 prompt 只能依赖 T2 final，不能接收 AI observation 或任一内部 route
candidate。所有调用都通过唯一的 AI T2 publisher 进入 T3。
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from docfit.core.io import now_iso, sha256_json
from docfit.template_generation.final_results import (
    AVAILABLE,
    NOT_AVAILABLE,
    FinalStageResult,
)
from docfit.template_generation.t2_ai import (
    T2AIContractError,
    materialize_t2_ai_observation,
    publish_t2_ai_final,
    require_t2_page_packet,
)

from .evidence import build_t2_evidence, build_t4_evidence
from .observation_config import ObservationConfig, ObservationConfigError
from .observation_materialize import (
    materialize_layout_observation,
)
from .observation_schema import (
    OBSERVATION_SCHEMA_VERSION,
    PROMPT_CONTRACT_VERSION,
)
from .packet import packet_source_seq_set
from .t3_hierarchical_input import (
    build_t3_hierarchical_stage_input,
    validate_t3_hierarchical_stage_input,
)
from .t3_sparse_decisions import run_t3_sparse_traversal
from .t3_sparse_materialize import materialize_sparse_t3_observation


class ObservationResponder(Protocol):
    """三阶段原始 payload 的来源（replay 取自 transcript / live 调真实模型）。"""

    def fetch_units(self, *, evidence: dict[str, Any], n_samples: int) -> list[dict[str, Any]]: ...

    def fetch_t3_decision(
        self,
        *,
        evidence: dict[str, Any],
        node: dict[str, Any],
        unit_id: str,
    ) -> dict[str, Any]: ...

    def fetch_layout(self, *, evidence: dict[str, Any]) -> dict[str, Any]: ...


class ReplayResponder:
    """从手写/录制的 transcript 取原始 payload —— 仅作确定性回归护栏，非产品口径。"""

    def __init__(self, transcript: dict[str, Any]) -> None:
        self._transcript = transcript or {}
        self.supports_action_refinement = False

    def fetch_units(self, *, evidence: dict[str, Any], n_samples: int) -> list[dict[str, Any]]:
        del evidence
        return list(self._transcript.get("t2", []) or [])[: max(1, n_samples)]

    def fetch_t3_decision(
        self,
        *,
        evidence: dict[str, Any],
        node: dict[str, Any],
        unit_id: str,
    ) -> dict[str, Any]:
        del evidence
        recorded = self._transcript.get("t3_sparse") or {}
        if isinstance(recorded, dict):
            decision = recorded.get(str(node.get("ref") or ""))
            if isinstance(decision, dict):
                return dict(decision)
        return _keep_leaf(
            node,
            reason=(
                "hierarchical replay has no recorded decision for "
                f"{node.get('ref') or unit_id}"
            ),
        )

    def fetch_layout(self, *, evidence: dict[str, Any]) -> dict[str, Any]:
        del evidence
        return dict(self._transcript.get("t4", {}) or {})


def run_observation_pipeline(
    *,
    packet: dict[str, Any],
    responder: ObservationResponder | None = None,
    transcript: dict[str, Any] | None = None,
    config: ObservationConfig | None = None,
    t3_concurrency: int = 1,
    vision_responder: Any = None,
) -> dict[str, Any]:
    """跑一次三阶段流水线，返回 bundle（含三份产物 + quality_report）。

    传 ``responder`` 走真实/自定义来源；只传 ``transcript`` 时退化为 ReplayResponder。
    ``t3_concurrency`` > 1 时按单元并发跑 T3（各单元窗口独立），缩短 live 墙钟。
    """

    config = config or ObservationConfig()
    if responder is None:
        responder = ReplayResponder(transcript or {})

    timing: dict[str, float] = {}
    pipeline_start = time.monotonic()

    # --- Pass-T2：逐页图像与客观事实 → 单次 AI 页面分组 → 严格物化 ---
    t2_start = time.monotonic()
    unit_observation, t2_consistency, t2_evidence = run_t2_observation(
        packet=packet,
        responder=responder,
        config=config,
    )
    timing["t2_seconds"] = round(time.monotonic() - t2_start, 2)

    # --- Final-T2：唯一 AI publisher；T3 不认识 candidate route。 ---
    t2_final = publish_t2_ai_final(
        unit_observation,
        packet=packet,
    )

    # --- Pass-T3：只从 T2 final 构建唯一分层输入 → 物化 ---
    t3_start = time.monotonic()
    element_observation, t3_stage_input = run_t3_observation(
        t2_final=t2_final,
        responder=responder,
        packet=packet,
        config=config,
        concurrency=t3_concurrency,
    )
    timing["t3_seconds"] = round(time.monotonic() - t3_start, 2)

    # --- Pass-T4：AI 是唯一布局语义来源；代码只提供证据与物化校验。 ---
    t4_start = time.monotonic()
    t4_evidence = build_t4_evidence(packet)
    raw_layout_payload = responder.fetch_layout(evidence=t4_evidence)
    layout_observation, t4_evidence = run_t4_observation(
        packet=packet,
        config=config,
        vision_responder=vision_responder,
        raw_payload=raw_layout_payload,
        evidence=t4_evidence,
    )
    timing["t4_seconds"] = round(time.monotonic() - t4_start, 2)
    timing["total_seconds"] = round(time.monotonic() - pipeline_start, 2)

    return {
        "artifact_type": "ai_observation_bundle",
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "created_at": now_iso(),
        "source_render_hash": packet.get("source_render_hash"),
        "input_contract_hash": packet.get("input_contract_hash"),
        "model": config.model,
        "ai_unit_observation": unit_observation,
        "t2_final_result": t2_final.payload,
        "ai_element_observation": element_observation,
        "ai_layout_observation": layout_observation,
        "t3_hierarchical_stage_input": t3_stage_input,
        "timing": timing,
        "evidence_scopes": {
            "t2": _scope_summary(t2_evidence),
            "t4": {"render_available": t4_evidence.get("render_available")},
        },
        "quality_report": _quality_report(
            unit_observation, element_observation, layout_observation, t2_consistency
        ),
    }


def run_t2_observation(
    *,
    packet: dict[str, Any],
    responder: ObservationResponder,
    config: ObservationConfig,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Run only the T2 live/replay observation pass."""

    require_t2_page_packet(packet)
    evidence = build_t2_evidence(packet)
    samples = responder.fetch_units(
        evidence=evidence,
        n_samples=1,
    )
    observation, consistency = _run_t2(
        samples=samples,
        packet=packet,
        model=config.model,
    )
    observation["input_contract_hash"] = packet.get("input_contract_hash")
    return observation, consistency, evidence


def run_t3_observation(
    *,
    packet: dict[str, Any],
    t2_final: FinalStageResult,
    responder: ObservationResponder,
    config: ObservationConfig,
    concurrency: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run only T3 from the selected published final T2 result."""

    observation, stage_input = _run_t3(
        responder=responder,
        t2_final=t2_final,
        packet=packet,
        valid_seq=packet_source_seq_set(packet),
        model=config.model,
        concurrency=concurrency,
    )
    observation["input_contract_hash"] = packet.get("input_contract_hash")
    return observation, stage_input


def _unavailable_t3_observation(
    *,
    packet: dict[str, Any],
    model: str,
    stage_input: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "ai_element_observation",
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "stage": "t3",
        "source_render_hash": packet.get("source_render_hash"),
        "model": model,
        "created_at": now_iso(),
        "stage_input_ref": {
            "artifact_version": stage_input.get("artifact_version"),
            "tree_hash": stage_input.get("tree_hash"),
            "contract": dict(stage_input.get("contract") or {}),
        },
        "coverage": {
            "total": len(packet_source_seq_set(packet)),
            "owned_source_seq": [],
            "unknown_source_seq": sorted(packet_source_seq_set(packet)),
        },
        "items": [],
        "object_items": [],
        "unknown_items": [],
        "open_questions": [
            {
                "question_id": "q_t3_required_t2_final_unavailable",
                "blocking_level": "blocking",
                "reason": reason,
            }
        ],
        "abstain": True,
        "self_consistency": None,
        "sparse_decisions": [],
        "atomic_coverage": [],
        "sparse_call_records": [],
        "quality_report": {
            "availability": NOT_AVAILABLE,
            "reason": reason,
            "t2_final_hash": (stage_input.get("contract") or {}).get(
                "t2_final_hash"
            ),
            "decision_call_count": 0,
            "coverage_validation": {
                "valid": False,
                "errors": [{"type": "required_t2_final_unavailable", "message": reason}],
            },
        },
    }


def run_t4_observation(
    *,
    packet: dict[str, Any],
    config: ObservationConfig,
    vision_responder: Any = None,
    raw_payload: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Materialize one AI T4 answer and optional per-page visual evidence."""

    evidence = evidence or build_t4_evidence(packet)
    render_available = bool(evidence.get("render_available"))
    page_observations: list[dict[str, Any]] = []
    if vision_responder is not None and render_available:
        page_images = (packet.get("render_artifacts", {}) or {}).get(
            "clean_page_images", []
        ) or []
        page_images = _attach_layout_context_to_page_images(
            page_images,
            global_layout_facts=evidence.get("global_layout_facts", {}),
        )
        page_observations = vision_responder.observe_pages(page_images)
    observation = materialize_layout_observation(
        raw_payload or {"section_profiles": []},
        packet=packet,
        render_available=render_available,
        model=config.model,
        page_observations=page_observations,
    )
    observation["input_contract_hash"] = packet.get("input_contract_hash")
    return observation, evidence


def _attach_layout_context_to_page_images(
    page_images: list[dict[str, Any]],
    *,
    global_layout_facts: dict[str, Any],
) -> list[dict[str, Any]]:
    context = {
        "sections": global_layout_facts.get("sections", []),
        "header_footer": global_layout_facts.get("header_footer", []),
        "fields": global_layout_facts.get("fields", []),
        "breaks": global_layout_facts.get("breaks", []),
    }
    return [
        {**page, "layout_context": context}
        for page in page_images
        if isinstance(page, dict)
    ]


def _run_t2(
    *,
    samples: list[dict[str, Any]],
    packet: dict[str, Any],
    model: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not samples:
        raise T2AIContractError("T2 AI returned no output")
    if len(samples) != 1:
        raise T2AIContractError(
            f"T2 accepts exactly one AI output, got {len(samples)}"
        )
    observation = materialize_t2_ai_observation(
        samples[0],
        packet=packet,
        model=model,
    )
    return observation, {"samples": 1, "mode": "single_ai_output"}


def _run_t3(
    *,
    responder: ObservationResponder,
    t2_final: FinalStageResult,
    packet: dict[str, Any],
    valid_seq: set[int],
    model: str,
    concurrency: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    del valid_seq, concurrency
    stage_input = build_t3_hierarchical_stage_input(
        packet,
        t2_final=t2_final,
    )
    validation = validate_t3_hierarchical_stage_input(stage_input)
    if not validation["valid"]:
        messages = "; ".join(
            str(error.get("message") or error)
            for error in validation["errors"][:12]
        )
        raise ObservationConfigError(
            f"T3 hierarchical Stage Input validation failed: {messages}"
        )
    if t2_final.availability != AVAILABLE:
        return _unavailable_t3_observation(
            packet=packet,
            model=model,
            stage_input=stage_input,
            reason=(
                "T3 did not call AI because required T2 final is "
                f"{t2_final.availability}: {t2_final.reason or 'no reason supplied'}"
            ),
        ), stage_input
    trace = run_t3_sparse_traversal(
        stage_input,
        decide=lambda evidence, node, unit_id: _fetch_t3_sparse_decision(
            responder,
            evidence=evidence,
            node=node,
            unit_id=unit_id,
        ),
    )
    return (
        materialize_sparse_t3_observation(
            trace,
            packet=packet,
            model=model,
            stage_input=stage_input,
        ),
        stage_input,
    )


def _fetch_t3_sparse_decision(
    responder: ObservationResponder,
    *,
    evidence: dict[str, Any],
    node: dict[str, Any],
    unit_id: str,
) -> dict[str, Any]:
    method = getattr(responder, "fetch_t3_decision", None)
    if not callable(method):
        return _keep_leaf(
            node,
            reason="responder does not implement the hierarchical T3 decision contract",
        )
    return method(
        evidence=evidence,
        node=node,
        unit_id=unit_id,
    )


def _keep_leaf(node: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "target_ref": node.get("ref"),
        "result": "keep",
        "confidence": "low",
        "reason": reason,
    }


def _quality_report(
    unit_observation: dict[str, Any],
    element_observation: dict[str, Any],
    layout_observation: dict[str, Any],
    t2_consistency: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "ai_observation_quality_report",
        "self_consistency": t2_consistency,
        "stages": {
            "t2": _stage_quality(unit_observation),
            "t3": _stage_quality(element_observation),
            "t4": _stage_quality(layout_observation),
        },
        "demotions": (
            unit_observation.get("quality_report", {}).get("demotions", [])
            + element_observation.get("quality_report", {}).get("demotions", [])
            + layout_observation.get("quality_report", {}).get("demotions", [])
        ),
    }


def _stage_quality(observation: dict[str, Any]) -> dict[str, Any]:
    coverage = observation.get("coverage", {})
    unit_count = len(
        observation.get("units", observation.get("items", [])) or []
    )
    return {
        "abstain": observation.get("abstain"),
        "owned": len(coverage.get("owned_source_seq", [])),
        "unknown": len(coverage.get("unknown_source_seq", [])),
        "total": coverage.get("total"),
        "items": unit_count,
        "demotions": len(observation.get("quality_report", {}).get("demotions", [])),
    }


def _scope_summary(view: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope": view.get("scope"),
        "pages": len(view.get("page_packets", [])),
        "rows": sum(
            len(page.get("content", []))
            for page in view.get("page_packets", [])
            if isinstance(page, dict)
        ),
        "hash": sha256_json(view),
    }
