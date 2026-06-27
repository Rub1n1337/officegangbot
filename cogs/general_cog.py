# cogs/general_cog.py
from discord.ext import commands
from core.i18n import t
from .utils import reply

class GeneralCog(commands.Cog, name="💬 General"):
    """General purpose commands for everyone."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _locale(self, ctx: commands.Context) -> str:
        return await self.bot.db.get_locale(ctx.guild.id) if ctx.guild else "en"

    @commands.hybrid_command(name="ping", description="Test command to check bot response time.")
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        loc = await self._locale(ctx)
        await reply(ctx, t(loc, "ping.reply", latency=latency), ephemeral=True)

    @commands.hybrid_command(name="hello", description="Say hello to the bot!")
    async def hello(self, ctx: commands.Context):
        loc = await self._locale(ctx)
        await reply(ctx, t(loc, "hello.reply", mention=ctx.author.mention), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCog(bot))
