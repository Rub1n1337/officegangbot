# core/giveaways.py
"""Pure giveaway helpers (duration parsing + winner selection). No bot/DB, so
they're unit-tested; the cog handles the Discord I/O and the DB mixin persists."""
import random
import re
from typing import List, Optional

_DURATION_RE = re.compile(r"^\s*(\d+)\s*([smhdw])\s*$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
MAX_DURATION_SECONDS = 60 * 86400  # ~60 days


def parse_duration(text: str) -> Optional[int]:
    """Parse a short duration like '10m', '2h', '1d', '1w' into seconds. Returns
    None for anything invalid or out of range (0 < d <= ~60 days)."""
    match = _DURATION_RE.match(text or "")
    if not match:
        return None
    seconds = int(match.group(1)) * _UNIT_SECONDS[match.group(2).lower()]
    if seconds <= 0 or seconds > MAX_DURATION_SECONDS:
        return None
    return seconds


def pick_winners(entries: List[int], count: int) -> List[int]:
    """Pick up to ``count`` distinct random winners from ``entries`` (dedupes
    first). Fewer entries than winners just returns all of them."""
    unique = list(dict.fromkeys(entries))
    if not unique or count <= 0:
        return []
    return random.sample(unique, min(count, len(unique)))
