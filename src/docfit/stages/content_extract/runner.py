from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from docfit.core.io import now_iso, sha256_file, sha256_json, sha256_text, write_json
from docfit.core.models import Finding, StageResult, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.ooxml.package import detect_unsupported_visible_objects, is_valid_docx


def iter_block_items(parent: DocumentType) -> Iterable[Paragraph | Table]:
    body = parent.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _paragraph_kind(paragraph: Paragraph) -> tuple[str, list[dict[str, Any]]]:
    style_name = paragraph.style.name if paragraph.style is not None else ""
    candidates: list[dict[str, Any]] = []
    if style_name.lower().startswith("heading"):
        level = 1
        parts = style_name.split()
        if parts and parts[-1].isdigit():
            level = int(parts[-1])
        candidates.append(
            {
                "kind": "heading",
                "level_candidate": level,
                "confidence": 0.95,
                "evidence": [f"style:{style_name}"],
            }
        )
        return "heading", candidates
    if paragraph.runs and any(run.bold for run in paragraph.runs) and len(paragraph.text) <= 40:
        candidates.append(
            {
                "kind": "heading",
                "level_candidate": 1,
                "confidence": 0.55,
                "evidence": ["bold", "short_text"],
            }
        )
    return "paragraph", candidates


def _style_signals(paragraph: Paragraph) -> dict[str, Any]:
    sizes = [
        run.font.size.pt
        for run in paragraph.runs
        if run.font.size is not None and run.font.size.pt is not None
    ]
    return {
        "style_name": paragraph.style.name if paragraph.style is not None else None,
        "bold": any(bool(run.bold) for run in paragraph.runs),
        "font_size": max(sizes) if sizes else None,
        "alignment": str(paragraph.alignment) if paragraph.alignment is not None else None,
    }


def _table_payload(table: Table) -> list[list[str]]:
    return [[cell.text.strip() for cell in row.cells] for row in table.rows]


def extract_student_content(
    student_docx: Path,
    *,
    simulate_missing_content_id: str | None = None,
) -> StageResult:
    findings: list[Finding] = []
    if not is_valid_docx(student_docx):
        findings.append(
            make_finding(
                1,
                "content",
                Status.FAIL,
                "invalid_docx",
                "Student input is not a valid DOCX package",
                "valid .docx package",
                str(student_docx),
                root_cause_bucket="input_invalid",
            )
        )
        return StageResult("content", Status.FAIL, findings=findings)

    doc = Document(student_docx)
    ledger: list[dict[str, Any]] = []
    nonempty_paragraph_count = 0
    table_count = 0
    reading_order = 1
    paragraph_index = 0
    table_index = 0
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            paragraph_index += 1
            text = block.text.strip()
            if not text:
                continue
            nonempty_paragraph_count += 1
            kind, semantic_candidates = _paragraph_kind(block)
            content_id = f"c_{reading_order:03d}"
            item = {
                "content_id": content_id,
                "kind": kind,
                "text": text,
                "text_hash": sha256_text(text),
                "reading_order": reading_order,
                "source_ref": f"word/document.xml:p[{paragraph_index}]",
                "style_signals": _style_signals(block),
                "semantic_candidates": semantic_candidates,
                "payload": {"type": "text", "text": text},
            }
            if simulate_missing_content_id != content_id:
                ledger.append(item)
            reading_order += 1
        elif isinstance(block, Table):
            table_index += 1
            table_count += 1
            payload = _table_payload(block)
            content_id = f"c_{reading_order:03d}"
            if simulate_missing_content_id != content_id:
                ledger.append(
                    {
                        "content_id": content_id,
                        "kind": "table",
                        "text": json.dumps(payload, ensure_ascii=False),
                        "text_hash": sha256_json(payload),
                        "reading_order": reading_order,
                        "source_ref": f"word/document.xml:tbl[{table_index}]",
                        "style_signals": {"rows": len(payload), "columns": len(payload[0]) if payload else 0},
                        "semantic_candidates": [],
                        "payload": {"type": "table", "rows": payload},
                    }
                )
            reading_order += 1

    unsupported = detect_unsupported_visible_objects(student_docx)
    artifact = {
        "artifact_type": "student_content_artifact",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-content-extract", "version": "0.1.0"},
        "created_at": now_iso(),
        "input_hashes": {"student_docx": sha256_file(student_docx)},
        "provenance": {"student_docx": str(student_docx)},
        "status_notes": [],
        "unsupported": unsupported,
        "data": {
            "document_stats": {
                "paragraph_count": nonempty_paragraph_count,
                "table_count": table_count,
                "image_count": sum(1 for item in unsupported if item["object_type"] == "image"),
            },
            "visible_content_ledger": ledger,
            "assets": [],
            "unsupported": unsupported,
        },
    }
    findings.extend(verify_student_content_artifact(artifact, expected_visible_count=nonempty_paragraph_count + table_count))
    status = merge_statuses([Status(f.status) for f in findings]) if findings else Status.PASS
    return StageResult(
        "content",
        status,
        findings=findings,
        artifacts={"student_content_artifact": artifact},
        coverage={
            "content.visible_paragraphs": nonempty_paragraph_count > 0,
            "content.visible_tables": table_count > 0,
            "content.reading_order": True,
            "content.stable_ids": True,
        },
        user_message=(
            "当前无法安全转换该文档，因为文档中包含系统尚不能可靠处理的可见内容。"
            if status == Status.UNKNOWN
            else None
        ),
    )


def verify_student_content_artifact(
    artifact: dict[str, Any],
    *,
    expected_visible_count: int | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    ledger = artifact.get("data", {}).get("visible_content_ledger", [])
    unsupported = artifact.get("unsupported", [])
    next_index = 1
    if expected_visible_count is not None and len(ledger) != expected_visible_count:
        findings.append(
            make_finding(
                next_index,
                "content",
                Status.FAIL,
                "visible_content_missing_from_ledger",
                "Visible content was not fully represented in the ledger",
                f"{expected_visible_count} ledger items",
                f"{len(ledger)} ledger items",
                root_cause_bucket="content_extraction_gap",
            )
        )
        next_index += 1
    seen: set[str] = set()
    for item in ledger:
        content_id = item.get("content_id")
        if not content_id:
            findings.append(
                make_finding(
                    next_index,
                    "content",
                    Status.FAIL,
                    "missing_content_id",
                    "Every visible content block must have content_id",
                    "content_id present",
                    repr(item),
                    root_cause_bucket="content_contract_violation",
                )
            )
            next_index += 1
        elif content_id in seen:
            findings.append(
                make_finding(
                    next_index,
                    "content",
                    Status.FAIL,
                    "duplicate_content_id",
                    "Every content_id must be unique",
                    "unique content_id",
                    content_id,
                    affected_ids=[content_id],
                    root_cause_bucket="content_contract_violation",
                )
            )
            next_index += 1
        seen.add(content_id)
        if "reading_order" not in item:
            findings.append(
                make_finding(
                    next_index,
                    "content",
                    Status.FAIL,
                    "missing_reading_order",
                    "Every visible content block must have reading order",
                    "reading_order present",
                    content_id or "missing id",
                    affected_ids=[content_id] if content_id else [],
                    root_cause_bucket="content_contract_violation",
                )
            )
            next_index += 1
        if not item.get("source_ref"):
            findings.append(
                make_finding(
                    next_index,
                    "content",
                    Status.UNKNOWN,
                    "missing_provenance",
                    "Every visible content block must have provenance",
                    "source_ref present",
                    content_id or "missing id",
                    affected_ids=[content_id] if content_id else [],
                    root_cause_bucket="content_provenance_gap",
                )
            )
            next_index += 1
    for item in unsupported:
        if item.get("blocking", True):
            findings.append(
                make_finding(
                    next_index,
                    "content",
                    Status.UNKNOWN,
                    "unsupported_visible_object",
                    f"Unsupported visible object: {item.get('object_type')}",
                    "all visible objects are extracted or modeled",
                    item.get("reason", "unsupported"),
                    evidence_refs=[item.get("source_ref", "")],
                    affected_ids=[item.get("content_id", "")],
                    root_cause_bucket="unsupported_visible_object",
                )
            )
            next_index += 1
    return findings


def write_content_outputs(out_dir: Path, result: StageResult) -> None:
    artifact = result.artifacts.get("student_content_artifact")
    if artifact is not None:
        path = out_dir / "artifacts" / "student_content_artifact.json"
        write_json(path, artifact)
        result.artifact_paths["student_content_artifact"] = path
