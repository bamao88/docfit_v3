from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from docfit.core.io import read_json, read_yaml, sha256_json, write_json, write_yaml
from docfit.harness.template_generation_standard_quality import (
    TemplateGenerationStandardSet,
)
from docfit.template_generation.artifacts import build_template_spec


ROUTE_REPLAY_DIR = "route_replay"


def materialize_template_generation_route_replay(
    *,
    run_dir: Path,
    out_dir: Path,
    standard_set: TemplateGenerationStandardSet,
) -> Path:
    route_root = out_dir / ROUTE_REPLAY_DIR
    l1_input_contract = _load_json_route(run_dir, "01.5_l1_input_contract.json")
    if l1_input_contract is None:
        for route_id in ("code_raw", "ai_raw"):
            for stage_id, stage_key in _DOWNSTREAM_STAGES.items():
                _write_status(
                    route_root / route_id,
                    route_id=route_id,
                    stage_id=stage_id,
                    stage_key=stage_key,
                    availability="NOT_AVAILABLE",
                    reason="sealed L1 input contract is required before downstream route replay",
                )
        return route_root

    _materialize_code_raw(
        run_dir=run_dir,
        route_root=route_root,
        standard_set=standard_set,
        l1_input_contract=l1_input_contract,
    )
    _materialize_ai_raw(
        run_dir=run_dir,
        route_root=route_root,
    )
    return route_root


def _materialize_code_raw(
    *,
    run_dir: Path,
    route_root: Path,
    standard_set: TemplateGenerationStandardSet,
    l1_input_contract: dict[str, Any],
) -> None:
    route_dir = route_root / "code_raw"
    unit_map = _load_yaml_route(run_dir, "02.0_t2_code_unit_map.yaml")
    element_spec = _load_yaml_route(run_dir, "03.0_t3_code_element_spec.yaml")
    global_spec = _load_yaml_route(run_dir, "04.0_t4_code_global_spec.yaml")
    if not all(isinstance(item, dict) for item in (unit_map, element_spec, global_spec)):
        for stage_id, stage_key in _DOWNSTREAM_STAGES.items():
            _write_status(
                route_dir,
                route_id="code_raw",
                stage_id=stage_id,
                stage_key=stage_key,
                availability="NOT_AVAILABLE",
                reason="code_raw T2/T3/T4 artifacts are not all available",
            )
        return

    if _route_availability(unit_map) != "AVAILABLE":
        reason = str((unit_map.get("route") or {}).get("reason") or "code_raw T2 route is unavailable")
        for stage_id, stage_key in _DOWNSTREAM_STAGES.items():
            _write_status(
                route_dir,
                route_id="code_raw",
                stage_id=stage_id,
                stage_key=stage_key,
                availability="NOT_AVAILABLE",
                reason=reason,
            )
        return

    template_spec = build_template_spec(
        l1_input_contract,
        _strip_route(unit_map),
        _strip_route(element_spec),
        _strip_route(global_spec),
    )
    template_spec["route"] = {
        "route_id": "code_raw",
        "stage_id": "T5",
        "stage_key": "t5_template_spec",
        "availability": "AVAILABLE",
        "origin": "route_replay_from_code_raw_t2_t3_t4",
    }
    write_yaml(route_dir / "05_template_spec.yaml", template_spec)

    if _route_equals_merged(run_dir, "code_raw"):
        _copy_if_exists(run_dir / "06.1_fillable_template.docx", route_dir / "06.1_fillable_template.docx")
        _copy_if_exists(run_dir / "06.2_build_manifest.json", route_dir / "06.2_build_manifest.json")
        _copy_if_exists(run_dir / "07_verification_report.json", route_dir / "07_verification_report.json")
        gap = _find_merged_gap(run_dir)
        if gap is not None:
            _copy_if_exists(gap, route_dir / "template_gap_report.json")
        else:
            _write_status(
                route_dir,
                route_id="code_raw",
                stage_id="POST_T6",
                stage_key="post_t6_template_gap",
                availability="NOT_AVAILABLE",
                reason="merged post-T6 gap report is not available for an equivalent code_raw route",
            )
        return

    reason = (
        "code_raw T5 is materialized, but isolated T6 replay requires a route-specific "
        "generation_model/action plan that is not captured in this run bundle"
    )
    for stage_id, stage_key in {
        "T6": "t6_fillable_template",
        "T7": "t7_verification_report",
        "POST_T6": "post_t6_template_gap",
    }.items():
        _write_status(
            route_dir,
            route_id="code_raw",
            stage_id=stage_id,
            stage_key=stage_key,
            availability="OUT_OF_SCOPE",
            reason=reason,
        )


def _materialize_ai_raw(*, run_dir: Path, route_root: Path) -> None:
    route_dir = route_root / "ai_raw"
    ai_routes = [
        _load_yaml_route(run_dir, "02.2_t2_ai_unit_observation.yaml"),
        _load_yaml_route(run_dir, "03.1_t3_ai_element_observation.yaml"),
        _load_yaml_route(run_dir, "04.1_t4_ai_layout_observation.yaml"),
    ]
    if any(_route_availability(route) == "AVAILABLE" for route in ai_routes if isinstance(route, dict)):
        availability = "OUT_OF_SCOPE"
        reason = (
            "ai_raw observations are available, but they are not a complete downstream "
            "T2/T3/T4 authority payload until AI-primary materialization is enabled"
        )
    else:
        availability = "NOT_AVAILABLE"
        reason = "ai_raw observation routes were not produced for this run"
    for stage_id, stage_key in _DOWNSTREAM_STAGES.items():
        _write_status(
            route_dir,
            route_id="ai_raw",
            stage_id=stage_id,
            stage_key=stage_key,
            availability=availability,
            reason=reason,
        )


def _write_status(
    route_dir: Path,
    *,
    route_id: str,
    stage_id: str,
    stage_key: str,
    availability: str,
    reason: str,
) -> None:
    write_json(
        route_dir / f"{stage_id.lower()}_route_status.json",
        {
            "artifact_type": "template_generation_route_stage_status",
            "artifact_version": "1.0",
            "route": {
                "route_id": route_id,
                "stage_id": stage_id,
                "stage_key": stage_key,
                "availability": availability,
                "origin": "route_replay_contract",
                "reason": reason,
            },
            "reason": reason,
        },
    )


def _route_equals_merged(run_dir: Path, route_id: str) -> bool:
    pairs = {
        "code_raw": [
            ("02.0_t2_code_unit_map.yaml", "02.3_t2_merged_unit_map.yaml"),
            ("03.0_t3_code_element_spec.yaml", "03.2_t3_merged_element_spec.yaml"),
            ("04.0_t4_code_global_spec.yaml", "04.2_t4_merged_global_spec.yaml"),
        ]
    }.get(route_id, [])
    if not pairs:
        return False
    for left_name, right_name in pairs:
        left = _load_yaml_route(run_dir, left_name)
        right = _load_yaml_route(run_dir, right_name)
        if not isinstance(left, dict) or not isinstance(right, dict):
            return False
        if sha256_json(_strip_route(left)) != sha256_json(_strip_route(right)):
            return False
    return True


def _find_merged_gap(run_dir: Path) -> Path | None:
    for path in (
        run_dir / "template_gap_report.json",
        run_dir / "artifacts" / "template_gap_report.json",
        run_dir.parent / "template_gap" / "template_gap_report.json",
        run_dir.parent / "template_gap" / "artifacts" / "template_gap_report.json",
        run_dir.parent.parent / "template_gap" / "artifacts" / "template_gap_report.json",
    ):
        if path.exists():
            return path
    return None


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _load_json_route(run_dir: Path, name: str) -> dict[str, Any] | None:
    path = run_dir / name
    if not path.exists():
        return None
    loaded = read_json(path)
    return loaded if isinstance(loaded, dict) else None


def _load_yaml_route(run_dir: Path, name: str) -> dict[str, Any] | None:
    path = run_dir / name
    if not path.exists():
        return None
    loaded = read_yaml(path)
    return loaded if isinstance(loaded, dict) else None


def _route_availability(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return "NOT_AVAILABLE"
    route = payload.get("route") or {}
    return str(route.get("availability") or "AVAILABLE")


def _strip_route(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "route"}


_DOWNSTREAM_STAGES = {
    "T5": "t5_template_spec",
    "T6": "t6_fillable_template",
    "T7": "t7_verification_report",
    "POST_T6": "post_t6_template_gap",
}
