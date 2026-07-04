# cogs/channel_tools.py
import discord
from discord.ext import commands
from discord import app_commands
from core.logger import logger
from core.i18n import t
from .utils import reply
from typing import Optional

MAX_SLOWMODE = 21600  # Discord's per-channel slowmode ceiling (6 hours), in seconds.


class ChannelToolsCog(commands.Cog, name="🔧 Channel Tools"):
    """Quick channel moderation: slowmode and lock / unlock."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="slowmode",
        description="Set slowmode (seconds between messages per user) on a channel. 0 disables it.",
    )
    @app_commands.describe(
        seconds="Seconds each member must wait between messages (0–21600). 0 turns it off.",
        channel="Channel to apply it to (defaults to the current one).",
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(
        self, ctx: commands.Context, seconds: int, channel: Optional[discord.TextChannel] = None
    ):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        target = channel or ctx.channel
        seconds = max(0, min(int(seconds), MAX_SLOWMODE))
        try:
            await target.edit(slowmode_delay=seconds, reason=f"Slowmode by {ctx.author}")
        except discord.Forbidden:
            return await reply(ctx, t(loc, "channel.no_perm", channel=target.mention), ephemeral=True)
        key = "channel.slowmode_off" if seconds == 0 else "channel.slowmode_set"
        await reply(ctx, t(loc, key, channel=target.mention, seconds=seconds), ephemeral=True)
        logger.info(f"Slowmode {seconds}s on #{target.name} by {ctx.author} in {ctx.guild.name}")

    async def _set_lock(self, ctx: commands.Context, channel: Optional[discord.TextChannel], lock: bool):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        target = channel or ctx.channel
        try:
            # None resets the @everyone override back to neutral (inherit); False
            # explicitly denies sending. Only send_messages is touched, so other
            # overwrites on the channel are preserved.
            await target.set_permissions(
                ctx.guild.default_role,
                send_messages=False if lock else None,
                reason=f"{'Lock' if lock else 'Unlock'} by {ctx.author}",
            )
        except discord.Forbidden:
            return await reply(ctx, t(loc, "channel.no_perm", channel=target.mention), ephemeral=True)
        await reply(ctx, t(loc, "channel.locked" if lock else "channel.unlocked", channel=target.mention))
        logger.info(f"{'Locked' if lock else 'Unlocked'} #{target.name} by {ctx.author} in {ctx.guild.name}")

    @commands.hybrid_command(name="lock", description="Lock a channel so members can't send messages.")
    @app_commands.describe(channel="Channel to lock (defaults to the current one).")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def lock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        await self._set_lock(ctx, channel, lock=True)

    @commands.hybrid_command(name="unlock", description="Unlock a previously locked channel.")
    @app_commands.describe(channel="Channel to unlock (defaults to the current one).")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unlock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        await self._set_lock(ctx, channel, lock=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelToolsCog(bot))
