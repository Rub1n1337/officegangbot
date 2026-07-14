# core/appeals.py
"""Discord-native ban-appeal flow.

A banned user receives a DM (from the ban) with an "Appeal" button. Clicking it
opens a modal; the submitted text is stored in ban_appeals for moderators to
review from the dashboard. The button is a DynamicItem so it keeps working after
a bot restart — its custom_id carries the guild id and locale.
"""
import discord

from core.i18n import t, normalize_locale
from core.logger import logger


class AppealModal(discord.ui.Modal):
    """Collects the banned user's appeal text and stores it."""

    def __init__(self, guild_id: int, loc: str):
        self.guild_id = guild_id
        self.loc = loc
        super().__init__(title=t(loc, "appeal.modal_title"), timeout=600)
        self.reason = discord.ui.TextInput(
            label=t(loc, "appeal.reason_label"),
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
            placeholder=t(loc, "appeal.reason_ph"),
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        db = getattr(interaction.client, "db", None)
        text = (self.reason.value or "").strip()
        if not db:
            await interaction.response.send_message(t(self.loc, "appeal.error"), ephemeral=True)
            return
        try:
            await db.add_ban_appeal(self.guild_id, interaction.user.id, str(interaction.user), text)
        except Exception as e:
            logger.exception(f"Failed to store ban appeal for {interaction.user} in {self.guild_id}: {e}")
            await interaction.response.send_message(t(self.loc, "appeal.error"), ephemeral=True)
            return
        await interaction.response.send_message(t(self.loc, "appeal.submitted"), ephemeral=True)
        # Surface the new appeal in the punishment log too — admins who don't
        # open the dashboard regularly would otherwise never see it.
        try:
            await _notify_moderators(interaction.client, self.guild_id, interaction.user, text)
        except Exception:
            logger.exception(f"Failed to post appeal alert for guild {self.guild_id}")


async def _notify_moderators(bot, guild_id: int, user, text: str) -> None:
    """Best-effort embed to the punishment log when a new appeal arrives."""
    db = getattr(bot, "db", None)
    guild = bot.get_guild(guild_id)
    if not db or not guild:
        return
    log_id = await db.get_guild_setting(guild_id, "punishment_log_id")
    if not log_id:
        return
    channel = guild.get_channel(int(log_id))
    if channel is None:
        try:
            channel = await guild.fetch_channel(int(log_id))
        except discord.HTTPException:
            return
    embed = discord.Embed(
        title="📝 New ban appeal",
        description=text[:1000],
        color=discord.Color.orange(),
    )
    embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
    embed.set_footer(text="Review it on the dashboard → Moderation")
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass


class AppealButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"appeal:(?P<guild>\d+):(?P<loc>[a-z]{2})",
):
    """Persistent 'Appeal this ban' button. Survives restarts via its custom_id."""

    def __init__(self, guild_id: int, loc: str):
        self.guild_id = guild_id
        self.loc = normalize_locale(loc)
        super().__init__(
            discord.ui.Button(
                label=t(self.loc, "appeal.button"),
                style=discord.ButtonStyle.primary,
                custom_id=f"appeal:{guild_id}:{self.loc}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["guild"]), match["loc"])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AppealModal(self.guild_id, self.loc))


async def send_ban_appeal_dm(guild: discord.Guild, user, reason: str, loc: str) -> bool:
    """DMs `user` the ban notice plus an Appeal button. Returns True if the DM
    was delivered (best-effort; users with closed DMs simply won't get it)."""
    embed = discord.Embed(
        title=t(loc, "mod.dm_banned_title", guild=guild.name),
        color=discord.Color.red(),
    )
    embed.add_field(name=t(loc, "field.reason"), value=(reason or "—")[:1024], inline=False)
    embed.add_field(name=t(loc, "appeal.dm_field"), value=t(loc, "appeal.dm_hint"), inline=False)

    view = discord.ui.View(timeout=None)
    view.add_item(AppealButton(guild.id, loc))
    try:
        await user.send(embed=embed, view=view)
        return True
    except discord.HTTPException:
        return False
