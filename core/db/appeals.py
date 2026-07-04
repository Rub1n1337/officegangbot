# core/db/appeals.py
"""Ban appeals (mixin for DatabaseManager)."""
from typing import Optional, List, Dict, Any


class _AppealsMixin:

    # --- Ban appeals -------------------------------------------------------

    async def add_ban_appeal(self, guild_id: int, user_id: int, user_name: str, reason: str) -> None:
        """Records (or replaces) a banned user's appeal. One active appeal per
        (guild, user): re-submitting overwrites the text and reopens it."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO ban_appeals (guild_id, user_id, user_name, reason, status, created_at) "
                "VALUES ($1, $2, $3, $4, 'pending', NOW()) "
                "ON CONFLICT (guild_id, user_id) DO UPDATE SET "
                "user_name = EXCLUDED.user_name, reason = EXCLUDED.reason, "
                "status = 'pending', created_at = NOW(), "
                "decided_by_id = NULL, decided_by_name = NULL, decided_at = NULL",
                guild_id, int(user_id), str(user_name)[:100] if user_name else None,
                str(reason)[:2000] if reason else None,
            )

    async def get_ban_appeals(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns a guild's ban appeals, pending first then most recent."""
        limit = max(1, min(int(limit), 200))
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, user_id, user_name, reason, status, decided_by_name, "
                "created_at, decided_at FROM ban_appeals WHERE guild_id = $1 "
                "ORDER BY (status = 'pending') DESC, created_at DESC LIMIT $2",
                guild_id, limit,
            )
        return [dict(r) for r in rows]

    async def decide_ban_appeal(
        self, appeal_id: int, guild_id: int, status: str,
        decided_by_id: Optional[int], decided_by_name: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Marks a pending appeal approved/denied and returns the row (incl.
        user_id so the caller can unban / DM). Returns None if it wasn't pending."""
        if status not in ("approved", "denied"):
            return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE ban_appeals SET status = $1, decided_by_id = $2, "
                "decided_by_name = $3, decided_at = NOW() "
                "WHERE id = $4 AND guild_id = $5 AND status = 'pending' RETURNING *",
                status, int(decided_by_id) if decided_by_id else None,
                str(decided_by_name)[:100] if decided_by_name else None,
                int(appeal_id), guild_id,
            )
        return dict(row) if row else None
