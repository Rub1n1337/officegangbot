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
    'locale', 'automod_block_invites', 'automod_block_links',
    'automod_allowed_domains', 'automod_spam_count', 'automod_spam_window',
    'automod_mention_limit', 'automod_block_mass_mentions',
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
        # Per-guild enabled-features cache. get_enabled_features is called on
        # every message (automod/filter/levels), so hitting Postgres each time
        # would hammer the DB on busy servers. Invalidated on set_feature_enabled.
        self._enabled_features_cache: Dict[int, List[str]] = {}
        # Per-guild AutoMod content-filter config (read on every message when
        # AutoMod is on). Invalidated on set_automod_config.
        self._automod_cache: Dict[int, Dict[str, Any]] = {}

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
        """Returns the list of enabled features for a guild, cached in memory
        (called on every message; invalidated on set_feature_enabled)."""
        cached = self._enabled_features_cache.get(guild_id)
        if cached is not None:
            return cached
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT enabled_features FROM guilds WHERE guild_id = $1",
                guild_id
            )
            features = list(row['enabled_features']) if row and row['enabled_features'] else []
        self._enabled_features_cache[guild_id] = features
        return features

    async def set_feature_enabled(self, guild_id: int, feature: str, enabled: bool) -> None:
        """Enables or disables a feature for a guild by adding/removing it from enabled_features."""
        await self.ensure_guild(guild_id)
        self._enabled_features_cache.pop(guild_id, None)  # invalidate the cache
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
    # Dashboard audit trail
    # -------------------------

    async def add_dashboard_audit(
        self, guild_id: int, *, actor_id: int, actor_name: str,
        action: str, target: str = None, detail: str = None,
    ) -> None:
        """Records a dashboard action (best-effort; never raises to the caller)."""
        try:
            await self.ensure_guild(guild_id)
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO dashboard_audit (guild_id, actor_id, actor_name, action, target, detail)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    guild_id, actor_id or None, (actor_name or None),
                    action, (target[:200] if target else None), (detail[:1000] if detail else None),
                )
        except Exception as e:
            logger.warning(f"Failed to write dashboard_audit for guild {guild_id}: {e}")

    async def get_dashboard_audit(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent dashboard audit entries for a guild."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, actor_id, actor_name, action, target, detail, created_at
                FROM dashboard_audit
                WHERE guild_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                guild_id, limit,
            )
            return [dict(r) for r in rows]

    async def get_recent_warnings(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent warnings across the whole guild (for the dashboard)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, reason, moderator_id, moderator_name, created_at
                FROM warnings
                WHERE guild_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                guild_id, limit
            )
            return [dict(r) for r in rows]

    async def delete_warning(self, guild_id: int, warning_id: int) -> bool:
        """Deletes a single warning by id. Returns True if a row was removed."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM warnings WHERE guild_id = $1 AND id = $2",
                guild_id, warning_id
            )
            return int(result.split()[-1]) > 0

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

    async def remove_level_role(self, guild_id: int, level: int) -> None:
        """Removes the role reward configured for a specific level."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM level_roles WHERE guild_id = $1 AND level = $2",
                guild_id, level
            )

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

    # --- Scheduled messages -------------------------------------------------

    async def get_scheduled_messages(self, guild_id: int) -> List[Dict[str, Any]]:
        """Returns a guild's scheduled messages, newest schedule first."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, channel_id, content, scheduled_at, repeat, enabled, last_sent_at "
                "FROM scheduled_messages WHERE guild_id = $1 ORDER BY scheduled_at",
                guild_id,
            )
            return [dict(r) for r in rows]

    async def replace_scheduled_messages(self, guild_id: int, rows: List[Dict[str, Any]]) -> None:
        """Replaces all of a guild's scheduled messages with `rows`. Each row needs
        channel_id, content, scheduled_at (datetime), repeat, enabled."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM scheduled_messages WHERE guild_id = $1", guild_id
                )
                for r in rows:
                    await conn.execute(
                        """
                        INSERT INTO scheduled_messages
                            (guild_id, channel_id, content, scheduled_at, repeat, enabled)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        guild_id, int(r["channel_id"]), str(r["content"]),
                        r["scheduled_at"], str(r["repeat"]), bool(r["enabled"]),
                    )

    async def get_due_scheduled_messages(self, now) -> List[Dict[str, Any]]:
        """Returns enabled scheduled messages (across all guilds) due at or before
        `now`, for the Scheduled Messages cog to post."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, guild_id, channel_id, content, scheduled_at, repeat "
                "FROM scheduled_messages WHERE enabled AND scheduled_at <= $1",
                now,
            )
            return [dict(r) for r in rows]

    async def advance_scheduled_message(self, message_id: int, next_at) -> None:
        """Reschedules a recurring message to its next run and records the send."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE scheduled_messages SET scheduled_at = $1, last_sent_at = NOW() WHERE id = $2",
                next_at, message_id,
            )

    async def disable_scheduled_message(self, message_id: int) -> None:
        """Marks a one-off message as sent (disabled) after it fires."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE scheduled_messages SET enabled = FALSE, last_sent_at = NOW() WHERE id = $1",
                message_id,
            )

    # --- AutoMod content-filter config -------------------------------------

    async def get_automod_config(self, guild_id: int) -> Dict[str, Any]:
        """Returns the guild's AutoMod content-filter config (cached, since it is
        read on every message while AutoMod is enabled)."""
        cached = self._automod_cache.get(guild_id)
        if cached is not None:
            return cached
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT automod_block_invites, automod_block_links, automod_allowed_domains, "
                "automod_spam_count, automod_spam_window, automod_mention_limit, "
                "automod_block_mass_mentions "
                "FROM guilds WHERE guild_id = $1",
                guild_id,
            )
        config = {
            "block_invites": bool(row["automod_block_invites"]) if row else False,
            "block_links": bool(row["automod_block_links"]) if row else False,
            "allowed_domains": list(row["automod_allowed_domains"]) if row and row["automod_allowed_domains"] else [],
            "spam_count": int(row["automod_spam_count"]) if row and row["automod_spam_count"] else 5,
            "spam_window": int(row["automod_spam_window"]) if row and row["automod_spam_window"] else 3,
            "mention_limit": int(row["automod_mention_limit"]) if row and row["automod_mention_limit"] else 5,
            "block_mass_mentions": bool(row["automod_block_mass_mentions"]) if row else False,
        }
        self._automod_cache[guild_id] = config
        return config

    async def set_automod_config(
        self,
        guild_id: int,
        block_invites: bool,
        block_links: bool,
        allowed_domains: List[str],
        spam_count: int = 5,
        spam_window: int = 3,
        mention_limit: int = 5,
        block_mass_mentions: bool = False,
    ) -> None:
        """Persists the AutoMod content-filter/anti-spam config and invalidates the cache."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE guilds SET automod_block_invites = $1, automod_block_links = $2, "
                "automod_allowed_domains = $3, automod_spam_count = $4, automod_spam_window = $5, "
                "automod_mention_limit = $6, automod_block_mass_mentions = $7, updated_at = NOW() "
                "WHERE guild_id = $8",
                bool(block_invites), bool(block_links), list(allowed_domains),
                int(spam_count), int(spam_window), int(mention_limit),
                bool(block_mass_mentions), guild_id,
            )
        self._automod_cache.pop(guild_id, None)

    # --- Role menus --------------------------------------------------------

    async def get_reaction_menus(self, guild_id: int) -> List[Dict[str, Any]]:
        """Returns the guild's role menus, each with its emoji->role items
        (resolved from reaction_roles where source='menu')."""
        async with self.pool.acquire() as conn:
            menus = await conn.fetch(
                "SELECT id, channel_id, message_id, title, description "
                "FROM reaction_menus WHERE guild_id = $1 ORDER BY id",
                guild_id,
            )
            items = await conn.fetch(
                "SELECT message_id, emoji, role_id FROM reaction_roles "
                "WHERE guild_id = $1 AND source = 'menu'",
                guild_id,
            )
        by_msg: Dict[int, List[Dict[str, Any]]] = {}
        for it in items:
            by_msg.setdefault(it["message_id"], []).append(
                {"emoji": it["emoji"], "role_id": it["role_id"]}
            )
        result = []
        for m in menus:
            md = dict(m)
            md["items"] = by_msg.get(m["message_id"], []) if m["message_id"] else []
            result.append(md)
        return result

    async def create_reaction_menu(self, guild_id: int, channel_id: int, title: str, description: str) -> int:
        """Inserts a role menu (message not posted yet) and returns its id."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO reaction_menus (guild_id, channel_id, title, description) "
                "VALUES ($1, $2, $3, $4) RETURNING id",
                guild_id, int(channel_id), str(title)[:256], str(description),
            )
        return row["id"]

    async def update_reaction_menu(self, menu_id: int, channel_id: int, title: str, description: str, message_id) -> None:
        """Updates a role menu's channel/title/description and posted message id."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE reaction_menus SET channel_id = $1, title = $2, description = $3, message_id = $4 WHERE id = $5",
                int(channel_id), str(title)[:256], str(description),
                int(message_id) if message_id else None, menu_id,
            )

    async def delete_reaction_menu(self, menu_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM reaction_menus WHERE id = $1", menu_id)

    async def replace_message_reaction_roles(self, guild_id: int, message_id: int, source: str, rows: List[Dict[str, Any]]) -> None:
        """Replaces the reaction roles on a single message (used by role menus,
        which have many messages per guild — unlike replace_reaction_roles, which
        clears a whole source)."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM reaction_roles WHERE guild_id = $1 AND message_id = $2 AND source = $3",
                    guild_id, int(message_id), source,
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
                        str(r["emoji"]), int(r["role_id"]), source,
                    )
