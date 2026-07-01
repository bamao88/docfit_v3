from __future__ import annotations

from docx import Document
from typer.testing import CliRunner

from docfit.cli.main import app
from docfit.core.io import read_json, read_yaml, write_json
from docfit.template_generation.agent.packet import build_template_agent_render_packet
from docfit.template_generation.artifacts import source_tree_from_document_facts
from docfit.template_generation.source_tree import inspect_document_facts_docx
from docfit.template_generation.structure_candidates import build_template_structure_candidates


def test_template_generate_cli_replay_writes_agent_artifacts(tmp_path) -> None:
    source = tmp_path / "school-template.docx"
    doc = Document()
    doc.add_paragraph("封面")
    doc.add_paragraph("承诺书")
    doc.add_paragraph("正文")
    doc.save(source)
    facts = inspect_document_facts_docx(source)
    source_tree = source_tree_from_document_facts(facts)
    candidates = build_template_structure_candidates(source_tree)
    packet = build_template_agent_render_packet(
        document_facts=facts,
        structure_candidates=candidates,
        source_template_docx=source,
    )
    packet["render_status"] = "real_render"
    packet["render_artifacts"]["render_status"] = "real_render"
    packet_path = tmp_path / "packet.json"
    transcript_path = tmp_path / "transcript.json"
    write_json(packet_path, packet)
    write_json(
        transcript_path,
        {
            "artifact_type": "template_agent_transcript",
            "rounds": [
                {
                    "submission": {
                        "source_render_hash": packet["source_render_hash"],
                        "round_id": "round_001",
                        "model": "fixture",
                        "layers": {
                            "t2": {
                                "unit_candidates": [],
                                "block_candidates": [],
                                "boundary_adjustments": [],
                                "open_questions": []
                            },
                            "t3": {
                                "element_policy_candidates": [],
                                "open_questions": []
                            },
                            "t4": {
                                "page_policy_hints": [
                                    {
                                        "proposal_id": "t4_page_001",
                                        "kind": "page_policy_hint",
                                        "page_no": 1,
                                        "hint": "visual_new_page"
                                    }
                                ],
                                "section_profile_hints": [],
                                "page_numbering_hints": [],
                                "open_questions": []
                            }
                        }
                    }
                }
            ]
        },
    )
    out_dir = tmp_path / "template_generate"

    result = CliRunner().invoke(
        app,
        [
            "eval",
            "template-generate",
            "--template",
            str(source),
            "--out",
            str(out_dir),
            "--agent-replay",
            str(transcript_path),
            "--agent-render-packet",
            str(packet_path),
        ],
    )

    assert result.exit_code == 0, result.output
    hints = read_json(out_dir / "artifacts/agent_t4_hints.json")
    decisions = read_json(out_dir / "artifacts/template_agent_decisions.json")
    comparison = read_json(
        out_dir / "artifacts/template_agent_submission_comparison.json"
    )
    manual_review = read_json(
        out_dir / "artifacts/template_agent_manual_review_items.json"
    )
    assert hints["page_policy_hints"][0]["proposal_id"] == "t4_page_001"
    assert decisions["accepted_proposal_ids"] == ["t4_page_001"]
    assert comparison["summary"]["compatible"] == 1
    assert manual_review["summary"]["total"] == 0


def test_template_generate_cli_observation_bundle_writes_bridge_artifacts(tmp_path) -> None:
    source = tmp_path / "school-template.docx"
    doc = Document()
    doc.add_paragraph("封面")
    doc.add_paragraph("承诺书")
    doc.add_paragraph("正文")
    doc.save(source)
    facts = inspect_document_facts_docx(source)
    source_tree = source_tree_from_document_facts(facts)
    candidates = build_template_structure_candidates(source_tree)
    packet = build_template_agent_render_packet(
        document_facts=facts,
        structure_candidates=candidates,
        source_template_docx=source,
    )
    packet_path = tmp_path / "packet.json"
    bundle_path = tmp_path / "observation_bundle.json"
    write_json(packet_path, packet)
    write_json(
        bundle_path,
        {
            "artifact_type": "ai_observation_bundle",
            "source_render_hash": packet["source_render_hash"],
            "model": "fixture",
            "ai_unit_observation": {
                "artifact_type": "ai_unit_observation",
                "items": [],
                "quality_report": {"demotions": []},
            },
            "ai_element_observation": {
                "artifact_type": "ai_element_observation",
                "items": [],
                "quality_report": {"demotions": []},
            },
            "ai_layout_observation": {
                "artifact_type": "ai_layout_observation",
                "items": [],
                "abstain": False,
                "quality_report": {"demotions": []},
            },
        },
    )
    out_dir = tmp_path / "template_generate_observation"

    result = CliRunner().invoke(
        app,
        [
            "eval",
            "template-generate",
            "--template",
            str(source),
            "--out",
            str(out_dir),
            "--agent-render-packet",
            str(packet_path),
            "--agent-observation-bundle",
            str(bundle_path),
        ],
    )

    assert result.exit_code == 0, result.output
    bridge = read_json(out_dir / "artifacts/template_agent_observation_bridge.json")
    ai_t3 = read_yaml(out_dir / "artifacts/t3_ai_element_observation.yaml")
    comparison = read_json(
        out_dir / "artifacts/template_agent_submission_comparison.json"
    )
    attribution = read_json(out_dir / "artifacts/agent_attribution.json")
    assert bridge["summary"]["total_proposals"] == 0
    assert ai_t3["route"]["route_id"] == "ai_raw"
    assert ai_t3["route"]["availability"] == "AVAILABLE"
    assert ai_t3["artifact_type"] == "ai_element_observation"
    assert comparison["summary"]["total"] == 0
    assert attribution["observation_bridge"]["present"] is True
