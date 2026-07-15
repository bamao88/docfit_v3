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
                                "section_profile_hints": [
                                    {
                                        "proposal_id": "t4_section_001",
                                        "kind": "section_profile_hint",
                                        "source_seq_refs": [1],
                                        "hint": "visual_section_profile"
                                    }
                                ],
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
    hints = read_json(out_dir / "13_agent_t4_hints.json")
    t4_merged = read_yaml(out_dir / "04.2_t4_merged_global_spec.yaml")
    decisions = read_json(out_dir / "10_agent_decisions.json")
    comparison = read_json(
        out_dir / "09.5_agent_submission_comparison.json"
    )
    manual_review = read_json(
        out_dir / "10.5_agent_manual_review_items.json"
    )
    assert hints["section_profile_hints"][0]["proposal_id"] == "t4_section_001"
    assert t4_merged["merge_trace"][-1]["source_artifact"] == "agent_t4_hints"
    assert t4_merged["merge_trace"][-1]["accepted_count"] == 1
    assert decisions["accepted_proposal_ids"] == ["t4_section_001"]
    assert comparison["summary"]["compatible"] == 1
    assert manual_review["summary"]["total"] == 0


def test_template_generate_cli_replay_rejects_t4_page_policy_hint(tmp_path) -> None:
    source = tmp_path / "school-template.docx"
    doc = Document()
    doc.add_paragraph("封面")
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
                                "open_questions": [],
                            },
                            "t3": {
                                "element_policy_candidates": [],
                                "open_questions": [],
                            },
                            "t4": {
                                "page_policy_hints": [
                                    {
                                        "proposal_id": "t4_page_body",
                                        "kind": "page_policy_hint",
                                        "unit_id": "body_main",
                                        "page_nos": [1],
                                        "standalone": True,
                                        "origin": "ai_observation",
                                    }
                                ],
                                "section_profile_hints": [],
                                "page_numbering_hints": [],
                                "open_questions": [],
                            },
                        },
                    }
                }
            ],
        },
    )
    out_dir = tmp_path / "template_generate_page_policy"

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
    manifest = read_json(out_dir / "06.2_build_manifest.json")
    decisions = read_json(out_dir / "10_agent_decisions.json")
    unit_map = read_yaml(out_dir / "02_unit_map.yaml")
    body = next(unit for unit in unit_map["units"] if unit["unit_id"] == "body_main")
    page_actions = [
        action
        for action in manifest["actions_executed"]
        if action["action_type"] == "insert_page_break_before_unit"
        and action["unit_id"] == "body_main"
    ]
    page = body.get("page") or {}
    assert page.get("origin") != "ai_observation"
    assert page.get("agent_proposal_id") is None
    assert page_actions == []
    assert "page_policy_hints" not in manifest.get("layout_hint_consumption", {})
    assert decisions["accepted_proposal_ids"] == []
    assert decisions["decisions"][0]["checks"][0]["check_id"] == "C-SCHEMA"
    assert "unsupported t4 proposal collection" in decisions["decisions"][0]["reason"]


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
    bridge = read_json(out_dir / "09.25_agent_observation_bridge.json")
    ai_t2 = read_yaml(out_dir / "02.2_t2_ai_unit_observation.yaml")
    ai_t3 = read_yaml(out_dir / "03.1_t3_ai_element_observation.yaml")
    ai_t4 = read_yaml(out_dir / "04.1_t4_ai_layout_observation.yaml")
    comparison = read_json(
        out_dir / "09.5_agent_submission_comparison.json"
    )
    attribution = read_json(out_dir / "14_agent_attribution.json")
    assert bridge["summary"]["total_proposals"] == 0
    assert ai_t2["route"]["route_id"] == "ai_raw"
    assert ai_t2["route"]["availability"] == "AVAILABLE"
    assert ai_t2["artifact_type"] == "ai_unit_observation"
    assert ai_t3["route"]["route_id"] == "ai_raw"
    assert ai_t3["route"]["availability"] == "AVAILABLE"
    assert ai_t3["artifact_type"] == "ai_element_observation"
    assert ai_t4["route"]["route_id"] == "ai_raw"
    assert ai_t4["route"]["availability"] == "AVAILABLE"
    assert ai_t4["artifact_type"] == "ai_layout_observation"
    assert comparison["summary"]["total"] == 0
    assert attribution["observation_bridge"]["present"] is True


def test_template_generate_cli_observation_replay_runs_module1_in_same_run(tmp_path) -> None:
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
    observation_replay_path = tmp_path / "observation_replay.json"
    write_json(packet_path, packet)
    write_json(
        observation_replay_path,
        {
            "t2": [
                {
                    "items": [
                        {
                            "unit_id": "cover",
                            "source_seq_refs": [1],
                            "confidence": "high",
                        },
                        {
                            "unit_id": "integrity_statement",
                            "source_seq_refs": [2],
                            "confidence": "high",
                        },
                        {
                            "unit_id": "body_main",
                            "source_seq_refs": [3],
                            "confidence": "high",
                        },
                    ]
                }
            ],
            "t3": {
                "cover": {
                    "items": [
                        {
                            "element_id": "cover.001",
                            "policy": "fixed",
                            "role": "template_fixed",
                            "content": "封面",
                            "source_seq_refs": [1],
                            "confidence": "high",
                        }
                    ]
                },
                "integrity_statement": {
                    "items": [
                        {
                            "element_id": "integrity_statement.001",
                            "policy": "fixed",
                            "role": "template_fixed",
                            "content": "承诺书",
                            "source_seq_refs": [2],
                            "confidence": "high",
                        }
                    ]
                },
                "body_main": {
                    "items": [
                        {
                            "element_id": "body_main.001",
                            "policy": "fill",
                            "fill_source": "student_content",
                            "source_seq_refs": [3],
                            "confidence": "high",
                        }
                    ]
                },
            },
            "t4": {"section_profiles": []},
        },
    )
    out_dir = tmp_path / "template_generate_observation_replay"

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
            "--agent-observation-replay",
            str(observation_replay_path),
        ],
    )

    assert result.exit_code == 0, result.output
    bundle = read_json(out_dir / "09.1_ai_observation_bundle.json")
    l1_input_contract = read_json(out_dir / "01.5_l1_input_contract.json")
    bridge = read_json(out_dir / "09.25_agent_observation_bridge.json")
    ai_t3 = read_yaml(out_dir / "03.1_t3_ai_element_observation.yaml")
    assert bundle["source_render_hash"] == (
        l1_input_contract["visual_page_index"]["source_render_hash"]
    )
    assert ai_t3["route"]["route_id"] == "ai_raw"
    assert ai_t3["route"]["availability"] == "AVAILABLE"
    assert ai_t3["items"]
    assert all(
        item.get("reason_code") != "OBSERVATION-HASH-MISMATCH"
        for item in bridge["manual_review_items"]
    )
    assert (out_dir / "09.1_ai_observation_bundle.json").exists()
