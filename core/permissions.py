# core/permissions.py
from discord.ext import commands
from discord.ext.commands.errors import NoPrivateMessage

from core.logger import logger
from typing import Callable, Optional

# Discord caps a member timeout at 28 days.
MAX_TIMEOUT_MINUTES = 28 * 24 * 60  # 40320

# Reason codes returned by member_hierarchy_block (None means the action is allowed).
HIERARCHY_SELF = "self"
HIERARCHY_BOT_SELF = "bot_self"
HIERARCHY_OWNER = "owner"
HIERARCHY_TARGET_HIGHER = "higher"
HIERARCHY_BOT_NOT_HIGHER = "bot_higher"


def member_hierarchy_block(
    *,
    author_id: int,
    author_top_role_pos: int,
    target_id: int,
    target_top_role_pos: int,
    bot_id: int,
    bot_top_role_pos: int,
    owner_id: int,
) -> Optional[str]:
    """Whether a moderator (`author`) may act on `target` via a slash command.

    Returns one of the HIERARCHY_* reason codes if the action must be blocked, or
    None if allowed. Pure/position-based so it can be unit-tested without discord
    objects, and shared by the Moderation and Timed Events cogs so their rules
    can't drift apart. Policy: never self, the bot, or the owner; the author must
    be at least as high as the target (equal allowed; the owner is exempt from the
    author check); and the bot must be strictly higher than the target.
    """
    if target_id == author_id:
        return HIERARCHY_SELF
    if target_id == bot_id:
        return HIERARCHY_BOT_SELF
    if target_id == owner_id:
        return HIERARCHY_OWNER
    if author_id != owner_id and author_top_role_pos < target_top_role_pos:
        return HIERARCHY_TARGET_HIGHER
    if bot_top_role_pos <= target_top_role_pos:
        return HIERARCHY_BOT_NOT_HIGHER
    return None


def bot_can_act_on(
    *,
    target_id: int,
    target_top_role_pos: int,
    bot_id: int,
    bot_top_role_pos: int,
    owner_id: int,
) -> bool:
    """Whether the bot may moderate a target member.

    Never the bot itself or the server owner, and only members strictly below
    the bot's top role. Pure (position-based) so it can be unit-tested without
    discord objects.
    """
    if target_id == bot_id or target_id == owner_id:
        return False
    return bot_top_role_pos > target_top_role_pos


def clamp_mute_minutes(raw, default: int = 10) -> int:
    """Clamp a requested mute duration to Discord's [1 min, 28 days] window.

    Non-numeric / missing values fall back to `default`; negatives clamp up to 1.
    """
    try:
        minutes = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        minutes = default
    return max(1, min(minutes, MAX_TIMEOUT_MINUTES))

def has_permission(permission_level: str) -> Callable:
    """
    Custom check decorator that verifies if the user has the required permission level.
    Reads mod roles from PostgreSQL (mod_roles). Logs missing roles and raises NoPrivateMessage in DMs.
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

        # Server administrators always pass. Without this, no one but the bot
        # owner could bootstrap permissions, since assigning the first mod_role
        # via /config role is itself gated by has_permission("config").
        if ctx.author.guild_permissions.administrator:
            return True

        # 1. Try Postgres (mod_roles table)
        if hasattr(ctx.bot, 'db') and ctx.bot.db:
            mod_roles = await ctx.bot.db.get_mod_roles(ctx.guild.id)
            allowed_role_ids = mod_roles.get(permission_level, [])
            if allowed_role_ids:
                has_role = any(role.id in allowed_role_ids for role in ctx.author.roles)
                if has_role:
                    return True


        
        logger.info(f"User {ctx.author} lacks required permissions for '{permission_level}' in guild {ctx.guild.id}.")
        return False

    return commands.check(predicate)
