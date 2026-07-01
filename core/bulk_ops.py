"""Pure helpers for bulk moderation commands — parsing user-id lists out of the
free-text argument a slash command receives. Kept discord-free for testing."""
import re
from typing import List

# A Discord snowflake is 17-20 digits; the surrounding lookarounds stop us from
# grabbing a slice out of an even longer digit run.
_ID_RE = re.compile(r"(?<!\d)\d{17,20}(?!\d)")


def parse_id_list(text: str, limit: int = 20) -> List[int]:
    """Extracts snowflake ids from free text — accepts raw ids and
    <@…>/<@!…> mentions separated by spaces, commas or newlines. Dedupes while
    preserving first-seen order and caps the result at `limit`."""
    out: List[int] = []
    for m in _ID_RE.findall(str(text or "")):
        v = int(m)
        if v not in out:
            out.append(v)
    return out[: max(0, limit)]
