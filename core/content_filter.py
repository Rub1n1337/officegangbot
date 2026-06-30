"""Pure content-filter helpers for AutoMod (invite links + disallowed links).

Kept free of discord.py and the DB so the matching can be unit-tested. The
AutoMod cog calls these on each message when the relevant rule is enabled.
"""
import re
from typing import Iterable, Optional
from urllib.parse import urlparse

# discord.gg/x, discord.com/invite/x, discordapp.com/invite/x — with or without
# a scheme / www, since spammers post them bare.
INVITE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?discord(?:\.gg|app\.com/invite|\.com/invite)/[A-Za-z0-9\-]{2,}",
    re.IGNORECASE,
)

# Only explicit http(s) URLs, to keep the "block links" rule low on false
# positives (bare "e.g." / "U.S." / "file.txt" won't match).
URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


def contains_invite(content: str) -> bool:
    """True if the text contains a Discord invite link."""
    return bool(INVITE_RE.search(content or ""))


def normalize_domain(domain: str) -> str:
    """Reduce a domain or pasted URL to a bare host: drop scheme, path and a
    leading ``www.`` (e.g. ``https://www.YouTube.com/x`` -> ``youtube.com``)."""
    d = (domain or "").strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/", 1)[0]
    return d[4:] if d.startswith("www.") else d


def first_disallowed_link(content: str, allowed_domains: Iterable[str]) -> Optional[str]:
    """Return the first http(s) URL whose host is not allowed, or None.

    A host is allowed if it equals an allowed domain or is a subdomain of one
    (so ``youtube.com`` in the allow-list also permits ``www.youtube.com`` and
    ``m.youtube.com``).
    """
    allowed = {normalize_domain(d) for d in (allowed_domains or []) if d and d.strip()}
    for match in URL_RE.finditer(content or ""):
        url = match.group(0)
        host = normalize_domain(urlparse(url).hostname or "")
        if not host:
            continue
        if host in allowed or any(host.endswith("." + d) for d in allowed):
            continue
        return url
    return None
