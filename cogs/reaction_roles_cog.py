# cogs/reaction_roles_cog.py

import discord
from discord.ext import commands
from core.logger import logger

# Which feature flag gates each reaction-role source.
SOURCE_FEATURE = {
    "reaction-role": "reaction-role",
    "rules": "rules",
}


def _emoji_match(payload_emoji, stored: str) -> bool:
    """Matches a reaction payload emoji against a stored emoji string.
    Handles unicode emoji and custom emoji (by full string, name, or id)."""
    stored = str(stored)
    if getattr(payload_emoji, "id", None):
        return stored in (str(payload_emoji), str(payload_emoji.id), str(payload_emoji.name))
    return str(payload_emoji) == stored


class ReactionRolesCog(commands.Cog, name="Reaction Roles"):
    """Grants/removes roles based on reactions, using the reaction_roles table.
    Supports many mappings per guild on arbitrary messages, plus the one tied
    to the rules message."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _handle_reaction(self, payload: discord.RawReactionActionEvent, *, add_role: bool) -> None:
        if payload.user_id == self.bot.user.id or not payload.guild_id or not self.bot.db:
            return

        mappings = await self.bot.db.get_message_reaction_roles(payload.guild_id, payload.message_id)
        if not mappings:
            return

        match = next((m for m in mappings if _emoji_match(payload.emoji, m["emoji"])), None)
        if not match:
            return

        # Gate by the feature that owns this mapping.
        enabled_features = await self.bot.db.get_enabled_features(payload.guild_id)
        if SOURCE_FEATURE.get(match["source"], "reaction-role") not in enabled_features:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        role = guild.get_role(int(match["role_id"]))
        if not role:
            logger.warning(f"Reaction role {match['role_id']} not found in guild {guild.name}.")
            return

        try:
            member = await guild.fetch_member(payload.user_id)
        except discord.NotFound:
            return
        if not member:
            return

        try:
            if add_role and role not in member.roles:
                await member.add_roles(role, reason="Reaction role granted.")
                logger.info(f"Assigned role '{role.name}' to {member.name} in {guild.name}.")
            elif not add_role and role in member.roles:
                await member.remove_roles(role, reason="Reaction role removed.")
                logger.info(f"Removed role '{role.name}' from {member.name} in {guild.name}.")
        except discord.Forbidden:
            logger.error(f"Cannot manage reaction role in {guild.name}: missing 'Manage Roles' or role too high.")
        except Exception as e:
            logger.error(f"Unexpected error in reaction role management: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload, add_role=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload, add_role=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRolesCog(bot))
