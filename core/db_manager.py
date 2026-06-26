# core/db_manager.py
"""
Async PostgreSQL database manager using asyncpg connection pool.
Replaces the JSON-based SettingsManager for all persistent storage.
"""

import asyncpg
import os
import datetime
from typing import Optional, List, Dict, Any
from core.logger import logger


# Whitelist of column names allowed as `key` in get/set_guild_setting.
# Column names cannot be parameterized in SQL, so they are interpolated into
# the query string. Validating against this set prevents SQL injection if a
# `key` ever originates from an untrusted source. Must stay in sync with the
# `guilds` table columns in scripts/init_db.sql.
ALLOWED_GUILD_SETTINGS = frozenset({
    'prefix', 'punishment_log_id', 'usage_log_id', 'leave_log_id',
    'audit_log_id', 'welcome_channel_id', 'welcome_message', 'welcome_enabled',
    'autorole_id', 'rules_channel_id', 'rules_message_id', 'rules_message',
    'reaction_emoji', 'reaction_role_id', 'setup_complete', 'levels_enabled',
    'level_up_channel_id', 'automod_enabled', 'filter_enabled', 'filter_words',
    'ticket_support_role_id', 'ticket_category_id', 'enabled_features',
    'locale',
})


class DatabaseManager:
    """
    Async PostgreSQL manager with connection pooling via asyncpg.
    Initialize once at bot startup via connect(), close pool via close().
    """

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        # Per-guild locale cache (locale changes rarely; invalidated on set_locale).
        self._locale_cache: Dict[int, str] = {}

    async def connect(self) -> None:
        """Creates the asyncpg connection pool. Call this in bot.setup_hook()."""
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise ValueError("DATABASE_URL environment variable is not set.")
        try:
            self._pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            logger.info("PostgreSQL connection pool created successfully.")
            await self._init_schema()
        except Exception as e:
            logger.critical(f"Failed to connect to PostgreSQL: {e}", exc_info=True)
            raise

    async def close(self) -> None:
        """Closes the connection pool. Call this in bot.close()."""
        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL connection pool closed.")

    async def _init_schema(self) -> None:
        """Runs the SQL schema initialization script."""
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'init_db.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        async with self._pool.acquire() as conn:
            await conn.execute(schema_sql)
        logger.info("Database schema initialized.")

    @property
    def pool(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("DatabaseManager is not connected. Call connect() first.")
        return self._pool

    # -------------------------
    # Guild settings
    # -------------------------

    async def ensure_guild(self, guild_id: int) -> None:
        """Inserts guild row if it doesn't exist (upsert)."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guilds (guild_id) VALUES ($1)
                ON CONFLICT (guild_id) DO NOTHING
                """,
                guild_id
            )

    async def get_guild_setting(self, guild_id: int, key: str, default: Any = None) -> Any:
        """Returns a single guild setting by column name."""
        if key not in ALLOWED_GUILD_SETTINGS:
            raise ValueError(f"Invalid guild setting key: {key}")
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {key} FROM guilds WHERE guild_id = $1",
                guild_id
            )
            if row is None:
                return default
            value = row[key]
            return value if value is not None else default

    async def set_guild_setting(self, guild_id: int, key: str, value: Any) -> None:
        """Updates a single guild setting by column name."""
        if key not in ALLOWED_GUILD_SETTINGS:
            raise ValueError(f"Invalid guild setting key: {key}")
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE guilds SET {key} = $1, updated_at = NOW() WHERE guild_id = $2",
                value, guild_id
            )

    async def get_locale(self, guild_id: int) -> str:
        """Returns the guild's locale ('en'/'ru'), cached. Defaults to 'en'."""
        cached = self._locale_cache.get(guild_id)
        if cached is not None:
            return cached
        value = await self.get_guild_setting(guild_id, 'locale') or 'en'
        self._locale_cache[guild_id] = value
        return value

    async def set_locale(self, guild_id: int, locale: str) -> None:
        """Sets the guild's locale and updates the cache."""
        await self.set_guild_setting(guild_id, 'locale', locale)
        self._locale_cache[guild_id] = locale

    async def get_all_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """Returns all settings for a guild as a dict (excludes internal timestamp columns)."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM guilds WHERE guild_id = $1",
                guild_id
            )
            if not row:
                return {}
            data = dict(row)
            data.pop("created_at", None)
            data.pop("updated_at", None)
            return data

    async def get_enabled_features(self, guild_id: int) -> List[str]:
        """Returns the list of enabled features for a guild."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT enabled_features FROM guilds WHERE guild_id = $1",
                guild_id
            )
            if row is None:
                return []
            features = row['enabled_features']
            return features if features else []

    async def set_feature_enabled(self, guild_id: int, feature: str, enabled: bool) -> None:
        """Enables or disables a feature for a guild by adding/removing it from enabled_features."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            if enabled:
                await conn.execute(
                    """
                    UPDATE guilds
                    SET enabled_features = array_append(enabled_features, $1),
                        updated_at = NOW()
                    WHERE guild_id = $2 AND NOT ($1 = ANY(enabled_features))
                    """,
                    feature, guild_id
                )
            else:
                await conn.execute(
                    """
                    UPDATE guilds
                    SET enabled_features = array_remove(enabled_features, $1),
                        updated_at = NOW()
                    WHERE guild_id = $2
                    """,
                    feature, guild_id
                )

    # -------------------------
    # XP / Levels
    # -------------------------

    async def get_user_xp(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Returns XP data for a user."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT xp, level, display_name FROM users_xp WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )
            if row:
                return dict(row)
            return {'xp': 0, 'level': 0, 'display_name': None}

    async def upsert_user_xp(self, guild_id: int, user_id: int, xp: int, level: int, display_name: str) -> None:
        """Inserts or updates XP data for a user."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users_xp (guild_id, user_id, xp, level, display_name, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (guild_id, user_id) DO UPDATE
                SET xp = EXCLUDED.xp,
                    level = EXCLUDED.level,
                    display_name = EXCLUDED.display_name,
                    updated_at = NOW()
                """,
                guild_id, user_id, xp, level, display_name
            )

    async def bulk_upsert_xp(self, records: List[Dict[str, Any]]) -> None:
        """
        Bulk upsert XP records for multiple users at once.
        records: list of dicts with keys: guild_id, user_id, xp, level, display_name
        """
        if not records:
            return
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO users_xp (guild_id, user_id, xp, level, display_name, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (guild_id, user_id) DO UPDATE
                SET xp = EXCLUDED.xp,
                    level = EXCLUDED.level,
                    display_name = EXCLUDED.display_name,
                    updated_at = NOW()
                """,
                [(r['guild_id'], r['user_id'], r['xp'], r['level'], r['display_name']) for r in records]
            )
        logger.info(f"Bulk XP upsert: {len(records)} records.")

    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns top N users by XP for a guild."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, xp, level, display_name
                FROM users_xp
                WHERE guild_id = $1
                ORDER BY xp DESC
                LIMIT $2
                """,
                guild_id, limit
            )
            return [dict(r) for r in rows]

    # -------------------------
    # Warnings
    # -------------------------

    async def add_warning(self, guild_id: int, user_id: int, reason: str,
                          moderator_id: int, moderator_name: str) -> int:
        """Adds a warning and returns its ID."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO warnings (guild_id, user_id, reason, moderator_id, moderator_name)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                guild_id, user_id, reason, moderator_id, moderator_name
            )
            return row['id']

    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Returns all warnings for a user."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, reason, moderator_id, moderator_name, created_at
                FROM warnings
                WHERE guild_id = $1 AND user_id = $2
                ORDER BY created_at ASC
                """,
                guild_id, user_id
            )
            return [dict(r) for r in rows]

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        """Clears all warnings for a user. Returns count deleted."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )
            return int(result.split()[-1])

    # -------------------------
    # Timed Punishments
    # -------------------------

    async def add_timed_punishment(self, guild_id: int, user_id: int,
                                    punishment_type: str, expires_at: datetime.datetime,
                                    reason: str = None, moderator_id: int = None) -> None:
        """Adds or replaces a timed punishment."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO timed_punishments (guild_id, user_id, punishment_type, expires_at, reason, moderator_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (guild_id, user_id) DO UPDATE
                SET punishment_type = EXCLUDED.punishment_type,
                    expires_at = EXCLUDED.expires_at,
                    reason = EXCLUDED.reason,
                    moderator_id = EXCLUDED.moderator_id,
                    created_at = NOW()
                """,
                guild_id, user_id, punishment_type, expires_at, reason, moderator_id
            )

    async def get_expired_punishments(self) -> List[Dict[str, Any]]:
        """Returns all punishments that have expired."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT guild_id, user_id, punishment_type
                FROM timed_punishments
                WHERE expires_at <= NOW()
                """
            )
            return [dict(r) for r in rows]

    async def remove_timed_punishment(self, guild_id: int, user_id: int) -> None:
        """Removes a timed punishment after it has been lifted."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM timed_punishments WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )

    async def get_timed_punishments(self, guild_id: int) -> List[Dict[str, Any]]:
        """Returns all active timed punishments for a guild."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, punishment_type, expires_at, reason
                FROM timed_punishments
                WHERE guild_id = $1
                ORDER BY expires_at ASC
                """,
                guild_id
            )
            return [dict(r) for r in rows]

    # -------------------------
    # Level Roles
    # -------------------------

    async def set_level_role(self, guild_id: int, level: int, role_id: int) -> None:
        """Sets a role reward for a specific level."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO level_roles (guild_id, level, role_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, level) DO UPDATE SET role_id = EXCLUDED.role_id
                """,
                guild_id, level, role_id
            )

    async def get_level_roles(self, guild_id: int) -> Dict[int, int]:
        """Returns {level: role_id} mapping for a guild."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT level, role_id FROM level_roles WHERE guild_id = $1",
                guild_id
            )
            return {r['level']: r['role_id'] for r in rows}

    # -------------------------
    # Mod Roles
    # -------------------------

    async def set_mod_role(self, guild_id: int, role_id: int, role_type: str) -> None:
        """Adds a role to mod_roles table for a specific permission type."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mod_roles (guild_id, role_id, role_type)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, role_id, role_type) DO NOTHING
                """,
                guild_id, role_id, role_type
            )

    async def remove_mod_role(self, guild_id: int, role_type: str, role_id: int = None) -> None:
        """Removes roles from mod_roles. If role_id is provided, removes specific role; otherwise removes all roles of that type."""
        async with self.pool.acquire() as conn:
            if role_id:
                await conn.execute(
                    "DELETE FROM mod_roles WHERE guild_id = $1 AND role_type = $2 AND role_id = $3",
                    guild_id, role_type, role_id
                )
            else:
                await conn.execute(
                    "DELETE FROM mod_roles WHERE guild_id = $1 AND role_type = $2",
                    guild_id, role_type
                )

    async def get_mod_roles(self, guild_id: int) -> Dict[str, List[int]]:
        """Returns all mod roles for a guild grouped by type."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT role_id, role_type FROM mod_roles WHERE guild_id = $1",
                guild_id
            )
            result = {}
            for r in rows:
                rtype = r['role_type']
                if rtype not in result:
                    result[rtype] = []
                result[rtype].append(r['role_id'])
            return result

    # -------------------------
    # Reaction roles
    # -------------------------

    async def get_reaction_roles(self, guild_id: int, source: str = None) -> List[Dict[str, Any]]:
        """Returns reaction-role mappings for a guild, optionally filtered by source."""
        async with self.pool.acquire() as conn:
            if source is None:
                rows = await conn.fetch(
                    "SELECT channel_id, message_id, emoji, role_id, source "
                    "FROM reaction_roles WHERE guild_id = $1 ORDER BY id",
                    guild_id
                )
            else:
                rows = await conn.fetch(
                    "SELECT channel_id, message_id, emoji, role_id, source "
                    "FROM reaction_roles WHERE guild_id = $1 AND source = $2 ORDER BY id",
                    guild_id, source
                )
            return [dict(r) for r in rows]

    async def get_message_reaction_roles(self, guild_id: int, message_id: int) -> List[Dict[str, Any]]:
        """Returns reaction-role mappings on a specific message (emoji matched in Python)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT emoji, role_id, source FROM reaction_roles "
                "WHERE guild_id = $1 AND message_id = $2",
                guild_id, message_id
            )
            return [dict(r) for r in rows]

    async def replace_reaction_roles(self, guild_id: int, source: str, rows: List[Dict[str, Any]]) -> None:
        """Replaces all reaction roles of a given source for a guild with `rows`.
        Each row needs channel_id, message_id, emoji, role_id."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM reaction_roles WHERE guild_id = $1 AND source = $2",
                    guild_id, source
                )
                for r in rows:
                    await conn.execute(
                        """
                        INSERT INTO reaction_roles
                            (guild_id, channel_id, message_id, emoji, role_id, source)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (guild_id, message_id, emoji) DO UPDATE
                            SET role_id = EXCLUDED.role_id,
                                channel_id = EXCLUDED.channel_id,
                                source = EXCLUDED.source
                        """,
                        guild_id, int(r["channel_id"]), int(r["message_id"]),
                        str(r["emoji"]), int(r["role_id"]), source
                    )
