# cogs/verification.py
import discord
from discord.ext import commands
from discord import app_commands

from core.logger import logger
from core.i18n import t
from core.permissions import role_is_assignable
from .utils import reply
from typing import Optional


class VerifyView(discord.ui.View):
    """Persistent view with the Verify button. Registered at startup with the
    default label (only used to re-bind the handler by custom_id); the posted
    panel carries a locale-aware label."""

    def __init__(self, loc: Optional[str] = None):
        super().__init__(timeout=None)
        if loc:
            self.verify.label = t(loc, "verify.button")

    @discord.ui.button(
        label="✅ Verify",
        style=discord.ButtonStyle.success,
        custom_id="verify_member",
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        bot = interaction.client
        guild = interaction.guild
        member = interaction.user
        loc = await bot.db.get_locale(guild.id)

        # The dashboard toggle controls the gate via enabled_features.
        enabled = await bot.db.get_enabled_features(guild.id)
        if "verification" not in enabled:
            return await interaction.response.send_message(t(loc, "verify.disabled"), ephemeral=True)

        role_id = await bot.db.get_guild_setting(guild.id, "verification_role_id")
        role = guild.get_role(int(role_id)) if role_id else None
        if role is None:
            return await interaction.response.send_message(t(loc, "verify.not_configured"), ephemeral=True)

        if role in member.roles:
            return await interaction.response.send_message(t(loc, "verify.already"), ephemeral=True)

        try:
            await member.add_roles(role, reason="Verification gate")
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"Verification: couldn't grant {role.name} to {member} in {guild.name}: {e}")
            return await interaction.response.send_message(t(loc, "verify.grant_failed"), ephemeral=True)

        await interaction.response.send_message(t(loc, "verify.granted"), ephemeral=True)
        logger.info(f"Verified {member} in {guild.name} (role {role.name})")


class VerificationCog(commands.Cog, name="✅ Verification"):
    """Verification gate: a panel with a button that grants the verified role."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Re-bind the persistent button handler after restarts.
        bot.add_view(VerifyView())

    @commands.hybrid_command(name="verify_setup", description="Post the verification panel to a channel.")
    @app_commands.describe(
        channel="Channel to post the Verify panel in.",
        role="Role granted to members who verify.",
    )
    @commands.has_permissions(manage_guild=True)
    async def verify_setup(self, ctx: commands.Context, channel: discord.TextChannel, role: discord.Role):
        loc = await self.bot.db.get_locale(ctx.guild.id)

        if not role_is_assignable(
            role_managed=role.managed,
            role_position=role.position,
            bot_top_role_pos=ctx.guild.me.top_role.position,
        ):
            return await reply(ctx, t(loc, "verify.setup_bad_role"), ephemeral=True)

        await self.bot.db.set_guild_setting(ctx.guild.id, "verification_role_id", role.id)

        embed = discord.Embed(
            title=t(loc, "verify.panel_title"),
            description=t(loc, "verify.panel_desc"),
            color=discord.Color.green(),
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        try:
            await channel.send(embed=embed, view=VerifyView(loc))
        except discord.Forbidden:
            return await reply(ctx, t(loc, "verify.setup_no_perm"), ephemeral=True)

        await reply(ctx, t(loc, "verify.setup_sent", channel=channel.mention), ephemeral=True)
        logger.info(f"Verification panel set up in #{channel.name} by {ctx.author} in {ctx.guild.name}")


async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))
