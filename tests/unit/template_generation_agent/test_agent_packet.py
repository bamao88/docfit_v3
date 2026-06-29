from __future__ import annotations

import shutil

import pytest
from docx import Document

from docfit.template_generation.agent.packet import build_template_agent_render_packet
from docfit.template_generation.artifacts import source_tree_from_document_facts
from docfit.template_generation.source_tree import inspect_document_facts_docx
from docfit.template_generation.structure_candidates import build_template_structure_candidates

from .helpers import packet


def test_packet_exposes_projection_fallback_status() -> None:
    render_packet = packet()

    assert render_packet["artifact_type"] == "template_agent_render_packet"
    assert render_packet["status_authority"] == "verify_template_parse_build"
    assert render_packet["advisory_only"] is True
    assert render_packet["render_status"] == "projection_fallback"
    assert render_packet["render_artifacts"]["render_status"] == "projection_fallback"
    assert render_packet["render_artifacts"]["clean_page_images"] == []
    assert render_packet["page_text_index"][0]["source_seq"] == 1
    assert render_packet["page_text_index"][0]["page_no"] == 1
    assert "bbox" in render_packet["page_text_index"][0]
    assert render_packet["page_layout_index"][0]["render_target_id"] == "source_seq:1"
    assert render_packet["source_render_hash"].startswith("sha256:")


def test_packet_can_build_real_render_images_and_page_bindings(tmp_path) -> None:
    if not all(shutil.which(name) for name in ("soffice", "pdftoppm", "pdftotext")):
        pytest.skip("real render packet requires soffice, pdftoppm, and pdftotext")
    source = tmp_path / "two-page-template.docx"
    doc = Document()
    doc.add_paragraph("第一页标题")
    doc.add_paragraph("第一页正文")
    doc.add_page_break()
    doc.add_paragraph("第二页标题")
    doc.add_paragraph("第二页正文")
    doc.save(source)
    facts = inspect_document_facts_docx(source)
    candidates = build_template_structure_candidates(source_tree_from_document_facts(facts))

    render_packet = build_template_agent_render_packet(
        document_facts=facts,
        structure_candidates=candidates,
        source_template_docx=source,
        render_artifacts_dir=tmp_path / "agent_render",
    )

    assert render_packet["render_status"] == "real_render"
    assert render_packet["render_artifacts"]["clean_page_images"]
    assert render_packet["render_artifacts"]["annotated_page_images"]
    pages = {item["page_no"] for item in render_packet["page_text_index"]}
    assert 2 in pages
    assert any(item.get("bbox") for item in render_packet["page_text_index"])
    assert any(
        item.get("page_top_ratio") is not None
        for item in render_packet["page_layout_index"]
    )
