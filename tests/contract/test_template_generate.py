from __future__ import annotations

from pathlib import Path

from docx import Document
from typer.testing import CliRunner

from docfit.cli.main import app
from docfit.convert.orchestrator import run_template_generate_eval
from docfit.core.io import read_json, sha256_file
from docfit.core.status import Status
from docfit.stages.template_generate.runner import BODY_SLOT_MARKER


def write_source_docx(path: Path, paragraphs: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    doc.save(path)


def docx_texts(path: Path) -> list[str]:
    return [paragraph.text for paragraph in Document(path).paragraphs]


def test_template_generate_writes_scaffold_docx_and_manifest(tmp_path) -> None:
    source = tmp_path / "inputs/school-template.docx"
    write_source_docx(source, ["学校固定封面", "正文开始"])

    result = run_template_generate_eval(tmp_path, source, tmp_path / "template_generate")

    generated = tmp_path / "template_generate/generated_template.docx"
    manifest_path = (
        tmp_path / "template_generate/artifacts/template_generation_manifest.json"
    )
    plan_path = tmp_path / "template_generate/artifacts/template_generation_plan.json"
    summary = read_json(tmp_path / "template_generate/summary.json")
    manifest = read_json(manifest_path)

    assert result.status == Status.PASS
    assert generated.exists()
    assert manifest_path.exists()
    assert plan_path.exists()
    assert summary["status"] == Status.PASS.value
    assert summary["artifacts"]["generated_template_docx"] == str(generated)
    assert BODY_SLOT_MARKER in docx_texts(generated)
    assert manifest["strategy"] == "source_copy_scaffold"
    assert manifest["output"]["generated_template_docx"] == str(generated)
    assert manifest["output"]["generated_template_docx_hash"] == sha256_file(generated)
    assert manifest["slots"][0]["slot_id"] == "slot_body_start"
    assert manifest["actions_deferred"]


def test_template_generate_preserves_existing_body_slot(tmp_path) -> None:
    source = tmp_path / "inputs/school-template-with-slot.docx"
    write_source_docx(source, ["学校固定封面", BODY_SLOT_MARKER])

    result = run_template_generate_eval(tmp_path, source, tmp_path / "template_generate")
    generated = tmp_path / "template_generate/generated_template.docx"
    manifest = read_json(
        tmp_path / "template_generate/artifacts/template_generation_manifest.json"
    )

    assert result.status == Status.PASS
    assert docx_texts(generated).count(BODY_SLOT_MARKER) == 1
    assert manifest["actions_executed"][1]["action_type"] == "preserve_existing_body_slot"
    assert manifest["slots"][0]["source"] == "source_template"


def test_template_generate_invalid_docx_fails_without_output(tmp_path) -> None:
    source = tmp_path / "inputs/not-a-docx.docx"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("not a zip package", encoding="utf-8")

    result = run_template_generate_eval(tmp_path, source, tmp_path / "template_generate")
    summary = read_json(tmp_path / "template_generate/summary.json")

    assert result.status == Status.FAIL
    assert summary["status"] == Status.FAIL.value
    assert summary["blocked_at"] == "template_generate"
    assert not (tmp_path / "template_generate/generated_template.docx").exists()
    assert any(
        finding.type == "template_generation_source_invalid"
        for finding in result.findings
    )


def test_template_generate_cli_writes_public_outputs(tmp_path) -> None:
    source = tmp_path / "inputs/school-template.docx"
    out_dir = tmp_path / "cli_template_generate"
    write_source_docx(source, ["学校固定封面"])

    result = CliRunner().invoke(
        app,
        [
            "eval",
            "template-generate",
            "--template",
            str(source),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert "status = PASS" in result.stdout
    assert (out_dir / "generated_template.docx").exists()
    assert (out_dir / "artifacts/template_generation_manifest.json").exists()
    assert (out_dir / "summary.json").exists()
