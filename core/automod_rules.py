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


def _group_spans(pattern: str) -> List[Tuple[int, int]]:
    """(open, close) index pairs of every '(...)' group, honouring escaped
    parens. Innermost groups come first (they close first)."""
    stack: List[int] = []
    spans: List[Tuple[int, int]] = []
    i, n = 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "\\":
            i += 2
            continue
        if c == "(":
            stack.append(i)
        elif c == ")" and stack:
            spans.append((stack.pop(), i))
        i += 1
    return spans


def _has_unbounded_quantifier(s: str) -> bool:
    """True if s contains an unescaped +, *, or {n,}/{n,m} quantifier."""
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c in "+*":
            return True
        if c == "{":
            j = s.find("}", i)
            if j != -1 and "," in s[i + 1 : j]:
                return True
        i += 1
    return False


def _quantifier_at(pattern: str, idx: int) -> bool:
    """True if pattern[idx:] begins a repetition quantifier (+, *, or {n,})."""
    if idx >= len(pattern):
        return False
    c = pattern[idx]
    if c in "+*":
        return True
    if c == "{":
        j = pattern.find("}", idx)
        return j != -1 and "," in pattern[idx + 1 : j]
    return False


def has_redos_risk(pattern: str) -> bool:
    """Heuristic flag for catastrophic-backtracking risk: a quantified group whose
    contents also contain an unbounded quantifier — e.g. (a+)+, (\\w*)*, (.+){2,}.
    These can hang the shared event loop on a crafted message. This is a defensive
    filter over admin-authored patterns, not a formal guarantee."""
    if not pattern:
        return False
    for start, end in _group_spans(pattern):
        inner = pattern[start + 1 : end]
        if _has_unbounded_quantifier(inner) and _quantifier_at(pattern, end + 1):
            return True
    return False


def validate_pattern(pattern: str) -> Optional[str]:
    """Returns None if the pattern is a usable, safe regex, else a short reason."""
    if not pattern or not pattern.strip():
        return "empty pattern"
    if len(pattern) > MAX_PATTERN_LEN:
        return f"pattern too long (max {MAX_PATTERN_LEN})"
    try:
        re.compile(pattern)
    except re.error as e:
        return f"invalid regex: {e}"
    if has_redos_risk(pattern):
        return "unsafe pattern: nested quantifiers can cause catastrophic backtracking"
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
    Invalid patterns are skipped rather than raising. Patterns flagged as ReDoS
    risks are also skipped, so even a risky pattern stored before validation
    existed can never actually run against messages."""
    compiled: List[Tuple[Any, str]] = []
    for r in rules or []:
        if not r.get("enabled", True):
            continue
        try:
            pattern = str(r["pattern"])
        except (KeyError, TypeError):
            continue
        if has_redos_risk(pattern):
            continue
        try:
            compiled.append((re.compile(pattern, re.IGNORECASE), normalize_action(r.get("action"))))
        except re.error:
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
