"""Pure helpers for the Scheduled Messages feature, kept free of discord.py and
the DB so the recurrence math can be unit-tested. The cog calls compute_next_run
after posting a due message to decide when (or whether) it runs again."""
from datetime import datetime, timedelta
from typing import Optional

REPEAT_DELTAS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}

VALID_REPEATS = ("none", "daily", "weekly")


def compute_next_run(scheduled_at: datetime, repeat: str, now: datetime) -> Optional[datetime]:
    """The next run time strictly after ``now`` for a recurring message, or None
    for a one-off (repeat ``"none"``) that has already fired.

    Advances past any intervals missed while the bot was down (computed in O(1),
    not by looping), so a daily message that was due three days ago jumps to its
    next future occurrence rather than firing three times in a row.
    """
    delta = REPEAT_DELTAS.get(repeat)
    if delta is None:
        return None
    nxt = scheduled_at
    if nxt <= now:
        elapsed = now - scheduled_at
        steps = int(elapsed / delta) + 1
        nxt = scheduled_at + steps * delta
        # Guard the exact-boundary case so the result is strictly in the future.
        while nxt <= now:
            nxt += delta
    return nxt
