# cogs/config_cog.py
import discord
from discord.ext import commands
from discord import app_commands
from core.logger import logger
from core.permissions import has_permission
from core.settings_manager import SettingsManager
from typing import Literal
from .utils import reply

VALID_PERMISSIONS = ["config", "kick", "ban", "mute", "warn", "clear"]
VALID_LOG_TYPES = {
    "punishment": "punishment_log_id",
    "usage": "usage_log_id",
    "message": "message_log_id",
    "leave": "leave_log_id"
}

class Configuration(commands.Cog, name="⚙️ Configuration"):
    """Commands to view and manage bot settings after initial setup."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager = bot.settings_manager

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handles errors for commands in this cog."""
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.BotMissingPermissions):
            perms = ', '.join(error.missing_permissions)
            await reply(ctx, f"❌ I need the following permissions to do that: `{perms}`.", ephemeral=True)
        elif isinstance(error, (commands.MissingPermissions, commands.CheckFailure)):
            await reply(ctx, "❌ You don't have the required permissions for this command.", ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await reply(ctx, "❌ Invalid input provided. Please check the command's help for usage.", ephemeral=True)
        else:
            logger.error(f"An unhandled error occurred in Configuration cog: {error}", exc_info=True)
            await reply(ctx, "🐞 An unexpected error occurred. The developers have been notified.", ephemeral=True)

    @commands.hybrid_command(name="settings", description="Displays a summary of all current bot settings for this server.")
    @has_permission("config")
    async def view_settings(self, ctx: commands.Context):
        settings = self.settings_manager.get_guild_settings(ctx.guild.id)
        embed = discord.Embed(title=f"⚙️ Settings for {ctx.guild.name}", color=discord.Color.blurple())
        embed.set_footer(text="Use /config to manage these settings.")

        # Permissions
        perm_text = "\n".join([
            f"`{perm_name.title()}`: {ctx.guild.get_role(self.settings_manager.get_setting(ctx.guild.id, f'{perm_name}_role_id')).mention if self.settings_manager.get_setting(ctx.guild.id, f'{perm_name}_role_id') and ctx.guild.get_role(self.settings_manager.get_setting(ctx.guild.id, f'{perm_name}_role_id')) else '❌ Not Set'}"
            for perm_name in VALID_PERMISSIONS
        ])
        embed.add_field(name="🛡️ Permission Roles", value=perm_text or 'No permissions configured.', inline=False)

        # Logging
        log_channels = {name: self.bot.get_channel(settings.get(key, 0)) for name, key in VALID_LOG_TYPES.items()}
        all_channels = list(log_channels.values())
        set_channels = [ch for ch in all_channels if ch]
        unique_channels = set(set_channels)
        log_text = ""
        if len(unique_channels) == 1 and set_channels:
            only_channel = next(iter(unique_channels))
            log_text = f"All logs will be sent to {only_channel.mention}"
        else:
            for name, channel in log_channels.items():
                log_text += f"`{name.title()}`: {channel.mention if channel else '❌ Not Set'}\n"
        embed.add_field(name="📝 Logging Channels", value=log_text or 'No log channels configured.', inline=False)

        # Section divider
        embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━", inline=False)
        embed.description = (
            "**Legend:**\n"
            "❌ Not Set — No role or channel configured.\n"
            "Use `/config` or `!config` to change permissions and log channels."
        )
        await reply(ctx, embed=embed, ephemeral=True)


    @commands.hybrid_group(name="config", description="Parent command for all configuration management.")
    @has_permission("config")
    async def config(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            help_cog = self.bot.get_cog("❓ Help")
            if help_cog:
                await help_cog.send_command_help(ctx, ctx.command)
            else:
                await reply(ctx, "The help command is currently unavailable.", ephemeral=True)

    @config.command(name="prefix", description="Changes the bot's command prefix.")
    @has_permission("config")
    async def config_prefix(self, ctx: commands.Context, new_prefix: str):
        if len(new_prefix) > 5:
            return await reply(ctx, "❌ Prefix cannot be longer than 5 characters.", ephemeral=True)
        await self.settings_manager.update_setting(ctx.guild.id, 'prefix', new_prefix)
        await reply(ctx, f"✅ Command prefix has been updated to `{new_prefix}`.", ephemeral=True)

    @config.command(name="logs", description="Sets or disables a channel for a specific log type.")
    @app_commands.describe(log_type="The type of log to configure.", channel="The channel to send logs to. Leave empty to disable.")
    @has_permission("config")
    async def config_logs(self, ctx: commands.Context, log_type: Literal["punishment", "usage", "message", "leave"], channel: discord.TextChannel = None):
        key = VALID_LOG_TYPES[log_type]
        if channel:
            await self.settings_manager.update_setting(ctx.guild.id, key, channel.id)
            await reply(ctx, f"✅ Logs for `{log_type}` will now be sent to {channel.mention}.", ephemeral=True)
        else:
            await self.settings_manager.update_setting(ctx.guild.id, key, None)
            await reply(ctx, f"✅ Logging for `{log_type}` has been disabled.", ephemeral=True)

    @config.command(name="role", description="Assigns a permission level to a role.")
    @app_commands.describe(permission="The permission level to assign.", role="The role to grant this permission to. Leave empty to remove.")
    @has_permission("config")
    async def config_role(self, ctx: commands.Context, permission: Literal["config", "kick", "ban", "mute", "warn", "clear"], role: discord.Role = None):
        key = f"{permission}_role_id"
        if role:
            if role.is_default() or role.is_bot_managed() or role.is_premium_subscriber() or role.is_integration():
                return await reply(ctx, f"❌ The role `{role.name}` cannot be used for permissions.", ephemeral=True)
            await self.settings_manager.update_setting(ctx.guild.id, key, role.id)
            await reply(ctx, f"✅ The `{permission}` permission has been assigned to {role.mention}.", ephemeral=True)
        else:
            await self.settings_manager.update_setting(ctx.guild.id, key, None)
            await reply(ctx, f"✅ The `{permission}` permission has been unassigned.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Configuration(bot))
