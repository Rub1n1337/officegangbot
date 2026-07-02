"""Safe rendering of user-authored message templates (welcome messages, etc.).

Server admins can set these templates from the dashboard, so they must NOT be
passed to ``str.format()`` with live objects: ``str.format`` allows arbitrary
attribute traversal, so a template like ``{user._state.http.token}`` or
``{server._state...}`` would leak the bot token / internals into a channel the
admin controls. Instead we substitute only a fixed whitelist of ``{placeholder}``
tokens from a pre-computed string map and never touch the objects themselves.
"""
import re
from typing import Dict

# One {token} that is not part of a {{ }} escape (no nested braces inside).
_FIELD = re.compile(r"\{([^{}]*)\}")

# Placeholders offered to admins for welcome messages, mapped to safe string
# values by welcome_values(). Anything outside this set is left as literal text.
WELCOME_PLACEHOLDERS = (
    "user",
    "user.mention",
    "user.name",
    "user.display_name",
    "user.id",
    "server",
    "server.name",
    "server.id",
    "server.member_count",
)


def render_template(template: str, values: Dict[str, str]) -> str:
    """Render a template by substituting only whitelisted ``{placeholder}``
    tokens (the keys of ``values``). Unknown placeholders — including hostile
    attribute chains like ``{user.__class__}`` — are left untouched as literal
    text. ``{{`` / ``}}`` are treated as escaped literal braces, matching
    ``str.format`` semantics. No attribute access is performed, so this cannot
    read object internals."""
    if not template:
        return template
    # Protect escaped braces before scanning for real placeholders.
    open_sentinel, close_sentinel = "\x00", "\x01"
    protected = template.replace("{{", open_sentinel).replace("}}", close_sentinel)

    def _sub(match: "re.Match[str]") -> str:
        key = match.group(1).strip()
        if key in values:
            return str(values[key])
        return match.group(0)  # leave unknown placeholder as-is

    rendered = _FIELD.sub(_sub, protected)
    return rendered.replace(open_sentinel, "{").replace(close_sentinel, "}")


def is_template_valid(template: str, allowed: tuple = WELCOME_PLACEHOLDERS) -> bool:
    """True if every ``{placeholder}`` in the template is in ``allowed``. Used to
    warn an admin that a placeholder won't be substituted (it would otherwise be
    left as literal text). ``{{``/``}}`` escapes are ignored."""
    stripped = template.replace("{{", "").replace("}}", "")
    return all(m.group(1).strip() in allowed for m in _FIELD.finditer(stripped))


def welcome_values(member, guild) -> Dict[str, str]:
    """Build the whitelist of safe string values for a welcome message. Kept
    thin (no logic) so render_template stays the unit-tested pure part."""
    return {
        "user": str(member),
        "user.mention": member.mention,
        "user.name": member.name,
        "user.display_name": getattr(member, "display_name", member.name),
        "user.id": str(member.id),
        "server": guild.name,
        "server.name": guild.name,
        "server.id": str(guild.id),
        "server.member_count": str(getattr(guild, "member_count", "") or ""),
    }
