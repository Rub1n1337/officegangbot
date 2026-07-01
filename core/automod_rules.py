"""Pure helpers for AutoMod custom regex rules — validation, sanitization,
compilation and matching. Kept discord-free so they can be unit-tested and so
untrusted-ish (admin-authored) patterns are handled defensively.

Patterns are authored by server admins, but we still cap their number and length
and swallow regex errors so a bad pattern can't take AutoMod down."""
import re
from typing import Any, Dict, List, Optional, Tuple

MAX_RULES = 25
MAX_PATTERN_LEN = 200
VALID_ACTIONS = ("delete", "strike")
# Cap how much of a message we scan, to bound worst-case regex cost.
MAX_SCAN_LEN = 2000


def normalize_action(action: Optional[str]) -> str:
    """Coerces an action to a valid value, defaulting to 'delete'."""
    a = (action or "").strip().lower()
    return a if a in VALID_ACTIONS else "delete"


def validate_pattern(pattern: str) -> Optional[str]:
    """Returns None if the pattern is a usable regex, else a short error reason."""
    if not pattern or not pattern.strip():
        return "empty pattern"
    if len(pattern) > MAX_PATTERN_LEN:
        return f"pattern too long (max {MAX_PATTERN_LEN})"
    try:
        re.compile(pattern)
    except re.error as e:
        return f"invalid regex: {e}"
    return None


def sanitize_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validates and caps a list of {pattern, action, enabled} dicts for
    persistence: drops empty/invalid/too-long/duplicate patterns and limits the
    count to MAX_RULES."""
    out: List[Dict[str, Any]] = []
    seen = set()
    for r in rules or []:
        pattern = str(r.get("pattern", "")).strip()
        if not pattern or pattern in seen:
            continue
        if validate_pattern(pattern) is not None:
            continue
        seen.add(pattern)
        out.append(
            {
                "pattern": pattern,
                "action": normalize_action(r.get("action")),
                "enabled": bool(r.get("enabled", True)),
            }
        )
        if len(out) >= MAX_RULES:
            break
    return out


def compile_rules(rules: List[Dict[str, Any]]) -> List[Tuple[Any, str]]:
    """Compiles the enabled rules into [(regex, action)] (case-insensitive).
    Invalid patterns are skipped rather than raising."""
    compiled: List[Tuple[Any, str]] = []
    for r in rules or []:
        if not r.get("enabled", True):
            continue
        try:
            compiled.append((re.compile(str(r["pattern"]), re.IGNORECASE), normalize_action(r.get("action"))))
        except (re.error, KeyError, TypeError):
            continue
    return compiled


def first_match(compiled: List[Tuple[Any, str]], content: str) -> Optional[str]:
    """Returns the action of the first compiled rule that matches the content
    (scanning at most MAX_SCAN_LEN chars), or None."""
    if not content:
        return None
    text = content[:MAX_SCAN_LEN]
    for regex, action in compiled:
        try:
            if regex.search(text):
                return action
        except re.error:
            continue
    return None
