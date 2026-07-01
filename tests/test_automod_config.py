"""Tests for AutoMod threshold clamping in MyBot._clamp_int — the dashboard can
send arbitrary numbers for spam/mention thresholds, so they must be coerced into
safe ranges before hitting the DB."""
import pytest

pytest.importorskip("redis")  # bot.py imports core.redis_manager -> redis.asyncio
from bot import MyBot  # noqa: E402

clamp = MyBot._clamp_int


def test_within_range_passes_through():
    assert clamp(7, 5, 3, 20) == 7


def test_string_number_is_parsed():
    assert clamp("8", 5, 3, 20) == 8


def test_below_min_clamps_up():
    assert clamp(1, 5, 3, 20) == 3


def test_above_max_clamps_down():
    assert clamp(100, 5, 3, 20) == 20


def test_none_uses_default():
    assert clamp(None, 5, 3, 20) == 5


def test_non_numeric_uses_default():
    assert clamp("nope", 5, 3, 20) == 5


def test_float_string_uses_default():
    # int("3.5") raises ValueError -> default, rather than silently truncating.
    assert clamp("3.5", 5, 3, 20) == 5
