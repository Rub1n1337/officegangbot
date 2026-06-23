# core/permissions.py
from discord.ext import commands
from discord.ext.commands.errors import NoPrivateMessage
from core.settings_manager import SettingsManager
from core.logger import logger
from typing import Callable

def has_permission(permission_level: str) -> Callable:
    """
    Custom check decorator that verifies if the user has the required permission level.
    Uses the bot's singleton SettingsManager. Logs missing roles and raises NoPrivateMessage in DMs.
    Args:
        permission_level (str): Permission level to check (e.g., 'config').
    Returns:
        Callable: A check function usable with discord.py commands.
    """
    async def predicate(ctx: commands.Context) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True  # Bot owner bypasses all checks

        if not ctx.guild:
            logger.warning(f"Permission check for '{permission_level}' failed: command used in DM by {ctx.author}.")
            raise NoPrivateMessage("This command cannot be used in private messages.")

        # 1. Try Postgres (mod_roles table)
        if hasattr(ctx.bot, 'db') and ctx.bot.db:
            mod_roles = await ctx.bot.db.get_mod_roles(ctx.guild.id)
            allowed_role_ids = mod_roles.get(permission_level, [])
            if allowed_role_ids:
                has_role = any(role.id in allowed_role_ids for role in ctx.author.roles)
                if has_role:
                    return True

        # 2. Fallback to Legacy JSON (single role per permission)
        settings_manager = getattr(ctx.bot, 'settings_manager', None)
        if settings_manager:
            required_role_id = settings_manager.get_setting(ctx.guild.id, f'{permission_level}_role_id')
            if required_role_id:
                has_role = any(role.id == required_role_id for role in ctx.author.roles)
                if has_role:
                    return True
        
        logger.info(f"User {ctx.author} lacks required permissions for '{permission_level}' in guild {ctx.guild.id}.")
        return False

    return commands.check(predicate)
