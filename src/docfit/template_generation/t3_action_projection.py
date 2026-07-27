"""Project T3 element and span policies onto stable run identities."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


T3_CORE_ACTIONS = frozenset({"keep", "fill", "delete"})
T3_POLICY_TO_CORE_ACTION = {
    "fixed": "keep",
    "template_default": "keep",
    "template_default_optional": "keep",
    "fill": "fill",
    "generated": "fill",
    "instruction_remove": "delete",
    "remove_instruction": "delete",
}
T3_SPAN_TYPE_TO_CORE_ACTION = {
    "label": "keep",
    "sample_value": "fill",
    "inline_instruction": "delete",
    "layout_spacer": "delete",
}

T3RunIdentity = tuple[str, str]


@dataclass(frozen=True)
class T3GoldItemProjection:
    """Candidate actions and coverage for one adaptive run/span gold item."""

    actions: frozenset[str]
    coverage_complete: bool
    identity_covered: bool


def project_t3_actions_by_run_identity(
    items: Iterable[dict[str, Any]],
) -> dict[T3RunIdentity, frozenset[str]]:
    """Return actions by raw/logical run identity with lossless span folding.

    Exact spans override the parent only when their ranges cover the complete
    run.  Otherwise the uncovered parent action is retained.  Legacy spans
    without coordinates keep their historical whole-run meaning.  Multiple
    actions remain a set so mixed runs become explicit conflicts instead of an
    arbitrary last-write-wins result.
    """

    parent_actions: dict[T3RunIdentity, set[str]] = defaultdict(set)
    span_actions: dict[T3RunIdentity, set[str]] = defaultdict(set)
    span_claimed: set[T3RunIdentity] = set()
    full_span_claimed: set[T3RunIdentity] = set()
    span_ranges: dict[T3RunIdentity, list[tuple[int, int]]] = defaultdict(list)
    run_lengths: dict[T3RunIdentity, set[int]] = defaultdict(set)

    for item in items:
        if not isinstance(item, dict):
            continue
        parent_action = t3_core_action(item)
        item_identities = _run_identities(item)
        for identity in item_identities:
            if parent_action:
                parent_actions[identity].add(parent_action)
            if isinstance(item.get("run_text_length"), int):
                run_lengths[identity].add(int(item["run_text_length"]))

        for span in _dict_items(item.get("spans")):
            identities = _run_identities(span, include_char_ranges=True)
            span_claimed.update(identities)
            span_action = t3_core_action(span, allow_span_type=True)
            for identity in identities:
                if isinstance(span.get("run_text_length"), int):
                    run_lengths[identity].add(int(span["run_text_length"]))
                ranges = _char_ranges_for_identity(span, identity)
                if ranges:
                    span_ranges[identity].extend(ranges)
                else:
                    # Legacy spans without coordinates historically claim the
                    # complete named run. Preserve that compatibility only
                    # when no exact range was supplied for the identity.
                    full_span_claimed.add(identity)
                if span_action:
                    span_actions[identity].add(span_action)

    identities = set(parent_actions) | span_claimed
    result: dict[T3RunIdentity, frozenset[str]] = {}
    for identity in identities:
        if identity not in span_claimed:
            result[identity] = frozenset(parent_actions.get(identity, set()))
            continue
        actions = set(span_actions.get(identity, set()))
        lengths = run_lengths.get(identity, set())
        exact_ranges_cover_run = (
            len(lengths) == 1
            and _ranges_cover_complete(
                span_ranges.get(identity, []),
                run_length=next(iter(lengths)),
            )
        )
        if (
            identity not in full_span_claimed
            and not exact_ranges_cover_run
        ):
            actions.update(parent_actions.get(identity, set()))
        result[identity] = frozenset(actions)
    return result


def actions_for_t3_gold_run(
    projection: dict[T3RunIdentity, frozenset[str]],
    gold_row: dict[str, Any],
) -> frozenset[str]:
    """Resolve one raw-run gold row, using logical identity only as fallback."""

    raw_run_id = str(gold_row.get("raw_run_id") or "")
    raw_identity = ("raw_run_id", raw_run_id)
    if raw_run_id and raw_identity in projection:
        return projection[raw_identity]
    logical_run_id = str(gold_row.get("logical_run_id") or "")
    if logical_run_id:
        return projection.get(("logical_run_id", logical_run_id), frozenset())
    return frozenset()


def project_t3_gold_item(
    items: Iterable[dict[str, Any]],
    gold_row: dict[str, Any],
) -> T3GoldItemProjection:
    """Project candidate items onto one exact adaptive run/span gold identity."""

    candidates = [item for item in items if isinstance(item, dict)]
    target_kind = str(gold_row.get("target_kind") or "")
    if not target_kind:
        target_kind = (
            "span"
            if isinstance(gold_row.get("start"), int)
            and isinstance(gold_row.get("end"), int)
            else "run"
        )
    raw_run_id = str(gold_row.get("raw_run_id") or "")
    if target_kind == "span" and raw_run_id:
        start = gold_row.get("start")
        end = gold_row.get("end")
        if isinstance(start, int) and isinstance(end, int) and 0 <= start <= end:
            return _project_t3_range(
                candidates,
                raw_run_id=raw_run_id,
                start=start,
                end=end,
            )
        return T3GoldItemProjection(frozenset(), False, False)
    if target_kind == "run" and raw_run_id and isinstance(gold_row.get("text"), str):
        return _project_t3_range(
            candidates,
            raw_run_id=raw_run_id,
            start=0,
            end=len(str(gold_row.get("text") or "")),
        )

    projection = project_t3_actions_by_run_identity(candidates)
    actions = actions_for_t3_gold_run(projection, gold_row)
    raw_identity = ("raw_run_id", raw_run_id)
    logical_run_id = str(gold_row.get("logical_run_id") or "")
    identity_covered = bool(
        (raw_run_id and raw_identity in projection)
        or (
            logical_run_id
            and ("logical_run_id", logical_run_id) in projection
        )
    )
    return T3GoldItemProjection(
        actions=actions,
        coverage_complete=bool(actions),
        identity_covered=identity_covered,
    )


def t3_core_action(
    value: Any,
    *,
    allow_span_type: bool = False,
) -> str:
    """Normalize a direct core action, policy, or supported span type."""

    if isinstance(value, dict):
        direct = str(value.get("core_action") or "")
        if direct in T3_CORE_ACTIONS:
            return direct
        policy = str(value.get("policy") or "")
        action = T3_POLICY_TO_CORE_ACTION.get(policy, "")
        if action:
            return action
        if allow_span_type:
            return T3_SPAN_TYPE_TO_CORE_ACTION.get(
                str(value.get("span_type") or ""),
                "",
            )
        return ""
    label = str(value or "")
    if label in T3_CORE_ACTIONS:
        return label
    return T3_POLICY_TO_CORE_ACTION.get(label, "")


def _run_identities(
    value: dict[str, Any],
    *,
    include_char_ranges: bool = False,
) -> set[T3RunIdentity]:
    result = {
        (identity_kind, identity)
        for field, identity_kind in (
            ("raw_run_ids", "raw_run_id"),
            ("logical_run_ids", "logical_run_id"),
        )
        for identity in _strings(value.get(field))
    }
    if include_char_ranges:
        result.update(
            ("raw_run_id", raw_run_id)
            for char_range in _dict_items(value.get("char_ranges"))
            if (raw_run_id := str(char_range.get("raw_run_id") or ""))
        )
    return result


def _char_ranges_for_identity(
    value: dict[str, Any],
    identity: T3RunIdentity,
) -> list[tuple[int, int]]:
    if identity[0] != "raw_run_id":
        return []
    return [
        (int(char_range["start"]), int(char_range["end"]))
        for char_range in _dict_items(value.get("char_ranges"))
        if str(char_range.get("raw_run_id") or "") == identity[1]
        and isinstance(char_range.get("start"), int)
        and isinstance(char_range.get("end"), int)
        and 0 <= int(char_range["start"]) <= int(char_range["end"])
    ]


def _ranges_cover_complete(
    ranges: list[tuple[int, int]],
    *,
    run_length: int,
) -> bool:
    cursor = 0
    for start, end in sorted(ranges):
        if end <= cursor:
            continue
        if start > cursor:
            return False
        cursor = max(cursor, end)
        if cursor >= run_length:
            return True
    return cursor >= run_length


def _project_t3_range(
    items: list[dict[str, Any]],
    *,
    raw_run_id: str,
    start: int,
    end: int,
) -> T3GoldItemProjection:
    actions: set[str] = set()
    action_ranges: list[tuple[int, int]] = []
    identity_ranges: list[tuple[int, int]] = []
    for item in items:
        item_names_run = ("raw_run_id", raw_run_id) in _run_identities(item)
        parent_action = t3_core_action(item)
        matching_spans = [
            span
            for span in _dict_items(item.get("spans"))
            if ("raw_run_id", raw_run_id)
            in _run_identities(span, include_char_ranges=True)
        ]
        if not item_names_run and not matching_spans:
            continue

        exact_span_ranges: list[tuple[int, int]] = []
        legacy_full_span = False
        for span in matching_spans:
            span_action = t3_core_action(span, allow_span_type=True)
            ranges = _char_ranges_for_identity(
                span,
                ("raw_run_id", raw_run_id),
            )
            if not ranges:
                legacy_full_span = True
                identity_ranges.append((start, end))
                if span_action:
                    actions.add(span_action)
                    action_ranges.append((start, end))
                continue
            for range_start, range_end in ranges:
                overlap = _range_overlap(
                    range_start,
                    range_end,
                    start=start,
                    end=end,
                )
                if overlap is None:
                    continue
                exact_span_ranges.append(overlap)
                identity_ranges.append(overlap)
                if span_action:
                    actions.add(span_action)
                    action_ranges.append(overlap)

        if legacy_full_span:
            continue
        if item_names_run:
            # The parent owns all characters not claimed by exact spans.  Its
            # identity still covers the complete target even when its policy is
            # unknown; action coverage requires a mapped parent action.
            identity_ranges.append((start, end))
            if parent_action and not _ranges_cover_interval(
                exact_span_ranges,
                start=start,
                end=end,
            ):
                actions.add(parent_action)
                action_ranges.append((start, end))

    return T3GoldItemProjection(
        actions=frozenset(actions),
        coverage_complete=_ranges_cover_interval(
            action_ranges,
            start=start,
            end=end,
        ),
        identity_covered=_ranges_cover_interval(
            identity_ranges,
            start=start,
            end=end,
        ),
    )


def _range_overlap(
    range_start: int,
    range_end: int,
    *,
    start: int,
    end: int,
) -> tuple[int, int] | None:
    overlap_start = max(range_start, start)
    overlap_end = min(range_end, end)
    if overlap_start < overlap_end:
        return overlap_start, overlap_end
    if start == end == overlap_start == overlap_end:
        return overlap_start, overlap_end
    return None


def _ranges_cover_interval(
    ranges: list[tuple[int, int]],
    *,
    start: int,
    end: int,
) -> bool:
    if start == end:
        return bool(ranges) and any(
            range_start <= start <= range_end
            for range_start, range_end in ranges
        )
    cursor = start
    for range_start, range_end in sorted(ranges):
        if range_end <= cursor:
            continue
        if range_start > cursor:
            return False
        cursor = max(cursor, range_end)
        if cursor >= end:
            return True
    return cursor >= end


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item not in (None, "")]
