# core/limits.py
"""Per-guild resource caps by plan.

Free servers keep the original, already-generous ceilings; premium raises them.
This is purely additive — no free limit was lowered — so nothing a current
server has configured can break. Mirrored on the dashboard in
``dashboard/src/config/limits.ts``; keep the two in sync.
"""

FREE_LIMITS = {
    "level_rewards": 100,
    "scheduled_messages": 50,
    "automod_rules": 25,
    "banned_words": 500,
    "role_menus": 25,
    "reaction_roles": 100,
    "level_multipliers": 50,
    "custom_commands": 0,
}

PREMIUM_LIMITS = {
    "level_rewards": 300,
    "scheduled_messages": 200,
    "automod_rules": 100,
    "banned_words": 2000,
    "role_menus": 100,
    "reaction_roles": 400,
    "level_multipliers": 150,
    "custom_commands": 15,
}


def limit_for(resource: str, premium: bool) -> int:
    """The cap for ``resource`` on the guild's plan."""
    return (PREMIUM_LIMITS if premium else FREE_LIMITS)[resource]


def limit_error(resource: str, name: str, premium: bool) -> str:
    """A user-facing 'too many' message. On the free plan it nudges toward
    premium (and states the higher cap); on premium it's just the ceiling."""
    cap = limit_for(resource, premium)
    if premium:
        return f"Too many {name} (max {cap})."
    return (
        f"Too many {name} — the free plan allows up to {cap}. "
        f"Premium raises this to {PREMIUM_LIMITS[resource]}."
    )
