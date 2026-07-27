"""Unit tests for premium status resolution (core.db.premium._PremiumMixin.
is_premium), using a fake asyncpg pool and the PREMIUM_GUILD_IDS env allowlist."""
import asyncio
from datetime import datetime, timedelta, timezone

import discord

from core.db.premium import _PremiumMixin
from core.discord_utils import guild_accent_color


class _FakeConn:
    def __init__(self, row):
        self._row = row
        self.calls = 0

    async def fetchrow(self, *args, **kwargs):
        self.calls += 1
        return self._row


class _FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class _FakePool:
    def __init__(self, row):
        self.conn = _FakeConn(row)

    def acquire(self):
        return _FakeAcquire(self.conn)


def _db(row):
    db = _PremiumMixin()
    db._premium_cache = {}
    db.pool = _FakePool(row)
    return db


def _run(coro):
    return asyncio.run(coro)


def test_allowlist_grants_without_db(monkeypatch):
    monkeypatch.setenv("PREMIUM_GUILD_IDS", "123, 456 789")
    db = _db(row=None)  # DB would say "not premium"
    assert _run(db.is_premium(123)) is True
    assert _run(db.is_premium(789)) is True
    # allowlist hit short-circuits before touching the pool
    assert db.pool.conn.calls == 0


def test_active_row_is_premium(monkeypatch):
    monkeypatch.delenv("PREMIUM_GUILD_IDS", raising=False)
    db = _db(row={"active": True, "current_period_end": None})
    assert _run(db.is_premium(1)) is True


def test_inactive_row_is_not_premium(monkeypatch):
    monkeypatch.delenv("PREMIUM_GUILD_IDS", raising=False)
    db = _db(row={"active": False, "current_period_end": None})
    assert _run(db.is_premium(1)) is False


def test_expired_period_is_not_premium(monkeypatch):
    monkeypatch.delenv("PREMIUM_GUILD_IDS", raising=False)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    db = _db(row={"active": True, "current_period_end": past})
    assert _run(db.is_premium(1)) is False


def test_future_period_is_premium(monkeypatch):
    monkeypatch.delenv("PREMIUM_GUILD_IDS", raising=False)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    db = _db(row={"active": True, "current_period_end": future})
    assert _run(db.is_premium(1)) is True


def test_no_row_is_not_premium(monkeypatch):
    monkeypatch.delenv("PREMIUM_GUILD_IDS", raising=False)
    db = _db(row=None)
    assert _run(db.is_premium(1)) is False


def test_result_is_cached(monkeypatch):
    monkeypatch.delenv("PREMIUM_GUILD_IDS", raising=False)
    db = _db(row={"active": True, "current_period_end": None})
    assert _run(db.is_premium(42)) is True
    assert _run(db.is_premium(42)) is True
    # second call served from cache — DB queried only once
    assert db.pool.conn.calls == 1


def test_db_outage_falls_back_to_cache(monkeypatch):
    monkeypatch.delenv("PREMIUM_GUILD_IDS", raising=False)
    db = _db(row={"active": True, "current_period_end": None})
    assert _run(db.is_premium(7)) is True
    # expire the cache and make the pool raise on the next query
    db._premium_cache[7] = (db._premium_cache[7][0], 0.0)

    class _BoomPool:
        def acquire(self):
            raise RuntimeError("db down")

    db.pool = _BoomPool()
    assert _run(db.is_premium(7)) is True  # last-known value, not an error


# --- guild_accent_color (premium embed branding) ---------------------------

class _FakeColorDB:
    def __init__(self, premium, color):
        self._premium = premium
        self._color = color

    async def is_premium(self, guild_id):
        return self._premium

    async def get_guild_setting(self, guild_id, key, default=None):
        return self._color


DEFAULT = discord.Color.gold()


def test_accent_color_premium_with_color():
    db = _FakeColorDB(premium=True, color=0x5865F2)
    assert _run(guild_accent_color(db, 1, DEFAULT)) == discord.Color(0x5865F2)


def test_accent_color_premium_without_color_is_default():
    db = _FakeColorDB(premium=True, color=None)
    assert _run(guild_accent_color(db, 1, DEFAULT)) == DEFAULT


def test_accent_color_free_is_default_even_if_color_set():
    db = _FakeColorDB(premium=False, color=0x5865F2)
    assert _run(guild_accent_color(db, 1, DEFAULT)) == DEFAULT


def test_accent_color_bad_value_falls_back_to_default():
    db = _FakeColorDB(premium=True, color="not-an-int")
    assert _run(guild_accent_color(db, 1, DEFAULT)) == DEFAULT
