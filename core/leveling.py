"""Pure helpers for the leveling system — XP multipliers and prestige checks.
Kept discord-free so they can be unit-tested directly."""
from typing import List, Optional

# Guard-rails so a bad multiplier can't award absurd XP or zero everything out.
MIN_MULTIPLIER = 0.1
MAX_MULTIPLIER = 10.0


def sanitize_multiplier(value, default: float = 1.0) -> float:
    """Coerces a value to a multiplier in [MIN_MULTIPLIER, MAX_MULTIPLIER],
    rounded to 2 decimals, falling back to `default` when unparseable."""
    try:
        m = float(value)
    except (TypeError, ValueError):
        m = default
    m = max(MIN_MULTIPLIER, min(MAX_MULTIPLIER, m))
    return round(m, 2)


def effective_multiplier(base: float, member_role_multipliers: Optional[List[float]] = None) -> float:
    """Combines the guild's global multiplier with the best of the member's role
    multipliers (roles the member actually holds). Result is clamped."""
    best_role = max(member_role_multipliers) if member_role_multipliers else 1.0
    combined = sanitize_multiplier(base) * best_role
    return max(MIN_MULTIPLIER, min(MAX_MULTIPLIER, round(combined, 2)))


def apply_multiplier(xp: int, multiplier: float) -> int:
    """Applies a multiplier to an XP amount, never dropping below 1 for a
    positive base so an active member always earns something."""
    if xp <= 0:
        return 0
    return max(1, int(round(xp * multiplier)))


def can_prestige(level: int, threshold: int) -> bool:
    """Whether a member at `level` may prestige (threshold disabled when <= 0)."""
    return threshold > 0 and level >= threshold
