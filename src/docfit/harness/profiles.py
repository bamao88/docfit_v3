from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvalProfile:
    profile_id: str
    required_capabilities: dict[str, tuple[str, ...]]

    def capabilities_for_stage(self, stage: str) -> list[str]:
        return list(self.required_capabilities[stage])

    def all_required_capabilities(self) -> list[str]:
        return [
            capability
            for stage_capabilities in self.required_capabilities.values()
            for capability in stage_capabilities
        ]


BOOTSTRAP_PROFILE = EvalProfile(
    profile_id="bootstrap-core",
    required_capabilities={
        "template": (
            "template.docx_openable",
            "template.required_regions",
            "template.required_slots",
            "template.styles_inventory",
        ),
        "content": (
            "content.visible_paragraphs",
            "content.visible_tables",
            "content.reading_order",
            "content.stable_ids",
        ),
        "placement": (
            "placement.no_silent_drop",
            "placement.slot_compatibility",
            "placement.required_slots",
        ),
        "render": (
            "render.valid_docx_package",
            "render.plan_coverage",
            "render.feature_snapshot",
            "render.content_hash_coverage",
        ),
    },
)

REAL_CORE_PROFILE = EvalProfile(
    profile_id="real-core-v0",
    required_capabilities={
        "template": (
            "template.unit_tree",
            "template.element_order",
            "template.style_dimensions",
            "template.review_metadata",
            "template.comparator_policy",
        ),
        "content": (
            "content.visible_content_tree",
            "content.body_flow",
            "content.source_hashes",
            "content.unsupported_disposition",
            "content.comparator_policy",
        ),
        "placement": (
            "placement.disposition_coverage",
            "placement.no_silent_drop",
            "placement.fixed_content_policy",
            "placement.manual_only_policy",
            "placement.comparator_policy",
        ),
        "render": (
            "render.valid_docx_package",
            "render.manifest_coverage",
            "render.feature_snapshot",
            "render.word_image_evidence",
            "render.ai_advisory_boundary",
        ),
    },
)

REAL_CORE_SCHOOLS = (
    {
        "school_id": "hunannongye",
        "template_docx": Path("inputs/targets/hunannongye/raw/source_template.docx"),
        "generated_template_docx": Path(
            "inputs/targets/hunannongye/fixtures/template_gap/generated_template.input.docx"
        ),
    },
    {
        "school_id": "nannong-undergraduate",
        "template_docx": Path(
            "inputs/targets/nannong-undergraduate/raw/source_template.docx"
        ),
        "generated_template_docx": Path(
            "inputs/targets/nannong-undergraduate/fixtures/template_gap/"
            "generated_template.input.docx"
        ),
    },
    {
        "school_id": "pku-graduate",
        "template_docx": Path("inputs/targets/pku-graduate/raw/source_template.docx"),
        "generated_template_docx": Path(
            "inputs/targets/pku-graduate/fixtures/template_gap/generated_template.input.docx"
        ),
    },
)

PROFILES = {
    BOOTSTRAP_PROFILE.profile_id: BOOTSTRAP_PROFILE,
    REAL_CORE_PROFILE.profile_id: REAL_CORE_PROFILE,
}


def get_eval_profile(profile_id: str) -> EvalProfile | None:
    return PROFILES.get(profile_id)
