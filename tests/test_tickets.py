"""Tests for core/tickets.py — transcript formatting and priority normalization."""
from core.tickets import (
    build_transcript,
    format_transcript_line,
    normalize_priority,
    VALID_PRIORITIES,
    PRIORITY_LABELS,
)


def test_normalize_priority_valid_passthrough():
    for p in VALID_PRIORITIES:
        assert normalize_priority(p) == p


def test_normalize_priority_case_and_whitespace():
    assert normalize_priority("  HIGH ") == "high"


def test_normalize_priority_unknown_uses_default():
    assert normalize_priority("banana") == "medium"
    assert normalize_priority(None) == "medium"
    assert normalize_priority("", default="urgent") == "urgent"


def test_normalize_priority_bad_default_falls_back_to_medium():
    assert normalize_priority("x", default="nonsense") == "medium"


def test_priority_labels_cover_all_priorities():
    assert set(PRIORITY_LABELS) == set(VALID_PRIORITIES)


def test_format_line_plain():
    line = format_transcript_line("2026-07-02 10:00", "alice (1)", "hello", [])
    assert line == "[2026-07-02 10:00] alice (1): hello"


def test_format_line_with_attachments():
    line = format_transcript_line("t", "a", "hi", ["http://x/1.png", "http://x/2.png"])
    assert "hi" in line
    assert "[attachments] http://x/1.png http://x/2.png" in line


def test_format_line_attachment_only():
    line = format_transcript_line("t", "a", "", ["http://x/1.png"])
    assert line.endswith("[attachments] http://x/1.png")


def test_build_transcript_with_header_and_entries():
    entries = [
        {"timestamp": "t1", "author": "a", "content": "first", "attachments": []},
        {"timestamp": "t2", "author": "b", "content": "second", "attachments": []},
    ]
    out = build_transcript(entries, header="Transcript — #ticket")
    lines = out.splitlines()
    assert lines[0] == "Transcript — #ticket"
    assert set(lines[1]) == {"-"}  # separator row
    assert lines[2] == "[t1] a: first"
    assert lines[3] == "[t2] b: second"


def test_build_transcript_empty():
    out = build_transcript([])
    assert out == "(no messages)"
