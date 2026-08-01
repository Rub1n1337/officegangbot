# core/invites.py
"""Pure invite-tracking helper: work out which invite a join used by diffing
the guild's invite use-counts around the join. No bot/DB, so it's unit-tested;
the cog holds the per-guild cache and does the Discord I/O, the DB mixin persists
and aggregates the leaderboard.
"""
from typing import Dict, Optional


def detect_used_invite(before: Dict[str, int], after: Dict[str, int]) -> Optional[str]:
    """Return the invite code whose use-count went up between two snapshots —
    the invite the member just used — or None when it can't be told apart.

    ``before``/``after`` map an invite code to its use count. A code present in
    ``after`` but not ``before`` counts as a candidate if its uses are >= 1 (a
    single-use invite created and consumed between snapshots). None is returned
    for the ambiguous cases the caller must treat as "unknown inviter":
      * nothing incremented — a vanity URL, or invites weren't readable;
      * two or more codes incremented at once — can't attribute to one.
    """
    candidates = [code for code, uses in after.items() if uses > before.get(code, 0)]
    return candidates[0] if len(candidates) == 1 else None
