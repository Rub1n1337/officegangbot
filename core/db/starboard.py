# core/db/starboard.py
"""Starboard post mapping (mixin for DatabaseManager)."""
from typing import Any, Dict, Optional


class _StarboardMixin:
    async def get_starboard_post(self, message_id: int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM starboard_posts WHERE message_id = $1", message_id
            )
        return dict(row) if row else None

    async def upsert_starboard_post(
        self, message_id: int, guild_id: int, starboard_message_id: int, star_count: int
    ) -> None:
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO starboard_posts (message_id, guild_id, starboard_message_id, star_count)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (message_id) DO UPDATE SET
                    starboard_message_id = EXCLUDED.starboard_message_id,
                    star_count = EXCLUDED.star_count
                """,
                message_id, guild_id, starboard_message_id, star_count,
            )

    async def delete_starboard_post(self, message_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM starboard_posts WHERE message_id = $1", message_id)
