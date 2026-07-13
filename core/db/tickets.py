# core/db/tickets.py
"""Support tickets (mixin for DatabaseManager)."""
from typing import Optional, List, Dict, Any


class _TicketsMixin:

    # --- Tickets -----------------------------------------------------------

    VALID_TICKET_PRIORITIES = ("low", "medium", "high", "urgent")

    async def create_ticket(self, guild_id: int, channel_id: int, opener_id: int, opener_name: str) -> int:
        """Records a newly opened ticket and returns its id. If an open record for
        the channel somehow already exists, returns that instead of duplicating."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM tickets WHERE channel_id = $1 AND status = 'open'",
                int(channel_id),
            )
            if existing:
                return existing["id"]
            row = await conn.fetchrow(
                "INSERT INTO tickets (guild_id, channel_id, opener_id, opener_name) "
                "VALUES ($1, $2, $3, $4) RETURNING id",
                guild_id, int(channel_id), int(opener_id), str(opener_name)[:100],
            )
        return row["id"]

    async def get_open_ticket_by_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Returns the open ticket record for a channel, or None."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tickets WHERE channel_id = $1 AND status = 'open'",
                int(channel_id),
            )
        return dict(row) if row else None

    async def get_autoclose_candidates(self) -> List[Dict[str, Any]]:
        """Returns open tickets in guilds that have auto-close enabled, with the
        guild's threshold, so the ticket cog can close the idle ones."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT t.guild_id, t.channel_id, t.opened_at, "
                "g.ticket_auto_close_hours AS hours "
                "FROM tickets t JOIN guilds g ON g.guild_id = t.guild_id "
                "WHERE t.status = 'open' AND COALESCE(g.ticket_auto_close_hours, 0) > 0"
            )
        return [dict(r) for r in rows]

    async def set_ticket_priority(self, channel_id: int, priority: str) -> bool:
        """Sets the priority on the open ticket for a channel. Returns True if a
        row was updated. Invalid priorities are ignored (returns False)."""
        if priority not in self.VALID_TICKET_PRIORITIES:
            return False
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE tickets SET priority = $1 WHERE channel_id = $2 AND status = 'open'",
                priority, int(channel_id),
            )
        return result.endswith("1")

    async def close_ticket(
        self,
        channel_id: int,
        closed_by_id: int,
        closed_by_name: str,
        close_comment: Optional[str],
        transcript: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Finalizes the open ticket for a channel: marks it closed and stores the
        closer, comment and transcript. Returns the updated row (incl. opener_id
        so the caller can DM them), or None if there was no open ticket."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE tickets SET status = 'closed', closed_at = NOW(), "
                "closed_by_id = $1, closed_by_name = $2, close_comment = $3, transcript = $4 "
                "WHERE channel_id = $5 AND status = 'open' RETURNING *",
                int(closed_by_id), str(closed_by_name)[:100],
                (str(close_comment)[:2000] if close_comment else None),
                transcript, int(channel_id),
            )
        return dict(row) if row else None

    async def set_ticket_subject(self, channel_id: int, subject: str) -> bool:
        """Sets the subject from the opener's first message; only once."""
        async with self.pool.acquire() as conn:
            res = await conn.execute(
                "UPDATE tickets SET subject = $1 "
                "WHERE channel_id = $2 AND status = 'open' AND subject IS NULL",
                subject[:200], channel_id,
            )
        return res.endswith("1")

    async def count_open_tickets(self, guild_id: int) -> int:
        """Number of currently open tickets — cheap enough for the stats poll."""
        async with self.pool.acquire() as conn:
            n = await conn.fetchval(
                "SELECT COUNT(*) FROM tickets WHERE guild_id = $1 AND status = 'open'",
                guild_id,
            )
        return int(n or 0)

    async def get_tickets(self, guild_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns recent tickets for a guild (open first, then most recent),
        without the (potentially large) transcript body."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, channel_id, opener_id, opener_name, priority, status, subject, "
                "opened_at, closed_at, closed_by_id, closed_by_name, close_comment, "
                "(transcript IS NOT NULL) AS has_transcript "
                "FROM tickets WHERE guild_id = $1 "
                "ORDER BY (status = 'open') DESC, COALESCE(closed_at, opened_at) DESC "
                "LIMIT $2",
                guild_id, max(1, min(int(limit), 500)),
            )
        return [dict(r) for r in rows]

    async def search_ticket_transcripts(
        self, guild_id: int, query: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Full-text-ish search across closed ticket transcripts (and closing
        comments). Returns matching tickets in the same shape as get_tickets,
        plus a short `snippet` of transcript text around the first match."""
        # Escape LIKE wildcards so the user's text is matched literally; the raw
        # query is used for position()/substring() to build the snippet window.
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, channel_id, opener_id, opener_name, priority, status, subject, "
                "opened_at, closed_at, closed_by_id, closed_by_name, close_comment, "
                "(transcript IS NOT NULL) AS has_transcript, "
                "CASE WHEN position(lower($2) in lower(transcript)) > 0 THEN "
                "  substring(transcript from greatest(1, position(lower($2) in lower(transcript)) - 40) "
                "            for char_length($2) + 80) "
                "  ELSE NULL END AS snippet "
                "FROM tickets "
                "WHERE guild_id = $1 AND transcript IS NOT NULL "
                "AND (transcript ILIKE '%' || $3 || '%' ESCAPE '\\' "
                "     OR close_comment ILIKE '%' || $3 || '%' ESCAPE '\\') "
                "ORDER BY (status = 'open') DESC, COALESCE(closed_at, opened_at) DESC "
                "LIMIT $4",
                guild_id, query, escaped, max(1, min(int(limit), 100)),
            )
        return [dict(r) for r in rows]

    async def get_ticket_transcript(self, guild_id: int, ticket_id: int) -> Optional[Dict[str, Any]]:
        """Returns a single ticket's metadata + full transcript, scoped to guild."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, opener_name, priority, status, subject, opened_at, closed_at, "
                "closed_by_name, close_comment, transcript "
                "FROM tickets WHERE guild_id = $1 AND id = $2",
                guild_id, int(ticket_id),
            )
        return dict(row) if row else None
