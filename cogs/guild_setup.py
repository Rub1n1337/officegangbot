# cogs/guild_setup.py
import discord
from discord.ext import commands
from core.logger import logger
from core.i18n import t

from cogs.utils import reply

DEFAULT_WELCOME_MESSAGE = "Welcome {user.mention} to **{server.name}**! We're glad to have you."

# Internal data key -> guilds column. The "edited/deleted messages" log is
# stored in the audit_log_id column (kept identical to the old text wizard).
SETTING_COLUMNS = {
    "rules_channel_id": "rules_channel_id",
    "welcome_message": "welcome_message",
    "punishment_log_id": "punishment_log_id",
    "usage_log_id": "usage_log_id",
    "message_log_id": "audit_log_id",
    "leave_log_id": "leave_log_id",
}

# (internal data key, i18n label key)
LOG_FIELDS = [
    ("punishment_log_id", "setup.log_punishments"),
    ("usage_log_id", "setup.log_usage"),
    ("message_log_id", "setup.log_messages"),
    ("leave_log_id", "setup.log_leaves"),
]


def _channel_value(loc: str, data: dict, key: str) -> str:
    cid = data.get(key)
    return f"<#{cid}>" if cid else t(loc, "setup.not_set")


class _PickChannelSelect(discord.ui.ChannelSelect):
    """Single text-channel picker that writes one field then returns to the panel."""

    def __init__(self, field: str, placeholder: str):
        super().__init__(
            channel_types=[discord.ChannelType.text],
            placeholder=placeholder,
            min_values=1,
            max_values=1,
        )
        self.field = field

    async def callback(self, interaction: discord.Interaction):
        panel: "SetupView" = self.view.panel  # type: ignore[attr-defined]
        panel.data[self.field] = self.values[0].id
        await panel.show_main(interaction)


class _LogChannelSelect(discord.ui.ChannelSelect):
    """One log-channel picker; stays on the logs sub-panel so several can be set."""

    def __init__(self, field: str, label: str):
        super().__init__(
            channel_types=[discord.ChannelType.text],
            placeholder=label,
            min_values=1,
            max_values=1,
        )
        self.field = field

    async def callback(self, interaction: discord.Interaction):
        sub: "LogsView" = self.view  # type: ignore[assignment]
        sub.panel.data[self.field] = self.values[0].id
        await interaction.response.edit_message(embed=sub.embed(), view=sub)


class _BackButton(discord.ui.Button):
    def __init__(self, loc: str):
        super().__init__(label=t(loc, "setup.back"), style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction):
        await self.view.panel.show_main(interaction)  # type: ignore[attr-defined]


class RulesChannelView(discord.ui.View):
    def __init__(self, panel: "SetupView"):
        super().__init__(timeout=panel.timeout)
        self.panel = panel
        self.add_item(_PickChannelSelect("rules_channel_id", t(panel.loc, "setup.rules_placeholder")))
        self.add_item(_BackButton(panel.loc))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await self.panel.interaction_check(interaction)


class LogsView(discord.ui.View):
    def __init__(self, panel: "SetupView"):
        super().__init__(timeout=panel.timeout)
        self.panel = panel
        for field, label_key in LOG_FIELDS:
            self.add_item(_LogChannelSelect(field, t(panel.loc, label_key)))
        self.add_item(_BackButton(panel.loc))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await self.panel.interaction_check(interaction)

    def embed(self) -> discord.Embed:
        loc = self.panel.loc
        embed = discord.Embed(
            title=t(loc, "setup.logs_title"),
            description=t(loc, "setup.logs_desc"),
            color=discord.Color.blurple(),
        )
        for field, label_key in LOG_FIELDS:
            embed.add_field(name=t(loc, label_key), value=_channel_value(loc, self.panel.data, field), inline=False)
        return embed


class WelcomeModal(discord.ui.Modal):
    def __init__(self, panel: "SetupView"):
        super().__init__(title=t(panel.loc, "setup.welcome_modal_title"))
        self.panel = panel
        self.message = discord.ui.TextInput(
            label=t(panel.loc, "setup.welcome_input_label"),
            style=discord.TextStyle.paragraph,
            default=panel.data.get("welcome_message") or DEFAULT_WELCOME_MESSAGE,
            max_length=1000,
            required=True,
            placeholder=t(panel.loc, "setup.welcome_input_placeholder"),
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        self.panel.data["welcome_message"] = self.message.value.strip()
        await self.panel.show_main(interaction)


class SetupView(discord.ui.View):
    """The main interactive setup panel. Nothing is persisted until Save."""

    def __init__(self, bot: commands.Bot, guild_id: int, author_id: int, loc: str, *, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.author_id = author_id
        self.loc = loc
        self.data: dict = {}
        self.message: discord.Message | None = None
        # Localize button labels (decorator labels are the fallback).
        self.rules_button.label = t(loc, "setup.btn_rules")
        self.welcome_button.label = t(loc, "setup.btn_welcome")
        self.logs_button.label = t(loc, "setup.btn_logs")
        self.save_button.label = t(loc, "setup.btn_save")
        self.cancel_button.label = t(loc, "setup.btn_cancel")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(t(self.loc, "setup.not_yours"), ephemeral=True)
            return False
        return True

    def main_embed(self) -> discord.Embed:
        loc = self.loc
        embed = discord.Embed(
            title=t(loc, "setup.title"),
            description=t(loc, "setup.desc"),
            color=discord.Color.blurple(),
        )
        embed.add_field(name=t(loc, "setup.field_rules"), value=_channel_value(loc, self.data, "rules_channel_id"), inline=True)
        welcome = self.data.get("welcome_message")
        embed.add_field(
            name=t(loc, "setup.field_welcome"),
            value=(f"`{welcome[:60]}`" if welcome else t(loc, "setup.welcome_default")),
            inline=True,
        )
        embed.add_field(
            name=t(loc, "setup.field_logs"),
            value="\n".join(
                f"{t(loc, label_key)}: {_channel_value(loc, self.data, field)}"
                for field, label_key in LOG_FIELDS
            ),
            inline=False,
        )
        return embed

    async def show_main(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.main_embed(), view=self)

    @discord.ui.button(label="Rules Channel", emoji="📋", style=discord.ButtonStyle.secondary, row=0)
    async def rules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RulesChannelView(self)
        embed = discord.Embed(
            title=t(self.loc, "setup.rules_title"),
            description=t(self.loc, "setup.rules_desc"),
            color=discord.Color.blurple(),
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Welcome Message", emoji="👋", style=discord.ButtonStyle.secondary, row=0)
    async def welcome_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WelcomeModal(self))

    @discord.ui.button(label="Log Channels", emoji="🪵", style=discord.ButtonStyle.secondary, row=0)
    async def logs_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LogsView(self)
        await interaction.response.edit_message(embed=view.embed(), view=view)

    @discord.ui.button(label="Save", emoji="💾", style=discord.ButtonStyle.success, row=1)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.bot.db:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title=t(self.loc, "setup.fail_title"),
                    description=t(self.loc, "setup.fail_db"),
                    color=discord.Color.red(),
                ),
                view=None,
            )
            self.stop()
            return
        try:
            for key, column in SETTING_COLUMNS.items():
                value = self.data.get(key)
                if value is not None:
                    await self.bot.db.set_guild_setting(self.guild_id, column, value)
        except Exception as e:
            logger.error(f"Setup save failed for guild {self.guild_id}: {e}", exc_info=True)
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title=t(self.loc, "setup.fail_title"),
                    description=t(self.loc, "setup.fail_save"),
                    color=discord.Color.red(),
                ),
                view=None,
            )
            self.stop()
            return

        summary = self.main_embed()
        summary.title = t(self.loc, "setup.done_title")
        summary.color = discord.Color.green()
        summary.description = t(self.loc, "setup.done_desc")
        await interaction.response.edit_message(embed=summary, view=None)
        logger.info(f"Setup completed for guild {self.guild_id} by {self.author_id}.")
        self.stop()

    @discord.ui.button(label="Cancel", emoji="✖️", style=discord.ButtonStyle.danger, row=1)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=t(self.loc, "setup.cancelled_title"),
                description=t(self.loc, "setup.cancelled_desc"),
                color=discord.Color.greyple(),
            ),
            view=None,
        )
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class SetupCog(commands.Cog, name="🛠️ Server Setup"):
    """Interactive, button-driven server setup for admins (rules, welcome, logs)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        logger.info(f"Joined new guild: {guild.name} ({guild.id}).")
        channel = next(
            (ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages),
            None,
        )
        if not channel:
            return
        # Locale defaults to English at join time (nothing configured yet).
        embed = discord.Embed(
            title=f"👋 Hello, {guild.name}!",
            description="Thanks for adding me! To get started, an administrator should run "
                        "the setup command.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="🚀 Setup Command", value="```/setup```", inline=False)
        await channel.send(embed=embed)

    @commands.hybrid_command(name="setup", description="Interactive server setup.")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def setup(self, ctx: commands.Context):
        """Opens an interactive panel to configure rules, welcome and log channels."""
        if not ctx.guild:
            return await reply(ctx, t("en", "setup.guild_only"), ephemeral=True)

        loc = await self.bot.db.get_locale(ctx.guild.id)
        view = SetupView(self.bot, ctx.guild.id, ctx.author.id, loc)
        embed = view.main_embed()

        # The global auto-defer has already acked the interaction ephemerally, so
        # the panel is sent as an ephemeral followup (admin-only). Falls back to a
        # channel message for the rare prefix invocation.
        if ctx.interaction is not None:
            view.message = await ctx.interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            view.message = await ctx.channel.send(embed=embed, view=view)

    @setup.error
    async def setup_error(self, ctx: commands.Context, error: commands.CommandError):
        """Error handler specific to the setup command."""
        loc = "en"
        if ctx.guild and self.bot.db:
            try:
                loc = await self.bot.db.get_locale(ctx.guild.id)
            except Exception:
                loc = "en"
        if isinstance(error, commands.CheckFailure):
            await reply(ctx, t(loc, "setup.err_no_admin"), ephemeral=True)
        elif isinstance(error, commands.NoPrivateMessage):
            pass
        else:
            logger.error(f"Unexpected setup error for guild {getattr(ctx.guild, 'id', None)}:", exc_info=error)
            await reply(ctx, t(loc, "setup.err_unexpected"), ephemeral=True)


async def setup(bot: commands.Bot):
    """This function is required by discord.py to load the cog."""
    await bot.add_cog(SetupCog(bot))
