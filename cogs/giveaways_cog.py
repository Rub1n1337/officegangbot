"""Giveaways: /giveaway start|end|reroll|list with a button to enter and an
auto-ending loop. Free servers can run a couple at once; premium raises the cap.

The entry button uses a static custom_id and looks the giveaway up by the
message it's attached to, so it survives bot restarts without dynamic ids.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.logger import logger
from core.discord_utils import safe_send
from core.giveaways import parse_duration, pick_winners
from core.limits import limit_for


def _giveaway_embed(prize, winners_count, ends_at, active, winner_mentions=None) -> discord.Embed:
    ts = int(ends_at.timestamp())
    if active:
        embed = discord.Embed(
            title="🎉 Giveaway",
            description=(
                f"**Prize:** {prize}\n"
                f"**Winners:** {winners_count}\n"
                f"**Ends:** <t:{ts}:R>\n\n"
                "Click the button below to enter!"
            ),
            color=discord.Color.blurple(),
        )
    else:
        won = ", ".join(winner_mentions) if winner_mentions else "no valid entries"
        embed = discord.Embed(
            title="🎉 Giveaway ended",
            description=f"**Prize:** {prize}\n**Winners:** {won}",
            color=discord.Color.greyple(),
        )
    return embed


class GiveawayView(discord.ui.View):
    """Persistent entry button; the giveaway is resolved from the message id."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎉 Enter", style=discord.ButtonStyle.primary, custom_id="giveaway:enter")
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        bot = interaction.client
        if not bot.db:
            return
        giveaway = await bot.db.get_giveaway_by_message(interaction.message.id)
        if not giveaway or giveaway["ended"]:
            await interaction.response.send_message("This giveaway has ended.", ephemeral=True)
            return
        added = await bot.db.add_giveaway_entry(giveaway["id"], interaction.user.id)
        await interaction.response.send_message(
            "You’re entered — good luck! 🎉" if added else "You’re already entered.",
            ephemeral=True,
        )


class GiveawaysCog(commands.Cog, name="🎉 Giveaways"):
    giveaway = app_commands.Group(name="giveaway", description="Run giveaways.", guild_only=True)

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.add_view(GiveawayView())  # rebind the entry button after restarts
        self._end_loop.start()

    def cog_unload(self):
        self._end_loop.cancel()

    async def _finish(self, g: dict) -> None:
        """Draw winners, edit the original message and announce (does not mark
        the row ended — the caller does, so a failure can't loop forever)."""
        entries = await self.bot.db.get_giveaway_entries(g["id"])
        winners = pick_winners(entries, g["winners_count"])
        mentions = [f"<@{w}>" for w in winners]
        guild = self.bot.get_guild(g["guild_id"])
        channel = guild.get_channel(g["channel_id"]) if guild else None
        if channel and g["message_id"]:
            try:
                msg = await channel.fetch_message(g["message_id"])
                await msg.edit(
                    embed=_giveaway_embed(g["prize"], g["winners_count"], g["ends_at"], active=False, winner_mentions=mentions),
                    view=None,
                )
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        if channel:
            if winners:
                await safe_send(channel, f"🎉 Congratulations {', '.join(mentions)} — you won **{g['prize']}**!")
            else:
                await safe_send(channel, f"No valid entries for **{g['prize']}** — no winner drawn.")

    @tasks.loop(seconds=60)
    async def _end_loop(self):
        if not self.bot.db:
            return
        try:
            due = await self.bot.db.get_due_giveaways(datetime.now(timezone.utc))
        except Exception:
            logger.exception("Giveaway end loop: failed to fetch due rows")
            return
        for g in due:
            try:
                await self._finish(g)
            except Exception:
                logger.exception(f"Failed to end giveaway {g['id']}")
            await self.bot.db.mark_giveaway_ended(g["id"])

    @_end_loop.before_loop
    async def _before_end(self):
        await self.bot.wait_until_ready()

    @giveaway.command(name="start", description="Start a giveaway.")
    @app_commands.describe(
        prize="What are you giving away?",
        duration="How long, e.g. 10m, 2h, 1d, 1w",
        winners="Number of winners (default 1)",
        channel="Where to post it (default: here)",
    )
    async def start(
        self,
        interaction: discord.Interaction,
        prize: str,
        duration: str,
        winners: int = 1,
        channel: Optional[discord.TextChannel] = None,
    ):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need the Manage Server permission.", ephemeral=True)
            return
        secs = parse_duration(duration)
        if secs is None:
            await interaction.response.send_message("Invalid duration — use e.g. 10m, 2h, 1d, 1w.", ephemeral=True)
            return
        winners = max(1, min(winners, 20))
        prize = prize.strip()[:200]
        channel = channel or interaction.channel
        premium = await self.bot.db.is_premium(interaction.guild_id)
        cap = limit_for("giveaways", premium)
        if await self.bot.db.count_active_giveaways(interaction.guild_id) >= cap:
            extra = "" if premium else " Upgrade to Premium to run more at once."
            await interaction.response.send_message(
                f"You already have the maximum of {cap} active giveaways.{extra}", ephemeral=True
            )
            return
        ends_at = datetime.now(timezone.utc) + timedelta(seconds=secs)
        gid = await self.bot.db.create_giveaway(
            interaction.guild_id, channel.id, prize, winners, ends_at, interaction.user.id
        )
        try:
            msg = await channel.send(
                embed=_giveaway_embed(prize, winners, ends_at, active=True), view=GiveawayView()
            )
        except discord.Forbidden:
            await self.bot.db.mark_giveaway_ended(gid)
            await interaction.response.send_message(f"I can’t post in {channel.mention}.", ephemeral=True)
            return
        await self.bot.db.set_giveaway_message(gid, msg.id)
        await interaction.response.send_message(f"Giveaway #{gid} started in {channel.mention}! 🎉", ephemeral=True)

    @giveaway.command(name="end", description="End a giveaway now.")
    @app_commands.describe(giveaway_id="The giveaway id (see /giveaway list)")
    async def end(self, interaction: discord.Interaction, giveaway_id: int):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need the Manage Server permission.", ephemeral=True)
            return
        g = await self.bot.db.get_giveaway(interaction.guild_id, giveaway_id)
        if not g or g["ended"]:
            await interaction.response.send_message("No active giveaway with that id.", ephemeral=True)
            return
        await self._finish(g)
        await self.bot.db.mark_giveaway_ended(giveaway_id)
        await interaction.response.send_message(f"Giveaway #{giveaway_id} ended.", ephemeral=True)

    @giveaway.command(name="reroll", description="Draw new winners for a giveaway.")
    @app_commands.describe(giveaway_id="The giveaway id (see /giveaway list)")
    async def reroll(self, interaction: discord.Interaction, giveaway_id: int):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need the Manage Server permission.", ephemeral=True)
            return
        g = await self.bot.db.get_giveaway(interaction.guild_id, giveaway_id)
        if not g:
            await interaction.response.send_message("No giveaway with that id.", ephemeral=True)
            return
        winners = pick_winners(await self.bot.db.get_giveaway_entries(giveaway_id), g["winners_count"])
        if not winners:
            await interaction.response.send_message("That giveaway has no valid entries.", ephemeral=True)
            return
        mentions = ", ".join(f"<@{w}>" for w in winners)
        await interaction.response.send_message(f"🎉 New winner(s) for **{g['prize']}**: {mentions}!")

    @giveaway.command(name="list", description="List this server's active giveaways.")
    async def list_giveaways(self, interaction: discord.Interaction):
        rows = await self.bot.db.list_active_giveaways(interaction.guild_id)
        if not rows:
            await interaction.response.send_message("No active giveaways.", ephemeral=True)
            return
        lines = [
            f"**#{r['id']}** — {r['prize']} · ends <t:{int(r['ends_at'].timestamp())}:R>"
            for r in rows
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawaysCog(bot))
