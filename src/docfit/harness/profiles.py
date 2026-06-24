from __future__ import annotations

from dataclasses import dataclass
from itertools import product
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
    student_docx: Path | None
    expected_status: str
    profile_id: str
    stage: str = "e2e"
    template_docx: Path | None = None
    generated_template_docx: Path | None = None
    student_id: str | None = None
    template_version: str = "v1"


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
    expected_dir=Path("standards/cases/demo-school__bootstrap-demo/v1"),
    expected_placement_plan=Path(
        "standards/cases/demo-school__bootstrap-demo/v1/placement/placement_plan.expected.json"
    ),
    expected_feature_snapshot=Path(
        "standards/cases/demo-school__bootstrap-demo/v1/render/feature_snapshot.expected.json"
    ),
)

BOOTSTRAP_TEMPLATE_DOCX = Path(
    "inputs/targets/demo-school/raw/source_template.docx"
)
BOOTSTRAP_PASS_STUDENT_DOCX = Path(
    "inputs/students/bootstrap-demo-pass/raw/source_document.docx"
)
BOOTSTRAP_UNSUPPORTED_TEXTBOX_DOCX = Path(
    "inputs/students/bootstrap-demo-unsupported-textbox/raw/source_document.docx"
)
BOOTSTRAP_SILENT_DROP_DOCX = Path(
    "inputs/students/bootstrap-demo-silent-drop/raw/source_document.docx"
)

BOOTSTRAP_E2E_PASS_CASE = EvalCase(
    case_id="demo-school__bootstrap-demo",
    school_id="demo-school",
    student_docx=BOOTSTRAP_PASS_STUDENT_DOCX,
    expected_status="PASS",
    profile_id=BOOTSTRAP_PROFILE.profile_id,
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
    expected_dir=Path("standards"),
    expected_placement_plan=Path("standards/cases"),
    expected_feature_snapshot=Path("standards/cases"),
)

REAL_CORE_SCHOOLS = (
    {
        "school_id": "hunannongye",
        "template_docx": Path(
            "inputs/targets/hunannongye/raw/source_template.docx"
        ),
        "generated_template_docx": Path(
            "inputs/targets/hunannongye/fixtures/template_gap/generated_template.input.docx"
        ),
        "review_source": Path(
            "inputs/targets/hunannongye/raw/source_review.md"
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
        "review_source": Path(
            "inputs/targets/nannong-undergraduate/raw/source_review.md"
        ),
    },
    {
        "school_id": "pku-graduate",
        "template_docx": Path(
            "inputs/targets/pku-graduate/raw/source_template.docx"
        ),
        "generated_template_docx": Path(
            "inputs/targets/pku-graduate/fixtures/template_gap/generated_template.input.docx"
        ),
        "review_source": Path(
            "inputs/targets/pku-graduate/raw/source_review.md"
        ),
    },
)

REAL_CORE_STUDENTS = (
    {
        "student_id": "real-student-001",
        "student_docx": Path("inputs/students/real-student-001/raw/source_document.docx"),
        "review_source": Path("inputs/students/real-student-001/raw/content_review.md"),
    },
    {
        "student_id": "real-student-002",
        "student_docx": Path("inputs/students/real-student-002/raw/source_document.docx"),
        "review_source": Path("inputs/students/real-student-002/raw/content_review.md"),
    },
    {
        "student_id": "real-student-003",
        "student_docx": Path("inputs/students/real-student-003/raw/source_document.docx"),
        "review_source": Path("inputs/students/real-student-003/raw/content_review.md"),
    },
)


def _real_core_template_cases() -> tuple[EvalCase, ...]:
    return tuple(
        EvalCase(
            case_id=f"real_core_v0_template_{school['school_id']}",
            school_id=str(school["school_id"]),
            student_docx=None,
            expected_status="UNKNOWN",
            profile_id=REAL_CORE_PROFILE.profile_id,
            stage="template",
            template_docx=school["template_docx"],
            generated_template_docx=school["generated_template_docx"],
        )
        for school in REAL_CORE_SCHOOLS
    )


def _real_core_content_cases() -> tuple[EvalCase, ...]:
    return tuple(
        EvalCase(
            case_id=f"real_core_v0_content_{student['student_id']}",
            school_id="",
            student_docx=student["student_docx"],
            expected_status="UNKNOWN",
            profile_id=REAL_CORE_PROFILE.profile_id,
            stage="content",
            student_id=str(student["student_id"]),
        )
        for student in REAL_CORE_STUDENTS
    )


def _real_core_e2e_cases() -> tuple[EvalCase, ...]:
    cases: list[EvalCase] = []
    for school, student in product(REAL_CORE_SCHOOLS, REAL_CORE_STUDENTS):
        cases.append(
            EvalCase(
                case_id=(
                    f"{school['school_id']}__{student['student_id']}"
                ),
                school_id=str(school["school_id"]),
                student_docx=student["student_docx"],
                expected_status="UNKNOWN",
                profile_id=REAL_CORE_PROFILE.profile_id,
                stage="e2e",
                template_docx=school["template_docx"],
                generated_template_docx=school["generated_template_docx"],
                student_id=str(student["student_id"]),
            )
        )
    return tuple(cases)


REAL_CORE_CASES = (
    *_real_core_template_cases(),
    *_real_core_content_cases(),
    *_real_core_e2e_cases(),
)

PROFILES = {
    BOOTSTRAP_PROFILE.profile_id: BOOTSTRAP_PROFILE,
    REAL_CORE_PROFILE.profile_id: REAL_CORE_PROFILE,
}
EVAL_CASES = {
    BOOTSTRAP_E2E_PASS_CASE.case_id: BOOTSTRAP_E2E_PASS_CASE,
    **{case.case_id: case for case in REAL_CORE_CASES},
}


def get_eval_profile(profile_id: str) -> EvalProfile | None:
    return PROFILES.get(profile_id)


def get_eval_case(case_id: str) -> EvalCase | None:
    return EVAL_CASES.get(case_id)


def get_eval_cases_for_profile(profile_id: str) -> list[EvalCase]:
    return [case for case in EVAL_CASES.values() if case.profile_id == profile_id]
