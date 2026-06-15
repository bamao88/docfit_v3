from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document

from docfit.core.io import now_iso, sha256_file, write_json
from docfit.core.models import Finding, StageResult, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.harness.real_core import (
    accepted_expected_artifact,
    compare_to_accepted_expected,
    is_real_core_bundle,
    load_template_unit_baseline,
)
from docfit.harness.standards import StandardBundle, verify_template_hash
from docfit.ooxml.package import detect_unsupported_visible_objects, is_valid_docx


def parse_template(template_docx: Path, bundle: StandardBundle) -> StageResult:
    findings: list[Finding] = []
    if not is_valid_docx(template_docx):
        findings.append(
            make_finding(
                1,
                "template",
                Status.FAIL,
                "invalid_docx",
                "Template is not a valid DOCX package",
                "valid .docx package",
                str(template_docx),
                root_cause_bucket="input_invalid",
            )
        )
        return StageResult("template", Status.FAIL, findings=findings)

    findings.extend(verify_template_hash(bundle, "template", start_index=1))
    doc = Document(template_docx)
    styles = []
    for style in doc.styles:
        if getattr(style, "type", None) is None:
            continue
        styles.append(
            {
                "style_id": style.style_id,
                "name": style.name,
                "type": str(style.type),
            }
        )

    paragraphs = [
        {"index": index, "text": paragraph.text.strip(), "style": paragraph.style.name}
        for index, paragraph in enumerate(doc.paragraphs, start=1)
        if paragraph.text.strip()
    ]
    slots = []
    regions = []
    for paragraph in paragraphs:
        if "[[DOCFIT_SLOT:body]]" in paragraph["text"]:
            slots.append(
                {
                    "slot_id": "slot_body_start",
                    "kind": "body_content",
                    "writable": True,
                    "required": True,
                    "accepted_content_kinds": ["heading", "paragraph", "table"],
                    "source_ref": f"word/document.xml:p[{paragraph['index']}]",
                }
            )
            regions.append(
                {
                    "region_id": "body",
                    "kind": "body",
                    "required": True,
                    "anchors": ["slot_body_start"],
                }
            )

    real_core_source_facts: dict[str, Any] | None = None
    real_core_coverage: dict[str, Any] = {}
    if is_real_core_bundle(bundle):
        baseline, baseline_findings = load_template_unit_baseline(
            bundle,
            stage="template",
            start_index=len(findings) + 1,
        )
        findings.extend(baseline_findings)
        if baseline is not None and not baseline_findings:
            real_core_source_facts = accepted_expected_artifact(baseline)
            comparison = compare_to_accepted_expected(
                baseline,
                stage="template",
                start_index=len(findings) + 1,
            )
            findings.extend(comparison.findings)
            source_facts_ok = comparison.status == Status.PASS
            real_core_coverage = {
                "template.unit_tree": source_facts_ok,
                "template.element_order": source_facts_ok,
                "template.style_dimensions": source_facts_ok,
                "template.review_metadata": source_facts_ok,
                "template.comparator_policy": source_facts_ok,
            }
            if source_facts_ok and not slots:
                slots.append(
                    {
                        "slot_id": "slot_body_start",
                        "kind": "body_content",
                        "writable": True,
                        "required": True,
                        "accepted_content_kinds": [
                            "heading",
                            "paragraph",
                            "table",
                            "image",
                        ],
                        "source_ref": "real-core:virtual-body-slot",
                    }
                )
                regions.append(
                    {
                        "region_id": "body",
                        "kind": "body",
                        "required": True,
                        "anchors": ["slot_body_start"],
                        "source_ref": "real-core:virtual-body-slot",
                    }
                )

    unsupported = [
        item
        for item in detect_unsupported_visible_objects(template_docx)
        if item.get("object_type") != "image"
    ]
    if is_real_core_bundle(bundle):
        for item in unsupported:
            item["blocking"] = False
            item["disposition"] = "preserve_in_source_template_copy"
            item["reason"] = (
                "fixed template layout feature is preserved by copying the signed "
                "source DOCX before rendering student content"
            )
    artifact = {
        "artifact_type": "template_artifact",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-parse", "version": "0.1.0"},
        "created_at": now_iso(),
        "school_id": bundle.school_id,
        "template_version": bundle.template_version,
        "input_hashes": {"template_docx": sha256_file(template_docx)},
        "provenance": {"template_docx": str(template_docx)},
        "status_notes": [],
        "unsupported": unsupported,
        "data": {
            "page_setup": {"paper_size": "A4", "margins": {}, "sections": []},
            "styles": styles,
            "paragraphs": paragraphs,
            "regions": regions,
            "slots": slots,
            "protected_zones": [],
            "numbering": [],
            "headers_footers": [],
            "required_fields": [],
            "unsupported": unsupported,
        },
    }
    if real_core_source_facts is not None:
        artifact["real_core_source_facts"] = real_core_source_facts
    findings.extend(verify_template_artifact(artifact, bundle.contracts.get("template_contract", {}), start_index=len(findings) + 1))
    status = merge_statuses([Status(f.status) for f in findings]) if findings else Status.PASS
    return StageResult(
        "template",
        status,
        findings=findings,
        artifacts={"template_artifact": artifact},
        coverage={
            "template.docx_openable": True,
            "template.required_regions": bool(regions),
            "template.required_slots": bool(slots),
            "template.styles_inventory": bool(styles),
            **real_core_coverage,
        },
    )


def verify_template_artifact(
    artifact: dict[str, Any],
    contract: dict[str, Any],
    *,
    start_index: int = 1,
) -> list[Finding]:
    findings: list[Finding] = []
    data = artifact.get("data", {})
    slots = {slot.get("slot_id") for slot in data.get("slots", [])}
    regions = {region.get("region_id") for region in data.get("regions", [])}
    required_slots = contract.get("required_slots", ["slot_body_start"])
    required_regions = contract.get("required_regions", ["body"])
    next_index = start_index
    for slot_id in required_slots:
        if slot_id not in slots:
            findings.append(
                make_finding(
                    next_index,
                    "template",
                    Status.FAIL,
                    "required_slot_missing",
                    f"Required template slot {slot_id} was not identified",
                    "required slot present",
                    ", ".join(sorted(slots)) or "no slots",
                    affected_ids=[slot_id],
                    root_cause_bucket="template_slot_gap",
                )
            )
            next_index += 1
    for region_id in required_regions:
        if region_id not in regions:
            findings.append(
                make_finding(
                    next_index,
                    "template",
                    Status.FAIL,
                    "required_region_missing",
                    f"Required template region {region_id} was not identified",
                    "required region present",
                    ", ".join(sorted(regions)) or "no regions",
                    affected_ids=[region_id],
                    root_cause_bucket="template_region_gap",
                )
            )
            next_index += 1
    for item in artifact.get("unsupported", []):
        if item.get("blocking", True):
            findings.append(
                make_finding(
                    next_index,
                    "template",
                    Status.UNKNOWN,
                    "unsupported_layout_feature",
                    f"Unsupported template layout feature: {item.get('object_type')}",
                    "layout feature modeled or explicitly registered",
                    item.get("reason", "unsupported"),
                    evidence_refs=[item.get("source_ref", "")],
                    root_cause_bucket="unsupported_layout_feature",
                )
            )
            next_index += 1
    return findings


def write_template_outputs(out_dir: Path, result: StageResult) -> None:
    artifact = result.artifacts.get("template_artifact")
    if artifact is not None:
        path = out_dir / "artifacts" / "template_artifact.json"
        write_json(path, artifact)
        result.artifact_paths["template_artifact"] = path
