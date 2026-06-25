from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file, sha256_json


def build_template_generation_manifest(
    *,
    request: dict[str, Any],
    document_facts: dict[str, Any],
    unit_map: dict[str, Any],
    element_spec: dict[str, Any],
    global_spec: dict[str, Any],
    template_spec: dict[str, Any],
    plan: dict[str, Any],
    fillable_template_docx: Path,
    execution: dict[str, Any],
    debug_snapshot_dir: Path | None = None,
    copy_source_snapshot_docx: Path | None = None,
) -> dict[str, Any]:
    manifest = {
        "artifact_type": "build_manifest",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.3.0"},
        "created_at": now_iso(),
        "strategy": request.get("strategy"),
        "input_hashes": {
            "source_template_docx": request.get("source_template_hash"),
            "document_facts": sha256_json(document_facts),
            "unit_map": sha256_json(unit_map),
            "element_spec": sha256_json(element_spec),
            "global_spec": sha256_json(global_spec),
            "template_spec": sha256_json(template_spec),
            "template_generation_plan": sha256_json(plan),
        },
        "output": {
            "fillable_template_docx": str(fillable_template_docx),
            "fillable_template_docx_hash": sha256_file(fillable_template_docx),
        },
        "slots": execution.get("slots", []),
        "generated_fields": execution.get("generated_fields", []),
        "page_breaks": execution.get("page_breaks", []),
        "section_breaks": execution.get("section_breaks", []),
        "synthesized_texts": execution.get("synthesized_texts", []),
        "actions_executed": execution.get("actions_executed", []),
        "actions_requiring_review": execution.get("actions_requiring_review", []),
    }
    if debug_snapshot_dir is not None:
        manifest["debug_snapshot"] = {
            "dir": str(debug_snapshot_dir),
            "copy_source_docx": str(copy_source_snapshot_docx)
            if copy_source_snapshot_docx is not None
            else None,
            "naming": "files are ordered by template parse/build phase prefix",
        }
    return manifest
