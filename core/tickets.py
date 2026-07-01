"""Pure helpers for the ticket system — transcript formatting and priority
normalization. Kept free of discord.py so they can be unit-tested directly."""
from typing import Any, Dict, List, Optional

VALID_PRIORITIES = ("low", "medium", "high", "urgent")

# Emoji + label used in embeds and the dashboard.
PRIORITY_LABELS = {
    "low": "🟢 Low",
    "medium": "🟡 Medium",
    "high": "🟠 High",
    "urgent": "🔴 Urgent",
}


def normalize_priority(value: Optional[str], default: str = "medium") -> str:
    """Coerces arbitrary input to one of VALID_PRIORITIES, falling back to
    `default` (itself validated) when the value is unknown."""
    v = (value or "").strip().lower()
    if v in VALID_PRIORITIES:
        return v
    return default if default in VALID_PRIORITIES else "medium"


def format_transcript_line(
    timestamp: str, author: str, content: str, attachments: Optional[List[str]] = None
) -> str:
    """Formats one message as `[timestamp] author: content` with any attachment
    URLs appended on an indented continuation line."""
    body = content or ""
    if attachments:
        joined = " ".join(a for a in attachments if a)
        if joined:
            att = f"[attachments] {joined}"
            body = f"{body}\n    {att}" if body else att
    return f"[{timestamp}] {author}: {body}"


def build_transcript(entries: List[Dict[str, Any]], header: Optional[str] = None) -> str:
    """Builds a plain-text transcript from oldest-first message entries. Each
    entry is a dict with keys: timestamp, author, content, attachments (list)."""
    lines: List[str] = []
    if header:
        lines.append(header)
        lines.append("-" * 60)
    for e in entries:
        lines.append(
            format_transcript_line(
                str(e.get("timestamp", "")),
                str(e.get("author", "")),
                str(e.get("content", "")),
                e.get("attachments") or [],
            )
        )
    if not entries:
        lines.append("(no messages)")
    return "\n".join(lines)
