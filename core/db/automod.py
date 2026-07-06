# core/db/automod.py
"""AutoMod config, strikes and custom rules (mixin for DatabaseManager)."""
from typing import List, Dict, Any


class _AutomodMixin:

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
                "automod_block_mass_mentions, automod_strikes_enabled, automod_strike_expiry_hours, "
                "automod_strike_mute_at, automod_strike_kick_at, automod_strike_ban_at, automod_dry_run, "
                "automod_ignored_channels, automod_ignored_roles, filter_words "
                "FROM guilds WHERE guild_id = $1",
                guild_id,
            )
            rule_rows = await conn.fetch(
                "SELECT id, pattern, action, enabled FROM automod_rules WHERE guild_id = $1 ORDER BY id",
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
            "strikes_enabled": bool(row["automod_strikes_enabled"]) if row else False,
            "strike_expiry_hours": int(row["automod_strike_expiry_hours"]) if row and row["automod_strike_expiry_hours"] is not None else 24,
            "strike_mute_at": int(row["automod_strike_mute_at"]) if row and row["automod_strike_mute_at"] is not None else 3,
            "strike_kick_at": int(row["automod_strike_kick_at"]) if row and row["automod_strike_kick_at"] is not None else 5,
            "strike_ban_at": int(row["automod_strike_ban_at"]) if row and row["automod_strike_ban_at"] is not None else 0,
            "dry_run": bool(row["automod_dry_run"]) if row else False,
            "ignored_channels": [int(x) for x in row["automod_ignored_channels"]] if row and row["automod_ignored_channels"] else [],
            "ignored_roles": [int(x) for x in row["automod_ignored_roles"]] if row and row["automod_ignored_roles"] else [],
            # The banned-words list lives in the legacy filter_words column (the
            # standalone word filter merged into AutoMod), so existing lists
            # carry over without a data migration.
            "banned_words": list(row["filter_words"]) if row and row["filter_words"] else [],
            "rules": [
                {"id": r["id"], "pattern": r["pattern"], "action": r["action"], "enabled": bool(r["enabled"])}
                for r in rule_rows
            ],
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
        dry_run: bool = False,
        ignored_channels: List[int] = None,
        ignored_roles: List[int] = None,
    ) -> None:
        """Persists the AutoMod content-filter/anti-spam config and invalidates the cache."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE guilds SET automod_block_invites = $1, automod_block_links = $2, "
                "automod_allowed_domains = $3, automod_spam_count = $4, automod_spam_window = $5, "
                "automod_mention_limit = $6, automod_block_mass_mentions = $7, automod_dry_run = $8, "
                "automod_ignored_channels = $9, automod_ignored_roles = $10, "
                "updated_at = NOW() WHERE guild_id = $11",
                bool(block_invites), bool(block_links), list(allowed_domains),
                int(spam_count), int(spam_window), int(mention_limit),
                bool(block_mass_mentions), bool(dry_run),
                [int(c) for c in (ignored_channels or [])],
                [int(r) for r in (ignored_roles or [])],
                guild_id,
            )
        self._automod_cache.pop(guild_id, None)

    async def set_filter_words(self, guild_id: int, words: List[str]) -> None:
        """Persists the banned-words list (legacy filter_words column) and
        invalidates the automod cache — the words are enforced by AutoMod, so a
        plain set_guild_setting write would leave a stale compiled pattern."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE guilds SET filter_words = $1, updated_at = NOW() WHERE guild_id = $2",
                [str(w) for w in (words or [])], guild_id,
            )
        self._automod_cache.pop(guild_id, None)

    async def set_automod_strikes(
        self,
        guild_id: int,
        enabled: bool,
        expiry_hours: int,
        mute_at: int,
        kick_at: int,
        ban_at: int,
    ) -> None:
        """Persists the AutoMod strike-escalation config and invalidates the cache."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE guilds SET automod_strikes_enabled = $1, automod_strike_expiry_hours = $2, "
                "automod_strike_mute_at = $3, automod_strike_kick_at = $4, automod_strike_ban_at = $5, "
                "updated_at = NOW() WHERE guild_id = $6",
                bool(enabled), int(expiry_hours), int(mute_at), int(kick_at), int(ban_at), guild_id,
            )
        self._automod_cache.pop(guild_id, None)

    async def replace_automod_rules(self, guild_id: int, rules: List[Dict[str, Any]]) -> None:
        """Replaces all custom regex rules for a guild (already sanitized upstream)
        and invalidates the automod cache."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM automod_rules WHERE guild_id = $1", guild_id)
                for r in rules:
                    await conn.execute(
                        "INSERT INTO automod_rules (guild_id, pattern, action, enabled) "
                        "VALUES ($1, $2, $3, $4)",
                        guild_id, str(r["pattern"])[:200], str(r.get("action", "delete"))[:10],
                        bool(r.get("enabled", True)),
                    )
        self._automod_cache.pop(guild_id, None)

    async def add_strike(self, guild_id: int, user_id: int, reason: str, expiry_hours: int = 24) -> int:
        """Records a strike and returns the number of active strikes for the user
        within the decay window (expiry_hours; 0 means strikes never decay)."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO automod_strikes (guild_id, user_id, reason) VALUES ($1, $2, $3)",
                guild_id, int(user_id), str(reason)[:200] if reason else None,
            )
            if expiry_hours and int(expiry_hours) > 0:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM automod_strikes WHERE guild_id = $1 AND user_id = $2 "
                    "AND created_at > NOW() - ($3 || ' hours')::interval",
                    guild_id, int(user_id), str(int(expiry_hours)),
                )
            else:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM automod_strikes WHERE guild_id = $1 AND user_id = $2",
                    guild_id, int(user_id),
                )
        return int(count)

    async def get_active_strikes(self, guild_id: int) -> Dict[str, Any]:
        """Summarises AutoMod strikes per user for the dashboard: how many are
        currently active (inside the decay window) and when each user's oldest
        active strike will decay, so the UI can show "N strikes, next expires
        in X". Also returns the strike-escalation config for context."""
        async with self.pool.acquire() as conn:
            cfg = await conn.fetchrow(
                "SELECT automod_strikes_enabled, automod_strike_expiry_hours, "
                "automod_strike_mute_at, automod_strike_kick_at, automod_strike_ban_at "
                "FROM guilds WHERE guild_id = $1",
                guild_id,
            )
            expiry = int(cfg["automod_strike_expiry_hours"]) if cfg and cfg["automod_strike_expiry_hours"] is not None else 24
            if expiry > 0:
                rows = await conn.fetch(
                    "SELECT user_id, COUNT(*) AS count, "
                    "MIN(created_at) + ($2 || ' hours')::interval AS next_decay, "
                    "MAX(created_at) AS last_strike "
                    "FROM automod_strikes WHERE guild_id = $1 "
                    "AND created_at > NOW() - ($2 || ' hours')::interval "
                    "GROUP BY user_id ORDER BY count DESC, last_strike DESC",
                    guild_id, str(expiry),
                )
            else:
                # No decay: every strike counts forever, so there is no expiry.
                rows = await conn.fetch(
                    "SELECT user_id, COUNT(*) AS count, "
                    "NULL::timestamptz AS next_decay, MAX(created_at) AS last_strike "
                    "FROM automod_strikes WHERE guild_id = $1 "
                    "GROUP BY user_id ORDER BY count DESC, last_strike DESC",
                    guild_id,
                )
        return {
            "enabled": bool(cfg["automod_strikes_enabled"]) if cfg else False,
            "expiry_hours": expiry,
            "mute_at": int(cfg["automod_strike_mute_at"]) if cfg and cfg["automod_strike_mute_at"] is not None else 0,
            "kick_at": int(cfg["automod_strike_kick_at"]) if cfg and cfg["automod_strike_kick_at"] is not None else 0,
            "ban_at": int(cfg["automod_strike_ban_at"]) if cfg and cfg["automod_strike_ban_at"] is not None else 0,
            "users": [dict(r) for r in rows],
        }
