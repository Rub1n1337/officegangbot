"""Tests for the has_permission() check in core/permissions.py.

The check decides who may run gated commands. The security-relevant guarantees:
bot owner and guild administrators always pass (so permissions can be
bootstrapped), DMs are refused, and otherwise a user passes only if one of their
roles is configured for the requested permission level.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from discord.ext.commands.errors import NoPrivateMessage

from core.permissions import has_permission


def _predicate(level="config"):
    # discord.py exposes the underlying coroutine as `.predicate` on the check.
    return has_permission(level).predicate


def _make_ctx(*, is_owner=False, guild=True, administrator=False, role_ids=(), mod_roles=None):
    author = SimpleNamespace(
        roles=[SimpleNamespace(id=rid) for rid in role_ids],
        guild_permissions=SimpleNamespace(administrator=administrator),
    )
    db = SimpleNamespace(get_mod_roles=AsyncMock(return_value=mod_roles or {}))
    bot = SimpleNamespace(is_owner=AsyncMock(return_value=is_owner), db=db)
    return SimpleNamespace(
        bot=bot,
        author=author,
        guild=SimpleNamespace(id=42) if guild else None,
    )


def test_owner_always_passes():
    ctx = _make_ctx(is_owner=True, administrator=False)
    assert asyncio.run(_predicate()(ctx)) is True


def test_administrator_passes_without_mod_roles():
    ctx = _make_ctx(administrator=True)
    assert asyncio.run(_predicate()(ctx)) is True


def test_dm_is_refused():
    ctx = _make_ctx(guild=False)
    with pytest.raises(NoPrivateMessage):
        asyncio.run(_predicate()(ctx))


def test_user_with_matching_mod_role_passes():
    ctx = _make_ctx(role_ids=(111,), mod_roles={"config": [111, 222]})
    assert asyncio.run(_predicate("config")(ctx)) is True


def test_user_without_matching_role_is_denied():
    ctx = _make_ctx(role_ids=(999,), mod_roles={"config": [111]})
    assert asyncio.run(_predicate("config")(ctx)) is False


def test_user_with_no_configured_roles_is_denied():
    ctx = _make_ctx(role_ids=(111,), mod_roles={})
    assert asyncio.run(_predicate("config")(ctx)) is False
