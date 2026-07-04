# cogs/moderation.py
import discord
from discord.ext import commands
from discord import app_commands
from core.logger import logger
from core.permissions import has_permission, member_hierarchy_block
from core.i18n import t
from core.appeals import send_ban_appeal_dm
from typing import Optional
from .utils import reply

# Map the shared hierarchy reason codes to this cog's i18n message keys.
_HIERARCHY_KEYS = {
    "self": "mod.hierarchy_self",
    "bot_self": "mod.hierarchy_bot_self",
    "owner": "mod.hierarchy_owner",
    "higher": "mod.hierarchy_higher",
    "bot_higher": "mod.hierarchy_bot_higher",
}

class BanConfirmView(discord.ui.View):
    """Confirmation view for the /ban command."""

    def __init__(self, moderator: discord.Member, target: discord.Member, reason: str, loc: str):
        super().__init__(timeout=30)
        self.moderator = moderator
        self.target = target
        self.reason = reason
        self.loc = loc
        self.confirmed = False
        # Localize the button labels (decorator labels are the fallback).
        self.confirm.label = t(loc, "mod.ban_confirm_label")
        self.cancel.label = t(loc, "mod.ban_cancel_label")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the moderator who called the command can press the buttons."""
        if interaction.user.id != self.moderator.id:
            await interaction.response.send_message(
                t(self.loc, "mod.ban_not_yours"),
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="✅ Confirm Ban", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(
            content=t(self.loc, "mod.ban_in_progress", target=self.target),
            view=None
        )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.edit_message(
            content=t(self.loc, "mod.ban_view_cancelled", target=self.target),
            view=None
        )

    async def on_timeout(self):
        self.confirmed = False
        self.stop()

class HierarchyError(commands.CheckFailure):
    """Custom exception for hierarchy check failures. Carries an i18n key."""
    pass

class Moderation(commands.Cog, name="🛡️ Moderation"):
    """Server moderation commands with configurable permissions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handles errors for all commands in this cog."""
        if isinstance(error, commands.CommandNotFound):
            return

        loc = "en"
        if ctx.guild and self.bot.db:
            try:
                loc = await self.bot.db.get_locale(ctx.guild.id)
            except Exception:
                loc = "en"

        if isinstance(error, HierarchyError):
            # error message is an i18n key set by _check_hierarchy.
            await reply(ctx, t(loc, str(error)), ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ', '.join(error.missing_permissions)
            await reply(ctx, t(loc, "mod.err_bot_missing_perms", perms=perms), ephemeral=True)
        elif isinstance(error, (commands.MissingPermissions, commands.CheckFailure)):
            await reply(ctx, t(loc, "mod.err_no_permission"), ephemeral=True)
        elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            await reply(ctx, t(loc, "mod.err_member_not_found", argument=error.argument), ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await reply(ctx, t(loc, "mod.err_bad_argument"), ephemeral=True)
        else:
            logger.error(f"An unhandled error occurred in moderation cog: {error}", exc_info=True)
            await reply(ctx, t(loc, "mod.err_unexpected"), ephemeral=True)

    def _check_hierarchy(self, ctx: commands.Context, target: discord.Member):
        """Checks if the author can perform an action on the target.

        Raises HierarchyError whose message is an i18n key, translated by the
        error handler in the guild's locale."""
        code = member_hierarchy_block(
            author_id=ctx.author.id,
            author_top_role_pos=ctx.author.top_role.position,
            target_id=target.id,
            target_top_role_pos=target.top_role.position,
            bot_id=self.bot.user.id,
            bot_top_role_pos=ctx.guild.me.top_role.position,
            owner_id=ctx.guild.owner_id,
        )
        if code:
            raise HierarchyError(_HIERARCHY_KEYS[code])

    async def _notify_user(self, target: discord.Member, guild_name: str, title_key: str, reason: str, loc: str, duration: Optional[str] = None):
        """Sends a DM to the user about the moderation action, in the guild's locale."""
        embed = discord.Embed(title=t(loc, title_key, guild=guild_name), color=discord.Color.red())
        embed.add_field(name=t(loc, "field.reason"), value=reason, inline=False)
        if duration:
            embed.add_field(name=t(loc, "field.duration"), value=duration, inline=False)
        try:
            await target.send(embed=embed)
            return True
        except discord.Forbidden:
            return False

    async def _log_action(self, ctx: commands.Context, action: str, target: discord.abc.User, reason: str, **kwargs):
        if not self.bot.db:
            return

        # Record a numbered case for every action, independent of whether the
        # logging channel is configured, so /case <n> always has a record.
        case_number = None
        try:
            case_number = await self.bot.db.add_mod_case(
                ctx.guild.id, action, getattr(target, "id", None), str(target),
                ctx.author.id, str(ctx.author), reason,
            )
        except Exception as e:
            logger.exception(f"Failed to record mod case for {action}: {e}")

        # Check if logging feature is enabled
        enabled_features = await self.bot.db.get_enabled_features(ctx.guild.id)
        if "logging" not in enabled_features:
            return

        log_channel_id = await self.bot.db.get_guild_setting(ctx.guild.id, 'punishment_log_id')
        if not log_channel_id:
            return

        log_channel = ctx.guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        timestamp = discord.utils.utcnow()
        title = f"{action}" + (f" · Case #{case_number}" if case_number is not None else "")
        embed = discord.Embed(title=title, color=discord.Color.orange(), timestamp=timestamp)
        embed.add_field(name="Target", value=f"{target.mention} (`{target.id}`)", inline=False)
        embed.add_field(name="Moderator", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
        embed.add_field(name="Reason", value=f"```{reason}```", inline=False)

        for key, value in kwargs.items():
            embed.add_field(name=key.replace('_', ' ').title(), value=value, inline=True)

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.hybrid_command(name="clear", description="Delete a specified number of messages.")
    @app_commands.describe(amount="Number of messages to delete (1-100).")
    @commands.bot_has_permissions(manage_messages=True)
    @commands.cooldown(3, 10, commands.BucketType.user)
    @has_permission("clear")
    async def clear(self, ctx: commands.Context, amount: commands.Range[int, 1, 100]):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        deleted = await ctx.channel.purge(limit=amount)
        await reply(ctx, t(loc, "mod.cleared", count=len(deleted)), ephemeral=True)

    @commands.hybrid_command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="The member to kick.", reason="The reason for the kick.")
    @commands.bot_has_permissions(kick_members=True)
    @commands.cooldown(3, 10, commands.BucketType.user)
    @has_permission("kick")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        self._check_hierarchy(ctx, member)
        await self._notify_user(member, ctx.guild.name, "mod.dm_kicked_title", reason, loc)
        await member.kick(reason=f"{reason} (Moderator: {ctx.author.id})")
        await self._log_action(ctx, "Member Kicked", member, reason)
        await reply(ctx, t(loc, "mod.kicked", member=member), ephemeral=True)

    @commands.hybrid_command(name="ban", description="Ban a member from the server.", extras={"manages_own_response": True})
    @app_commands.describe(member="Member to ban.", reason="Reason for the ban.")
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(3, 10, commands.BucketType.user)
    @has_permission("ban")
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        self._check_hierarchy(ctx, member)

        view = BanConfirmView(moderator=ctx.author, target=member, reason=reason, loc=loc)

        confirm_content = t(loc, "mod.ban_confirm_prompt", member=member.mention, reason=reason)

        if ctx.interaction:
            await ctx.interaction.response.send_message(
                content=confirm_content,
                view=view,
                ephemeral=True
            )
        else:
            await ctx.send(content=confirm_content, view=view)

        await view.wait()

        if not view.confirmed:
            return

        # When ban appeals are enabled, the DM carries an "Appeal" button;
        # otherwise it's the plain ban notice.
        if await self.bot.db.get_guild_setting(ctx.guild.id, "ban_appeals_enabled"):
            dm_sent = await send_ban_appeal_dm(ctx.guild, member, reason, loc)
        else:
            dm_sent = await self._notify_user(member, ctx.guild.name, "mod.dm_banned_title", reason, loc)
        await member.ban(reason=f"{reason} | Moderator: {ctx.author}")
        await self._log_action(ctx, "🔨 Ban", member, reason, dm_notified="✅" if dm_sent else "❌")

        result_content = t(loc, "mod.banned", member=member.mention, reason=reason)
        if ctx.interaction:
            await ctx.interaction.followup.send(content=result_content, ephemeral=True)
        else:
            await ctx.send(content=result_content)

    @commands.hybrid_command(name="unban", description="Unban a user from the server.")
    @app_commands.describe(user_id="The ID of the user to unban.", reason="The reason for the unban.")
    @commands.bot_has_permissions(ban_members=True)
    @has_permission("ban")
    async def unban(self, ctx: commands.Context, user_id: str, *, reason: str = "No reason provided"):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            return await reply(ctx, t(loc, "mod.unban_invalid"), ephemeral=True)

        try:
            await ctx.guild.unban(user, reason=f"{reason} (Moderator: {ctx.author.id})")
            await self._log_action(ctx, "User Unbanned", user, reason)
            await reply(ctx, t(loc, "mod.unbanned", user=user), ephemeral=True)
        except discord.NotFound:
            await reply(ctx, t(loc, "mod.unban_not_banned", user=user), ephemeral=True)

    @commands.hybrid_command(name="unmute", description="Unmute a member.")
    @app_commands.describe(member="The member to unmute.", reason="The reason for unmuting.")
    @commands.bot_has_permissions(moderate_members=True)
    @has_permission("mute")
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Moderator decision"):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        self._check_hierarchy(ctx, member)
        if not member.is_timed_out():
            return await reply(ctx, t(loc, "mod.unmute_not_muted", member=member.mention), ephemeral=True)

        await member.timeout(None, reason=f"{reason} (Moderator: {ctx.author.id})")
        await self._log_action(ctx, "Member Unmuted", member, reason)
        await reply(ctx, t(loc, "mod.unmuted", member=member), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
