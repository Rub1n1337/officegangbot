"""Tests for the SQL-injection whitelist on guild-setting column names.

`get/set_guild_setting` interpolate the column name into the SQL string (column
names can't be parameterized), so an unknown key must be rejected *before* any
query is built. The validation happens before the coroutine awaits the pool, so
we can drive it with asyncio.run() without a live database.
"""
import asyncio

import pytest

from core.db_manager import DatabaseManager, ALLOWED_GUILD_SETTINGS


@pytest.mark.parametrize(
    "bad_key",
    [
        "id; DROP TABLE guilds",
        "prefix; DELETE FROM guilds",
        "unknown_column",
        "",
        "PREFIX",  # whitelist is case-sensitive on purpose
    ],
)
def test_get_rejects_unknown_key(bad_key):
    db = DatabaseManager()
    with pytest.raises(ValueError):
        asyncio.run(db.get_guild_setting(1, bad_key))


@pytest.mark.parametrize(
    "bad_key",
    [
        "id; DROP TABLE guilds",
        "unknown_column",
        "",
    ],
)
def test_set_rejects_unknown_key(bad_key):
    db = DatabaseManager()
    with pytest.raises(ValueError):
        asyncio.run(db.set_guild_setting(1, bad_key, "x"))


def test_allowed_key_passes_whitelist_then_needs_pool():
    # An allowed key must get *past* the whitelist; it then fails on the missing
    # connection pool (RuntimeError, not ValueError). Catching RuntimeError here
    # proves validation accepted the key rather than rejecting it.
    db = DatabaseManager()
    for key in ("prefix", "filter_words", "welcome_message"):
        with pytest.raises(RuntimeError):
            asyncio.run(db.get_guild_setting(1, key))


def test_whitelist_is_nonempty_and_immutable():
    assert len(ALLOWED_GUILD_SETTINGS) > 0
    assert isinstance(ALLOWED_GUILD_SETTINGS, frozenset)
