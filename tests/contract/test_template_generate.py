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


def table_texts(path: Path) -> list[str]:
    doc = Document(path)
    return [
        cell.text
        for table in doc.tables
        for row in table.rows
        for cell in row.cells
    ]


def test_template_generate_writes_full_stage_artifact_chain(tmp_path) -> None:
    source = tmp_path / "test_inputs/template_generation/school-template.docx"
    write_source_docx(source, ["学校固定封面", "目录", "正文开始", "格式说明：小四宋体"])

    out_dir = (
        tmp_path
        / "test_outputs/debug/template_generation/school-template/eval_runs/template_generate"
    )
    result = run_template_generate_eval(tmp_path, source, out_dir)

    generated = out_dir / "generated_template.docx"
    artifacts = out_dir / "artifacts"
    manifest_path = artifacts / "template_generation_manifest.json"
    plan_path = artifacts / "template_generation_plan.json"
    debug_root = tmp_path / "test_outputs/debug/template_generation/school-template"
    summary = read_json(out_dir / "summary.json")
    manifest = read_json(manifest_path)
    plan = read_json(plan_path)
    source_tree = read_json(artifacts / "source_template_tree.json")
    structure_candidates = read_json(artifacts / "template_structure_candidates.json")
    generation_model = read_json(artifacts / "template_generation_model.json")
    debug_dirs = sorted(
        path for path in debug_root.iterdir() if path.is_dir() and path.name != "eval_runs"
    )
    debug_dir = debug_dirs[0]
    debug_index = read_json(debug_dir / "99_template_generation_debug_index.json")

    assert result.status == Status.PASS
    assert out_dir.parent.name == "eval_runs"
    assert generated.exists()
    assert (artifacts / "template_generation_request.json").exists()
    assert source_tree["artifact_type"] == "source_template_tree"
    assert structure_candidates["artifact_type"] == "template_structure_candidates"
    assert generation_model["artifact_type"] == "template_generation_model"
    assert manifest_path.exists()
    assert plan_path.exists()
    source_seq_refs = [
        item["source_seq"] for item in source_tree["layers"]["body_flow"]
    ]
    assert source_seq_refs == list(range(1, len(source_seq_refs) + 1))
    assert source_tree["indexes"]["by_source_seq"]["1"]["node_id"] == "body_0001"
    assert len(debug_dirs) == 1
    assert debug_dir.parent == debug_root
    assert summary["artifacts"]["template_generation_debug_dir"] == str(debug_dir)
    assert (debug_dir / "00_input_source_template.docx").exists()
    assert (debug_dir / "00_template_generation_request.json").exists()
    assert (debug_dir / "01_source_template_tree.json").exists()
    assert (debug_dir / "02_template_structure_candidates.json").exists()
    assert (debug_dir / "03_template_generation_model.json").exists()
    assert (debug_dir / "04_template_generation_plan.json").exists()
    assert (debug_dir / "05.0_copy_source_docx.docx").exists()
    assert (debug_dir / "05.1_generated_template.docx").exists()
    assert (debug_dir / "05.2_template_generation_manifest.json").exists()
    assert summary["status"] == Status.PASS.value
    assert summary["artifacts"]["generated_template_docx"] == str(generated)
    assert BODY_SLOT_MARKER in docx_texts(generated)
    assert BODY_SLOT_MARKER not in docx_texts(debug_dir / "05.0_copy_source_docx.docx")
    assert "格式说明：小四宋体" in docx_texts(debug_dir / "05.0_copy_source_docx.docx")
    assert manifest["strategy"] == "source_copy_scaffold"
    assert manifest["debug_snapshot"]["dir"] == str(debug_dir)
    assert manifest["output"]["generated_template_docx"] == str(generated)
    assert manifest["output"]["generated_template_docx_hash"] == sha256_file(generated)
    assert {
        item["name"] for item in debug_index["files"]
    } >= {
        "00_input_source_template.docx",
        "05.0_copy_source_docx.docx",
        "05.1_generated_template.docx",
    }
    assert {slot["slot_id"] for slot in manifest["slots"]} >= {"slot_body_start"}
    assert manifest["actions_executed"]
    assert "actions_deferred" not in manifest
    assert any(unit["unit_id"] == "toc" for unit in structure_candidates["units"])
    assert any(
        item["policy"] == "strip"
        for item in generation_model["cleanup"]
    )
    assert all("affected_source_seq_refs" in action for action in plan["actions"])


def test_template_generate_preserves_existing_body_slot(tmp_path) -> None:
    source = tmp_path / "test_inputs/template_generation/school-template-with-slot.docx"
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
    source = tmp_path / "test_inputs/template_generation/school-template-table.docx"
    source.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_paragraph("摘要")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "学生姓名：×××"
    table.cell(0, 1).text = "格式说明：此处用小四宋体"
    doc.add_paragraph("正文")
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
    source = tmp_path / "test_inputs/template_generation/not-a-docx.docx"
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
    source = tmp_path / "test_inputs/template_generation/school-template.docx"
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


def test_template_generate_cli_rejects_school_standard_input(tmp_path) -> None:
    source = tmp_path / "test_inputs/template_generation/school-template.docx"
    out_dir = tmp_path / "cli_template_generate"
    write_source_docx(source, ["学校固定封面"])

    result = CliRunner().invoke(
        app,
        [
            "eval",
            "template-generate",
            "--school",
            "hunannongye",
            "--template",
            str(source),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code != 0
    assert "No such option" in result.output or "No such option" in result.stderr


def test_template_generate_marks_fixed_unit_as_whole_unit_copy(tmp_path) -> None:
    source = tmp_path / "test_inputs/template_generation/school-template.docx"
    out_dir = tmp_path / "template_generate"
    write_source_docx(source, ["封面", "参考文献"])

    result = run_template_generate_eval(tmp_path, source, out_dir)
    generation_model = read_json(out_dir / "artifacts/template_generation_model.json")
    plan = read_json(out_dir / "artifacts/template_generation_plan.json")
    cover = next(
        unit for unit in generation_model["unit_strategies"] if unit["unit_id"] == "cover"
    )

    assert result.status == Status.PASS
    assert cover["generation_mode"] == "whole_unit_copy"
    assert cover["generation_policy"] == "whole_unit_copy"
    references = next(
        unit
        for unit in generation_model["unit_strategies"]
        if unit["unit_id"] == "references"
    )
    assert references["generation_mode"] == "copy_then_patch"
    assert references["generation_policy"] == "unit_actions"
    assert cover["decisions"] == [
        {
            "copy_scope": "whole_unit",
            "decision_id": "cover.keep_whole_unit_copy",
            "decision_type": "keep_whole_unit_copy",
            "element_id": None,
            "reason": "this unit can be preserved by the initial source DOCX copy",
            "source_seq_refs": [1],
            "source_ref": "word/document.xml:p[1]",
            "unit_id": "cover",
        }
    ]
    assert any(
        action["action_type"] == "preserve_whole_unit_copy"
        and action["unit_id"] == "cover"
        and action["affected_source_seq_refs"] == [1]
        for action in plan["actions"]
    )
    assert not any(
        action["action_type"] == "preserve_whole_unit_copy"
        and action["unit_id"] == "references"
        for action in plan["actions"]
    )


def test_template_generate_copy_only_units_use_restricted_internal_element_analysis(
    tmp_path,
) -> None:
    source = tmp_path / "test_inputs/template_generation/school-template.docx"
    out_dir = tmp_path / "template_generate"
    write_source_docx(
        source,
        [
            "封面",
            "论文题目：____",
            "格式说明：小四宋体",
            "目录",
            "正文",
        ],
    )

    result = run_template_generate_eval(tmp_path, source, out_dir)
    generated = out_dir / "generated_template.docx"
    structure_candidates = read_json(out_dir / "artifacts/template_structure_candidates.json")
    generation_model = read_json(out_dir / "artifacts/template_generation_model.json")
    plan = read_json(out_dir / "artifacts/template_generation_plan.json")
    cover_candidate = next(
        unit for unit in structure_candidates["units"] if unit["unit_id"] == "cover"
    )
    cover_model = next(
        unit
        for unit in generation_model["units"]
        if unit["unit_id"] == "cover"
    )
    cover_strategy = next(
        unit for unit in generation_model["unit_strategies"] if unit["unit_id"] == "cover"
    )
    cover_elements = cover_candidate["elements"]
    cover_model_elements = cover_model["elements"]
    whole_copy = next(
        element
        for element in cover_elements
        if element.get("relationship") == "copy_region_candidate"
    )
    title_candidate = next(
        element
        for element in cover_elements
        if element.get("source_refs") == ["word/document.xml:p[2]"]
    )
    instruction_candidate = next(
        element
        for element in cover_elements
        if element.get("source_refs") == ["word/document.xml:p[3]"]
    )
    model_title = next(
        element
        for element in cover_model_elements
        if element.get("source_refs") == ["word/document.xml:p[2]"]
    )

    assert result.status == Status.PASS
    assert whole_copy["candidate_policy"] == "fixed"
    assert whole_copy["role_hint"] == "copy_region_candidate"
    assert title_candidate["role_hint"] == "student_field_candidate"
    assert title_candidate["candidate_policy"] == "fill"
    assert title_candidate["source_seq_refs"] == [2]
    assert model_title["candidate_policy"] == "fill"
    assert model_title["policy"] == "fixed"
    assert instruction_candidate["role_hint"] == "instruction_candidate"
    assert instruction_candidate["candidate_policy"] == "remove_instruction"
    assert instruction_candidate["source_seq_refs"] == [3]
    assert cover_strategy["generation_mode"] == "whole_unit_copy"
    assert any(
        decision["decision_type"] == "keep_whole_unit_copy"
        for decision in cover_strategy["decisions"]
    )
    assert any(
        decision["decision_type"] == "remove_instruction_text"
        and decision["source_ref"] == "word/document.xml:p[3]"
        and decision["source_seq_refs"] == [3]
        for decision in cover_strategy["decisions"]
    )
    assert not any(
        action.get("unit_id") == "cover"
        and action["action_type"] in {"create_fillable_slot", "create_generated_field_placeholder"}
        for action in plan["actions"]
    )
    assert any(
        action["action_type"] == "remove_instruction_text"
        and action.get("source_ref") == "word/document.xml:p[3]"
        and action["affected_source_seq_refs"] == [3]
        for action in plan["actions"]
    )
    assert "论文题目：____" in docx_texts(generated)
    assert "格式说明：小四宋体" not in docx_texts(generated)
    assert not any("[[DOCFIT_SLOT:cover." in text for text in docx_texts(generated))


def test_template_generate_references_unit_is_fillable_not_copy_only(tmp_path) -> None:
    source = tmp_path / "test_inputs/template_generation/school-template.docx"
    out_dir = tmp_path / "template_generate"
    write_source_docx(source, ["封面", "正文", "参考文献", "学生文献内容占位"])

    result = run_template_generate_eval(tmp_path, source, out_dir)
    generation_model = read_json(out_dir / "artifacts/template_generation_model.json")
    plan = read_json(out_dir / "artifacts/template_generation_plan.json")
    references = next(
        unit
        for unit in generation_model["unit_strategies"]
        if unit["unit_id"] == "references"
    )

    assert result.status == Status.PASS
    assert references["generation_mode"] == "copy_then_patch"
    assert any(
        action["action_type"] == "create_fillable_slot"
        and action["unit_id"] == "references"
        for action in plan["actions"]
    )
    assert any(
        "[[DOCFIT_SLOT:references." in text
        for text in docx_texts(out_dir / "generated_template.docx")
    )
