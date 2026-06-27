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
    run_dir = tmp_path / "runs/template_generation/demo-school/eval_runs/template_generate"
    run_template_generate_eval(tmp_path, source, run_dir)

    out_dir = tmp_path / "runs/eval/template_generation_judge/demo-school/template_generate"
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

    summary = read_json(out_dir / "summary.json")
    run_bundle = read_json(out_dir / "template_generation_run_bundle.json")
    stage_checks = read_json(out_dir / "template_generation_stage_checks.json")
    judge_report = read_json(out_dir / "template_generation_judge_report.json")

    assert summary["status"] == "UNKNOWN"
    assert run_bundle["status"] == "PASS"
    assert run_bundle["source_run_id"] == "template_generate"
    assert run_bundle["artifacts"]["document_facts"]["source_kind"] == "ordered_top_level"
    assert len(stage_checks) == 5
    assert stage_checks[0]["stage_id"] == "T1"
    assert stage_checks[0]["status"] == "UNKNOWN"
    assert stage_checks[0]["audit_status"] == "PASS"
    assert judge_report["first_bad_stage"] == "T1"


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
