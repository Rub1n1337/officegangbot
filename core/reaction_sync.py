"""Pure helpers for reconciling the bot's own reactions on reaction-role messages.

Kept free of discord.py and the DB so the add/remove planning can be unit-tested.
``MyBot._sync_reactions`` calls :func:`plan_reaction_changes` and then performs the
actual Discord IO based on the returned plan.
"""
from typing import Any, Dict, List, Optional, Set


def plan_reaction_changes(
    new_rows: List[Dict[str, Any]],
    old_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[int, Dict[str, Any]]:
    """Diff the previous and desired reaction-role rows into a per-message plan.

    Each row is a dict with ``message_id``, ``channel_id`` and ``emoji``. Returns::

        {message_id: {"channel_id": int, "add": set[str], "remove": set[str]}}

    - ``add``: the emojis that should be present on the message (adding is
      idempotent, so this is just the desired set).
    - ``remove``: emojis the bot previously reacted with that are no longer desired
      on that message — this is what clears the *old* reaction when an admin changes
      the emoji on a reaction role (the previous bug left it behind).

    Messages that need neither an add nor a remove are omitted.
    """
    old_rows = old_rows or []
    channel_of: Dict[int, int] = {}
    new_by_msg: Dict[int, Set[str]] = {}
    old_by_msg: Dict[int, Set[str]] = {}

    for r in new_rows:
        mid = int(r["message_id"])
        channel_of[mid] = int(r["channel_id"])
        new_by_msg.setdefault(mid, set()).add(str(r["emoji"]))
    for r in old_rows:
        mid = int(r["message_id"])
        channel_of.setdefault(mid, int(r["channel_id"]))
        old_by_msg.setdefault(mid, set()).add(str(r["emoji"]))

    plan: Dict[int, Dict[str, Any]] = {}
    for mid in set(new_by_msg) | set(old_by_msg):
        add = new_by_msg.get(mid, set())
        remove = old_by_msg.get(mid, set()) - new_by_msg.get(mid, set())
        if not add and not remove:
            continue
        plan[mid] = {
            "channel_id": channel_of.get(mid),
            "add": add,
            "remove": remove,
        }
    return plan
