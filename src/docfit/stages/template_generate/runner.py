from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from docx import Document

from docfit.core.io import now_iso, sha256_file, sha256_json, write_json
from docfit.core.models import StageResult, make_finding
from docfit.core.status import Status
from docfit.ooxml.package import is_valid_docx


DEFAULT_TEMPLATE_GENERATION_STRATEGY = "source_copy_scaffold"
BODY_SLOT_MARKER = "[[DOCFIT_SLOT:body]]"


def generate_template(
    source_template_docx: Path,
    out_dir: Path,
    *,
    strategy: str = DEFAULT_TEMPLATE_GENERATION_STRATEGY,
) -> StageResult:
    if not source_template_docx.exists():
        return StageResult(
            "template_generate",
            Status.UNKNOWN,
            findings=[
                make_finding(
                    1,
                    "template_generate",
                    Status.UNKNOWN,
                    "template_generation_source_missing",
                    "缺少学校原始模板 Word，无法生成可填写模板",
                    "existing source template DOCX",
                    str(source_template_docx),
                    root_cause_bucket="input_missing",
                )
            ],
            coverage=_coverage(input_exists=False),
            blocked_at="template_generate",
        )
    if not is_valid_docx(source_template_docx):
        return StageResult(
            "template_generate",
            Status.FAIL,
            findings=[
                make_finding(
                    1,
                    "template_generate",
                    Status.FAIL,
                    "template_generation_source_invalid",
                    "学校原始模板不是有效 DOCX 包，无法生成可填写模板",
                    "valid source template DOCX",
                    str(source_template_docx),
                    evidence_refs=[str(source_template_docx)],
                    root_cause_bucket="input_invalid",
                )
            ],
            coverage=_coverage(input_exists=True, input_valid_docx=False),
            blocked_at="template_generate",
        )

    generated_template_docx = out_dir / "generated_template.docx"
    generated_template_docx.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_template_docx, generated_template_docx)

    actions_executed: list[dict[str, Any]] = [
        {
            "action_id": "a_001",
            "action_type": "copy_source_docx",
            "unit_id": None,
            "element_id": None,
            "source_ref": str(source_template_docx),
            "output_ref": str(generated_template_docx),
            "status": "executed",
            "reason": "source_copy_scaffold first copies the whole source Word as the generation base",
        }
    ]
    slots: list[dict[str, Any]] = []
    slot_action, slot = _ensure_body_slot(generated_template_docx)
    actions_executed.append(slot_action)
    slots.append(slot)

    actions_deferred = _deferred_actions()
    plan = build_template_generation_plan(
        source_template_docx,
        strategy=strategy,
        actions=[
            {
                "action_id": "a_001",
                "action_type": "copy_source_docx",
                "unit_id": None,
                "element_id": None,
                "source_ref": str(source_template_docx),
                "target_ref": str(generated_template_docx),
                "status": "planned",
                "reason": "create a real generated_template.docx scaffold",
            },
            {
                "action_id": "a_002",
                "action_type": "create_or_preserve_body_slot",
                "unit_id": "body_main",
                "element_id": "slot_body_start",
                "source_ref": None,
                "target_ref": slot["output_ref"],
                "status": "planned",
                "reason": "make the first scaffold usable by later placement/render work",
            },
            *actions_deferred,
        ],
    )
    manifest = build_template_generation_manifest(
        source_template_docx=source_template_docx,
        generated_template_docx=generated_template_docx,
        strategy=strategy,
        plan=plan,
        slots=slots,
        actions_executed=actions_executed,
        actions_deferred=actions_deferred,
    )

    return StageResult(
        "template_generate",
        Status.PASS,
        artifacts={
            "template_generation_plan": plan,
            "template_generation_manifest": manifest,
        },
        artifact_paths={"generated_template_docx": generated_template_docx},
        coverage=_coverage(
            input_exists=True,
            input_valid_docx=True,
            output_docx=True,
            manifest=True,
            body_slot=True,
            deferred_actions_recorded=True,
        ),
        user_message=(
            "template_generate wrote a source-copy scaffold only; run template-gap "
            "before using the generated template as quality evidence."
        ),
    )


def build_template_generation_plan(
    source_template_docx: Path,
    *,
    strategy: str = DEFAULT_TEMPLATE_GENERATION_STRATEGY,
    actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "template_generation_plan",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.1.0"},
        "created_at": now_iso(),
        "strategy": strategy,
        "source_template_docx": str(source_template_docx),
        "input_hashes": {
            "source_template_docx": sha256_file(source_template_docx)
            if source_template_docx.exists()
            else None
        },
        "actions": actions or [],
    }


def build_template_generation_manifest(
    *,
    source_template_docx: Path,
    generated_template_docx: Path,
    strategy: str,
    plan: dict[str, Any],
    slots: list[dict[str, Any]],
    actions_executed: list[dict[str, Any]],
    actions_deferred: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "template_generation_manifest",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-template-generate", "version": "0.1.0"},
        "created_at": now_iso(),
        "strategy": strategy,
        "input_hashes": {
            "source_template_docx": sha256_file(source_template_docx),
            "template_generation_plan": sha256_json(plan),
        },
        "output": {
            "generated_template_docx": str(generated_template_docx),
            "generated_template_docx_hash": sha256_file(generated_template_docx),
        },
        "slots": slots,
        "actions_executed": actions_executed,
        "actions_deferred": actions_deferred,
    }


def write_template_generation_outputs(out_dir: Path, result: StageResult) -> None:
    for key in ["template_generation_plan", "template_generation_manifest"]:
        artifact = result.artifacts.get(key)
        if artifact is None:
            continue
        path = out_dir / "artifacts" / f"{key}.json"
        write_json(path, artifact)
        result.artifact_paths[key] = path


def _ensure_body_slot(generated_template_docx: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    doc = Document(generated_template_docx)
    for index, paragraph in enumerate(doc.paragraphs, start=1):
        if BODY_SLOT_MARKER in paragraph.text:
            output_ref = f"word/document.xml:p[{index}]"
            return (
                {
                    "action_id": "a_002",
                    "action_type": "preserve_existing_body_slot",
                    "unit_id": "body_main",
                    "element_id": "slot_body_start",
                    "source_ref": output_ref,
                    "output_ref": output_ref,
                    "status": "executed",
                    "reason": "source Word already contained the DocFit body slot marker",
                },
                _body_slot(output_ref=output_ref, source="source_template"),
            )

    doc.add_paragraph(BODY_SLOT_MARKER)
    doc.save(generated_template_docx)
    output_ref = f"word/document.xml:p[{len(doc.paragraphs)}]"
    return (
        {
            "action_id": "a_002",
            "action_type": "append_body_slot_marker",
            "unit_id": "body_main",
            "element_id": "slot_body_start",
            "source_ref": None,
            "output_ref": output_ref,
            "status": "executed",
            "reason": "first scaffold adds a stable body slot marker when the source Word has none",
        },
        _body_slot(output_ref=output_ref, source="generated_scaffold"),
    )


def _body_slot(*, output_ref: str, source: str) -> dict[str, Any]:
    return {
        "slot_id": "slot_body_start",
        "unit_id": "body_main",
        "element_id": "slot_body_start",
        "kind": "body_content",
        "marker": BODY_SLOT_MARKER,
        "output_ref": output_ref,
        "source": source,
        "required": True,
    }


def _deferred_actions() -> list[dict[str, Any]]:
    return [
        {
            "action_id": "d_001",
            "action_type": "infer_template_rules",
            "unit_id": None,
            "element_id": None,
            "source_ref": None,
            "target_ref": None,
            "status": "deferred",
            "reason": "automatic template rule discovery is not implemented in the first scaffold",
        },
        {
            "action_id": "d_002",
            "action_type": "remove_instruction_text",
            "unit_id": None,
            "element_id": None,
            "source_ref": None,
            "target_ref": None,
            "status": "deferred",
            "reason": "instruction cleanup needs unit regions before it can be done safely",
        },
        {
            "action_id": "d_003",
            "action_type": "copy_fixed_blocks_by_unit",
            "unit_id": None,
            "element_id": None,
            "source_ref": None,
            "target_ref": None,
            "status": "deferred",
            "reason": "unit-level copying needs automatic unit boundaries",
        },
    ]


def _coverage(
    *,
    input_exists: bool,
    input_valid_docx: bool | None = None,
    output_docx: bool = False,
    manifest: bool = False,
    body_slot: bool = False,
    deferred_actions_recorded: bool = False,
) -> dict[str, bool]:
    return {
        "template_generation.input_exists": input_exists,
        "template_generation.input_valid_docx": bool(input_valid_docx),
        "template_generation.output_docx": output_docx,
        "template_generation.manifest": manifest,
        "template_generation.body_slot": body_slot,
        "template_generation.deferred_actions_recorded": deferred_actions_recorded,
    }
