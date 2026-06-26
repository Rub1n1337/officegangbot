# cogs/locale_cog.py
from discord.ext import commands
from discord import app_commands

from core.permissions import has_permission
from core.i18n import t
from .utils import reply


class LocaleCog(commands.Cog, name="🌐 Language"):
    """Per-guild language selection for the bot's responses."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="language", description="Set the bot's language for this server.")
    @app_commands.describe(locale="The language to use.")
    @app_commands.choices(
        locale=[
            app_commands.Choice(name="English", value="en"),
            app_commands.Choice(name="Русский", value="ru"),
        ]
    )
    @has_permission("config")
    async def language(self, ctx: commands.Context, locale: str):
        await self.bot.db.set_locale(ctx.guild.id, locale)
        # Confirm in the language just chosen.
        await reply(ctx, t(locale, "language.set"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LocaleCog(bot))
