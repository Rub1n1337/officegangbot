# core/db/giveaways.py
"""Giveaways persistence (mixin for DatabaseManager)."""
from datetime import datetime
from typing import Any, Dict, List, Optional


class _GiveawaysMixin:
    async def create_giveaway(
        self, guild_id: int, channel_id: int, prize: str,
        winners_count: int, ends_at: datetime, created_by: int,
    ) -> int:
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO giveaways (guild_id, channel_id, prize, winners_count, ends_at, created_by)
                VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
                """,
                guild_id, channel_id, prize, winners_count, ends_at, created_by,
            )

    async def set_giveaway_message(self, giveaway_id: int, message_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE giveaways SET message_id = $2 WHERE id = $1", giveaway_id, message_id
            )

    async def add_giveaway_entry(self, giveaway_id: int, user_id: int) -> bool:
        """Adds an entry; returns True if newly added, False if already entered."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                INSERT INTO giveaway_entries (giveaway_id, user_id) VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                giveaway_id, user_id,
            )
        return result.endswith("1")

    async def get_giveaway_entries(self, giveaway_id: int) -> List[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT user_id FROM giveaway_entries WHERE giveaway_id = $1", giveaway_id
            )
        return [r["user_id"] for r in rows]

    async def get_giveaway(self, guild_id: int, giveaway_id: int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM giveaways WHERE id = $1 AND guild_id = $2", giveaway_id, guild_id
            )
        return dict(row) if row else None

    async def get_giveaway_by_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM giveaways WHERE message_id = $1", message_id
            )
        return dict(row) if row else None

    async def get_due_giveaways(self, now: datetime) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM giveaways WHERE ended = FALSE AND ends_at <= $1", now
            )
        return [dict(r) for r in rows]

    async def list_active_giveaways(self, guild_id: int) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM giveaways WHERE guild_id = $1 AND ended = FALSE ORDER BY ends_at",
                guild_id,
            )
        return [dict(r) for r in rows]

    async def count_active_giveaways(self, guild_id: int) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM giveaways WHERE guild_id = $1 AND ended = FALSE", guild_id
            )

    async def mark_giveaway_ended(self, giveaway_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE giveaways SET ended = TRUE WHERE id = $1", giveaway_id)
