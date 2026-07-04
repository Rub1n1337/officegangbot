# core/guild_context.py
"""GuildContext — the three per-guild reads (locale, enabled features, settings)
that nearly every handler needs, fetched together in one place instead of as
separate awaits repeated across every cog (get_locale is called 50+ times,
get_enabled_features / get_guild_setting dozens more).
"""
import asyncio
from typing import Any, Dict, List, Optional


class GuildContext:
    """Bundles a guild's locale, enabled features and settings. Build one with
    ``await GuildContext.load(db, guild_id)`` and read ``ctx.locale``,
    ``ctx.is_enabled("automod")``, ``ctx.setting("punishment_log_id")``."""

    def __init__(self, guild_id: int, locale: Optional[str],
                 features: Optional[List[str]], settings: Optional[Dict[str, Any]]):
        self.guild_id = guild_id
        self.locale = locale or "en"
        self.features = features or []
        self.settings = settings or {}

    @classmethod
    async def load(cls, db, guild_id: int) -> "GuildContext":
        """Fetches locale + enabled features + settings for a guild concurrently."""
        locale, features, settings = await asyncio.gather(
            db.get_locale(guild_id),
            db.get_enabled_features(guild_id),
            db.get_all_guild_settings(guild_id),
        )
        return cls(guild_id, locale, features, settings)

    def is_enabled(self, feature: str) -> bool:
        return feature in self.features

    def setting(self, key: str, default: Optional[Any] = None) -> Any:
        return self.settings.get(key, default)
