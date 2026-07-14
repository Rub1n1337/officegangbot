# cogs/filter_cog.py
"""Banned-words list management. Enforcement lives in the AutoMod cog (the
standalone word filter was merged into AutoMod so it shares the exemptions,
dry-run mode and strike escalation) — these commands just edit the shared list,
which is also editable from the AutoMod page in the dashboard."""
import discord
from discord.ext import commands
from discord import app_commands
from core.permissions import has_permission
from core.i18n import t

from .utils import reply

# A default list of profanities. This can be expanded.
DEFAULT_BANNED_WORDS = [
    "fuck", "shit", "bitch", "cunt", "asshole", "dick", "pussy",
    "bastard", "damn", "hell", "nigger", "faggot"
]


class FilterCog(commands.Cog, name="🚫 Filter"):
    """Manages the banned words list (enforced by AutoMod)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _filter_word_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Suggests words already in this guild's filter for /filter remove."""
        if interaction.guild_id is None:
            return []
        words = await self.bot.db.get_guild_setting(interaction.guild_id, 'filter_words') or []
        current = current.lower()
        return [
            app_commands.Choice(name=word, value=word)
            for word in sorted(words)
            if current in word
        ][:25]

    @commands.hybrid_group(name="filter")
    @has_permission("config")
    async def filter(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            help_cog = self.bot.get_cog("❓ Help")
            if help_cog:
                await help_cog.send_command_help(ctx, ctx.command)
            else:
                await reply(ctx, "The help command is currently unavailable.", ephemeral=True)

    @filter.command(name="toggle", description="(Deprecated) The word filter now runs as part of AutoMod.")
    @has_permission("config")
    async def filter_toggle(self, ctx: commands.Context):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        await reply(ctx, t(loc, "filter.toggle_deprecated"), ephemeral=True)

    @filter.command(name="add", description="Adds a word to the banned-words list (enforced by AutoMod).")
    @app_commands.describe(word="The word to add to the filter.")
    @has_permission("config")
    async def filter_add(self, ctx: commands.Context, word: str):
        word = word.lower().strip()
        loc = await self.bot.db.get_locale(ctx.guild.id)

        # A 1-char "word" would flag half the dictionary; an essay isn't a word.
        if len(word) < 2 or len(word) > 100:
            return await reply(ctx, t(loc, "filter.bad_length"), ephemeral=True)

        current_words = await self.bot.db.get_guild_setting(ctx.guild.id, 'filter_words') or []
        if word in current_words:
            await reply(ctx, t(loc, "filter.add_exists", word=word))
            return
        current_words.append(word)
        # set_filter_words also invalidates the AutoMod config cache, which now
        # carries the compiled banned-words pattern.
        await self.bot.db.set_filter_words(ctx.guild.id, current_words)
        await reply(ctx, t(loc, "filter.added", word=word))

    @filter.command(name="add_defaults", description="Adds the default list of profanities to the filter.")
    @has_permission("config")
    async def filter_add_defaults(self, ctx: commands.Context):
        """Adds a predefined list of common profanities to the server's filter."""
        loc = await self.bot.db.get_locale(ctx.guild.id)
        current_words = await self.bot.db.get_guild_setting(ctx.guild.id, 'filter_words') or []

        new_words = [word for word in DEFAULT_BANNED_WORDS if word not in current_words]
        added_count = len(new_words)

        if added_count == 0:
            await reply(ctx, t(loc, "filter.defaults_all"))
            return

        current_words.extend(new_words)
        await self.bot.db.set_filter_words(ctx.guild.id, current_words)
        await reply(ctx, t(loc, "filter.defaults_added", count=added_count))

    @filter.command(name="remove", description="Removes a word from the banned-words list.")
    @app_commands.describe(word="The word to remove from the filter.")
    @app_commands.autocomplete(word=_filter_word_autocomplete)
    @has_permission("config")
    async def filter_remove(self, ctx: commands.Context, word: str):
        word = word.lower()
        loc = await self.bot.db.get_locale(ctx.guild.id)

        current_words = await self.bot.db.get_guild_setting(ctx.guild.id, 'filter_words') or []

        if word not in current_words:
            await reply(ctx, t(loc, "filter.not_found", word=word))
            return

        current_words.remove(word)
        await self.bot.db.set_filter_words(ctx.guild.id, current_words)
        await reply(ctx, t(loc, "filter.removed", word=word))

    @filter.command(name="list", description="Lists all words in the filter.")
    @has_permission("config")
    async def filter_list(self, ctx: commands.Context):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        banned_words = await self.bot.db.get_guild_setting(ctx.guild.id, 'filter_words') or []

        if not banned_words:
            await reply(ctx, t(loc, "filter.list_empty"))
            return
        description = ", ".join(f"`{word}`" for word in sorted(banned_words))
        if len(description) > 4000:
            description = description[:4000] + "..."
        embed = discord.Embed(title=t(loc, "filter.list_title"), description=description, color=discord.Color.red())
        await reply(ctx, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(FilterCog(bot))
