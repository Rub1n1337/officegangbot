# core/discord_utils.py
"""Small Discord helpers shared across cogs, replacing repeated try/except send
patterns and ad-hoc embed styling (48 embed constructions, 27 `except Forbidden`
sites across the cogs)."""
import datetime
from typing import Optional

import discord


async def safe_send(target, *args, **kwargs) -> Optional[discord.Message]:
    """Send a message, swallowing the routine "can't post here" errors (missing
    permissions, DMs closed, deleted channel). Returns the Message, or None if it
    couldn't be delivered. Replaces the repeated
    ``try: await x.send(...) \n except discord.Forbidden: pass`` pattern."""
    try:
        return await target.send(*args, **kwargs)
    except (discord.Forbidden, discord.HTTPException):
        return None


def themed_embed(
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[discord.Color] = None,
    timestamp: bool = True,
) -> discord.Embed:
    """A discord.Embed with the bot's default styling (brand colour + UTC
    timestamp), so cogs don't re-specify colour/timestamp on every embed."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color if color is not None else discord.Color.blurple(),
    )
    if timestamp:
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    return embed
