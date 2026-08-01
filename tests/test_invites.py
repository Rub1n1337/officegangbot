"""Unit tests for the invite-attribution diff (core.invites)."""
from core.invites import detect_used_invite


def test_single_increment_is_the_used_code():
    assert detect_used_invite({"abc": 1, "xyz": 5}, {"abc": 2, "xyz": 5}) == "abc"


def test_new_single_use_invite_between_snapshots():
    # A fresh invite created and consumed before the next snapshot.
    assert detect_used_invite({"abc": 1}, {"abc": 1, "new": 1}) == "new"


def test_empty_before_single_after():
    assert detect_used_invite({}, {"a": 1}) == "a"


def test_nothing_incremented_is_unknown():
    # Vanity URL / unattributable join.
    assert detect_used_invite({"abc": 1}, {"abc": 1}) is None


def test_two_codes_incrementing_is_ambiguous():
    # Two joins landed between snapshots — can't attribute to one code.
    assert detect_used_invite({"a": 0, "b": 0}, {"a": 1, "b": 1}) is None


def test_deleted_invite_does_not_count_as_used():
    # A code disappeared (deleted); a drop is not an increment.
    assert detect_used_invite({"a": 3, "b": 1}, {"a": 3}) is None


def test_unreadable_after_snapshot_is_unknown():
    # Invites became unreadable (empty snapshot) — no candidate.
    assert detect_used_invite({"a": 1}, {}) is None
