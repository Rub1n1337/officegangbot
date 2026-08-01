"""Polls: /poll create posts a button poll with a live-updating result bar;
votes persist and the poll auto-closes at its deadline (or via /poll end).

The vote toggle is the pure, unit-tested core in core.polls. The buttons use
static custom_ids (poll:vote:{i}) and resolve the poll by message id, so they
survive restarts. Bot-only, available to all (like giveaways/starboard).
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.logger import logger
from core.giveaways import parse_duration
from core.polls import apply_vote, format_results, parse_options, MAX_OPTIONS, MIN_OPTIONS


def _poll_embed(poll: dict, counts: List[int], closed: bool) -> discord.Embed:
    total = sum(counts)
    embed = discord.Embed(
        title=f"📊 {poll['question']}",
        description=format_results(poll["options"], counts),
        color=discord.Color.greyple() if closed else discord.Color.blurple(),
    )
    if closed:
        hint = "Poll closed"
    elif poll["allow_multi"]:
        hint = "Vote with the buttons — you can pick more than one"
    else:
        hint = "Vote with the buttons"
    embed.set_footer(text=f"{hint} · {total} vote(s)")
    return embed


class PollButton(discord.ui.Button):
    def __init__(self, index: int, label: Optional[str] = None):
        super().__init__(
            label=(label or str(index + 1))[:80],
            style=discord.ButtonStyle.secondary,
            custom_id=f"poll:vote:{index}",
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        bot = interaction.client
        if not bot.db:
            return
        poll = await bot.db.get_poll_by_message(interaction.message.id)
        if not poll or poll["closed"]:
            await interaction.response.send_message("This poll is closed.", ephemeral=True)
            return
        options = poll["options"]
        if self.index >= len(options):  # defensive: registered template has MAX buttons
            await interaction.response.defer()
            return
        current = await bot.db.get_user_poll_votes(poll["id"], interaction.user.id)
        new = apply_vote(current, self.index, poll["allow_multi"])
        await bot.db.set_user_poll_votes(poll["id"], interaction.user.id, new)
        counts = await bot.db.get_poll_counts(poll["id"], len(options))
        await interaction.response.edit_message(embed=_poll_embed(poll, counts, closed=False))


class PollView(discord.ui.View):
    """Persistent poll buttons. Registered once with MAX_OPTIONS buttons so any
    poll:vote:{i} survives a restart; a specific poll is sent with only as many
    buttons (and real labels) as it has options."""

    def __init__(self, count: int, labels: Optional[List[str]] = None):
        super().__init__(timeout=None)
        for i in range(count):
            self.add_item(PollButton(i, labels[i] if labels else None))


class PollsCog(commands.Cog, name="📊 Polls"):
    poll = app_commands.Group(name="poll", description="Create and manage polls.", guild_only=True)

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.add_view(PollView(MAX_OPTIONS))  # rebind vote buttons after restarts
        self._close_loop.start()

    def cog_unload(self):
        self._close_loop.cancel()

    async def _finalize(self, p: dict) -> None:
        """Edit the poll message to its final, view-less state (does not mark the
        row closed — the caller does, so a failure can't loop forever)."""
        counts = await self.bot.db.get_poll_counts(p["id"], len(p["options"]))
        guild = self.bot.get_guild(p["guild_id"])
        channel = guild.get_channel(p["channel_id"]) if guild else None
        if channel and p["message_id"]:
            try:
                msg = await channel.fetch_message(p["message_id"])
                await msg.edit(embed=_poll_embed(p, counts, closed=True), view=None)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

    @tasks.loop(seconds=60)
    async def _close_loop(self):
        if not self.bot.db:
            return
        try:
            due = await self.bot.db.get_due_polls(datetime.now(timezone.utc))
        except Exception:
            logger.exception("Poll close loop: failed to fetch due polls")
            return
        for p in due:
            try:
                await self._finalize(p)
            except Exception:
                logger.exception(f"Failed to close poll {p['id']}")
            await self.bot.db.close_poll(p["id"])

    @_close_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    @poll.command(name="create", description="Start a poll with up to 10 options.")
    @app_commands.describe(
        question="The poll question",
        options="Options separated by | e.g. Pizza | Sushi | Tacos",
        duration="Optional auto-close, e.g. 10m, 2h, 1d (default: open until /poll end)",
        multiple="Allow choosing more than one option (default: no)",
        channel="Where to post it (default: here)",
    )
    async def create(
        self,
        interaction: discord.Interaction,
        question: str,
        options: str,
        duration: Optional[str] = None,
        multiple: bool = False,
        channel: Optional[discord.TextChannel] = None,
    ):
        opts = parse_options(options)
        if len(opts) < MIN_OPTIONS:
            await interaction.response.send_message(
                f"Give at least {MIN_OPTIONS} options separated by `|` (up to {MAX_OPTIONS}).",
                ephemeral=True,
            )
            return
        ends_at = None
        if duration:
            secs = parse_duration(duration)
            if secs is None:
                await interaction.response.send_message(
                    "Invalid duration — use e.g. 10m, 2h, 1d, 1w.", ephemeral=True
                )
                return
            ends_at = datetime.now(timezone.utc) + timedelta(seconds=secs)
        question = question.strip()[:240]
        target = channel or interaction.channel
        pid = await self.bot.db.create_poll(
            interaction.guild_id, target.id, question, opts, multiple, ends_at, interaction.user.id
        )
        poll = {"id": pid, "question": question, "options": opts, "allow_multi": multiple}
        try:
            msg = await target.send(
                embed=_poll_embed(poll, [0] * len(opts), closed=False),
                view=PollView(len(opts), opts),
            )
        except discord.Forbidden:
            await self.bot.db.close_poll(pid)
            await interaction.response.send_message(f"I can’t post in {target.mention}.", ephemeral=True)
            return
        await self.bot.db.set_poll_message(pid, msg.id)
        await interaction.response.send_message(
            f"Poll #{pid} posted in {target.mention}. 📊", ephemeral=True
        )

    @poll.command(name="end", description="Close a poll now and show the final results.")
    @app_commands.describe(poll_id="The poll id (shown when you created it)")
    async def end(self, interaction: discord.Interaction, poll_id: int):
        p = await self.bot.db.get_poll(interaction.guild_id, poll_id)
        if not p or p["closed"]:
            await interaction.response.send_message("No open poll with that id.", ephemeral=True)
            return
        if not (interaction.user.guild_permissions.manage_messages or interaction.user.id == p["created_by"]):
            await interaction.response.send_message(
                "Only the poll’s creator or someone with Manage Messages can end it.", ephemeral=True
            )
            return
        await self._finalize(p)
        await self.bot.db.close_poll(poll_id)
        await interaction.response.send_message(f"Poll #{poll_id} closed.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PollsCog(bot))
