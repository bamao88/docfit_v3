from __future__ import annotations

from typing import Any

from docfit.harness.baselines import load_baseline_file
from docfit.harness.standards import StandardBundle


def load_template_unit_baseline(
    bundle: StandardBundle,
    *,
    stage: str,
    start_index: int = 1,
) -> tuple[dict[str, Any] | None, list]:
    rel_path = bundle.signed_standard.get("evidence_baselines", {}).get(
        "template_generation_final",
        "template_quality/final_template.expected.yaml",
    )
    return load_baseline_file(
        bundle.school_dir / rel_path,
        stage=stage,
        start_index=start_index,
    )


def accepted_expected_artifact(baseline: dict[str, Any]) -> dict[str, Any]:
    expected = baseline.get("expected")
    return expected if isinstance(expected, dict) else {}
