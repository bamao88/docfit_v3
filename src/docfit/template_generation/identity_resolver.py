from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.core.io import sha256_file


class L1IdentityResolver:
    def __init__(self, l1_input_contract: dict[str, Any]) -> None:
        self._l1 = l1_input_contract
        self._source_by_seq = {
            int(item["source_seq"]): item
            for item in l1_input_contract.get("source_text_index", []) or []
            if isinstance(item, dict) and item.get("source_seq") is not None
        }
        self._source_refs = {
            str(item.get("source_ref"))
            for item in l1_input_contract.get("source_text_index", []) or []
            if isinstance(item, dict) and item.get("source_ref")
        }
        self._source_refs.update(
            _collect_source_refs(l1_input_contract.get("source_object_index", []))
        )
        self._source_refs.update(
            _collect_source_refs(l1_input_contract.get("layout_fact_index", {}))
        )
        self._raw_runs = {
            str(item.get("raw_run_id")): item
            for item in (l1_input_contract.get("run_index", {}) or {}).get(
                "raw_runs", []
            )
            or []
            if isinstance(item, dict) and item.get("raw_run_id")
        }
        self._source_refs.update(
            str(item.get("source_ref"))
            for item in self._raw_runs.values()
            if item.get("source_ref")
        )

    def validate_source_package(self, source_docx: Path) -> dict[str, Any]:
        expected = str(
            self._l1.get("input_hashes", {}).get("source_template") or ""
        )
        observed = sha256_file(source_docx)
        return {
            "status": "PASS" if expected and expected == observed else "FAIL",
            "expected_source_hash": expected or None,
            "observed_source_hash": observed,
            "reason": None
            if expected and expected == observed
            else "source DOCX hash does not match sealed L1",
        }

    def validate_action(self, action: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        action_type = str(action.get("action_type") or "")
        source_ref = str(action.get("source_ref") or "")
        source_seq_refs = [
            int(value)
            for value in action.get("affected_source_seq_refs", []) or []
            if isinstance(value, int) or str(value).isdigit()
        ]
        raw_run_ids = [
            str(value)
            for value in action.get("affected_raw_run_ids", []) or []
            if value
        ]
        char_ranges = [
            item
            for item in action.get("affected_char_ranges", []) or []
            if isinstance(item, dict)
        ]

        source_optional = action_type in {"copy_source_docx", "ensure_body_slot"}
        if source_ref and not source_optional and not self._has_source_ref(source_ref):
            errors.append(f"source_ref is not bound in L1: {source_ref}")
        for source_seq in source_seq_refs:
            if source_seq not in self._source_by_seq:
                errors.append(f"source_seq is not bound in L1: {source_seq}")
        for raw_run_id in raw_run_ids:
            raw = self._raw_runs.get(raw_run_id)
            if raw is None:
                errors.append(f"raw_run_id is not bound in L1: {raw_run_id}")
                continue
            parent_seq_refs = list(raw.get("parent_source_seq_refs", []) or [])
            if not parent_seq_refs and raw.get("parent_source_seq") is not None:
                parent_seq_refs = [raw.get("parent_source_seq")]
            if source_seq_refs and not set(parent_seq_refs).intersection(source_seq_refs):
                errors.append(
                    f"raw_run_id parent source_seq mismatch: {raw_run_id} -> {parent_seq_refs}"
                )
        for char_range in char_ranges:
            raw_run_id = str(char_range.get("raw_run_id") or "")
            raw = self._raw_runs.get(raw_run_id)
            if raw is None:
                errors.append(f"char range raw_run_id is not bound in L1: {raw_run_id}")
                continue
            start = _as_int(char_range.get("start"))
            end = _as_int(char_range.get("end"))
            text = str(raw.get("text") or "")
            if start is None or end is None or start < 0 or end < start or end > len(text):
                errors.append(
                    f"char range is outside L1 raw run text: {raw_run_id}:{start}-{end}/{len(text)}"
                )
        return {
            "status": "PASS" if not errors else "FAIL",
            "action_id": action.get("action_id"),
            "action_type": action_type,
            "source_ref": source_ref or None,
            "source_seq_refs": source_seq_refs,
            "raw_run_ids": raw_run_ids,
            "char_ranges": char_ranges,
            "errors": errors,
        }

    def _has_source_ref(self, source_ref: str) -> bool:
        return source_ref in self._source_refs


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _collect_source_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        source_ref = value.get("source_ref")
        if source_ref:
            refs.add(str(source_ref))
        for item in value.values():
            refs.update(_collect_source_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_collect_source_refs(item))
    return refs
