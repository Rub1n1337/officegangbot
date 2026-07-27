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


async def guild_accent_color(db, guild_id: int, default: discord.Color) -> discord.Color:
    """Premium branding: the guild's custom embed accent colour when it's a
    premium guild and a colour is set, otherwise ``default``. Defensive — any
    lookup error falls back to ``default`` so a member-facing embed never fails
    over a cosmetic setting."""
    try:
        if not await db.is_premium(guild_id):
            return default
        raw = await db.get_guild_setting(guild_id, "premium_embed_color")
        if raw is None:
            return default
        return discord.Color(int(raw) & 0xFFFFFF)
    except Exception:
        return default


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
