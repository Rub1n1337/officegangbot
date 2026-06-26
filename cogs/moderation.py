# cogs/moderation.py
import discord
from discord.ext import commands
from discord import app_commands
from core.logger import logger
from core.permissions import has_permission
from typing import Optional
from .utils import reply

class BanConfirmView(discord.ui.View):
    """Confirmation view for the /ban command."""

    def __init__(self, moderator: discord.Member, target: discord.Member, reason: str):
        super().__init__(timeout=30)
        self.moderator = moderator
        self.target = target
        self.reason = reason
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the moderator who called the command can press the buttons."""
        if interaction.user.id != self.moderator.id:
            await interaction.response.send_message(
                "❌ Only the moderator who issued this command can confirm the action.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="✅ Confirm Ban", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(
            content=f"⏳ Banning `{self.target}`...",
            view=None
        )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.edit_message(
            content=f"🚫 Ban of `{self.target}` has been cancelled.",
            view=None
        )

    async def on_timeout(self):
        self.confirmed = False
        self.stop()

class HierarchyError(commands.CheckFailure):
    """Custom exception for hierarchy check failures."""
    pass

class Moderation(commands.Cog, name="🛡️ Moderation"):
    """Server moderation commands with configurable permissions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handles errors for all commands in this cog."""
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, HierarchyError):
            await reply(ctx, f"❌ {error}", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ', '.join(error.missing_permissions)
            await reply(ctx, f"❌ I need the following permissions to do that: `{perms}`.", ephemeral=True)
        elif isinstance(error, (commands.MissingPermissions, commands.CheckFailure)):
            await reply(ctx, "❌ You don't have the required permissions for this command.", ephemeral=True)
        elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            await reply(ctx, f"❌ I could not find a user named `{error.argument}`. Please check the name or use their ID.", ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await reply(ctx, "❌ Invalid argument provided. Please check the command's help for usage.", ephemeral=True)
        else:
            logger.error(f"An unhandled error occurred in moderation cog: {error}", exc_info=True)
            await reply(ctx, "🐞 An unexpected error occurred. The developers have been notified.", ephemeral=True)

    def _check_hierarchy(self, ctx: commands.Context, target: discord.Member):
        """Checks if the author can perform an action on the target."""
        if target.id == ctx.author.id:
            raise HierarchyError("You cannot moderate yourself.")
        if target.id == self.bot.user.id:
            raise HierarchyError("I cannot moderate myself.")
        if target.id == ctx.guild.owner_id:
            raise HierarchyError("You cannot moderate the server owner.")
        # Moderators may act on members with an EQUAL top role; only a strictly
        # higher target is blocked. (Bot-side check below stays <= on purpose.)
        if ctx.author.id != ctx.guild.owner_id and ctx.author.top_role < target.top_role:
            raise HierarchyError("You cannot moderate a member with a higher role.")
        if ctx.guild.me.top_role <= target.top_role:
            raise HierarchyError("I cannot moderate a member with an equal or higher role than me.")

    async def _notify_user(self, target: discord.Member, guild_name: str, action: str, reason: str, duration: Optional[str] = None):
        """Sends a DM to the user about the moderation action."""
        embed = discord.Embed(title=f"You have been {action} in {guild_name}", color=discord.Color.red())
        embed.add_field(name="Reason", value=reason, inline=False)
        if duration:
            embed.add_field(name="Duration", value=duration, inline=False)
        try:
            await target.send(embed=embed)
            return True
        except discord.Forbidden:
            return False

    async def _log_action(self, ctx: commands.Context, action: str, target: discord.abc.User, reason: str, **kwargs):
        if not self.bot.db:
            return

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
        embed = discord.Embed(title=f"{action}", color=discord.Color.orange(), timestamp=timestamp)
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
        deleted = await ctx.channel.purge(limit=amount)
        await reply(ctx, f"✅ Deleted {len(deleted)} messages.", ephemeral=True)

    @commands.hybrid_command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="The member to kick.", reason="The reason for the kick.")
    @commands.bot_has_permissions(kick_members=True)
    @commands.cooldown(3, 10, commands.BucketType.user)
    @has_permission("kick")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        self._check_hierarchy(ctx, member)
        await self._notify_user(member, ctx.guild.name, "kicked", reason)
        await member.kick(reason=f"{reason} (Moderator: {ctx.author.id})")
        await self._log_action(ctx, "Member Kicked", member, reason)
        await reply(ctx, f"✅ **{member}** has been kicked.", ephemeral=True)

    @commands.hybrid_command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(member="Member to ban.", reason="Reason for the ban.")
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(3, 10, commands.BucketType.user)
    @has_permission("ban")
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        self._check_hierarchy(ctx, member)

        view = BanConfirmView(moderator=ctx.author, target=member, reason=reason)

        confirm_content = (
            f"⚠️ **Ban Confirmation**\n"
            f"Are you sure you want to ban {member.mention}?\n"
            f"**Reason:** `{reason}`"
        )

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

        dm_sent = await self._notify_user(member, ctx.guild.name, "banned", reason)
        await member.ban(reason=f"{reason} | Moderator: {ctx.author}")
        await self._log_action(ctx, "🔨 Ban", member, reason, dm_notified="✅" if dm_sent else "❌")

        result_content = f"✅ {member.mention} has been banned. Reason: `{reason}`"
        if ctx.interaction:
            await ctx.interaction.followup.send(content=result_content, ephemeral=True)
        else:
            await ctx.send(content=result_content)

    @commands.hybrid_command(name="unban", description="Unban a user from the server.")
    @app_commands.describe(user_id="The ID of the user to unban.", reason="The reason for the unban.")
    @commands.bot_has_permissions(ban_members=True)
    @has_permission("ban")
    async def unban(self, ctx: commands.Context, user_id: str, *, reason: str = "No reason provided"):
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            return await reply(ctx, "❌ Invalid user ID or user not found.", ephemeral=True)
        
        try:
            await ctx.guild.unban(user, reason=f"{reason} (Moderator: {ctx.author.id})")
            await self._log_action(ctx, "User Unbanned", user, reason)
            await reply(ctx, f"✅ **{user}** has been unbanned.", ephemeral=True)
        except discord.NotFound:
            await reply(ctx, f"❌ **{user}** is not banned from this server.", ephemeral=True)

    @commands.hybrid_command(name="unmute", description="Unmute a member.")
    @app_commands.describe(member="The member to unmute.", reason="The reason for unmuting.")
    @commands.bot_has_permissions(moderate_members=True)
    @has_permission("mute")
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Moderator decision"):
        self._check_hierarchy(ctx, member)
        if not member.is_timed_out():
            return await reply(ctx, f"❌ {member.mention} is not currently muted.", ephemeral=True)
        
        await member.timeout(None, reason=f"{reason} (Moderator: {ctx.author.id})")
        await self._log_action(ctx, "Member Unmuted", member, reason)
        await reply(ctx, f"✅ **{member}** has been unmuted.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
