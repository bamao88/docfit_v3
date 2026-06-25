from __future__ import annotations

from docfit.core.status import Status
from docfit.template_generation.artifacts import (
    build_global_spec,
    build_template_spec,
)
from docfit.template_generation.verifier import (
    _verify_t4_global_spec,
    _verify_t5_template_spec,
)


def _document_facts_with_two_sections() -> dict:
    return {
        "artifact_type": "document_facts",
        "body_flow": [
            {
                "source_seq": 1,
                "source_ref": "word/document.xml:p[1]",
                "part_name": "word/document.xml",
                "paragraph_id": "p_0001",
            },
            {
                "source_seq": 2,
                "source_ref": "word/document.xml:p[2]",
                "part_name": "word/document.xml",
                "paragraph_id": "p_0002",
            },
            {
                "source_seq": 3,
                "source_ref": "word/document.xml:p[3]",
                "part_name": "word/document.xml",
                "paragraph_id": "p_0003",
            },
            {
                "source_seq": 4,
                "source_ref": "word/document.xml:p[4]",
                "part_name": "word/document.xml",
                "paragraph_id": "p_0004",
            },
        ],
        "runs": [],
        "unknown_objects": [],
        "data": {
            "sections": [
                {
                    "index": 1,
                    "paragraph_index": 2,
                    "source_ref": "word/document.xml:p[2]/sectPr",
                    "references": [
                        {
                            "kind": "footer",
                            "type": "default",
                            "part_name": "word/footer1.xml",
                            "source_ref": "word/document.xml:p[2]/sectPr/footerReference[1]",
                        }
                    ],
                    "effective_references": [
                        {
                            "kind": "footer",
                            "type": "default",
                            "part_name": "word/footer1.xml",
                            "source_ref": "word/document.xml:p[2]/sectPr/footerReference[1]",
                        }
                    ],
                    "page_numbering": {"format": "upperRoman", "start": 1},
                    "page_size": {},
                    "page_margins": {},
                },
                {
                    "index": 2,
                    "paragraph_index": None,
                    "source_ref": "word/document.xml:body/sectPr",
                    "references": [],
                    "effective_references": [],
                    "page_numbering": {},
                    "page_size": {},
                    "page_margins": {},
                },
            ],
            "headers_footers": [
                {
                    "kind": "footer",
                    "part_name": "word/footer1.xml",
                    "text": "I",
                    "source_ref": "word/footer1.xml",
                }
            ],
            "fields": [
                {
                    "kind": "fldSimple",
                    "field_type": "PAGE",
                    "instruction": "PAGE",
                    "part_name": "word/footer1.xml",
                    "paragraph_index": 1,
                    "end_paragraph_index": 1,
                    "source_ref": "word/footer1.xml:p[1]/field[1]",
                }
            ],
            "numbering_definitions": [],
            "numbering_refs": [],
        },
    }


def test_global_spec_builds_section_boundaries_and_page_evidence() -> None:
    global_spec = build_global_spec(_document_facts_with_two_sections())

    first, second = global_spec["section_profiles"]
    assert global_spec["artifact_version"] == "1.1"
    assert first["boundary"]["start_source_seq"] == 1
    assert first["boundary"]["end_source_seq"] == 2
    assert first["page_numbering"]["declared"]["format"] == "upperRoman"
    assert first["page_numbering"]["display"]["status"] == "detected"
    assert first["page_numbering"]["fields"][0]["source_ref"] == (
        "word/footer1.xml:p[1]/field[1]"
    )
    assert second["boundary"]["start_source_seq"] == 3
    assert second["boundary"]["end_source_seq"] == 4
    assert second["page_numbering"]["display"]["status"] == "no_page_field"
    assert global_spec["page_numbering"]["status"] == "mixed"

    findings = _verify_t4_global_spec(global_spec, start_index=1)
    assert findings == []


def test_template_spec_binds_units_to_overlapping_section_profiles() -> None:
    document_facts = _document_facts_with_two_sections()
    global_spec = build_global_spec(document_facts)
    unit_map = {
        "artifact_type": "unit_map",
        "flags": [],
        "units": [
            {
                "unit_id": "toc",
                "source_seq_refs": [3, 4],
                "source_seq_range": {"start": 3, "end": 4},
                "section_profile": "section_001",
                "flags": [],
            }
        ],
    }

    template_spec = build_template_spec(
        document_facts,
        unit_map,
        {"artifact_type": "element_spec", "elements": [], "flags": []},
        global_spec,
    )

    unit = template_spec["units"][0]
    assert unit["section_profile"] == "section_002"
    assert [ref["section_profile_id"] for ref in unit["section_profile_refs"]] == [
        "section_002"
    ]
    assert unit["section_profile_refs"][0]["overlap_source_seq_range"] == {
        "start": 3,
        "end": 4,
    }
    assert _verify_t5_template_spec(template_spec, start_index=1) == []


def test_template_spec_records_cross_section_unit_flag() -> None:
    document_facts = _document_facts_with_two_sections()
    global_spec = build_global_spec(document_facts)
    unit_map = {
        "artifact_type": "unit_map",
        "flags": [],
        "units": [
            {
                "unit_id": "front_matter",
                "source_seq_refs": [2, 3],
                "source_seq_range": {"start": 2, "end": 3},
                "section_profile": "section_001",
                "flags": [],
            }
        ],
    }

    template_spec = build_template_spec(
        document_facts,
        unit_map,
        {"artifact_type": "element_spec", "elements": [], "flags": []},
        global_spec,
    )

    unit = template_spec["units"][0]
    assert [ref["section_profile_id"] for ref in unit["section_profile_refs"]] == [
        "section_001",
        "section_002",
    ]
    assert any(
        flag["type"] == "unit_crosses_section_profiles"
        for flag in template_spec["review_flags"]
    )


def test_t4_verifier_rejects_detected_page_numbering_without_page_field() -> None:
    global_spec = build_global_spec(_document_facts_with_two_sections())
    first = global_spec["section_profiles"][0]
    first["page_numbering"]["fields"] = []
    first["page_numbering"]["display"]["status"] = "detected"
    first["page_numbering"]["display"]["has_page_field"] = True

    findings = _verify_t4_global_spec(global_spec, start_index=1)

    assert any(
        finding.type == "global_spec_page_numbering_detected_without_page_field"
        and finding.status == Status.FAIL
        for finding in findings
    )


def test_t5_verifier_rejects_missing_section_profile_ref() -> None:
    global_spec = build_global_spec(_document_facts_with_two_sections())
    template_spec = {
        "artifact_type": "template_spec",
        "global": global_spec,
        "units": [
            {
                "unit_id": "toc",
                "source_seq_refs": [1],
                "section_profile_refs": [
                    {
                        "section_profile_id": "section_missing",
                        "overlap_source_seq_range": {"start": 1, "end": 1},
                    }
                ],
                "elements": [],
            }
        ],
        "review_flags": [],
    }

    findings = _verify_t5_template_spec(template_spec, start_index=1)

    assert any(
        finding.type == "template_spec_unit_section_profile_ref_missing"
        and finding.status == Status.FAIL
        for finding in findings
    )


def test_t5_verifier_reviews_duplicate_other_units_without_fail() -> None:
    global_spec = build_global_spec(_document_facts_with_two_sections())
    other_unit = {
        "unit_id": "other",
        "source_seq_refs": [1],
        "section_profile_refs": [
            {
                "section_profile_id": "section_001",
                "overlap_source_seq_range": {"start": 1, "end": 1},
            }
        ],
        "elements": [],
    }
    template_spec = {
        "artifact_type": "template_spec",
        "global": global_spec,
        "units": [
            other_unit,
            {
                **other_unit,
                "source_seq_refs": [2],
                "section_profile_refs": [
                    {
                        "section_profile_id": "section_001",
                        "overlap_source_seq_range": {"start": 2, "end": 2},
                    }
                ],
            },
        ],
        "review_flags": [],
    }

    findings = _verify_t5_template_spec(template_spec, start_index=1)

    assert any(
        finding.type == "template_spec_duplicate_other_unit_id"
        and finding.status == Status.UNKNOWN
        for finding in findings
    )
    assert not any(
        finding.type == "template_spec_duplicate_unit_id"
        and finding.status == Status.FAIL
        for finding in findings
    )
