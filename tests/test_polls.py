"""Unit tests for the pure poll helpers (core.polls)."""
from core.polls import apply_vote, format_results, parse_options, tally, MAX_OPTIONS


def test_parse_trims_and_drops_empties():
    assert parse_options("a | b |  | c ") == ["a", "b", "c"]


def test_parse_dedupes_case_insensitive_keeping_first():
    assert parse_options("Yes | yes | No") == ["Yes", "No"]


def test_parse_caps_at_max():
    raw = " | ".join(str(i) for i in range(20))
    assert len(parse_options(raw)) == MAX_OPTIONS


def test_parse_truncates_long_option_to_label_limit():
    assert len(parse_options("x" * 100)[0]) == 80


def test_parse_empty_string_is_empty():
    assert parse_options("") == []


def test_single_choice_selects_then_replaces():
    assert apply_vote(set(), 1, allow_multi=False) == {1}
    assert apply_vote({1}, 2, allow_multi=False) == {2}


def test_single_choice_clicking_same_clears():
    assert apply_vote({1}, 1, allow_multi=False) == set()


def test_multi_choice_toggles_in_and_out():
    assert apply_vote({0}, 1, allow_multi=True) == {0, 1}
    assert apply_vote({0, 1}, 1, allow_multi=True) == {0}


def test_tally_counts_and_ignores_out_of_range():
    assert tally([0, 0, 1, 5, -1], 3) == [2, 1, 0]


def test_format_results_zero_total_does_not_crash():
    out = format_results(["a", "b"], [0, 0])
    assert "0%" in out and "**1.** a" in out


def test_format_results_percentages():
    out = format_results(["a", "b"], [3, 1])
    assert "75%" in out and "25%" in out
