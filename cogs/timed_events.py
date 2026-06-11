# cogs/timed_events.py
import discord
from discord.ext import commands, tasks
from discord import app_commands
from core.logger import logger
from core.permissions import has_permission
from .utils import reply
import datetime
import re


def parse_duration(duration_str: str) -> int | None:
    """
    Parses a duration string like '30m', '2h', '1d' into seconds.
    Returns None if the format is invalid.
    """
    pattern = re.compile(r'^(\d+)(s|m|h|d)$')
    match = pattern.match(duration_str.lower().strip())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    seconds = value * multipliers[unit]
    if seconds <= 0 or seconds > 60 * 60 * 24 * 365:
        return None
    return seconds


def format_duration(seconds: int) -> str:
    """Formats seconds into a human-readable string like '2h 30m'."""
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    parts = []
    for name, secs in periods:
        if seconds >= secs:
            parts.append(f"{seconds // secs}{name}")
            seconds %= secs
    return ' '.join(parts) if parts else '0s'


class TimedEventsCog(commands.Cog, name="⏱️ Timed Events"):
    """Handles timed punishments: temp mute and temp ban with auto-expiry."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager = bot.settings_manager
        self.check_expired_punishments.start()

    def cog_unload(self):
        self.check_expired_punishments.cancel()

    @tasks.loop(seconds=60)
    async def check_expired_punishments(self):
        """Checks PostgreSQL for expired punishments and lifts them."""
        try:
            if not self.bot.db:
                return

            expired = await self.bot.db.get_expired_punishments()

            for record in expired:
                guild_id = record['guild_id']
                user_id = record['user_id']
                punishment_type = record['punishment_type']
                guild = self.bot.get_guild(guild_id)

                if not guild:
                    await self.bot.db.remove_timed_punishment(guild_id, user_id)
                    continue

                try:
                    if punishment_type == 'mute':
                        member = guild.get_member(user_id)
                        if member:
                            mute_role = discord.utils.get(guild.roles, name="Muted")
                            if mute_role and mute_role in member.roles:
                                await member.remove_roles(mute_role, reason="Timed mute expired")
                                logger.info(f"Auto-unmuted {member} in {guild.name}")
                    elif punishment_type == 'ban':
                        try:
                            await guild.unban(
                                discord.Object(id=user_id),
                                reason="Timed ban expired"
                            )
                            logger.info(f"Auto-unbanned {user_id} in {guild.name}")
                        except discord.NotFound:
                            pass

                    await self.bot.db.remove_timed_punishment(guild_id, user_id)

                    # Log to punishment channel
                    log_channel_id = await self.bot.db.get_guild_setting(guild_id, 'punishment_log_id')
                    if log_channel_id:
                        channel = guild.get_channel(log_channel_id)
                        if channel:
                            embed = discord.Embed(
                                title=f"⏰ Timed {punishment_type.title()} Expired",
                                color=discord.Color.green(),
                                timestamp=datetime.datetime.utcnow()
                            )
                            embed.add_field(name="User ID", value=f"`{user_id}`", inline=True)
                            embed.add_field(
                                name="Action",
                                value=f"Auto-{'unmuted' if punishment_type == 'mute' else 'unbanned'}",
                                inline=True
                            )
                            await channel.send(embed=embed)

                except discord.Forbidden as e:
                    logger.warning(f"Missing permissions for {punishment_type} on {user_id} in {guild.name}: {e}")
                except Exception as e:
                    logger.error(f"Error lifting {punishment_type} for {user_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"check_expired_punishments crashed: {e}", exc_info=True)

    @check_expired_punishments.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="tempmute", description="Temporarily mute a member.")
    @app_commands.describe(
        member="Member to mute.",
        duration="Duration (e.g. 30m, 2h, 1d).",
        reason="Reason for the mute."
    )
    @commands.cooldown(3, 10, commands.BucketType.user)
    @has_permission("mute")
    async def tempmute(self, ctx: commands.Context, member: discord.Member,
                       duration: str, *, reason: str = "No reason provided"):
        seconds = parse_duration(duration)
        if not seconds:
            return await reply(ctx,
                "❌ Invalid duration format. Use: `30s`, `10m`, `2h`, `1d`",
                ephemeral=True
            )

        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            # Create mute role if it doesn't exist
            try:
                mute_role = await ctx.guild.create_role(name="Muted", reason="Created for mute system")
                for channel in ctx.guild.channels:
                    await channel.set_permissions(mute_role, send_messages=False, speak=False)
            except discord.Forbidden:
                return await reply(ctx,
                    "❌ I don't have permission to create roles.",
                    ephemeral=True
                )

        await member.add_roles(mute_role, reason=f"{reason} | Moderator: {ctx.author}")

        expires_at = (datetime.datetime.utcnow() +
                      datetime.timedelta(seconds=seconds)).timestamp()
        timed = self.settings_manager.get_setting(ctx.guild.id, 'timed_punishments', {})
        timed[str(member.id)] = {
            'type': 'mute',
            'expires_at': expires_at,
            'reason': reason,
            'moderator_id': ctx.author.id
        }
        await self.settings_manager.update_setting(ctx.guild.id, 'timed_punishments', timed)

        embed = discord.Embed(title="🔇 Temporary Mute", color=discord.Color.orange())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Duration", value=format_duration(seconds), inline=True)
        embed.add_field(name="Expires", value=f"<t:{int(expires_at)}:R>", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        await reply(ctx, embed=embed)

        # DM user
        try:
            dm_embed = discord.Embed(
                title=f"🔇 You have been temporarily muted in {ctx.guild.name}",
                color=discord.Color.orange()
            )
            dm_embed.add_field(name="Duration", value=format_duration(seconds), inline=True)
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        logger.info(f"Temp-muted {member} in {ctx.guild.name} for {format_duration(seconds)} by {ctx.author}")

    @commands.hybrid_command(name="tempban", description="Temporarily ban a member.")
    @app_commands.describe(
        member="Member to ban.",
        duration="Duration (e.g. 30m, 2h, 1d).",
        reason="Reason for the ban."
    )
    @commands.cooldown(3, 10, commands.BucketType.user)
    @has_permission("ban")
    async def tempban(self, ctx: commands.Context, member: discord.Member,
                      duration: str, *, reason: str = "No reason provided"):
        seconds = parse_duration(duration)
        if not seconds:
            return await reply(ctx,
                "❌ Invalid duration format. Use: `30s`, `10m`, `2h`, `1d`",
                ephemeral=True
            )

        expires_at = (datetime.datetime.utcnow() +
                      datetime.timedelta(seconds=seconds)).timestamp()

        # DM user before ban
        try:
            dm_embed = discord.Embed(
                title=f"🔨 You have been temporarily banned from {ctx.guild.name}",
                color=discord.Color.red()
            )
            dm_embed.add_field(name="Duration", value=format_duration(seconds), inline=True)
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        await member.ban(reason=f"{reason} | Moderator: {ctx.author} | Duration: {format_duration(seconds)}")

        timed = self.settings_manager.get_setting(ctx.guild.id, 'timed_punishments', {})
        timed[str(member.id)] = {
            'type': 'ban',
            'expires_at': expires_at,
            'reason': reason,
            'moderator_id': ctx.author.id
        }
        await self.settings_manager.update_setting(ctx.guild.id, 'timed_punishments', timed)

        embed = discord.Embed(title="🔨 Temporary Ban", color=discord.Color.red())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Duration", value=format_duration(seconds), inline=True)
        embed.add_field(name="Expires", value=f"<t:{int(expires_at)}:R>", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        await reply(ctx, embed=embed)

        logger.info(f"Temp-banned {member} in {ctx.guild.name} for {format_duration(seconds)} by {ctx.author}")


async def setup(bot: commands.Bot):
    await bot.add_cog(TimedEventsCog(bot))
