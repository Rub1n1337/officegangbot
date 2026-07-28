# core/db/custom_commands.py
"""Per-guild custom /tag commands (mixin for DatabaseManager)."""
import time
from typing import Dict, List


class _CustomCommandsMixin:
    _CUSTOM_COMMANDS_TTL = 300  # seconds

    async def get_custom_commands(self, guild_id: int) -> List[Dict[str, str]]:
        """The guild's custom commands as [{name, response}], cached in memory
        (read on every /tag autocomplete keystroke). Serves the last-known value
        on a DB outage rather than raising."""
        cached = self._custom_commands_cache.get(guild_id)
        if cached is not None:
            rows, stored_at = cached
            if time.time() - stored_at < self._CUSTOM_COMMANDS_TTL:
                return rows
        try:
            async with self.pool.acquire() as conn:
                records = await conn.fetch(
                    "SELECT name, response FROM custom_commands WHERE guild_id = $1 ORDER BY name",
                    guild_id,
                )
            rows = [{"name": r["name"], "response": r["response"]} for r in records]
        except Exception:
            if cached is not None:
                return cached[0]
            raise
        self._custom_commands_cache[guild_id] = (rows, time.time())
        return rows

    async def replace_custom_commands(self, guild_id: int, rows: List[Dict[str, str]]) -> None:
        """Replaces the guild's custom commands with ``rows`` (already sanitized)
        in one transaction; invalidates the cache."""
        await self.ensure_guild(guild_id)
        self._custom_commands_cache.pop(guild_id, None)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM custom_commands WHERE guild_id = $1", guild_id)
                if rows:
                    await conn.executemany(
                        "INSERT INTO custom_commands (guild_id, name, response) VALUES ($1, $2, $3)",
                        [(guild_id, r["name"], r["response"]) for r in rows],
                    )
