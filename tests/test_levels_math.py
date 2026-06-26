"""Tests for the XP/level math in cogs/levels.py.

These functions run on every message (`get_level_from_xp`) and on `/rank`
(`_cumulative_xp`), and were rewritten to closed-form / binary-search versions.
The whole point of that rewrite is that it must stay numerically identical to
the original naive loop, so that's exactly what we pin down here.
"""
from cogs.levels import get_xp_for_level, _cumulative_xp, get_level_from_xp, _MAX_LEVEL


def naive_cumulative_xp(level: int) -> int:
    """The original O(n) definition: total XP to reach `level` is the sum of the
    per-level requirements for levels 0..level-1."""
    return sum(get_xp_for_level(n) for n in range(level))


def test_cumulative_matches_naive_sum():
    # The closed form must equal the naive sum across a wide range.
    for level in range(0, 2000):
        assert _cumulative_xp(level) == naive_cumulative_xp(level), f"mismatch at level {level}"


def test_cumulative_is_strictly_increasing():
    prev = -1
    for level in range(0, 500):
        cur = _cumulative_xp(level)
        assert cur > prev, f"cumulative XP not increasing at level {level}"
        prev = cur


def test_zero_and_negative_xp_is_level_zero():
    assert get_level_from_xp(0) == 0
    assert get_level_from_xp(-5) == 0
    assert get_level_from_xp(_cumulative_xp(1) - 1) == 0


def test_level_boundaries_are_exact():
    # At exactly the cumulative threshold for level L you ARE level L; one XP
    # short you are still L-1.
    for level in range(1, 300):
        threshold = _cumulative_xp(level)
        assert get_level_from_xp(threshold) == level, f"at threshold of level {level}"
        assert get_level_from_xp(threshold - 1) == level - 1, f"just below level {level}"
        assert get_level_from_xp(threshold + 1) == level, f"just above level {level}"


def test_binary_search_matches_linear_scan():
    # Independent O(n) reference implementation of "current level for total xp".
    def linear_level(xp: int) -> int:
        level = 0
        while level < _MAX_LEVEL and _cumulative_xp(level + 1) <= xp:
            level += 1
        return level

    for xp in range(0, 200_000, 137):  # sample the curve without testing every value
        assert get_level_from_xp(xp) == linear_level(xp), f"mismatch at xp={xp}"


def test_level_is_capped():
    huge = _cumulative_xp(_MAX_LEVEL) * 10
    assert get_level_from_xp(huge) == _MAX_LEVEL
