"""Invite tracker: attributes each join to the invite (and its creator) used,
by diffing the guild's invite use-counts around the join. Keeps a per-inviter
leaderboard and can announce joins with attribution in a log channel.

Reading invites needs the Manage Server permission; without it a join is still
recorded, just unattributed. The diff is the pure, unit-tested core in
core.invites — this cog holds the per-guild invite cache and does the Discord I/O.
"""
from typing import Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.logger import logger
from core.discord_utils import safe_send
from core.invites import detect_used_invite


async def _uses(guild: discord.Guild) -> Optional[Dict[str, int]]:
    """Current {code: uses} for the guild, or None if invites aren't readable
    (missing Manage Server). The vanity URL isn't in guild.invites(), so vanity
    joins fall through to "unknown inviter" — by design."""
    try:
        invites = await guild.invites()
    except (discord.Forbidden, discord.HTTPException):
        return None
    return {inv.code: (inv.uses or 0) for inv in invites}


class InviteTrackerCog(commands.Cog, name="📨 Invite Tracker"):
    tracker = app_commands.Group(
        name="invitetracker", description="Configure invite tracking.", guild_only=True
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> {code: uses}, primed on ready and kept fresh by the
        # invite create/delete events and each join.
        self._cache: Dict[int, Dict[str, int]] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        # Re-prime on every (re)connect: invites can change while disconnected,
        # so a stale cache would misattribute the next join.
        for guild in self.bot.guilds:
            snap = await _uses(guild)
            if snap is not None:
                self._cache[guild.id] = snap

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        snap = await _uses(guild)
        if snap is not None:
            self._cache[guild.id] = snap

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if invite.guild:
            self._cache.setdefault(invite.guild.id, {})[invite.code] = invite.uses or 0

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if invite.guild:
            self._cache.get(invite.guild.id, {}).pop(invite.code, None)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot or not self.bot.db:
            return
        guild = member.guild
        before = self._cache.get(guild.id, {})
        inviter_id: Optional[int] = None
        code: Optional[str] = None
        try:
            invites = await guild.invites()
        except (discord.Forbidden, discord.HTTPException):
            invites = None
        if invites is not None:
            after = {inv.code: (inv.uses or 0) for inv in invites}
            self._cache[guild.id] = after
            code = detect_used_invite(before, after)
            if code:
                used = next((i for i in invites if i.code == code), None)
                inviter_id = used.inviter.id if used and used.inviter else None
        try:
            await self.bot.db.record_invite_join(guild.id, member.id, inviter_id, code)
        except Exception:
            logger.exception("invite tracker: failed to record join")
            return
        await self._announce(member, inviter_id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot or not self.bot.db:
            return
        try:
            await self.bot.db.mark_invite_left(member.guild.id, member.id)
        except Exception:
            logger.exception("invite tracker: failed to mark left")

    async def _announce(self, member: discord.Member, inviter_id: Optional[int]) -> None:
        channel_id = await self.bot.db.get_guild_setting(member.guild.id, "invite_log_channel_id")
        if not channel_id:
            return
        channel = member.guild.get_channel(int(channel_id))
        if not channel:
            return
        if inviter_id:
            stats = await self.bot.db.get_inviter_stats(member.guild.id, inviter_id)
            text = (
                f"📨 {member.mention} joined — invited by <@{inviter_id}>, "
                f"now at **{stats['net']}** invites."
            )
        else:
            text = f"📨 {member.mention} joined — I couldn't tell which invite they used."
        await safe_send(channel, text)

    @app_commands.command(name="invites", description="Show how many members someone has invited.")
    @app_commands.describe(member="Whose invites to show (default: you)")
    @app_commands.guild_only()
    async def invites_cmd(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        member = member or interaction.user
        stats = await self.bot.db.get_inviter_stats(interaction.guild_id, member.id)
        await interaction.response.send_message(
            f"**{member.display_name}** has **{stats['net']}** invites "
            f"({stats['joined']} joined · {stats['left']} left).",
            ephemeral=True,
        )

    @app_commands.command(name="inviteleaderboard", description="Top inviters in this server.")
    @app_commands.guild_only()
    async def leaderboard_cmd(self, interaction: discord.Interaction):
        rows = await self.bot.db.get_invite_leaderboard(interaction.guild_id, 10)
        if not rows:
            await interaction.response.send_message("No invites tracked yet.", ephemeral=True)
            return
        lines = [
            f"**{i}.** <@{r['inviter_id']}> — **{r['net']}** ({r['joined']} joined · {r['left']} left)"
            for i, r in enumerate(rows, 1)
        ]
        embed = discord.Embed(
            title="📨 Invite Leaderboard",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)

    @tracker.command(name="channel", description="Announce joins (and who invited them) in a channel.")
    @app_commands.describe(channel="Where to post join announcements")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need the Manage Server permission.", ephemeral=True)
            return
        await self.bot.db.set_guild_setting(interaction.guild_id, "invite_log_channel_id", channel.id)
        await interaction.response.send_message(
            f"Join announcements will post in {channel.mention}. 📨", ephemeral=True
        )

    @tracker.command(name="disable", description="Stop announcing joins (tracking continues).")
    async def disable(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need the Manage Server permission.", ephemeral=True)
            return
        await self.bot.db.set_guild_setting(interaction.guild_id, "invite_log_channel_id", None)
        await interaction.response.send_message("Join announcements turned off.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(InviteTrackerCog(bot))
