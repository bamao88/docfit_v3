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
TEMPLATE_GENERATION_STAGE_MODEL = (
    "00_input_request -> 01_source_parse -> 02_structure_discovery -> "
    "03_generation_model -> 04_plan_build -> 05_action_execution -> "
    "06_final_template_gap"
)
TEMPLATE_GENERATION_STAGE_BOUNDARIES: list[dict[str, Any]] = [
    {
        "stage_id": "01_source_parse",
        "artifact": "source_template_tree.json",
        "input_artifacts": [
            "template_generation_request.json",
            "00_input_source_template.docx",
        ],
        "output_artifacts": ["source_template_tree.json"],
        "checks_against_review": [
            "源模板可见段落、表格、页眉页脚、分节和未知对象必须保留为事实证据",
            "每个后续可引用的可见节点必须有稳定 source_seq/source_ref",
            "源文件 hash 必须绑定到 signed_standard.source.template_docx_sha256",
        ],
        "not_allowed": [
            "不得在本阶段裁定 unit_id、policy 或最终生成策略",
            "不得删除人工 review 中后续需要判断的可见模板事实",
        ],
        "missing_or_unreadable_result": "UNKNOWN",
    },
    {
        "stage_id": "02_structure_discovery",
        "artifact": "template_structure_candidates.json",
        "input_artifacts": ["source_template_tree.json"],
        "output_artifacts": ["template_structure_candidates.json"],
        "checks_against_review": [
            "候选 unit 顺序必须能覆盖人工 review 的 expected.unit_order",
            "logical element 必须保留 source_seq_refs，合并关系必须可追溯",
            "固定、填充、生成、manual_only、template_default_optional 的角色提示必须来自源模板证据",
        ],
        "not_allowed": [
            "不得把学校说明文字当作学生正文候选",
            "不得把 manual_only 固定表单误标成学生内容 slot",
            "不得把缺证据的启发式写成已验收结论",
        ],
        "missing_or_unreadable_result": "UNKNOWN",
    },
    {
        "stage_id": "03_generation_model",
        "artifact": "template_generation_model.json",
        "input_artifacts": [
            "template_generation_request.json",
            "template_structure_candidates.json",
        ],
        "output_artifacts": ["template_generation_model.json"],
        "checks_against_review": [
            "unit 策略必须保持人工 review 的单元顺序、status、policy 和处理口径",
            "manual_only/fixed/template_default 单元必须被保护或保留，不得静默删除",
            "学生内容、元数据、Word 生成字段和人工填写区域必须区分",
        ],
        "not_allowed": [
            "不得读取学校标准作为 template-generate 正常业务输入",
            "不得用某次学生内容决定学校模板单元是否存在",
            "不得用 manifest 或模型替代最终 gap 判断",
        ],
        "missing_or_unreadable_result": "UNKNOWN",
    },
    {
        "stage_id": "04_plan_build",
        "artifact": "template_generation_plan.json",
        "input_artifacts": ["template_generation_model.json"],
        "output_artifacts": ["template_generation_plan.json"],
        "checks_against_review": [
            "每个修改型 action 必须声明 affected_source_seq_refs",
            "cleanup action 只能处理人工 review 允许剥离的说明文字或示例痕迹",
            "字段、目录、图目录、表目录、页眉页码等生成动作必须能回到人工 review 的对应单元",
        ],
        "not_allowed": [
            "不得生成无法回溯来源的删除、替换或 slot action",
            "不得把 copy-only/protected 单元拆成普通正文动作",
        ],
        "missing_or_unreadable_result": "UNKNOWN",
    },
    {
        "stage_id": "05_action_execution",
        "artifact": "generated_template.docx + template_generation_manifest.json",
        "input_artifacts": ["00_input_source_template.docx", "template_generation_plan.json"],
        "output_artifacts": [
            "05.0_copy_source_docx.docx",
            "generated_template.docx",
            "template_generation_manifest.json",
        ],
        "checks_against_review": [
            "manifest 必须记录执行动作、输入输出 hash 和 affected_source_seq_refs",
            "生成 Word 必须先能作为 DOCX 打开并进入 06_final_template_gap",
            "固定模板块、人工表单和签名日期区必须按人工 review 的保留策略处理",
        ],
        "not_allowed": [
            "不得把生成命令执行成功当成最终模板合格",
            "不得在缺 manifest/hash 时用重新生成补旧 run 的证据",
        ],
        "missing_or_unreadable_result": "UNKNOWN",
    },
]


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
        existing_units = _existing_template_units(school_dir / "template_unit_contract.yaml")
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
                    "template_generation_stage_contract": (
                        "template_generation_stage_contract.yaml"
                    ),
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
                    "units": existing_units,
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
        _write_template_generation_stage_contract(
            school_dir=school_dir,
            school_id=school_id,
            packet_path=packet_path,
            packet_sha=packet_sha,
            reviewed_by=reviewed_by,
            section_sha=section_sha,
            template_docx=template_docx,
            template_hash=template_hash,
            review_source=review_source,
            template_units=existing_units,
        )
        for stage, capabilities, invariants, verifier_refs in _contract_specs():
            write_json(
                school_dir / f"{stage}_contract.json",
                _contract_json(stage, capabilities, invariants, verifier_refs),
            )


def _existing_template_units(template_unit_contract_path: Path) -> list[dict[str, Any]]:
    if not template_unit_contract_path.exists():
        return []
    loaded = yaml.safe_load(template_unit_contract_path.read_text(encoding="utf-8")) or {}
    units = loaded.get("expected", {}).get("units", [])
    return units if isinstance(units, list) else []


def _write_template_generation_stage_contract(
    *,
    school_dir: Path,
    school_id: str,
    packet_path: Path,
    packet_sha: str,
    reviewed_by: str,
    section_sha: str,
    template_docx: Path,
    template_hash: str,
    review_source: Path,
    template_units: list[dict[str, Any]],
) -> None:
    template_unit_contract_path = school_dir / "template_unit_contract.yaml"
    _write_yaml(
        school_dir / "template_generation_stage_contract.yaml",
        {
            "baseline_type": "template_generation_stage_contract",
            "profile_id": PROFILE_ID,
            "school_id": school_id,
            "review_metadata": _review_metadata(
                reviewed_by=reviewed_by,
                review_source=f"{packet_path}#source-{school_id}",
                source_hash=template_hash,
                change_reason=(
                    "derive template generation stage standards from reviewed "
                    "template source facts"
                ),
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
                "upstream_template_unit_contract": "template_unit_contract.yaml",
                "upstream_template_unit_contract_sha256": sha256_file(
                    template_unit_contract_path
                ),
            },
            "purpose": (
                "为模板生成 01-05 阶段提供人工签收的输入/输出标准。"
                "这些标准来自 template_unit_contract.yaml 的 expected.units 和完整人工 review；"
                "在阶段 verifier 接入前只表示标准已存在，不表示阶段已 PASS。"
            ),
            "ai_boundary": {
                "ai_may_explain": True,
                "ai_may_edit_status_or_standard_without_human_review": False,
                "auto_update_allowed": False,
            },
            "gate_policy": {
                "enabled_verifier_required_for_pass": True,
                "not_configured_is_not_pass": True,
                "missing_standard_result": "UNKNOWN",
                "missing_artifact_result": "UNKNOWN",
            },
            "expected": {
                "school_id": school_id,
                "source_section_sha256": section_sha,
                "review_packet_sha256": packet_sha,
                "stage_model": TEMPLATE_GENERATION_STAGE_MODEL,
                "unit_tree_source": "template_unit_contract.yaml#/expected/units",
                "unit_order": [unit["unit_id"] for unit in template_units],
                "unit_summaries": _unit_summaries(template_units),
                "policy_groups": _policy_groups(template_units),
                "stage_boundaries": TEMPLATE_GENERATION_STAGE_BOUNDARIES,
                "stage_standards": {
                    stage["stage_id"]: _template_generation_stage_standard(
                        stage["stage_id"], template_units
                    )
                    for stage in TEMPLATE_GENERATION_STAGE_BOUNDARIES
                },
            },
            "dimensions": [
                _dimension(
                    "template_generation_stage.source_section_hash",
                    "exact",
                    "source_section_sha256",
                ),
                _dimension(
                    "template_generation_stage.stage_model",
                    "exact",
                    "stage_model",
                ),
                _dimension(
                    "template_generation_stage.unit_order",
                    "ordered_sequence",
                    "unit_order",
                ),
            ],
        },
    )


def _unit_summaries(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for unit in units:
        element_policies = sorted(
            {
                str(element.get("policy"))
                for element in unit.get("elements", [])
                if element.get("policy")
            }
        )
        summaries.append(
            {
                "unit_id": unit["unit_id"],
                "name": unit.get("name"),
                "order": unit.get("order"),
                "status": unit.get("status"),
                "policy": unit.get("policy"),
                "element_count": len(unit.get("elements", [])),
                "element_policies": element_policies,
                "source_refs": unit.get("source_refs", []),
                "handling": unit.get("handling"),
            }
        )
    return summaries


def _policy_groups(units: list[dict[str, Any]]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {
        "manual_only_units": [],
        "fillable_units": [],
        "generated_units": [],
        "template_default_units": [],
        "fixed_or_protected_units": [],
    }
    for unit in units:
        unit_id = str(unit["unit_id"])
        unit_policy = str(unit.get("policy") or "")
        unit_status = str(unit.get("status") or "")
        element_policies = {
            str(element.get("policy"))
            for element in unit.get("elements", [])
            if element.get("policy")
        }
        if (
            unit_policy == "manual_only"
            or unit_status == "manual_only"
            or "manual_only" in element_policies
        ):
            groups["manual_only_units"].append(unit_id)
        if "fill" in element_policies:
            groups["fillable_units"].append(unit_id)
        if "generated" in element_policies:
            groups["generated_units"].append(unit_id)
        if unit_policy.startswith("template_default") or unit_status.startswith(
            "template_default"
        ):
            groups["template_default_units"].append(unit_id)
        if unit_policy in {"fixed", "manual_only"} or "fixed" in element_policies:
            groups["fixed_or_protected_units"].append(unit_id)
    return groups


def _template_generation_stage_standard(
    stage_id: str,
    units: list[dict[str, Any]],
) -> dict[str, Any]:
    base = {
        "standard_state": "signed_pending_verifier",
        "verifier_state": "not_configured",
        "gate_enabled": False,
    }
    if stage_id == "01_source_parse":
        return {
            **base,
            "expected_from_review": {
                "source_template_hash_bound": True,
                "visible_source_facts_required": [
                    "paragraphs",
                    "tables",
                    "headers_footers",
                    "sections",
                    "fields",
                    "numbering_definitions",
                    "unknown_objects",
                ],
                "stable_locator_fields": [
                    "source_seq",
                    "source_seq_refs",
                    "source_ref",
                ],
            },
        }
    if stage_id == "02_structure_discovery":
        return {
            **base,
            "expected_from_review": {
                "required_unit_order": [unit["unit_id"] for unit in units],
                "policy_groups": _policy_groups(units),
                "candidate_trace_fields": [
                    "source_seq_refs",
                    "role_hint",
                    "evidence",
                ],
            },
        }
    if stage_id == "03_generation_model":
        return {
            **base,
            "expected_from_review": {
                "required_unit_strategies": [
                    {
                        "unit_id": unit["unit_id"],
                        "status": unit.get("status"),
                        "policy": unit.get("policy"),
                        "handling": unit.get("handling"),
                    }
                    for unit in units
                ],
                "must_distinguish_policy_groups": _policy_groups(units),
            },
        }
    if stage_id == "04_plan_build":
        return {
            **base,
            "expected_from_review": {
                "required_action_trace_fields": [
                    "affected_source_seq_refs",
                    "unit_id",
                    "action_type",
                ],
                "cleanup_requires_review_basis": True,
                "protected_unit_ids": _policy_groups(units)["manual_only_units"],
            },
        }
    if stage_id == "05_action_execution":
        return {
            **base,
            "expected_from_review": {
                "required_outputs": [
                    "generated_template.docx",
                    "template_generation_manifest.json",
                    "05.0_copy_source_docx.docx",
                ],
                "manifest_must_bind_hashes": True,
                "manifest_must_preserve_source_refs": True,
                "final_quality_gate": "06_final_template_gap",
            },
        }
    raise ValueError(stage_id)


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
