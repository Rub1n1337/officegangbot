"""Pure helper for the Role Menu embed body, kept free of discord.py so the
text composition can be unit-tested. The bot renders the result into an embed."""
from typing import List, Tuple


def build_menu_body(description: str, lines: List[Tuple[str, str]]) -> str:
    """Compose a role-menu message body: an optional description, then one
    ``emoji — mention`` line per role.

    ``lines`` is a list of ``(emoji, role_mention)`` tuples. Always returns a
    non-empty string (Discord embeds reject an empty description).
    """
    parts: List[str] = []
    if description and description.strip():
        parts.append(description.strip())
    for emoji, mention in lines:
        parts.append(f"{emoji} — {mention}")
    if not parts:
        return "React below to pick up a role."
    return "\n".join(parts)
