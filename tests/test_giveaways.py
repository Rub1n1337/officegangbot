"""Unit tests for the pure giveaway helpers (core.giveaways)."""
from core.giveaways import parse_duration, pick_winners, MAX_DURATION_SECONDS


def test_parse_duration_units():
    assert parse_duration("30s") == 30
    assert parse_duration("10m") == 600
    assert parse_duration("2h") == 7200
    assert parse_duration("1d") == 86400
    assert parse_duration("1w") == 604800
    assert parse_duration(" 5 m ") == 300  # whitespace tolerant
    assert parse_duration("3H") == 10800   # case-insensitive


def test_parse_duration_invalid():
    for bad in ["", "abc", "10", "m", "-5m", "0m", "10x", "1.5h"]:
        assert parse_duration(bad) is None


def test_parse_duration_out_of_range():
    assert parse_duration("100d") is None  # > ~60 days
    assert parse_duration("60d") == MAX_DURATION_SECONDS  # exactly at the cap is allowed


def test_pick_winners_basic():
    winners = pick_winners([1, 2, 3, 4, 5], 2)
    assert len(winners) == 2
    assert len(set(winners)) == 2
    assert all(w in {1, 2, 3, 4, 5} for w in winners)


def test_pick_winners_dedupes_entries():
    assert pick_winners([7, 7, 7], 3) == [7]


def test_pick_winners_fewer_than_requested():
    assert sorted(pick_winners([1, 2], 5)) == [1, 2]


def test_pick_winners_empty_or_zero():
    assert pick_winners([], 3) == []
    assert pick_winners([1, 2], 0) == []
