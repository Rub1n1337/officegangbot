# cogs/reaction_roles_cog.py

import discord
from discord.ext import commands
from core.logger import logger


class ReactionRolesCog(commands.Cog, name="Reaction Roles"):
    """Handles granting and removing roles based on message reactions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _handle_reaction(self, payload: discord.RawReactionActionEvent, *, add_role: bool) -> None:
        """A single helper function to handle both adding and removing roles. Emoji comparison is robust for unicode/custom."""
        if payload.user_id == self.bot.user.id or not payload.guild_id:
            return

        # Check if reaction-role feature is enabled
        enabled_features = await self.bot.db.get_enabled_features(payload.guild_id)
        if "reaction-role" not in enabled_features:
            return

        # Fetch settings from Postgres
        rules_message_id = await self.bot.db.get_guild_setting(payload.guild_id, 'rules_message_id')
        reaction_emoji = await self.bot.db.get_guild_setting(payload.guild_id, 'reaction_emoji')
        role_id = await self.bot.db.get_guild_setting(payload.guild_id, 'reaction_role_id')
        
        # Ensure rules_message_id and role_id are integers
        if rules_message_id:
            try:
                rules_message_id = int(rules_message_id)
            except (ValueError, TypeError):
                rules_message_id = None
                
        if role_id:
            try:
                role_id = int(role_id)
            except (ValueError, TypeError):
                role_id = None

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
