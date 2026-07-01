"""Tests for core/automod_rules.py — regex rule validation and matching."""
from core.automod_rules import (
    normalize_action,
    validate_pattern,
    sanitize_rules,
    compile_rules,
    first_match,
    MAX_RULES,
    MAX_PATTERN_LEN,
)


def test_normalize_action():
    assert normalize_action("strike") == "strike"
    assert normalize_action("DELETE") == "delete"
    assert normalize_action("nonsense") == "delete"
    assert normalize_action(None) == "delete"


def test_validate_pattern_ok():
    assert validate_pattern(r"free\s*nitro") is None


def test_validate_pattern_empty():
    assert validate_pattern("   ") == "empty pattern"


def test_validate_pattern_too_long():
    assert validate_pattern("a" * (MAX_PATTERN_LEN + 1)) is not None


def test_validate_pattern_invalid_regex():
    assert validate_pattern("(unclosed").startswith("invalid regex")


def test_sanitize_drops_invalid_and_dupes():
    rules = [
        {"pattern": "good", "action": "strike"},
        {"pattern": "good", "action": "delete"},  # duplicate
        {"pattern": "(bad", "action": "delete"},   # invalid regex
        {"pattern": "   ", "action": "delete"},    # empty
    ]
    out = sanitize_rules(rules)
    assert len(out) == 1
    assert out[0] == {"pattern": "good", "action": "strike", "enabled": True}


def test_sanitize_caps_count():
    rules = [{"pattern": f"word{i}"} for i in range(MAX_RULES + 10)]
    assert len(sanitize_rules(rules)) == MAX_RULES


def test_sanitize_defaults_action_and_enabled():
    out = sanitize_rules([{"pattern": "hello"}])
    assert out[0]["action"] == "delete"
    assert out[0]["enabled"] is True


def test_compile_skips_disabled():
    compiled = compile_rules([
        {"pattern": "a", "action": "delete", "enabled": True},
        {"pattern": "b", "action": "delete", "enabled": False},
    ])
    assert len(compiled) == 1


def test_first_match_returns_action():
    compiled = compile_rules([{"pattern": r"free\s*nitro", "action": "strike", "enabled": True}])
    assert first_match(compiled, "get FREE   NITRO now") == "strike"


def test_first_match_case_insensitive_and_none():
    compiled = compile_rules([{"pattern": "scam", "action": "delete", "enabled": True}])
    assert first_match(compiled, "totally SCAM link") == "delete"
    assert first_match(compiled, "clean message") is None


def test_first_match_empty_content():
    compiled = compile_rules([{"pattern": "x", "action": "delete", "enabled": True}])
    assert first_match(compiled, "") is None
