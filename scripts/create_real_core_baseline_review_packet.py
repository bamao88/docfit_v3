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
    parser.add_argument(
        "--docs-packet",
        type=Path,
        default=None,
        help=(
            "Optional checked-in markdown packet path. When set, writes the same "
            "full source-fact review packet there."
        ),
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
    packet_markdown = _review_packet_markdown(manifest)
    write_text(out_dir / "review_packet.md", packet_markdown)
    if args.docs_packet is not None:
        write_text(ROOT / args.docs_packet, packet_markdown)


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
    lines = [
        "# real-core-v0 Full Source-Fact Review Packet",
        "",
        "Last generated: deterministic local script output",
        "Status: source-fact review packet, not a signed baseline",
        "",
        "This packet is intended to be the human review surface for the real-core-v0",
        "acceptance chain. It is not a direction-only draft. The full school template",
        "review sources and full student content review sources are embedded below so",
        "unit elements, element order, relationships, fill policy, layout constraints,",
        "and style dimensions are not lost in summary tables.",
        "",
        "## Gate Boundary",
        "",
        "- Runtime human review is not allowed as a pass/fail gate.",
        "- AI may diagnose and organize evidence but may not decide final status.",
        "- `auto_update_allowed` must remain false.",
        "- This packet can approve source facts; deterministic verifiers still decide",
        "  `PASS`, `FAIL`, or `UNKNOWN` during eval runs.",
        "",
        "## How This Packet Is Used",
        "",
        "| Stage | Reviewer checks in this packet | Later runnable artifact |",
        "| --- | --- | --- |",
        "| template parse | Full embedded school review source: unit order, unit elements, sub-elements, relationships, fixed/manual/generated/content policy, style dimensions, page/header/footer rules, keep-together constraints. | `standards/schools/<school_id>/v1/template_unit_contract.yaml` and `signed_standard.yaml` |",
        "| content extract | Full embedded student review source: ignored donor content, title metadata, abstracts, keywords, ordered body flow, figures, tables, references, appendix, acknowledgement. | `standards/eval_profiles/real-core-v0/expected/student_content_trees/<student_id>.yaml` |",
        "| placement | Shared alignment rules plus every render case matrix row; every accepted student content node must receive a disposition against the accepted target-school unit tree. | `standards/eval_profiles/real-core-v0/expected/render_plans/<case_id>.yaml` |",
        "| render | Accepted template/content/placement facts plus later DOCX feature snapshots and Word image evidence. | `render_feature_snapshots/<case_id>.json` and `reports/real-core-v0/<case_id>/evidence/word_image_evidence.json` |",
        "",
        "## Generated Draft Inventory",
        "",
        f"- Template draft files: {len(manifest['template_contract_drafts'])}",
        f"- Student content draft files: {len(manifest['student_content_tree_drafts'])}",
        f"- Render plan draft files: {len(manifest['render_plan_drafts'])}",
        "- Draft YAML files remain unsigned until the full source facts below are accepted",
        "  and converted into runnable baseline artifacts.",
        "",
        "## Fixed Source Evidence",
        "",
        "### School Templates",
        "",
        "| school_id | template_docx | template_sha256 | review_source | review_sha256 |",
        "| --- | --- | --- | --- | --- |",
    ]

    for school in REAL_CORE_SCHOOLS:
        template_docx = ROOT / school["template_docx"]
        review_source = ROOT / school["review_source"]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{school['school_id']}`",
                    f"`{school['template_docx']}`",
                    f"`{sha256_file(template_docx)}`",
                    f"`{school['review_source']}`",
                    f"`{sha256_file(review_source)}`",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "### Student Documents",
            "",
            "| student_id | source_docx | source_sha256 | review_source | review_sha256 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for student in REAL_CORE_STUDENTS:
        student_docx = ROOT / student["student_docx"]
        review_source = ROOT / student["review_source"]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{student['student_id']}`",
                    f"`{student['student_docx']}`",
                    f"`{sha256_file(student_docx)}`",
                    f"`{student['review_source']}`",
                    f"`{sha256_file(review_source)}`",
                ]
            )
            + " |"
        )

    shared_review = Path("inputs/shared-template-recognition-alignment-review.txt")
    lines.extend(
        [
            "",
            "### Shared Alignment Review",
            "",
            f"- Source: `{shared_review}`",
            f"- SHA-256: `{sha256_file(ROOT / shared_review)}`",
            "",
            "## Render Case Matrix",
            "",
            "Every row below inherits the complete target-school template contract from",
            "the embedded school review source and the complete student content tree from",
            "the embedded student review source. The later render plan baseline must not",
            "collapse this to a unit-only summary; it must preserve content-node",
            "dispositions against target unit elements and sub-elements.",
            "",
            "| case_id | target_school | student_content | acceptance focus |",
            "| --- | --- | --- | --- |",
        ]
    )

    for case in get_eval_cases_for_profile(PROFILE_ID):
        if case.stage != "e2e":
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{case.case_id}`",
                    f"`{case.school_id}`",
                    f"`{case.student_id}`",
                    _render_case_focus(case.school_id, case.student_id or ""),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Full School Template Review Sources",
            "",
            "The following sections are embedded verbatim from the human school review",
            "sources. They are the review facts for unit contents, element order,",
            "relationships, policies, styles, page rules, and unresolved decisions.",
            "",
        ]
    )
    for school in REAL_CORE_SCHOOLS:
        lines.extend(_embedded_source_section(school["school_id"], school["review_source"]))

    lines.extend(
        [
            "",
            "## Full Student Content Review Sources",
            "",
            "The following sections are embedded verbatim from the human student content",
            "review sources. They are the review facts for title metadata, ignored",
            "donor content, abstracts, keywords, ordered body flow, visible objects,",
            "references, appendix, and acknowledgement.",
            "",
        ]
    )
    for student in REAL_CORE_STUDENTS:
        lines.extend(
            _embedded_source_section(student["student_id"], student["review_source"])
        )

    lines.extend(
        [
            "",
            "## Full Shared Alignment Review Source",
            "",
            "This source defines the shared document-unit -> unit-element -> sub-element",
            "model used to align template extraction, student content extraction,",
            "placement, and render verification.",
            "",
            *_embedded_source_section("shared-template-recognition-alignment", shared_review),
            "",
            "## Reviewer Response Template",
            "",
            "```text",
            "real-core-v0 source-fact review",
            "",
            "Reviewer:",
            "- reviewed_by: <name or role>",
            "- review_source: this acceptance note",
            "",
            "Accepted fact groups:",
            "- fixed evidence set: accepted",
            "- school template full facts: accepted / changes requested",
            "- student content full facts: accepted / changes requested",
            "- render-case placement expectations: accepted / changes requested",
            "",
            "Required changes:",
            "- <school_id, student_id, case_id, unit, element, or line reference>: <change>",
            "",
            "Approval boundary:",
            "- auto_update_allowed must remain false",
            "- runtime human review is not allowed as a pass/fail gate",
            "- AI may diagnose but may not decide final status",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _embedded_source_section(source_id: str, source_path: Path) -> list[str]:
    absolute = ROOT / source_path
    text = absolute.read_text(encoding="utf-8").rstrip()
    return [
        f"### Source: `{source_id}`",
        "",
        f"- Path: `{source_path}`",
        f"- SHA-256: `{sha256_file(absolute)}`",
        "",
        "~~~~text",
        text,
        "~~~~",
        "",
    ]


def _render_case_focus(school_id: str, student_id: str) -> str:
    focus_by_student = {
        "real-student-001": (
            "ignore donor-school front matter and old TOC; preserve title metadata, "
            "abstracts, keywords, ordered body flow, 2 figures, 2 content tables, "
            "references, and acknowledgement; empty appendix title is not student content"
        ),
        "real-student-002": (
            "preserve title metadata, abstracts, keywords, ordered body flow, "
            "1 figure, 1 table, and references; no appendix or acknowledgement found"
        ),
        "real-student-003": (
            "ignore Hunan Agriculture donor front matter and template lead-ins; "
            "preserve title metadata, abstracts, keywords, ordered body flow, "
            "2 figures, 1 table, and references; second figure lacks independent "
            "English caption"
        ),
    }
    focus_by_school = {
        "hunannongye": (
            "target keeps Hunan fixed cover, integrity statement, TOC, title block, "
            "abstract units, body, references, default acknowledgement/appendix policy, "
            "and manual-only rear forms"
        ),
        "nannong-undergraduate": (
            "target keeps Nanjing cover, originality/authorization statements, TOC "
            "before abstracts, abstract units, body with conclusion/outlook type, "
            "references, appendix, achievements, and acknowledgement policy"
        ),
        "pku-graduate": (
            "target keeps PKU cover, copyright, abstract units, TOC, figure/table "
            "lists, body with conclusion/discussion ending, references, achievements, "
            "acknowledgement, and originality/authorization page"
        ),
    }
    return f"{focus_by_school[school_id]}; {focus_by_student[student_id]}"


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
