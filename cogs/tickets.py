# cogs/tickets.py
import discord
from discord.ext import commands, tasks
from discord import app_commands
from core.logger import logger
from core.i18n import t
from core.tickets import build_transcript, normalize_priority, PRIORITY_LABELS
from core.guild_context import GuildContext
from core.discord_utils import safe_send
from .utils import reply
from typing import Optional
import asyncio
import datetime
import io
import re


async def _can_manage_ticket(interaction: discord.Interaction) -> bool:
    """True if the user may act on this ticket: server manage_channels, the
    configured support role, or the ticket's opener. Replies with a no-perm
    message and returns False otherwise."""
    bot = interaction.client
    guild = interaction.guild
    user = interaction.user

    if user.guild_permissions.manage_channels:
        return True

    support_role_id = await bot.db.get_guild_setting(guild.id, 'ticket_support_role_id')
    if support_role_id:
        role = guild.get_role(int(support_role_id))
        if role and role in user.roles:
            return True

    ticket = await bot.db.get_open_ticket_by_channel(interaction.channel.id)
    if ticket and int(ticket["opener_id"]) == user.id:
        return True

    loc = await bot.db.get_locale(guild.id)
    if not interaction.response.is_done():
        await interaction.response.send_message(t(loc, "tickets.close_no_perm"), ephemeral=True)
    return False


async def _capture_transcript(channel: discord.TextChannel, guild: discord.Guild) -> str:
    """Reads the channel's message history (oldest first) into a plain-text
    transcript. Best-effort: returns whatever could be read."""
    entries = []
    incomplete = False
    try:
        async for msg in channel.history(limit=500, oldest_first=True):
            content = msg.content or ("[embed]" if msg.embeds else "")
            entries.append({
                "timestamp": msg.created_at.strftime("%Y-%m-%d %H:%M"),
                "author": f"{msg.author} ({msg.author.id})",
                "content": content,
                "attachments": [a.url for a in msg.attachments],
            })
    except discord.HTTPException as e:
        incomplete = True
        logger.warning(f"Transcript capture incomplete for channel {channel.id}: {e}")
    header = f"Transcript — #{channel.name} — {guild.name}"
    if incomplete:
        header += " [INCOMPLETE — some messages could not be retrieved]"
    return build_transcript(entries, header)


async def _notify_opener(bot, guild, ticket, comment, transcript, loc):
    """DMs the ticket opener that their ticket was closed, with the closing
    comment and the transcript attached. Silently ignored if DMs are closed."""
    opener_id = int(ticket["opener_id"])
    user = guild.get_member(opener_id) or bot.get_user(opener_id)
    if user is None:
        try:
            user = await bot.fetch_user(opener_id)
        except discord.HTTPException:
            return

    embed = discord.Embed(
        title=t(loc, "tickets.closed_dm_title"),
        description=t(loc, "tickets.closed_dm_desc", guild=guild.name),
        color=discord.Color.blurple(),
    )
    if comment:
        embed.add_field(name=t(loc, "tickets.close_comment_field"), value=comment[:1024], inline=False)

    file = None
    if transcript:
        file = discord.File(io.BytesIO(transcript.encode("utf-8")), filename=f"transcript-{ticket['id']}.txt")
    await safe_send(user, embed=embed, file=file)


async def _close_channel(bot, guild, channel, closer_id, closer_name, comment, loc):
    """Core close flow: capture the transcript, persist, notify the opener and
    delete the channel. Shared by the close modal and the auto-close loop."""
    transcript = await _capture_transcript(channel, guild)
    ticket = await bot.db.close_ticket(channel.id, closer_id, closer_name, comment, transcript)
    if ticket:
        await _notify_opener(bot, guild, ticket, comment, transcript, loc)

    await asyncio.sleep(3)
    try:
        await channel.delete(reason=f"Ticket closed by {closer_name}")
        logger.info(f"Ticket channel {channel.name} closed by {closer_name}")
    except discord.Forbidden:
        await safe_send(channel, t(loc, "tickets.close_no_delete_perm"))
    except discord.NotFound:
        pass
    return ticket


async def _finalize_close(interaction: discord.Interaction, comment: Optional[str]):
    """Close flow from the close modal: acks the interaction, then runs the
    shared close."""
    bot = interaction.client
    guild = interaction.guild
    channel = interaction.channel
    loc = await bot.db.get_locale(guild.id)

    await interaction.response.send_message(t(loc, "tickets.closing"), ephemeral=False)
    await _close_channel(bot, guild, channel, interaction.user.id, str(interaction.user), comment, loc)


class CloseTicketModal(discord.ui.Modal):
    """Prompts the closer for an optional comment sent to the ticket owner."""

    def __init__(self, loc: Optional[str] = None):
        self._loc = loc or "en"
        super().__init__(title=t(self._loc, "tickets.close_modal_title"), timeout=300)
        self.comment = discord.ui.TextInput(
            label=t(self._loc, "tickets.close_comment_label"),
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            placeholder=t(self._loc, "tickets.close_comment_ph"),
        )
        self.add_item(self.comment)

    async def on_submit(self, interaction: discord.Interaction):
        await _finalize_close(interaction, (self.comment.value or "").strip() or None)


class TicketControlView(discord.ui.View):
    """Persistent controls inside a ticket channel: a priority selector and a
    close button. Only the opener, support role or admins can use them."""

    def __init__(self, loc: Optional[str] = None):
        super().__init__(timeout=None)
        # Persistent view registered at startup has no locale (labels there are
        # only used to re-bind handlers by custom_id). When a ticket is opened we
        # post a fresh view with the guild's locale so labels are translated.
        if loc:
            self.close_ticket.label = t(loc, "tickets.close_button")
            self.set_priority.placeholder = t(loc, "tickets.priority_placeholder")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await _can_manage_ticket(interaction)

    @discord.ui.select(
        placeholder="Set priority…",
        custom_id="ticket_priority",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Low", value="low", emoji="🟢"),
            discord.SelectOption(label="Medium", value="medium", emoji="🟡"),
            discord.SelectOption(label="High", value="high", emoji="🟠"),
            discord.SelectOption(label="Urgent", value="urgent", emoji="🔴"),
        ],
    )
    async def set_priority(self, interaction: discord.Interaction, select: discord.ui.Select):
        bot = interaction.client
        loc = await bot.db.get_locale(interaction.guild.id)
        value = normalize_priority(select.values[0])
        ok = await bot.db.set_ticket_priority(interaction.channel.id, value)
        if ok:
            await interaction.response.send_message(
                t(loc, "tickets.priority_set", priority=PRIORITY_LABELS[value], user=interaction.user.mention),
                ephemeral=False,
            )
        else:
            await interaction.response.send_message(t(loc, "tickets.priority_no_ticket"), ephemeral=True)

    @discord.ui.button(
        label="🔒 Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="close_ticket",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        loc = await interaction.client.db.get_locale(interaction.guild.id)
        await interaction.response.send_modal(CloseTicketModal(loc))


class OpenTicketView(discord.ui.View):
    """Persistent view with an open ticket button."""

    def __init__(self, loc: Optional[str] = None):
        super().__init__(timeout=None)
        if loc:
            self.open_ticket.label = t(loc, "tickets.open_button")

    @discord.ui.button(
        label="📩 Open Ticket",
        style=discord.ButtonStyle.primary,
        custom_id="open_ticket"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        bot = interaction.client
        # locale + enabled features + settings in one bundled read.
        ctx = await GuildContext.load(bot.db, guild.id)
        loc = ctx.locale

        # The dashboard toggle controls the ticket system via enabled_features.
        if not ctx.is_enabled("tickets"):
            await interaction.response.send_message(
                t(loc, "tickets.disabled"), ephemeral=True
            )
            return

        # Sanitize channel name for Unicode safety
        clean_name = re.sub(r'[^a-z0-9-]', '', member.name.lower()) or str(member.id)
        channel_name = f"ticket-{clean_name}-{member.id}"

        # Check if ticket already exists
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            await interaction.response.send_message(
                t(loc, "tickets.already_open", channel=existing.mention),
                ephemeral=True
            )
            return

        # Get support role from settings
        support_role_id = ctx.setting('ticket_support_role_id')
        support_role = guild.get_role(int(support_role_id)) if support_role_id else None

        # Get ticket category
        category_id = ctx.setting('ticket_category_id')
        category = guild.get_channel(int(category_id)) if category_id else None

        # Set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            )

        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=category,
                reason=f"Ticket opened by {member}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                t(loc, "tickets.no_create_perm"),
                ephemeral=True
            )
            return

        # Record the ticket so its priority, closer, comment and transcript can
        # be persisted (and surfaced on the dashboard) across the channel's life.
        try:
            await bot.db.create_ticket(guild.id, channel.id, member.id, str(member))
        except Exception as e:
            logger.exception(f"Failed to record ticket for {member} in {guild.name}: {e}")

        # Send ticket message
        embed = discord.Embed(
            title=t(loc, "tickets.channel_title"),
            description=t(loc, "tickets.channel_desc", member=member.mention),
            color=discord.Color.blurple()
        )
        embed.set_footer(text=t(loc, "tickets.channel_footer", member=member), icon_url=member.display_avatar.url)

        await channel.send(
            content=f"{member.mention}" + (f" | {support_role.mention}" if support_role else ""),
            embed=embed,
            view=TicketControlView(loc)
        )

        await interaction.response.send_message(
            t(loc, "tickets.created", channel=channel.mention),
            ephemeral=True
        )
        logger.info(f"Ticket opened by {member} in {guild.name}: #{channel.name}")


class TicketsCog(commands.Cog, name="🎫 Tickets"):
    """Ticket support system with persistent buttons."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Register persistent views (default labels; only used to re-bind handlers
        # by custom_id after a restart — displayed labels come from posted views).
        bot.add_view(OpenTicketView())
        bot.add_view(TicketControlView())
        # Channels whose subject is already captured (or checked) this session,
        # so the on_message listener doesn't query the DB per message.
        self._subject_done: set[int] = set()
        self.auto_close_loop.start()

    def cog_unload(self):
        self.auto_close_loop.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Captures the opener's first message as the ticket subject (shown in
        the dashboard's ticket list). Cheap guard: ticket channels are named
        ticket-*, and each channel is checked at most once per session."""
        if (
            message.author.bot
            or not message.guild
            or not self.bot.db
            or not isinstance(message.channel, discord.TextChannel)
            or not message.channel.name.startswith("ticket-")
            or message.channel.id in self._subject_done
        ):
            return
        ticket = await self.bot.db.get_open_ticket_by_channel(message.channel.id)
        if ticket is None:
            self._subject_done.add(message.channel.id)
            return
        if ticket.get("subject"):
            self._subject_done.add(message.channel.id)
            return
        if int(ticket["opener_id"]) != message.author.id:
            return  # wait for the opener's own first message
        text = (message.content or "").strip()
        if not text:
            return  # attachments-only message — wait for text
        await self.bot.db.set_ticket_subject(message.channel.id, text)
        self._subject_done.add(message.channel.id)

    async def _close_orphaned_record(self, guild_id: int, channel_id: int):
        """Closes the DB record for a ticket whose channel no longer exists —
        it can never be closed from inside the channel, so without this it sits
        "open" in the dashboard forever. No transcript and no opener DM: the
        channel (and its history) is already gone."""
        loc = await self.bot.db.get_locale(guild_id)
        ticket = await self.bot.db.close_ticket(
            channel_id, self.bot.user.id, "System",
            t(loc, "tickets.channel_deleted_comment"), None,
        )
        if ticket:
            logger.info(f"Closed ticket record #{ticket['id']} — channel {channel_id} was deleted (guild {guild_id})")
        return ticket

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """A manually deleted ticket channel leaves its record stuck open —
        close it as soon as the deletion happens."""
        if not self.bot.db or not isinstance(channel, discord.TextChannel):
            return
        try:
            await self._close_orphaned_record(channel.guild.id, channel.id)
        except Exception as e:
            logger.exception(f"Failed to close ticket record for deleted channel {channel.id}: {e}")

    @staticmethod
    async def _channel_last_activity(channel: discord.TextChannel, opened_at):
        """Best-effort last-activity time for a ticket channel: derived from the
        last message's snowflake (no fetch), falling back to a history read, then
        the ticket's open time."""
        last_id = channel.last_message_id
        if last_id:
            return discord.utils.snowflake_time(last_id)
        try:
            async for m in channel.history(limit=1):
                return m.created_at
        except discord.HTTPException:
            pass
        return opened_at

    @tasks.loop(minutes=15)
    async def auto_close_loop(self):
        """Closes open tickets that have been idle beyond their guild's
        configured auto-close threshold."""
        try:
            if not self.bot.db:
                return
            candidates = await self.bot.db.get_autoclose_candidates()
            now = datetime.datetime.now(datetime.timezone.utc)
            for c in candidates:
                hours = int(c["hours"])
                channel = self.bot.get_channel(int(c["channel_id"]))
                if channel is None:
                    # Not in cache — confirm whether it still exists before
                    # touching the record.
                    try:
                        channel = await self.bot.fetch_channel(int(c["channel_id"]))
                    except discord.NotFound:
                        # Deleted (e.g. while the bot was offline, so the
                        # delete event was missed) — close the stuck record.
                        await self._close_orphaned_record(int(c["guild_id"]), int(c["channel_id"]))
                        continue
                    except (discord.Forbidden, discord.HTTPException):
                        continue  # can't verify — leave the record alone
                if not isinstance(channel, discord.TextChannel):
                    continue  # not visible / wrong type; leave the record alone
                last_activity = await self._channel_last_activity(channel, c["opened_at"])
                if last_activity is None:
                    continue
                idle_hours = (now - last_activity).total_seconds() / 3600.0
                if idle_hours < hours:
                    continue
                loc = await self.bot.db.get_locale(int(c["guild_id"]))
                await safe_send(channel, t(loc, "tickets.auto_closed_notice", hours=hours))
                await _close_channel(
                    self.bot, channel.guild, channel, self.bot.user.id, "Auto-close",
                    t(loc, "tickets.auto_close_comment", hours=hours), loc,
                )
                logger.info(f"Auto-closed idle ticket #{channel.name} in {channel.guild.name}")
        except Exception as e:
            logger.error(f"Ticket auto-close loop crashed: {e}", exc_info=True)

    @auto_close_loop.before_loop
    async def before_auto_close(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="ticket_setup", description="Send the ticket panel to a channel.")
    @app_commands.describe(
        channel="Channel to send the ticket panel to.",
        support_role="Role that can see and respond to tickets.",
        category="Category to create ticket channels in."
    )
    @commands.has_permissions(manage_guild=True)
    async def ticket_setup(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        support_role: Optional[discord.Role] = None,
        category: Optional[discord.CategoryChannel] = None
    ):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        # Save settings
        if support_role:
            await self.bot.db.set_guild_setting(ctx.guild.id, 'ticket_support_role_id', support_role.id)

        if category:
            await self.bot.db.set_guild_setting(ctx.guild.id, 'ticket_category_id', category.id)

        embed = discord.Embed(
            title=t(loc, "tickets.panel_title"),
            description=t(loc, "tickets.panel_desc"),
            color=discord.Color.blurple()
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

        try:
            await channel.send(embed=embed, view=OpenTicketView(loc))
            await reply(ctx, t(loc, "tickets.setup_sent", channel=channel.mention), ephemeral=True)
            logger.info(f"Ticket panel set up in #{channel.name} by {ctx.author} in {ctx.guild.name}")
        except discord.Forbidden:
            await reply(ctx, t(loc, "tickets.setup_no_perm"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
