# core/db/analytics.py
"""Activity buckets and analytics aggregation (mixin for DatabaseManager)."""
from typing import List, Dict, Any


class _AnalyticsMixin:

    # --- Analytics ---------------------------------------------------------

    async def bulk_add_activity(self, records: List[Dict[str, Any]]) -> None:
        """Adds message counts to the per-guild weekday×hour activity buckets.
        `records` is a list of {guild_id, weekday, hour, delta}. Purely additive
        and idempotent per flush; stores no content/author/timestamps."""
        if not records:
            return
        async with self.pool.acquire() as conn:
            await conn.executemany(
                "INSERT INTO activity_buckets (guild_id, weekday, hour, count) "
                "VALUES ($1, $2, $3, $4) "
                "ON CONFLICT (guild_id, weekday, hour) DO UPDATE "
                "SET count = activity_buckets.count + EXCLUDED.count",
                [
                    (int(r["guild_id"]), int(r["weekday"]), int(r["hour"]), int(r["delta"]))
                    for r in records
                ],
            )

    async def get_analytics(self, guild_id: int, days: int = 30) -> Dict[str, Any]:
        """Aggregates dashboard analytics for a guild: the activity heatmap (from
        activity_buckets) plus moderation/ticket trends computed on the fly from
        existing dated tables (mod_cases, automod_strikes, tickets). No new data
        is collected for the trends — they are pure aggregations."""
        days = max(1, min(int(days), 365))
        window = f"{days} days"
        async with self.pool.acquire() as conn:
            heatmap = await conn.fetch(
                "SELECT weekday, hour, count FROM activity_buckets WHERE guild_id = $1",
                guild_id,
            )
            mod_by_day = await conn.fetch(
                "SELECT (created_at AT TIME ZONE 'UTC')::date AS day, action, COUNT(*) AS count "
                "FROM mod_cases WHERE guild_id = $1 "
                "AND created_at > NOW() - $2::interval "
                "GROUP BY day, action ORDER BY day",
                guild_id, window,
            )
            automod_by_day = await conn.fetch(
                "SELECT (created_at AT TIME ZONE 'UTC')::date AS day, COUNT(*) AS count "
                "FROM automod_strikes WHERE guild_id = $1 "
                "AND created_at > NOW() - $2::interval "
                "GROUP BY day ORDER BY day",
                guild_id, window,
            )
            tickets_opened = await conn.fetch(
                "SELECT (opened_at AT TIME ZONE 'UTC')::date AS day, COUNT(*) AS count "
                "FROM tickets WHERE guild_id = $1 AND opened_at > NOW() - $2::interval "
                "GROUP BY day ORDER BY day",
                guild_id, window,
            )
            tickets_closed = await conn.fetch(
                "SELECT (closed_at AT TIME ZONE 'UTC')::date AS day, COUNT(*) AS count "
                "FROM tickets WHERE guild_id = $1 AND closed_at IS NOT NULL "
                "AND closed_at > NOW() - $2::interval "
                "GROUP BY day ORDER BY day",
                guild_id, window,
            )
            avg_resolution = await conn.fetchval(
                "SELECT AVG(EXTRACT(EPOCH FROM (closed_at - opened_at)) / 3600.0) "
                "FROM tickets WHERE guild_id = $1 AND closed_at IS NOT NULL "
                "AND closed_at > NOW() - $2::interval",
                guild_id, window,
            )
            top_mods = await conn.fetch(
                "SELECT moderator_name AS name, COUNT(*) AS count FROM mod_cases "
                "WHERE guild_id = $1 AND created_at > NOW() - $2::interval "
                "AND moderator_name IS NOT NULL "
                "GROUP BY moderator_name ORDER BY count DESC LIMIT 5",
                guild_id, window,
            )
        return {
            "days": days,
            "heatmap": [
                {"weekday": int(r["weekday"]), "hour": int(r["hour"]), "count": int(r["count"])}
                for r in heatmap
            ],
            "modActionsByDay": [
                {"day": r["day"].isoformat(), "action": r["action"], "count": int(r["count"])}
                for r in mod_by_day
            ],
            "automodByDay": [
                {"day": r["day"].isoformat(), "count": int(r["count"])} for r in automod_by_day
            ],
            "ticketsOpenedByDay": [
                {"day": r["day"].isoformat(), "count": int(r["count"])} for r in tickets_opened
            ],
            "ticketsClosedByDay": [
                {"day": r["day"].isoformat(), "count": int(r["count"])} for r in tickets_closed
            ],
            "avgTicketResolutionHours": round(float(avg_resolution), 1) if avg_resolution is not None else None,
            "topModerators": [
                {"name": r["name"], "count": int(r["count"])} for r in top_mods
            ],
        }
