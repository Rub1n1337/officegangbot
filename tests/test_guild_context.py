"""Tests for GuildContext — the bundled per-guild locale/features/settings read."""
import asyncio
from unittest.mock import AsyncMock

from core.guild_context import GuildContext


def test_load_fetches_all_three_concurrently():
    db = AsyncMock()
    db.get_locale.return_value = "ru"
    db.get_enabled_features.return_value = ["automod", "levels"]
    db.get_all_guild_settings.return_value = {"punishment_log_id": 42}

    ctx = asyncio.run(GuildContext.load(db, 123))

    assert ctx.guild_id == 123
    assert ctx.locale == "ru"
    assert ctx.is_enabled("automod")
    assert not ctx.is_enabled("tickets")
    assert ctx.setting("punishment_log_id") == 42
    assert ctx.setting("missing", "fallback") == "fallback"
    db.get_locale.assert_awaited_once_with(123)
    db.get_enabled_features.assert_awaited_once_with(123)
    db.get_all_guild_settings.assert_awaited_once_with(123)


def test_defaults_when_reads_return_none():
    ctx = GuildContext(1, None, None, None)
    assert ctx.locale == "en"
    assert ctx.features == []
    assert ctx.settings == {}
    assert not ctx.is_enabled("anything")
    assert ctx.setting("anything") is None
