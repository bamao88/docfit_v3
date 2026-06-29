from __future__ import annotations

from docx import Document
from typer.testing import CliRunner

from docfit.cli import main as cli_main
from docfit.core.models import StageResult
from docfit.core.status import Status


def test_cli_live_without_packet_requests_auto_render_packet(monkeypatch, tmp_path) -> None:
    source = tmp_path / "template.docx"
    Document().save(source)
    captured = {}

    def fake_run_template_generate_eval(
        _root,
        _template,
        _out,
        *,
        agent_config=None,
    ):
        captured["agent_config"] = agent_config
        return StageResult("template_generate", Status.PASS)

    monkeypatch.setattr(
        cli_main,
        "run_template_generate_eval",
        fake_run_template_generate_eval,
    )

    result = CliRunner().invoke(
        cli_main.app,
        [
            "eval",
            "template-generate",
            "--template",
            str(source),
            "--out",
            str(tmp_path / "out"),
            "--agent-live",
        ],
    )

    assert result.exit_code == 0, result.output
    agent_config = captured["agent_config"]
    assert agent_config.transport == "kimi"
    assert agent_config.render_packet_path is None
    assert agent_config.allow_live_without_render_packet is True
