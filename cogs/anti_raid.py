# cogs/anti_raid.py
import time
import datetime
from collections import deque

import discord
from discord.ext import commands

from core.logger import logger
from core.permissions import bot_can_act_on

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
        min_age_days = cfg.get("min_account_age_days", 0)
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
                if m and not m.bot and not self._old_enough(m, min_age_days):
                    await self._act(m, action, duration)
        elif raid_active:
            # Still in raid mode — treat each new join as part of the wave.
            if not self._old_enough(member, min_age_days):
                await self._act(member, action, duration)

    @staticmethod
    def _old_enough(member: discord.Member, min_age_days: int) -> bool:
        """False-positive guard: with a configured minimum account age, mature
        accounts caught in a join wave (e.g. after a YouTube shout-out) are
        spared — raid bots are overwhelmingly fresh accounts."""
        if min_age_days <= 0:
            return False
        age = datetime.datetime.now(datetime.timezone.utc) - member.created_at
        return age.days >= min_age_days

    async def _act(self, member: discord.Member, action: str, duration: int):
        reason = "Anti-raid: join spike detected"
        guild = member.guild
        # Hierarchy guard (matches the manual moderation commands).
        if action in ("ban", "kick", "timeout") and not bot_can_act_on(
            target_id=member.id,
            target_top_role_pos=member.top_role.position,
            bot_id=self.bot.user.id,
            bot_top_role_pos=guild.me.top_role.position,
            owner_id=guild.owner_id,
        ):
            logger.info(f"Anti-raid: {action} skipped for {member} — protected by hierarchy")
            return
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
        """Posts a raid alert to the punishment log channel — honouring the
        Logging feature flag and falling back to fetch_channel on a cold cache,
        consistent with the other log paths (_log_automod etc.)."""
        try:
            enabled = await self.bot.db.get_enabled_features(guild.id)
            if "logging" not in enabled:
                return
            log_id = await self.bot.db.get_guild_setting(guild.id, "punishment_log_id")
            if not log_id:
                return
            channel = guild.get_channel(int(log_id))
            if channel is None:
                try:
                    channel = await guild.fetch_channel(int(log_id))
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    return
            embed = discord.Embed(
                title="🚨 Raid detected",
                description=f"**{joins}** members joined within **{window}s**.\nAction applied: **{action}**.",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            ping_role_id = (await self.bot.db.get_antiraid_config(guild.id)).get("ping_role_id")
            content = f"<@&{ping_role_id}>" if ping_role_id else None
            await channel.send(content=content, embed=embed)
        except discord.HTTPException as e:
            # A raid alert the admins never see is exactly when they need it —
            # at least leave a trace in the logs.
            logger.warning(f"Anti-raid: raid alert could not be posted in guild {guild.id}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiRaidCog(bot))
