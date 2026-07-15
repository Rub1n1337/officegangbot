# cogs/mod_tools.py
"""Advanced moderation tools: numbered case lookup, temporary roles (with an
expiry loop) and bulk actions (mass ban / mass role). Kept separate from the
core Moderation cog so it stays self-contained. User-facing text is English, in
line with the timed_events cog."""
import datetime
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.logger import logger
from core.i18n import t
from core.permissions import has_permission, role_is_assignable
from core.bulk_ops import parse_id_list
from .utils import reply
from .timed_events import parse_duration, format_duration

MAX_BULK = 20

# Emoji hints for the case log by action keyword.
_ACTION_EMOJI = {"ban": "🔨", "kick": "👢", "mute": "🔇", "warn": "⚠️", "unban": "♻️", "unmute": "🔊"}


def _action_emoji(action: str) -> str:
    a = (action or "").lower()
    for key, emoji in _ACTION_EMOJI.items():
        if key in a:
            return emoji
    return "📄"


class ConfirmView(discord.ui.View):
    """A generic confirm/cancel prompt bound to the invoking user."""

    def __init__(self, author_id: int, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.value: Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This confirmation isn't yours.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.edit_message(content="Working…", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.edit_message(content="❌ Cancelled.", view=None)

    async def on_timeout(self):
        self.value = False
        self.stop()


class ModToolsCog(commands.Cog, name="🧰 Mod Tools"):
    """Case lookup, temporary roles and bulk moderation actions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_expired_temp_roles.start()

    def cog_unload(self):
        self.check_expired_temp_roles.cancel()

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CommandOnCooldown):
            return await reply(
                ctx, f"⏳ Slow down — try again in {error.retry_after:.0f}s.", ephemeral=True
            )
        if isinstance(error, commands.BotMissingPermissions):
            perms = ', '.join(error.missing_permissions)
            return await reply(ctx, f"❌ I'm missing permissions: {perms}", ephemeral=True)
        if isinstance(error, (commands.MissingPermissions, commands.CheckFailure)):
            return await reply(ctx, "❌ You don't have permission to use this command.", ephemeral=True)
        if isinstance(error, (commands.MemberNotFound, commands.RoleNotFound, commands.BadArgument)):
            return await reply(ctx, f"❌ {error}", ephemeral=True)
        logger.error(f"Unhandled error in mod_tools: {error}", exc_info=True)
        await reply(ctx, "❌ An unexpected error occurred.", ephemeral=True)

    # -- Temp-role expiry loop ---------------------------------------------

    @tasks.loop(seconds=60)
    async def check_expired_temp_roles(self):
        """Removes temp roles whose expiry has passed."""
        try:
            if not self.bot.db:
                return
            expired = await self.bot.db.get_expired_temp_roles()
            for r in expired:
                guild = self.bot.get_guild(r["guild_id"])
                if not guild:
                    await self.bot.db.remove_temp_role(r["guild_id"], r["user_id"], r["role_id"])
                    continue
                member = guild.get_member(r["user_id"])
                role = guild.get_role(r["role_id"])
                if member and role and role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Temporary role expired")
                        logger.info(f"Removed expired temp role {role.id} from {member} in {guild.name}")
                    except (discord.Forbidden, discord.HTTPException) as e:
                        logger.warning(f"Could not remove temp role {role.id} in {guild.name}: {e}")
                await self.bot.db.remove_temp_role(r["guild_id"], r["user_id"], r["role_id"])
        except Exception as e:
            logger.error(f"check_expired_temp_roles crashed: {e}", exc_info=True)

    @check_expired_temp_roles.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    # -- Case management ----------------------------------------------------

    @commands.hybrid_command(name="case", description="Look up a moderation case by its number.")
    @app_commands.describe(number="The case number to look up.")
    @commands.has_permissions(moderate_members=True)
    async def case(self, ctx: commands.Context, number: int):
        row = await self.bot.db.get_mod_case(ctx.guild.id, number)
        if not row:
            return await reply(ctx, f"❌ Case #{number} was not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"{_action_emoji(row['action'])} Case #{row['case_number']} · {row['action']}",
            color=discord.Color.orange(),
            timestamp=row["created_at"],
        )
        target = f"<@{row['target_id']}>" if row["target_id"] else (row["target_name"] or "—")
        embed.add_field(name="Target", value=f"{target}\n`{row['target_id'] or '—'}`", inline=True)
        embed.add_field(name="Moderator", value=row["moderator_name"] or "—", inline=True)
        embed.add_field(name="Reason", value=(row["reason"] or "No reason provided")[:1024], inline=False)
        await reply(ctx, embed=embed, ephemeral=True)

    @commands.hybrid_command(name="cases", description="List recent moderation cases (optionally for one member).")
    @app_commands.describe(member="Only show cases for this member (optional).")
    @commands.has_permissions(moderate_members=True)
    async def cases(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        rows = await self.bot.db.get_mod_cases(
            ctx.guild.id, target_id=member.id if member else None, limit=15
        )
        if not rows:
            scope = f" for {member.mention}" if member else ""
            return await reply(ctx, f"No cases recorded{scope}.", ephemeral=True)

        title = f"Cases for {member.display_name}" if member else "Recent moderation cases"
        embed = discord.Embed(title=f"📁 {title}", color=discord.Color.blurple())
        for r in rows:
            who = r["target_name"] or (f"<@{r['target_id']}>" if r["target_id"] else "—")
            when = f"<t:{int(r['created_at'].timestamp())}:R>" if r["created_at"] else ""
            reason = (r["reason"] or "No reason").strip()
            if len(reason) > 80:
                reason = reason[:77] + "…"
            embed.add_field(
                name=f"#{r['case_number']} · {_action_emoji(r['action'])} {r['action']}",
                value=f"{who} · by {r['moderator_name'] or '—'} {when}\n{reason}",
                inline=False,
            )
        await reply(ctx, embed=embed, ephemeral=True)

    @commands.hybrid_command(name="history", description="A member's full moderation history in one place.")
    @app_commands.describe(member="Member to look up.")
    @has_permission("warn")
    async def history(self, ctx: commands.Context, member: discord.Member):
        """One dossier instead of running /warnings, /cases and /notes in turn.

        Same data the dashboard's member card already assembles — warnings
        (active vs expired), notes, strikes and numbered cases — so a moderator
        can see the whole picture before deciding on an action.
        """
        db = self.bot.db
        if not db:
            loc = "en"
            return await reply(ctx, t(loc, "common.db_unavailable"), ephemeral=True)
        loc = await db.get_locale(ctx.guild.id)

        cfg = await db.get_warn_escalation(ctx.guild.id)
        expiry_hours = cfg["expiry_hours"] if cfg["enabled"] else 0
        warnings = await db.get_warnings(ctx.guild.id, member.id)
        active_warnings = await db.count_active_warnings(ctx.guild.id, member.id, expiry_hours)
        notes = await db.get_mod_notes(ctx.guild.id, member.id)
        strikes = await db.count_active_strikes_for(ctx.guild.id, member.id)
        cases = await db.get_mod_cases(ctx.guild.id, target_id=member.id, limit=5)

        embed = discord.Embed(
            title=t(loc, "history.title", member=member.display_name),
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name=t(loc, "history.summary"),
            value=t(
                loc, "history.summary_value",
                warnings=len(warnings), active=active_warnings,
                strikes=int(strikes), notes=len(notes), cases=len(cases),
            ),
            inline=False,
        )
        if member.joined_at:
            embed.add_field(
                name=t(loc, "history.joined"),
                value=f"<t:{int(member.joined_at.timestamp())}:D> (<t:{int(member.joined_at.timestamp())}:R>)",
                inline=True,
            )
        embed.add_field(
            name=t(loc, "history.account_created"),
            value=f"<t:{int(member.created_at.timestamp())}:D>",
            inline=True,
        )

        if cases:
            lines = []
            for r in cases:
                when = f"<t:{int(r['created_at'].timestamp())}:R>" if r["created_at"] else ""
                reason = (r["reason"] or t(loc, "history.no_reason")).strip()
                if len(reason) > 60:
                    reason = reason[:57] + "…"
                lines.append(f"`#{r['case_number']}` {_action_emoji(r['action'])} {r['action']} {when} — {reason}")
            embed.add_field(name=t(loc, "history.recent_cases"), value="\n".join(lines)[:1024], inline=False)

        if warnings:
            cutoff = (
                datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=expiry_hours)
                if expiry_hours > 0 else None
            )
            lines = []
            for w in warnings[-5:]:
                ts = w["created_at"]
                when = f"<t:{int(ts.timestamp())}:R>" if isinstance(ts, datetime.datetime) else ""
                reason = (w["reason"] or "—")[:60]
                expired = bool(cutoff and isinstance(ts, datetime.datetime) and ts < cutoff)
                line = f"{when} — {reason} ({w['moderator_name'] or '—'})"
                lines.append(f"~~{line}~~" if expired else line)
            embed.add_field(name=t(loc, "history.recent_warnings"), value="\n".join(lines)[:1024], inline=False)

        if notes:
            lines = [f"`#{n['id']}` {(n['note'] or '')[:70]}" for n in notes[-3:]]
            embed.add_field(name=t(loc, "history.notes"), value="\n".join(lines)[:1024], inline=False)

        embed.set_footer(text=t(loc, "history.footer"))
        await reply(ctx, embed=embed, ephemeral=True)

    # -- Moderator notes ------------------------------------------------------

    @commands.hybrid_command(name="note", description="Add a moderator note to a member (never shown to them).")
    @app_commands.describe(member="Member the note is about.", text="The note (mods-only context, max 1000 chars).")
    @has_permission("warn")
    async def note(self, ctx: commands.Context, member: discord.Member, *, text: str):
        text = text.strip()
        if not text:
            return await reply(ctx, "❌ The note can't be empty.", ephemeral=True)
        note_id = await self.bot.db.add_mod_note(
            ctx.guild.id, member.id, text, ctx.author.id, str(ctx.author)
        )
        await reply(ctx, f"📝 Note **#{note_id}** added for {member.mention}.", ephemeral=True)
        logger.info(f"Mod note #{note_id} added for {member} in {ctx.guild.name} by {ctx.author}")

    @commands.hybrid_command(name="notes", description="Show a member's moderator notes.")
    @app_commands.describe(member="Member whose notes to view.")
    @has_permission("warn")
    async def notes(self, ctx: commands.Context, member: discord.Member):
        rows = await self.bot.db.get_mod_notes(ctx.guild.id, member.id)
        if not rows:
            return await reply(ctx, f"No notes for {member.mention}.", ephemeral=True)
        embed = discord.Embed(
            title=f"📝 Notes for {member.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        for r in rows[:15]:
            when = f"<t:{int(r['created_at'].timestamp())}:R>" if r["created_at"] else ""
            embed.add_field(
                name=f"#{r['id']} · {r['author_name'] or '—'} {when}",
                value=r["note"][:1024],
                inline=False,
            )
        if len(rows) > 15:
            embed.set_footer(text=f"Showing 15 of {len(rows)} notes.")
        await reply(ctx, embed=embed, ephemeral=True)

    @commands.hybrid_command(name="delnote", description="Delete a moderator note by its id.")
    @app_commands.describe(note_id="The note id (shown in /notes).")
    @has_permission("warn")
    async def delnote(self, ctx: commands.Context, note_id: int):
        removed = await self.bot.db.delete_mod_note(ctx.guild.id, note_id)
        if not removed:
            return await reply(ctx, f"❌ Note #{note_id} was not found.", ephemeral=True)
        await reply(ctx, f"🗑️ Note #{note_id} deleted.", ephemeral=True)
        logger.info(f"Mod note #{note_id} deleted in {ctx.guild.name} by {ctx.author}")

    # -- Temporary roles ----------------------------------------------------

    def _role_guard(self, ctx: commands.Context, role: discord.Role) -> Optional[str]:
        """Returns an error string if the role can't be assigned here, else None."""
        if role.is_default():
            return "You can't assign @everyone."
        if not role_is_assignable(
            role_managed=role.managed, role_position=role.position,
            bot_top_role_pos=ctx.guild.me.top_role.position,
        ):
            return f"I can't manage {role.mention} — it's managed or above my top role."
        if not ctx.author.guild_permissions.administrator and role >= ctx.author.top_role:
            return f"You can't manage {role.mention} — it's at or above your top role."
        return None

    @commands.hybrid_command(name="temprole", description="Give a member a role that is removed after a duration.")
    @app_commands.describe(
        member="Member to give the role to.",
        role="Role to grant temporarily.",
        duration="Duration (e.g. 30m, 2h, 7d). Max 365d.",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @has_permission("config")
    async def temprole(self, ctx: commands.Context, member: discord.Member, role: discord.Role, duration: str):
        guard = self._role_guard(ctx, role)
        if guard:
            return await reply(ctx, f"❌ {guard}", ephemeral=True)

        seconds = parse_duration(duration)
        if not seconds:
            return await reply(ctx, "❌ Invalid duration. Use e.g. `30m`, `2h`, `7d` (max 365d).", ephemeral=True)

        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
        try:
            await member.add_roles(role, reason=f"Temp role for {format_duration(seconds)} (by {ctx.author})")
        except discord.Forbidden:
            return await reply(ctx, "❌ I couldn't add that role (check my permissions and role order).", ephemeral=True)

        await self.bot.db.add_temp_role(ctx.guild.id, member.id, role.id, expires_at, ctx.author.id)

        embed = discord.Embed(title="⏳ Temporary role granted", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.add_field(name="Removed", value=f"<t:{int(expires_at.timestamp())}:R>", inline=True)
        await reply(ctx, embed=embed)
        logger.info(f"Temp role {role.id} -> {member} for {format_duration(seconds)} in {ctx.guild.name}")

    @commands.hybrid_command(name="temproles", description="List active temporary roles (optionally for one member).")
    @app_commands.describe(member="Only show temp roles for this member (optional).")
    @has_permission("config")
    async def temproles(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        rows = await self.bot.db.get_temp_roles(ctx.guild.id, user_id=member.id if member else None)
        if not rows:
            return await reply(ctx, "No active temporary roles.", ephemeral=True)

        embed = discord.Embed(title="⏳ Active temporary roles", color=discord.Color.blurple())
        for r in rows[:20]:
            when = f"<t:{int(r['expires_at'].timestamp())}:R>" if r["expires_at"] else "—"
            embed.add_field(
                name=f"<@{r['user_id']}>",
                value=f"<@&{r['role_id']}> · removed {when}",
                inline=False,
            )
        await reply(ctx, embed=embed, ephemeral=True)

    # -- Bulk actions -------------------------------------------------------

    @commands.hybrid_command(name="massban", description="Ban multiple users by ID/mention (max 20).")
    @app_commands.describe(users="User IDs or mentions, space/comma separated.", reason="Reason for the bans.")
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    @has_permission("ban")
    async def massban(self, ctx: commands.Context, users: str, *, reason: str = "Mass ban"):
        ids = parse_id_list(users, limit=MAX_BULK)
        ids = [i for i in ids if i not in (ctx.author.id, self.bot.user.id)]
        if not ids:
            return await reply(ctx, "❌ No valid user IDs found (max 20).", ephemeral=True)

        view = ConfirmView(ctx.author.id)
        await reply(ctx, f"⚠️ Ban **{len(ids)}** user(s)? This can't be undone in bulk.", view=view, ephemeral=True)
        await view.wait()
        if not view.value:
            return

        ok, failed = 0, 0
        for uid in ids:
            try:
                await ctx.guild.ban(discord.Object(id=uid), reason=f"{reason} | Mass ban by {ctx.author}")
                ok += 1
                try:
                    await self.bot.db.add_mod_case(
                        ctx.guild.id, "🔨 Mass Ban", uid, str(uid), ctx.author.id, str(ctx.author), reason
                    )
                except Exception as e:
                    # The ban went through; don't fail the batch if only the
                    # case record didn't persist — but don't hide it either.
                    logger.warning(f"Mass ban: failed to record case for {uid}: {e}")
            except (discord.Forbidden, discord.HTTPException):
                failed += 1

        await reply(ctx, f"✅ Banned **{ok}**" + (f", failed **{failed}**" if failed else "") + ".", ephemeral=True)
        logger.info(f"Mass ban by {ctx.author} in {ctx.guild.name}: {ok} ok, {failed} failed")

    @commands.hybrid_command(name="massrole", description="Add or remove a role for many members at once (max 20).")
    @app_commands.describe(
        action="add or remove.",
        role="Role to add or remove.",
        users="User IDs or mentions, space/comma separated.",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    @has_permission("config")
    async def massrole(
        self, ctx: commands.Context, action: Literal["add", "remove"], role: discord.Role, users: str
    ):
        guard = self._role_guard(ctx, role)
        if guard:
            return await reply(ctx, f"❌ {guard}", ephemeral=True)

        ids = parse_id_list(users, limit=MAX_BULK)
        if not ids:
            return await reply(ctx, "❌ No valid user IDs found (max 20).", ephemeral=True)

        ok, skipped = 0, 0
        for uid in ids:
            member = ctx.guild.get_member(uid)
            if member is None:
                skipped += 1
                continue
            try:
                if action == "add":
                    await member.add_roles(role, reason=f"Mass role by {ctx.author}")
                else:
                    await member.remove_roles(role, reason=f"Mass role by {ctx.author}")
                ok += 1
            except (discord.Forbidden, discord.HTTPException):
                skipped += 1

        verb = "Added" if action == "add" else "Removed"
        await reply(
            ctx,
            f"✅ {verb} {role.mention} for **{ok}** member(s)" + (f", skipped **{skipped}**" if skipped else "") + ".",
            ephemeral=True,
        )
        logger.info(f"Mass role {action} {role.id} by {ctx.author} in {ctx.guild.name}: {ok} ok, {skipped} skipped")


async def setup(bot: commands.Bot):
    await bot.add_cog(ModToolsCog(bot))
