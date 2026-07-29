# core/db/command_overrides.py
"""Per-command overrides (mixin for DatabaseManager). Read on every command, so
cached in memory and invalidated on write."""
import time
from typing import Any, Dict, List


class _CommandOverridesMixin:
    _COMMAND_OVERRIDES_TTL = 300  # seconds

    @staticmethod
    def _row_to_override(row) -> Dict[str, Any]:
        return {
            "enabled": row["enabled"],
            "allowed_channels": list(row["allowed_channels"] or []),
            "ignored_channels": list(row["ignored_channels"] or []),
            "allowed_roles": list(row["allowed_roles"] or []),
            "ignored_roles": list(row["ignored_roles"] or []),
        }

    async def get_command_overrides(self, guild_id: int) -> Dict[str, Dict[str, Any]]:
        """{command: override} for the guild, cached. Serves the last-known value
        on a DB outage rather than raising (so the gate stays fail-open)."""
        cached = self._command_overrides_cache.get(guild_id)
        if cached is not None:
            data, stored_at = cached
            if time.time() - stored_at < self._COMMAND_OVERRIDES_TTL:
                return data
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM command_overrides WHERE guild_id = $1", guild_id
                )
            data = {r["command"]: self._row_to_override(r) for r in rows}
        except Exception:
            if cached is not None:
                return cached[0]
            raise
        self._command_overrides_cache[guild_id] = (data, time.time())
        return data

    async def set_command_override(
        self, guild_id: int, command: str, *,
        enabled: bool = True,
        allowed_channels: List[int] = None,
        ignored_channels: List[int] = None,
        allowed_roles: List[int] = None,
        ignored_roles: List[int] = None,
    ) -> None:
        """Upsert a command's override; delete the row when it's back to the
        default (enabled + no restrictions) to keep the table sparse."""
        allowed_channels = list(allowed_channels or [])
        ignored_channels = list(ignored_channels or [])
        allowed_roles = list(allowed_roles or [])
        ignored_roles = list(ignored_roles or [])
        await self.ensure_guild(guild_id)
        self._command_overrides_cache.pop(guild_id, None)
        is_default = enabled and not (allowed_channels or ignored_channels or allowed_roles or ignored_roles)
        async with self.pool.acquire() as conn:
            if is_default:
                await conn.execute(
                    "DELETE FROM command_overrides WHERE guild_id = $1 AND command = $2",
                    guild_id, command,
                )
                return
            await conn.execute(
                """
                INSERT INTO command_overrides
                    (guild_id, command, enabled, allowed_channels, ignored_channels, allowed_roles, ignored_roles)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (guild_id, command) DO UPDATE SET
                    enabled = EXCLUDED.enabled,
                    allowed_channels = EXCLUDED.allowed_channels,
                    ignored_channels = EXCLUDED.ignored_channels,
                    allowed_roles = EXCLUDED.allowed_roles,
                    ignored_roles = EXCLUDED.ignored_roles
                """,
                guild_id, command, enabled,
                allowed_channels, ignored_channels, allowed_roles, ignored_roles,
            )
