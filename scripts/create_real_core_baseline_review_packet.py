from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from docfit.core.io import ensure_dir, sha256_file, write_json, write_text
from docfit.harness.profiles import REAL_CORE_SCHOOLS, REAL_CORE_STUDENTS, get_eval_cases_for_profile


ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "real-core-v0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "out/real-core-v0-baseline-review",
        help="Review packet output directory. Defaults to ignored generated output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    out_dir = args.out
    draft_root = out_dir / "drafts"
    ensure_dir(draft_root)

    template_drafts = []
    for school in REAL_CORE_SCHOOLS:
        draft_path = draft_root / "template_unit_contracts" / f"{school['school_id']}.yaml"
        draft = _template_contract_draft(school)
        _write_yaml(draft_path, draft)
        template_drafts.append(str(draft_path))

    student_drafts = []
    for student in REAL_CORE_STUDENTS:
        draft_path = draft_root / "student_content_trees" / f"{student['student_id']}.yaml"
        draft = _student_content_tree_draft(student)
        _write_yaml(draft_path, draft)
        student_drafts.append(str(draft_path))

    render_drafts = []
    for case in get_eval_cases_for_profile(PROFILE_ID):
        if case.stage != "e2e":
            continue
        draft_path = draft_root / "render_plans" / f"{case.case_id}.yaml"
        draft = _render_plan_draft(case.case_id, case.school_id, case.student_id or "")
        _write_yaml(draft_path, draft)
        render_drafts.append(str(draft_path))

    manifest = {
        "profile_id": PROFILE_ID,
        "status": "draft_pending_user_review",
        "template_contract_drafts": template_drafts,
        "student_content_tree_drafts": student_drafts,
        "render_plan_drafts": render_drafts,
        "signed_standard_write_policy": "not_written_by_default",
        "auto_update_allowed": False,
    }
    write_json(out_dir / "manifest.json", manifest)
    write_text(out_dir / "review_packet.md", _review_packet_markdown(manifest))


def _template_contract_draft(school: dict[str, Any]) -> dict[str, Any]:
    template_docx = ROOT / school["template_docx"]
    return {
        "baseline_type": "template_unit_contract",
        "profile_id": PROFILE_ID,
        "school_id": school["school_id"],
        "review_state": "draft_pending_user_review",
        "review_metadata": _pending_review_metadata(
            source_docx=school["template_docx"],
            review_source=school["review_source"],
            change_reason="initial real-core-v0 template unit contract draft",
        ),
        "source_docx_sha256": sha256_file(template_docx),
        "unit_model": "document_unit -> unit_element -> sub_element",
        "units": [],
        "dimensions": [
            {
                "dimension_id": "template.units.order",
                "required": True,
                "comparator_mode": "ordered_sequence",
                "review_note": "Fill from the human template review before signing.",
            }
        ],
    }


def _student_content_tree_draft(student: dict[str, Any]) -> dict[str, Any]:
    student_docx = ROOT / student["student_docx"]
    return {
        "baseline_type": "student_content_tree",
        "profile_id": PROFILE_ID,
        "student_id": student["student_id"],
        "review_state": "draft_pending_user_review",
        "review_metadata": _pending_review_metadata(
            source_docx=student["student_docx"],
            review_source=student["review_source"],
            change_reason="initial real-core-v0 student content tree draft",
        ),
        "source_docx_sha256": sha256_file(student_docx),
        "content_model": "document_unit -> unit_element -> sub_element",
        "content_nodes": [],
        "unsupported_or_ambiguous": [],
        "dimensions": [
            {
                "dimension_id": "student.visible_content.order",
                "required": True,
                "comparator_mode": "ordered_sequence",
                "review_note": "Fill from the human content review before signing.",
            }
        ],
    }


def _render_plan_draft(case_id: str, school_id: str, student_id: str) -> dict[str, Any]:
    return {
        "baseline_type": "aligned_render_plan",
        "profile_id": PROFILE_ID,
        "case_id": case_id,
        "school_id": school_id,
        "student_id": student_id,
        "review_state": "draft_pending_user_review",
        "review_metadata": {
            "reviewed_by": "PENDING_USER_REVIEW",
            "review_source": [
                f"standards/schools/{school_id}/v1/template_unit_contract.yaml",
                f"standards/eval_profiles/{PROFILE_ID}/expected/student_content_trees/{student_id}.yaml",
            ],
            "source_docx_sha256": "PENDING_AFTER_TEMPLATE_AND_STUDENT_BASELINES_LOCK",
            "change_reason": "initial real-core-v0 aligned render plan draft",
            "auto_update_allowed": False,
        },
        "actions": [],
        "dimensions": [
            {
                "dimension_id": "placement.content_dispositions",
                "required": True,
                "comparator_mode": "ordered_sequence",
                "review_note": "Fill after template and student baselines are reviewed.",
            }
        ],
    }


def _pending_review_metadata(
    *,
    source_docx: Path,
    review_source: Path,
    change_reason: str,
) -> dict[str, Any]:
    return {
        "reviewed_by": "PENDING_USER_REVIEW",
        "review_source": str(review_source),
        "source_docx_sha256": sha256_file(ROOT / source_docx),
        "change_reason": change_reason,
        "auto_update_allowed": False,
    }


def _review_packet_markdown(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# real-core-v0 Baseline Review Packet",
            "",
            f"- Status: {manifest['status']}",
            f"- Template drafts: {len(manifest['template_contract_drafts'])}",
            f"- Student content drafts: {len(manifest['student_content_tree_drafts'])}",
            f"- Render plan drafts: {len(manifest['render_plan_drafts'])}",
            "- Runtime human review: not allowed as a pass/fail gate",
            "- AI final-status authority: none",
            "- Auto-update from current output: false",
            "",
            "These drafts are review inputs only. They are not signed standards until a",
            "product/user reviewer locks the expected content and metadata.",
            "",
        ]
    )


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
