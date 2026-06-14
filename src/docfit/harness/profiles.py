from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvalProfile:
    profile_id: str
    required_capabilities: dict[str, tuple[str, ...]]
    expected_dir: Path
    expected_placement_plan: Path
    expected_feature_snapshot: Path

    def capabilities_for_stage(self, stage: str) -> list[str]:
        return list(self.required_capabilities[stage])

    def all_required_capabilities(self) -> list[str]:
        return [
            capability
            for stage_capabilities in self.required_capabilities.values()
            for capability in stage_capabilities
        ]

    def expected_paths(self, root: Path) -> dict[str, Path]:
        return {
            "placement_plan": root / self.expected_placement_plan,
            "feature_snapshot": root / self.expected_feature_snapshot,
        }


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    school_id: str
    student_docx: Path
    expected_status: str
    profile_id: str


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
    expected_dir=Path("standards/eval_profiles/bootstrap-core/expected"),
    expected_placement_plan=Path(
        "standards/eval_profiles/bootstrap-core/expected/placement_plan.json"
    ),
    expected_feature_snapshot=Path(
        "standards/eval_profiles/bootstrap-core/expected/feature_snapshot.json"
    ),
)

BOOTSTRAP_TEMPLATE_DOCX = Path("inputs/bootstrap-demo-school-template.docx")
BOOTSTRAP_PASS_STUDENT_DOCX = Path("inputs/bootstrap-demo-student-pass.docx")
BOOTSTRAP_UNSUPPORTED_TEXTBOX_DOCX = Path(
    "inputs/bootstrap-demo-student-unsupported-textbox.docx"
)
BOOTSTRAP_SILENT_DROP_DOCX = Path("inputs/bootstrap-demo-student-silent-drop.docx")

BOOTSTRAP_E2E_PASS_CASE = EvalCase(
    case_id="bootstrap_e2e_demo_001",
    school_id="demo-school",
    student_docx=BOOTSTRAP_PASS_STUDENT_DOCX,
    expected_status="PASS",
    profile_id=BOOTSTRAP_PROFILE.profile_id,
)

PROFILES = {BOOTSTRAP_PROFILE.profile_id: BOOTSTRAP_PROFILE}
EVAL_CASES = {BOOTSTRAP_E2E_PASS_CASE.case_id: BOOTSTRAP_E2E_PASS_CASE}


def get_eval_profile(profile_id: str) -> EvalProfile | None:
    return PROFILES.get(profile_id)


def get_eval_case(case_id: str) -> EvalCase | None:
    return EVAL_CASES.get(case_id)
