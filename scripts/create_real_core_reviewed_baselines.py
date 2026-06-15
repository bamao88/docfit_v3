from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

from docfit.core.io import ensure_dir, sha256_file, sha256_text, write_json
from docfit.harness.profiles import (
    REAL_CORE_PROFILE,
    REAL_CORE_SCHOOLS,
    REAL_CORE_STUDENTS,
    get_eval_cases_for_profile,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = REAL_CORE_PROFILE.profile_id
DEFAULT_PACKET = Path("docs/human/real-core-v0-review-packet.md")
DEFAULT_REVIEWER = "user-reviewed-source-fact-packet"
APPROVED_AT = "2026-06-15T00:00:00+08:00"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--packet",
        type=Path,
        default=DEFAULT_PACKET,
        help="Reviewed full source-fact packet to bind into baselines.",
    )
    parser.add_argument(
        "--reviewed-by",
        default=DEFAULT_REVIEWER,
        help="Reviewer label to write into baseline review_metadata.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    packet_path = args.packet
    packet_text = (ROOT / packet_path).read_text(encoding="utf-8")
    packet_sha = sha256_text(packet_text)

    school_sections = {
        str(school["school_id"]): _extract_source_section(
            packet_text, str(school["school_id"])
        )
        for school in REAL_CORE_SCHOOLS
    }
    student_sections = {
        str(student["student_id"]): _extract_source_section(
            packet_text, str(student["student_id"])
        )
        for student in REAL_CORE_STUDENTS
    }
    shared_section = _extract_source_section(
        packet_text, "shared-template-recognition-alignment"
    )
    case_focus = _extract_case_focus(packet_text)

    _write_school_standards(
        packet_path=packet_path,
        packet_sha=packet_sha,
        reviewed_by=args.reviewed_by,
        school_sections=school_sections,
    )
    _write_profile_expected_baselines(
        packet_path=packet_path,
        packet_sha=packet_sha,
        reviewed_by=args.reviewed_by,
        school_sections=school_sections,
        student_sections=student_sections,
        shared_section=shared_section,
        case_focus=case_focus,
    )


def _write_school_standards(
    *,
    packet_path: Path,
    packet_sha: str,
    reviewed_by: str,
    school_sections: dict[str, str],
) -> None:
    for school in REAL_CORE_SCHOOLS:
        school_id = str(school["school_id"])
        school_dir = ROOT / "standards/schools" / school_id / "v1"
        ensure_dir(school_dir)
        section_text = school_sections[school_id]
        section_sha = sha256_text(section_text)
        template_docx = Path(school["template_docx"])
        review_source = Path(school["review_source"])
        template_hash = sha256_file(ROOT / template_docx)
        _write_yaml(
            school_dir / "signed_standard.yaml",
            {
                "standard_id": f"{school_id}-v1",
                "school_id": school_id,
                "template_version": "v1",
                "status": "signed_source_facts",
                "owner": "docfit-core",
                "approved_at": APPROVED_AT,
                "source": {
                    "template_docx": str(template_docx),
                    "template_docx_sha256": template_hash,
                    "review_packet": str(packet_path),
                    "review_packet_sha256": packet_sha,
                    "template_review_source": str(review_source),
                    "template_review_source_sha256": sha256_file(ROOT / review_source),
                    "accepted_template_review_section_sha256": section_sha,
                },
                "contracts": {
                    "template_contract": "template_contract.json",
                    "student_content_contract": "student_content_contract.json",
                    "placement_contract": "placement_contract.json",
                    "render_contract": "render_contract.json",
                },
                "evidence_baselines": {
                    "template_unit_contract": "template_unit_contract.yaml",
                },
                "coverage_requirements": {
                    "profile": PROFILE_ID,
                    "required_capabilities": REAL_CORE_PROFILE.all_required_capabilities(),
                },
                "change_control": {
                    "auto_update_allowed": False,
                    "requires_review": True,
                    "change_reason": "initial real-core-v0 reviewed source facts",
                },
            },
        )
        _write_yaml(
            school_dir / "template_unit_contract.yaml",
            {
                "baseline_type": "template_unit_contract",
                "profile_id": PROFILE_ID,
                "school_id": school_id,
                "review_metadata": _review_metadata(
                    reviewed_by=reviewed_by,
                    review_source=f"{packet_path}#source-{school_id}",
                    source_hash=template_hash,
                    change_reason="initial real-core-v0 reviewed template source facts",
                ),
                "accepted_source_facts": {
                    "review_packet": str(packet_path),
                    "review_packet_sha256": packet_sha,
                    "source_section_id": school_id,
                    "source_section_sha256": section_sha,
                    "template_docx": str(template_docx),
                    "template_docx_sha256": template_hash,
                    "original_review_source": str(review_source),
                    "original_review_source_sha256": sha256_file(ROOT / review_source),
                    "full_review_text": section_text,
                },
                "expected": {
                    "school_id": school_id,
                    "source_section_sha256": section_sha,
                    "review_packet_sha256": packet_sha,
                    "unit_model": "document_unit -> unit_element -> sub_element",
                    "full_review_text": section_text,
                },
                "dimensions": [
                    _dimension(
                        "template.source_section_hash",
                        "exact",
                        "source_section_sha256",
                    ),
                    _dimension(
                        "template.full_review_text",
                        "normalized_text",
                        "full_review_text",
                    ),
                    _dimension("template.unit_model", "exact", "unit_model"),
                ],
            },
        )
        for stage, capabilities, invariants, verifier_refs in _contract_specs():
            write_json(
                school_dir / f"{stage}_contract.json",
                _contract_json(stage, capabilities, invariants, verifier_refs),
            )


def _write_profile_expected_baselines(
    *,
    packet_path: Path,
    packet_sha: str,
    reviewed_by: str,
    school_sections: dict[str, str],
    student_sections: dict[str, str],
    shared_section: str,
    case_focus: dict[str, str],
) -> None:
    expected_root = ROOT / REAL_CORE_PROFILE.expected_dir
    for student in REAL_CORE_STUDENTS:
        student_id = str(student["student_id"])
        section_text = student_sections[student_id]
        section_sha = sha256_text(section_text)
        student_docx = Path(student["student_docx"])
        review_source = Path(student["review_source"])
        student_hash = sha256_file(ROOT / student_docx)
        _write_yaml(
            expected_root / "student_content_trees" / f"{student_id}.yaml",
            {
                "baseline_type": "student_content_tree",
                "profile_id": PROFILE_ID,
                "student_id": student_id,
                "review_metadata": _review_metadata(
                    reviewed_by=reviewed_by,
                    review_source=f"{packet_path}#source-{student_id}",
                    source_hash=student_hash,
                    change_reason="initial real-core-v0 reviewed student source facts",
                ),
                "accepted_source_facts": {
                    "review_packet": str(packet_path),
                    "review_packet_sha256": packet_sha,
                    "source_section_id": student_id,
                    "source_section_sha256": section_sha,
                    "student_docx": str(student_docx),
                    "student_docx_sha256": student_hash,
                    "original_review_source": str(review_source),
                    "original_review_source_sha256": sha256_file(ROOT / review_source),
                    "full_review_text": section_text,
                },
                "expected": {
                    "student_id": student_id,
                    "source_section_sha256": section_sha,
                    "review_packet_sha256": packet_sha,
                    "content_model": "document_unit -> unit_element -> sub_element",
                    "full_review_text": section_text,
                },
                "dimensions": [
                    _dimension(
                        "content.source_section_hash",
                        "exact",
                        "source_section_sha256",
                    ),
                    _dimension(
                        "content.full_review_text",
                        "normalized_text",
                        "full_review_text",
                    ),
                    _dimension("content.model", "exact", "content_model"),
                ],
            },
        )

    shared_sha = sha256_text(shared_section)
    for case in get_eval_cases_for_profile(PROFILE_ID):
        if case.stage != "e2e":
            continue
        school_id = case.school_id
        student_id = str(case.student_id)
        template_section_sha = sha256_text(school_sections[school_id])
        student_section_sha = sha256_text(student_sections[student_id])
        focus = case_focus.get(case.case_id, "")
        case_source_sha = sha256_text(
            "|".join([case.case_id, template_section_sha, student_section_sha, shared_sha, focus])
        )
        metadata = _review_metadata(
            reviewed_by=reviewed_by,
            review_source=f"{packet_path}#case-{case.case_id}",
            source_hash=case_source_sha,
            change_reason="initial real-core-v0 reviewed placement/render source facts",
        )
        plan = {
            "baseline_type": "aligned_render_plan",
            "profile_id": PROFILE_ID,
            "case_id": case.case_id,
            "school_id": school_id,
            "student_id": student_id,
            "review_metadata": metadata,
            "accepted_source_facts": {
                "review_packet": str(packet_path),
                "review_packet_sha256": packet_sha,
                "case_source_bundle_sha256": case_source_sha,
                "target_school_section_sha256": template_section_sha,
                "student_content_section_sha256": student_section_sha,
                "shared_alignment_section_sha256": shared_sha,
                "case_focus": focus,
                "no_silent_drop_policy": "every accepted visible student content node receives a disposition",
            },
            "expected": {
                "case_id": case.case_id,
                "school_id": school_id,
                "student_id": student_id,
                "case_source_bundle_sha256": case_source_sha,
                "source_section_hashes": [
                    template_section_sha,
                    student_section_sha,
                    shared_sha,
                ],
                "case_focus": focus,
                "no_silent_drop_policy": "every accepted visible student content node receives a disposition",
            },
            "dimensions": [
                _dimension(
                    "placement.case_source_bundle_hash",
                    "exact",
                    "case_source_bundle_sha256",
                ),
                _dimension(
                    "placement.source_section_hashes",
                    "set_equality",
                    "source_section_hashes",
                ),
                _dimension("placement.case_focus", "normalized_text", "case_focus"),
                _dimension(
                    "placement.no_silent_drop_policy",
                    "exact",
                    "no_silent_drop_policy",
                ),
            ],
        }
        _write_yaml(expected_root / "render_plans" / f"{case.case_id}.yaml", plan)
        write_json(
            expected_root
            / "render_feature_snapshots"
            / f"{case.case_id}.json",
            {
                "baseline_type": "render_feature_snapshot",
                "profile_id": PROFILE_ID,
                "case_id": case.case_id,
                "school_id": school_id,
                "student_id": student_id,
                "review_metadata": metadata,
                "accepted_source_facts": {
                    "review_packet": str(packet_path),
                    "review_packet_sha256": packet_sha,
                    "case_source_bundle_sha256": case_source_sha,
                    "word_image_evidence_required": True,
                },
                "expected": {
                    "case_source_bundle_sha256": case_source_sha,
                    "word_image_evidence_required": True,
                    "render_feature_snapshot_status": "source_facts_accepted_word_evidence_pending",
                },
                "dimensions": [
                    _dimension(
                        "render.case_source_bundle_hash",
                        "exact",
                        "case_source_bundle_sha256",
                    ),
                    _dimension(
                        "render.word_image_evidence_required",
                        "exact",
                        "word_image_evidence_required",
                    ),
                    _dimension(
                        "render.feature_snapshot_status",
                        "exact",
                        "render_feature_snapshot_status",
                    ),
                ],
            },
        )


def _contract_specs() -> list[tuple[str, list[str], list[str], list[str]]]:
    capabilities = REAL_CORE_PROFILE.required_capabilities
    return [
        (
            "template",
            list(capabilities["template"]),
            [
                "template unit tree preserves units, elements, sub-elements, order, policies, styles, and layout constraints",
            ],
            ["docfit.stages.template_parse.verify_template_artifact"],
        ),
        (
            "student_content",
            list(capabilities["content"]),
            [
                "visible student content tree preserves ignored donor content, body flow, figures, tables, references, appendix, and acknowledgement facts",
            ],
            ["docfit.stages.content_extract.verify_student_content_artifact"],
        ),
        (
            "placement",
            list(capabilities["placement"]),
            [
                "every accepted visible content node receives a target disposition without silent drop",
            ],
            ["docfit.stages.placement.verify_placement_plan"],
        ),
        (
            "render",
            list(capabilities["render"]),
            [
                "render output must bind to feature snapshot and Word image evidence before final pass",
            ],
            ["docfit.stages.render.verify_render_outputs"],
        ),
    ]


def _contract_json(
    contract_type: str,
    required_capabilities: list[str],
    required_invariants: list[str],
    verifier_refs: list[str],
) -> dict[str, Any]:
    return {
        "contract_type": contract_type,
        "contract_version": "1.0",
        "owner": "docfit-core",
        "required_invariants": required_invariants,
        "required_capabilities": required_capabilities,
        "unsupported_policy": {
            "blocking_unknown": True,
            "unknown_is_blocking": True,
        },
        "coverage_requirements": {
            "profile": PROFILE_ID,
        },
        "verifier_refs": verifier_refs,
    }


def _review_metadata(
    *,
    reviewed_by: str,
    review_source: str,
    source_hash: str,
    change_reason: str,
) -> dict[str, Any]:
    return {
        "reviewed_by": reviewed_by,
        "review_source": review_source,
        "source_docx_sha256": source_hash,
        "change_reason": change_reason,
        "auto_update_allowed": False,
    }


def _dimension(dimension_id: str, comparator_mode: str, key: str) -> dict[str, str]:
    return {
        "dimension_id": dimension_id,
        "required": True,
        "comparator_mode": comparator_mode,
        "expected_path": key,
        "actual_path": key,
    }


def _extract_source_section(packet_text: str, source_id: str) -> str:
    pattern = (
        rf"### Source: `{re.escape(source_id)}`\n"
        rf".*?\n~~~~text\n(?P<body>.*?)\n~~~~"
    )
    match = re.search(pattern, packet_text, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"Could not find reviewed source section {source_id!r}")
    return match.group("body")


def _extract_case_focus(packet_text: str) -> dict[str, str]:
    focus: dict[str, str] = {}
    for line in packet_text.splitlines():
        if not line.startswith("| `real_core_v0_"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != 4:
            continue
        case_id = parts[0].strip("`")
        focus[case_id] = parts[3]
    return focus


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
