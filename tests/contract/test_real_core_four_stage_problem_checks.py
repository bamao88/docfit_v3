from __future__ import annotations

from pathlib import Path

from docfit.convert.orchestrator import run_e2e_eval
from docfit.harness.product_quality import _append_only_finding, audit_e2e_case


ROOT = Path.cwd()


def _by_type(findings):
    return {finding.type: finding for finding in findings}


def test_real_core_problem_check_reports_all_four_stages(tmp_path) -> None:
    result = run_e2e_eval(
        ROOT,
        "hunannongye",
        ROOT / "inputs/students/real-student-003/raw/source_document.docx",
        tmp_path / "real_core_product_quality_case",
    )
    assert (tmp_path / "real_core_product_quality_case/final.docx").exists()

    direct_audit_findings = audit_e2e_case(tmp_path / "real_core_product_quality_case")
    direct_by_type = _by_type(direct_audit_findings)
    by_type = _by_type(result.findings)

    assert "template_unit_tree_missing" not in by_type
    assert "template_instruction_paragraph_unclassified" not in by_type
    assert "template_unit_tree_missing" not in direct_by_type
    assert "template_instruction_paragraph_unclassified" not in direct_by_type

    assert "content_heading_semantics_unclassified" in by_type
    assert by_type["content_heading_semantics_unclassified"].stage == "content"
    assert "content_id" not in by_type["content_heading_semantics_unclassified"].actual
    assert "c_" in by_type["content_heading_semantics_unclassified"].actual
    assert "1 前言" not in by_type["content_heading_semantics_unclassified"].actual
    assert "参考文献" in by_type["content_heading_semantics_unclassified"].actual

    assert "content_donor_front_matter_not_disposed" in by_type
    assert by_type["content_donor_front_matter_not_disposed"].stage == "content"
    assert "湖 南 农 业 大 学" in by_type["content_donor_front_matter_not_disposed"].actual

    assert "placement_actions_collapsed_to_virtual_body_slot" not in by_type
    assert "placement_actions_collapsed_to_virtual_body_slot" not in direct_by_type

    assert "render_template_instruction_text_leaked" not in by_type
    assert "render_template_instruction_text_leaked" not in direct_by_type

    assert "render_append_only_insertion" not in by_type
    assert "render_append_only_insertion" not in direct_by_type

    assert result.blocked_at == "template"
    assert result.status.value == "FAIL"


def test_append_only_check_uses_earliest_rendered_paragraph_position() -> None:
    finding = _append_only_finding(
        {"data": {"paragraphs": [{} for _ in range(100)]}},
        {
            "data": {
                "actions": [
                    {"action_id": "a_001", "disposition": "place"},
                    {"action_id": "a_002", "disposition": "place"},
                ]
            }
        },
        {
            "actions_executed": [
                {
                    "action_id": "a_001",
                    "actual_ooxml_ref": "word/document.xml:p[150]",
                },
                {
                    "action_id": "a_002",
                    "actual_ooxml_ref": "word/document.xml:p[50]",
                },
            ]
        },
        [{"index": 1, "text": "模板正文"}],
    )

    assert finding is None


def test_append_only_check_reports_when_all_writes_follow_template() -> None:
    finding = _append_only_finding(
        {"data": {"paragraphs": [{} for _ in range(100)]}},
        {
            "data": {
                "actions": [
                    {"action_id": "a_001", "disposition": "place"},
                    {"action_id": "a_002", "disposition": "place"},
                ]
            }
        },
        {
            "actions_executed": [
                {
                    "action_id": "a_001",
                    "actual_ooxml_ref": "word/document.xml:p[150]",
                },
                {
                    "action_id": "a_002",
                    "actual_ooxml_ref": "word/document.xml:p[151]",
                },
            ]
        },
        [{"index": 1, "text": "模板正文"}],
    )

    assert finding is not None
    assert finding.type == "render_append_only_insertion"
