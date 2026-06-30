from __future__ import annotations

from pathlib import Path

from docfit.template_generation.t2_standard import (
    audit_unit_map_against_t2_standard,
    expected_unit_ids_from_t2_standard,
    expected_units_from_t2_standard,
    load_t2_unit_pagination_standard,
)


ROOT = Path(__file__).resolve().parents[2]
SCHOOLS = ["hunannongye", "nannong-undergraduate", "pku-graduate"]


def test_t2_standard_loader_reads_three_school_unit_order() -> None:
    for school in SCHOOLS:
        standard = load_t2_unit_pagination_standard(ROOT, school)
        expected_ids = expected_unit_ids_from_t2_standard(standard)
        expected_ids_from_units = [
            str(unit["unit_id"]) for unit in expected_units_from_t2_standard(standard)
        ]

        assert standard["artifact_under_test"] == "unit_map"
        assert standard["stage_id"] == "T2"
        assert standard["verifier_state"] == "configured"
        assert standard["gate_enabled"] is True
        assert expected_ids
        assert expected_ids == expected_ids_from_units


def test_t2_standard_audit_passes_matching_unit_order_with_gate_disabled() -> None:
    standard = _standard(["cover", "toc", "body_main"], gate_enabled=False)
    audit = audit_unit_map_against_t2_standard(
        _unit_map(["cover", "toc", "body_main"]),
        standard,
    )

    assert audit["audit_status"] == "PASS"
    assert audit["gate_status"] == "AUDIT_PASS"
    assert audit["missing_unit_ids"] == []
    assert audit["unexpected_unit_ids"] == []
    assert audit["unit_order_matches"] is True


def test_t2_standard_audit_reports_mismatch_without_enforcing_disabled_gate() -> None:
    standard = _standard(["cover", "toc", "body_main"], gate_enabled=False)
    audit = audit_unit_map_against_t2_standard(
        _unit_map(["cover", "toc", "custom:template:正文:3"]),
        standard,
    )

    assert audit["audit_status"] == "FAIL"
    assert audit["gate_status"] == "AUDIT_FAIL"
    assert audit["missing_unit_ids"] == ["body_main"]
    assert audit["unexpected_unit_ids"] == ["custom:template:正文:3"]
    assert audit["custom_unit_ids"] == ["custom:template:正文:3"]
    assert {finding["type"] for finding in audit["findings"]} == {
        "t2_standard_unit_order_mismatch",
        "t2_standard_units_missing",
        "t2_standard_custom_units_present",
    }


def test_t2_standard_audit_enforces_enabled_gate() -> None:
    standard = _standard(["cover", "toc", "body_main"], gate_enabled=True)
    audit = audit_unit_map_against_t2_standard(
        _unit_map(["cover", "toc"]),
        standard,
    )

    assert audit["audit_status"] == "FAIL"
    assert audit["gate_status"] == "FAIL"
    assert audit["missing_unit_ids"] == ["body_main"]


def test_t2_standard_audit_reports_invalid_standard_as_unknown() -> None:
    audit = audit_unit_map_against_t2_standard(
        _unit_map(["cover"]),
        {
            "school_id": "demo",
            "standard_id": "demo-t2",
            "artifact_under_test": "wrong_artifact",
            "expected": {"unit_order": ["cover"], "units": []},
        },
    )

    assert audit["audit_status"] == "UNKNOWN"
    assert audit["gate_status"] == "AUDIT_UNKNOWN"
    assert "artifact_under_test must be unit_map" in audit["schema_errors"]
    assert "expected.units is missing or empty" in audit["schema_errors"]


def test_t2_standard_audit_checks_anchor_owner_when_source_tree_is_supplied() -> None:
    standard = _standard(["cover", "abstract_cn"], gate_enabled=False)
    standard["expected"]["units"][1]["anchors"] = {
        "start_title": "摘要",
        "title_aliases": ["摘要"],
    }
    audit = audit_unit_map_against_t2_standard(
        _unit_map_with_refs({"cover": [1], "abstract_cn": [2]}),
        standard,
        source_tree=_source_tree([(1, "封面"), (2, "摘□要（三号黑体）")]),
    )

    assert audit["anchor_owner_failures"] == []
    assert audit["anchor_owner_results"][-1]["status"] == "PASS"
    assert audit["anchor_owner_results"][-1]["actual_unit_id"] == "abstract_cn"


def test_t2_standard_audit_reports_anchor_owner_mismatch() -> None:
    standard = _standard(["cover", "abstract_cn"], gate_enabled=False)
    standard["expected"]["units"][1]["anchors"] = {
        "start_title": "摘要",
        "title_aliases": ["摘要"],
    }
    audit = audit_unit_map_against_t2_standard(
        _unit_map_with_refs({"cover": [1], "toc": [2]}),
        standard,
        source_tree=_source_tree([(1, "封面"), (2, "摘□要（三号黑体）")]),
    )

    assert audit["audit_status"] == "FAIL"
    assert audit["anchor_owner_failures"] == [
        {
            "expected_unit_id": "abstract_cn",
            "source_seq": 2,
            "text": "摘□要（三号黑体）",
            "actual_unit_id": "toc",
            "status": "FAIL",
        }
    ]
    assert any(
        finding["type"] == "t2_standard_anchor_owner_mismatch"
        for finding in audit["findings"]
    )


def test_t2_standard_audit_accepts_anchor_owner_by_source_ref_without_source_seq() -> None:
    standard = _standard(["toc"], gate_enabled=True)
    standard["expected"]["units"][0]["anchors"] = {
        "start_title": "目录",
        "title_aliases": ["目录"],
    }
    audit = audit_unit_map_against_t2_standard(
        {
            "units": [
                {
                    "unit_id": "toc",
                    "source_refs": ["word/document.xml:p[65]/field[39]"],
                }
            ]
        },
        standard,
        source_tree={
            "layers": {
                "body_flow": [
                    {
                        "structure_layer": "body_flow",
                        "source_ref": "word/document.xml:p[65]/field[39]",
                        "text": "目录",
                    }
                ]
            }
        },
    )

    assert audit["audit_status"] == "PASS"
    assert audit["gate_status"] == "PASS"
    assert audit["anchor_owner_failures"] == []
    assert audit["anchor_owner_results"] == [
        {
            "expected_unit_id": "toc",
            "source_seq": None,
            "text": "目录",
            "actual_unit_id": "toc",
            "status": "PASS",
        }
    ]


def _standard(unit_ids: list[str], *, gate_enabled: bool) -> dict:
    return {
        "school_id": "demo",
        "standard_id": "demo-t2",
        "artifact_under_test": "unit_map",
        "verifier_state": "configured" if gate_enabled else "not_configured",
        "gate_enabled": gate_enabled,
        "expected": {
            "unit_order": unit_ids,
            "units": [{"unit_id": unit_id} for unit_id in unit_ids],
        },
    }


def _unit_map(unit_ids: list[str]) -> dict:
    return {"units": [{"unit_id": unit_id} for unit_id in unit_ids]}


def _unit_map_with_refs(unit_refs: dict[str, list[int]]) -> dict:
    return {
        "units": [
            {"unit_id": unit_id, "source_seq_refs": refs}
            for unit_id, refs in unit_refs.items()
        ]
    }


def _source_tree(entries: list[tuple[int, str]]) -> dict:
    return {
        "layers": {
            "body_flow": [
                {
                    "structure_layer": "body_flow",
                    "source_seq": seq,
                    "text": text,
                }
                for seq, text in entries
            ]
        }
    }
