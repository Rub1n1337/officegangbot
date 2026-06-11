# cogs/usage_log_cog.py
import discord
from discord.ext import commands
import datetime
from core.logger import logger

class UsageLogCog(commands.Cog):
    """Handles logging for command usage."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager = bot.settings_manager

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return

        log_channel_id = self.settings_manager.get_setting(ctx.guild.id, 'usage_log_id')
        if not log_channel_id:
            return

        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel:
            logger.warning(f"Usage log channel ID {log_channel_id} not found in guild {ctx.guild.id}.")
            return

        # Truncate fields for Discord embed limits
        command_name = f"`{ctx.command.qualified_name}`"[:256]
        channel_mention = ctx.channel.mention[:256]

        # Build full command string for both prefix and slash commands
        if ctx.interaction:
            # Slash command: reconstruct from interaction data
            args_parts = []
            if ctx.args:
                args_parts.extend([str(a) for a in ctx.args[2:] if a is not None])  # skip self and ctx
            if ctx.kwargs:
                args_parts.extend([f"{k}: {v}" for k, v in ctx.kwargs.items() if v is not None])
            full_command_text = f"/{ctx.command.qualified_name} {' '.join(args_parts)}".strip()
        else:
            # Prefix command: use message content directly
            full_command_text = ctx.message.content or f"!{ctx.command.qualified_name}"

        full_command = f"```\n{full_command_text[:900]}\n```"

        embed = discord.Embed(
            title="Command Used",
            color=discord.Color.light_grey(),
            timestamp=ctx.message.created_at
        )
        embed.set_author(name=f"{ctx.author.name} ({ctx.author.id})", icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Command", value=command_name)
        embed.add_field(name="Channel", value=channel_mention)
        embed.add_field(name="Type", value="Slash `/`" if ctx.interaction else "Prefix `!`", inline=True)
        embed.add_field(name="Full Command", value=full_command, inline=False)

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning(f"Missing permissions to send usage log to channel {log_channel_id} in guild {ctx.guild.id}.")
        except Exception as e:
            logger.error(f"Failed to send usage log embed: {e}", exc_info=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(UsageLogCog(bot))