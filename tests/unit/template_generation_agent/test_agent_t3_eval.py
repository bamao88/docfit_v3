from __future__ import annotations

import pytest

from docfit.template_generation.agent.t3_eval import (
    T3GoldUpstreamError,
    validate_t3_gold_upstream,
)


def packet() -> dict:
    return {"page_text_index": [{"source_seq": 1}, {"source_seq": 2}, {"source_seq": 3}]}


def test_t3_eval_accepts_only_human_confirmed_exact_t2_partition() -> None:
    result = validate_t3_gold_upstream(
        {
            "items": [
                {"unit_id": "cover", "source_seq_refs": [1]},
                {"unit_id": "body_main", "source_seq_refs": [2, 3]},
            ]
        },
        packet=packet(),
        human_confirmed=True,
        gold_source="signed/t2.standard.yaml",
    )

    assert result["status"] == "PASS"
    assert result["exact_packet_partition"] is True


@pytest.mark.parametrize(
    ("observation", "human_confirmed"),
    [
        ({"items": [{"unit_id": "cover", "source_seq_refs": [1, 2, 3]}]}, False),
        ({"items": [{"unit_id": "cover", "source_seq_refs": [1, 2]}]}, True),
        (
            {
                "items": [
                    {"unit_id": "cover", "source_seq_refs": [1, 2]},
                    {"unit_id": "body_main", "source_seq_refs": [2, 3]},
                ]
            },
            True,
        ),
    ],
)
def test_t3_eval_rejects_live_or_inexact_upstream(observation, human_confirmed) -> None:
    with pytest.raises(T3GoldUpstreamError):
        validate_t3_gold_upstream(
            observation,
            packet=packet(),
            human_confirmed=human_confirmed,
            gold_source="signed/t2.standard.yaml",
        )
