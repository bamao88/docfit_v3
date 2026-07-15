from __future__ import annotations

import pytest

from docfit.template_generation.agent.observation_vision import (
    MinimaxVisionError,
    _parse_json_object,
)


def test_parse_plain_json() -> None:
    d = _parse_json_object('{"has_header":false,"page_number_visible":false}')
    assert d["has_header"] is False
    assert d["page_number_visible"] is False


def test_parse_json_with_fences_and_prose() -> None:
    # M3 偶尔包 ```json 或前后杂字 → 取第一个 { 到最后一个 }。
    raw = '这是分析：\n```json\n{"has_footer":true,"page_number_visible":true}\n```\n完'
    d = _parse_json_object(raw)
    assert d["has_footer"] is True
    assert d["page_number_visible"] is True


def test_parse_empty_raises() -> None:
    with pytest.raises(MinimaxVisionError):
        _parse_json_object("   ")


def test_parse_non_object_raises() -> None:
    with pytest.raises((MinimaxVisionError, ValueError)):
        _parse_json_object("[1,2,3]")
