"""Integration tests against a real PostgreSQL and Redis.

These run in CI (service containers provide DATABASE_URL / REDIS_URL) and skip
themselves locally when those env vars aren't set, so the normal `pytest` run
stays infra-free. They use the same asyncio.run() driving style as the other
tests, so no pytest-asyncio is needed.
"""
import asyncio
import os

import pytest

DB_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

TEST_GUILD = 999999999999999999


@pytest.mark.skipif(not DB_URL, reason="DATABASE_URL not set (DB integration test)")
def test_database_roundtrips():
    asyncio.run(_db_roundtrips())


async def _db_roundtrips():
    from core.db_manager import DatabaseManager

    db = DatabaseManager()
    await db.connect()  # also applies scripts/init_db.sql
    try:
        gid = TEST_GUILD
        # Clean slate (FKs cascade from guilds).
        await db.pool.execute("DELETE FROM guilds WHERE guild_id = $1", gid)
        await db.ensure_guild(gid)

        # Locale defaults to 'en', then round-trips.
        assert await db.get_locale(gid) == "en"
        await db.set_locale(gid, "ru")
        assert await db.get_locale(gid) == "ru"

        # Whitelisted guild-setting column round-trip.
        await db.set_guild_setting(gid, "welcome_message", "hi {user.mention}")
        assert await db.get_guild_setting(gid, "welcome_message") == "hi {user.mention}"

        # Enabled features.
        await db.set_feature_enabled(gid, "filter", True)
        assert "filter" in await db.get_enabled_features(gid)
        await db.set_feature_enabled(gid, "filter", False)
        assert "filter" not in await db.get_enabled_features(gid)

        # Mod roles (the schema that previously crashed /config role).
        await db.set_mod_role(gid, 424242, "kick")
        assert 424242 in (await db.get_mod_roles(gid)).get("kick", [])
        await db.remove_mod_role(gid, "kick", 424242)
        assert 424242 not in (await db.get_mod_roles(gid)).get("kick", [])

        # Warnings add / read / clear.
        await db.add_warning(gid, 111, "spam", 222, "Mod#0001")
        warns = await db.get_warnings(gid, 111)
        assert len(warns) == 1 and warns[0]["reason"] == "spam"
        assert await db.clear_warnings(gid, 111) == 1
        assert await db.get_warnings(gid, 111) == []

        # Analytics aggregation. Regression: the window parameter is bound to a
        # $2::interval cast, so asyncpg requires a timedelta — a plain
        # '30 days' string raised DataError in production (only reproducible
        # against a live PG, since it's prepared-statement type inference).
        await db.bulk_add_activity([{"guild_id": gid, "weekday": 0, "hour": 12, "delta": 3}])
        await db.bulk_add_activity([{"guild_id": gid, "weekday": 0, "hour": 12, "delta": 2}])
        case_no = await db.add_mod_case(gid, "warn", 111, "user", 222, "Mod#0001", "spam")
        assert case_no == 1
        analytics = await db.get_analytics(gid, 30)
        assert analytics["days"] == 30
        assert {"weekday": 0, "hour": 12, "count": 5} in analytics["heatmap"]
        assert sum(r["count"] for r in analytics["modActionsByDay"]) == 1
        assert analytics["topModerators"][0]["name"] == "Mod#0001"
    finally:
        try:
            await db.pool.execute("DELETE FROM guilds WHERE guild_id = $1", TEST_GUILD)
        except Exception:
            pass
        await db.close()


@pytest.mark.skipif(not REDIS_URL, reason="REDIS_URL not set (Redis integration test)")
def test_redis_roundtrips():
    asyncio.run(_redis_roundtrips())


async def _redis_roundtrips():
    from core.redis_manager import RedisManager

    r = RedisManager()
    await r.connect()
    try:
        await r.set("test:int:key", {"a": 1, "b": [2, 3]}, ttl=30)
        assert await r.get("test:int:key") == {"a": 1, "b": [2, 3]}
        await r.delete("test:int:key")
        assert await r.get("test:int:key") is None

        await r.set_xp_data(1, 2, {"xp": 50, "level": 1, "display_name": "x"})
        data = await r.get_xp_data(1, 2)
        assert data is not None and data["xp"] == 50
    finally:
        await r.close()
