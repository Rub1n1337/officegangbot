# cogs/owner_cog.py
import discord
from discord.ext import commands, tasks
from discord import app_commands
from core.logger import logger
from typing import List, Literal
import asyncio
import os
from .utils import reply

# Helper to get cog names for autocomplete
async def cog_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    cogs_path = os.path.join(os.path.dirname(__file__))
    return [
        app_commands.Choice(name=f[:-3], value=f'cogs.{f[:-3]}')
        for f in os.listdir(cogs_path)
        if f.endswith('.py') and not f.startswith('__') and f != 'utils.py' and current.lower() in f.lower()
    ]

class OwnerCog(commands.Cog, name="👑 Owner"):
    """Special commands for the bot owner for maintenance and debugging."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Assume healthy at startup; alerts are edge-triggered on state change.
        self._db_ok = True
        self._redis_ok = True
        self.infra_watch.start()

    def cog_unload(self):
        self.infra_watch.cancel()

    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    async def _dm_owner(self, message: str) -> None:
        """Best-effort DM to the bot owner for infra alerts."""
        try:
            owner_id = int(os.getenv("BOT_OWNER_ID", "0")) or (self.bot.owner_id or 0)
            if not owner_id:
                return
            user = self.bot.get_user(owner_id) or await self.bot.fetch_user(owner_id)
            if user:
                await user.send(message)
        except Exception as e:
            logger.warning(f"Could not DM owner with infra alert: {e}")

    @tasks.loop(minutes=2)
    async def infra_watch(self):
        """Pings PostgreSQL and Redis; DMs the owner when a service goes
        down or comes back (edge-triggered, so no repeat spam)."""
        # --- PostgreSQL ---
        db_ok, db_err = False, "not connected"
        try:
            if self.bot.db and getattr(self.bot.db, "_pool", None):
                async with self.bot.db.pool.acquire() as conn:
                    await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=5)
                db_ok = True
        except Exception as e:
            db_err = str(e)
        if db_ok != self._db_ok:
            self._db_ok = db_ok
            if db_ok:
                await self._dm_owner("✅ **PostgreSQL recovered** — the database is reachable again.")
            else:
                await self._dm_owner(f"⚠️ **PostgreSQL is DOWN** — `{db_err[:200]}`")

        # --- Redis ---
        redis_ok, redis_err = False, "not connected"
        try:
            if self.bot.redis:
                await asyncio.wait_for(self.bot.redis.redis.ping(), timeout=5)
                redis_ok = True
        except Exception as e:
            redis_err = str(e)
        if redis_ok != self._redis_ok:
            self._redis_ok = redis_ok
            if redis_ok:
                await self._dm_owner("✅ **Redis recovered** — caching / RPC is back online.")
            else:
                await self._dm_owner(f"⚠️ **Redis is DOWN** — `{redis_err[:200]}`")

    @infra_watch.before_loop
    async def before_infra_watch(self):
        await self.bot.wait_until_ready()

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CheckFailure):
            await reply(ctx, "❌ This command is reserved for the bot owner.", ephemeral=True)
        else:
            logger.error(f"An error occurred in the Owner cog: {error}", exc_info=True)
            await reply(ctx, "🐞 An unexpected error occurred. Check logs for details.", ephemeral=True)

    @app_commands.autocomplete(cog=cog_autocomplete)
    @commands.hybrid_command(name="load", description="Loads a cog.")
    async def load(self, ctx: commands.Context, cog: str):
        try:
            await self.bot.load_extension(cog)
            await reply(ctx, f"✅ Successfully loaded cog: `{cog}`", ephemeral=True)
            logger.info(f"Cog '{cog}' loaded by {ctx.author}.")
        except Exception as e:
            await reply(ctx, f"❌ Failed to load cog `{cog}`.\n```py\n{e}\n```", ephemeral=True)

    @app_commands.autocomplete(cog=cog_autocomplete)
    @commands.hybrid_command(name="unload", description="Unloads a cog.")
    async def unload(self, ctx: commands.Context, cog: str):
        try:
            await self.bot.unload_extension(cog)
            await reply(ctx, f"✅ Successfully unloaded cog: `{cog}`", ephemeral=True)
            logger.info(f"Cog '{cog}' unloaded by {ctx.author}.")
        except Exception as e:
            await reply(ctx, f"❌ Failed to unload cog `{cog}`.\n```py\n{e}\n```", ephemeral=True)

    @app_commands.autocomplete(cog=cog_autocomplete)
    @commands.hybrid_command(name="reload", description="Reloads a cog or all cogs.")
    async def reload(self, ctx: commands.Context, cog: str):
        if cog.lower() == 'all':
            reloaded, failed = [], []
            for ext in list(self.bot.extensions.keys()):
                try:
                    await self.bot.reload_extension(ext)
                    reloaded.append(ext)
                except Exception:
                    failed.append(ext)

            msg = ""
            if reloaded:
                msg += f"✅ Reloaded: `{', '.join(reloaded)}`\n"
            if failed:
                msg += f"❌ Failed: `{', '.join(failed)}`"
            await reply(ctx, msg or "No cogs found to reload.", ephemeral=True)
            logger.info(f"All cogs reloaded by {ctx.author}.")
        else:
            try:
                await self.bot.reload_extension(cog)
                await reply(ctx, f"✅ Successfully reloaded cog: `{cog}`", ephemeral=True)
                logger.info(f"Cog '{cog}' reloaded by {ctx.author}.")
            except Exception as e:
                await reply(ctx, f"❌ Failed to reload cog `{cog}`.\n```py\n{e}\n```", ephemeral=True)


    @commands.hybrid_command(name="shutdown", description="Shuts down the bot.")
    async def shutdown(self, ctx: commands.Context):
        await reply(ctx, "💤 Shutting down...", ephemeral=True)
        logger.info(f"Shutdown command initiated by {ctx.author}.")
        await self.bot.close()

    @commands.hybrid_command(name="status", description="Changes the bot's status.")
    @app_commands.describe(status="The status to set", activity_type="The type of activity", name="The name of the activity")
    async def status(self, ctx: commands.Context, status: Literal["online", "idle", "dnd", "invisible"], activity_type: Literal["playing", "watching", "listening", "competing"], *, name: str):
        status_map = {"online": discord.Status.online, "idle": discord.Status.idle, "dnd": discord.Status.dnd, "invisible": discord.Status.invisible}
        activity_map = {"playing": discord.ActivityType.playing, "watching": discord.ActivityType.watching, "listening": discord.ActivityType.listening, "competing": discord.ActivityType.competing}

        await self.bot.change_presence(status=status_map[status], activity=discord.Activity(type=activity_map[activity_type], name=name))
        await reply(ctx, f"✅ Status updated to **{status}** and activity to **{activity_type} {name}**.", ephemeral=True)
        logger.info(f"Status changed by {ctx.author}: {status}, {activity_type} {name}")

async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCog(bot))
