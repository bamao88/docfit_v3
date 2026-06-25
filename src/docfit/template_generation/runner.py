from __future__ import annotations

from pathlib import Path

from docfit.core.models import StageResult, make_finding
from docfit.core.status import Status
from docfit.ooxml.package import is_valid_docx

from .constants import BODY_SLOT_MARKER, DEFAULT_TEMPLATE_GENERATION_STRATEGY
from .executor import execute_template_generation_plan
from .generation_model import build_template_generation_model
from .manifest import build_template_generation_manifest
from .artifacts import (
    build_element_spec,
    build_global_spec,
    build_template_spec,
    build_unit_map,
    source_tree_from_document_facts,
    template_artifact_view_from_template_spec,
)
from .outputs import (
    _new_template_generation_debug_dir,
    write_template_generation_debug_snapshot,
    write_template_generation_outputs,
)
from .plan import build_template_generation_plan
from .request import build_template_generation_request
from .source_tree import inspect_document_facts_docx
from .structure_candidates import build_template_structure_candidates
from .verifier import verify_template_parse_build


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
        debug_dir / "06.0_copy_source_docx.docx" if debug_dir is not None else None
    )

    request = build_template_generation_request(
        source_template_docx,
        out_dir,
        strategy=strategy,
    )
    document_facts = inspect_document_facts_docx(source_template_docx)
    source_tree = source_tree_from_document_facts(document_facts)
    structure_candidates = build_template_structure_candidates(source_tree)
    unit_map = build_unit_map(document_facts, structure_candidates)
    global_spec = build_global_spec(document_facts)
    generation_model = build_template_generation_model(
        request,
        structure_candidates=structure_candidates,
    )
    element_spec = build_element_spec(generation_model)
    template_spec = build_template_spec(
        document_facts,
        unit_map,
        element_spec,
        global_spec,
    )
    plan = build_template_generation_plan(
        request,
        generation_model=generation_model,
    )
    fillable_template_docx = out_dir / "fillable_template.docx"
    execution = execute_template_generation_plan(
        source_template_docx,
        fillable_template_docx,
        plan,
        copy_source_snapshot_docx=copy_source_snapshot_docx,
    )
    build_manifest = build_template_generation_manifest(
        request=request,
        document_facts=document_facts,
        unit_map=unit_map,
        element_spec=element_spec,
        global_spec=global_spec,
        template_spec=template_spec,
        plan=plan,
        fillable_template_docx=fillable_template_docx,
        execution=execution,
        debug_snapshot_dir=debug_dir,
        copy_source_snapshot_docx=copy_source_snapshot_docx,
    )
    template_artifact = template_artifact_view_from_template_spec(
        request,
        template_spec,
        fillable_template_docx=str(fillable_template_docx),
        build_manifest="build_manifest.json",
    )
    verification_status, verification_findings, verification_report, verification_coverage = (
        verify_template_parse_build(
            document_facts=document_facts,
            unit_map=unit_map,
            element_spec=element_spec,
            global_spec=global_spec,
            template_spec=template_spec,
            build_manifest=build_manifest,
            fillable_template_docx=fillable_template_docx,
        )
    )
    if debug_dir is not None:
        write_template_generation_debug_snapshot(
            debug_dir,
            source_template_docx=source_template_docx,
            request=request,
            document_facts=document_facts,
            unit_map=unit_map,
            element_spec=element_spec,
            global_spec=global_spec,
            template_spec=template_spec,
            source_tree=source_tree,
            structure_candidates=structure_candidates,
            generation_model=generation_model,
            plan=plan,
            copy_source_snapshot_docx=copy_source_snapshot_docx,
            fillable_template_docx=fillable_template_docx,
            build_manifest=build_manifest,
            verification_report=verification_report,
        )

    artifact_paths = {
        "fillable_template_docx": fillable_template_docx,
        "generated_template_docx": fillable_template_docx,
    }
    if debug_dir is not None:
        artifact_paths["template_generation_debug_dir"] = debug_dir

    return StageResult(
        "template_generate",
        verification_status,
        findings=verification_findings,
        artifacts={
            "template_generation_request": request,
            "document_facts": document_facts,
            "unit_map": unit_map,
            "element_spec": element_spec,
            "global_spec": global_spec,
            "template_spec": template_spec,
            "build_manifest": build_manifest,
            "verification_report": verification_report,
            "template_artifact": template_artifact,
            "source_template_tree": source_tree,
            "template_structure_candidates": structure_candidates,
            "template_generation_model": generation_model,
            "template_generation_plan": plan,
        },
        artifact_paths=artifact_paths,
        coverage=_coverage(
            input_exists=True,
            input_valid_docx=True,
            document_facts=bool(document_facts.get("body_flow")),
            unit_map=bool(unit_map.get("units")),
            element_spec=bool(element_spec.get("elements")),
            global_spec=bool(global_spec.get("section_profiles")),
            template_spec=bool(template_spec.get("units")),
            generation_plan=bool(plan.get("actions")),
            output_docx=fillable_template_docx.exists(),
            manifest=True,
            body_slot=bool(build_manifest.get("slots")),
            **verification_coverage,
        ),
        user_message=(
            "template_generate produced document_facts, template_spec, "
            "fillable_template.docx, and deterministic verification evidence."
        ),
    )


def _coverage(
    *,
    input_exists: bool,
    input_valid_docx: bool | None = None,
    document_facts: bool = False,
    unit_map: bool = False,
    element_spec: bool = False,
    global_spec: bool = False,
    template_spec: bool = False,
    generation_plan: bool = False,
    output_docx: bool = False,
    manifest: bool = False,
    body_slot: bool = False,
    **extra: bool,
) -> dict[str, bool]:
    coverage = {
        "template_generation.input_exists": input_exists,
        "template_generation.input_valid_docx": bool(input_valid_docx),
        "template_generation.document_facts": document_facts,
        "template_generation.unit_map": unit_map,
        "template_generation.element_spec": element_spec,
        "template_generation.global_spec": global_spec,
        "template_generation.template_spec": template_spec,
        "template_generation.plan": generation_plan,
        "template_generation.fillable_template_docx": output_docx,
        "template_generation.build_manifest": manifest,
        "template_generation.body_slot": body_slot,
    }
    coverage.update(extra)
    return coverage
