from __future__ import annotations

from pathlib import Path

from docx import Document
from typer.testing import CliRunner

from docfit.cli.main import app
from docfit.convert.orchestrator import run_template_generate_eval
from docfit.core.io import read_json, sha256_file, write_yaml


def test_template_generation_judge_cli_writes_bundle_stage_checks_and_reports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "inputs/targets/demo-school/raw/source_template.docx"
    _write_source_docx(source, ["学校固定封面", "目录", "正文开始"])
    _write_demo_standard_set(tmp_path, sha256_file(source))
    bundle_root = tmp_path / "test_outputs/debug/template_generation/demo-school-run"
    run_dir = bundle_root / "eval_runs/template_generate"
    run_template_generate_eval(tmp_path, source, run_dir)

    out_dir = bundle_root / "eval_runs/template_generation_judge"
    result = CliRunner().invoke(
        app,
        [
            "eval",
            "template-generation-judge",
            "--school",
            "demo-school",
            "--run",
            str(run_dir),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "status = UNKNOWN" in result.stdout
    assert (out_dir / "summary.json").exists()
    assert (out_dir / "findings.json").exists()
    assert (out_dir / "template_generation_run_bundle.json").exists()
    assert (out_dir / "template_generation_stage_checks.json").exists()
    assert (out_dir / "template_generation_stage_standard_quality_report.json").exists()
    assert (out_dir / "template_generation_stage_standard_quality_report.md").exists()
    assert (out_dir / "template_generation_judge_report.json").exists()
    assert (out_dir / "template_generation_judge_report.md").exists()
    expected_stage_reports = [
        "00_template_generation_request_standard_quality_report",
        "01_document_facts_standard_quality_report",
        "01.5_l1_input_contract_standard_quality_report",
        "02_unit_map_standard_quality_report",
        "03_element_spec_standard_quality_report",
        "04_global_spec_standard_quality_report",
        "05_template_spec_standard_quality_report",
        "06.1_fillable_template_standard_quality_report",
        "06.2_build_manifest_standard_quality_report",
        "07_verification_report_standard_quality_report",
    ]
    for report_name in expected_stage_reports:
        assert (out_dir / f"{report_name}.json").exists()
        assert (out_dir / f"{report_name}.md").exists()
    expected_stage_diff_reports = [
        "00_template_generation_request_standard_diff_report",
        "01_document_facts_standard_diff_report",
        "01.5_l1_input_contract_standard_diff_report",
        "02_unit_map_standard_diff_report",
        "03_element_spec_standard_diff_report",
        "04_global_spec_standard_diff_report",
        "05_template_spec_standard_diff_report",
        "06.1_fillable_template_standard_diff_report",
        "06.2_build_manifest_standard_diff_report",
        "07_verification_report_standard_diff_report",
    ]
    for report_name in expected_stage_diff_reports:
        assert (out_dir / f"{report_name}.json").exists()
        assert (out_dir / f"{report_name}.md").exists()
    assert (out_dir / "template_generation_root_cause_report.json").exists()
    assert (out_dir / "template_generation_root_cause_report.md").exists()
    assert (out_dir / "template_agent_bridge_standard_acceptance.json").exists()
    assert (out_dir / "template_agent_bridge_standard_acceptance.md").exists()
    assert (out_dir / "template_generation_route_eval_report.json").exists()
    assert (out_dir / "template_generation_route_eval_report.md").exists()

    summary = read_json(out_dir / "summary.json")
    run_bundle = read_json(out_dir / "template_generation_run_bundle.json")
    stage_checks = read_json(out_dir / "template_generation_stage_checks.json")
    judge_report = read_json(out_dir / "template_generation_judge_report.json")
    unit_quality = read_json(out_dir / "02_unit_map_standard_quality_report.json")
    unit_diff = read_json(out_dir / "02_unit_map_standard_diff_report.json")
    root_cause_report = read_json(out_dir / "template_generation_root_cause_report.json")
    bridge_acceptance = read_json(out_dir / "template_agent_bridge_standard_acceptance.json")
    route_eval = read_json(out_dir / "template_generation_route_eval_report.json")
    l1_contract = read_json(run_dir / "01.5_l1_input_contract.json")
    fillable_quality = read_json(
        out_dir / "06.1_fillable_template_standard_quality_report.json"
    )

    assert summary["status"] == "UNKNOWN"
    assert run_bundle["status"] == "PASS"
    assert run_bundle["source_run_id"] == "template_generate"
    assert run_bundle["artifacts"]["document_facts"]["source_kind"] == "ordered_top_level"
    assert len(stage_checks) == 5
    assert stage_checks[0]["stage_id"] == "T1"
    assert stage_checks[0]["status"] == "UNKNOWN"
    assert stage_checks[0]["audit_status"] == "PASS"
    assert judge_report["first_bad_stage"] == "T1"
    assert judge_report["standard_acceptance_status"] == "UNKNOWN"
    assert judge_report["signoff_status"] == "NOT_SIGNABLE"
    assert "t1_document_facts.verifier_state=not_configured" in judge_report[
        "signoff_blockers"
    ]
    assert judge_report["owner_summary"]["verifier"] >= 5
    assert len(judge_report["stage_standard_diffs"]) >= 5
    assert len(judge_report["mismatches"]) >= 5
    assert len(judge_report["root_causes"]) >= 5
    assert len(judge_report["owner_assignments"]) >= 5
    assert len(judge_report["fix_plan"]) >= 5
    assert len(judge_report["stage_standard_quality_reports"]) == 10
    assert len(judge_report["stage_standard_diff_reports"]) == 10
    assert summary["coverage"]["standard_acceptance_status"] == "UNKNOWN"
    assert summary["coverage"]["signoff_status"] == "NOT_SIGNABLE"
    assert summary["coverage"]["mismatch_count"] >= 5
    assert summary["coverage"]["root_cause_count"] >= 5
    assert unit_quality["report_kind"] == "standard_quality_report"
    assert unit_quality["stage_id"] == "T2"
    assert unit_quality["stage_key"] == "t2_unit_pagination"
    assert unit_quality["artifact_name"] == "02_unit_map.yaml"
    assert unit_quality["artifact_under_test"] == "unit_map"
    assert unit_quality["audit_status"] == "PASS"
    assert unit_quality["standard_acceptance_status"] == "UNKNOWN"
    assert unit_quality["signoff_status"] == "NOT_SIGNABLE"
    assert unit_quality["owner_summary"]["verifier"] >= 1
    assert unit_diff["report_kind"] == "standard_diff_report"
    assert unit_diff["stage_id"] == "T2"
    assert unit_diff["mismatches"][0]["id"] == "T2-MISMATCH-001"
    assert unit_diff["root_causes"][0]["category"] == "comparator_issue"
    assert unit_diff["owner_assignments"][0]["primary"] == "standard_judge_owner"
    assert unit_diff["fix_plan"][0]["action"].startswith("Implement or configure")
    assert root_cause_report["report_kind"] == "root_cause_report"
    assert len(root_cause_report["mismatches"]) == len(judge_report["mismatches"])
    assert bridge_acceptance["report_kind"] == "agent_bridge_standard_acceptance"
    assert bridge_acceptance["bridge_present"] is False
    assert "bridged_output_accuracy" in bridge_acceptance
    assert route_eval["artifact_type"] == "template_generation_route_eval_report"
    assert l1_contract["artifact_type"] == "template_generation_l1_input_contract"
    assert "source_text_index" in l1_contract
    assert "source_object_index" in l1_contract
    assert "layout_fact_index" in l1_contract
    assert "visual_page_index" in l1_contract
    assert "run_index" in l1_contract
    assert "bundle_gate_view" not in l1_contract
    assert len(route_eval["routes"]) == 23
    assert set(route_eval["stage_metrics"]) == {
        "T1",
        "L1",
        "T2",
        "T3",
        "T4",
        "T5",
        "T6",
        "T7",
        "POST_T6",
    }
    assert route_eval["stage_metrics"]["L1"]["coverage"]["available"] is True
    assert route_eval["stage_metrics"]["T6"]["route_availability"]["merged"] == "AVAILABLE"
    assert route_eval["stage_metrics"]["POST_T6"]["route_availability"]["merged"] == "AVAILABLE"
    assert route_eval["stage_metrics"]["T5"]["route_availability"]["code_raw"] in {
        "AVAILABLE",
        "OUT_OF_SCOPE",
    }
    assert route_eval["stage_metrics"]["T5"]["route_availability"]["ai_raw"] in {
        "NOT_AVAILABLE",
        "OUT_OF_SCOPE",
    }
    t2_ai_route = next(
        route
        for route in route_eval["routes"]
        if route["stage_id"] == "T2" and route["route_id"] == "ai_raw"
    )
    assert t2_ai_route["availability"] == "NOT_AVAILABLE"
    assert "no AI observation bundle" in t2_ai_route["reason"]
    assert t2_ai_route["payload_summary"]["item_count"] == 0
    assert "no AI observation bundle" in route_eval["stage_metrics"]["T2"]["route_reasons"]["ai_raw"]
    ai_not_available = [
        mismatch
        for mismatch in route_eval["mismatches"]
        if mismatch["stage_id"] == "T2" and mismatch["type"] == "ai_raw_not_available"
    ][0]
    assert "no AI observation bundle" in ai_not_available["observed"]
    assert "mismatches" in route_eval
    assert "root_causes" in route_eval
    assert "owner_assignments" in route_eval
    assert "fix_plan" in route_eval
    assert fillable_quality["stage_id"] == "T6"
    assert fillable_quality["stage_key"] == "t6_fillable_template"
    assert fillable_quality["comparison_scope"] == "run_bundle_artifact_binding"
    assert fillable_quality["standard_acceptance_status"] == "PASS"


def test_template_generation_standard_quality_cli_supports_profile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "inputs/targets/demo-school/raw/source_template.docx"
    _write_source_docx(source, ["学校固定封面"])
    _write_demo_standard_set(tmp_path, sha256_file(source))

    out_dir = tmp_path / "runs/eval/template_generation_standard_quality/demo-profile"
    result = CliRunner().invoke(
        app,
        [
            "eval",
            "template-generation-standard-quality",
            "--profile",
            "demo-profile",
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "status = PASS" in result.stdout
    report = read_json(out_dir / "template_generation_stage_standard_quality_report.json")
    assert report["scope"] == "demo-profile"
    assert report["status"] == "PASS"


def test_template_generation_full_cli_writes_gap_judge_and_full_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "inputs/targets/demo-school/raw/source_template.docx"
    _write_source_docx(source, ["学校固定封面", "目录", "正文开始"])
    _write_demo_standard_set(tmp_path, sha256_file(source))

    out_dir = tmp_path / "runs/full"
    result = CliRunner().invoke(
        app,
        [
            "eval",
            "template-generation-full",
            "--school",
            "demo-school",
            "--template",
            str(source),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (out_dir / "eval_runs/template_generate/summary.json").exists()
    assert (out_dir / "eval_runs/template_gap/artifacts/template_gap_report.json").exists()
    assert (
        out_dir
        / "eval_runs/template_generation_judge/template_generation_route_eval_report.json"
    ).exists()
    assert (out_dir / "full_summary.json").exists()
    summary = read_json(out_dir / "full_summary.json")
    assert summary["artifact_type"] == "template_generation_full_summary"
    assert summary["stage_statuses"]["template_generate"] in {"PASS", "UNKNOWN", "FAIL"}
    assert summary["final_gap"]
    assert "first_bad_stage" in summary
    assert "render_l1" in summary["gates"]
    assert "t3_residual" in summary["gates"]
    assert "ai_primary" in summary["gates"]
    run_manifest = read_json(out_dir / "run_manifest.json")
    nested_manifest = read_json(
        out_dir / "eval_runs/template_generate/run_manifest.json"
    )
    assert run_manifest["entrypoint"] == "python.run_template_generation_full_eval"
    assert run_manifest["ai_mode"] == nested_manifest["ai_mode"] == "off"
    assert run_manifest["source_render_hash"] == nested_manifest["source_render_hash"]
    assert run_manifest["l1_contract_hash"] == nested_manifest["l1_contract_hash"]
    assert run_manifest["api_call_count"] == nested_manifest["api_call_count"] == 0
    quality_report = summary["quality_report"]
    assert quality_report["artifact_type"] == "template_generation_full_quality_report"
    assert quality_report["overall_status"] in {"PASS", "UNKNOWN", "FAIL"}
    stage_cards = quality_report["stage_cards"]
    assert [card["stage_id"] for card in stage_cards] == [
        "T1",
        "L1",
        "T2",
        "T3",
        "T4",
        "T5",
        "T6",
        "T7",
        "POST_T6",
    ]
    assert all("quality_checks" in card for card in stage_cards)
    assert all("mismatches" in card for card in stage_cards)
    assert all("root_causes" in card for card in stage_cards)
    assert all("owner_assignments" in card for card in stage_cards)
    assert all("fix_plan" in card for card in stage_cards)
    assert "top_blockers" in quality_report
    assert "next_optimization_targets" in quality_report


def test_route_eval_reports_t4_layout_hint_consumption_gaps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "inputs/targets/demo-school/raw/source_template.docx"
    _write_source_docx(source, ["封面", "正文"])
    _write_demo_standard_set(tmp_path, sha256_file(source))
    from docfit.template_generation.agent.packet import build_template_agent_render_packet
    from docfit.template_generation.artifacts import source_tree_from_document_facts
    from docfit.template_generation.source_tree import inspect_document_facts_docx
    from docfit.template_generation.structure_candidates import build_template_structure_candidates
    from docfit.core.io import write_json

    facts = inspect_document_facts_docx(source)
    candidates = build_template_structure_candidates(source_tree_from_document_facts(facts))
    packet = build_template_agent_render_packet(
        document_facts=facts,
        structure_candidates=candidates,
        source_template_docx=source,
    )
    packet["render_status"] = "real_render"
    packet["render_artifacts"]["render_status"] = "real_render"
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
                "items": [
                    {
                        "section_profile_id": "section_1",
                        "source_seq_refs": [1],
                        "confidence": "high",
                    }
                ],
                "abstain": False,
                "quality_report": {"demotions": []},
            },
        },
    )
    run_dir = tmp_path / "runs/template_generate"
    generate_result = CliRunner().invoke(
        app,
        [
            "eval",
            "template-generate",
            "--template",
            str(source),
            "--out",
            str(run_dir),
            "--agent-render-packet",
            str(packet_path),
            "--agent-observation-bundle",
            str(bundle_path),
        ],
    )
    assert generate_result.exit_code == 0, generate_result.output
    out_dir = tmp_path / "runs/template_generation_judge"
    judge_result = CliRunner().invoke(
        app,
        [
            "eval",
            "template-generation-judge",
            "--school",
            "demo-school",
            "--run",
            str(run_dir),
            "--out",
            str(out_dir),
        ],
    )
    assert judge_result.exit_code == 0, judge_result.output

    route_eval = read_json(out_dir / "template_generation_route_eval_report.json")
    consumption = route_eval["stage_metrics"]["T4"]["hint_consumption"]
    assert consumption["section_profile_hint_count"] == 1
    assert consumption["page_numbering_hint_count"] == 0
    assert consumption["section_profile_effective_action_count"] == 1
    assert consumption["page_numbering_effective_action_count"] == 0
    mismatch_types = {
        mismatch["type"] for mismatch in route_eval["mismatches"]
    }
    assert "t4_section_profile_hint_advisory_only" not in mismatch_types


def _write_source_docx(path: Path, paragraphs: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    doc.save(path)


def _write_demo_standard_set(root: Path, source_hash: str) -> None:
    target_dir = root / "standards/targets/demo-school/v1"
    write_yaml(
        target_dir / "target.standard.yaml",
        {
            "standard_id": "demo-school-v1",
            "school_id": "demo-school",
            "template_version": "v1",
            "source": {
                "template_docx": "inputs/targets/demo-school/raw/source_template.docx",
                "template_docx_sha256": source_hash,
            },
            "evidence_baselines": {
                "template_generation_final": "template_quality/final_template.expected.yaml",
                "template_generation_stages": {
                    "t1_document_facts": "template_generation/t1_document_facts.standard.yaml",
                    "t2_unit_pagination": "template_generation/t2_unit_pagination.standard.yaml",
                    "t3_element_policy": "template_generation/t3_element_policy.standard.yaml",
                    "t4_global_layout": "template_generation/t4_global_layout.standard.yaml",
                    "t5_template_spec": "template_generation/t5_template_spec.standard.yaml",
                },
            },
            "coverage_requirements": {"profile": "demo-profile", "required_capabilities": []},
        },
    )
    write_yaml(
        target_dir / "template_quality/final_template.expected.yaml",
        {
            "baseline_type": "template_generation_final",
            "school_id": "demo-school",
            "expected": {
                "units": [
                    {"unit_id": "cover"},
                    {"unit_id": "toc"},
                    {"unit_id": "body_main"},
                ]
            },
        },
    )
    write_yaml(
        target_dir / "template_generation/t1_document_facts.standard.yaml",
        _stage_standard(
            "demo-school",
            "T1",
            "t1_document_facts",
            "document_facts",
            source_hash,
            {
                "artifact_type": "document_facts",
                "source_fact_contract": {
                    "required_top_level_fields": [
                        "artifact_type",
                        "metadata",
                        "body_flow",
                        "runs",
                        "data",
                        "indexes",
                        "warnings",
                    ],
                    "required_data_groups": [
                        "sections",
                        "headers_footers",
                        "fields",
                        "numbering_definitions",
                        "numbering_refs",
                        "images",
                        "tables",
                    ],
                    "locator_contract": {
                        "source_seq_required_for_visible_body_flow": True,
                        "source_ref_required_for_visible_body_flow": True,
                    },
                },
                "forbidden_semantic_fields": [
                    "is_toc_entry",
                    "is_spacing_line",
                    "looks_like_instruction_text",
                    "likely_unit_heading",
                    "large_font",
                    "short_text",
                    "unit_id",
                    "policy",
                    "confidence",
                ],
            },
        ),
    )
    for stage_id, stage_key, artifact, expected in [
        (
            "T2",
            "t2_unit_pagination",
            "unit_map",
            {
                "unit_order": ["cover", "toc", "body_main"],
                "units": [{"unit_id": "cover"}, {"unit_id": "toc"}, {"unit_id": "body_main"}],
            },
        ),
        (
            "T3",
            "t3_element_policy",
            "element_spec",
            {
                "unit_order": ["cover", "toc", "body_main"],
                "policy_groups": {
                    "fixed_units": ["cover"],
                    "generated_units": ["toc"],
                    "fill_units": ["body_main"],
                },
                "element_policy_contract": {
                    "required_fields_by_policy": {
                        "fill": ["fill_source", "source_refs", "source_seq_refs"],
                        "generated": ["generated.field_type", "source_refs"],
                    }
                },
            },
        ),
        (
            "T4",
            "t4_global_layout",
            "global_spec",
            {
                "unit_order": ["cover", "toc", "body_main"],
                "global_layout_contract": {
                    "artifact_type": "global_spec",
                    "section_profiles_required": True,
                },
            },
        ),
        (
            "T5",
            "t5_template_spec",
            "template_spec",
            {
                "unit_order": ["cover", "toc", "body_main"],
                "template_spec_contract": {
                    "required_input_hashes": [
                        "document_facts",
                        "unit_map",
                        "element_spec",
                        "global_spec",
                    ],
                    "review_flags_must_not_be_dropped": True,
                },
            },
        ),
    ]:
        write_yaml(
            target_dir / "template_generation" / f"{stage_key}.standard.yaml",
            _stage_standard(
                "demo-school",
                stage_id,
                stage_key,
                artifact,
                source_hash,
                expected,
            ),
        )


def _stage_standard(
    school_id: str,
    stage_id: str,
    stage_key: str,
    artifact: str,
    source_hash: str,
    expected: dict,
) -> dict:
    return {
        "baseline_type": f"template_generation_{stage_key}",
        "school_id": school_id,
        "stage_id": stage_id,
        "standard_id": f"{school_id}-{stage_key}",
        "standard_state": "signed_pending_verifier",
        "verifier_state": "not_configured",
        "gate_enabled": False,
        "artifact_under_test": artifact,
        "accepted_source_facts": {"template_docx_sha256": source_hash},
        "expected": expected,
    }
