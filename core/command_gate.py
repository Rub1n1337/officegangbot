# core/command_gate.py
"""Pure per-command permission check. No bot/DB, so it's unit-tested; the bot's
global slash + prefix checks call it (fail-open, admins bypass)."""
from typing import Any, Dict, Iterable, Optional


def command_allowed(
    override: Optional[Dict[str, Any]], *, channel_id: Optional[int], role_ids: Iterable[int]
) -> bool:
    """Given a guild's override for one command (or None for the default), decide
    whether it may run in this channel for a member with these roles.

    Rules (matching Dyno): disabled -> no. An 'allowed' list means only those
    are permitted; an 'ignored' list blocks those. Channels and roles are
    checked independently; both must pass.
    """
    if override is None:
        return True
    if not override.get("enabled", True):
        return False

    allowed_ch = override.get("allowed_channels") or []
    ignored_ch = override.get("ignored_channels") or []
    if channel_id is not None:
        if ignored_ch and channel_id in ignored_ch:
            return False
        if allowed_ch and channel_id not in allowed_ch:
            return False

    roles = set(role_ids)
    allowed_r = override.get("allowed_roles") or []
    ignored_r = override.get("ignored_roles") or []
    if ignored_r and roles & set(ignored_r):
        return False
    if allowed_r and not (roles & set(allowed_r)):
        return False
    return True
