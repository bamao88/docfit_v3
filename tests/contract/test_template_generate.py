from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from docx import Document
from typer.testing import CliRunner

from docfit.cli.main import app
from docfit.convert.orchestrator import (
    _template_generation_project_dir,
    run_template_generate_eval,
)
from docfit.core.io import read_json, read_yaml, sha256_file
from docfit.core.status import Status
from docfit.template_generation.runner import BODY_SLOT_MARKER


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def write_source_docx(path: Path, paragraphs: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    doc.save(path)


def write_source_docx_with_runs(
    path: Path,
    paragraphs: list[str | list[tuple[str, dict[str, object]]]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    for paragraph_spec in paragraphs:
        if isinstance(paragraph_spec, str):
            doc.add_paragraph(paragraph_spec)
            continue
        paragraph = doc.add_paragraph()
        for text, attrs in paragraph_spec:
            run = paragraph.add_run(text)
            if "bold" in attrs:
                run.bold = bool(attrs["bold"])
            if "italic" in attrs:
                run.italic = bool(attrs["italic"])
            if "underline" in attrs:
                run.underline = bool(attrs["underline"])
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


def docx_sdt_tags(path: Path) -> set[str]:
    tags: set[str] = set()
    with ZipFile(path) as package:
        root = ET.fromstring(package.read("word/document.xml"))
    for tag in root.iter(f"{W_NS}tag"):
        value = tag.attrib.get(f"{W_NS}val")
        if value:
            tags.add(value)
    return tags


def test_template_generation_debug_root_follows_run_bundle(tmp_path) -> None:
    bundle_root = tmp_path / "test_outputs/debug/template_generation/run_001"

    assert _template_generation_project_dir(
        tmp_path,
        out_dir=bundle_root / "eval_runs/template_generate",
    ) == bundle_root / "human"
    assert _template_generation_project_dir(
        tmp_path,
        out_dir=bundle_root / "human/20260628T000000+0800",
    ) == bundle_root / "human"
    assert _template_generation_project_dir(
        tmp_path,
        out_dir=tmp_path / "adhoc_template_generate",
    ) == (tmp_path / "adhoc_template_generate" / "human").resolve()


def test_template_generate_writes_full_stage_artifact_chain(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template.docx"
    write_source_docx(source, ["学校固定封面", "目录", "正文开始", "格式说明：小四宋体"])

    bundle_root = (
        tmp_path
        / "test_outputs/debug/template_generation/20260621T160704467333+0800"
    )
    out_dir = (
        bundle_root
        / "eval_runs/template_generate"
    )
    result = run_template_generate_eval(tmp_path, source, out_dir)

    fillable = out_dir / "fillable_template.docx"
    artifacts = out_dir / "artifacts"
    manifest_path = artifacts / "build_manifest.json"
    plan_path = artifacts / "template_generation_plan.json"
    debug_root = bundle_root / "human"
    summary = read_json(out_dir / "summary.json")
    manifest = read_json(manifest_path)
    plan = read_json(plan_path)
    document_facts = read_json(artifacts / "document_facts.json")
    unit_map = read_yaml(artifacts / "unit_map.yaml")
    t2_code = read_yaml(artifacts / "t2_code_unit_map.yaml")
    t2_ai = read_yaml(artifacts / "t2_ai_unit_observation.yaml")
    t2_merged = read_yaml(artifacts / "t2_merged_unit_map.yaml")
    element_spec = read_yaml(artifacts / "element_spec.yaml")
    t3_code = read_yaml(artifacts / "t3_code_element_spec.yaml")
    t3_ai = read_yaml(artifacts / "t3_ai_element_observation.yaml")
    t3_merged = read_yaml(artifacts / "t3_merged_element_spec.yaml")
    global_spec = read_yaml(artifacts / "global_spec.yaml")
    t4_code = read_yaml(artifacts / "t4_code_global_spec.yaml")
    t4_ai = read_yaml(artifacts / "t4_ai_layout_observation.yaml")
    t4_merged = read_yaml(artifacts / "t4_merged_global_spec.yaml")
    template_spec = read_yaml(artifacts / "template_spec.yaml")
    verification_report = read_json(artifacts / "verification_report.json")
    source_tree = read_json(artifacts / "source_template_tree.json")
    structure_candidates = read_json(artifacts / "template_structure_candidates.json")
    t2_input = read_json(artifacts / "t2_input.json")
    generation_model = read_json(artifacts / "template_generation_model.json")
    debug_dirs = sorted(
        path for path in debug_root.iterdir() if path.is_dir() and path.name != "eval_runs"
    )
    debug_dir = debug_dirs[0]
    debug_index = read_json(debug_dir / "99_template_generation_debug_index.json")
    issue_clusters = read_json(out_dir / "issue_clusters.json")

    assert result.status == Status.UNKNOWN
    assert out_dir.parent.name == "eval_runs"
    assert fillable.exists()
    assert (artifacts / "template_generation_request.json").exists()
    assert document_facts["artifact_type"] == "document_facts"
    assert unit_map["artifact_type"] == "unit_map"
    assert t2_code["route"]["route_id"] == "code_raw"
    assert t2_code["route"]["availability"] == "AVAILABLE"
    assert t2_ai["artifact_type"] == "ai_unit_observation"
    assert t2_ai["route"]["route_id"] == "ai_raw"
    assert t2_ai["route"]["availability"] == "NOT_AVAILABLE"
    assert "abstain" not in t2_ai
    assert t2_ai["coverage"]["unknown_source_seq"] == []
    assert t2_ai["coverage"]["total"] == len(document_facts["body_flow"])
    assert t2_merged["artifact_type"] == "unit_map"
    assert t2_merged["route"]["route_id"] == "merged"
    assert t2_merged["route"]["availability"] == "AVAILABLE"
    assert element_spec["artifact_type"] == "element_spec"
    assert t3_code["route"]["route_id"] == "code_raw"
    assert t3_code["route"]["availability"] == "AVAILABLE"
    assert t3_ai["artifact_type"] == "ai_element_observation"
    assert t3_ai["route"]["route_id"] == "ai_raw"
    assert t3_ai["route"]["availability"] == "NOT_AVAILABLE"
    assert "abstain" not in t3_ai
    assert t3_ai["coverage"]["unknown_source_seq"] == []
    assert t3_ai["coverage"]["total"] == len(document_facts["body_flow"])
    assert t3_merged["artifact_type"] == "element_spec"
    assert t3_merged["route"]["route_id"] == "merged"
    assert t3_merged["route"]["availability"] == "AVAILABLE"
    assert global_spec["artifact_type"] == "global_spec"
    assert t4_code["route"]["route_id"] == "code_raw"
    assert t4_code["route"]["availability"] == "AVAILABLE"
    assert t4_ai["artifact_type"] == "ai_layout_observation"
    assert t4_ai["route"]["route_id"] == "ai_raw"
    assert t4_ai["route"]["availability"] == "NOT_AVAILABLE"
    assert "abstain" not in t4_ai
    assert t4_ai["coverage"]["unknown_source_seq"] == []
    assert t4_ai["coverage"]["total"] == len(document_facts["body_flow"])
    assert t4_merged["artifact_type"] == "global_spec"
    assert t4_merged["route"]["route_id"] == "merged"
    assert t4_merged["route"]["availability"] == "AVAILABLE"
    assert template_spec["artifact_type"] == "template_spec"
    assert manifest["artifact_type"] == "build_manifest"
    assert verification_report["status"] == Status.UNKNOWN.value
    assert verification_report["first_bad_stage"] == "T2"
    assert any(flag["type"] == "unit_confidence_needs_review" for flag in unit_map["flags"])
    # Element confidence is graded by final policy/evidence (not blanket medium):
    # unambiguous fixed/instruction/generated elements grade `high` and raise no
    # review flag; only genuinely-ambiguous elements stay medium/low and get one.
    assert all(
        element["confidence"] in {"high", "medium", "low"}
        for element in element_spec["elements"]
    )
    assert any(element["confidence"] == "high" for element in element_spec["elements"])
    assert all(
        flag["confidence"] in {"medium", "low"}
        for flag in element_spec["flags"]
        if flag["type"] == "element_confidence_needs_review"
    )
    assert global_spec["section_profiles"][0]["boundary"]["status"] == "detected"
    assert global_spec["section_profiles"][0]["page_numbering"]["display"]["status"] == (
        "no_page_field"
    )
    assert global_spec["page_numbering"]["status"] == "none"
    assert not any(flag["type"] == "page_numbering_unknown" for flag in global_spec["flags"])
    assert template_spec["review_flags"]
    assert any(
        finding["type"] == "t2_unit_confidence_needs_review"
        for finding in verification_report["findings"]
    )
    assert not any(
        finding["type"] == "t4_page_numbering_unknown"
        for finding in verification_report["findings"]
    )
    assert issue_clusters
    assert source_tree["artifact_type"] == "source_template_tree"
    assert structure_candidates["artifact_type"] == "template_structure_candidates"
    assert t2_input["artifact_type"] == "t2_input"
    assert generation_model["artifact_type"] == "template_generation_model"
    assert any(question["kind"] == "boundary" for question in unit_map["open_questions"])
    assert manifest_path.exists()
    assert plan_path.exists()
    source_seq_refs = [
        item["source_seq"] for item in document_facts["body_flow"]
    ]
    assert source_seq_refs == list(range(1, len(source_seq_refs) + 1))
    assert document_facts["indexes"]["by_source_seq"]["1"]["node_id"] == "body_0001"
    assert document_facts["runs"]
    assert all(run["raw_run_id"] and run["logical_run_id"] for run in document_facts["runs"])
    assert len(debug_dirs) == 1
    assert debug_dir.parent == debug_root
    assert not (tmp_path / "runs/template_generation").exists()
    assert summary["artifacts"]["template_generation_debug_dir"] == str(debug_dir)
    assert (out_dir / "00_input_source_template.docx").exists()
    assert (out_dir / "00_template_generation_request.json").exists()
    assert (out_dir / "01_document_facts.json").exists()
    assert (out_dir / "02.0_t2_code_unit_map.yaml").exists()
    assert (out_dir / "02_unit_map.yaml").exists()
    assert (out_dir / "02.1_t2_input.json").exists()
    assert (out_dir / "02.2_t2_ai_unit_observation.yaml").exists()
    assert (out_dir / "02.3_t2_merged_unit_map.yaml").exists()
    assert (out_dir / "03.0_t3_code_element_spec.yaml").exists()
    assert (out_dir / "03.1_t3_ai_element_observation.yaml").exists()
    assert (out_dir / "03.2_t3_merged_element_spec.yaml").exists()
    assert (out_dir / "03_element_spec.yaml").exists()
    assert (out_dir / "04.0_t4_code_global_spec.yaml").exists()
    assert (out_dir / "04.1_t4_ai_layout_observation.yaml").exists()
    assert (out_dir / "04.2_t4_merged_global_spec.yaml").exists()
    assert (out_dir / "04_global_spec.yaml").exists()
    assert (out_dir / "05_template_spec.yaml").exists()
    assert (out_dir / "06.0_copy_source_docx.docx").exists()
    assert (out_dir / "06.1_fillable_template.docx").exists()
    assert (out_dir / "06.2_build_manifest.json").exists()
    assert (out_dir / "07_verification_report.json").exists()
    assert (out_dir / "99_template_generation_debug_index.json").exists()
    assert (debug_dir / "00_input_source_template.docx").exists()
    assert (debug_dir / "00_template_generation_request.json").exists()
    assert (debug_dir / "01_document_facts.json").exists()
    assert (debug_dir / "02.0_t2_code_unit_map.yaml").exists()
    assert (debug_dir / "02_unit_map.yaml").exists()
    assert (debug_dir / "02.1_t2_input.json").exists()
    assert (debug_dir / "02.2_t2_ai_unit_observation.yaml").exists()
    assert (debug_dir / "02.3_t2_merged_unit_map.yaml").exists()
    assert (debug_dir / "03.0_t3_code_element_spec.yaml").exists()
    assert (debug_dir / "03.1_t3_ai_element_observation.yaml").exists()
    assert (debug_dir / "03.2_t3_merged_element_spec.yaml").exists()
    assert (debug_dir / "03_element_spec.yaml").exists()
    assert (debug_dir / "04.0_t4_code_global_spec.yaml").exists()
    assert (debug_dir / "04.1_t4_ai_layout_observation.yaml").exists()
    assert (debug_dir / "04.2_t4_merged_global_spec.yaml").exists()
    assert (debug_dir / "04_global_spec.yaml").exists()
    assert (debug_dir / "05_template_spec.yaml").exists()
    assert (debug_dir / "06.0_copy_source_docx.docx").exists()
    assert (debug_dir / "06.1_fillable_template.docx").exists()
    assert (debug_dir / "06.2_build_manifest.json").exists()
    assert (debug_dir / "07_verification_report.json").exists()
    assert summary["status"] == Status.UNKNOWN.value
    assert summary["unknown_findings"] > 0
    assert summary["artifacts"]["fillable_template_docx"] == str(fillable)
    assert "slot_body_start" in docx_sdt_tags(fillable)
    assert not any("[[DOCFIT_" in text for text in docx_texts(fillable))
    assert BODY_SLOT_MARKER not in docx_texts(debug_dir / "06.0_copy_source_docx.docx")
    assert "格式说明：小四宋体" in docx_texts(debug_dir / "06.0_copy_source_docx.docx")
    assert manifest["strategy"] == "source_copy_scaffold"
    assert manifest["debug_snapshot"]["dir"] == str(debug_dir)
    assert manifest["output"]["fillable_template_docx"] == str(fillable)
    assert manifest["output"]["fillable_template_docx_hash"] == sha256_file(fillable)
    assert {
        item["name"] for item in debug_index["files"]
    } >= {
        "00_input_source_template.docx",
        "06.0_copy_source_docx.docx",
        "06.1_fillable_template.docx",
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
    source = tmp_path / "inputs/targets/demo-school/raw/school-template-with-slot.docx"
    write_source_docx(source, ["学校固定封面", BODY_SLOT_MARKER])

    result = run_template_generate_eval(tmp_path, source, tmp_path / "template_generate")
    fillable = tmp_path / "template_generate/fillable_template.docx"
    manifest = read_json(
        tmp_path / "template_generate/artifacts/build_manifest.json"
    )

    assert result.status == Status.UNKNOWN
    assert BODY_SLOT_MARKER not in docx_texts(fillable)
    assert "slot_body_start" in docx_sdt_tags(fillable)
    assert any(
        action["action_type"] == "ensure_body_slot"
        for action in manifest["actions_executed"]
    )
    assert any(slot["slot_id"] == "slot_body_start" for slot in manifest["slots"])


def test_template_generate_cleans_instruction_text_inside_table_cells(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template-table.docx"
    source.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_paragraph("摘要")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "学生姓名：×××"
    table.cell(0, 1).text = "格式说明：此处用小四宋体"
    doc.add_paragraph("正文")
    doc.save(source)

    result = run_template_generate_eval(tmp_path, source, tmp_path / "template_generate")
    fillable = tmp_path / "template_generate/fillable_template.docx"
    manifest = read_json(
        tmp_path / "template_generate/artifacts/build_manifest.json"
    )

    assert result.status == Status.UNKNOWN
    assert not manifest["actions_requiring_review"]
    assert not any("格式说明" in text for text in table_texts(fillable))
    assert any(tag != "slot_body_start" for tag in docx_sdt_tags(fillable))


def test_template_generate_removes_form_usage_notes_but_keeps_manual_fields(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template-form-notes.docx"
    out_dir = tmp_path / "template_generate"
    notes = [
        "一、毕业设计任务书是学校根据已经确定的毕业设计题目下达给学生的一种教学文件，是学生在指导教师指导下独立从事毕业设计工作的依据。此表由指导教师填写。",
        "四、任务书一经下达，不得随意更改。",
        "请在合适的对应选项前的“□”内打“√”，科研课题请注明课题项目和名称，项目指“国家青年基金”等。",
        "六、本表可从毕业论文管理系统填写打印或教务处网站下载中心下载填写打印，但签名栏必须相应责任人亲笔签名，且应用黑色签字笔填写。",
        "注：此表如不够填写，可另加附页。",
        "注：此表可从毕业论文管理系统或教务处网站下载中心下载。记录、签名栏必须用黑色笔手工填写。",
    ]
    write_source_docx(
        source,
        [
            "毕业设计任务书",
            *notes,
            "指导教师签名：",
            "评阅教师意见：",
            "正文",
        ],
    )

    result = run_template_generate_eval(tmp_path, source, out_dir)
    fillable = out_dir / "fillable_template.docx"
    plan = read_json(out_dir / "artifacts/template_generation_plan.json")
    output_text = "\n".join(docx_texts(fillable))

    assert result.status == Status.UNKNOWN
    for note in notes:
        assert note not in output_text
    assert "指导教师签名：" in output_text
    assert "评阅教师意见：" in output_text
    assert sum(
        action["action_type"] == "remove_instruction_text"
        for action in plan["actions"]
    ) >= len(notes)


def test_template_generate_merges_table_label_value_candidates(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template-table-label.docx"
    source.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_paragraph("摘要")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "学生姓名："
    table.cell(0, 1).text = "____"
    doc.add_paragraph("正文")
    doc.save(source)

    result = run_template_generate_eval(tmp_path, source, tmp_path / "template_generate")
    structure_candidates = read_json(
        tmp_path / "template_generate/artifacts/template_structure_candidates.json"
    )
    merged = next(
        element
        for unit in structure_candidates["units"]
        for element in unit["elements"]
        if element.get("source_refs")
        == [
            "word/document.xml:tbl[1]/tr[1]/tc[1]",
            "word/document.xml:tbl[1]/tr[1]/tc[2]",
        ]
    )

    assert result.status == Status.UNKNOWN
    assert merged["candidate_policy"] == "fill"
    assert merged["role_hint"] == "student_field_candidate"
    assert len(merged["source_seq_refs"]) == 2
    assert len(merged["entry_refs"]) == 2
    assert merged["merge"]["type"] == "table_row_label_value"
    assert merged["merge"]["merged_source_seq_refs"] == merged["source_seq_refs"]


def test_template_generate_merges_business_sentence_continuation(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template-continuation.docx"
    out_dir = tmp_path / "template_generate"
    write_source_docx(
        source,
        [
            "摘要",
            "摘要正文：本研究围绕生成流程，",
            "重点讨论阶段证据链。",
            "正文",
        ],
    )

    result = run_template_generate_eval(tmp_path, source, out_dir)
    structure_candidates = read_json(out_dir / "artifacts/template_structure_candidates.json")
    abstract = next(
        unit for unit in structure_candidates["units"] if unit["unit_id"] == "abstract_cn"
    )
    merged = next(
        element
        for element in abstract["elements"]
        if element.get("source_refs")
        == ["word/document.xml:p[2]", "word/document.xml:p[3]"]
    )

    assert result.status == Status.UNKNOWN
    assert merged["candidate_policy"] == "fill"
    assert merged["role_hint"] == "student_field_candidate"
    assert merged["source_seq_refs"] == [2, 3]
    assert merged["entry_refs"] == ["body_0002", "body_0003"]
    assert merged["merge"]["type"] == "business_sentence_continuation"
    assert merged["merge"]["merged_source_seq_refs"] == [2, 3]


def test_template_generate_invalid_docx_fails_without_output(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/not-a-docx.docx"
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
    source = tmp_path / "inputs/targets/demo-school/raw/school-template.docx"
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
    assert "status = UNKNOWN" in result.stdout
    assert (out_dir / "fillable_template.docx").exists()
    assert (out_dir / "artifacts/build_manifest.json").exists()
    assert (out_dir / "artifacts/template_spec.yaml").exists()
    assert (out_dir / "summary.json").exists()


def test_template_generate_cli_rejects_school_standard_input(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template.docx"
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


def test_template_generate_disables_whole_unit_copy_by_default(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template.docx"
    out_dir = tmp_path / "template_generate"
    write_source_docx(source, ["封面", "参考文献"])

    result = run_template_generate_eval(tmp_path, source, out_dir)
    generation_model = read_json(out_dir / "artifacts/template_generation_model.json")
    plan = read_json(out_dir / "artifacts/template_generation_plan.json")
    cover = next(
        unit for unit in generation_model["unit_strategies"] if unit["unit_id"] == "cover"
    )

    assert result.status == Status.UNKNOWN
    assert cover["generation_mode"] == "copy_then_patch"
    assert cover["generation_policy"] == "unit_actions"
    references = next(
        unit
        for unit in generation_model["unit_strategies"]
        if unit["unit_id"] == "references"
    )
    assert references["generation_mode"] == "copy_then_patch"
    assert references["generation_policy"] == "unit_actions"
    assert not any(
        action["action_type"] == "preserve_whole_unit_copy"
        for action in plan["actions"]
    )


def test_template_generate_custom_units_are_not_copy_only_by_default(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template.docx"
    out_dir = tmp_path / "template_generate"
    source.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_paragraph("封面")
    doc.add_paragraph("研究方案设计", style="Heading 1")
    doc.add_paragraph("论文题目：____")
    doc.add_paragraph("正文", style="Heading 1")
    doc.save(source)

    result = run_template_generate_eval(tmp_path, source, out_dir)
    generation_model = read_json(out_dir / "artifacts/template_generation_model.json")
    plan = read_json(out_dir / "artifacts/template_generation_plan.json")
    custom_strategy = next(
        unit
        for unit in generation_model["unit_strategies"]
        if str(unit["unit_id"]).startswith("custom:template:")
    )

    assert result.status == Status.UNKNOWN
    assert custom_strategy["generation_mode"] == "copy_then_patch"
    assert custom_strategy["generation_policy"] == "unit_actions"
    assert not any(
        action["action_type"] == "preserve_whole_unit_copy"
        and action["unit_id"] == custom_strategy["unit_id"]
        for action in plan["actions"]
    )
    assert any(
        action["action_type"] == "create_fillable_slot"
        and action["unit_id"] == custom_strategy["unit_id"]
        for action in plan["actions"]
    )


def test_template_generate_cover_uses_patch_analysis_when_copy_only_disabled(
    tmp_path,
) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template.docx"
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
    fillable = out_dir / "fillable_template.docx"
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

    assert result.status == Status.UNKNOWN
    assert not any(
        element.get("relationship") == "copy_region_candidate"
        for element in cover_elements
    )
    assert title_candidate["role_hint"] == "student_field_candidate"
    assert title_candidate["candidate_policy"] == "fill"
    assert title_candidate["source_seq_refs"] == [2]
    assert model_title["candidate_policy"] == "fill"
    assert model_title["policy"] == "fill"
    assert instruction_candidate["role_hint"] == "instruction_candidate"
    assert instruction_candidate["candidate_policy"] == "remove_instruction"
    assert instruction_candidate["source_seq_refs"] == [3]
    assert cover_strategy["generation_mode"] == "copy_then_patch"
    assert not any(
        decision["decision_type"] == "keep_whole_unit_copy"
        for decision in cover_strategy["decisions"]
    )
    assert any(
        decision["decision_type"] == "remove_instruction_text"
        and decision["source_ref"] == "word/document.xml:p[3]"
        and decision["source_seq_refs"] == [3]
        for decision in cover_strategy["decisions"]
    )
    assert any(
        action.get("unit_id") == "cover"
        and action["action_type"] == "create_fillable_slot"
        and action["affected_source_seq_refs"] == [2]
        for action in plan["actions"]
    )
    assert any(
        action["action_type"] == "remove_instruction_text"
        and action.get("source_ref") == "word/document.xml:p[3]"
        and action["affected_source_seq_refs"] == [3]
        for action in plan["actions"]
    )
    assert "格式说明：小四宋体" not in docx_texts(fillable)
    assert any(tag.startswith("cover.") for tag in docx_sdt_tags(fillable))


def test_template_generate_splits_within_paragraph_format_instruction_runs(
    tmp_path,
) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template.docx"
    out_dir = tmp_path / "template_generate"
    write_source_docx_with_runs(
        source,
        [
            "封面",
            [
                ("毕业论文（设计）中文题目  ", {"bold": False}),
                ("（小二黑体加粗）", {"bold": True}),
            ],
            "目录",
            "正文",
            [
                ("这是", {"bold": False}),
                ("普通", {"bold": True}),
                ("正文段落", {"bold": False}),
            ],
        ],
    )

    result = run_template_generate_eval(tmp_path, source, out_dir)
    fillable = out_dir / "fillable_template.docx"
    structure_candidates = read_json(out_dir / "artifacts/template_structure_candidates.json")
    generation_model = read_json(out_dir / "artifacts/template_generation_model.json")
    element_spec = read_yaml(out_dir / "artifacts/element_spec.yaml")
    plan = read_json(out_dir / "artifacts/template_generation_plan.json")
    manifest = read_json(out_dir / "artifacts/build_manifest.json")

    cover_candidate = next(
        unit for unit in structure_candidates["units"] if unit["unit_id"] == "cover"
    )
    cover_model = next(
        unit for unit in generation_model["units"] if unit["unit_id"] == "cover"
    )
    cover_elements = [
        element
        for element in cover_candidate["elements"]
        if element.get("source_refs") == ["word/document.xml:p[2]"]
    ]
    model_cover_elements = [
        element
        for element in cover_model["elements"]
        if element.get("source_refs") == ["word/document.xml:p[2]"]
    ]
    instruction_candidate = next(
        element
        for element in cover_elements
        if element.get("candidate_policy") == "remove_instruction"
    )
    content_candidate = next(
        element
        for element in cover_elements
        if element.get("candidate_policy") in {"fixed", "fill"}
    )
    instruction_spec = next(
        element
        for element in element_spec["elements"]
        if element["unit_id"] == "cover"
        and element["element_id"] == instruction_candidate["element_id"]
    )
    instruction_action = next(
        action
        for action in plan["actions"]
        if action["action_type"] == "remove_instruction_text"
        and action.get("unit_id") == "cover"
        and action.get("element_id") == instruction_candidate["element_id"]
    )
    executed_instruction = next(
        action
        for action in manifest["actions_executed"]
        if action["action_type"] == "remove_instruction_text"
        and action.get("unit_id") == "cover"
        and action.get("element_id") == instruction_candidate["element_id"]
    )
    body_main = next(
        unit for unit in structure_candidates["units"] if unit["unit_id"] == "body_main"
    )
    body_paragraph_elements = [
        element
        for element in body_main["elements"]
        if element.get("source_refs") == ["word/document.xml:p[5]"]
    ]

    assert result.status == Status.UNKNOWN
    assert len(cover_elements) >= 2
    assert len(model_cover_elements) >= 2
    assert content_candidate["source_seq_refs"] == [2]
    assert instruction_candidate["source_seq_refs"] == [2]
    assert content_candidate["raw_run_ids"]
    assert instruction_candidate["raw_run_ids"]
    assert set(content_candidate["raw_run_ids"]).isdisjoint(
        set(instruction_candidate["raw_run_ids"])
    )
    assert instruction_candidate["logical_run_ids"]
    assert instruction_spec["policy"] == "instruction_remove"
    assert instruction_spec["raw_run_ids"] == instruction_candidate["raw_run_ids"]
    assert instruction_action["affected_source_seq_refs"] == [2]
    assert instruction_action["affected_raw_run_ids"] == instruction_candidate["raw_run_ids"]
    assert instruction_action["affected_logical_run_ids"] == instruction_candidate["logical_run_ids"]
    assert executed_instruction["affected_raw_run_ids"] == instruction_candidate["raw_run_ids"]
    assert any("毕业论文（设计）中文题目" in text for text in docx_texts(fillable))
    assert not any("小二黑体加粗" in text for text in docx_texts(fillable))
    assert len(body_paragraph_elements) == 1


def test_template_generate_replaces_field_line_placeholder_spans(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template.docx"
    out_dir = tmp_path / "template_generate"
    write_source_docx_with_runs(
        source,
        [
            "封面",
            [
                ("□□□□□□", {"bold": True}),
                ("学□□号：", {"bold": True}),
                ("20××××××××××", {"bold": True}),
            ],
            "目录",
            "正文",
        ],
    )

    result = run_template_generate_eval(tmp_path, source, out_dir)
    fillable = out_dir / "fillable_template.docx"
    element_spec = read_yaml(out_dir / "artifacts/element_spec.yaml")
    plan = read_json(out_dir / "artifacts/template_generation_plan.json")
    manifest = read_json(out_dir / "artifacts/build_manifest.json")
    cover_field = next(
        element
        for element in element_spec["elements"]
        if element["unit_id"] == "cover"
        and "学□□号" in element.get("content", "")
    )

    span_types = {span["span_type"] for span in cover_field["spans"]}
    assert result.status == Status.UNKNOWN
    assert {"label", "layout_spacer", "sample_value"}.issubset(span_types)
    assert any(
        action["action_type"] == "replace_span_with_slot"
        and action["unit_id"] == "cover"
        and action["element_id"] == cover_field["element_id"]
        for action in plan["actions"]
    )
    assert any(
        action["action_type"] == "replace_span_with_slot"
        for action in manifest["actions_executed"]
    )
    joined_text = "\n".join(docx_texts(fillable))
    assert "□□□□□□" not in joined_text
    assert "学□□号" not in joined_text
    assert "20××" not in joined_text
    assert "学号：" in joined_text
    assert any(tag.startswith("cover.") for tag in docx_sdt_tags(fillable))


def test_template_generate_references_unit_is_fillable_not_copy_only(tmp_path) -> None:
    source = tmp_path / "inputs/targets/demo-school/raw/school-template.docx"
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

    assert result.status == Status.UNKNOWN
    assert references["generation_mode"] == "copy_then_patch"
    assert any(
        action["action_type"] == "create_fillable_slot"
        and action["unit_id"] == "references"
        for action in plan["actions"]
    )
    assert any(tag.startswith("references.") for tag in docx_sdt_tags(out_dir / "fillable_template.docx"))
