# cogs/moderation.py
import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import time
import uuid
from core.logger import logger
from core.permissions import has_permission
from core.settings_manager import SettingsManager
from typing import Optional, Literal
from .utils import reply

class HierarchyError(commands.CheckFailure):
    """Custom exception for hierarchy check failures."""
    pass

class Moderation(commands.Cog, name="🛡️ Moderation"):
    """Server moderation commands with configurable permissions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager = bot.settings_manager

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
        if ctx.author.id != ctx.guild.owner_id and ctx.author.top_role <= target.top_role:
            raise HierarchyError("You cannot moderate a member with an equal or higher role.")
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
        log_channel_id = self.settings_manager.get_setting(ctx.guild.id, 'punishment_log_id')
        if not log_channel_id or not (log_channel := ctx.guild.get_channel(log_channel_id)):
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
            logger.warning(f"Could not log punishment to channel {log_channel_id} in guild {ctx.guild.id}.")

    @commands.hybrid_command(name="clear", description="Delete a specified number of messages.")
    @app_commands.describe(amount="Number of messages to delete (1-100).")
    @commands.bot_has_permissions(manage_messages=True)
    @has_permission("clear")
    async def clear(self, ctx: commands.Context, amount: commands.Range[int, 1, 100]):
        deleted = await ctx.channel.purge(limit=amount)
        await reply(ctx, f"✅ Deleted {len(deleted)} messages.", ephemeral=True)

    @commands.hybrid_command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="The member to kick.", reason="The reason for the kick.")
    @commands.bot_has_permissions(kick_members=True)
    @has_permission("kick")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        self._check_hierarchy(ctx, member)
        await self._notify_user(member, ctx.guild.name, "kicked", reason)
        await member.kick(reason=f"{reason} (Moderator: {ctx.author.id})")
        await self._log_action(ctx, "Member Kicked", member, reason)
        await reply(ctx, f"✅ **{member}** has been kicked.", ephemeral=True)

    @commands.hybrid_command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(member="The member to ban.", delete_messages="Delete user's message history.", reason="The reason for the ban.")
    @commands.bot_has_permissions(ban_members=True)
    @has_permission("ban")
    async def ban(self, ctx: commands.Context, member: discord.Member, delete_messages: Optional[Literal["Don't Delete", "1 Hour", "6 Hours", "12 Hours", "1 Day", "3 Days", "7 Days"]] = "Don't Delete", *, reason: str = "No reason provided"):
        self._check_hierarchy(ctx, member)
        delete_seconds_map = {
            "1 Hour": 3600, "6 Hours": 21600, "12 Hours": 43200,
            "1 Day": 86400, "3 Days": 259200, "7 Days": 604800
        }
        delete_seconds = delete_seconds_map.get(delete_messages, 0)

        await self._notify_user(member, ctx.guild.name, "banned", reason)
        await member.ban(reason=f"{reason} (Moderator: {ctx.author.id})", delete_message_seconds=delete_seconds)
        await self._log_action(ctx, "Member Banned", member, reason, delete_history=delete_messages)
        await reply(ctx, f"✅ **{member}** has been banned.", ephemeral=True)

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

    @commands.hybrid_command(name="mute", description="Mute a member for a specified duration.")
    @app_commands.describe(member="The member to mute.", duration="Duration (e.g., 10m, 1h, 1d). Max: 28d.", reason="The reason for the mute.")
    @commands.bot_has_permissions(moderate_members=True)
    @has_permission("mute")
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        self._check_hierarchy(ctx, member)
        try:
            units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
            amount = int(duration[:-1])
            unit = duration[-1].lower()
            if unit not in units:
                raise ValueError()
            delta = timedelta(seconds=amount * units[unit])
            if delta > timedelta(days=28):
                return await reply(ctx, "❌ Mute duration cannot exceed 28 days.", ephemeral=True)
        except (ValueError, KeyError):
            return await reply(ctx, "❌ Invalid duration format. Use a number followed by `s`, `m`, `h`, or `d`.", ephemeral=True)

        await self._notify_user(member, ctx.guild.name, "muted", reason, duration=duration)
        await member.timeout(delta, reason=f"{reason} (Moderator: {ctx.author.id})")
        await self._log_action(ctx, "Member Muted", member, reason, duration=duration)
        await reply(ctx, f"✅ **{member}** has been muted for {duration}.", ephemeral=True)

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

    @commands.hybrid_group(name="warn", description="Manage warnings for a member.")
    @has_permission("warn")
    async def warn(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            help_cog = self.bot.get_cog("❓ Help")
            if help_cog:
                await help_cog.send_command_help(ctx, ctx.command)
            else:
                await reply(ctx, "The help command is currently unavailable.", ephemeral=True)

    @warn.command(name="add", description="Warns a member and logs it.")
    @app_commands.describe(member="The member to warn.", reason="The reason for the warning.")
    @has_permission("warn")
    async def warn_add(self, ctx: commands.Context, member: discord.Member, *, reason: str):
        self._check_hierarchy(ctx, member)
        warnings = self.settings_manager.get_setting(ctx.guild.id, 'warnings', {})
        user_warnings = warnings.get(str(member.id), [])
        warn_id = str(uuid.uuid4()).split('-')[0]
        
        user_warnings.append({
            "id": warn_id, "moderator_id": ctx.author.id,
            "reason": reason, "timestamp": int(time.time())
        })
        warnings[str(member.id)] = user_warnings

        await self.settings_manager.update_setting(ctx.guild.id, 'warnings', warnings)
        await self._log_action(ctx, "Member Warned", member, reason, warning_id=warn_id, total_warnings=len(user_warnings))
        await reply(ctx, f"✅ **{member}** has been warned. (Warning ID: `{warn_id}`)", ephemeral=True)

    @warn.command(name="list", description="View warnings for a member.")
    @has_permission("warn")
    async def warn_list(self, ctx: commands.Context, member: discord.Member):
        all_warnings = self.settings_manager.get_setting(ctx.guild.id, 'warnings', {})
        user_warnings = all_warnings.get(str(member.id), [])

        if not user_warnings:
            return await reply(ctx, f"✅ **{member}** has no warnings.", ephemeral=True)

        embed = discord.Embed(title=f"Warnings for {member}", color=discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)
        
        description = []
        for w in user_warnings:
            mod_mention = f"<@{w['moderator_id']}>" or f"ID: {w['moderator_id']}"
            description.append(f"**ID:** `{w['id']}` | **Mod:** {mod_mention} (<t:{w['timestamp']}:R>)\n**Reason:** {w['reason']}")
        
        embed.description = "\n\n".join(description)
        await reply(ctx, embed=embed, ephemeral=True)

    @warn.command(name="remove", description="Remove a warning from a member by ID.")
    @app_commands.describe(member="The member to unwarn.", warn_id="The ID of the warning to remove.")
    @has_permission("warn")
    async def warn_remove(self, ctx: commands.Context, member: discord.Member, warn_id: str):
        all_warnings = self.settings_manager.get_setting(ctx.guild.id, 'warnings', {})
        user_warnings = all_warnings.get(str(member.id), [])

        if not any(w.get('id') == warn_id for w in user_warnings):
            return await reply(ctx, f"❌ Warning ID `{warn_id}` not found for {member}.", ephemeral=True)

        all_warnings[str(member.id)] = [w for w in user_warnings if w.get('id') != warn_id]
        await self.settings_manager.update_setting(ctx.guild.id, 'warnings', all_warnings)
        await self._log_action(ctx, "Warning Removed", member, f"Removed warning `{warn_id}`.")
        await reply(ctx, f"✅ Warning `{warn_id}` removed from **{member}**.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))

