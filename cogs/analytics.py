# cogs/analytics.py
import asyncio

import discord
from discord.ext import commands, tasks

from core.logger import logger


class AnalyticsCog(commands.Cog):
    """Collects an *aggregate* activity signal for the dashboard heatmap: a count
    of human messages per guild, bucketed by weekday (0=Mon..6=Sun) and hour
    (0-23, UTC). It deliberately stores no message content, author or per-message
    timestamp — only running per-bucket counts — so there is no PII to retain.

    Counts are buffered in memory and flushed to PostgreSQL every 30 seconds
    (mirroring the XP flush) so a busy server isn't one write per message.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # {(guild_id, weekday, hour): count}
        self._buffer: dict[tuple[int, int, int], int] = {}
        # {(guild_id, date): count} — daily volume for the KPI sparklines.
        self._daily: dict[tuple[int, object], int] = {}
        self._lock = asyncio.Lock()
        self.flush_activity.start()
        self.snapshot_members.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        # message.created_at is timezone-aware UTC; bucket by weekday/hour.
        ts = message.created_at
        key = (message.guild.id, ts.weekday(), ts.hour)
        day_key = (message.guild.id, ts.date())
        async with self._lock:
            self._buffer[key] = self._buffer.get(key, 0) + 1
            self._daily[day_key] = self._daily.get(day_key, 0) + 1

    @tasks.loop(seconds=30)
    async def flush_activity(self):
        """Flushes buffered per-bucket counts to PostgreSQL every 30 seconds."""
        try:
            if not self._buffer or not self.bot.db:
                return
            async with self._lock:
                snapshot = self._buffer
                self._buffer = {}
                daily_snapshot = self._daily
                self._daily = {}

            if daily_snapshot:
                try:
                    await self.bot.db.bulk_add_daily_messages([
                        {"guild_id": g, "day": d, "delta": delta}
                        for (g, d), delta in daily_snapshot.items()
                    ])
                except Exception:
                    async with self._lock:
                        for (g, d), delta in daily_snapshot.items():
                            self._daily[(g, d)] = self._daily.get((g, d), 0) + delta
                    raise

            records = [
                {"guild_id": g, "weekday": wd, "hour": hr, "delta": delta}
                for (g, wd, hr), delta in snapshot.items()
            ]
            try:
                await self.bot.db.bulk_add_activity(records)
                logger.info(f"Activity flush: {len(records)} buckets to PostgreSQL")
            except Exception:
                # Put the counts back so a transient DB error doesn't lose them.
                async with self._lock:
                    for (g, wd, hr), delta in snapshot.items():
                        key = (g, wd, hr)
                        self._buffer[key] = self._buffer.get(key, 0) + delta
                raise
        except Exception as e:
            logger.error(f"flush_activity crashed: {e}", exc_info=True)

    @tasks.loop(hours=1)
    async def snapshot_members(self):
        """Upserts today's member count per guild (for the members sparkline).
        Hourly upsert of the same (guild, day) row — the last write of the day
        wins, which is exactly the snapshot we want."""
        try:
            if not self.bot.db:
                return
            rows = [(g.id, g.member_count) for g in self.bot.guilds if g.member_count]
            await self.bot.db.snapshot_member_counts(rows)
        except Exception as e:
            logger.error(f"snapshot_members crashed: {e}", exc_info=True)

    @snapshot_members.before_loop
    async def before_snapshot_members(self):
        await self.bot.wait_until_ready()

    @flush_activity.before_loop
    async def before_flush_activity(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.flush_activity.cancel()
        self.snapshot_members.cancel()
        # Best-effort final flush on a graceful unload so buffered counts survive
        # a normal restart. Skipped if the pool is already closing/closed.
        pool = getattr(self.bot.db, "_pool", None) if self.bot.db else None
        if pool and not getattr(pool, "_closing", False) and not getattr(pool, "_closed", False):
            asyncio.create_task(self._emergency_flush())

    async def _emergency_flush(self):
        """Best-effort flush of buffered activity on unload."""
        try:
            await self.flush_activity()
        except Exception:
            logger.warning("Emergency activity flush on unload failed.", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AnalyticsCog(bot))
