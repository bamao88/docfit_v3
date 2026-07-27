"""T2 page-native AI contract and deterministic downstream materialization.

The model owns only the semantic page grouping.  This module owns strict shape
validation, complete-page coverage, page-to-L1 binding, and the fixed page
policy required by downstream stages.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

from docfit.core.io import now_iso, sha256_file
from docfit.template_generation.final_results import (
    AVAILABLE,
    FinalStageResult,
    candidate_ref,
    publish_final_stage_result,
)


T2_AI_SCHEMA_VERSION = "t2-page-units-1.0"
T2_PROMPT_CONTRACT_VERSION = "t2-page-units-prompt-1.0"

_UNIT_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_TOP_LEVEL_KEYS = {"units"}
_UNIT_KEYS = {"unit_id", "unit_name", "boundary"}
_BOUNDARY_KEYS = {"start_page", "end_page"}


class T2AIContractError(ValueError):
    """The T2 AI output or its required render binding is not publishable."""


def materialize_t2_ai_observation(
    raw_payload: dict[str, Any],
    *,
    packet: dict[str, Any],
    model: str = "replay",
) -> dict[str, Any]:
    """Validate the exact AI payload and wrap it as the sole T2 candidate."""

    page_count = require_t2_page_packet(packet)
    units = _validate_ai_units(raw_payload, page_count=page_count)
    return {
        "artifact_type": "ai_unit_observation",
        "schema_version": T2_AI_SCHEMA_VERSION,
        "prompt_contract_version": T2_PROMPT_CONTRACT_VERSION,
        "stage": "t2",
        "source_render_hash": packet.get("source_render_hash"),
        "input_contract_hash": packet.get("input_contract_hash"),
        "model": model,
        "created_at": now_iso(),
        "units": units,
        "validation": {
            "page_count": page_count,
            "complete_page_coverage": True,
            "non_overlapping": True,
            "contiguous": True,
            "unique_unit_ids": True,
        },
    }


def materialize_t2_final_unit_map(
    observation: dict[str, Any],
    *,
    packet: dict[str, Any],
) -> dict[str, Any]:
    """Bind validated page ranges to L1 rows and derive the fixed page policy."""

    page_count = require_t2_page_packet(packet)
    units = _validate_ai_units(
        {"units": observation.get("units")},
        page_count=page_count,
    )
    rows = _ordered_packet_rows(packet, page_count=page_count)
    pages_by_seq: dict[int, set[int]] = {}
    for row in rows:
        source_seq = _as_int(row.get("source_seq"))
        page_no = _as_int(row.get("page_no"))
        if source_seq is None or page_no is None:
            continue
        pages_by_seq.setdefault(source_seq, set()).add(page_no)

    owner_by_page: dict[int, int] = {}
    for unit_index, unit in enumerate(units):
        boundary = unit["boundary"]
        for page_no in range(boundary["start_page"], boundary["end_page"] + 1):
            owner_by_page[page_no] = unit_index

    for source_seq, page_nos in pages_by_seq.items():
        owners = {owner_by_page[page_no] for page_no in page_nos}
        if len(owners) > 1:
            raise T2AIContractError(
                "one L1 body node spans multiple T2 page groups: "
                f"source_seq={source_seq}, pages={sorted(page_nos)}"
            )

    materialized_units: list[dict[str, Any]] = []
    for index, unit in enumerate(units, start=1):
        start_page = unit["boundary"]["start_page"]
        end_page = unit["boundary"]["end_page"]
        unit_rows = [
            row
            for row in rows
            if (
                (page_no := _as_int(row.get("page_no"))) is not None
                and start_page <= page_no <= end_page
            )
        ]
        source_seq_refs = _unique_ints(
            row.get("source_seq") for row in unit_rows
        )
        source_refs = _unique_strings(
            row.get("source_ref") for row in unit_rows
        )
        source_seq_range = (
            {"start": source_seq_refs[0], "end": source_seq_refs[-1]}
            if source_seq_refs
            else {}
        )
        materialized_units.append(
            {
                "unit_id": unit["unit_id"],
                "unit_name": unit["unit_name"],
                "order": index,
                "boundary": deepcopy(unit["boundary"]),
                "page_refs": [
                    f"page:{page_no}"
                    for page_no in range(start_page, end_page + 1)
                ],
                "source_seq_refs": source_seq_refs,
                "source_refs": source_refs,
                "source_seq_range": source_seq_range,
                "page_policy": {
                    "start": "document_start" if index == 1 else "new_page",
                    "scope": "page_range_exclusive",
                },
            }
        )

    return {
        "artifact_type": "unit_map",
        "artifact_version": "3.0",
        "created_at": now_iso(),
        "source_render_hash": packet.get("source_render_hash"),
        "page_count": page_count,
        "units": materialized_units,
        "flags": [],
        "open_questions": [],
    }


def publish_t2_ai_final(
    observation: dict[str, Any],
    *,
    packet: dict[str, Any],
) -> FinalStageResult:
    """Publish the only production T2 final from a validated AI observation."""

    unit_map = materialize_t2_final_unit_map(observation, packet=packet)
    return publish_final_stage_result(
        unit_map,
        stage_id="T2",
        artifact_type="unit_map",
        artifact_name="02_unit_map.yaml",
        availability=AVAILABLE,
        producer_mode="ai",
        selected_from=[
            candidate_ref(
                observation,
                route_id="ai_raw",
                artifact="02.2_t2_ai_unit_observation.yaml",
            )
        ],
        input_refs={
            "l1": {
                "stage_id": "L1",
                "artifact": "01.5_l1_input_contract.json",
                "sha256": packet.get("input_contract_hash"),
                "availability": AVAILABLE,
            }
        },
    )


def require_t2_page_packet(packet: dict[str, Any]) -> int:
    """Require a complete real-render packet because pages are T2 authority."""

    errors: list[str] = []
    if packet.get("render_status") != "real_render":
        errors.append(
            "T2 requires render_status=real_render; projection or missing render is invalid"
        )
    render_artifacts = packet.get("render_artifacts", {}) or {}
    page_count = _as_int(render_artifacts.get("page_count"))
    if page_count is None or page_count < 1:
        errors.append("T2 requires a positive real-render page_count")
        page_count = 0

    images_by_page: dict[int, dict[str, Any]] = {}
    duplicate_image_pages: set[int] = set()
    for image in render_artifacts.get("clean_page_images", []) or []:
        if not isinstance(image, dict):
            continue
        page_no = _as_int(image.get("page_no"))
        if page_no is not None:
            if page_no in images_by_page:
                duplicate_image_pages.add(page_no)
            images_by_page[page_no] = image
    expected_pages = set(range(1, page_count + 1))
    if set(images_by_page) != expected_pages:
        errors.append(
            "T2 clean page images must cover every rendered page exactly once: "
            f"expected={sorted(expected_pages)}, actual={sorted(images_by_page)}"
        )
    if duplicate_image_pages:
        errors.append(
            "T2 clean page images contain duplicate page entries: "
            f"pages={sorted(duplicate_image_pages)}"
        )
    missing_image_files = [
        page_no
        for page_no, image in images_by_page.items()
        if not Path(str(image.get("path") or "")).is_file()
    ]
    if missing_image_files:
        errors.append(
            f"T2 clean page image files are missing for pages {sorted(missing_image_files)}"
        )
    image_hash_errors: list[str] = []
    for page_no, image in sorted(images_by_page.items()):
        image_path = Path(str(image.get("path") or ""))
        if not image_path.is_file():
            continue
        declared_hash = str(image.get("sha256") or "")
        if not declared_hash:
            image_hash_errors.append(f"page={page_no}: missing sha256")
            continue
        actual_hash = sha256_file(image_path)
        if declared_hash != actual_hash:
            image_hash_errors.append(
                f"page={page_no}: declared={declared_hash}, actual={actual_hash}"
            )
    if image_hash_errors:
        errors.append(
            "T2 clean page image hashes are invalid: "
            + "; ".join(image_hash_errors)
        )

    seen_seq_page: set[tuple[int, int]] = set()
    for index, row in enumerate(packet.get("page_text_index", []) or []):
        if not isinstance(row, dict):
            continue
        if not is_t2_page_body_row(row):
            continue
        source_seq = _as_int(row.get("source_seq"))
        page_no = _as_int(row.get("page_no"))
        if source_seq is None:
            continue
        binding_status = str(row.get("render_binding_status") or "")
        if not (
            binding_status in {"exact", "prefix"}
            or binding_status.startswith("inferred_")
        ):
            errors.append(
                "T2 page binding is unresolved for "
                f"source_seq={source_seq}: status={binding_status or 'missing'}"
            )
        if page_no is None or page_no not in expected_pages:
            errors.append(
                f"T2 page binding missing or out of range for source_seq={source_seq}"
            )
            continue
        identity = (source_seq, page_no)
        if identity in seen_seq_page:
            errors.append(
                "T2 page_text_index contains duplicate source/page binding at "
                f"row {index}: source_seq={source_seq}, page={page_no}"
            )
        seen_seq_page.add(identity)

    if errors:
        raise T2AIContractError("; ".join(errors))
    return page_count


def _validate_ai_units(
    raw_payload: dict[str, Any],
    *,
    page_count: int,
) -> list[dict[str, Any]]:
    if not isinstance(raw_payload, dict):
        raise T2AIContractError("T2 AI output must be one JSON object")
    unexpected_top = set(raw_payload) - _TOP_LEVEL_KEYS
    missing_top = _TOP_LEVEL_KEYS - set(raw_payload)
    if unexpected_top or missing_top:
        raise T2AIContractError(
            "T2 AI output must contain only top-level field 'units': "
            f"missing={sorted(missing_top)}, unexpected={sorted(unexpected_top)}"
        )
    raw_units = raw_payload.get("units")
    if not isinstance(raw_units, list) or not raw_units:
        raise T2AIContractError("T2 AI output units must be a non-empty array")

    units: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    expected_start = 1
    for index, raw_unit in enumerate(raw_units, start=1):
        if not isinstance(raw_unit, dict):
            raise T2AIContractError(f"T2 unit {index} must be an object")
        unexpected = set(raw_unit) - _UNIT_KEYS
        missing = _UNIT_KEYS - set(raw_unit)
        if unexpected or missing:
            raise T2AIContractError(
                f"T2 unit {index} fields invalid: "
                f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
            )
        unit_id = str(raw_unit.get("unit_id") or "").strip()
        unit_name = str(raw_unit.get("unit_name") or "").strip()
        if not _UNIT_ID_RE.fullmatch(unit_id):
            raise T2AIContractError(
                f"T2 unit {index} unit_id must be lower snake_case: {unit_id!r}"
            )
        if unit_id in seen_ids:
            raise T2AIContractError(f"T2 unit_id must be unique: {unit_id!r}")
        if not unit_name:
            raise T2AIContractError(f"T2 unit {index} unit_name must be non-empty")

        boundary = raw_unit.get("boundary")
        if not isinstance(boundary, dict):
            raise T2AIContractError(f"T2 unit {index} boundary must be an object")
        unexpected_boundary = set(boundary) - _BOUNDARY_KEYS
        missing_boundary = _BOUNDARY_KEYS - set(boundary)
        if unexpected_boundary or missing_boundary:
            raise T2AIContractError(
                f"T2 unit {index} boundary fields invalid: "
                f"missing={sorted(missing_boundary)}, "
                f"unexpected={sorted(unexpected_boundary)}"
            )
        start_page = _strict_int(boundary.get("start_page"))
        end_page = _strict_int(boundary.get("end_page"))
        if start_page is None or end_page is None:
            raise T2AIContractError(
                f"T2 unit {index} page boundary values must be integers"
            )
        if not (1 <= start_page <= end_page <= page_count):
            raise T2AIContractError(
                f"T2 unit {index} boundary is outside rendered pages: "
                f"{start_page}-{end_page}, page_count={page_count}"
            )
        if start_page != expected_start:
            relation = "overlap" if start_page < expected_start else "gap"
            raise T2AIContractError(
                f"T2 page ranges must be contiguous without {relation}: "
                f"unit {index} starts at {start_page}, expected {expected_start}"
            )
        expected_start = end_page + 1
        seen_ids.add(unit_id)
        units.append(
            {
                "unit_id": unit_id,
                "unit_name": unit_name,
                "boundary": {
                    "start_page": start_page,
                    "end_page": end_page,
                },
            }
        )
    if expected_start != page_count + 1:
        raise T2AIContractError(
            "T2 page ranges must cover the final rendered page: "
            f"covered_through={expected_start - 1}, page_count={page_count}"
        )
    return units


def _ordered_packet_rows(
    packet: dict[str, Any],
    *,
    page_count: int,
) -> list[dict[str, Any]]:
    rows = [
        row
        for row in packet.get("page_text_index", []) or []
        if isinstance(row, dict)
        and is_t2_page_body_row(row)
        and _as_int(row.get("source_seq")) is not None
    ]
    invalid = [
        row.get("source_seq")
        for row in rows
        if (
            (page_no := _as_int(row.get("page_no"))) is None
            or page_no < 1
            or page_no > page_count
        )
    ]
    if invalid:
        raise T2AIContractError(
            f"T2 cannot bind L1 rows without valid page_no: source_seq={invalid}"
        )
    return sorted(
        rows,
        key=lambda row: (
            _as_int(row.get("source_seq")) or 0,
            _as_int(row.get("page_no")) or 0,
        ),
    )


def is_t2_page_body_row(row: dict[str, Any]) -> bool:
    """Return whether an L1 row belongs to T2's page-grouped body content."""

    if str(row.get("structure_layer") or "") == "header_footer":
        return False
    if (
        str(row.get("kind") or "") == "content_control"
        and str(row.get("text") or "").startswith("sdt:slot_")
        and row.get("bbox") is None
    ):
        return False
    return True


def _strict_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return None


def _unique_ints(values: Any) -> list[int]:
    result: list[int] = []
    for value in values:
        parsed = _as_int(value)
        if parsed is not None and parsed not in result:
            result.append(parsed)
    return result


def _unique_strings(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result
