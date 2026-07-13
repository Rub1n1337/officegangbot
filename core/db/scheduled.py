# core/db/scheduled.py
"""Scheduled / recurring messages (mixin for DatabaseManager)."""
from typing import List, Dict, Any


class _ScheduledMixin:

    # --- Scheduled messages -------------------------------------------------

    async def get_scheduled_messages(self, guild_id: int) -> List[Dict[str, Any]]:
        """Returns a guild's scheduled messages, newest schedule first."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, channel_id, content, scheduled_at, repeat, enabled, last_sent_at "
                "FROM scheduled_messages WHERE guild_id = $1 ORDER BY scheduled_at",
                guild_id,
            )
            return [dict(r) for r in rows]

    async def replace_scheduled_messages(self, guild_id: int, rows: List[Dict[str, Any]]) -> None:
        """Replaces all of a guild's scheduled messages with `rows`. Each row needs
        channel_id, content, scheduled_at (datetime), repeat, enabled."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM scheduled_messages WHERE guild_id = $1", guild_id
                )
                for r in rows:
                    await conn.execute(
                        """
                        INSERT INTO scheduled_messages
                            (guild_id, channel_id, content, scheduled_at, repeat, enabled)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        guild_id, int(r["channel_id"]), str(r["content"]),
                        r["scheduled_at"], str(r["repeat"]), bool(r["enabled"]),
                    )

    async def get_due_scheduled_messages(self, now) -> List[Dict[str, Any]]:
        """Returns enabled scheduled messages (across all guilds) due at or before
        `now`, for the Scheduled Messages cog to post."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                # Filter by the feature toggle here: without it, a due message
                # in a guild with the feature off was re-fetched (and its
                # feature flag re-checked) every minute, forever.
                "SELECT sm.id, sm.guild_id, sm.channel_id, sm.content, sm.scheduled_at, sm.repeat "
                "FROM scheduled_messages sm "
                "JOIN guilds g ON g.guild_id = sm.guild_id "
                "WHERE sm.enabled AND sm.scheduled_at <= $1 "
                "AND 'scheduled-messages' = ANY(g.enabled_features)",
                now,
            )
            return [dict(r) for r in rows]

    async def advance_scheduled_message(self, message_id: int, next_at) -> None:
        """Reschedules a recurring message to its next run and records the send."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE scheduled_messages SET scheduled_at = $1, last_sent_at = NOW() WHERE id = $2",
                next_at, message_id,
            )

    async def disable_scheduled_message(self, message_id: int) -> None:
        """Marks a one-off message as sent (disabled) after it fires."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE scheduled_messages SET enabled = FALSE, last_sent_at = NOW() WHERE id = $1",
                message_id,
            )
