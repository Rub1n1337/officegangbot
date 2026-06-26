# cogs/audit_log_cog.py
import discord
from discord.ext import commands
import datetime
from core.logger import logger

class AuditLogCog(commands.Cog):
    """Handles logging for message edits and deletions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get_log_channel(self, guild_id: int):
        if not self.bot.db:
            return None
            
        # Check if logging feature is enabled
        enabled_features = await self.bot.db.get_enabled_features(guild_id)
        if "logging" not in enabled_features:
            return None
            
        # Use audit_log_id for message logs
        log_channel_id = await self.bot.db.get_guild_setting(guild_id, 'audit_log_id')
        if not log_channel_id:
            return None
            
        channel = self.bot.get_channel(int(log_channel_id))
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(int(log_channel_id))
            except (discord.NotFound, discord.Forbidden):
                logger.warning(f"Audit log channel {log_channel_id} not found or inaccessible.")
                return None
        return channel

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        log_channel = await self._get_log_channel(message.guild.id)
        if not log_channel:
            return

        embed = discord.Embed(
            description=f"**Message sent by {message.author.mention} deleted in {message.channel.mention}**",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Content", value=f"```{message.content[:1020]}```" if message.content else "No message content (e.g., an embed).", inline=False)
        embed.set_author(name=f"{message.author.name} ({message.author.id})", icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"Message ID: {message.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.error(f"Error sending delete log: {e}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not after.guild or after.author.bot or before.content == after.content:
            return

        log_channel = await self._get_log_channel(after.guild.id)
        if not log_channel:
            return

        embed = discord.Embed(
            description=f"**Message edited in {after.channel.mention}** [Jump to Message]({after.jump_url})",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=f"{after.author.name} ({after.author.id})", icon_url=after.author.display_avatar.url)
        embed.add_field(name="Before", value=f"```{before.content[:1020]}```", inline=False)
        embed.add_field(name="After", value=f"```{after.content[:1020]}```", inline=False)
        embed.set_footer(text=f"Message ID: {after.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.error(f"Error sending edit log: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AuditLogCog(bot))
