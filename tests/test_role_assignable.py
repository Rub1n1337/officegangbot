"""Tests for role_is_assignable() in core/permissions.py — used to reject
auto-grant configs (autorole, level/reaction roles) the bot can't actually grant.
"""
from core.permissions import role_is_assignable

BOT_TOP = 10


def test_role_below_bot_is_assignable():
    assert role_is_assignable(role_managed=False, role_position=5, bot_top_role_pos=BOT_TOP) is True


def test_role_above_bot_is_not_assignable():
    assert role_is_assignable(role_managed=False, role_position=11, bot_top_role_pos=BOT_TOP) is False


def test_role_equal_to_bot_is_not_assignable():
    # Discord requires the bot's role to be strictly higher.
    assert role_is_assignable(role_managed=False, role_position=BOT_TOP, bot_top_role_pos=BOT_TOP) is False


def test_managed_role_is_never_assignable():
    assert role_is_assignable(role_managed=True, role_position=1, bot_top_role_pos=BOT_TOP) is False
