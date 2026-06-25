# cogs/general_cog.py
from discord.ext import commands
from .utils import reply

class GeneralCog(commands.Cog, name="💬 General"):
    """General purpose commands for everyone."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Test command to check bot response time.")
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        await reply(ctx, f"Pong! 🏓 Response time: {latency}ms", ephemeral=True)

    @commands.hybrid_command(name="hello", description="Say hello to the bot!")
    async def hello(self, ctx: commands.Context):
        await reply(ctx, f"Hello, {ctx.author.mention}! 👋", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCog(bot))
