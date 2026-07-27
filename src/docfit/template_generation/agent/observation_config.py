"""Configuration shared by replay and live observation execution."""

from __future__ import annotations

from dataclasses import dataclass


class ObservationConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ObservationConfig:
    model: str = "replay"
