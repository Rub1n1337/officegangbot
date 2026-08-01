# core/polls.py
"""Pure poll helpers: parse the options string, apply a vote toggle, tally votes
and render the result bars. No bot/DB, so unit-tested; the cog does the Discord
I/O (buttons + live embed) and the DB mixin persists votes.
"""
from typing import List, Set

MIN_OPTIONS = 2
MAX_OPTIONS = 10
LABEL_LIMIT = 80  # Discord button-label max


def parse_options(raw: str, sep: str = "|") -> List[str]:
    """Split an 'a | b | c' string into cleaned options: trimmed, empties
    dropped, case-insensitive duplicates removed (first kept), each truncated to
    the button-label limit, capped at MAX_OPTIONS. The caller checks there are at
    least MIN_OPTIONS."""
    seen: Set[str] = set()
    out: List[str] = []
    for part in (raw or "").split(sep):
        opt = part.strip()
        if not opt:
            continue
        key = opt.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(opt[:LABEL_LIMIT])
        if len(out) >= MAX_OPTIONS:
            break
    return out


def apply_vote(current: Set[int], index: int, allow_multi: bool) -> Set[int]:
    """The user's new selection after clicking option ``index``.

    Single-choice: clicking selects only that option; clicking the same option
    again clears the vote. Multi-choice: toggles the option in/out of the set.
    """
    if allow_multi:
        new = set(current)
        if index in new:
            new.discard(index)
        else:
            new.add(index)
        return new
    return set() if current == {index} else {index}


def tally(votes: List[int], num_options: int) -> List[int]:
    """Count votes per option index into a fixed-length list (out-of-range
    indices are ignored)."""
    counts = [0] * num_options
    for idx in votes:
        if 0 <= idx < num_options:
            counts[idx] += 1
    return counts


def format_results(options: List[str], counts: List[int], width: int = 10) -> str:
    """Render each option as 'N. text' with a proportional bar, its count and
    percentage. Zero total votes renders empty bars at 0%."""
    total = sum(counts)
    lines = []
    for i, (opt, count) in enumerate(zip(options, counts), 1):
        pct = (count / total * 100) if total else 0
        filled = round(pct / 100 * width)
        bar = "█" * filled + "░" * (width - filled)
        lines.append(f"**{i}.** {opt}\n`{bar}` **{count}** ({pct:.0f}%)")
    return "\n\n".join(lines)
