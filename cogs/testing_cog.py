# cogs/testing_cog.py
import discord
from discord.ext import commands
from core.logger import logger
from .utils import reply
import asyncio
import inspect

class TestingCog(commands.Cog, name="🔬 Testing"):
    """Provides commands to test the bot's stability and functionality."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    _test_lock = asyncio.Lock()
    _skip_commands = {'help', 'shutdown', 'sync', 'reload', 'unload', 'load', 'testall', 'setup'}

    @commands.command(name="testall", description="Run automated tests on all commands.")
    async def test_all_commands(self, ctx: commands.Context):
        """Iterates through all commands and attempts to invoke them as prefix commands to check for errors. Skips destructive/admin commands. Prevents concurrent test runs."""
        if self._test_lock.locked():
            await reply(ctx, "A test run is already in progress. Please wait for it to finish.", ephemeral=True)
            return
        async with self._test_lock:
            await reply(ctx, "🔬 Starting comprehensive command test... This will test the prefix-command path for all applicable commands. Results will be logged and summarized. (Ephemeral is ignored for prefix commands)", ephemeral=True)

            results = {"success": [], "failed": [], "skipped": []}
            all_commands = list(self.bot.commands)

            for cmd in all_commands:
                if cmd.cog_name == self.qualified_name or cmd.name in self._skip_commands:
                    results["skipped"].append(f"`{cmd.qualified_name}` (Skipped by design)")
                    continue

                # Check for required parameters, excluding 'self' and 'ctx'
                required_params = [p for p in cmd.params.values() if p.name not in ('self', 'ctx') and p.default is inspect.Parameter.empty]

                if required_params:
                    param_names = ', '.join([p.name for p in required_params])
                    results["skipped"].append(f"`{cmd.qualified_name}` (Requires arguments: {param_names})")
                    continue

                logger.info(f"Testing command: {cmd.qualified_name}")
                try:
                    await ctx.invoke(cmd)
                    results["success"].append(f"`{cmd.qualified_name}`")
                    await asyncio.sleep(1)
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc(limit=2)
                    error_info = f"{type(e).__name__}: {e}\n{tb}"
                    results["failed"].append(f"`{cmd.qualified_name}` - {error_info}")
                    logger.error(f"Test failed for command '{cmd.qualified_name}': {error_info}", exc_info=True)

            summary_embed = discord.Embed(title="Command Test Summary (Prefix Path)", color=discord.Color.gold())
            summary_embed.description = "This test invokes commands that do not require arguments to verify their basic functionality and response handling."
            if results["success"]:
                summary_embed.add_field(name="✅ Success", value="\n".join(results["success"])[:1024] or "None", inline=False)
            if results["failed"]:
                summary_embed.add_field(name="❌ Failed", value="\n".join(results["failed"])[:1024] or "None", inline=False)
            if results["skipped"]:
                summary_embed.add_field(name="⏭️ Skipped", value="\n".join(results["skipped"])[:1024] or "None", inline=False)

            await reply(ctx, embed=summary_embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TestingCog(bot))
