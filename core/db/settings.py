# core/db/settings.py
"""Per-guild settings, locale and feature flags (mixin for DatabaseManager)."""
import time

from typing import List, Dict, Any


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
    'ticket_support_role_id', 'ticket_category_id', 'ticket_auto_close_hours',
    'verification_role_id', 'ban_appeals_enabled', 'enabled_features',
    'locale', 'automod_block_invites', 'automod_block_links',
    'automod_allowed_domains', 'automod_spam_count', 'automod_spam_window',
    'automod_mention_limit', 'automod_block_mass_mentions',
})


class _SettingsMixin:

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

    async def save_settings_atomic(self, guild_id: int, settings: Dict[str, Any],
                                   enable_feature: str = None) -> None:
        """Writes several guild settings (whitelisted columns) and optionally
        enables a feature, all in one transaction — so a mid-save failure
        (e.g. the /setup wizard) can't leave a half-applied config."""
        for key in settings:
            if key not in ALLOWED_GUILD_SETTINGS:
                raise ValueError(f"Invalid guild setting key: {key}")
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for key, value in settings.items():
                    await conn.execute(
                        f"UPDATE guilds SET {key} = $1, updated_at = NOW() WHERE guild_id = $2",
                        value, guild_id,
                    )
                if enable_feature:
                    await conn.execute(
                        """
                        UPDATE guilds
                        SET enabled_features = array_append(enabled_features, $1),
                            updated_at = NOW()
                        WHERE guild_id = $2 AND NOT ($1 = ANY(enabled_features))
                        """,
                        enable_feature, guild_id,
                    )
        self._enabled_features_cache.pop(guild_id, None)
        if "locale" in settings:
            self._locale_cache[guild_id] = settings["locale"]

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

    # The bot is normally the only writer, but direct SQL edits (Supabase
    # console, admin scripts) bypass set_feature_enabled's invalidation — a
    # TTL bounds how stale the cache can get in that case.
    _ENABLED_FEATURES_TTL = 300  # seconds

    async def get_enabled_features(self, guild_id: int) -> List[str]:
        """Returns the list of enabled features for a guild, cached in memory
        (called on every message; invalidated on set_feature_enabled, expired
        by TTL to survive out-of-band DB edits)."""
        cached = self._enabled_features_cache.get(guild_id)
        if cached is not None:
            features, stored_at = cached
            if time.time() - stored_at < self._ENABLED_FEATURES_TTL:
                return features
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT enabled_features FROM guilds WHERE guild_id = $1",
                guild_id
            )
            features = list(row['enabled_features']) if row and row['enabled_features'] else []
        self._enabled_features_cache[guild_id] = (features, time.time())
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
