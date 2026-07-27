# core/db/premium.py
"""Per-guild premium status (mixin for DatabaseManager).

Premium can be granted two ways:
- the ``PREMIUM_GUILD_IDS`` env allowlist — the manual grant used until billing
  is wired (comma/space-separated guild ids), and
- an active row in the ``guild_premium`` table — where the future billing
  webhook writes.

``is_premium()`` treats a guild as premium if EITHER source says so.
"""
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class _PremiumMixin:
    # Premium status changes rarely and is read on dashboard loads, so a short
    # in-memory TTL avoids hitting Postgres on every guild-info request.
    _PREMIUM_TTL = 300  # seconds

    @staticmethod
    def _premium_allowlist() -> set:
        """Guild ids granted premium via the PREMIUM_GUILD_IDS env var
        (comma/space-separated). Empty when unset."""
        raw = os.getenv("PREMIUM_GUILD_IDS", "")
        out = set()
        for tok in raw.replace(",", " ").split():
            try:
                out.add(int(tok))
            except ValueError:
                continue
        return out

    async def is_premium(self, guild_id: int) -> bool:
        """True if the guild has premium — via the env allowlist or an active
        ``guild_premium`` row (not expired). Cached in memory (TTL-bounded);
        falls back to the last-known value on a DB outage."""
        if guild_id in self._premium_allowlist():
            return True
        cached = self._premium_cache.get(guild_id)
        if cached is not None:
            value, stored_at = cached
            if time.time() - stored_at < self._PREMIUM_TTL:
                return value
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT active, current_period_end FROM guild_premium WHERE guild_id = $1",
                    guild_id,
                )
        except Exception:
            # DB outage: serve the last-known value rather than downgrading a
            # paying server to free mid-incident.
            if cached is not None:
                return cached[0]
            raise
        value = bool(
            row
            and row["active"]
            and (
                row["current_period_end"] is None
                or row["current_period_end"] > datetime.now(timezone.utc)
            )
        )
        self._premium_cache[guild_id] = (value, time.time())
        return value

    async def get_premium(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """The full premium row for a guild (None if there is none). For
        inspection / admin tooling."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM guild_premium WHERE guild_id = $1", guild_id
            )
        return dict(row) if row else None

    async def set_premium(
        self,
        guild_id: int,
        *,
        active: bool = True,
        plan: str = "premium",
        current_period_end: Optional[datetime] = None,
        provider: Optional[str] = None,
        provider_customer_id: Optional[str] = None,
        provider_subscription_id: Optional[str] = None,
    ) -> None:
        """Upserts a guild's premium status. Written by the billing webhook
        (Phase 3) or an admin script; invalidates the cache so the change is
        visible immediately."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guild_premium (
                    guild_id, active, plan, current_period_end,
                    provider, provider_customer_id, provider_subscription_id, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                ON CONFLICT (guild_id) DO UPDATE SET
                    active = EXCLUDED.active,
                    plan = EXCLUDED.plan,
                    current_period_end = EXCLUDED.current_period_end,
                    provider = EXCLUDED.provider,
                    provider_customer_id = EXCLUDED.provider_customer_id,
                    provider_subscription_id = EXCLUDED.provider_subscription_id,
                    updated_at = NOW()
                """,
                guild_id,
                active,
                plan,
                current_period_end,
                provider,
                provider_customer_id,
                provider_subscription_id,
            )
        self._premium_cache.pop(guild_id, None)
