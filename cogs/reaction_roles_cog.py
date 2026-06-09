# cogs/reaction_roles_cog.py

import discord
from discord.ext import commands
from core.logger import logger
from core.settings_manager import SettingsManager

class ReactionRolesCog(commands.Cog, name="Reaction Roles"):
    """Handles granting and removing roles based on message reactions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager: SettingsManager = bot.settings_manager

    async def _handle_reaction(self, payload: discord.RawReactionActionEvent, *, add_role: bool) -> None:
        """A single helper function to handle both adding and removing roles. Emoji comparison is robust for unicode/custom."""
        if payload.user_id == self.bot.user.id or not payload.guild_id:
            return

        guild_settings = self.settings_manager.get_guild_settings(payload.guild_id)
        rules_message_id = guild_settings.get('rules_message_id')
        reaction_emoji = guild_settings.get('reaction_emoji')
        role_id = guild_settings.get('reaction_role_id')

        def emoji_match(payload_emoji, config_emoji):
            # Match unicode or custom emoji by id or string
            if hasattr(payload_emoji, 'id') and payload_emoji.id:
                return str(payload_emoji.id) == str(config_emoji) or str(payload_emoji) == str(config_emoji)
            return str(payload_emoji) == str(config_emoji)

        if not (rules_message_id and reaction_emoji and role_id): return
        if payload.message_id != rules_message_id or not emoji_match(payload.emoji, reaction_emoji): return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return

        role_to_manage = guild.get_role(role_id)
        if not role_to_manage:
            logger.warning(f"Reaction role ID {role_id} not found in guild {guild.name}.")
            return

        try:
            member = await guild.fetch_member(payload.user_id)
        except discord.NotFound:
            return # Member left the server

        if not member: return

        try:
            if add_role:
                if role_to_manage not in member.roles:
                    await member.add_roles(role_to_manage, reason="Accepted server rules via reaction.")
                    logger.info(f"Assigned role '{role_to_manage.name}' to {member.name} in {guild.name}.")
            else: # Remove role
                if role_to_manage in member.roles:
                    await member.remove_roles(role_to_manage, reason="Un-accepted server rules via reaction.")
                    logger.info(f"Removed role '{role_to_manage.name}' from {member.name} in {guild.name}.")
        except discord.Forbidden:
            logger.error(f"Failed to manage reaction role in {guild.name}. Missing 'Manage Roles' permission or role is above mine.")
        except Exception as e:
            logger.error(f"An unexpected error in reaction role management: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Called when a user ADDS a reaction. Grants the role."""
        await self._handle_reaction(payload, add_role=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Called when a user REMOVES a reaction. Removes the role."""
        await self._handle_reaction(payload, add_role=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRolesCog(bot))
