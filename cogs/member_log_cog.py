# cogs/member_log_cog.py
import discord
from discord.ext import commands
import datetime
from core.logger import logger
from core.i18n import t

class MemberLogCog(commands.Cog):
    """Handles logging for members leaving the server."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not member.guild or not self.bot.db:
            return

        # Check if logging feature is enabled
        enabled_features = await self.bot.db.get_enabled_features(member.guild.id)
        if "logging" not in enabled_features:
            return

        log_channel_id = await self.bot.db.get_guild_setting(member.guild.id, 'leave_log_id')
        if not log_channel_id:
            return

        log_channel = self.bot.get_channel(int(log_channel_id))
        if log_channel is None:
            try:
                log_channel = await self.bot.fetch_channel(int(log_channel_id))
            except (discord.NotFound, discord.Forbidden):
                logger.warning(f"Leave log channel {log_channel_id} not found or inaccessible.")
                return

        loc = await self.bot.db.get_locale(member.guild.id)
        embed = discord.Embed(
            description=t(loc, "memberlog.left_desc", member=member.mention),
            color=discord.Color.dark_grey(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
        embed.set_footer(text=t(loc, "memberlog.footer"))

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.exception(f"Error sending leave log: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(MemberLogCog(bot))
