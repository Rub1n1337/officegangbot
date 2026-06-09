# cogs/audit_log_cog.py
import discord
from discord.ext import commands
import datetime

class AuditLogCog(commands.Cog):
    """Handles logging for message edits and deletions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager = bot.settings_manager

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        log_channel_id = self.settings_manager.get_setting(message.guild.id, 'message_log_id')
        if not log_channel_id:
            return

        log_channel = self.bot.get_channel(log_channel_id)
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

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not after.guild or after.author.bot or before.content == after.content:
            return

        log_channel_id = self.settings_manager.get_setting(after.guild.id, 'message_log_id')
        if not log_channel_id:
            return

        log_channel = self.bot.get_channel(log_channel_id)
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

async def setup(bot: commands.Bot):
    await bot.add_cog(AuditLogCog(bot))