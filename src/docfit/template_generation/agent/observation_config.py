"""Module 1 独立观察流水线的配置（replay-only，default-off）。

本轮范围只覆盖 replay 核心：固定 render packet + 固定模型响应 → 三份 observation。
live(kimi/minimax)、响应缓存、CLI ``template-observe`` 子命令均 out of scope。

default-off 不变量：不显式构造 ``ObservationConfig(enabled=True, ...)`` 时，主流程
不产出任何 observation artifact，现有输出与测试保持不变。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ObservationTransportName = Literal["replay"]
SUPPORTED_OBSERVATION_TRANSPORTS = {"replay"}


class ObservationConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ObservationConfig:
    enabled: bool = False
    transport: ObservationTransportName = "replay"
    # 自一致性多采样：N 份 submission 按 source_seq 多数投票（Phase 3 消费）。
    self_consistency_samples: int = 1
    transcript_path: Path | None = None
    model: str = "replay"
    # live 推理模式开关：默认 OFF——接地 prompt（1.1）下 thinking-off 质量已追平 thinking-on
    # 且快约 10×（实测 hunannongye：16 单元 / 0 闸门违规 / 满覆盖 / 103s）。需要时显式置 True。
    thinking: bool = False


def validate_observation_config(config: ObservationConfig) -> list[str]:
    if not config.enabled:
        return []

    errors: list[str] = []
    if config.transport not in SUPPORTED_OBSERVATION_TRANSPORTS:
        errors.append(
            "observation transport must be 'replay' this round "
            f"(got {config.transport!r}); live is out of scope"
        )
    if config.self_consistency_samples < 1:
        errors.append("observation self_consistency_samples must be >= 1")
    if config.transport == "replay":
        if config.transcript_path is None:
            errors.append("replay observation requires transcript_path")
        elif not config.transcript_path.exists():
            errors.append(
                f"observation transcript_path does not exist: {config.transcript_path}"
            )
    return errors
