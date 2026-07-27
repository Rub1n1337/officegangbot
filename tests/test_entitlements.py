"""Unit tests for the entitlement -> per-guild premium mapping
(core.entitlements). Pure logic, no bot/DB."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from core.entitlements import premium_sku_id, entitlement_guild_state

SKU = 999


def _ent(**kw):
    kw.setdefault("sku_id", SKU)
    kw.setdefault("guild_id", 42)
    kw.setdefault("deleted", False)
    kw.setdefault("ends_at", None)
    kw.setdefault("id", 1)
    return SimpleNamespace(**kw)


def test_sku_env(monkeypatch):
    monkeypatch.setenv("DISCORD_PREMIUM_SKU_ID", "12345")
    assert premium_sku_id() == 12345
    monkeypatch.delenv("DISCORD_PREMIUM_SKU_ID", raising=False)
    assert premium_sku_id() is None
    monkeypatch.setenv("DISCORD_PREMIUM_SKU_ID", "not-an-int")
    assert premium_sku_id() is None


def test_none_when_sku_unconfigured():
    assert entitlement_guild_state(_ent(), None) is None


def test_none_for_other_sku():
    assert entitlement_guild_state(_ent(sku_id=1), SKU) is None


def test_none_for_user_subscription():
    # No guild_id -> a user subscription, not a per-server one.
    assert entitlement_guild_state(_ent(guild_id=None), SKU) is None


def test_active_guild_subscription():
    state = entitlement_guild_state(_ent(guild_id=42, ends_at=None), SKU)
    assert state == (42, True, None)


def test_future_end_is_active():
    future = datetime.now(timezone.utc) + timedelta(days=30)
    gid, active, ends = entitlement_guild_state(_ent(ends_at=future), SKU)
    assert (gid, active) == (42, True)
    assert ends == future


def test_past_end_is_inactive():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    _, active, _ = entitlement_guild_state(_ent(ends_at=past), SKU)
    assert active is False


def test_deleted_is_inactive():
    _, active, _ = entitlement_guild_state(_ent(deleted=True), SKU)
    assert active is False
