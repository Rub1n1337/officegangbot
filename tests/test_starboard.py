"""Unit tests for the starboard decision logic (core.starboard)."""
from core.starboard import starboard_action


def test_create_when_over_threshold_and_no_post():
    assert starboard_action(count=3, threshold=3, has_post=False) == "create"
    assert starboard_action(count=10, threshold=3, has_post=False) == "create"


def test_update_when_over_threshold_and_post_exists():
    assert starboard_action(count=5, threshold=3, has_post=True) == "update"


def test_remove_when_below_threshold_and_post_exists():
    assert starboard_action(count=2, threshold=3, has_post=True) == "remove"
    assert starboard_action(count=0, threshold=3, has_post=True) == "remove"


def test_none_when_below_threshold_and_no_post():
    assert starboard_action(count=1, threshold=3, has_post=False) == "none"
    assert starboard_action(count=0, threshold=3, has_post=False) == "none"


def test_threshold_boundary_is_inclusive():
    assert starboard_action(count=3, threshold=3, has_post=False) == "create"
    assert starboard_action(count=2, threshold=3, has_post=False) == "none"
