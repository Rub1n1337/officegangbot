# core/db/polls.py
"""Polls persistence (mixin for DatabaseManager).

A poll row holds the question + options (TEXT[]) and its message; each vote is a
(poll_id, user_id, option_index) row, so single- and multi-choice are the same
storage — the difference is the toggle logic in core.polls.apply_vote.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


class _PollsMixin:
    async def create_poll(
        self, guild_id: int, channel_id: int, question: str, options: List[str],
        allow_multi: bool, ends_at: Optional[datetime], created_by: int,
    ) -> int:
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO polls (guild_id, channel_id, question, options, allow_multi, ends_at, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
                """,
                guild_id, channel_id, question, options, allow_multi, ends_at, created_by,
            )

    async def set_poll_message(self, poll_id: int, message_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE polls SET message_id = $2 WHERE id = $1", poll_id, message_id)

    async def get_poll(self, guild_id: int, poll_id: int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM polls WHERE id = $1 AND guild_id = $2", poll_id, guild_id
            )
        return dict(row) if row else None

    async def get_poll_by_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM polls WHERE message_id = $1", message_id)
        return dict(row) if row else None

    async def get_user_poll_votes(self, poll_id: int, user_id: int) -> Set[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT option_index FROM poll_votes WHERE poll_id = $1 AND user_id = $2",
                poll_id, user_id,
            )
        return {r["option_index"] for r in rows}

    async def set_user_poll_votes(self, poll_id: int, user_id: int, options: Set[int]) -> None:
        """Replace a user's votes for a poll with ``options`` (empty = cleared)."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM poll_votes WHERE poll_id = $1 AND user_id = $2", poll_id, user_id
                )
                if options:
                    await conn.executemany(
                        "INSERT INTO poll_votes (poll_id, user_id, option_index) VALUES ($1, $2, $3)",
                        [(poll_id, user_id, idx) for idx in options],
                    )

    async def get_poll_counts(self, poll_id: int, num_options: int) -> List[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT option_index, COUNT(*) AS n FROM poll_votes WHERE poll_id = $1 GROUP BY option_index",
                poll_id,
            )
        counts = [0] * num_options
        for r in rows:
            idx = r["option_index"]
            if 0 <= idx < num_options:
                counts[idx] = int(r["n"])
        return counts

    async def close_poll(self, poll_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE polls SET closed = TRUE WHERE id = $1", poll_id)

    async def get_due_polls(self, now: datetime) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM polls WHERE closed = FALSE AND ends_at IS NOT NULL AND ends_at <= $1",
                now,
            )
        return [dict(r) for r in rows]
