from __future__ import annotations

from pathlib import Path

from docfit.convert.orchestrator import run_e2e_eval
from docfit.harness.product_quality import audit_e2e_case


ROOT = Path.cwd()


def _by_type(findings):
    return {finding.type: finding for finding in findings}


def test_real_core_product_quality_audit_exposes_all_four_stage_gaps(tmp_path) -> None:
    result = run_e2e_eval(
        ROOT,
        "hunannongye",
        ROOT / "inputs/real-student-003-source.docx",
        tmp_path / "real_core_product_quality_case",
    )
    assert (tmp_path / "real_core_product_quality_case/final.docx").exists()

    findings = audit_e2e_case(tmp_path / "real_core_product_quality_case")
    by_type = _by_type(findings)

    assert "template_unit_tree_missing" in by_type
    assert by_type["template_unit_tree_missing"].stage == "template"
    assert "slot_body_start" in by_type["template_unit_tree_missing"].actual
    assert "first paragraph" in by_type["template_unit_tree_missing"].actual

    assert "template_instruction_paragraph_unclassified" in by_type
    assert by_type["template_instruction_paragraph_unclassified"].stage == "template"
    assert "附件1" in by_type["template_instruction_paragraph_unclassified"].actual

    assert "content_heading_semantics_unclassified" in by_type
    assert by_type["content_heading_semantics_unclassified"].stage == "content"
    assert "content_id" not in by_type["content_heading_semantics_unclassified"].actual
    assert "c_" in by_type["content_heading_semantics_unclassified"].actual
    assert "1 前言" in by_type["content_heading_semantics_unclassified"].actual

    assert "content_donor_front_matter_not_disposed" in by_type
    assert by_type["content_donor_front_matter_not_disposed"].stage == "content"
    assert "湖 南 农 业 大 学" in by_type["content_donor_front_matter_not_disposed"].actual

    assert "placement_actions_collapsed_to_virtual_body_slot" in by_type
    assert by_type["placement_actions_collapsed_to_virtual_body_slot"].stage == "placement"
    assert "slot_body_start" in by_type[
        "placement_actions_collapsed_to_virtual_body_slot"
    ].actual
    assert "a_001" in by_type["placement_actions_collapsed_to_virtual_body_slot"].actual

    assert "render_template_instruction_text_leaked" in by_type
    assert by_type["render_template_instruction_text_leaked"].stage == "render"
    assert "附件1" in by_type["render_template_instruction_text_leaked"].actual
    assert "paragraph" in by_type["render_template_instruction_text_leaked"].actual

    assert "render_append_only_insertion" in by_type
    assert by_type["render_append_only_insertion"].stage == "render"
    assert "word/document.xml:p[" in by_type["render_append_only_insertion"].actual
    assert "template artifact has" in by_type["render_append_only_insertion"].actual

    assert result.blocked_at == "render"
    assert result.status.value == "UNKNOWN"
