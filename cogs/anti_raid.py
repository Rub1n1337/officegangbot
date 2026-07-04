# cogs/anti_raid.py
import time
import datetime
from collections import deque

import discord
from discord.ext import commands

from core.logger import logger

MAX_TIMEOUT_SECONDS = 28 * 24 * 3600 - 60  # Discord timeout ceiling (~28 days).


class AntiRaidCog(commands.Cog, name="🚨 Anti-Raid"):
    """Detects a spike of member joins and reacts (timeout / kick / ban / notify).

    State is in-memory (raid activity is ephemeral); it resets on restart, which
    is fine — a raid is a live event, not something to persist.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._joins: dict[int, deque] = {}       # guild_id -> deque[(ts, member_id)]
        self._raid_until: dict[int, float] = {}   # guild_id -> epoch until raid mode ends

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot or not self.bot.db:
            return
        guild = member.guild

        # Gate on the feature flag (cached) so disabled guilds never hit the DB.
        enabled = await self.bot.db.get_enabled_features(guild.id)
        if "anti-raid" not in enabled:
            return

        cfg = await self.bot.db.get_antiraid_config(guild.id)
        window, count = cfg["join_window"], cfg["join_count"]
        action, duration = cfg["action"], cfg["duration"]
        now = time.time()

        dq = self._joins.setdefault(guild.id, deque())
        dq.append((now, member.id))
        while dq and now - dq[0][0] > window:
            dq.popleft()

        raid_active = self._raid_until.get(guild.id, 0) > now
        if not raid_active and len(dq) >= count:
            # New raid: enter raid mode and act on everyone in the join window.
            self._raid_until[guild.id] = now + duration
            logger.warning(f"Anti-raid: {len(dq)} joins in {window}s in {guild.name} — action={action}")
            await self._notify(guild, len(dq), window, action)
            for _, mid in list(dq):
                m = guild.get_member(mid)
                if m and not m.bot:
                    await self._act(m, action, duration)
        elif raid_active:
            # Still in raid mode — treat each new join as part of the wave.
            await self._act(member, action, duration)

    async def _act(self, member: discord.Member, action: str, duration: int):
        reason = "Anti-raid: join spike detected"
        try:
            if action == "ban":
                await member.ban(reason=reason, delete_message_seconds=0)
            elif action == "kick":
                await member.kick(reason=reason)
            elif action == "timeout":
                secs = max(60, min(int(duration), MAX_TIMEOUT_SECONDS))
                await member.timeout(datetime.timedelta(seconds=secs), reason=reason)
            # "notify" takes no action on members.
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"Anti-raid: couldn't {action} {member} in {member.guild.name}: {e}")

    async def _notify(self, guild: discord.Guild, joins: int, window: int, action: str):
        """Posts a raid alert to the punishment log channel, if one is set."""
        try:
            log_id = await self.bot.db.get_guild_setting(guild.id, "punishment_log_id")
            if not log_id:
                return
            channel = guild.get_channel(int(log_id))
            if channel is None:
                return
            embed = discord.Embed(
                title="🚨 Raid detected",
                description=f"**{joins}** members joined within **{window}s**.\nAction applied: **{action}**.",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiRaidCog(bot))
