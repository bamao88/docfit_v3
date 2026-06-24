from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file

from .constants import DEFAULT_TEMPLATE_GENERATION_STRATEGY


def build_template_generation_request(
    source_template_docx: Path,
    out_dir: Path,
    *,
    strategy: str = DEFAULT_TEMPLATE_GENERATION_STRATEGY,
) -> dict[str, Any]:
    return {
        "artifact_type": "template_generation_request",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "source_template_docx": str(source_template_docx),
        "source_template_hash": sha256_file(source_template_docx),
        "out_dir": str(out_dir),
        "strategy": strategy,
        "optional_labels": {},
    }
