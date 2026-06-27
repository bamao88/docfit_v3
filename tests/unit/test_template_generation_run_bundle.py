from __future__ import annotations

from pathlib import Path

from docfit.core.io import sha256_file, write_json, write_yaml
from docfit.harness.template_generation_run_bundle import (
    bind_template_generation_run_bundle,
)
from docfit.harness.template_generation_standard_quality import (
    load_template_generation_standard_set,
)


def test_run_bundle_binds_ordered_artifacts_and_hashes(tmp_path: Path) -> None:
    standard_set = _write_standard_set(tmp_path, "sha256:source")
    run_dir = _write_run_bundle(tmp_path, "sha256:source", include_debug_index=True)

    bundle = bind_template_generation_run_bundle(
        run_dir,
        standard_set=standard_set,
        source_run_id="stable-run",
    )

    assert bundle.status.value == "PASS"
    assert bundle.source_run_id == "stable-run"
    assert bundle.manifest_source == "debug_index"
    assert bundle.artifacts["document_facts"].source_kind == "ordered_top_level"
    assert bundle.artifacts["document_facts"].hash_match is True
    assert bundle.artifacts["build_manifest"].payload["artifact_type"] == "build_manifest"
    assert bundle.findings == []


def test_run_bundle_allows_missing_debug_index_with_finding(tmp_path: Path) -> None:
    standard_set = _write_standard_set(tmp_path, "sha256:source")
    run_dir = _write_run_bundle(tmp_path, "sha256:source", include_debug_index=False)

    bundle = bind_template_generation_run_bundle(
        run_dir,
        standard_set=standard_set,
    )

    assert bundle.status.value == "PASS"
    assert bundle.manifest_source == "filesystem_scan"
    assert {
        finding.type for finding in bundle.findings
    } == {"template_generation_run_bundle_missing_debug_index"}
    assert bundle.findings[0].severity == "advisory"


def test_run_bundle_marks_source_hash_mismatch_unknown(tmp_path: Path) -> None:
    standard_set = _write_standard_set(tmp_path, "sha256:expected")
    run_dir = _write_run_bundle(tmp_path, "sha256:actual", include_debug_index=True)

    bundle = bind_template_generation_run_bundle(
        run_dir,
        standard_set=standard_set,
    )

    assert bundle.status.value == "UNKNOWN"
    assert any(
        finding.type == "template_generation_run_bundle_source_hash_mismatch"
        for finding in bundle.findings
    )


def _write_standard_set(tmp_path: Path, source_hash: str):
    target_dir = tmp_path / "standards/targets/demo-school/v1"
    target_dir.mkdir(parents=True)
    write_yaml(
        target_dir / "target.standard.yaml",
        {
            "school_id": "demo-school",
            "template_version": "v1",
            "source": {"template_docx_sha256": source_hash},
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
        },
    )
    write_yaml(
        target_dir / "template_quality/final_template.expected.yaml",
        {"expected": {"units": [{"unit_id": "cover"}]}},
    )
    for stage_key, stage_id, artifact in [
        ("t1_document_facts", "T1", "document_facts"),
        ("t2_unit_pagination", "T2", "unit_map"),
        ("t3_element_policy", "T3", "element_spec"),
        ("t4_global_layout", "T4", "global_spec"),
        ("t5_template_spec", "T5", "template_spec"),
    ]:
        write_yaml(
            target_dir / "template_generation" / f"{stage_key}.standard.yaml",
            {
                "school_id": "demo-school",
                "stage_id": stage_id,
                "standard_id": f"demo-{stage_key}",
                "verifier_state": "not_configured",
                "gate_enabled": False,
                "artifact_under_test": artifact,
                "accepted_source_facts": {"template_docx_sha256": source_hash},
                "expected": {"unit_order": ["cover"]},
            },
        )
    return load_template_generation_standard_set(tmp_path, "demo-school")


def _write_run_bundle(
    tmp_path: Path,
    source_hash: str,
    *,
    include_debug_index: bool,
) -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_json(
        run_dir / "00_template_generation_request.json",
        {"artifact_type": "template_generation_request", "source_template_hash": source_hash},
    )
    write_json(
        run_dir / "01_document_facts.json",
        {
            "artifact_type": "document_facts",
            "metadata": {},
            "body_flow": [],
            "runs": [],
            "data": {},
            "indexes": {},
            "warnings": [],
        },
    )
    write_yaml(run_dir / "02_unit_map.yaml", {"artifact_type": "unit_map", "units": []})
    write_yaml(run_dir / "03_element_spec.yaml", {"artifact_type": "element_spec", "elements": []})
    write_yaml(run_dir / "04_global_spec.yaml", {"artifact_type": "global_spec", "section_profiles": []})
    write_yaml(run_dir / "05_template_spec.yaml", {"artifact_type": "template_spec", "units": []})
    fillable = run_dir / "06.1_fillable_template.docx"
    fillable.write_bytes(b"fake docx bytes")
    write_json(
        run_dir / "06.2_build_manifest.json",
        {
            "artifact_type": "build_manifest",
            "output": {"fillable_template_docx_hash": sha256_file(fillable)},
        },
    )
    write_json(
        run_dir / "07_verification_report.json",
        {"artifact_type": "verification_report", "status": "UNKNOWN"},
    )
    if include_debug_index:
        files = [
            {
                "name": path.name,
                "path": str(path),
                "sha256": sha256_file(path),
            }
            for path in sorted(run_dir.iterdir())
            if path.name != "99_template_generation_debug_index.json"
        ]
        write_json(
            run_dir / "99_template_generation_debug_index.json",
            {"artifact_type": "template_generation_debug_index", "files": files},
        )
    return run_dir
