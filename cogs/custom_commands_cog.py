"""Premium custom commands, surfaced via a single ``/tag <name>`` command with
autocomplete.

Deliberately one isolated slash command rather than dynamically-registered
per-name commands: a bug here can only affect ``/tag``, never the bot's other
commands or component interactions. Responses support the same safe
``{placeholder}`` tokens as welcome messages (see core.safe_format).
"""
import discord
from discord import app_commands
from discord.ext import commands

from core.logger import logger
from core.safe_format import render_template, welcome_values


class CustomCommandsCog(commands.Cog, name="🏷️ Custom Commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _commands_for(self, guild_id):
        """The guild's custom commands, but only when it's premium (so a lapsed
        subscription silently disables them without deleting the rows)."""
        if not self.bot.db or not guild_id:
            return []
        if not await self.bot.db.is_premium(guild_id):
            return []
        try:
            return await self.bot.db.get_custom_commands(guild_id)
        except Exception:
            logger.exception(f"Failed to load custom commands for guild {guild_id}")
            return []

    @app_commands.command(name="tag", description="Run one of this server's custom commands.")
    @app_commands.describe(name="Which custom command to run")
    @app_commands.guild_only()
    async def tag(self, interaction: discord.Interaction, name: str):
        cmds = await self._commands_for(interaction.guild_id)
        wanted = name.strip().lower()
        match = next((c for c in cmds if c["name"] == wanted), None)
        if not match:
            await interaction.response.send_message(
                "That custom command doesn’t exist on this server.", ephemeral=True
            )
            return
        text = render_template(match["response"], welcome_values(interaction.user, interaction.guild))
        await interaction.response.send_message(text[:2000])

    @tag.autocomplete("name")
    async def tag_autocomplete(self, interaction: discord.Interaction, current: str):
        cmds = await self._commands_for(interaction.guild_id)
        cur = current.strip().lower()
        return [
            app_commands.Choice(name=c["name"], value=c["name"])
            for c in cmds
            if cur in c["name"]
        ][:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(CustomCommandsCog(bot))
