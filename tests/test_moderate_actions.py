"""Unit tests for the dashboard moderation dispatch (core.moderation_actions).

Covers the branch behaviour of perform_moderation — which discord/db calls each
action makes, the hierarchy/owner guard, and that every action is mirrored to
the punishment log — using mocked guild/member/db objects (no live Discord).
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from core.moderation_actions import perform_moderation, HIERARCHY_ERROR


def _member(uid=2, pos=1):
    return SimpleNamespace(
        id=uid,
        top_role=SimpleNamespace(position=pos),
        timeout=AsyncMock(),
        kick=AsyncMock(),
    )


def _guild(member=None, bot_pos=5, owner_id=999):
    return SimpleNamespace(
        id=1,
        me=SimpleNamespace(top_role=SimpleNamespace(position=bot_pos)),
        owner_id=owner_id,
        get_member=lambda uid: member,
        ban=AsyncMock(),
    )


def _run(**kw):
    defaults = dict(
        db=SimpleNamespace(add_warning=AsyncMock(return_value=7)),
        bot_user_id=1,
        user_id=2,
        reason="x",
        mod_name="admin",
        mod_id=10,
        duration_minutes=None,
        log_action=AsyncMock(),
    )
    defaults.update(kw)
    return asyncio.run(perform_moderation(**defaults))


def test_warn_adds_warning_and_logs():
    db = SimpleNamespace(add_warning=AsyncMock(return_value=7))
    log = AsyncMock()
    res = _run(db=db, guild=_guild(_member()), act="warn", log_action=log)
    assert res["success"] and res["warningId"] == 7
    db.add_warning.assert_awaited_once()
    log.assert_awaited_once()


def test_unknown_action_errors():
    res = _run(guild=_guild(_member()), act="frobnicate")
    assert "error" in res and "success" not in res


def test_warn_member_not_in_server():
    res = _run(guild=_guild(None), act="warn")
    assert res["error"] == "Member is not in the server"


def test_kick_blocked_by_equal_hierarchy():
    m = _member(pos=5)  # equal to the bot's top role -> blocked
    res = _run(guild=_guild(m, bot_pos=5), act="kick")
    assert res["error"] == HIERARCHY_ERROR
    m.kick.assert_not_awaited()


def test_kick_success_below_hierarchy():
    m = _member(pos=1)
    log = AsyncMock()
    res = _run(guild=_guild(m, bot_pos=5), act="kick", log_action=log)
    assert res["success"]
    m.kick.assert_awaited_once()
    log.assert_awaited_once()


def test_ban_absent_user_succeeds():
    g = _guild(None)
    res = _run(guild=g, act="ban", user_id=2)
    assert res["success"]
    g.ban.assert_awaited_once()


def test_ban_owner_blocked():
    owner = _member(uid=999, pos=1)
    res = _run(guild=_guild(owner, owner_id=999), act="ban", user_id=999)
    assert res["error"] == HIERARCHY_ERROR


def test_mute_clamps_negative_and_logs():
    m = _member(pos=1)
    log = AsyncMock()
    res = _run(guild=_guild(m, bot_pos=5), act="mute", duration_minutes=-5, log_action=log)
    assert res["success"]
    m.timeout.assert_awaited_once()  # called with the clamped (>=1) duration
    log.assert_awaited_once()


def test_unmute_clears_timeout():
    m = _member(pos=1)
    res = _run(guild=_guild(m, bot_pos=5), act="unmute")
    assert res["success"]
    m.timeout.assert_awaited_once_with(None, reason="x (via dashboard: admin)")
