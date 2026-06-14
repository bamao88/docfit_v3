from __future__ import annotations

from pathlib import Path

from docfit.convert.orchestrator import run_e2e_eval, run_render_eval
from docfit.core.io import read_json, write_json
from docfit.core.status import Status
from docfit.harness.standards import load_standard_bundle
from docfit.stages.render.runner import render_docx


ROOT = Path.cwd()


def _bundle():
    bundle, findings = load_standard_bundle(ROOT, "demo-school")
    assert bundle is not None
    assert findings == []
    return bundle


def test_bootstrap_e2e_pass(tmp_path) -> None:
    result = run_e2e_eval(
        ROOT,
        "demo-school",
        ROOT / "fixtures/bootstrap/students/demo-thesis.docx",
        tmp_path / "bootstrap_pass",
    )

    assert result.status == Status.PASS
    assert (tmp_path / "bootstrap_pass/final.docx").exists()
    assert (tmp_path / "bootstrap_pass/summary.json").exists()
    assert (tmp_path / "bootstrap_pass/ai/diagnosis_packet.json").exists()


def test_convert_blocks_on_unknown(tmp_path) -> None:
    final_copy = tmp_path / "out/final.docx"
    result = run_e2e_eval(
        ROOT,
        "demo-school",
        ROOT / "fixtures/bootstrap/students/with-unsupported-textbox.docx",
        tmp_path / "bootstrap_unknown",
        final_copy=final_copy,
    )

    assert result.status == Status.UNKNOWN
    assert not final_copy.exists()
    assert result.blocked_at == "content"


def test_fail_when_renderer_skips_action(tmp_path) -> None:
    pass_result = run_e2e_eval(
        ROOT,
        "demo-school",
        ROOT / "fixtures/bootstrap/students/demo-thesis.docx",
        tmp_path / "bootstrap_pass",
    )
    assert pass_result.status == Status.PASS

    result = run_render_eval(
        ROOT,
        "demo-school",
        tmp_path / "bootstrap_pass/artifacts/template_artifact.json",
        tmp_path / "bootstrap_pass/artifacts/placement_plan.json",
        tmp_path / "render_fail",
        simulate_skip_action="a_002",
    )

    assert result.status == Status.FAIL
    assert any(finding.type == "renderer_skipped_action" for finding in result.findings)


def test_fail_when_renderer_writes_wrong_content(tmp_path) -> None:
    pass_result = run_e2e_eval(
        ROOT,
        "demo-school",
        ROOT / "fixtures/bootstrap/students/demo-thesis.docx",
        tmp_path / "bootstrap_pass",
    )
    assert pass_result.status == Status.PASS

    template_artifact = read_json(tmp_path / "bootstrap_pass/artifacts/template_artifact.json")
    placement_plan = read_json(tmp_path / "bootstrap_pass/artifacts/placement_plan.json")
    first_text_action = next(
        action
        for action in placement_plan["data"]["actions"]
        if action.get("payload", {}).get("type") == "text"
    )
    first_text_action["payload"]["text"] = "This text was not in the student document."

    result = render_docx(
        template_artifact,
        placement_plan,
        _bundle(),
        tmp_path / "render_wrong_content",
    )

    assert result.status == Status.FAIL
    assert any(finding.type == "blocking_feature_diff" for finding in result.findings)


def test_fail_when_render_artifact_hash_chain_mismatches(tmp_path) -> None:
    pass_result = run_e2e_eval(
        ROOT,
        "demo-school",
        ROOT / "fixtures/bootstrap/students/demo-thesis.docx",
        tmp_path / "bootstrap_pass",
    )
    assert pass_result.status == Status.PASS

    template_artifact = read_json(tmp_path / "bootstrap_pass/artifacts/template_artifact.json")
    template_artifact["status_notes"].append("tampered after placement")
    tampered_template = tmp_path / "tampered_template_artifact.json"
    write_json(tampered_template, template_artifact)

    result = run_render_eval(
        ROOT,
        "demo-school",
        tampered_template,
        tmp_path / "bootstrap_pass/artifacts/placement_plan.json",
        tmp_path / "render_hash_mismatch",
    )

    assert result.status == Status.FAIL
    assert any(finding.type == "artifact_hash_mismatch" for finding in result.findings)
