from __future__ import annotations

from docx import Document

from docfit.convert.orchestrator import run_template_generate_eval
from docfit.core.io import read_json


def test_template_generate_default_off_writes_l1_stage_inputs_but_no_agent_decisions(tmp_path) -> None:
    source = tmp_path / "school-template.docx"
    doc = Document()
    doc.add_paragraph("封面")
    doc.add_paragraph("正文")
    doc.save(source)

    out_dir = tmp_path / "template_generate"
    result = run_template_generate_eval(tmp_path, source, out_dir)

    assert "template_agent_render_packet" not in result.artifacts
    assert "template_agent_submission_comparison" not in result.artifacts
    assert "template_agent_manual_review_items" not in result.artifacts
    assert not (out_dir / "08_agent_render_packet.json").exists()
    assert (out_dir / "01.6_t2_l1_stage_input.json").exists()
    assert not (out_dir / "01.7_t3_l1_compatibility_input.json").exists()
    assert (out_dir / "01.8_t4_l1_stage_input.json").exists()
    assert (out_dir / "12_t3_materialization_trace.json").exists()
    trace = read_json(out_dir / "12_t3_materialization_trace.json")
    assert trace["materialization"]["availability"] == "NOT_AVAILABLE"
    assert not (out_dir / "09.5_agent_submission_comparison.json").exists()
    assert not (out_dir / "10.5_agent_manual_review_items.json").exists()
    summary = read_json(out_dir / "summary.json")
    assert "ordered.template_agent_render_packet" not in summary["artifacts"]
    assert "ordered.template_agent_submission_comparison" not in summary["artifacts"]
    assert "ordered.template_agent_manual_review_items" not in summary["artifacts"]
    run_manifest = read_json(out_dir / "run_manifest.json")
    assert run_manifest["entrypoint"] == "python.run_template_generate_eval"
    assert run_manifest["ai_mode"] == "off"
    assert run_manifest["api_call_count"] == 0
    assert run_manifest["source_template_hash"]
    assert run_manifest["source_render_hash"]
    assert "ordered.template_agent_render_packet" not in run_manifest["output_artifacts"]
