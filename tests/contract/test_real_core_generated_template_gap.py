from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from docfit.convert.orchestrator import run_template_gap_eval
from docfit.core.io import read_json, sha256_file
from docfit.core.status import Status
from docfit.harness.generated_template_gap import summarize_template_gap_report
from docfit.harness.profiles import REAL_CORE_PROFILE, REAL_CORE_SCHOOLS


ROOT = Path.cwd()


def unit_by_id(report: dict, unit_id: str) -> dict:
    return next(unit for unit in report["units"] if unit["unit_id"] == unit_id)


def element_by_id(unit: dict, element_id: str) -> dict:
    return next(element for element in unit["elements"] if element["element_id"] == element_id)


def collect_checks(
    report: dict,
    *,
    type: str | None = None,
    category: str | None = None,
    status: str | None = None,
) -> list[dict]:
    checks: list[dict] = []
    if isinstance(report.get("input"), dict):
        checks.append(report["input"])
    checks.extend(report.get("global_checks", []))
    for unit in report.get("units", []):
        if isinstance(unit.get("presence"), dict):
            checks.append(unit["presence"])
        for element in unit.get("elements", []):
            for key in ("presence", "style"):
                if isinstance(element.get(key), dict):
                    checks.append(element[key])
        for dimension_checks in unit.get("dimensions", {}).values():
            checks.extend(dimension_checks)
    checks.extend(report.get("unmodeled_objects", []))
    if type is not None:
        checks = [check for check in checks if check.get("type") == type]
    if category is not None:
        checks = [check for check in checks if check.get("category") == category]
    if status is not None:
        checks = [check for check in checks if check.get("status") == status]
    return checks


def write_minimal_gap_standard(
    root: Path,
    school_id: str,
    expected_units: list[dict],
) -> None:
    school_dir = root / "standards/schools" / school_id / "v1"
    school_dir.mkdir(parents=True)
    required = list(REAL_CORE_PROFILE.all_required_capabilities())
    signed_standard = {
        "standard_id": f"{school_id}-v1",
        "school_id": school_id,
        "template_version": "v1",
        "status": "test_fixture",
        "owner": "docfit-tests",
        "source": {
            "template_docx": "inputs/minimal-template.docx",
            "template_docx_sha256": "sha256:test",
        },
        "contracts": {
            "template_contract": "template_contract.json",
            "student_content_contract": "student_content_contract.json",
            "placement_contract": "placement_contract.json",
            "render_contract": "render_contract.json",
        },
        "evidence_baselines": {
            "template_unit_contract": "template_unit_contract.yaml",
        },
        "coverage_requirements": {
            "profile": REAL_CORE_PROFILE.profile_id,
            "required_capabilities": required,
        },
    }
    (school_dir / "signed_standard.yaml").write_text(
        _simple_yaml(signed_standard),
        encoding="utf-8",
    )
    contract = {
        "contract_type": "test",
        "contract_version": "1.0",
        "owner": "docfit-tests",
        "required_invariants": [],
        "required_capabilities": [],
        "unsupported_policy": {},
        "coverage_requirements": {},
        "verifier_refs": [],
    }
    for name in signed_standard["contracts"].values():
        (school_dir / name).write_text(json.dumps(contract), encoding="utf-8")
    baseline = {
        "baseline_type": "template_unit_contract",
        "profile_id": "test",
        "school_id": school_id,
        "review_metadata": {
            "reviewed_by": "test",
            "review_source": "tests",
            "source_docx_sha256": "sha256:test",
            "change_reason": "test fixture",
            "auto_update_allowed": False,
        },
        "dimensions": [
            {"dimension_id": "expected.units", "comparator_mode": "exact"},
        ],
        "expected": {"units": expected_units},
    }
    (school_dir / "template_unit_contract.yaml").write_text(
        _simple_yaml(baseline),
        encoding="utf-8",
    )


def write_docx(path: Path, paragraphs: list[dict | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    for item in paragraphs:
        if isinstance(item, str):
            doc.add_paragraph(item)
            continue
        paragraph = doc.add_paragraph()
        run = paragraph.add_run(str(item["text"]))
        if item.get("font"):
            run.font.name = str(item["font"])
        if item.get("size"):
            run.font.size = Pt(float(item["size"]))
        if "bold" in item:
            run.bold = bool(item["bold"])
        if item.get("alignment") == "center":
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.save(path)


def _simple_yaml(value, indent: int = 0) -> str:
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(" " * indent + f"{key}:")
                lines.append(_simple_yaml(item, indent + 2).rstrip())
            else:
                lines.append(" " * indent + f"{key}: {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines) + "\n"
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(" " * indent + "-")
                lines.append(_simple_yaml(item, indent + 2).rstrip())
            else:
                lines.append(" " * indent + f"- {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines) + "\n"
    return " " * indent + json.dumps(value, ensure_ascii=False) + "\n"


def minimal_expected_units(*, style: str = "") -> list[dict]:
    return [
        {
            "unit_id": "cover",
            "name": "封面",
            "order": 10,
            "status": "required",
            "elements": [
                {
                    "element_id": "e_001",
                    "name": "学校名称",
                    "policy": "fixed",
                    "content": "测试大学",
                    "style": style,
                },
                {
                    "element_id": "e_002",
                    "name": "学生姓名",
                    "policy": "manual_only",
                    "content": "学生姓名：",
                    "style": "",
                },
            ],
        },
        {
            "unit_id": "body",
            "name": "正文",
            "order": 20,
            "status": "required",
            "elements": [
                {
                    "element_id": "e_001",
                    "name": "正文标题",
                    "policy": "fixed",
                    "content": "第一章 绪论",
                    "style": "",
                }
            ],
        },
    ]


def test_template_gap_minimal_fixture_can_pass_cleanly(tmp_path) -> None:
    school_id = "minimal-school"
    write_minimal_gap_standard(tmp_path, school_id, minimal_expected_units())
    generated_template = tmp_path / "inputs/generated_template.docx"
    write_docx(
        generated_template,
        ["测试大学", "学生姓名：", "第一章 绪论"],
    )

    result = run_template_gap_eval(
        tmp_path,
        school_id,
        generated_template,
        tmp_path / "minimal_gap",
    )
    report = read_json(tmp_path / "minimal_gap/artifacts/template_gap_report.json")

    assert result.status == Status.PASS
    assert report["artifact_version"] == "2.0"
    assert "check_items" not in report
    assert report["summary"]["blocking_status"] == Status.PASS.value
    assert report["summary"]["failed_count"] == 0
    assert report["summary"]["unknown_count"] == 0
    assert unit_by_id(report, "cover")["verdict"] == Status.PASS.value


def test_template_gap_single_style_mutation_fails_only_that_element(tmp_path) -> None:
    school_id = "style-school"
    expected = minimal_expected_units(style="宋体；12pt；加粗；居中。")
    write_minimal_gap_standard(tmp_path, school_id, expected)
    generated_template = tmp_path / "inputs/generated_template.docx"
    write_docx(
        generated_template,
        [
            {"text": "测试大学", "font": "宋体", "size": 14, "bold": True, "alignment": "center"},
            "学生姓名：",
            "第一章 绪论",
        ],
    )

    result = run_template_gap_eval(
        tmp_path,
        school_id,
        generated_template,
        tmp_path / "style_gap",
    )
    report = read_json(tmp_path / "style_gap/artifacts/template_gap_report.json")
    mismatches = collect_checks(
        report,
        type="template_generation_style_mismatch",
    )

    assert result.status == Status.FAIL
    assert len(mismatches) == 1
    assert mismatches[0]["path"] == ["units", "cover", "elements", "e_001", "style"]
    assert "font_size expected 12pt" in mismatches[0]["actual"]


def test_template_gap_missing_required_element_is_presence_fail(tmp_path) -> None:
    school_id = "missing-element-school"
    write_minimal_gap_standard(tmp_path, school_id, minimal_expected_units())
    generated_template = tmp_path / "inputs/generated_template.docx"
    write_docx(generated_template, ["测试大学", "第一章 绪论"])

    result = run_template_gap_eval(
        tmp_path,
        school_id,
        generated_template,
        tmp_path / "missing_element_gap",
    )
    report = read_json(tmp_path / "missing_element_gap/artifacts/template_gap_report.json")
    cover = unit_by_id(report, "cover")
    missing = element_by_id(cover, "e_002")["presence"]

    assert result.status == Status.FAIL
    assert missing["status"] == Status.FAIL.value
    assert missing["type"] == "template_generation_element_missing"
    assert missing["path"] == ["units", "cover", "elements", "e_002", "presence"]


def test_template_gap_unsearchable_fixed_element_is_unknown_not_fail(tmp_path) -> None:
    school_id = "unsearchable-school"
    expected = [
        {
            "unit_id": "cover",
            "name": "封面",
            "order": 10,
            "status": "required",
            "elements": [
                {
                    "element_id": "e_001",
                    "name": "学校名称",
                    "policy": "fixed",
                    "content": "测试大学",
                    "style": "",
                },
                {
                    "element_id": "e_002",
                    "name": "内容",
                    "policy": "fixed",
                    "content": "正文内容",
                    "style": "",
                },
            ],
        }
    ]
    write_minimal_gap_standard(tmp_path, school_id, expected)
    generated_template = tmp_path / "inputs/generated_template.docx"
    write_docx(generated_template, ["测试大学"])

    result = run_template_gap_eval(
        tmp_path,
        school_id,
        generated_template,
        tmp_path / "unsearchable_gap",
    )
    report = read_json(tmp_path / "unsearchable_gap/artifacts/template_gap_report.json")
    uncheckable = collect_checks(
        report,
        type="template_generation_element_uncheckable",
    )

    assert result.status == Status.UNKNOWN
    assert len(uncheckable) == 1
    assert uncheckable[0]["status"] == Status.UNKNOWN.value


def test_template_gap_normalizes_template_noise(tmp_path) -> None:
    school_id = "noise-school"
    expected = [
        {
            "unit_id": "toc",
            "name": "目录",
            "order": 10,
            "status": "required",
            "elements": [
                {
                    "element_id": "e_001",
                    "name": "目录标签",
                    "policy": "fixed",
                    "content": "目 录",
                    "style": "",
                },
                {
                    "element_id": "e_002",
                    "name": "学生信息",
                    "policy": "manual_only",
                    "content": "学生姓名：；学号：；年级专业及班级：",
                    "style": "",
                },
            ],
        }
    ]
    write_minimal_gap_standard(tmp_path, school_id, expected)
    generated_template = tmp_path / "inputs/generated_template.docx"
    write_docx(
        generated_template,
        [
            "目□□录   (二号黑体，居中)",
            "□□□□□□学生姓名（三号黑体加粗）：×××；学号：×××；年级专业及班级：×××",
        ],
    )

    result = run_template_gap_eval(
        tmp_path,
        school_id,
        generated_template,
        tmp_path / "noise_gap",
    )
    report = read_json(tmp_path / "noise_gap/artifacts/template_gap_report.json")

    assert result.status == Status.PASS
    assert not collect_checks(report, type="template_generation_element_missing")


def test_template_gap_matches_repeated_text_inside_unit_range(tmp_path) -> None:
    school_id = "range-school"
    expected = [
        {
            "unit_id": "first",
            "name": "第一单元",
            "order": 10,
            "status": "required",
            "elements": [
                {"element_id": "e_001", "name": "第一锚点", "policy": "fixed", "content": "第一单元", "style": ""},
                {"element_id": "e_002", "name": "重复标签", "policy": "fixed", "content": "重复标签", "style": ""},
            ],
        },
        {
            "unit_id": "second",
            "name": "第二单元",
            "order": 20,
            "status": "required",
            "elements": [
                {"element_id": "e_001", "name": "第二锚点", "policy": "fixed", "content": "第二单元", "style": ""},
                {"element_id": "e_002", "name": "重复标签", "policy": "fixed", "content": "重复标签", "style": ""},
            ],
        },
    ]
    write_minimal_gap_standard(tmp_path, school_id, expected)
    generated_template = tmp_path / "inputs/generated_template.docx"
    write_docx(
        generated_template,
        ["第一单元", "重复标签", "第二单元", "重复标签"],
    )

    result = run_template_gap_eval(
        tmp_path,
        school_id,
        generated_template,
        tmp_path / "range_gap",
    )
    report = read_json(tmp_path / "range_gap/artifacts/template_gap_report.json")
    first_repeat = element_by_id(unit_by_id(report, "first"), "e_002")["presence"]
    second_repeat = element_by_id(unit_by_id(report, "second"), "e_002")["presence"]

    assert result.status == Status.PASS
    assert first_repeat["evidence_refs"] == ["word/document.xml:p[2]"]
    assert second_repeat["evidence_refs"] == ["word/document.xml:p[4]"]


def test_real_core_template_gap_outputs_tree_and_reports_for_all_schools(
    tmp_path,
) -> None:
    for school in REAL_CORE_SCHOOLS:
        school_id = str(school["school_id"])
        out_dir = tmp_path / school_id

        result = run_template_gap_eval(
            ROOT,
            school_id,
            ROOT / school["generated_template_docx"],
            out_dir,
        )

        artifacts = out_dir / "artifacts"
        generated_template = artifacts / "generated_template.docx"
        tree_path = artifacts / "generated_template_tree.json"
        report_json = artifacts / "template_gap_report.json"
        report_md = artifacts / "template_gap_report.md"
        report_docx = artifacts / "template_gap_report.docx"

        assert result.status in {Status.PASS, Status.FAIL, Status.UNKNOWN}
        assert generated_template.exists()
        assert tree_path.exists()
        assert report_json.exists()
        assert report_md.exists()
        assert report_docx.exists()

        tree = read_json(tree_path)
        report = read_json(report_json)
        assert tree["input_valid_docx"] is True
        assert tree["data"]["paragraphs"] or tree["data"]["tables"]
        assert report["generated_template"]["sha256"] == sha256_file(generated_template)
        assert {
            "known_status",
            "display_status",
            "passed_count",
            "failed_count",
            "unknown_count",
            "blocking_status",
            "per_unit",
        } <= set(report["summary"])
        assert report["generated_template"]["source_path"] == str(
            ROOT / school["generated_template_docx"]
        )
        assert "inputs/school-" not in report["generated_template"]["source_path"]
        assert "check_items" not in report
        assert collect_checks(report)
        assert any(
            item["check_id"] == "template_generation.output_docx"
            for item in collect_checks(report)
        )


def test_generated_template_gap_bad_docx_does_not_pass(tmp_path) -> None:
    bad_docx = tmp_path / "bad_generated_template.docx"
    doc = Document()
    doc.add_paragraph("这不是湖南农业大学模板。")
    doc.save(bad_docx)

    result = run_template_gap_eval(
        ROOT,
        "hunannongye",
        bad_docx,
        tmp_path / "bad_gap",
    )
    report = read_json(tmp_path / "bad_gap/artifacts/template_gap_report.json")

    assert result.status == Status.FAIL
    assert report["summary"]["blocking_status"] == Status.FAIL.value
    assert report["summary"]["failed_count"] > 0
    assert any(
        item["type"] == "template_generation_unit_missing"
        for item in collect_checks(report)
    )


def test_generated_template_gap_reports_ooxml_style_details(tmp_path) -> None:
    result = run_template_gap_eval(
        ROOT,
        "hunannongye",
        ROOT / "inputs/school-hunannongye-requirement.docx",
        tmp_path / "style_gap",
    )
    tree = read_json(tmp_path / "style_gap/artifacts/generated_template_tree.json")
    report = read_json(tmp_path / "style_gap/artifacts/template_gap_report.json")

    assert result.status == Status.FAIL
    paragraph = next(
        item
        for item in tree["data"]["paragraphs"]
        if item["text"].startswith("湖 南 农 业 大 学")
    )
    assert paragraph["style_details"]["dominant_run"]["font_names"] == ["华文行楷"]
    assert paragraph["style_details"]["dominant_run"]["font_size_pt"] == 26.0
    assert paragraph["style_details"]["paragraph"]["alignment"] == "center"

    style_mismatches = [
        item
        for item in collect_checks(report)
        if item["type"] == "template_generation_style_mismatch"
    ]
    assert style_mismatches
    assert any("font_size=" in item["actual"] for item in style_mismatches)


def test_generated_template_gap_resolves_ooxml_style_inheritance(tmp_path) -> None:
    result = run_template_gap_eval(
        ROOT,
        "nannong-undergraduate",
        ROOT / "inputs/school-nannong-undergraduate-template.docx",
        tmp_path / "style_inheritance_gap",
    )
    tree = read_json(
        tmp_path / "style_inheritance_gap/artifacts/generated_template_tree.json"
    )
    report = read_json(
        tmp_path / "style_inheritance_gap/artifacts/template_gap_report.json"
    )

    assert result.status == Status.FAIL
    signature_line = next(
        item
        for item in tree["data"]["paragraphs"]
        if item["text"].startswith("论文作者签名：")
    )
    assert signature_line["style_details"]["paragraph"]["spacing"][
        "line_spacing"
    ] == "exact:35pt"
    assert signature_line["style_details"]["style_inheritance"]["source_refs"] == [
        "word/styles.xml:style[a]"
    ]
    assert any(
        item["type"] == "template_generation_style_mismatch"
        and "line_spacing expected exact:20pt, actual exact:35pt" in item["actual"]
        for item in collect_checks(report)
    )


def test_generated_template_gap_binds_page_rules_to_ooxml_sources(tmp_path) -> None:
    result = run_template_gap_eval(
        ROOT,
        "hunannongye",
        ROOT / "inputs/school-hunannongye-requirement.docx",
        tmp_path / "page_gap",
    )
    report = read_json(tmp_path / "page_gap/artifacts/template_gap_report.json")

    assert result.status == Status.FAIL
    page_items = [
        item
        for item in collect_checks(report)
        if item["category"] == "page_rule"
    ]
    assert any(
        item["type"] == "template_generation_page_rule_match"
        and item["affected_ids"] == ["cover.page.page_break"]
        and "word/document.xml:p[" in item["evidence_refs"][0]
        for item in page_items
    )
    assert any(
        item["type"] == "template_generation_page_rule_mismatch"
        and item["affected_ids"] == ["integrity_statement.page.page_break"]
        and "no explicit page/section break" in item["actual"]
        for item in page_items
    )


def test_generated_template_gap_binds_keep_together_to_table_sources(tmp_path) -> None:
    result = run_template_gap_eval(
        ROOT,
        "nannong-undergraduate",
        ROOT / "inputs/school-nannong-undergraduate-template.docx",
        tmp_path / "table_keep_gap",
    )
    tree = read_json(tmp_path / "table_keep_gap/artifacts/generated_template_tree.json")
    report = read_json(tmp_path / "table_keep_gap/artifacts/template_gap_report.json")

    assert result.status == Status.FAIL
    cover_table = tree["data"]["tables"][0]
    assert cover_table["first_paragraph_index"] == 1
    assert cover_table["last_paragraph_index"] == 21
    assert cover_table["cant_split_row_refs"] == [
        "word/document.xml:tbl[1]/tr[1]/cantSplit"
    ]
    assert cover_table["cells"][0]["first_paragraph_index"] == 1

    assert any(
        item["type"] == "template_generation_element_found"
        and item["affected_ids"] == ["cover.e_001"]
        and item["evidence_refs"][0] == "word/document.xml:tbl[1]/tr[1]/tc[1]"
        for item in collect_checks(report)
    )
    assert any(
        item["type"] == "template_generation_page_rule_match"
        and item["affected_ids"] == ["cover.page.keep_together"]
        and item["evidence_refs"] == ["word/document.xml:tbl[1]/tr[1]/cantSplit"]
        for item in collect_checks(report)
    )


def test_generated_template_gap_binds_header_footer_rules_to_sections(tmp_path) -> None:
    result = run_template_gap_eval(
        ROOT,
        "nannong-undergraduate",
        ROOT / "inputs/school-nannong-undergraduate-template.docx",
        tmp_path / "header_footer_gap",
    )
    tree = read_json(tmp_path / "header_footer_gap/artifacts/generated_template_tree.json")
    report = read_json(
        tmp_path / "header_footer_gap/artifacts/template_gap_report.json"
    )

    assert result.status == Status.FAIL
    assert tree["data"]["sections"]
    toc_section = next(
        item for item in tree["data"]["sections"] if item["paragraph_index"] == 45
    )
    assert {
        (item["kind"], item["type"], item["part_name"])
        for item in toc_section["effective_references"]
    } >= {
        ("header", "default", "word/header2.xml"),
        ("footer", "default", "word/footer4.xml"),
    }
    assert toc_section["page_numbering"] == {"format": "upperRoman", "start": 1}

    header_footer_items = [
        item
        for item in collect_checks(report)
        if item["category"] == "header_footer"
    ]
    assert any(
        item["type"] == "template_generation_header_footer_match"
        and item["affected_ids"] == ["toc.header_footer.header"]
        and "word/document.xml:p[45]/sectPr" in item["evidence_refs"][0]
        for item in header_footer_items
    )
    toc_page_number = next(
        item
        for item in header_footer_items
        if item["affected_ids"] == ["toc.header_footer.page_number"]
    )
    assert toc_page_number["type"] == "template_generation_page_number_rule_mismatch"
    assert "page_numbering={'format': 'upperRoman', 'start': 1}" in toc_page_number["actual"]
    assert any("sectPr" in ref for ref in toc_page_number["evidence_refs"])


def test_generated_template_gap_binds_word_fields_to_units(tmp_path) -> None:
    nannong_result = run_template_gap_eval(
        ROOT,
        "nannong-undergraduate",
        ROOT / "inputs/school-nannong-undergraduate-template.docx",
        tmp_path / "nannong_field_gap",
    )
    nannong_tree = read_json(
        tmp_path / "nannong_field_gap/artifacts/generated_template_tree.json"
    )
    nannong_report = read_json(
        tmp_path / "nannong_field_gap/artifacts/template_gap_report.json"
    )

    assert nannong_result.status == Status.FAIL
    nannong_toc_field = next(
        item
        for item in nannong_tree["data"]["fields"]
        if item["field_type"] == "TOC"
    )
    assert nannong_toc_field["kind"] == "complexField"
    assert nannong_toc_field["instruction"] == 'TOC \\o "1-3" \\h \\z \\u'
    assert nannong_toc_field["paragraph_index"] == 49
    assert nannong_toc_field["end_paragraph_index"] == 74
    assert any(
        item["type"] == "template_generation_field_match"
        and item["affected_ids"] == ["toc.e_002.field"]
        and item["evidence_refs"] == [
            "word/document.xml:p[49]/field[1]",
            "word/document.xml:p[74]",
        ]
        for item in collect_checks(nannong_report)
    )

    pku_result = run_template_gap_eval(
        ROOT,
        "pku-graduate",
        ROOT / "inputs/school-pku-graduate-template.docx",
        tmp_path / "pku_field_gap",
    )
    pku_tree = read_json(
        tmp_path / "pku_field_gap/artifacts/generated_template_tree.json"
    )
    pku_report = read_json(tmp_path / "pku_field_gap/artifacts/template_gap_report.json")
    pku_field_items = [
        item
        for item in collect_checks(pku_report)
        if item["category"] == "field"
    ]
    pku_seq_instructions = {
        item["instruction"]
        for item in pku_tree["data"]["fields"]
        if item["field_type"] == "SEQ"
    }

    assert pku_result.status == Status.FAIL
    assert {
        "SEQ 图 \\* ARABIC \\S 1",
        "SEQ 表 \\* ARABIC \\s 1",
        "SEQ 公式 \\* ARABIC \\s 1",
    } <= pku_seq_instructions
    assert any(
        item["type"] == "template_generation_field_out_of_unit"
        and item["affected_ids"] == ["toc.field"]
        and 'TOC \\o "3-3" \\h \\z \\t "标题 1,1,标题 2,2,PKU正文前标题,9,PKU正文尾标题,9"' in item["actual"]
        for item in pku_field_items
    )
    assert any(
        item["type"] == "template_generation_field_match"
        and item["affected_ids"] == ["figure_list.field"]
        and item["actual"] == 'TOC \\h \\z \\t "PKU图题" \\c'
        for item in pku_field_items
    )
    assert any(
        item["type"] == "template_generation_field_unverified"
        and item["affected_ids"] == ["table_list.field"]
        and item["status"] == Status.UNKNOWN.value
        for item in pku_field_items
    )
    assert any(
        item["type"] == "template_generation_field_unverified"
        and item["affected_ids"] == ["body_main.e_014.field"]
        and item["status"] == Status.UNKNOWN.value
        for item in pku_field_items
    )
    assert any(
        item["type"] == "template_generation_field_unverified"
        and item["affected_ids"] == ["body_main.e_017.field"]
        and item["status"] == Status.UNKNOWN.value
        for item in pku_field_items
    )
    assert any(
        item["type"] == "template_generation_field_unverified"
        and item["affected_ids"] == ["body_main.e_024.field"]
        and item["status"] == Status.UNKNOWN.value
        for item in pku_field_items
    )


def test_generated_template_gap_binds_numbering_rules_to_units(tmp_path) -> None:
    result = run_template_gap_eval(
        ROOT,
        "pku-graduate",
        ROOT / "inputs/school-pku-graduate-template.docx",
        tmp_path / "pku_numbering_gap",
    )
    tree = read_json(
        tmp_path / "pku_numbering_gap/artifacts/generated_template_tree.json"
    )
    report = read_json(
        tmp_path / "pku_numbering_gap/artifacts/template_gap_report.json"
    )

    assert result.status == Status.FAIL
    heading_definition = next(
        item
        for item in tree["data"]["numbering_definitions"]
        if item["paragraph_style_id"] == "1"
        and item["lvl_text"] == "第%1章"
    )
    assert heading_definition["num_fmt"] == "chineseCountingThousand"

    heading_ref = next(
        item
        for item in tree["data"]["numbering_refs"]
        if item["paragraph_index"] == 127
    )
    assert heading_ref["source_kind"] == "paragraph_style"
    assert heading_ref["num_id"] == "1"
    assert heading_ref["ilvl"] == "0"
    assert heading_ref["lvl_text"] == "第%1章"
    assert heading_ref["source_refs"] == [
        "word/styles.xml:style[1]/numPr",
        "word/numbering.xml:abstractNum[0]/lvl[0]",
    ]

    numbering_items = [
        item
        for item in collect_checks(report)
        if item["category"] == "numbering"
    ]
    assert any(
        item["type"] == "template_generation_numbering_unverified"
        and item["affected_ids"] == ["body_main.e_001.numbering"]
        and "text=第%1章" in item["actual"]
        and "word/document.xml:p[127]/pStyle" in item["evidence_refs"]
        for item in numbering_items
    )
    assert any(
        item["type"] == "template_generation_numbering_unverified"
        and item["affected_ids"] == ["body_main.e_004.numbering"]
        and "%1.%2.%3.%4.%5" in item["expected"]
        and "word/document.xml:p[128]/pStyle" in item["evidence_refs"]
        for item in numbering_items
    )


def test_generated_template_gap_missing_docx_is_unknown(tmp_path) -> None:
    result = run_template_gap_eval(
        ROOT,
        "hunannongye",
        tmp_path / "missing_generated_template.docx",
        tmp_path / "missing_gap",
    )
    report = read_json(tmp_path / "missing_gap/artifacts/template_gap_report.json")

    assert result.status == Status.UNKNOWN
    assert report["summary"]["blocking_status"] == Status.UNKNOWN.value
    assert report["summary"]["display_status"] == Status.UNKNOWN.value
    assert any(
        item["type"] == "template_generation_output_missing"
        for item in collect_checks(report)
    )


def test_template_gap_status_combination_rules() -> None:
    def summary_for(*statuses: str) -> dict:
        report = {
            "input": {
                "status": statuses[0],
                "check_id": "test",
                "type": "test",
                "category": "test",
            },
            "units": [],
            "global_checks": [
                {
                    "status": status,
                    "check_id": "test",
                    "type": "test",
                    "category": "test",
                }
                for status in statuses[1:]
            ],
            "unmodeled_objects": [],
        }
        return summarize_template_gap_report(report)

    assert summary_for("PASS") == {
        "known_status": "PASS",
        "display_status": "PASS",
        "passed_count": 1,
        "failed_count": 0,
        "unknown_count": 0,
        "blocking_status": "PASS",
        "per_unit": [],
    }
    assert summary_for("PASS", "UNKNOWN")["display_status"] == "PASS + UNKNOWN"
    assert summary_for("FAIL")["blocking_status"] == "FAIL"
    assert summary_for("FAIL", "UNKNOWN")["display_status"] == "FAIL + UNKNOWN"
    assert summary_for("UNKNOWN") == {
        "known_status": "UNKNOWN",
        "display_status": "UNKNOWN",
        "passed_count": 0,
        "failed_count": 0,
        "unknown_count": 1,
        "blocking_status": "UNKNOWN",
        "per_unit": [],
    }
