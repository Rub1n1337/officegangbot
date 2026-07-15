# cogs/config_cog.py
import discord
from discord.ext import commands
from discord import app_commands
from core.logger import logger
from core.permissions import has_permission
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
        
        # One consistent shape for every feature: name · on/off · the settings
        # that matter. The old version checked two features that no longer
        # exist ("reaction-role", "filter" — merged into reaction-menus and
        # automod), so they always rendered "Disabled", and it silently omitted
        # anti-raid, verification, scheduled messages and role menus entirely.
        embed = discord.Embed(
            title=f"⚙️ Settings — {ctx.guild.name}",
            description="`/config` manages permissions and log channels · the dashboard covers the rest.",
            color=discord.Color.blurple(),
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        def _mark(feature: str) -> str:
            return "✅" if feature in enabled_features else "⬜"

        def _channel(key: str) -> str:
            cid = settings.get(key)
            channel = ctx.guild.get_channel(int(cid)) if cid else None
            return channel.mention if channel else "—"

        def _role(key: str) -> str:
            rid = settings.get(key)
            role = ctx.guild.get_role(int(rid)) if rid else None
            return role.mention if role else "—"

        def _preview(key: str, limit: int = 60) -> str:
            text = (settings.get(key) or "").strip().replace("\n", " ")
            if not text:
                return "—"
            return f"`{text[:limit]}…`" if len(text) > limit else f"`{text}`"

        # --- Moderation permissions ------------------------------------------
        perm_lines = []
        for perm_name in VALID_PERMISSIONS:
            role_ids = mod_roles.get(perm_name, [])
            roles = [ctx.guild.get_role(rid) for rid in role_ids] if role_ids else []
            mentions = ", ".join(r.mention for r in roles if r) or "—"
            perm_lines.append(f"`{perm_name:<6}` {mentions}")
        embed.add_field(
            name="🛡️ Moderation permissions",
            value="\n".join(perm_lines) + "\n-# Administrators always have full access.",
            inline=False,
        )

        # --- Logging ----------------------------------------------------------
        log_lines = [
            f"`{name:<10}` {_channel(key)}"
            for name, key in VALID_LOG_TYPES.items()
        ]
        embed.add_field(
            name=f"{_mark('logging')} Logging",
            value="\n".join(log_lines),
            inline=False,
        )

        # --- Content features -------------------------------------------------
        embed.add_field(
            name=f"{_mark('rules')} Rules",
            value=f"Channel: {_channel('rules_channel_id')}\nText: {_preview('rules_message')}",
            inline=False,
        )
        embed.add_field(
            name=f"{_mark('welcome-message')} Welcome message",
            value=f"Channel: {_channel('welcome_channel_id')}\nText: {_preview('welcome_message')}",
            inline=False,
        )
        embed.add_field(
            name=f"{_mark('verification')} Verification",
            value=f"Verified role: {_role('verification_role_id')}",
            inline=False,
        )

        # --- Safety -----------------------------------------------------------
        automod_bits = []
        if settings.get("automod_block_invites"):
            automod_bits.append("invites")
        if settings.get("automod_block_links"):
            automod_bits.append("links")
        if settings.get("automod_block_mass_mentions"):
            automod_bits.append("@everyone")
        words = settings.get("filter_words") or []
        if words:
            automod_bits.append(f"{len(words)} banned words")
        if settings.get("automod_dry_run"):
            automod_bits.append("**dry-run**")
        embed.add_field(
            name=f"{_mark('automod')} AutoMod",
            value=("Blocks: " + ", ".join(automod_bits)) if automod_bits else "Anti-spam only",
            inline=False,
        )

        raid_action = settings.get("antiraid_action") or "timeout"
        embed.add_field(
            name=f"{_mark('anti-raid')} Anti-raid",
            value=(
                f"{settings.get('antiraid_join_count') or 8} joins / "
                f"{settings.get('antiraid_join_window') or 10}s → **{raid_action}**"
            ),
            inline=False,
        )

        # --- Engagement / support ---------------------------------------------
        auto_close = int(settings.get("ticket_auto_close_hours") or 0)
        embed.add_field(
            name=f"{_mark('tickets')} Tickets",
            value=(
                f"Support role: {_role('ticket_support_role_id')} · "
                + (f"auto-close after {auto_close}h" if auto_close else "no auto-close")
            ),
            inline=False,
        )
        embed.add_field(
            name=f"{_mark('levels')} Levels",
            value=f"Level-up channel: {_channel('level_up_channel_id')}",
            inline=False,
        )
        embed.add_field(
            name=f"{_mark('reaction-menus')} Role menus",
            value="Configured on the dashboard.",
            inline=False,
        )
        embed.add_field(
            name=f"{_mark('scheduled-messages')} Scheduled messages",
            value="Configured on the dashboard.",
            inline=False,
        )

        embed.set_footer(text="✅ enabled · ⬜ off · — not set")
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
            
            # One role per permission level: clear any existing role(s) for this
            # level first, then assign the new one (matches the dashboard form).
            if self.bot.db:
                await self.bot.db.remove_mod_role(ctx.guild.id, permission)
                await self.bot.db.set_mod_role(ctx.guild.id, role.id, permission)

            await reply(ctx, f"✅ The `{permission}` permission has been assigned to {role.mention}.", ephemeral=True)
        else:
            # Remove from Postgres
            if self.bot.db:
                await self.bot.db.remove_mod_role(ctx.guild.id, permission)
            
            await reply(ctx, f"✅ All roles for `{permission}` permission have been unassigned.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Configuration(bot))
