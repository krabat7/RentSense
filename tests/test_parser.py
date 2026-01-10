import pytest
from app.parser.tools import recjson


def test_recjson():
    data = 'test {"key": "value"} test'
    result = recjson(r'(\{.*?\})', data)
    assert result == {"key": "value"}


