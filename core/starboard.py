# core/starboard.py
"""Pure starboard decision logic. No bot/DB, so it's unit-tested; the cog does
the Discord I/O and the DB mixin persists the post mapping."""

DEFAULT_THRESHOLD = 3


def starboard_action(count: int, threshold: int, has_post: bool) -> str:
    """Given the current ⭐ count, the threshold, and whether an entry already
    exists, decide what to do: 'create', 'update', 'remove', or 'none'."""
    if count >= threshold:
        return "update" if has_post else "create"
    return "remove" if has_post else "none"
