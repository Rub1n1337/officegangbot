"""Dashboard moderation actions, extracted from the RPC handler so the
warn/mute/kick/ban dispatch can be unit-tested without the bot/Redis/FastAPI
plumbing. `guild`, `db` and `log_action` are injected."""
import datetime

import discord

from core.permissions import bot_can_act_on, clamp_mute_minutes
from core.warn_escalation import maybe_escalate_warning

HIERARCHY_ERROR = "I can't moderate this member — they're higher than me in the role hierarchy."
VALID_ACTIONS = {"warn", "mute", "unmute", "kick", "ban"}


async def perform_moderation(
    *,
    db,
    guild,
    bot_user_id: int,
    user_id: int,
    act,
    reason,
    mod_name,
    mod_id: int,
    duration_minutes=None,
    log_action=None,
) -> dict:
    """Apply a moderation action to a member and return a result dict.

    Enforces the bot's role hierarchy (never the owner or the bot itself),
    clamps the mute duration, and mirrors each action into the punishment log
    via `log_action(guild, title, target_id, mod_name, reason, **extra)`.
    Returns ``{"success": True, "message": ...}`` or ``{"error": ...}``.
    """
    if act not in VALID_ACTIONS:
        return {"error": f"Unknown action: {act}"}
    reason = (str(reason or "").strip() or "No reason provided")[:500]
    mod_name = (str(mod_name or "Dashboard").strip() or "Dashboard")[:100]
    member = guild.get_member(user_id)
    tag = f"{reason} (via dashboard: {mod_name})"

    def _can(m):
        if m is None:
            return True  # banning a user not in the server
        return bot_can_act_on(
            target_id=m.id,
            target_top_role_pos=m.top_role.position,
            bot_id=bot_user_id,
            bot_top_role_pos=guild.me.top_role.position,
            owner_id=guild.owner_id,
        )

    async def _log(title, **extra):
        if log_action is not None:
            await log_action(guild, title, user_id, mod_name, reason, **extra)

    try:
        if act == "warn":
            if member is None:
                return {"error": "Member is not in the server"}
            wid = await db.add_warning(guild.id, user_id, reason, mod_id, mod_name)
            await _log("Member Warned")
            escalated = await maybe_escalate_warning(db, guild, member)
            msg = f"Warning added — escalated ({escalated})" if escalated else "Warning added"
            return {"success": True, "message": msg, "warningId": wid, "escalated": escalated}

        if act == "unmute":
            if member is None:
                return {"error": "Member is not in the server"}
            await member.timeout(None, reason=tag)
            await _log("Timeout Removed")
            return {"success": True, "message": "Timeout removed"}

        if act == "mute":
            if member is None:
                return {"error": "Member is not in the server"}
            if not _can(member):
                return {"error": HIERARCHY_ERROR}
            minutes = clamp_mute_minutes(duration_minutes)
            await member.timeout(datetime.timedelta(minutes=minutes), reason=tag)
            await _log("Member Muted", duration=f"{minutes} min")
            return {"success": True, "message": f"Muted for {minutes} min"}

        if act == "kick":
            if member is None:
                return {"error": "Member is not in the server"}
            if not _can(member):
                return {"error": HIERARCHY_ERROR}
            await member.kick(reason=tag)
            await _log("Member Kicked")
            return {"success": True, "message": "Member kicked"}

        if act == "ban":
            if member is not None and not _can(member):
                return {"error": HIERARCHY_ERROR}
            await guild.ban(member or discord.Object(id=user_id), reason=tag)
            await _log("Member Banned")
            return {"success": True, "message": "Member banned"}

        return {"error": "Unknown action"}
    except discord.Forbidden:
        return {"error": "I don't have permission to do that."}
    except discord.HTTPException as e:
        return {"error": f"Discord error: {getattr(e, 'text', str(e))}"}
