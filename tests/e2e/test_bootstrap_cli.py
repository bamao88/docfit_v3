from __future__ import annotations

from pathlib import Path

from docfit.convert.orchestrator import run_e2e_eval, run_render_eval
from docfit.core.status import Status


ROOT = Path.cwd()


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
