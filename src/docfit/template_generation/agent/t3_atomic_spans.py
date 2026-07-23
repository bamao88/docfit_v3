"""Policy-neutral atomic span identities for hierarchical T3 input.

The splitter only exposes stable character boundaries observed in the sealed L1
run text.  It deliberately does not attach Keep/Fill/Delete semantics: those
belong to T3 decisions, not Stage Input facts.
"""

from __future__ import annotations

import re
from typing import Any


T3_ATOMIC_SPAN_VERSION = "t3-atomic-span-1.0"

_VISIBLE_BOUNDARY_PATTERNS = (
    re.compile(r"[（(][^（）()]{1,160}[）)]"),
    re.compile(r"□+"),
    re.compile(r"×+"),
    re.compile(r"…{2,}"),
    re.compile(r"\.{3,}"),
    re.compile(r"_{2,}"),
)


def atomic_span_ref(raw_run_id: str, start: int, end: int) -> str:
    """Return the deterministic identity of one exact raw-run character range."""

    return f"span:{raw_run_id}@{start:06d}:{end:06d}"


def partition_atomic_run_spans(
    *,
    raw_run_id: str,
    text: str,
) -> list[dict[str, Any]]:
    """Partition one raw run into complete, ordered, non-overlapping ranges.

    Boundaries come from visible punctuation/placeholder runs only.  The output
    is a factual candidate partition; no segment is labelled with a policy or a
    semantic role.  Runs without a useful internal boundary remain one span.
    """

    boundaries = {0, len(text)}
    for pattern in _VISIBLE_BOUNDARY_PATTERNS:
        for match in pattern.finditer(text):
            boundaries.add(match.start())
            boundaries.add(match.end())
    for match in re.finditer(r"[：:]", text):
        boundaries.add(match.end())

    ordered = sorted(boundaries)
    ranges = [
        (start, end)
        for start, end in zip(ordered, ordered[1:])
        if start < end
    ]
    if not ranges:
        ranges = [(0, 0)]
    return [
        {
            "ref": atomic_span_ref(raw_run_id, start, end),
            "raw_run_id": raw_run_id,
            "start": start,
            "end": end,
            "text": text[start:end],
            "segmentation_version": T3_ATOMIC_SPAN_VERSION,
        }
        for start, end in ranges
    ]
