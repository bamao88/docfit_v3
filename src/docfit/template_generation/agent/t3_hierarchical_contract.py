"""T3 hierarchical input validation, evidence projection and fact firewall."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

T3_STAGE_INPUT_VERSION = "t3-hierarchical-input-1.1"
_T3_FACT_DENY_KEYS = frozenset(
    {
        "policy",
        "role",
        "fill_source",
        "generated",
        "core_action",
        "result",
        "decision_status",
        "candidate_policy",
        "element_spec",
        "template_spec",
        "standards",
        "gold",
        "judge",
    }
)


def validate_t3_hierarchical_stage_input(
    artifact: Any,
) -> dict[str, Any]:
    """Validate identity, parent/child, coverage and acyclic-tree invariants."""

    errors: list[dict[str, str]] = []
    if not isinstance(artifact, dict):
        return {"valid": False, "errors": [_error("$", "artifact must be an object")]}
    if artifact.get("artifact_type") != "t3_hierarchical_stage_input":
        errors.append(_error("$.artifact_type", "unexpected artifact type"))
    if artifact.get("artifact_version") != T3_STAGE_INPUT_VERSION:
        errors.append(_error("$.artifact_version", "unsupported Stage Input version"))

    raw_nodes = artifact.get("nodes")
    if not isinstance(raw_nodes, list):
        return {"valid": False, "errors": errors + [_error("$.nodes", "nodes must be a list")]}
    nodes = [node for node in raw_nodes if isinstance(node, dict)]
    if len(nodes) != len(raw_nodes):
        errors.append(_error("$.nodes", "every node must be an object"))
    by_ref: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        ref = str(node.get("ref") or "")
        if not ref:
            errors.append(_error(f"$.nodes[{index}].ref", "node ref is required"))
            continue
        if ref in by_ref:
            errors.append(_error(f"$.nodes[{index}].ref", f"duplicate node ref: {ref}"))
            continue
        by_ref[ref] = node

    child_owner: dict[str, str] = {}
    for ref, node in by_ref.items():
        children = _strings(node.get("child_refs"))
        if len(children) != len(set(children)):
            errors.append(_error(f"$.nodes[{ref}].child_refs", "duplicate child refs"))
        for child_ref in children:
            child = by_ref.get(child_ref)
            if child is None:
                errors.append(_error(f"$.nodes[{ref}].child_refs", f"unknown child: {child_ref}"))
                continue
            if str(child.get("parent_ref") or "") != ref:
                errors.append(_error(f"$.nodes[{child_ref}].parent_ref", f"expected {ref}"))
            previous = child_owner.setdefault(child_ref, ref)
            if previous != ref:
                errors.append(_error(f"$.nodes[{child_ref}]", "node has multiple parents"))
        expected_leaf_refs = sorted(
            {
                leaf_ref
                for child_ref in children
                for leaf_ref in _strings((by_ref.get(child_ref) or {}).get("member_leaf_refs"))
            }
        )
        actual_leaf_refs = sorted(set(_strings(node.get("member_leaf_refs"))))
        if children and actual_leaf_refs != expected_leaf_refs:
            errors.append(
                _error(
                    f"$.nodes[{ref}].member_leaf_refs",
                    "member leaves do not equal the union of direct children",
                )
            )
        if not children and not actual_leaf_refs:
            errors.append(_error(f"$.nodes[{ref}].member_leaf_refs", "leaf has no atomic identity"))

    roots = artifact.get("unit_roots")
    if not isinstance(roots, list):
        errors.append(_error("$.unit_roots", "unit_roots must be a list"))
        roots = []
    root_refs: list[str] = []
    for index, root in enumerate(roots):
        ref = str(root.get("root_ref") or "") if isinstance(root, dict) else ""
        root_refs.append(ref)
        node = by_ref.get(ref)
        if node is None:
            errors.append(_error(f"$.unit_roots[{index}].root_ref", "root node is missing"))
        elif node.get("source_kind") != "unit" or node.get("parent_ref") is not None:
            errors.append(_error(f"$.unit_roots[{index}].root_ref", "root must be a parentless unit"))
    if len(root_refs) != len(set(root_refs)):
        errors.append(_error("$.unit_roots", "unit roots must be unique"))

    visit_state: dict[str, int] = {}

    def visit(ref: str) -> None:
        state = visit_state.get(ref, 0)
        if state == 1:
            errors.append(_error(f"$.nodes[{ref}]", "cycle detected"))
            return
        if state == 2:
            return
        visit_state[ref] = 1
        for child_ref in _strings((by_ref.get(ref) or {}).get("child_refs")):
            if child_ref in by_ref:
                visit(child_ref)
        visit_state[ref] = 2

    for root_ref in root_refs:
        if root_ref in by_ref:
            visit(root_ref)
    unreachable = sorted(set(by_ref) - set(visit_state))
    if unreachable:
        errors.append(_error("$.nodes", f"nodes are unreachable from unit roots: {unreachable[:8]}"))

    try:
        assert_t3_stage_input_clean(artifact)
    except ValueError as exc:
        errors.append(_error("$", str(exc)))
    return {"valid": not errors, "errors": errors}


def t3_node_evidence(
    artifact: dict[str, Any],
    *,
    target_ref: str,
) -> dict[str, Any]:
    """Project one complete current node plus direct-child routing summaries."""

    by_ref = {
        str(node.get("ref")): node
        for node in artifact.get("nodes", []) or []
        if isinstance(node, dict) and node.get("ref")
    }
    target = by_ref.get(target_ref)
    if target is None:
        raise KeyError(f"unknown T3 target_ref: {target_ref}")
    children = [by_ref[ref] for ref in _strings(target.get("child_refs"))]
    evidence = {
        "scope": "t3_hierarchical_node",
        "contract": deepcopy(artifact.get("contract") or {}),
        "tree_hash": artifact.get("tree_hash"),
        "target": {
            key: deepcopy(target.get(key))
            for key in (
                "ref",
                "source_kind",
                "parent_ref",
                "ancestor_refs",
                "source_refs",
                "source_seq_refs",
                "page_nos",
                "bbox_refs",
                "member_leaf_refs",
            )
        },
        "completeness": deepcopy(target.get("completeness") or {}),
        "facts": deepcopy(target.get("facts") or {}),
        "children": [_child_summary(child) for child in children],
        "context": deepcopy(target.get("context") or {}),
        "visual_evidence": deepcopy(target.get("visual_evidence") or []),
        "_visual_attachment_limit": len(target.get("visual_evidence") or []),
    }
    assert_t3_stage_input_clean(evidence)
    return evidence


def nodes_by_ref(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(node.get("ref")): node
        for node in artifact.get("nodes", []) or []
        if isinstance(node, dict) and node.get("ref")
    }


def _child_summary(node: dict[str, Any]) -> dict[str, Any]:
    facts = node.get("facts") or {}
    text = facts.get("text")
    if text is None and isinstance(facts.get("text_by_row"), list):
        text = "\n".join(str(value) for value in facts["text_by_row"])
    return {
        "ref": node.get("ref"),
        "source_kind": node.get("source_kind"),
        "source_seq_refs": deepcopy(node.get("source_seq_refs") or []),
        "page_nos": deepcopy(node.get("page_nos") or []),
        "child_count": len(node.get("child_refs") or []),
        "member_leaf_count": len(node.get("member_leaf_refs") or []),
        "text": str(text or ""),
        "completeness": deepcopy(node.get("completeness") or {}),
        "fact_summary": {
            key: deepcopy(value)
            for key, value in facts.items()
            if key not in {"text", "text_by_row", "ordered_text"}
        },
    }


def _strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value or "").strip()]


def _error(path: str, message: str) -> dict[str, str]:
    return {"path": path, "check_id": "C-T3-HIERARCHY", "message": message}


def assert_t3_stage_input_clean(value: Any, *, where: str = "$") -> None:
    """Allow the required T2 unit identity while rejecting T3/downstream policy."""

    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if key_text in _T3_FACT_DENY_KEYS or key_text.startswith("expected_"):
                raise ValueError(
                    f"T3 Stage Input leaked semantic field {key_text!r} at {where}"
                )
            assert_t3_stage_input_clean(item, where=f"{where}.{key_text}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_t3_stage_input_clean(item, where=f"{where}[{index}]")
