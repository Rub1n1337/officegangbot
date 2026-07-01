"""Tests for core/bulk_ops.parse_id_list — bulk-command id parsing."""
from core.bulk_ops import parse_id_list


def test_parses_raw_ids():
    assert parse_id_list("123456789012345678 234567890123456789") == [
        123456789012345678,
        234567890123456789,
    ]


def test_parses_mentions():
    assert parse_id_list("<@123456789012345678> <@!234567890123456789>") == [
        123456789012345678,
        234567890123456789,
    ]


def test_mixed_separators():
    out = parse_id_list("123456789012345678, 234567890123456789\n345678901234567890")
    assert out == [123456789012345678, 234567890123456789, 345678901234567890]


def test_dedupes_preserving_order():
    out = parse_id_list("123456789012345678 123456789012345678 234567890123456789")
    assert out == [123456789012345678, 234567890123456789]


def test_ignores_short_numbers():
    # 123 is far too short to be a snowflake.
    assert parse_id_list("123 456 hello world") == []


def test_ignores_overlong_digit_runs():
    # A 25-digit run is not a valid snowflake and must not be sliced into one.
    assert parse_id_list("1234567890123456789012345") == []


def test_limit_caps_results():
    ids = " ".join(str(100000000000000000 + i) for i in range(30))
    assert len(parse_id_list(ids, limit=20)) == 20


def test_empty_and_none():
    assert parse_id_list("") == []
    assert parse_id_list(None) == []
