"""Three-school T2 structural metrics harness (Phase 2 gate verification).

Runs the deterministic T2 backbone against the real hunan/nannong/pku source
templates and reports the metrics the Phase 2 hard gate cares about:

- unit count / other count / custom_unit count
- TOC coverage: how many toc-entry-like paragraphs land inside the `toc` unit
- toc_entry_like leakage into non-toc units (gate target: 0)

Usage:
    python scripts/t2_metrics.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from docfit.template_generation.artifacts import (
    build_unit_map,
    source_tree_from_document_facts,
)
from docfit.template_generation.source_tree import inspect_document_facts_docx
from docfit.template_generation.structure_candidates import (
    _is_toc_entry,
    build_template_structure_candidates,
)
from docfit.template_generation.t2_standard import (
    audit_unit_map_against_t2_standard,
    load_t2_unit_pagination_standard,
)

SCHOOLS = {
    "hunannongye": 20,
    "nannong-undergraduate": 25,
    "pku-graduate": 17,
}
CATALOG_UNIT_IDS = {"toc", "figure_list", "table_list"}


def _body_entries(source_tree: dict) -> list[dict]:
    return [
        item
        for item in source_tree.get("layers", {}).get("body_flow", [])
        if item.get("structure_layer") == "body_flow" and item.get("text")
    ]


def _seq_to_unit(units: list[dict]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for unit in units:
        for ref in unit.get("source_seq_refs", []) or []:
            try:
                mapping[int(ref)] = str(unit.get("unit_id"))
            except (TypeError, ValueError):
                continue
    return mapping


def metrics_for(school: str) -> dict:
    docx = REPO / "inputs" / "targets" / school / "raw" / "source_template.docx"
    document_facts = inspect_document_facts_docx(docx)
    source_tree = source_tree_from_document_facts(document_facts)
    candidates = build_template_structure_candidates(source_tree)
    unit_map = build_unit_map(document_facts, candidates)
    units = candidates["units"]
    entries = _body_entries(source_tree)
    seq_to_unit = _seq_to_unit(units)

    toc_entry_seqs = [
        int(e["source_seq"])
        for e in entries
        if e.get("source_seq") is not None and _is_toc_entry(e)
    ]
    in_catalog = sum(1 for s in toc_entry_seqs if seq_to_unit.get(s) in CATALOG_UNIT_IDS)
    leak = sum(
        1
        for s in toc_entry_seqs
        if seq_to_unit.get(s) not in (None, *CATALOG_UNIT_IDS)
    )

    unit_ids = [u.get("unit_id") for u in units]
    metrics = {
        "school": school,
        "units": len(units),
        "other": sum(1 for u in unit_ids if u == "other"),
        "custom": sum(1 for u in unit_ids if str(u).startswith("custom:")),
        "toc_entries_total": len(toc_entry_seqs),
        "toc_entries_in_catalog": in_catalog,
        "toc_leak_nontoc": leak,
        "has_toc_unit": "toc" in unit_ids,
        "open_questions": len(candidates.get("open_questions", []) or []),
    }
    standard = load_t2_unit_pagination_standard(REPO, school)
    metrics["standard_audit"] = audit_unit_map_against_t2_standard(unit_map, standard)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--standard-gate",
        action="store_true",
        help="Also print the signed T2 standard audit for unit_map.",
    )
    args = parser.parse_args()
    if args.standard_gate:
        _print_standard_gate_metrics()
        return
    _print_toc_metrics()


def _print_toc_metrics() -> None:
    header = (
        f"{'school':<24} {'units':>5} {'other':>5} {'custom':>6} "
        f"{'cat_in/exp':>12} {'leak':>5} {'toc?':>5} {'oq':>4} gate"
    )
    print(header)
    print("-" * len(header))
    for school, expected in SCHOOLS.items():
        m = metrics_for(school)
        toc_col = f"{m['toc_entries_in_catalog']}/{expected}"
        toc_ok = m["toc_entries_in_catalog"] >= expected
        gate = "PASS" if (toc_ok and m["toc_leak_nontoc"] == 0) else "FAIL"
        print(
            f"{school:<24} {m['units']:>5} {m['other']:>5} {m['custom']:>6} "
            f"{toc_col:>12} {m['toc_leak_nontoc']:>5} "
            f"{str(m['has_toc_unit']):>5} {m['open_questions']:>4}  {gate}"
        )


def _print_standard_gate_metrics() -> None:
    header = (
        f"{'school':<24} {'units':>5} {'custom':>6} {'missing':>7} "
        f"{'unexpected':>10} {'order?':>7} {'audit':>7} {'gate':>13}"
    )
    print(header)
    print("-" * len(header))
    for school in SCHOOLS:
        m = metrics_for(school)
        audit = m["standard_audit"]
        print(
            f"{school:<24} {m['units']:>5} {m['custom']:>6} "
            f"{len(audit['missing_unit_ids']):>7} "
            f"{len(audit['unexpected_unit_ids']):>10} "
            f"{str(audit['unit_order_matches']):>7} "
            f"{audit['audit_status']:>7} {audit['gate_status']:>13}"
        )
        if audit["audit_status"] != "PASS":
            _print_audit_details(audit)


def _print_audit_details(audit: dict) -> None:
    missing = audit.get("missing_unit_ids") or []
    unexpected = audit.get("unexpected_unit_ids") or []
    if missing:
        print(f"  missing: {', '.join(missing)}")
    if unexpected:
        print(f"  unexpected: {', '.join(unexpected)}")


if __name__ == "__main__":
    main()
