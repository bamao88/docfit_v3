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

from .evidence import build_t2_evidence, build_t3_evidence, build_t4_evidence
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


class ObservationResponder(Protocol):
    """三阶段原始 payload 的来源（replay 取自 transcript / live 调真实模型）。"""

    def fetch_units(self, *, evidence: dict[str, Any], n_samples: int) -> list[dict[str, Any]]: ...

    def fetch_elements(self, *, evidence: dict[str, Any], window: dict[str, Any]) -> dict[str, Any]: ...

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

    valid_seq = packet_source_seq_set(packet)
    timing: dict[str, float] = {}
    pipeline_start = time.monotonic()

    # --- Pass-T2：全文压缩 → 自一致性投票 → 物化 ---
    t2_start = time.monotonic()
    t2_evidence = build_t2_evidence(packet)  # firewall asserted inside
    samples = responder.fetch_units(evidence=t2_evidence, n_samples=config.self_consistency_samples)
    unit_observation, t2_consistency = _run_t2(
        samples=samples, packet=packet, valid_seq=valid_seq, model=config.model
    )
    timing["t2_seconds"] = round(time.monotonic() - t2_start, 2)

    # --- Pass-T3：按 AI 自己的 T2 单元切窗口 → 物化 ---
    t3_start = time.monotonic()
    unit_windows = build_observation_windows(ai_unit_observation=unit_observation, packet=packet)
    element_observation = _run_t3(
        responder=responder,
        unit_windows=unit_windows,
        packet=packet,
        valid_seq=valid_seq,
        model=config.model,
        concurrency=t3_concurrency,
    )
    timing["t3_seconds"] = round(time.monotonic() - t3_start, 2)

    # --- Pass-T4：Track A 确定性版式(T1 分节事实) + 渲染 per-seq page_no
    # + Track B 视觉逐页读图(MiniMax M3, 有 vision_responder 且有页图时) ---
    t4_start = time.monotonic()
    t4_evidence = build_t4_evidence(packet)
    render_available = bool(t4_evidence.get("render_available"))
    page_observations: list[dict[str, Any]] = []
    if vision_responder is not None and render_available:
        page_images = (packet.get("render_artifacts", {}) or {}).get("clean_page_images", []) or []
        page_observations = vision_responder.observe_pages(page_images)
    layout_observation = materialize_layout_observation(
        {"section_profiles": []},
        packet=packet,
        render_available=render_available,
        model=config.model,
        page_observations=page_observations,
    )
    timing["t4_seconds"] = round(time.monotonic() - t4_start, 2)
    timing["total_seconds"] = round(time.monotonic() - pipeline_start, 2)

    return {
        "artifact_type": "ai_observation_bundle",
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "created_at": now_iso(),
        "source_render_hash": packet.get("source_render_hash"),
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

    def observe(window: dict[str, Any]) -> dict[str, Any]:
        # 第一相同样独立：T3 看的是按 AI 单元裁出的窗口证据（firewall asserted）。
        t3_evidence = build_t3_evidence(packet, window=window)
        payload = responder.fetch_elements(evidence=t3_evidence, window=window)
        raw_items = list(payload.get("items", []) or [])
        return materialize_element_observation(
            raw_items, packet=packet, window=window, model=model
        )

    if concurrency > 1 and len(windows) > 1:
        # 各单元窗口互相独立 → 可并发；保持输入顺序聚合，结果确定。
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            observations = list(pool.map(observe, windows))
    else:
        observations = [observe(window) for window in windows]

    items: list[dict[str, Any]] = []
    unknown_items: list[dict[str, Any]] = []
    demotions: list[dict[str, Any]] = []
    for observation in observations:
        items.extend(observation.get("items", []))
        unknown_items.extend(observation.get("unknown_items", []))
        demotions.extend(observation.get("quality_report", {}).get("demotions", []))

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
        "quality_report": {
            "demotions": demotions,
            "owned_count": len(coverage.get("owned_source_seq", [])),
            "unknown_count": len(coverage.get("unknown_source_seq", [])),
            "window_source": unit_windows.get("window_source"),
            "post_t2_observation_hash": unit_windows.get("post_t2_observation_hash"),
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
