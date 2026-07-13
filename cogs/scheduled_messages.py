# cogs/scheduled_messages.py
import datetime

import discord
from discord.ext import commands, tasks

from core.logger import logger
from core.schedule import compute_next_run


class ScheduledMessagesCog(commands.Cog, name="📅 Scheduled Messages"):
    """Posts dashboard-configured scheduled / recurring announcements.

    A 60s loop polls the scheduled_messages table for due rows, posts them, then
    reschedules recurring ones (compute_next_run) or retires one-offs.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_scheduled.start()

    def cog_unload(self):
        self.check_scheduled.cancel()

    @tasks.loop(seconds=60)
    async def check_scheduled(self):
        if not getattr(self.bot, "db", None):
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            due = await self.bot.db.get_due_scheduled_messages(now)
        except Exception as e:
            logger.error(f"Scheduled messages: failed to fetch due rows: {e}", exc_info=True)
            return
        for m in due:
            try:
                await self._dispatch_one(m, now)
            except Exception as e:
                logger.error(f"Scheduled message {m.get('id')} failed: {e}", exc_info=True)

    async def _dispatch_one(self, m, now):
        # Respect the feature toggle: while disabled, leave the row due so it fires
        # when re-enabled rather than being silently skipped forever.
        enabled = await self.bot.db.get_enabled_features(m["guild_id"])
        if "scheduled-messages" not in enabled:
            return

        guild = self.bot.get_guild(m["guild_id"])
        channel = guild.get_channel(int(m["channel_id"])) if guild else None
        if guild is not None and channel is None:
            # Cold cache after a restart — fall back to an API fetch so the
            # scheduled post isn't silently skipped.
            try:
                channel = await guild.fetch_channel(int(m["channel_id"]))
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                channel = None
        if channel is not None:
            try:
                await channel.send(str(m["content"])[:2000])
            except (discord.Forbidden, discord.HTTPException) as e:
                logger.warning(
                    f"Scheduled message {m['id']}: could not post to channel {m['channel_id']}: {e}"
                )
        else:
            logger.warning(f"Scheduled message {m['id']}: channel {m['channel_id']} not found")

        # Reschedule / retire regardless of post success, so a missing channel
        # doesn't make the row fire every minute forever.
        nxt = compute_next_run(m["scheduled_at"], m["repeat"], now)
        if nxt is not None:
            await self.bot.db.advance_scheduled_message(m["id"], nxt)
        else:
            await self.bot.db.disable_scheduled_message(m["id"])

    @check_scheduled.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduledMessagesCog(bot))
