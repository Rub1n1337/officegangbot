# cogs/utils.py
import discord
from discord.ext import commands
import logging
from typing import List, Optional

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
            logger.exception(f"Failed to send prefix command reply: {e}")
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
        logger.exception(f"Failed to send interaction followup: {e}. Attempting fallback.")
        try:
            # As a last resort, send a regular message to the channel.
            # This message will not be ephemeral.
            await ctx.channel.send(content=content, embed=embed)
        except Exception as final_e:
            logger.critical(f"FATAL: The fallback channel message in reply() also failed: {final_e}")


class Paginator(discord.ui.View):
    """A reusable embed paginator with first/prev/next/last buttons.

    Restricted to the member who ran the command; self-disables on timeout.
    Buttons edit the message in place via the component interaction, so it
    works on both ephemeral and public messages.
    """

    def __init__(self, pages: List[discord.Embed], author_id: int, *, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author_id = author_id
        self.index = 0
        self.message: Optional[discord.Message] = None
        self._sync()

    def _sync(self) -> None:
        last = len(self.pages) - 1
        self.first_page.disabled = self.prev_page.disabled = self.index <= 0
        self.next_page.disabled = self.last_page.disabled = self.index >= last
        self.indicator.label = f"{self.index + 1}/{len(self.pages)}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This menu isn't yours — run the command yourself.", ephemeral=True
            )
            return False
        return True

    async def _show(self, interaction: discord.Interaction) -> None:
        self._sync()
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = 0
        await self._show(interaction)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = max(0, self.index - 1)
        await self._show(interaction)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = min(len(self.pages) - 1, self.index + 1)
        await self._show(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = len(self.pages) - 1
        await self._show(interaction)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


async def send_paginated(
    ctx: commands.Context, pages: List[discord.Embed], *, ephemeral: bool = False
):
    """Sends a single embed if there's one page, otherwise an interactive
    Paginator. Relies on the global auto-defer having acked the interaction."""
    if not pages:
        return
    if len(pages) == 1:
        return await reply(ctx, embed=pages[0], ephemeral=ephemeral)

    view = Paginator(pages, ctx.author.id)

    # Prefix invocation: plain channel message.
    if ctx.interaction is None:
        view.message = await ctx.channel.send(embed=pages[0], view=view)
        return view.message

    interaction = ctx.interaction
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=ephemeral)
    view.message = await interaction.followup.send(embed=pages[0], view=view, ephemeral=ephemeral)
    return view.message
