"""Unit tests for custom-command validation (core.custom_commands)."""
from core.custom_commands import valid_name, sanitize_commands


def test_valid_names():
    assert valid_name("rules")
    assert valid_name("server-info")
    assert valid_name("faq_2")
    assert valid_name("a" * 32)


def test_invalid_names():
    assert not valid_name("")
    assert not valid_name("a" * 33)
    assert not valid_name("Rules")  # uppercase
    assert not valid_name("has space")
    assert not valid_name("emoji😀")
    assert not valid_name("dot.name")


def test_sanitize_lowercases_and_validates():
    out = sanitize_commands([{"name": "RULES", "response": "Be nice"}], 10)
    assert out == [{"name": "rules", "response": "Be nice"}]


def test_sanitize_drops_empty_and_invalid():
    out = sanitize_commands(
        [
            {"name": "ok", "response": "hi"},
            {"name": "bad name", "response": "x"},   # invalid name
            {"name": "empty", "response": "   "},     # blank response
            {"name": "", "response": "x"},            # empty name
        ],
        10,
    )
    assert [c["name"] for c in out] == ["ok"]


def test_sanitize_dedupes_by_name():
    out = sanitize_commands(
        [{"name": "a", "response": "1"}, {"name": "A", "response": "2"}], 10
    )
    assert len(out) == 1 and out[0]["response"] == "1"


def test_sanitize_caps_count():
    rows = [{"name": f"c{i}", "response": "x"} for i in range(50)]
    assert len(sanitize_commands(rows, 15)) == 15


def test_sanitize_trims_long_response():
    out = sanitize_commands([{"name": "a", "response": "x" * 5000}], 10)
    assert len(out[0]["response"]) == 2000
