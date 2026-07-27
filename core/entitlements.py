# core/entitlements.py
"""Maps Discord monetization entitlements to per-guild premium state.

Premium is a per-guild subscription tied to the SKU in ``DISCORD_PREMIUM_SKU_ID``.
This module is kept pure (no bot, no DB) so the mapping is unit-testable; the
I/O (listening for entitlement events, reconciling, writing guild_premium) lives
in ``cogs/premium_cog.py``.
"""
import os
from datetime import datetime, timezone
from typing import Optional, Tuple


def premium_sku_id() -> Optional[int]:
    """The configured premium SKU id, or None when monetization isn't set up
    (so the whole feature no-ops safely until the SKU exists)."""
    raw = os.getenv("DISCORD_PREMIUM_SKU_ID", "").strip()
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


def entitlement_guild_state(
    entitlement, sku_id: Optional[int], now: Optional[datetime] = None
) -> Optional[Tuple[int, bool, Optional[datetime]]]:
    """For our premium guild-subscription SKU, returns ``(guild_id, active,
    ends_at)``; None for a different SKU, a user (non-guild) subscription, or an
    unconfigured SKU. ``active`` is False once the entitlement is deleted
    (refund/chargeback) or past its ``ends_at``."""
    if sku_id is None or getattr(entitlement, "sku_id", None) != sku_id:
        return None
    guild_id = getattr(entitlement, "guild_id", None)
    if not guild_id:
        return None  # a user subscription, not a per-server one
    now = now or datetime.now(timezone.utc)
    deleted = bool(getattr(entitlement, "deleted", False))
    ends_at = getattr(entitlement, "ends_at", None)
    active = (not deleted) and (ends_at is None or ends_at > now)
    return (int(guild_id), active, ends_at)
