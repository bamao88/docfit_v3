from __future__ import annotations

from docx import Document
from typer.testing import CliRunner

from docfit.cli.main import app
from docfit.core.io import read_json, read_yaml, write_json
from docfit.template_generation.agent.packet import build_template_agent_render_packet
from docfit.template_generation.artifacts import source_tree_from_document_facts
from docfit.template_generation.source_tree import inspect_document_facts_docx
from docfit.template_generation.structure_candidates import build_template_structure_candidates


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
    ai_t4_global_spec = read_yaml(out_dir / "04.1.5_t4_ai_global_spec.yaml")
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
    assert ai_t4_global_spec["artifact_type"] == "global_spec"
    assert ai_t4_global_spec["route"]["route_id"] == "ai_raw"
    assert ai_t4_global_spec["route"]["availability"] == "AVAILABLE"
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
    hierarchical_input = read_json(
        out_dir / "03.0.5_t3_hierarchical_stage_input.json"
    )
    sparse_trace = read_json(out_dir / "03.1.5_t3_sparse_decision_trace.json")
    atomic_comparison = read_json(
        out_dir / "03.2.5_t3_atomic_route_comparison.json"
    )
    assert bundle["source_render_hash"] == (
        l1_input_contract["visual_page_index"]["source_render_hash"]
    )
    assert ai_t3["route"]["route_id"] == "ai_raw"
    assert ai_t3["route"]["availability"] == "AVAILABLE"
    assert ai_t3["items"]
    assert hierarchical_input["artifact_type"] == "t3_hierarchical_stage_input"
    assert sparse_trace["artifact_type"] == "t3_sparse_decision_trace"
    assert sparse_trace["stage_input_ref"]["tree_hash"] == hierarchical_input["tree_hash"]
    assert sparse_trace["validation"] == {"valid": True, "errors": []}
    assert len({row["member_ref"] for row in sparse_trace["atomic_coverage"]}) == len(
        sparse_trace["atomic_coverage"]
    )
    assert atomic_comparison["validation"]["valid"] is True
    assert atomic_comparison["stage_input_ref"]["tree_hash"] == hierarchical_input["tree_hash"]
    assert atomic_comparison["summary"]["atomic_member_count"] == len(
        sparse_trace["atomic_coverage"]
    )
    assert all(
        item.get("reason_code") != "OBSERVATION-HASH-MISMATCH"
        for item in bridge["manual_review_items"]
    )
    assert (out_dir / "09.1_ai_observation_bundle.json").exists()
    assert (out_dir / "03.0.5_t3_hierarchical_stage_input.json").exists()
    assert (out_dir / "03.1.5_t3_sparse_decision_trace.json").exists()
    assert (out_dir / "03.2.5_t3_atomic_route_comparison.json").exists()
