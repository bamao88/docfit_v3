"""T3 隔离评测的 gold-upstream 前置校验。

评测工具必须显式声明 T2 来自人工确认标准，并证明它与当前 packet 构成无重叠、无缺失的
精确分区；否则不能把结果称作 T3 准确率。
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from .packet import packet_source_seq_set


class T3GoldUpstreamError(ValueError):
    """T3 隔离评测的上游不满足人工 gold 契约。"""


_CANONICAL_T3_POLICIES = {
    "fixed",
    "template_default",
    "fill",
    "fixed",
    "generated",
    "instruction_remove",
}


def validate_t3_gold_upstream(
    ai_unit_observation: dict[str, Any],
    *,
    packet: dict[str, Any],
    human_confirmed: bool,
    gold_source: str,
    owned_structure_layers: set[str] | None = None,
    require_atomic_run_facts: bool = False,
    require_object_facts: bool = False,
) -> dict[str, Any]:
    if not human_confirmed:
        raise T3GoldUpstreamError("T3 stage evaluation requires human-confirmed T2 gold")
    if not str(gold_source or "").strip():
        raise T3GoldUpstreamError("T3 stage evaluation requires a traceable T2 gold source")
    items = [item for item in ai_unit_observation.get("items", []) if isinstance(item, dict)]
    refs = [
        int(value)
        for item in items
        for value in item.get("source_seq_refs", []) or []
        if not isinstance(value, bool) and str(value).isdigit()
    ]
    counts = Counter(refs)
    duplicates = sorted(seq for seq, count in counts.items() if count > 1)
    object_refs = [
        str(value)
        for item in items
        for value in item.get("source_ref_refs", []) or []
        if str(value or "").strip()
    ]
    object_counts = Counter(object_refs)
    duplicate_object_refs = sorted(
        source_ref for source_ref, count in object_counts.items() if count > 1
    )
    expected = _owned_packet_source_seq_set(
        packet,
        owned_structure_layers=owned_structure_layers,
    )
    observed = set(refs)
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    empty_units = [
        str(item.get("unit_id") or "")
        for item in items
        if not item.get("source_seq_refs") and not item.get("source_ref_refs")
    ]
    object_fact_audit = _object_fact_audit(packet, set(object_refs))
    if (
        duplicates
        or duplicate_object_refs
        or missing
        or extra
        or empty_units
        or (require_object_facts and object_fact_audit["gaps"])
    ):
        raise T3GoldUpstreamError(
            "T2 gold must exactly partition the current T3 packet: "
            f"duplicates={duplicates}, duplicate_object_refs={duplicate_object_refs}, "
            f"missing={missing}, extra={extra}, empty_units={empty_units}, "
            f"object_gaps={object_fact_audit['gaps'][:30]}"
        )
    atomic_run_audit = _atomic_run_fact_audit(packet, expected)
    if require_atomic_run_facts and atomic_run_audit["gaps"]:
        raise T3GoldUpstreamError(
            "T3 gold input requires complete atomic run facts: "
            f"gaps={atomic_run_audit['gaps'][:30]}"
        )
    return {
        "status": "PASS",
        "human_confirmed": True,
        "gold_source": gold_source,
        "unit_count": len(items),
        "source_seq_count": len(refs),
        "exact_packet_partition": True,
        "owned_structure_layers": sorted(owned_structure_layers or []),
        "atomic_run_facts_required": require_atomic_run_facts,
        "atomic_run_fact_count": atomic_run_audit["run_fact_count"],
        "atomic_run_facts_complete": not atomic_run_audit["gaps"],
        "object_facts_required": require_object_facts,
        "object_fact_count": object_fact_audit["object_fact_count"],
        "object_facts_complete": not object_fact_audit["gaps"],
        "source_ref_object_count": len(object_refs),
    }


def build_t3_gold_upstream(
    t2_standard: dict[str, Any],
    *,
    packet: dict[str, Any],
    gold_source: str,
    source_template_hash: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Materialize a T3-only T2 input directly from a signed T2 standard."""

    if str(t2_standard.get("stage_id") or "").upper() != "T2":
        raise T3GoldUpstreamError("T3 gold input requires a T2 stage standard")
    if str(t2_standard.get("standard_state") or "") != "signed_active":
        raise T3GoldUpstreamError("T3 gold input requires standard_state=signed_active")
    expected_source_hash = str(
        (t2_standard.get("accepted_source_facts", {}) or {}).get(
            "template_docx_sha256"
        )
        or (t2_standard.get("review_metadata", {}) or {}).get(
            "source_docx_sha256"
        )
        or ""
    )
    if not expected_source_hash or expected_source_hash != str(source_template_hash or ""):
        raise T3GoldUpstreamError(
            "T3 gold input source template hash does not match the signed T2 standard: "
            f"expected={expected_source_hash or 'missing'}, "
            f"actual={source_template_hash or 'missing'}"
        )

    expected = t2_standard.get("expected", {}) or {}
    units = [item for item in expected.get("units", []) or [] if isinstance(item, dict)]
    unit_order = [str(item) for item in expected.get("unit_order", []) or []]
    actual_order = [str(item.get("unit_id") or "") for item in units]
    if not unit_order or actual_order != unit_order:
        raise T3GoldUpstreamError(
            "signed T2 standard unit_order must exactly match expected.units: "
            f"unit_order={unit_order}, units={actual_order}"
        )

    items: list[dict[str, Any]] = []
    for order, unit in enumerate(units, start=1):
        boundary = unit.get("boundary", {}) or {}
        source_seq_range = boundary.get("source_seq_range")
        refs: list[int] = []
        source_ref_refs: list[str] = []
        if isinstance(source_seq_range, dict):
            start = _positive_int(source_seq_range.get("start"))
            end = _positive_int(source_seq_range.get("end"))
            if start is None or end is None or start > end:
                raise T3GoldUpstreamError(
                    "signed T2 standard has an invalid source_seq_range: "
                    f"unit_id={unit.get('unit_id')}, range={source_seq_range}"
                )
            refs = list(range(start, end + 1))
        elif boundary.get("source_ref_range"):
            source_ref_refs = _source_ref_range_refs(
                boundary.get("source_ref_range"),
                unit_id=str(unit.get("unit_id") or ""),
            )
        items.append(
            {
                "unit_id": unit.get("unit_id"),
                "order": order,
                "source_seq_refs": refs,
                "source_ref_refs": source_ref_refs,
                "source_ref_range": deepcopy(boundary.get("source_ref_range")),
                "confidence": "high",
                "gold_origin": "signed_t2_standard",
            }
        )
    observation = {
        "artifact_type": "t3_gold_unit_observation",
        "artifact_version": "1.0",
        "source_render_hash": packet.get("source_render_hash"),
        "input_contract_hash": packet.get("input_contract_hash"),
        "standard_id": t2_standard.get("standard_id"),
        "items": items,
    }
    audit = validate_t3_gold_upstream(
        observation,
        packet=packet,
        human_confirmed=True,
        gold_source=gold_source,
        owned_structure_layers={"body_flow"},
        require_atomic_run_facts=True,
        require_object_facts=True,
    )
    audit.update(
        {
            "standard_id": t2_standard.get("standard_id"),
            "standard_state": t2_standard.get("standard_state"),
            "source_template_hash": source_template_hash,
            "source_template_hash_matches": True,
        }
    )
    return observation, audit


def evaluate_t3_gold_accuracy(
    observation: dict[str, Any],
    *,
    t3_standard: dict[str, Any],
    packet: dict[str, Any],
    gold_unit_observation: dict[str, Any],
    gold_input_audit: dict[str, Any],
    source_template_hash: str | None,
) -> dict[str, Any]:
    """Score only T3 keep/fill/delete decisions after the gold-input gate passes."""

    if gold_input_audit.get("status") != "PASS":
        raise T3GoldUpstreamError(
            "T3 accuracy requires a passing gold input audit"
        )
    for hash_field in ("source_render_hash", "input_contract_hash"):
        expected_hash = packet.get(hash_field)
        observed_hash = observation.get(hash_field)
        if not expected_hash or observed_hash != expected_hash:
            raise T3GoldUpstreamError(
                "T3 observation is not bound to the audited gold input: "
                f"field={hash_field}, expected={expected_hash or 'missing'}, "
                f"actual={observed_hash or 'missing'}"
            )
    if str(t3_standard.get("stage_id") or "").upper() != "T3":
        raise T3GoldUpstreamError("T3 accuracy requires a T3 stage standard")
    if str(t3_standard.get("standard_state") or "") != "signed_active":
        raise T3GoldUpstreamError(
            "T3 accuracy requires standard_state=signed_active"
        )
    expected_source_hash = str(
        (t3_standard.get("accepted_source_facts", {}) or {}).get(
            "template_docx_sha256"
        )
        or (t3_standard.get("review_metadata", {}) or {}).get(
            "source_docx_sha256"
        )
        or ""
    )
    if expected_source_hash != str(source_template_hash or ""):
        raise T3GoldUpstreamError(
            "T3 accuracy source template hash does not match the signed T3 standard: "
            f"expected={expected_source_hash or 'missing'}, "
            f"actual={source_template_hash or 'missing'}"
        )

    (
        allowed_actions,
        policy_to_action,
        gold_source_field,
        unknown_action,
        unknown_execution_fallback,
    ) = _core_action_contract(t3_standard)

    owned_rows = [
        item
        for item in packet.get("page_text_index", []) or []
        if isinstance(item, dict)
        and str(item.get("structure_layer") or "") == "body_flow"
    ]
    owned_raw_ids = {
        str(raw_run_id)
        for row in owned_rows
        for raw_run_id in row.get("raw_run_ids", []) or []
        if raw_run_id
    }
    unit_by_source_seq = {
        int(source_seq): str(item.get("unit_id") or "")
        for item in gold_unit_observation.get("items", []) or []
        if isinstance(item, dict)
        for source_seq in item.get("source_seq_refs", []) or []
    }
    expected_rows = [
        item
        for item in (t3_standard.get("expected", {}) or {}).get(
            "run_span_ledger", []
        )
        or []
        if isinstance(item, dict)
        and str(item.get("raw_run_id") or "") in owned_raw_ids
    ]
    raw_id_counts = Counter(str(item.get("raw_run_id") or "") for item in expected_rows)
    duplicate_raw_ids = sorted(
        raw_run_id
        for raw_run_id, count in raw_id_counts.items()
        if raw_run_id and count > 1
    )
    if duplicate_raw_ids:
        raise T3GoldUpstreamError(
            "signed T3 run ledger must contain one gold row per raw run: "
            f"duplicates={duplicate_raw_ids[:100]}"
        )
    expected_by_raw = {
        str(item.get("raw_run_id") or ""): item for item in expected_rows
    }
    missing_ledger_raw_ids = sorted(owned_raw_ids - set(expected_by_raw))
    if missing_ledger_raw_ids:
        raise T3GoldUpstreamError(
            "signed T3 run ledger does not cover every T3-owned raw run: "
            f"missing={missing_ledger_raw_ids[:100]}"
        )

    invalid_gold_actions = [
        {
            "raw_run_id": raw_run_id,
            "gold_value": expectation.get(
                "expected_action",
                expectation.get(gold_source_field),
            ),
        }
        for raw_run_id, expectation in expected_by_raw.items()
        if _t3_core_action(
            expectation.get("expected_action", expectation.get(gold_source_field)),
            policy_to_action=policy_to_action,
            allowed_actions=set(allowed_actions),
            unknown_action=unknown_action,
        )
        not in {*allowed_actions, unknown_action}
    ]
    if invalid_gold_actions:
        raise T3GoldUpstreamError(
            "signed T3 run ledger contains unmapped core actions: "
            f"rows={invalid_gold_actions[:100]}"
        )

    unknown_by_raw = {
        raw_run_id: expectation
        for raw_run_id, expectation in expected_by_raw.items()
        if _t3_core_action(
            expectation.get("expected_action", expectation.get(gold_source_field)),
            policy_to_action=policy_to_action,
            allowed_actions=set(allowed_actions),
            unknown_action=unknown_action,
        )
        == unknown_action
    }
    scored_expected_by_raw = {
        raw_run_id: expectation
        for raw_run_id, expectation in expected_by_raw.items()
        if raw_run_id not in unknown_by_raw
    }

    claims = _t3_prediction_claims(observation)
    expected_count = len(scored_expected_by_raw)
    covered_count = 0
    covered_unknown_count = 0
    correct_action_count = 0
    conflict_count = 0
    predicted_unknown_count = 0
    expected_action_counts: Counter[str] = Counter()
    predicted_action_counts: Counter[str] = Counter()
    correct_action_counts: Counter[str] = Counter()
    unit_counts: dict[str, Counter[str]] = {}
    false_delete_raw_ids: list[str] = []
    true_delete_count = 0
    expected_delete_count = 0

    for raw_run_id, expectation in scored_expected_by_raw.items():
        expected_action = _t3_core_action(
            expectation.get("expected_action", expectation.get(gold_source_field)),
            policy_to_action=policy_to_action,
            allowed_actions=set(allowed_actions),
            unknown_action=unknown_action,
        )
        expected_unit = str(expectation.get("unit_id") or "") or unit_by_source_seq.get(
            _positive_int(expectation.get("source_seq")) or -1,
            "",
        )
        expected_action_counts[expected_action] += 1
        if expected_action == "delete":
            expected_delete_count += 1
        raw_claims = claims.get(raw_run_id, [])
        actions = {
            _t3_core_action(
                item.get("policy"),
                policy_to_action=policy_to_action,
                allowed_actions=set(allowed_actions),
                unknown_action=unknown_action,
            )
            for item in raw_claims
            if item.get("policy")
        }
        actions.discard("")
        unit_metrics = unit_counts.setdefault(expected_unit, Counter())
        unit_metrics["expected"] += 1
        if raw_claims:
            covered_count += 1
            unit_metrics["covered"] += 1
        if len(actions) > 1:
            conflict_count += 1
            unit_metrics["conflicted"] += 1
        predicted_action = next(iter(actions)) if len(actions) == 1 else ""
        if predicted_action in allowed_actions:
            predicted_action_counts[predicted_action] += 1
        elif predicted_action == unknown_action:
            predicted_unknown_count += 1
        action_correct = predicted_action == expected_action
        if action_correct:
            correct_action_count += 1
            correct_action_counts[expected_action] += 1
            unit_metrics["action_correct"] += 1
        if "delete" in actions:
            if expected_action == "delete":
                true_delete_count += 1
            else:
                false_delete_raw_ids.append(raw_run_id)

    # unknown gold 不进入 keep/fill/delete 准确率分母，但它仍然受删除安全门约束。
    # 任何对 unknown run 的 delete 预测都是违反“不确定则保留”原则。
    for raw_run_id in unknown_by_raw:
        raw_claims = claims.get(raw_run_id, [])
        if raw_claims:
            covered_unknown_count += 1
        actions = {
            _t3_core_action(
                item.get("policy"),
                policy_to_action=policy_to_action,
                allowed_actions=set(allowed_actions),
                unknown_action=unknown_action,
            )
            for item in raw_claims
            if item.get("policy")
        }
        if "delete" in actions:
            false_delete_raw_ids.append(raw_run_id)

    per_action: dict[str, dict[str, Any]] = {}
    f1_values: list[float] = []
    for action in allowed_actions:
        expected_action_count = expected_action_counts[action]
        predicted_action_count = predicted_action_counts[action]
        correct_count = correct_action_counts[action]
        precision = _safe_ratio(correct_count, predicted_action_count)
        recall = _safe_ratio(correct_count, expected_action_count)
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        f1_values.append(f1)
        per_action[action] = {
            "expected": expected_action_count,
            "predicted": predicted_action_count,
            "correct": correct_count,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    per_unit = {
        unit_id: {
            "expected": values["expected"],
            "covered": values["covered"],
            "conflicted": values["conflicted"],
            "action_accuracy": round(
                _safe_ratio(values["action_correct"], values["expected"]),
                4,
            ),
        }
        for unit_id, values in sorted(unit_counts.items())
    }
    predicted_delete_count = true_delete_count + len(false_delete_raw_ids)
    return {
        "artifact_type": "t3_gold_accuracy_report",
        "artifact_version": "2.1",
        "standard_id": t3_standard.get("standard_id"),
        "primary_metric": "exact_action_accuracy",
        "source_template_hash": source_template_hash,
        "input_contract_hash": packet.get("input_contract_hash"),
        "source_render_hash": packet.get("source_render_hash"),
        "scope": {
            "accuracy_level": "core_action",
            "allowed_actions": allowed_actions,
            "gold_source_field": gold_source_field,
            "policy_to_action": policy_to_action,
            "unknown_action": unknown_action,
            "unknown_scoring": "excluded_from_primary",
            "unknown_execution_fallback": unknown_execution_fallback,
            "uncertain_delete_forbidden": True,
            "grouping_invariant": True,
            "owned_structure_layers": ["body_flow"],
            "excluded_non_body_raw_run_count": len(
                {
                    str(raw_run_id)
                    for row in packet.get("page_text_index", []) or []
                    if isinstance(row, dict)
                    and str(row.get("structure_layer") or "") != "body_flow"
                    for raw_run_id in row.get("raw_run_ids", []) or []
                    if raw_run_id
                }
            ),
        },
        "metrics": {
            "gold_ledger_run_count": len(expected_by_raw),
            "gold_run_count": expected_count,
            "excluded_unknown_gold_run_count": len(unknown_by_raw),
            "excluded_unknown_gold_raw_run_ids": sorted(unknown_by_raw)[:100],
            "covered_unknown_gold_run_count": covered_unknown_count,
            "covered_run_count": covered_count,
            "coverage": round(_safe_ratio(covered_count, expected_count), 4),
            "conflicted_run_count": conflict_count,
            "predicted_unknown_run_count": predicted_unknown_count,
            "exact_action_accuracy": round(
                _safe_ratio(correct_action_count, expected_count),
                4,
            ),
            "action_macro_f1": round(
                sum(f1_values) / len(f1_values) if f1_values else 0.0,
                4,
            ),
            "per_action": per_action,
            "per_unit": per_unit,
            "deletion_safety": {
                "expected_delete_runs": expected_delete_count,
                "predicted_delete_runs": predicted_delete_count,
                "true_delete_runs": true_delete_count,
                "false_delete_runs": len(false_delete_raw_ids),
                "missed_delete_runs": expected_delete_count - true_delete_count,
                "delete_precision": round(
                    _safe_ratio(true_delete_count, predicted_delete_count),
                    4,
                ),
                "delete_recall": round(
                    _safe_ratio(true_delete_count, expected_delete_count),
                    4,
                ),
                "hard_gate_zero_false_delete": not false_delete_raw_ids,
                "false_delete_raw_run_ids": false_delete_raw_ids[:100],
            },
        },
    }


def _t3_prediction_claims(
    observation: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    claims: dict[str, list[dict[str, str]]] = {}
    for item in observation.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        unit_id = str(item.get("unit_id") or "")
        parent_policy = _canonical_t3_policy(item.get("policy"))
        span_raw_ids: set[str] = set()
        for span in item.get("spans", []) or []:
            if not isinstance(span, dict):
                continue
            span_policy = _canonical_t3_policy(span.get("policy"))
            for raw_run_id_value in span.get("raw_run_ids", []) or []:
                raw_run_id = str(raw_run_id_value or "")
                if not raw_run_id:
                    continue
                span_raw_ids.add(raw_run_id)
                claims.setdefault(raw_run_id, []).append(
                    {"policy": span_policy, "unit_id": unit_id}
                )
        for raw_run_id_value in item.get("raw_run_ids", []) or []:
            raw_run_id = str(raw_run_id_value or "")
            if not raw_run_id or raw_run_id in span_raw_ids:
                continue
            claims.setdefault(raw_run_id, []).append(
                {"policy": parent_policy, "unit_id": unit_id}
            )
    return claims


def _canonical_t3_policy(value: Any) -> str:
    policy = str(value or "")
    return {
        "remove_instruction": "instruction_remove",
        "template_default_optional": "template_default",
    }.get(policy, policy)


def _core_action_contract(
    t3_standard: dict[str, Any],
) -> tuple[list[str], dict[str, str], str, str, str]:
    contract = (t3_standard.get("expected", {}) or {}).get(
        "core_action_contract", {}
    )
    if not isinstance(contract, dict) or not contract:
        raise T3GoldUpstreamError(
            "T3 accuracy requires expected.core_action_contract"
        )
    if contract.get("primary_metric") != "exact_action_accuracy":
        raise T3GoldUpstreamError(
            "T3 core action contract must declare primary_metric=exact_action_accuracy"
        )
    if contract.get("scored_ledger") != "run_span_ledger":
        raise T3GoldUpstreamError(
            "T3 core action contract must score expected.run_span_ledger"
        )
    allowed_actions = [
        str(item) for item in contract.get("allowed_actions", []) or [] if item
    ]
    if allowed_actions != ["keep", "fill", "delete"]:
        raise T3GoldUpstreamError(
            "T3 core action contract allowed_actions must be keep/fill/delete"
        )
    raw_mapping = contract.get("policy_to_action")
    policy_to_action = {
        _canonical_t3_policy(policy): str(action)
        for policy, action in (raw_mapping or {}).items()
        if policy and action
    } if isinstance(raw_mapping, dict) else {}
    missing_policies = sorted(_CANONICAL_T3_POLICIES - set(policy_to_action))
    invalid_actions = {
        policy: action
        for policy, action in policy_to_action.items()
        if action not in allowed_actions
    }
    if missing_policies or invalid_actions:
        raise T3GoldUpstreamError(
            "T3 core action contract must map every canonical policy: "
            f"missing={missing_policies}, invalid={invalid_actions}"
        )
    gold_source_field = str(contract.get("gold_source_field") or "")
    if gold_source_field != "expected_action":
        raise T3GoldUpstreamError(
            "T3 core action contract gold_source_field must be expected_action"
        )
    if contract.get("grouping_invariant") is not True:
        raise T3GoldUpstreamError(
            "T3 core action accuracy must be invariant to element grouping"
        )
    unknown_action = str(contract.get("unknown_action") or "")
    if unknown_action != "unknown":
        raise T3GoldUpstreamError(
            "T3 core action contract must declare unknown_action=unknown"
        )
    if contract.get("unknown_scoring") != "excluded_from_primary":
        raise T3GoldUpstreamError(
            "T3 core action contract must exclude unknown from primary accuracy"
        )
    unknown_execution_fallback = str(
        contract.get("unknown_execution_fallback") or ""
    )
    if unknown_execution_fallback != "keep":
        raise T3GoldUpstreamError(
            "T3 core action contract must execute unknown as keep"
        )
    if contract.get("uncertain_delete_forbidden") is not True:
        raise T3GoldUpstreamError(
            "T3 core action contract must forbid delete for uncertain runs"
        )
    return (
        allowed_actions,
        policy_to_action,
        gold_source_field,
        unknown_action,
        unknown_execution_fallback,
    )


def _t3_core_action(
    value: Any,
    *,
    policy_to_action: dict[str, str],
    allowed_actions: set[str],
    unknown_action: str,
) -> str:
    label = str(value or "")
    if label == unknown_action:
        return unknown_action
    if label in allowed_actions:
        return label
    return policy_to_action.get(_canonical_t3_policy(label), "")


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _owned_packet_source_seq_set(
    packet: dict[str, Any],
    *,
    owned_structure_layers: set[str] | None,
) -> set[int]:
    if not owned_structure_layers:
        return packet_source_seq_set(packet)
    return {
        int(item["source_seq"])
        for item in packet.get("page_text_index", []) or []
        if isinstance(item, dict)
        and item.get("source_seq") is not None
        and str(item.get("structure_layer") or "") in owned_structure_layers
    }


def _atomic_run_fact_audit(
    packet: dict[str, Any],
    expected_source_seq: set[int],
) -> dict[str, Any]:
    indexed_run_facts = {
        str(item.get("raw_run_id") or ""): item
        for item in (packet.get("run_index", {}) or {}).get("raw_runs", []) or []
        if isinstance(item, dict) and item.get("raw_run_id")
    }
    rows = {
        int(item["source_seq"]): item
        for item in packet.get("page_text_index", []) or []
        if isinstance(item, dict) and item.get("source_seq") is not None
    }
    gaps: list[dict[str, Any]] = []
    run_fact_ids: set[str] = set()
    for source_seq in sorted(expected_source_seq):
        row = rows.get(source_seq)
        if row is None:
            gaps.append({"source_seq": source_seq, "reason": "source_row_missing"})
            continue
        expected_raw_ids = [str(item) for item in row.get("raw_run_ids", []) or []]
        if not expected_raw_ids and str(row.get("text") or ""):
            gaps.append(
                {
                    "source_seq": source_seq,
                    "reason": "source_row_without_raw_runs",
                }
            )
        run_facts = [
            item
            for item in (row.get("style_details", {}) or {}).get("runs", []) or []
            if isinstance(item, dict)
        ]
        by_raw_id = {
            str(item.get("raw_run_id") or ""): item
            for item in run_facts
            if item.get("raw_run_id")
        }
        for raw_id in expected_raw_ids:
            if raw_id not in by_raw_id and raw_id in indexed_run_facts:
                by_raw_id[raw_id] = indexed_run_facts[raw_id]
        run_fact_ids.update(by_raw_id)
        missing_raw_ids = [raw_id for raw_id in expected_raw_ids if raw_id not in by_raw_id]
        if missing_raw_ids:
            gaps.append(
                {
                    "source_seq": source_seq,
                    "reason": "raw_run_facts_missing",
                    "raw_run_ids": missing_raw_ids,
                }
            )
        for raw_id in expected_raw_ids:
            fact = by_raw_id.get(raw_id)
            if fact is None:
                continue
            missing_fields = [
                field
                for field in ("logical_run_id", "text", "source_ref", "effective_style")
                if field not in fact or fact.get(field) is None
            ]
            if missing_fields:
                gaps.append(
                    {
                        "source_seq": source_seq,
                        "reason": "raw_run_fact_incomplete",
                        "raw_run_id": raw_id,
                        "missing_fields": missing_fields,
                    }
                )
    return {"run_fact_count": len(run_fact_ids), "gaps": gaps}


def _object_fact_audit(
    packet: dict[str, Any],
    expected_source_refs: set[str],
) -> dict[str, Any]:
    facts = {
        str(item.get("source_ref") or ""): item
        for item in packet.get("object_fact_index", []) or []
        if isinstance(item, dict) and item.get("source_ref")
    }
    gaps: list[dict[str, Any]] = []
    for source_ref in sorted(expected_source_refs):
        fact = facts.get(source_ref)
        if fact is None:
            gaps.append({"source_ref": source_ref, "reason": "object_fact_missing"})
            continue
        missing_fields = [
            field
            for field in ("object_id", "object_type", "source_ref")
            if not fact.get(field)
        ]
        if str(fact.get("object_type") or "") == "field":
            missing_fields.extend(
                field
                for field in ("kind", "field_type", "instruction")
                if fact.get(field) is None
            )
        if missing_fields:
            gaps.append(
                {
                    "source_ref": source_ref,
                    "reason": "object_fact_incomplete",
                    "missing_fields": sorted(set(missing_fields)),
                }
            )
    return {
        "object_fact_count": len(expected_source_refs & set(facts)),
        "gaps": gaps,
    }


def _source_ref_range_refs(value: Any, *, unit_id: str) -> list[str]:
    if not isinstance(value, dict):
        raise T3GoldUpstreamError(
            "signed T2 standard has an invalid source_ref_range: "
            f"unit_id={unit_id}, range={value}"
        )
    start = str(value.get("start") or "").strip()
    end = str(value.get("end") or "").strip()
    if not start or not end:
        raise T3GoldUpstreamError(
            "signed T2 standard has an invalid source_ref_range: "
            f"unit_id={unit_id}, range={value}"
        )
    return [start] if start == end else [start, end]


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
