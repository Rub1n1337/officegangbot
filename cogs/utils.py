# cogs/utils.py
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

async def reply(
    ctx: commands.Context,
    content: str = None,
    embed: discord.Embed = None,
    ephemeral: bool = False,
    view: discord.ui.View = None,
):
    """
    A robust reply function that handles both prefix and slash commands,
    and deals with interaction deferrals and errors.
    This function is the single source of truth for all bot replies.
    """
    # discord.py rejects view=None; only pass the kwarg when a view exists.
    extra = {"view": view} if view is not None else {}

    # For prefix commands, just send a normal message to the channel.
    # The 'ephemeral' flag is ignored as it's not supported.
    if ctx.prefix:
        try:
            await ctx.channel.send(content=content, embed=embed, **extra)
        except discord.errors.HTTPException as e:
            logger.error(f"Failed to send prefix command reply: {e}")
        return

    # For slash commands, we must handle the interaction state carefully.
    interaction = ctx.interaction
    if not interaction:
        logger.error("reply() was called on a command context with no prefix and no interaction.")
        return

    try:
        # If the interaction has not been acknowledged yet, defer it.
        # Deferring tells Discord "I got the command, I'm working on it."
        # This gives us a 15-minute window to send a followup.
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)

        # Now that we are certain the interaction is acknowledged (deferred),
        # we can safely send a followup message.
        await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral, **extra)

    except discord.errors.HTTPException as e:
        # This typically happens if the interaction token expires (e.g., > 15 mins have passed)
        # or if there's another underlying Discord issue.
        logger.error(f"Failed to send interaction followup: {e}. Attempting fallback.")
        try:
            # As a last resort, send a regular message to the channel.
            # This message will not be ephemeral.
            await ctx.channel.send(content=content, embed=embed)
        except Exception as final_e:
            logger.critical(f"FATAL: The fallback channel message in reply() also failed: {final_e}")
