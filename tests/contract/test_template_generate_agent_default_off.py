from __future__ import annotations

from docx import Document

from docfit.convert.orchestrator import run_template_generate_eval
from docfit.core.io import read_json


def test_template_generate_default_off_writes_no_agent_artifacts(tmp_path) -> None:
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
    assert not (out_dir / "artifacts/template_agent_render_packet.json").exists()
    assert not (out_dir / "artifacts/template_agent_submission_comparison.json").exists()
    assert not (out_dir / "artifacts/template_agent_manual_review_items.json").exists()
    summary = read_json(out_dir / "summary.json")
    assert "template_agent_render_packet" not in summary["artifacts"]
    assert "template_agent_submission_comparison" not in summary["artifacts"]
    assert "template_agent_manual_review_items" not in summary["artifacts"]
