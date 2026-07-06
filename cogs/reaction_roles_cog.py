# cogs/reaction_roles_cog.py

import discord
from discord.ext import commands
from core.logger import logger

# Which feature flag gates each reaction-role source. The standalone
# 'reaction-role' source (and the former rules-message reaction, migrated into
# it) now lives under the Role Menus card, so both gate on 'reaction-menus'.
SOURCE_FEATURE = {
    "reaction-role": "reaction-menus",
    "menu": "reaction-menus",
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
        if SOURCE_FEATURE.get(match["source"], "reaction-menus") not in enabled_features:
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
            return
        except Exception as e:
            logger.error(f"Unexpected error in reaction role management: {e}", exc_info=True)
            return

        # Exclusive (single-select) menus: picking one role clears the member's
        # other roles from the same menu, and their reactions on the other emojis.
        if add_role and match.get("exclusive"):
            await self._enforce_exclusive(guild, member, payload, mappings, match)

    async def _enforce_exclusive(self, guild, member, payload, mappings, match) -> None:
        """Removes the member's other roles from this exclusive menu and clears
        their reactions on the menu's other emojis so it reflects one choice."""
        keep_role_id = int(match["role_id"])
        other_ids = {int(m["role_id"]) for m in mappings} - {keep_role_id}
        to_remove = [r for rid in other_ids if (r := guild.get_role(rid)) and r in member.roles]
        if to_remove:
            try:
                await member.remove_roles(*to_remove, reason="Exclusive role menu (single select).")
            except (discord.Forbidden, discord.HTTPException):
                logger.warning(f"Exclusive menu: couldn't remove other roles from {member} in {guild.name}.")

        channel = guild.get_channel(payload.channel_id)
        if channel is None:
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except (discord.HTTPException, discord.Forbidden):
            return
        for reaction in message.reactions:
            if _emoji_match(reaction.emoji, match["emoji"]):
                continue  # keep the just-selected reaction
            if any(_emoji_match(reaction.emoji, m["emoji"]) for m in mappings):
                try:
                    await reaction.remove(member)
                except (discord.HTTPException, discord.Forbidden):
                    pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload, add_role=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload, add_role=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRolesCog(bot))
