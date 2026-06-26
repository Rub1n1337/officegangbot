# cogs/levels.py
import discord
from discord.ext import commands, tasks
from discord import app_commands
from core.logger import logger
from .utils import reply, send_paginated
from core.i18n import t
from typing import Optional
import random
import datetime
import asyncio


def get_xp_for_level(level: int) -> int:
    """Returns the XP needed to advance from `level` to `level + 1`."""
    return 5 * (level ** 2) + 50 * level + 100


def _cumulative_xp(level: int) -> int:
    """Total XP required to reach `level` = sum(get_xp_for_level(0..level-1)),
    in closed form (sum of a quadratic) so it is O(1)."""
    n = level
    return 5 * (n - 1) * n * (2 * n - 1) // 6 + 50 * (n - 1) * n // 2 + 100 * n


_MAX_LEVEL = 1000


def get_level_from_xp(xp: int) -> int:
    """Current level for a total XP, in O(log n) via binary search over the
    closed-form cumulative curve. Called on every message. Capped at 1000."""
    if xp < _cumulative_xp(1):
        return 0
    lo, hi = 0, _MAX_LEVEL
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _cumulative_xp(mid) <= xp:
            lo = mid
        else:
            hi = mid - 1
    return lo


def build_progress_bar(current_xp: int, required_xp: int, length: int = 10) -> str:
    """Builds a Unicode progress bar."""
    filled = int((current_xp / required_xp) * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"


class LevelsCog(commands.Cog, name="⭐ Levels"):
    """XP and leveling system with role rewards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self._xp_lock = asyncio.Lock()
        # Redis handles caching — keep local dict only as write buffer
        self._write_buffer: dict = {}  # {guild_id: {user_id: data}}
        self._dirty_guilds: set = set()
        # Fallback cooldown tracking if Redis unavailable
        self._xp_cooldowns: dict = {}
        self.flush_xp_cache.start()

    async def _get_user_data(self, guild_id: int, user_id: int) -> dict:
        """Returns XP data from Redis cache, falling back to PostgreSQL."""
        # Try Redis first
        if self.bot.redis:
            cached = await self.bot.redis.get_xp_data(guild_id, user_id)
            if cached is not None:
                return cached

        # Fallback to PostgreSQL
        if self.bot.db:
            data = await self.bot.db.get_user_xp(guild_id, user_id)
        else:
            data = {'xp': 0, 'level': 0, 'display_name': None}

        # Populate Redis cache
        if self.bot.redis and data:
            await self.bot.redis.set_xp_data(guild_id, user_id, data)

        return data

    def _save_user_data(self, guild_id: int, user_id: int, data: dict) -> None:
        """Saves XP to write buffer and marks dirty for DB flush."""
        if guild_id not in self._write_buffer:
            self._write_buffer[guild_id] = {}
        self._write_buffer[guild_id][str(user_id)] = data
        self._dirty_guilds.add(guild_id)

    async def _check_role_rewards(self, member: discord.Member, level: int):
        """Assigns role rewards for reaching a level."""
        # Try to get from DB first
        role_rewards = await self.bot.db.get_level_roles(member.guild.id)
            
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
        enabled_features = await self.bot.db.get_enabled_features(message.guild.id)
        if "levels" not in enabled_features:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()

        # Cooldown check via Redis (atomic, cross-process safe)
        if self.bot.redis:
            on_cooldown = await self.bot.redis.check_xp_cooldown(guild_id, user_id)
            if on_cooldown:
                return
        else:
            # Fallback to in-memory cooldown
            guild_cooldowns = self._xp_cooldowns.setdefault(guild_id, {})
            last_xp = guild_cooldowns.get(user_id, 0)
            if now - last_xp < 60:
                return
            guild_cooldowns[user_id] = now

        # Award XP with lock to prevent race conditions
        xp_gain = random.randint(15, 25)
        async with self._xp_lock:
            user_data = await self._get_user_data(guild_id, user_id)
            old_level = user_data['level']
            user_data['xp'] += xp_gain
            new_level = get_level_from_xp(user_data['xp'])
            user_data['level'] = new_level
            # Save username for leaderboard display even after user leaves
            user_data['display_name'] = message.author.display_name
            self._save_user_data(guild_id, user_id, user_data)
            # Update Redis cache immediately
            if self.bot.redis:
                await self.bot.redis.set_xp_data(guild_id, user_id, user_data)

        # Level up notification
        if new_level > old_level:
            level_up_channel_id = await self.bot.db.get_guild_setting(
                guild_id, 'level_up_channel_id'
            )
            channel = (
                message.guild.get_channel(int(level_up_channel_id))
                if level_up_channel_id
                else message.channel
            )
            if channel:
                loc = await self.bot.db.get_locale(guild_id)
                embed = discord.Embed(
                    title=t(loc, "levelup.title"),
                    description=t(loc, "levelup.desc", mention=message.author.mention, level=new_level),
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
        loc = await self.bot.db.get_locale(ctx.guild.id)
        user_data = await self._get_user_data(ctx.guild.id, member.id)

        total_xp = user_data['xp']
        level = user_data['level']

        # XP earned within the current level (closed-form, O(1))
        xp_so_far = total_xp - _cumulative_xp(level)
        xp_needed = get_xp_for_level(level)
        progress_bar = build_progress_bar(xp_so_far, xp_needed)

        embed = discord.Embed(
            title=t(loc, "rank.title", member=member.display_name),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name=t(loc, "rank.level"), value=f"**{level}**", inline=True)
        embed.add_field(name=t(loc, "rank.total_xp"), value=f"**{total_xp}** XP", inline=True)
        embed.add_field(
            name=t(loc, "rank.progress"),
            value=f"{progress_bar}\n`{xp_so_far} / {xp_needed} XP`",
            inline=False
        )
        embed.set_footer(
            text=t(loc, "rank.requested_by", user=ctx.author),
            icon_url=ctx.author.display_avatar.url
        )
        await reply(ctx, embed=embed)

    @commands.hybrid_command(name="setlevelrole", description="Assign a role reward for reaching a level.")
    @app_commands.describe(level="Level required.", role="Role to assign.")
    @commands.has_permissions(manage_roles=True)
    async def setlevelrole(self, ctx: commands.Context, level: int, role: discord.Role):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        if level < 1:
            return await reply(ctx, t(loc, "setlevelrole.invalid"), ephemeral=True)

        # Save to DB - method name fix: add_level_role -> set_level_role
        await self.bot.db.set_level_role(ctx.guild.id, level, role.id)

        embed = discord.Embed(
            title=t(loc, "setlevelrole.set_title"),
            description=t(loc, "setlevelrole.set_desc", level=level, role=role.mention),
            color=discord.Color.green()
        )
        await reply(ctx, embed=embed)

    @commands.hybrid_command(name="leaderboard", description="Shows the server XP leaderboard.")
    async def leaderboard(self, ctx: commands.Context):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        rows = await self.bot.db.get_leaderboard(ctx.guild.id, limit=100)
        if not rows:
            return await reply(ctx, t(loc, "leaderboard.empty"), ephemeral=True)

        medals = ["🥇", "🥈", "🥉"]
        per_page = 10
        total_pages = (len(rows) + per_page - 1) // per_page
        pages = []

        for page in range(total_pages):
            chunk = rows[page * per_page:(page + 1) * per_page]
            description = ""
            for offset, row in enumerate(chunk):
                rank = page * per_page + offset
                member = ctx.guild.get_member(row['user_id'])
                name = member.display_name if member else (row.get('display_name') or f"User {row['user_id']}")
                medal = medals[rank] if rank < 3 else f"`#{rank + 1}`"
                description += t(
                    loc, "leaderboard.row",
                    medal=medal, name=name, level=row['level'], xp=row['xp'],
                ) + "\n"
            embed = discord.Embed(
                title=t(loc, "leaderboard.title"),
                description=description,
                color=discord.Color.gold(),
            )
            embed.set_footer(
                text=t(loc, "leaderboard.footer", current=page + 1, total=total_pages, user=ctx.author),
                icon_url=ctx.author.display_avatar.url,
            )
            pages.append(embed)

        await send_paginated(ctx, pages)



    @tasks.loop(seconds=30)
    async def flush_xp_cache(self):
        """Flushes XP write buffer to PostgreSQL every 30 seconds."""
        try:
            if not self._dirty_guilds or not self.bot.db:
                return

            async with self._xp_lock:
                dirty = set(self._dirty_guilds)
                snapshot = {
                    guild_id: {
                        user_id: dict(data)
                        for user_id, data in self._write_buffer.get(guild_id, {}).items()
                    }
                    for guild_id in dirty
                    if guild_id in self._write_buffer
                }

            records = []
            for guild_id, users in snapshot.items():
                for user_id_str, data in users.items():
                    records.append({
                        'guild_id': guild_id,
                        'user_id': int(user_id_str),
                        'xp': data.get('xp', 0),
                        'level': data.get('level', 0),
                        'display_name': data.get('display_name', '')
                    })

            if records:
                await self.bot.db.bulk_upsert_xp(records)
                async with self._xp_lock:
                    for guild_id, users in snapshot.items():
                        guild_buffer = self._write_buffer.get(guild_id)
                        if not guild_buffer:
                            self._dirty_guilds.discard(guild_id)
                            continue

                        for user_id_str, flushed_data in users.items():
                            if guild_buffer.get(user_id_str) == flushed_data:
                                del guild_buffer[user_id_str]

                        if guild_buffer:
                            self._dirty_guilds.add(guild_id)
                        else:
                            del self._write_buffer[guild_id]
                            self._dirty_guilds.discard(guild_id)
                logger.info(f"XP flush: {len(records)} records to PostgreSQL")

        except Exception as e:
            logger.error(f"flush_xp_cache crashed: {e}", exc_info=True)

    @flush_xp_cache.before_loop
    async def before_flush_xp(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.flush_xp_cache.cancel()
        # Best-effort final flush on a graceful unload so buffered XP isn't lost
        # on a normal restart. Skipped if the pool is already closing/closed.
        pool = getattr(self.bot.db, "_pool", None) if self.bot.db else None
        if pool and not getattr(pool, "_closing", False) and not getattr(pool, "_closed", False):
            asyncio.create_task(self._emergency_flush())

    async def _emergency_flush(self):
        """Best-effort flush of buffered XP on unload."""
        try:
            await self.flush_xp_cache()
        except Exception:
            logger.warning("Emergency XP flush on unload failed.", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LevelsCog(bot))
