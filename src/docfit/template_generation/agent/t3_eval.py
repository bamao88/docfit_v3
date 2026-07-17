"""T3 隔离评测的 gold-upstream 前置校验。

评测工具必须显式声明 T2 来自人工确认标准，并证明它与当前 packet 构成无重叠、无缺失的
精确分区；否则不能把结果称作 T3 准确率。
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .packet import packet_source_seq_set


class T3GoldUpstreamError(ValueError):
    """T3 隔离评测的上游不满足人工 gold 契约。"""


def validate_t3_gold_upstream(
    ai_unit_observation: dict[str, Any],
    *,
    packet: dict[str, Any],
    human_confirmed: bool,
    gold_source: str,
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
    expected = packet_source_seq_set(packet)
    observed = set(refs)
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    empty_units = [str(item.get("unit_id") or "") for item in items if not item.get("source_seq_refs")]
    if duplicates or missing or extra or empty_units:
        raise T3GoldUpstreamError(
            "T2 gold must exactly partition the current T3 packet: "
            f"duplicates={duplicates}, missing={missing}, extra={extra}, empty_units={empty_units}"
        )
    return {
        "status": "PASS",
        "human_confirmed": True,
        "gold_source": gold_source,
        "unit_count": len(items),
        "source_seq_count": len(refs),
        "exact_packet_partition": True,
    }
