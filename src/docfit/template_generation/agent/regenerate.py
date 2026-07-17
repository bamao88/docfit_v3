from __future__ import annotations

from typing import Any

from docfit.template_generation.artifacts import build_element_spec, build_unit_map
from docfit.template_generation.generation_model import build_template_generation_model


def regenerate_from_structure_candidates(
    *,
    request: dict[str, Any],
    document_facts: dict[str, Any],
    structure_candidates: dict[str, Any],
) -> dict[str, Any]:
    unit_map = build_unit_map(
        document_facts,
        structure_candidates,
        l1_hash=document_facts.get("input_hashes", {}).get("l1"),
    )
    generation_model = build_template_generation_model(
        request,
        structure_candidates=structure_candidates,
    )
    element_spec = build_element_spec(generation_model)
    return {
        "unit_map": unit_map,
        "generation_model": generation_model,
        "element_spec": element_spec,
    }
