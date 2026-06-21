from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file, sha256_json


def build_template_generation_manifest(
    *,
    request: dict[str, Any],
    source_tree: dict[str, Any],
    discovered_rules: dict[str, Any],
    template_artifact: dict[str, Any],
    decisions: dict[str, Any],
    plan: dict[str, Any],
    generated_template_docx: Path,
    execution: dict[str, Any],
    debug_snapshot_dir: Path | None = None,
    copy_source_snapshot_docx: Path | None = None,
) -> dict[str, Any]:
    manifest = {
        "artifact_type": "template_generation_manifest",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.2.0"},
        "created_at": now_iso(),
        "strategy": request.get("strategy"),
        "input_hashes": {
            "source_template_docx": request.get("source_template_hash"),
            "source_template_tree": sha256_json(source_tree),
            "discovered_template_rules": sha256_json(discovered_rules),
            "template_artifact": sha256_json(template_artifact),
            "template_unit_decisions": sha256_json(decisions),
            "template_generation_plan": sha256_json(plan),
        },
        "output": {
            "generated_template_docx": str(generated_template_docx),
            "generated_template_docx_hash": sha256_file(generated_template_docx),
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
            "naming": "files are ordered by flow step prefix plus artifact name",
        }
    return manifest
