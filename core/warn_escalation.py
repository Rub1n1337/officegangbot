# core/warn_escalation.py
"""Manual-warning escalation: once a member's active warning count crosses the
configured thresholds, auto-mute / kick / ban them. Shared by the /warn command
and the dashboard warn action so both behave identically."""
import datetime
from typing import Optional

import discord

from core.logger import logger

MUTE_MINUTES = 10  # timeout duration when escalating to a mute (matches AutoMod strikes)


async def maybe_escalate_warning(db, guild: discord.Guild, member: Optional[discord.Member]) -> Optional[str]:
    """If warning escalation is enabled and the member's active warning count has
    reached a threshold, apply the highest matching action. Returns the action
    taken ("banned"/"kicked"/"muted 10m") for the caller to report, or None."""
    if member is None or guild is None:
        return None
    cfg = await db.get_warn_escalation(guild.id)
    if not cfg["enabled"]:
        return None

    count = await db.count_active_warnings(guild.id, member.id, cfg["expiry_hours"])
    ban_at, kick_at, mute_at = cfg["ban_at"], cfg["kick_at"], cfg["mute_at"]
    if ban_at and count >= ban_at:
        action = "ban"
    elif kick_at and count >= kick_at:
        action = "kick"
    elif mute_at and count >= mute_at:
        action = "mute"
    else:
        return None

    reason = f"Warning escalation: {count} warnings"
    try:
        if action == "ban":
            await guild.ban(member, reason=reason)
            return "banned"
        if action == "kick":
            await member.kick(reason=reason)
            return "kicked"
        await member.timeout(datetime.timedelta(minutes=MUTE_MINUTES), reason=reason)
        return f"muted {MUTE_MINUTES}m"
    except (discord.Forbidden, discord.HTTPException) as e:
        logger.warning(f"Warn escalation ({action}) failed for {member} in {guild.name}: {e}")
        return None
