# cogs/levels.py
import discord
from discord.ext import commands, tasks
from discord import app_commands
from core.logger import logger
from .utils import reply
from typing import Optional
import random
import datetime
import asyncio


def get_xp_for_level(level: int) -> int:
    """Returns total XP required to reach a given level."""
    return 5 * (level ** 2) + 50 * level + 100


def get_level_from_xp(xp: int) -> int:
    """Calculates current level from total XP."""
    level = 0
    while xp >= get_xp_for_level(level):
        xp -= get_xp_for_level(level)
        level += 1
    return level


def build_progress_bar(current_xp: int, required_xp: int, length: int = 10) -> str:
    """Builds a Unicode progress bar."""
    filled = int((current_xp / required_xp) * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"


class LevelsCog(commands.Cog, name="⭐ Levels"):
    """XP and leveling system with role rewards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager = bot.settings_manager
        # Cooldown tracking: {guild_id: {user_id: last_xp_timestamp}}
        self._xp_cooldowns: dict = {}
        self._xp_lock = asyncio.Lock()
        self.cleanup_xp_cooldowns.start()

    def _get_user_data(self, guild_id: int, user_id: int) -> dict:
        """Returns XP data for a user."""
        levels_data = self.settings_manager.get_setting(guild_id, 'levels', {})
        return levels_data.get(str(user_id), {'xp': 0, 'level': 0})

    async def _save_user_data(self, guild_id: int, user_id: int, data: dict):
        """Saves XP data for a user."""
        levels_data = self.settings_manager.get_setting(guild_id, 'levels', {})
        levels_data[str(user_id)] = data
        await self.settings_manager.update_setting(guild_id, 'levels', levels_data)

    async def _check_role_rewards(self, member: discord.Member, level: int):
        """Assigns role rewards for reaching a level."""
        role_rewards = self.settings_manager.get_setting(
            member.guild.id, 'level_roles', {}
        )
        for level_str, role_id in role_rewards.items():
            if level >= int(level_str):
                role = member.guild.get_role(int(role_id))
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Level {level} reward")
                        logger.info(
                            f"Assigned role {role.name} to {member} "
                            f"for reaching level {level} in {member.guild.name}"
                        )
                    except discord.Forbidden:
                        logger.warning(
                            f"Cannot assign role {role.name} to {member} — missing permissions"
                        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Awards XP for messages with a 60-second cooldown per user."""
        if message.author.bot or not message.guild:
            return

        # Check XP system is enabled for this guild
        if not self.settings_manager.get_setting(message.guild.id, 'levels_enabled', True):
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.datetime.utcnow().timestamp()

        # Cooldown check (60 seconds)
        guild_cooldowns = self._xp_cooldowns.setdefault(guild_id, {})
        last_xp = guild_cooldowns.get(user_id, 0)
        if now - last_xp < 60:
            return
        guild_cooldowns[user_id] = now

        # Award XP with lock to prevent race conditions
        xp_gain = random.randint(15, 25)
        async with self._xp_lock:
            user_data = self._get_user_data(guild_id, user_id)
            old_level = user_data['level']
            user_data['xp'] += xp_gain
            new_level = get_level_from_xp(user_data['xp'])
            user_data['level'] = new_level
            # Save username for leaderboard display even after user leaves
            user_data['display_name'] = message.author.display_name
            await self._save_user_data(guild_id, user_id, user_data)

        # Level up notification
        if new_level > old_level:
            level_up_channel_id = self.settings_manager.get_setting(
                guild_id, 'level_up_channel_id'
            )
            channel = (
                message.guild.get_channel(int(level_up_channel_id))
                if level_up_channel_id
                else message.channel
            )
            if channel:
                embed = discord.Embed(
                    title="⭐ Level Up!",
                    description=f"🎉 {message.author.mention} reached **Level {new_level}**!",
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=message.author.display_avatar.url)
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

            # Check and assign role rewards
            await self._check_role_rewards(message.author, new_level)

    @commands.hybrid_command(name="rank", description="Shows the rank and XP of a member.")
    @app_commands.describe(member="Member to check. Defaults to yourself.")
    async def rank(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        member = member or ctx.author
        user_data = self._get_user_data(ctx.guild.id, member.id)

        total_xp = user_data['xp']
        level = user_data['level']

        # Calculate XP within current level
        xp_so_far = total_xp
        for lvl in range(level):
            xp_so_far -= get_xp_for_level(lvl)
        xp_needed = get_xp_for_level(level)
        progress_bar = build_progress_bar(xp_so_far, xp_needed)

        embed = discord.Embed(
            title=f"⭐ {member.display_name}'s Rank",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="Total XP", value=f"**{total_xp}** XP", inline=True)
        embed.add_field(
            name="Progress to Next Level",
            value=f"{progress_bar}\n`{xp_so_far} / {xp_needed} XP`",
            inline=False
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        await reply(ctx, embed=embed)

    @commands.hybrid_command(name="setlevelrole", description="Assign a role reward for reaching a level.")
    @app_commands.describe(level="Level required.", role="Role to assign.")
    @commands.has_permissions(manage_roles=True)
    async def setlevelrole(self, ctx: commands.Context, level: int, role: discord.Role):
        if level < 1:
            return await reply(ctx, "❌ Level must be at least 1.", ephemeral=True)

        level_roles = self.settings_manager.get_setting(ctx.guild.id, 'level_roles', {})
        level_roles[str(level)] = str(role.id)
        await self.settings_manager.update_setting(ctx.guild.id, 'level_roles', level_roles)

        embed = discord.Embed(
            title="✅ Level Role Set",
            description=f"Members who reach **Level {level}** will receive {role.mention}.",
            color=discord.Color.green()
        )
        await reply(ctx, embed=embed)

    @commands.hybrid_command(name="leaderboard", description="Shows the top 10 members by XP.")
    async def leaderboard(self, ctx: commands.Context):
        levels_data = self.settings_manager.get_setting(ctx.guild.id, 'levels', {})
        if not levels_data:
            return await reply(ctx, "❌ No XP data found for this server.", ephemeral=True)

        sorted_users = sorted(levels_data.items(), key=lambda x: x[1].get('xp', 0), reverse=True)[:10]

        embed = discord.Embed(title="🏆 XP Leaderboard", color=discord.Color.gold())
        medals = ["🥇", "🥈", "🥉"]

        description = ""
        for i, (user_id, data) in enumerate(sorted_users):
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else data.get('display_name', f'User {user_id}')
            medal = medals[i] if i < 3 else f"`#{i+1}`"
            description += f"{medal} **{name}** — Level {data.get('level', 0)} | {data.get('xp', 0)} XP\n"

        embed.description = description
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        await reply(ctx, embed=embed)


    @tasks.loop(minutes=10)
    async def cleanup_xp_cooldowns(self):
        """Removes stale XP cooldown entries older than 120 seconds."""
        try:
            now = datetime.datetime.utcnow().timestamp()
            for guild_id in list(self._xp_cooldowns.keys()):
                self._xp_cooldowns[guild_id] = {
                    uid: ts for uid, ts in self._xp_cooldowns[guild_id].items()
                    if now - ts < 120
                }
        except Exception as e:
            logger.error(f"cleanup_xp_cooldowns crashed: {e}", exc_info=True)

    @cleanup_xp_cooldowns.before_loop
    async def before_cleanup_xp(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.cleanup_xp_cooldowns.cancel()


async def setup(bot: commands.Bot):
    await bot.add_cog(LevelsCog(bot))
