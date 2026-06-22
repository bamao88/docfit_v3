from __future__ import annotations

from pathlib import Path

from docfit.core.models import StageResult, make_finding
from docfit.core.status import Status
from docfit.ooxml.package import is_valid_docx

from .constants import BODY_SLOT_MARKER, DEFAULT_TEMPLATE_GENERATION_STRATEGY
from .executor import execute_template_generation_plan
from .generation_model import build_template_generation_model
from .manifest import build_template_generation_manifest
from .outputs import (
    _new_template_generation_debug_dir,
    write_template_generation_debug_snapshot,
    write_template_generation_outputs,
)
from .plan import build_template_generation_plan
from .request import build_template_generation_request
from .source_tree import inspect_source_template_docx
from .structure_candidates import build_template_structure_candidates


def generate_template(
    source_template_docx: Path,
    out_dir: Path,
    *,
    strategy: str = DEFAULT_TEMPLATE_GENERATION_STRATEGY,
    debug_root: Path | None = None,
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

    debug_dir = _new_template_generation_debug_dir(debug_root)
    copy_source_snapshot_docx = (
        debug_dir / "05.0_copy_source_docx.docx" if debug_dir is not None else None
    )

    request = build_template_generation_request(
        source_template_docx,
        out_dir,
        strategy=strategy,
    )
    source_tree = inspect_source_template_docx(source_template_docx)
    structure_candidates = build_template_structure_candidates(source_tree)
    generation_model = build_template_generation_model(
        request,
        structure_candidates=structure_candidates,
    )
    plan = build_template_generation_plan(
        request,
        generation_model=generation_model,
    )
    generated_template_docx = out_dir / "generated_template.docx"
    execution = execute_template_generation_plan(
        source_template_docx,
        generated_template_docx,
        plan,
        copy_source_snapshot_docx=copy_source_snapshot_docx,
    )
    manifest = build_template_generation_manifest(
        request=request,
        source_tree=source_tree,
        structure_candidates=structure_candidates,
        generation_model=generation_model,
        plan=plan,
        generated_template_docx=generated_template_docx,
        execution=execution,
        debug_snapshot_dir=debug_dir,
        copy_source_snapshot_docx=copy_source_snapshot_docx,
    )
    if debug_dir is not None:
        write_template_generation_debug_snapshot(
            debug_dir,
            source_template_docx=source_template_docx,
            request=request,
            source_tree=source_tree,
            structure_candidates=structure_candidates,
            generation_model=generation_model,
            plan=plan,
            copy_source_snapshot_docx=copy_source_snapshot_docx,
            generated_template_docx=generated_template_docx,
            manifest=manifest,
        )

    artifact_paths = {"generated_template_docx": generated_template_docx}
    if debug_dir is not None:
        artifact_paths["template_generation_debug_dir"] = debug_dir

    return StageResult(
        "template_generate",
        Status.PASS,
        artifacts={
            "template_generation_request": request,
            "source_template_tree": source_tree,
            "template_structure_candidates": structure_candidates,
            "template_generation_model": generation_model,
            "template_generation_plan": plan,
            "template_generation_manifest": manifest,
        },
        artifact_paths=artifact_paths,
        coverage=_coverage(
            input_exists=True,
            input_valid_docx=True,
            source_tree=bool(source_tree.get("layers", {}).get("body_flow")),
            structure_candidates=bool(structure_candidates.get("units")),
            generation_model=bool(generation_model.get("units")),
            generation_plan=bool(plan.get("actions")),
            output_docx=generated_template_docx.exists(),
            manifest=True,
            body_slot=bool(manifest.get("slots")),
        ),
        user_message=(
            "template_generate produced a complete stage artifact chain; "
            "template quality still belongs to template-gap and real-core gates."
        ),
    )


def _coverage(
    *,
    input_exists: bool,
    input_valid_docx: bool | None = None,
    source_tree: bool = False,
    structure_candidates: bool = False,
    generation_model: bool = False,
    generation_plan: bool = False,
    output_docx: bool = False,
    manifest: bool = False,
    body_slot: bool = False,
) -> dict[str, bool]:
    return {
        "template_generation.input_exists": input_exists,
        "template_generation.input_valid_docx": bool(input_valid_docx),
        "template_generation.source_tree": source_tree,
        "template_generation.structure_candidates": structure_candidates,
        "template_generation.generation_model": generation_model,
        "template_generation.plan": generation_plan,
        "template_generation.output_docx": output_docx,
        "template_generation.manifest": manifest,
        "template_generation.body_slot": body_slot,
    }
