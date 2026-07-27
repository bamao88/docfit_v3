from __future__ import annotations

from docfit.convert.orchestrator import _route_evaluation_status


def test_route_evaluation_is_unknown_when_any_required_route_is_unavailable() -> None:
    status = _route_evaluation_status(
        {
            "route_availability": {
                "code_raw": "NOT_AVAILABLE",
                "ai_raw": "NOT_AVAILABLE",
                "merged": "NOT_AVAILABLE",
            }
        },
        [],
    )

    assert status == "UNKNOWN"


def test_route_evaluation_passes_only_when_all_routes_are_available() -> None:
    status = _route_evaluation_status(
        {
            "route_availability": {
                "code_raw": "AVAILABLE",
                "ai_raw": "AVAILABLE",
                "merged": "AVAILABLE",
            }
        },
        [],
    )

    assert status == "PASS"


def test_route_evaluation_allows_explicitly_out_of_scope_routes() -> None:
    status = _route_evaluation_status(
        {
            "route_availability": {
                "code_raw": "OUT_OF_SCOPE",
                "ai_raw": "OUT_OF_SCOPE",
                "merged": "AVAILABLE",
            }
        },
        [],
    )

    assert status == "PASS"
