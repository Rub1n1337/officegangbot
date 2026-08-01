# core/db/invites.py
"""Invite-tracking persistence (mixin for DatabaseManager).

One row per member join in ``invite_joins``, attributed to the invite code and
its creator. ``left_at`` is stamped when the member later leaves, so a
leaderboard can discount invites that didn't stick. (``left`` is a SQL reserved
word, so counts of departed members are aliased ``parted`` in queries.)
"""
from typing import Any, Dict, List, Optional


class _InvitesMixin:
    async def record_invite_join(
        self, guild_id: int, member_id: int, inviter_id: Optional[int], invite_code: Optional[str]
    ) -> None:
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO invite_joins (guild_id, member_id, inviter_id, invite_code)
                VALUES ($1, $2, $3, $4)
                """,
                guild_id, member_id, inviter_id, invite_code,
            )

    async def mark_invite_left(self, guild_id: int, member_id: int) -> None:
        """Stamp the member's most recent still-present join as left. A no-op if
        we never recorded their join (e.g. it predates the tracker)."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE invite_joins SET left_at = NOW()
                WHERE id = (
                    SELECT id FROM invite_joins
                    WHERE guild_id = $1 AND member_id = $2 AND left_at IS NULL
                    ORDER BY joined_at DESC LIMIT 1
                )
                """,
                guild_id, member_id,
            )

    async def get_inviter_stats(self, guild_id: int, inviter_id: int) -> Dict[str, int]:
        """{"joined", "left", "net"} for one inviter (net = joined − left)."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COUNT(*) AS joined,
                       COUNT(*) FILTER (WHERE left_at IS NOT NULL) AS parted
                FROM invite_joins
                WHERE guild_id = $1 AND inviter_id = $2
                """,
                guild_id, inviter_id,
            )
        joined = int(row["joined"]) if row else 0
        parted = int(row["parted"]) if row else 0
        return {"joined": joined, "left": parted, "net": joined - parted}

    async def get_invite_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Top inviters by net invites, then by joins, descending."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT inviter_id,
                       COUNT(*) AS joined,
                       COUNT(*) FILTER (WHERE left_at IS NOT NULL) AS parted
                FROM invite_joins
                WHERE guild_id = $1 AND inviter_id IS NOT NULL
                GROUP BY inviter_id
                ORDER BY (COUNT(*) - COUNT(*) FILTER (WHERE left_at IS NOT NULL)) DESC,
                         COUNT(*) DESC
                LIMIT $2
                """,
                guild_id, limit,
            )
        return [
            {
                "inviter_id": r["inviter_id"],
                "joined": int(r["joined"]),
                "left": int(r["parted"]),
                "net": int(r["joined"]) - int(r["parted"]),
            }
            for r in rows
        ]
