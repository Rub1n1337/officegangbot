# core/custom_commands.py
"""Validation for premium custom /tag commands.

Kept pure (no bot/DB) so it's unit-testable; the cog renders responses with the
shared safe_format machinery and the DB mixin persists the sanitized rows.
"""
import re
from typing import Any, Dict, List

# Discord slash-command / option names are lowercase; we surface custom commands
# as the value of /tag <name>, but keep to the same safe charset so names read
# and autocomplete cleanly.
NAME_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
MAX_RESPONSE_LEN = 2000


def valid_name(name: str) -> bool:
    return bool(NAME_RE.match(name))


def sanitize_commands(rows: List[Dict[str, Any]], max_count: int) -> List[Dict[str, str]]:
    """Normalize a list of {name, response} dicts for persistence: lowercase and
    validate names, drop empties/invalids/duplicates, trim responses, and cap the
    count at ``max_count``."""
    out: List[Dict[str, str]] = []
    seen = set()
    for r in rows or []:
        name = str(r.get("name", "")).strip().lower()
        response = str(r.get("response", "")).strip()[:MAX_RESPONSE_LEN]
        if not valid_name(name) or not response or name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "response": response})
        if len(out) >= max_count:
            break
    return out
