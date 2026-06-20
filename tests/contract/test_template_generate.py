from __future__ import annotations

from pathlib import Path

from docx import Document
from typer.testing import CliRunner

from docfit.cli.main import app
from docfit.convert.orchestrator import run_template_generate_eval
from docfit.core.io import read_json, sha256_file
from docfit.core.status import Status
from docfit.harness.generated_template_inspector import inspect_generated_template_docx
from docfit.stages.template_generate.runner import BODY_SLOT_MARKER, generate_template


ROOT = Path.cwd()


def write_source_docx(path: Path, paragraphs: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    doc.save(path)


def docx_texts(path: Path) -> list[str]:
    return [paragraph.text for paragraph in Document(path).paragraphs]


def table_texts(path: Path) -> list[str]:
    doc = Document(path)
    return [
        cell.text
        for table in doc.tables
        for row in table.rows
        for cell in row.cells
    ]


def test_template_generate_writes_full_stage_artifact_chain(tmp_path) -> None:
    source = tmp_path / "inputs/school-template.docx"
    write_source_docx(source, ["学校固定封面", "目录", "正文开始", "格式说明：小四宋体"])

    result = run_template_generate_eval(tmp_path, source, tmp_path / "template_generate")

    generated = tmp_path / "template_generate/generated_template.docx"
    artifacts = tmp_path / "template_generate/artifacts"
    manifest_path = artifacts / "template_generation_manifest.json"
    plan_path = artifacts / "template_generation_plan.json"
    summary = read_json(tmp_path / "template_generate/summary.json")
    manifest = read_json(manifest_path)
    source_tree = read_json(artifacts / "source_template_tree.json")
    rules = read_json(artifacts / "discovered_template_rules.json")
    template_artifact = read_json(artifacts / "template_artifact.json")
    decisions = read_json(artifacts / "template_unit_decisions.json")

    assert result.status == Status.PASS
    assert generated.exists()
    assert (artifacts / "template_generation_request.json").exists()
    assert source_tree["artifact_type"] == "source_template_tree"
    assert rules["artifact_type"] == "discovered_template_rules"
    assert template_artifact["artifact_type"] == "template_artifact"
    assert decisions["artifact_type"] == "template_unit_decisions"
    assert manifest_path.exists()
    assert plan_path.exists()
    assert summary["status"] == Status.PASS.value
    assert summary["artifacts"]["generated_template_docx"] == str(generated)
    assert BODY_SLOT_MARKER in docx_texts(generated)
    assert manifest["strategy"] == "source_copy_scaffold"
    assert manifest["output"]["generated_template_docx"] == str(generated)
    assert manifest["output"]["generated_template_docx_hash"] == sha256_file(generated)
    assert {slot["slot_id"] for slot in manifest["slots"]} >= {"slot_body_start"}
    assert manifest["actions_executed"]
    assert "actions_deferred" not in manifest
    assert any(unit["unit_id"] == "toc" for unit in rules["units"])
    assert any(
        item["policy"] == "strip"
        for item in template_artifact["data"]["instruction_paragraphs"]
    )


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
    assert any(
        action["action_type"] == "ensure_body_slot"
        for action in manifest["actions_executed"]
    )
    assert any(slot["slot_id"] == "slot_body_start" for slot in manifest["slots"])


def test_template_generate_cleans_instruction_text_inside_table_cells(tmp_path) -> None:
    source = tmp_path / "inputs/school-template-table.docx"
    source.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_paragraph("学校固定封面")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "学生姓名：×××"
    table.cell(0, 1).text = "格式说明：此处用小四宋体"
    doc.save(source)

    result = run_template_generate_eval(tmp_path, source, tmp_path / "template_generate")
    generated = tmp_path / "template_generate/generated_template.docx"
    manifest = read_json(
        tmp_path / "template_generate/artifacts/template_generation_manifest.json"
    )

    assert result.status == Status.PASS
    assert not manifest["actions_requiring_review"]
    assert not any("格式说明" in text for text in table_texts(generated))
    assert any("[[DOCFIT_SLOT:" in text for text in table_texts(generated))


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


def test_template_generate_can_use_signed_school_units(tmp_path) -> None:
    source = tmp_path / "inputs/school-template.docx"
    write_source_docx(source, ["测试大学", "学生姓名：×××"])

    result = run_template_generate_eval(
        ROOT,
        source,
        tmp_path / "template_generate",
        school_id="hunannongye",
    )
    manifest = read_json(
        tmp_path / "template_generate/artifacts/template_generation_manifest.json"
    )

    assert result.status == Status.PASS
    assert any(slot["slot_id"] == "cover.e_003" for slot in manifest["slots"])
    assert "[[DOCFIT_SLOT:cover.e_003]]" in docx_texts(
        tmp_path / "template_generate/generated_template.docx"
    )


def test_template_generate_synthesizes_missing_visible_unit_title(tmp_path) -> None:
    out_dir = tmp_path / "template_generate"

    result = run_template_generate_eval(
        ROOT,
        ROOT / "inputs/school-hunannongye-requirement.docx",
        out_dir,
        school_id="hunannongye",
    )
    manifest = read_json(out_dir / "artifacts/template_generation_manifest.json")
    expected_title = "湖南农业大学全日制普通本科生毕业论文（设计）；成绩评定表"

    assert result.status == Status.PASS
    assert expected_title in docx_texts(out_dir / "generated_template.docx")
    assert any(
        item["unit_id"] == "grade_form"
        and item["element_id"] == "e_001"
        and item["text"] == expected_title
        for item in manifest["synthesized_texts"]
    )


def test_template_generate_inserts_page_and_section_break_before_later_unit(
    tmp_path,
) -> None:
    source = tmp_path / "inputs/school-template.docx"
    source.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    table = doc.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "封面标题"
    doc.add_paragraph("原创性声明")
    doc.add_paragraph("正文开始")
    doc.save(source)
    out_dir = tmp_path / "template_generate"
    target_units = [
        {
            "unit_id": "cover",
            "name": "封面",
            "order": 10,
            "status": "required",
            "page": {"page_break": "是"},
            "elements": [
                {
                    "element_id": "e_001",
                    "name": "封面标题",
                    "policy": "fixed",
                    "content": "封面标题",
                }
            ],
        },
        {
            "unit_id": "integrity_statement",
            "name": "原创性声明",
            "order": 20,
            "status": "required",
            "page": {"page_break": "是", "section_isolation": "是"},
            "elements": [
                {
                    "element_id": "e_001",
                    "name": "原创性声明",
                    "policy": "fixed",
                    "content": "原创性声明",
                }
            ],
        },
    ]

    result = generate_template(source, out_dir, target_units=target_units)
    generated = out_dir / "generated_template.docx"
    manifest = result.artifacts["template_generation_manifest"]
    plan = result.artifacts["template_generation_plan"]
    tree = inspect_generated_template_docx(generated)
    statement = next(
        item
        for item in tree["data"]["paragraphs"]
        if item["text"] == "原创性声明"
    )
    statement_index = int(statement["index"])

    assert result.status == Status.PASS
    assert any(
        action["action_type"] == "insert_page_break_before_unit"
        and action["unit_id"] == "integrity_statement"
        for action in plan["actions"]
    )
    assert any(
        action["action_type"] == "insert_section_break_before_unit"
        and action["unit_id"] == "integrity_statement"
        for action in plan["actions"]
    )
    assert manifest["page_breaks"] == [
        {
            "unit_id": "integrity_statement",
            "source_ref": "word/document.xml:p[1]",
            "output_ref": "word/document.xml:p[1]/pageBreakBefore",
        }
    ]
    assert manifest["section_breaks"] == [
        {
            "unit_id": "integrity_statement",
            "source_ref": "word/document.xml:p[1]",
            "output_ref": "word/document.xml:p[1]/before:sectPr",
        }
    ]
    assert statement_index == 2
    assert statement["style_details"]["paragraph"]["page_break_before"] is True
    assert any(
        item["kind"] == "section"
        and int(item["paragraph_index"]) < int(statement["xml_index"])
        and int(item["paragraph_index"]) >= int(statement["xml_index"]) - 2
        for item in tree["data"]["breaks"]
    )
