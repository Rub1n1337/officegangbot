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
        # In-memory XP cache: {guild_id: {user_id: data_dict}}
        self._xp_cache: dict = {}
        self._dirty_guilds: set = set()  # Guilds with unsaved XP changes
        self.cleanup_xp_cooldowns.start()
        self.flush_xp_cache.start()

    async def _get_user_data_db(self, guild_id: int, user_id: int) -> dict:
        """Returns XP data from cache or PostgreSQL."""
        if guild_id not in self._xp_cache:
            self._xp_cache[guild_id] = {}

        user_id_str = str(user_id)
        if user_id_str not in self._xp_cache[guild_id]:
            db_data = await self.bot.db.get_user_xp(guild_id, user_id)
            self._xp_cache[guild_id][user_id_str] = db_data

        return dict(self._xp_cache[guild_id].get(user_id_str, {'xp': 0, 'level': 0}))

    def _save_user_data(self, guild_id: int, user_id: int, data: dict):
        """Saves XP data to in-memory cache only. Disk flush happens every 2 minutes."""
        if guild_id not in self._xp_cache:
            self._xp_cache[guild_id] = {}
        self._xp_cache[guild_id][str(user_id)] = data
        self._dirty_guilds.add(guild_id)

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
            user_data = await self._get_user_data_db(guild_id, user_id)
            old_level = user_data['level']
            user_data['xp'] += xp_gain
            new_level = get_level_from_xp(user_data['xp'])
            user_data['level'] = new_level
            # Save username for leaderboard display even after user leaves
            user_data['display_name'] = message.author.display_name
            self._save_user_data(guild_id, user_id, user_data)

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
        user_data = await self._get_user_data_db(ctx.guild.id, member.id)

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
        rows = await self.bot.db.get_leaderboard(ctx.guild.id, limit=10)
        if not rows:
            return await reply(ctx, "❌ No XP data found for this server.", ephemeral=True)

        embed = discord.Embed(title="🏆 XP Leaderboard", color=discord.Color.gold())
        medals = ["🥇", "🥈", "🥉"]
        description = ""

        for i, row in enumerate(rows):
            member = ctx.guild.get_member(row['user_id'])
            name = member.display_name if member else (row.get('display_name') or f"User {row['user_id']}")
            medal = medals[i] if i < 3 else f"`#{i+1}`"
            description += f"{medal} **{name}** — Level {row['level']} | {row['xp']} XP\n"

        embed.description = description
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
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

    @tasks.loop(minutes=2)
    async def flush_xp_cache(self):
        """Flushes in-memory XP cache to PostgreSQL every 2 minutes via bulk upsert."""
        try:
            if not self._dirty_guilds:
                return

            dirty = set(self._dirty_guilds)
            self._dirty_guilds.clear()

            records = []
            for guild_id in dirty:
                if guild_id not in self._xp_cache:
                    continue
                for user_id_str, data in self._xp_cache[guild_id].items():
                    records.append({
                        'guild_id': guild_id,
                        'user_id': int(user_id_str),
                        'xp': data.get('xp', 0),
                        'level': data.get('level', 0),
                        'display_name': data.get('display_name', '')
                    })

            if records:
                await self.bot.db.bulk_upsert_xp(records)
                logger.info(f"XP cache flushed: {len(records)} records to PostgreSQL")

        except Exception as e:
            logger.error(f"flush_xp_cache crashed: {e}", exc_info=True)

    @flush_xp_cache.before_loop
    async def before_flush_xp(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.cleanup_xp_cooldowns.cancel()
        self.flush_xp_cache.cancel()
        # Don't attempt DB write on unload - pool may already be closed
        self._dirty_guilds.clear()
        self._xp_cache.clear()


async def setup(bot: commands.Bot):
    await bot.add_cog(LevelsCog(bot))
