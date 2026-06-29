"""Unit tests for the dashboard member search + profile shaping
(core.member_queries), using mocked guild/member/db objects."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from core.member_queries import search_guild_members, build_member_profile


def _member(uid, name, display, bot=False):
    return SimpleNamespace(
        id=uid,
        name=name,
        display_name=display,
        bot=bot,
        display_avatar=SimpleNamespace(url=f"http://cdn/{uid}.png"),
    )


def _guild(members):
    return SimpleNamespace(members=members, get_member=lambda uid: next((m for m in members if m.id == uid), None))


def test_search_excludes_bots():
    g = _guild([_member(1, "alice", "Alice"), _member(2, "botty", "Botty", bot=True)])
    names = [m["name"] for m in search_guild_members(g, "")["members"]]
    assert names == ["alice"]


def test_search_matches_name_display_and_id():
    g = _guild([
        _member(1, "alice", "Alice"),
        _member(2, "bob", "Bobby"),
        _member(123, "carol", "Carol"),
    ])
    assert {m["id"] for m in search_guild_members(g, "bob")["members"]} == {"2"}
    assert {m["id"] for m in search_guild_members(g, "carol")["members"]} == {"123"}
    assert {m["id"] for m in search_guild_members(g, "12")["members"]} == {"123"}  # id prefix


def test_search_sorts_and_caps():
    members = [_member(i, f"u{i}", f"User{100 - i}") for i in range(40)]
    out = search_guild_members(_guild(members), "", limit=25)["members"]
    assert len(out) == 25
    displays = [m["displayName"] for m in out]
    assert displays == sorted(displays, key=str.lower)


def _db(level=3, xp=120, warnings=None, display_name=None):
    return SimpleNamespace(
        get_user_xp=AsyncMock(return_value={"level": level, "xp": xp, "display_name": display_name}),
        get_warnings=AsyncMock(return_value=warnings or []),
    )


def test_profile_member_in_server_has_roles_and_join():
    role = SimpleNamespace(id=9, name="VIP", color=SimpleNamespace(value=0xABCDEF), is_default=lambda: False)
    everyone = SimpleNamespace(id=1, name="@everyone", color=SimpleNamespace(value=0), is_default=lambda: True)
    m = _member(5, "dave", "Dave")
    m.joined_at = SimpleNamespace(isoformat=lambda: "2024-01-01T00:00:00+00:00")
    m.roles = [everyone, role]
    g = _guild([m])
    res = asyncio.run(build_member_profile(g, _db(warnings=[]), 1, 5))
    assert res["inServer"] is True
    assert res["joinedAt"] == "2024-01-01T00:00:00+00:00"
    assert [r["name"] for r in res["roles"]] == ["VIP"]  # @everyone filtered out
    assert res["level"] == 3 and res["xp"] == 120


def test_profile_member_left_falls_back_to_stored_name():
    g = _guild([])  # not in server
    res = asyncio.run(build_member_profile(g, _db(display_name="OldName"), 1, 77))
    assert res["inServer"] is False
    assert res["name"] == "OldName"
    assert res["roles"] == [] and res["avatar"] is None


def test_profile_maps_warnings():
    warnings = [{"id": 3, "reason": "spam", "moderator_name": "mod", "created_at": None}]
    m = _member(5, "dave", "Dave")
    m.joined_at = None
    m.roles = []
    res = asyncio.run(build_member_profile(_guild([m]), _db(warnings=warnings), 1, 5))
    assert res["warnings"] == [
        {"id": 3, "reason": "spam", "moderatorName": "mod", "createdAt": None}
    ]
