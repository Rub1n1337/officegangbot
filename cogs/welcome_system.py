# cogs/welcome_system.py

"""
This Cog manages the welcome message system for new members.
-------------------------------------------------------------
What it does:
- It listens for the `on_member_join` event.
- If the welcome system is enabled for that server, it sends a customizable
  welcome message to a designated channel.
- It provides commands for administrators to:
  - Enable or disable the welcome system (`/welcome toggle`).
  - Set the welcome channel (`/welcome channel #channel-name`).
  - Customize the welcome message (`/welcome message ...`).
- It uses placeholders like `{user.mention}` and `{server.name}` to create
  dynamic and personal welcome messages.
"""

import discord
from discord.ext import commands
from core.logger import logger
from core.permissions import has_permission
from core.i18n import t
from core.safe_format import render_template, welcome_values, is_template_valid
from typing import Optional
from .utils import reply

DEFAULT_WELCOME_MESSAGE = "Welcome {user.mention} to {server.name}! We're glad to have you."

class WelcomeSystem(commands.Cog, name="👋 Welcome System"):
    """Manages welcome messages and auto-roles for new members."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._send_welcome_message(member)
        await self._assign_auto_role(member)

    async def _send_welcome_message(self, member: discord.Member):
        guild = member.guild
        if not self.bot.db:
            return

        # Check if welcome-message feature is enabled via enabled_features
        enabled_features = await self.bot.db.get_enabled_features(guild.id)
        if "welcome-message" not in enabled_features:
            return

        channel_id = await self.bot.db.get_guild_setting(guild.id, "welcome_channel_id")
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            logger.warning(f"Welcome channel ID {channel_id} not found in {guild.name}. Disabling system.")
            await self.bot.db.set_feature_enabled(guild.id, "welcome-message", False)
            return

        message_format = await self.bot.db.get_guild_setting(guild.id, "welcome_message", DEFAULT_WELCOME_MESSAGE)
        # Safe substitution: only whitelisted {placeholders} are replaced, so an
        # admin-authored template can't traverse object attributes (e.g. leak the
        # bot token via {user._state.http.token}). Never use str.format() here.
        try:
            formatted_message = render_template(message_format, welcome_values(member, guild))
            await channel.send(formatted_message)
            logger.info(f"Sent welcome message for {member} in {guild.name}.")
        except discord.Forbidden:
            logger.error(f"Missing permissions for welcome message in #{channel.name} ({guild.name}). Disabling system.")
            await self.bot.db.set_feature_enabled(guild.id, "welcome-message", False)
        except Exception as e:
            logger.error(f"Failed to send welcome message in {guild.name}: {e}", exc_info=True)

    async def _assign_auto_role(self, member: discord.Member) -> None:
        guild = member.guild
        if not self.bot.db:
            return

        auto_role_id = await self.bot.db.get_guild_setting(guild.id, "autorole_id")
        if not auto_role_id:
            return

        role = guild.get_role(auto_role_id)
        if not role:
            logger.warning(f"Auto-role ID {auto_role_id} not found in {guild.name}. Removing setting.")
            await self.bot.db.set_guild_setting(guild.id, "autorole_id", None)
            return

        if role >= guild.me.top_role:
            logger.error(f"Cannot assign auto-role '{role.name}' in {guild.name} as it is higher or equal to my top role.")
            channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
            if channel:
                loc = await self.bot.db.get_locale(guild.id)
                await channel.send(t(loc, "welcome.autorole_too_high_channel", role=role.name))
            return

        try:
            await member.add_roles(role, reason="Automatic role assignment on join.")
            logger.info(f"Assigned auto-role '{role.name}' to {member} in {guild.name}.")
        except discord.Forbidden:
            logger.error(f"Missing permissions to assign auto-role in {guild.name}.")
            channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
            if channel:
                loc = await self.bot.db.get_locale(guild.id)
                await channel.send(t(loc, "welcome.autorole_no_perms_channel", role=role.name))
        except Exception as e:
            logger.error(f"Failed to assign auto-role in {guild.name}: {e}", exc_info=True)

    @commands.hybrid_group(name="welcome", fallback="status")
    @has_permission("config")
    async def welcome(self, ctx: commands.Context):
        """Displays the current welcome system and auto-role settings."""
        if not self.bot.db:
            return await reply(ctx, t("en", "common.db_unavailable"))
        loc = await self.bot.db.get_locale(ctx.guild.id)

        enabled_features = await self.bot.db.get_enabled_features(ctx.guild.id)
        is_enabled = "welcome-message" in enabled_features
        channel_id = await self.bot.db.get_guild_setting(ctx.guild.id, "welcome_channel_id")
        message = await self.bot.db.get_guild_setting(ctx.guild.id, "welcome_message", DEFAULT_WELCOME_MESSAGE)
        auto_role_id = await self.bot.db.get_guild_setting(ctx.guild.id, "autorole_id")

        embed = discord.Embed(title=t(loc, "welcome.status_title"), color=discord.Color.blue())

        # Welcome Message Info
        status = t(loc, "common.enabled") if is_enabled else t(loc, "common.disabled")
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        channel_status = channel.mention if channel else t(loc, "common.not_set")
        embed.add_field(
            name=t(loc, "welcome.field_messages"),
            value=t(loc, "welcome.field_messages_value", status=status, channel=channel_status),
            inline=False,
        )
        embed.add_field(name=t(loc, "welcome.field_template"), value=f"```{message}```", inline=False)

        # Auto-Role Info
        auto_role = ctx.guild.get_role(auto_role_id) if auto_role_id else None
        role_status = auto_role.mention if auto_role else t(loc, "common.not_set")
        embed.add_field(
            name=t(loc, "welcome.field_autorole"),
            value=t(loc, "welcome.field_autorole_value", role=role_status),
            inline=False,
        )

        await reply(ctx, embed=embed)

    @welcome.command(name="toggle")
    @has_permission("config")
    async def welcome_toggle(self, ctx: commands.Context):
        """Enables or disables the welcome message system."""
        if not self.bot.db:
            return await reply(ctx, t("en", "common.db_unavailable"))
        loc = await self.bot.db.get_locale(ctx.guild.id)

        enabled_features = await self.bot.db.get_enabled_features(ctx.guild.id)
        is_enabled = "welcome-message" in enabled_features
        new_status = not is_enabled
        await self.bot.db.set_feature_enabled(ctx.guild.id, "welcome-message", new_status)
        await reply(ctx, t(loc, "welcome.toggled_on" if new_status else "welcome.toggled_off"))

    @welcome.command(name="channel")
    @has_permission("config")
    async def welcome_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the channel for welcome messages."""
        if not self.bot.db:
            return await reply(ctx, t("en", "common.db_unavailable"))
        loc = await self.bot.db.get_locale(ctx.guild.id)
        if not channel.permissions_for(ctx.guild.me).send_messages:
            return await reply(ctx, t(loc, "welcome.no_send_perms", channel=channel.mention))

        await self.bot.db.set_guild_setting(ctx.guild.id, "welcome_channel_id", channel.id)
        await reply(ctx, t(loc, "welcome.channel_set", channel=channel.mention))

    @welcome.command(name="message", description="Set the welcome message template for new members.")
    @has_permission("config")
    async def welcome_message(self, ctx: commands.Context, *, message: str):
        """Sets the custom welcome message. Use placeholders for dynamic content. Pre-validates placeholders and sanitizes input."""
        if not self.bot.db:
            return await reply(ctx, t("en", "common.db_unavailable"))
        loc = await self.bot.db.get_locale(ctx.guild.id)
        if len(message) > 1500:
            return await reply(ctx, t(loc, "welcome.msg_too_long"))
        # Warn (don't format the live objects) if the template uses an unknown
        # placeholder — it would be left as literal text rather than substituted.
        if not is_template_valid(message):
            return await reply(ctx, t(loc, "welcome.msg_invalid_placeholder", error="unknown placeholder"))

        await self.bot.db.set_guild_setting(ctx.guild.id, "welcome_message", message)
        await reply(ctx, t(loc, "welcome.msg_updated"))

    @welcome.command(name="autorole")
    @has_permission("config")
    async def welcome_autorole(self, ctx: commands.Context, role: Optional[discord.Role] = None):
        """Sets or removes the role automatically assigned to new members."""
        if not self.bot.db:
            return await reply(ctx, t("en", "common.db_unavailable"))
        loc = await self.bot.db.get_locale(ctx.guild.id)
        if role:
            if role >= ctx.guild.me.top_role:
                return await reply(ctx, t(loc, "welcome.role_too_high", role=role.name))
            if role.is_default() or role.is_bot_managed() or role.is_premium_subscriber() or role.is_integration():
                return await reply(ctx, t(loc, "welcome.role_invalid", role=role.name))
            await self.bot.db.set_guild_setting(ctx.guild.id, "autorole_id", role.id)
            await reply(ctx, t(loc, "welcome.autorole_set", role=role.mention))
        else:
            await self.bot.db.set_guild_setting(ctx.guild.id, "autorole_id", None)
            await reply(ctx, t(loc, "welcome.autorole_disabled"))

    @welcome.command(name="test")
    @has_permission("config")
    async def welcome_test(self, ctx: commands.Context):
        """Sends a test welcome message to the configured channel."""
        if not self.bot.db:
            return await reply(ctx, t("en", "common.db_unavailable"))
        loc = await self.bot.db.get_locale(ctx.guild.id)

        enabled_features = await self.bot.db.get_enabled_features(ctx.guild.id)
        if "welcome-message" not in enabled_features:
            return await reply(ctx, t(loc, "welcome.test_disabled"))

        channel_id = await self.bot.db.get_guild_setting(ctx.guild.id, "welcome_channel_id")
        if not channel_id:
            return await reply(ctx, t(loc, "welcome.test_no_channel"))

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await reply(ctx, t(loc, "welcome.test_channel_missing"))

        await self._send_welcome_message(ctx.author)
        await reply(ctx, t(loc, "welcome.test_sent", channel=channel.mention))

    @welcome.command(name="placeholders")
    @has_permission("config")
    async def welcome_placeholders(self, ctx: commands.Context):
        """Shows available placeholders for the welcome message."""
        loc = await self.bot.db.get_locale(ctx.guild.id) if self.bot.db else "en"
        embed = discord.Embed(title=t(loc, "welcome.ph_title"), color=discord.Color.teal())
        embed.description = t(loc, "welcome.ph_desc")
        embed.add_field(name=t(loc, "welcome.ph_member"), value=t(loc, "welcome.ph_member_value"), inline=False)
        embed.add_field(name=t(loc, "welcome.ph_server"), value=t(loc, "welcome.ph_server_value"), inline=False)
        await reply(ctx, embed=embed)

    # Local error handler removed. The global handler in bot.py will now manage errors.

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeSystem(bot))
