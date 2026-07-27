from __future__ import annotations

from typing import Any

from docfit.core.io import now_iso


def build_t3_materialization_trace(
    materialization: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "t3_materialization_trace",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "authority": "ai",
        "purpose": "materialization_self_check",
        "materialization": materialization,
    }
