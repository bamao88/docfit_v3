"""Module 1 独立观察流水线（responder 驱动；replay 与 live 共用编排）。

三阶段 pass，每阶段产物即终稿（不 patch 代码结构）：

  Pass-T2 : clean evidence 全文压缩 → 自一致性 N 投票 → 物化 → ai_unit_observation
  Pass-T3 : 按【AI 自己的 T2 单元】切窗口 → 物化 → ai_element_observation
  Pass-T4 : 真实页图（否则 abstain） → 物化 → ai_layout_observation

编排只认一个 ``responder`` 抽象：

  - ``ReplayResponder``（确定性回归护栏）从 transcript 取原始 payload；
  - ``LiveResponder``（真实模型，见 observation_live）逐阶段调用 OpenAI 兼容端点。

关键：T3 prompt 依赖 T2 的真实输出（AI 自己的单元），所以 live 必须在 T2 调用拿到
结果后再发 T3——这正是 responder 内联在编排里、而非预先攒好整包 transcript 的原因。
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Protocol

from docfit.core.io import now_iso, sha256_json

from .evidence import build_t2_evidence, build_t4_evidence
from .observation_config import ObservationConfig, ObservationConfigError
from .observation_materialize import (
    materialize_element_observation,
    materialize_layout_observation,
    materialize_unit_observation,
)
from .observation_schema import (
    OBSERVATION_SCHEMA_VERSION,
    OBSERVATION_STAGES,
    PROMPT_CONTRACT_VERSION,
    UNKNOWN_UNIT_ID,
    compute_coverage,
    open_questions_from,
)
from .observation_windows import build_observation_windows
from .packet import packet_source_seq_set
from .t3_input import (
    build_t3_local_evidence,
    build_t3_local_tasks,
    build_t3_unit_plan_evidence,
    sanitize_unit_plan,
    task_summary,
)
from .t3_safety import (
    guard_t3_payload,
    preservation_fallback_items,
    restrict_tasks_to_unit_plan,
)


class ObservationResponder(Protocol):
    """三阶段原始 payload 的来源（replay 取自 transcript / live 调真实模型）。"""

    def fetch_units(self, *, evidence: dict[str, Any], n_samples: int) -> list[dict[str, Any]]: ...

    def fetch_elements(self, *, evidence: dict[str, Any], window: dict[str, Any]) -> dict[str, Any]: ...

    def fetch_unit_plan(self, *, evidence: dict[str, Any], window: dict[str, Any]) -> dict[str, Any]: ...

    def fetch_layout(self, *, evidence: dict[str, Any]) -> dict[str, Any]: ...


class ReplayResponder:
    """从手写/录制的 transcript 取原始 payload —— 仅作确定性回归护栏，非产品口径。"""

    def __init__(self, transcript: dict[str, Any]) -> None:
        self._transcript = transcript or {}

    def fetch_units(self, *, evidence: dict[str, Any], n_samples: int) -> list[dict[str, Any]]:
        del evidence
        return list(self._transcript.get("t2", []) or [])[: max(1, n_samples)]

    def fetch_elements(self, *, evidence: dict[str, Any], window: dict[str, Any]) -> dict[str, Any]:
        del evidence
        unit_id = str(window.get("unit_id") or "")
        return dict((self._transcript.get("t3", {}) or {}).get(unit_id, {}) or {})

    def fetch_unit_plan(self, *, evidence: dict[str, Any], window: dict[str, Any]) -> dict[str, Any]:
        """Replay follows the canonical unit router without retaining a flat T3 path.

        Older transcripts contain only final T3 items.  They are replayed through
        ``full_local_analysis`` so the current routing and safety gates remain in
        force; newer fixtures may provide a per-unit plan explicitly.
        """

        del evidence
        unit_id = str(window.get("unit_id") or "")
        plans = self._transcript.get("t3_unit", {}) or {}
        recorded = plans.get(unit_id) if isinstance(plans, dict) else None
        if isinstance(recorded, dict):
            return dict(recorded)
        return {
            "route": "full_local_analysis",
            "default_preservation_policy": "fixed",
            "inspect_source_seq_refs": list(window.get("source_seq_refs", []) or []),
            "confidence": "medium",
            "rationale": "legacy transcript replayed through canonical unit route",
        }

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

    config = config or ObservationConfig(enabled=True)
    if config.self_consistency_samples < 1:
        raise ObservationConfigError("observation self_consistency_samples must be >= 1")
    if responder is None:
        responder = ReplayResponder(transcript or {})

    timing: dict[str, float] = {}
    pipeline_start = time.monotonic()

    # --- Pass-T2：全文压缩 → 自一致性投票 → 物化 ---
    t2_start = time.monotonic()
    unit_observation, t2_consistency, t2_evidence = run_t2_observation(
        packet=packet,
        responder=responder,
        config=config,
    )
    timing["t2_seconds"] = round(time.monotonic() - t2_start, 2)

    # --- Pass-T3：按 AI 自己的 T2 单元切窗口 → 物化 ---
    t3_start = time.monotonic()
    element_observation, unit_windows = run_t3_observation(
        ai_unit_observation=unit_observation,
        responder=responder,
        packet=packet,
        config=config,
        concurrency=t3_concurrency,
    )
    timing["t3_seconds"] = round(time.monotonic() - t3_start, 2)

    # --- Pass-T4：Track A 确定性版式(T1 分节事实) + 渲染 per-seq page_no
    # + Track B 视觉逐页读图(MiniMax M3, 有 vision_responder 且有页图时) ---
    t4_start = time.monotonic()
    replay_layout_payload = (
        responder.fetch_layout(evidence=build_t4_evidence(packet))
        if isinstance(responder, ReplayResponder)
        else None
    )
    layout_observation, t4_evidence = run_t4_observation(
        packet=packet,
        config=config,
        vision_responder=vision_responder,
        raw_payload=replay_layout_payload,
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
        "self_consistency_samples": config.self_consistency_samples,
        "ai_unit_observation": unit_observation,
        "ai_element_observation": element_observation,
        "ai_layout_observation": layout_observation,
        "unit_windows": unit_windows,
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

    if config.self_consistency_samples < 1:
        raise ObservationConfigError("observation self_consistency_samples must be >= 1")
    evidence = build_t2_evidence(packet)
    samples = responder.fetch_units(
        evidence=evidence,
        n_samples=config.self_consistency_samples,
    )
    observation, consistency = _run_t2(
        samples=samples,
        packet=packet,
        valid_seq=packet_source_seq_set(packet),
        model=config.model,
    )
    observation["input_contract_hash"] = packet.get("input_contract_hash")
    return observation, consistency, evidence


def run_t3_observation(
    *,
    packet: dict[str, Any],
    ai_unit_observation: dict[str, Any],
    responder: ObservationResponder,
    config: ObservationConfig,
    concurrency: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run only T3, using an AI-produced T2 observation as its window source."""

    unit_windows = build_observation_windows(
        ai_unit_observation=ai_unit_observation,
        packet=packet,
    )
    observation = _run_t3(
        responder=responder,
        unit_windows=unit_windows,
        packet=packet,
        valid_seq=packet_source_seq_set(packet),
        model=config.model,
        concurrency=concurrency,
    )
    observation["input_contract_hash"] = packet.get("input_contract_hash")
    unit_windows["input_contract_hash"] = packet.get("input_contract_hash")
    return observation, unit_windows


def run_t4_observation(
    *,
    packet: dict[str, Any],
    config: ObservationConfig,
    vision_responder: Any = None,
    raw_payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run only T4; a live vision responder consumes the rendered page images."""

    evidence = build_t4_evidence(packet)
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
    valid_seq: set[int],
    model: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not samples:
        observation = materialize_unit_observation([], packet=packet, model=model)
        return observation, {"samples": 0, "agreement": {}}

    if len(samples) == 1:
        observation = materialize_unit_observation(
            list(samples[0].get("items", []) or []), packet=packet, model=model
        )
        return observation, {"samples": 1, "agreement": {}}

    voted_items, consistency = _vote_units(samples, valid_seq=valid_seq)
    observation = materialize_unit_observation(
        voted_items, packet=packet, model=model, self_consistency=consistency
    )
    return observation, consistency


def _vote_units(
    samples: list[dict[str, Any]],
    *,
    valid_seq: set[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """每 source_seq 跨样本多数投票 unit_id；ratio→confidence，平票→unknown。"""

    total = len(samples)
    votes: dict[int, dict[str, int]] = {seq: {} for seq in valid_seq}
    for sample in samples:
        for item in sample.get("items", []) or []:
            unit_id = str(item.get("unit_id") or "")
            for seq in _ints(item.get("source_seq_refs")):
                if seq in votes:
                    votes[seq][unit_id] = votes[seq].get(unit_id, 0) + 1

    seq_to_unit: dict[int, str] = {}
    agreement: dict[str, float] = {}
    for seq in sorted(valid_seq):
        tally = votes.get(seq, {})
        if not tally:
            # 无人认领的 seq 直接 unknown；不写进 agreement（避免 0.0 噪声）。
            seq_to_unit[seq] = UNKNOWN_UNIT_ID
            continue
        top_count = max(tally.values())
        leaders = [unit_id for unit_id, count in tally.items() if count == top_count]
        ratio = top_count / total
        if len(leaders) != 1 or ratio < 0.5:
            seq_to_unit[seq] = UNKNOWN_UNIT_ID
        else:
            seq_to_unit[seq] = leaders[0]
        agreement[str(seq)] = round(ratio, 3)

    items = _group_contiguous(seq_to_unit, agreement)
    consistency = {
        "samples": total,
        "agreement": agreement,
        "rule": ">=0.8 high / >=0.5 medium / tie or <0.5 unknown",
    }
    return items, consistency


def _group_contiguous(
    seq_to_unit: dict[int, str],
    agreement: dict[str, float],
) -> list[dict[str, Any]]:
    """把连续且同 unit_id 的 source_seq 合并成 item，confidence 由一致率定档。"""

    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for seq in sorted(seq_to_unit):
        unit_id = seq_to_unit[seq]
        if unit_id == UNKNOWN_UNIT_ID:
            current = None
            continue
        ratio = agreement.get(str(seq), 0.0)
        confidence = "high" if ratio >= 0.8 else "medium"
        if current and current["unit_id"] == unit_id and seq == current["source_seq_refs"][-1] + 1:
            current["source_seq_refs"].append(seq)
            current["_ratios"].append(ratio)
        else:
            current = {"unit_id": unit_id, "source_seq_refs": [seq], "_ratios": [ratio], "confidence": confidence}
            items.append(current)
    # 整 item confidence = 段内最低档（保守）。
    for item in items:
        ratios = item.pop("_ratios", [1.0])
        worst = min(ratios)
        item["confidence"] = "high" if worst >= 0.8 else "medium"
        item["order"] = item["source_seq_refs"][0]
    return items


def _run_t3(
    *,
    responder: ObservationResponder,
    unit_windows: dict[str, Any],
    packet: dict[str, Any],
    valid_seq: set[int],
    model: str,
    concurrency: int = 1,
) -> dict[str, Any]:
    windows = [w for w in unit_windows.get("windows", []) if isinstance(w, dict)]
    return _run_t3_unit_routed(
        responder=responder,
        windows=windows,
        unit_windows=unit_windows,
        packet=packet,
        valid_seq=valid_seq,
        model=model,
        concurrency=concurrency,
    )


def _run_t3_unit_routed(
    *,
    responder: ObservationResponder,
    windows: list[dict[str, Any]],
    unit_windows: dict[str, Any],
    packet: dict[str, Any],
    valid_seq: set[int],
    model: str,
    concurrency: int,
) -> dict[str, Any]:
    """整单元先看图和对象清单，再按 route 条件下钻。"""

    tasks = build_t3_local_tasks(packet, unit_windows=windows)
    unit_windows["local_tasks"] = [task_summary(task) for task in tasks]
    tasks_by_window: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        tasks_by_window.setdefault(str(task.get("parent_window_id") or ""), []).append(task)

    def observe_unit(window: dict[str, Any]) -> dict[str, Any]:
        unit_tasks = tasks_by_window.get(str(window.get("window_id") or ""), [])
        plan_evidence = build_t3_unit_plan_evidence(
            packet,
            unit_window=window,
            tasks=unit_tasks,
        )
        raw_plan = responder.fetch_unit_plan(evidence=plan_evidence, window=window)
        unit_plan = sanitize_unit_plan(raw_plan, unit_window=window)
        routed_tasks = restrict_tasks_to_unit_plan(unit_tasks, unit_plan)
        observations: list[dict[str, Any]] = []
        guard_demotions: list[dict[str, Any]] = []
        local_task_analysis: list[dict[str, Any]] = []

        for task in routed_tasks:
            executed_windows: list[dict[str, Any]] = []

            def observe_local(local_window: dict[str, Any], *, retry_depth: int = 0) -> None:
                evidence = build_t3_local_evidence(
                    packet,
                    task=task,
                    local_window=local_window,
                    unit_plan=unit_plan,
                )
                payload = responder.fetch_elements(evidence=evidence, window=local_window)
                refs = list(local_window.get("source_seq_refs", []) or [])
                if payload.get("_observation_error") and len(refs) > 1 and retry_depth < 3:
                    for split_window in _split_failed_t3_window(local_window):
                        observe_local(split_window, retry_depth=retry_depth + 1)
                    return
                payload, blocked = guard_t3_payload(
                    payload,
                    evidence=evidence,
                    unit_plan=unit_plan,
                )
                guard_demotions.extend(blocked)
                executed_windows.append(local_window)
                observations.append(
                    materialize_element_observation(
                        list(payload.get("items", []) or []),
                        packet=packet,
                        window=local_window,
                        model=model,
                    )
                )

            for local_window in task.get("local_windows", []):
                observe_local(local_window)
            local_task_analysis.append(
                {
                    **task_summary(task),
                    "executed_local_windows": [
                        {
                            "window_id": local.get("window_id"),
                            "source_seq_refs": local.get("source_seq_refs", []),
                            "context_source_seq_refs": local.get("context_source_seq_refs", []),
                        }
                        for local in executed_windows
                    ],
                }
            )

        existing_items = [
            item
            for observation in observations
            for item in observation.get("items", [])
        ]
        fallback = preservation_fallback_items(
            packet,
            unit_window=window,
            unit_plan=unit_plan,
            existing_items=existing_items,
        )
        if fallback:
            observations.append(
                materialize_element_observation(
                    fallback,
                    packet=packet,
                    window=window,
                    model=model,
                )
            )
        return {
            "unit_analysis": {
                "window_id": window.get("window_id"),
                "unit_id": window.get("unit_id"),
                "source_seq_refs": window.get("source_seq_refs", []),
                "unit_plan": unit_plan,
                "local_task_count": len(unit_tasks),
                "routed_local_task_count": len(routed_tasks),
                "executed_local_window_count": sum(
                    len(item.get("executed_local_windows", [])) for item in local_task_analysis
                ),
                "fallback_item_count": len(fallback),
            },
            "local_task_analysis": local_task_analysis,
            "observations": observations,
            "guard_demotions": guard_demotions,
        }

    if concurrency > 1 and len(windows) > 1:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(observe_unit, windows))
    else:
        results = [observe_unit(window) for window in windows]

    items: list[dict[str, Any]] = []
    unknown_items: list[dict[str, Any]] = []
    demotions: list[dict[str, Any]] = []
    local_task_analysis: list[dict[str, Any]] = []
    unit_analysis: list[dict[str, Any]] = []
    for result in results:
        unit_analysis.append(result["unit_analysis"])
        local_task_analysis.extend(result["local_task_analysis"])
        demotions.extend(result["guard_demotions"])
        for observation in result["observations"]:
            items.extend(observation.get("items", []))
            unknown_items.extend(observation.get("unknown_items", []))
            demotions.extend(observation.get("quality_report", {}).get("demotions", []))

    return _finalize_t3_observation(
        items=items,
        unknown_items=unknown_items,
        demotions=demotions,
        local_task_analysis=local_task_analysis,
        unit_analysis=unit_analysis,
        unit_windows=unit_windows,
        packet=packet,
        valid_seq=valid_seq,
        model=model,
        input_mode="unit_route_then_conditional_local",
    )


def _split_failed_t3_window(window: dict[str, Any]) -> list[dict[str, Any]]:
    """模型连续返回无效 JSON 时缩小 claim 范围；保持上下文只读和唯一 owner。"""

    refs = list(window.get("source_seq_refs", []) or [])
    midpoint = max(1, len(refs) // 2)
    left_refs = refs[:midpoint]
    right_refs = refs[midpoint:]
    base_context = list(window.get("context_source_seq_refs", []) or [])
    return [
        {
            **window,
            "window_id": f"{window.get('window_id')}:retry_a",
            "source_seq_refs": left_refs,
            "context_source_seq_refs": sorted(
                set(base_context + ([right_refs[0]] if right_refs else [])) - set(left_refs)
            ),
        },
        {
            **window,
            "window_id": f"{window.get('window_id')}:retry_b",
            "source_seq_refs": right_refs,
            "context_source_seq_refs": sorted(
                set(base_context + ([left_refs[-1]] if left_refs else [])) - set(right_refs)
            ),
        },
    ]


def _finalize_t3_observation(
    *,
    items: list[dict[str, Any]],
    unknown_items: list[dict[str, Any]],
    demotions: list[dict[str, Any]],
    local_task_analysis: list[dict[str, Any]],
    unit_analysis: list[dict[str, Any]],
    unit_windows: dict[str, Any],
    packet: dict[str, Any],
    valid_seq: set[int],
    model: str,
    input_mode: str,
) -> dict[str, Any]:
    coverage = compute_coverage(items, all_source_seq=valid_seq)
    return {
        "artifact_type": "ai_element_observation",
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "stage": OBSERVATION_STAGES["ai_element_observation"],
        "source_render_hash": packet.get("source_render_hash"),
        "model": model,
        "created_at": now_iso(),
        "coverage": coverage,
        "items": items,
        "unknown_items": unknown_items,
        "open_questions": open_questions_from(demotions=demotions, coverage=coverage),
        "abstain": not items,
        "self_consistency": None,
        "local_task_analysis": local_task_analysis,
        "unit_analysis": unit_analysis,
        "quality_report": {
            "demotions": demotions,
            "owned_count": len(coverage.get("owned_source_seq", [])),
            "unknown_count": len(coverage.get("unknown_source_seq", [])),
            "window_source": unit_windows.get("window_source"),
            "post_t2_observation_hash": unit_windows.get("post_t2_observation_hash"),
            "input_mode": input_mode,
            "local_task_count": len(local_task_analysis),
            "unit_count": len(unit_analysis),
            "route_counts": {
                route: sum(
                    1
                    for analysis in unit_analysis
                    if analysis.get("unit_plan", {}).get("route") == route
                )
                for route in sorted(
                    {
                        str(analysis.get("unit_plan", {}).get("route"))
                        for analysis in unit_analysis
                        if analysis.get("unit_plan", {}).get("route")
                    }
                )
            },
        },
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
    return {
        "abstain": observation.get("abstain"),
        "owned": len(coverage.get("owned_source_seq", [])),
        "unknown": len(coverage.get("unknown_source_seq", [])),
        "total": coverage.get("total"),
        "items": len(observation.get("items", [])),
        "demotions": len(observation.get("quality_report", {}).get("demotions", [])),
    }


def _scope_summary(view: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope": view.get("scope"),
        "rows": len(view.get("rows", [])),
        "hash": sha256_json(view),
    }


def _ints(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    result: list[int] = []
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            result.append(value)
        elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
            result.append(int(value))
    return result
