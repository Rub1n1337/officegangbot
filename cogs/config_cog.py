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
    "message": "audit_log_id",  # Dashboard uses audit_log_id for message logs
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
        if not self.bot.db:
            return await reply(ctx, "❌ Database unavailable.", ephemeral=True)
            
        settings = await self.bot.db.get_all_guild_settings(ctx.guild.id)
        enabled_features = await self.bot.db.get_enabled_features(ctx.guild.id)
        mod_roles = await self.bot.db.get_mod_roles(ctx.guild.id)
        
        embed = discord.Embed(title=f"⚙️ Settings for {ctx.guild.name}", color=discord.Color.blurple())
        embed.set_footer(text="Use /config to manage these settings.")

        # Permissions from Postgres mod_roles
        perm_lines = []
        for perm_name in VALID_PERMISSIONS:
            role_ids = mod_roles.get(perm_name, [])
            if role_ids:
                roles = [ctx.guild.get_role(rid) for rid in role_ids if ctx.guild.get_role(rid)]
                role_mentions = ", ".join([r.mention for r in roles]) if roles else "❌ Not Set"
                perm_lines.append(f"`{perm_name.title()}`: {role_mentions}")
            else:
                # Fallback to legacy JSON for display if nothing in Postgres
                legacy_id = self.settings_manager.get_setting(ctx.guild.id, f'{perm_name}_role_id')
                legacy_role = ctx.guild.get_role(legacy_id) if legacy_id else None
                perm_lines.append(f"`{perm_name.title()}`: {legacy_role.mention if legacy_role else '❌ Not Set'}")

        embed.add_field(name="🛡️ Permission Roles", value="\n".join(perm_lines) or 'No permissions configured.', inline=False)

        # Logging
        is_logging_enabled = "logging" in enabled_features
        log_channels = {name: self.bot.get_channel(int(settings.get(key))) if settings.get(key) else None for name, key in VALID_LOG_TYPES.items()}
        
        log_text = f"Feature Status: {'✅ **Enabled**' if is_logging_enabled else '❌ **Disabled**'}\n\n"
        for name, channel in log_channels.items():
            log_text += f"`{name.title()}`: {channel.mention if channel else '❌ Not Set'}\n"
        
        embed.add_field(name="📝 Logging Channels", value=log_text, inline=False)

        # Rules
        is_rules_enabled = "rules" in enabled_features
        rules_channel = ctx.guild.get_channel(settings.get("rules_channel_id")) if settings.get("rules_channel_id") else None
        rules_text = settings.get("rules_message") or "Not Set"
        if len(rules_text) > 100: rules_text = rules_text[:97] + "..."
        embed.add_field(
            name="📜 Rules System",
            value=f"**Status:** {'✅ Enabled' if is_rules_enabled else '❌ Disabled'}\n"
                  f"**Channel:** {rules_channel.mention if rules_channel else '❌ Not Set'}\n"
                  f"**Message:** `{rules_text}`",
            inline=False
        )

        # Welcome Message
        is_welcome_enabled = "welcome-message" in enabled_features
        welcome_channel = ctx.guild.get_channel(settings.get("welcome_channel_id")) if settings.get("welcome_channel_id") else None
        welcome_text = settings.get("welcome_message") or "Not Set"
        if len(welcome_text) > 100: welcome_text = welcome_text[:97] + "..."
        embed.add_field(
            name="👋 Welcome System",
            value=f"**Status:** {'✅ Enabled' if is_welcome_enabled else '❌ Enabled (via legacy)' if settings.get('welcome_enabled') else '❌ Disabled'}\n"
                  f"**Channel:** {welcome_channel.mention if welcome_channel else '❌ Not Set'}\n"
                  f"**Message:** `{welcome_text}`",
            inline=False
        )

        # Reaction Role
        is_rr_enabled = "reaction-role" in enabled_features
        rr_channel = ctx.guild.get_channel(settings.get("rules_channel_id")) if settings.get("rules_channel_id") else None
        rr_role = ctx.guild.get_role(settings.get("reaction_role_id")) if settings.get("reaction_role_id") else None
        embed.add_field(
            name="🎭 Reaction Role",
            value=f"**Status:** {'✅ Enabled' if is_rr_enabled else '❌ Disabled'}\n"
                  f"**Channel:** {rr_channel.mention if rr_channel else '❌ Not Set'}\n"
                  f"**Role:** {rr_role.mention if rr_role else '❌ Not Set'}\n"
                  f"**Emoji:** {settings.get('reaction_emoji') or '❌ Not Set'}",
            inline=False
        )

        # Section divider
        embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━", inline=False)
        embed.description = (
            "**Legend:**\n"
            "❌ Not Set — No role or channel configured.\n"
            "Use `/config` to change permissions and log channels."
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

    @config.command(name="logs", description="Sets or disables a channel for a specific log type.")
    @app_commands.describe(log_type="The type of log to configure.", channel="The channel to send logs to. Leave empty to disable.")
    @has_permission("config")
    async def config_logs(self, ctx: commands.Context, log_type: Literal["punishment", "usage", "message", "leave"], channel: discord.TextChannel = None):
        key = VALID_LOG_TYPES[log_type]
        value = channel.id if channel else None
        
        if self.bot.db:
            await self.bot.db.set_guild_setting(ctx.guild.id, key, value)
            # Also ensure 'logging' feature is enabled if setting a channel
            if channel:
                await self.bot.db.set_feature_enabled(ctx.guild.id, "logging", True)
        
        # Legacy JSON sync
        # Note: 'message' maps to 'audit_log_id' in DB but 'message_log_id' in JSON
        json_key = "message_log_id" if log_type == "message" else key
        await self.settings_manager.update_setting(ctx.guild.id, json_key, value)
        
        if channel:
            await reply(ctx, f"✅ Logs for `{log_type}` will now be sent to {channel.mention}.", ephemeral=True)
        else:
            await reply(ctx, f"✅ Logging for `{log_type}` has been disabled.", ephemeral=True)

    @config.command(name="role", description="Assigns a permission level to a role.")
    @app_commands.describe(permission="The permission level to assign.", role="The role to grant this permission to. Leave empty to remove ALL roles for this level.")
    @has_permission("config")
    async def config_role(self, ctx: commands.Context, permission: Literal["config", "kick", "ban", "mute", "warn", "clear"], role: discord.Role = None):
        if role:
            if role.is_default() or role.is_bot_managed() or role.is_premium_subscriber() or role.is_integration():
                return await reply(ctx, f"❌ The role `{role.name}` cannot be used for permissions.", ephemeral=True)
            
            # Save to Postgres
            if self.bot.db:
                await self.bot.db.set_mod_role(ctx.guild.id, role.id, permission)
            
            # Legacy JSON sync (only supports one role, so we overwrite)
            await self.settings_manager.update_setting(ctx.guild.id, f"{permission}_role_id", role.id)
            
            await reply(ctx, f"✅ The `{permission}` permission has been assigned to {role.mention}.", ephemeral=True)
        else:
            # Remove from Postgres
            if self.bot.db:
                await self.bot.db.remove_mod_role(ctx.guild.id, permission)
            
            # Legacy JSON sync
            await self.settings_manager.update_setting(ctx.guild.id, f"{permission}_role_id", None)
            
            await reply(ctx, f"✅ All roles for `{permission}` permission have been unassigned.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Configuration(bot))
