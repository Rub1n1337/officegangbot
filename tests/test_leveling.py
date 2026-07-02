"""Tests for core/leveling.py — XP multiplier math and prestige gating."""
from core.leveling import (
    sanitize_multiplier,
    effective_multiplier,
    apply_multiplier,
    can_prestige,
    MIN_MULTIPLIER,
    MAX_MULTIPLIER,
)


def test_sanitize_passthrough_and_round():
    assert sanitize_multiplier(2) == 2.0
    assert sanitize_multiplier("1.5") == 1.5
    assert sanitize_multiplier(1.239) == 1.24


def test_sanitize_clamps():
    assert sanitize_multiplier(100) == MAX_MULTIPLIER
    assert sanitize_multiplier(0) == MIN_MULTIPLIER


def test_sanitize_bad_uses_default():
    assert sanitize_multiplier(None) == 1.0
    assert sanitize_multiplier("abc", default=2.0) == 2.0


def test_effective_no_roles():
    assert effective_multiplier(2.0, []) == 2.0
    assert effective_multiplier(2.0, None) == 2.0


def test_effective_takes_best_role():
    # global 2.0 * best role (3.0) = 6.0
    assert effective_multiplier(2.0, [1.5, 3.0, 2.0]) == 6.0


def test_effective_clamped_to_max():
    assert effective_multiplier(5.0, [5.0]) == MAX_MULTIPLIER


def test_apply_multiplier_rounds():
    assert apply_multiplier(20, 1.5) == 30
    assert apply_multiplier(15, 2.0) == 30


def test_apply_multiplier_floor_one_for_positive():
    # A tiny multiplier still yields at least 1 for a positive base.
    assert apply_multiplier(1, 0.1) == 1


def test_apply_multiplier_zero_base():
    assert apply_multiplier(0, 5.0) == 0


def test_can_prestige():
    assert can_prestige(100, 100) is True
    assert can_prestige(120, 100) is True
    assert can_prestige(99, 100) is False


def test_can_prestige_disabled_threshold():
    assert can_prestige(500, 0) is False
    assert can_prestige(500, -1) is False
