# cogs/help_cog.py
import discord
from discord.ext import commands
from discord import app_commands
from core.i18n import t
from .utils import reply


# Cog → the feature toggle that governs it. /help marks a category as off when
# its feature is disabled for the guild: the commands still list (so an admin
# can find them), but nobody wonders why /rank does nothing.
COG_FEATURE = {
    "🚨 Anti-Raid": "anti-raid",
    "🛡️ AutoMod": "automod",
    "🚫 Filter": "automod",  # the word filter lives inside AutoMod now
    "⭐ Levels": "levels",
    "Reaction Roles": "reaction-menus",
    "📅 Scheduled Messages": "scheduled-messages",
    "🎫 Tickets": "tickets",
    "✅ Verification": "verification",
    "👋 Welcome System": "welcome-message",
}


def _visible_cogs(bot: commands.Bot):
    """Cogs that expose at least one non-hidden command, sorted by name."""
    cogs = [
        cog
        for cog in bot.cogs.values()
        if any(not cmd.hidden for cmd in cog.get_commands())
    ]
    return sorted(cogs, key=lambda c: c.qualified_name)


def build_main_embed(bot: commands.Bot, loc: str, enabled_features=None) -> discord.Embed:
    """The overview page listing every command category."""
    embed = discord.Embed(
        title=t(loc, "help.title"),
        description=t(loc, "help.desc"),
        color=discord.Color.blue()
    )
    disabled_any = False
    for cog in _visible_cogs(bot):
        commands_list = sorted(cmd.name for cmd in cog.get_commands() if not cmd.hidden)
        if not commands_list:
            continue
        name = cog.qualified_name
        feature = COG_FEATURE.get(name)
        if enabled_features is not None and feature and feature not in enabled_features:
            name = f"{name} · {t(loc, 'help.feature_off')}"
            disabled_any = True
        embed.add_field(
            name=name,
            value=f"`{'`, `'.join(commands_list)}`",
            inline=False
        )
    if disabled_any:
        embed.set_footer(text=t(loc, "help.feature_off_note"))
    return embed


def build_cog_embed(cog: commands.Cog, loc: str, enabled_features=None) -> discord.Embed:
    """The detail page for a single category."""
    description = cog.description or t(loc, "help.no_cat_desc")
    feature = COG_FEATURE.get(cog.qualified_name)
    off = enabled_features is not None and feature and feature not in enabled_features
    if off:
        description = f"{t(loc, 'help.feature_off_note')}\n\n{description}"
    embed = discord.Embed(
        title=t(loc, "help.cog_title", cog=cog.qualified_name),
        description=description,
        color=discord.Color.dark_grey() if off else discord.Color.green()
    )
    visible_commands = sorted(
        (cmd for cmd in cog.get_commands() if not cmd.hidden),
        key=lambda c: c.name,
    )
    for cmd in visible_commands:
        # All user-facing commands are slash commands.
        signature = f"/{cmd.name} {cmd.signature}".strip()
        embed.add_field(name=f"`{signature}`", value=cmd.short_doc or t(loc, "help.no_desc"), inline=False)
    return embed


class HelpView(discord.ui.View):
    """A category dropdown that swaps the help embed in place. Only the member
    who invoked /help can drive it; it self-disables after a short timeout."""

    def __init__(self, bot: commands.Bot, author_id: int, loc: str,
                 enabled_features=None, *, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.author_id = author_id
        self.loc = loc
        self.enabled_features = enabled_features
        self._message: discord.Message | None = None

        select = discord.ui.Select(placeholder=t(loc, "help.select_placeholder"), min_values=1, max_values=1)
        select.add_option(
            label=t(loc, "help.overview_label"),
            value="__overview__",
            description=t(loc, "help.overview_desc"),
            emoji="🏠",
        )
        for cog in _visible_cogs(bot):
            # qualified_name is like "🛡️ Moderation" — keep it as the label so the
            # category emoji shows without us having to parse it out.
            label = cog.qualified_name[:100]
            select.add_option(
                label=label,
                value=cog.qualified_name,
                description=(cog.description or "")[:100] or None,
            )
        select.callback = self._on_select
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                t(self.loc, "help.not_yours"),
                ephemeral=True,
            )
            return False
        return True

    async def _on_select(self, interaction: discord.Interaction):
        value = interaction.data["values"][0]
        if value == "__overview__":
            embed = build_main_embed(self.bot, self.loc, self.enabled_features)
        else:
            cog = self.bot.get_cog(value)
            embed = (
                build_cog_embed(cog, self.loc, self.enabled_features)
                if cog else build_main_embed(self.bot, self.loc, self.enabled_features)
            )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self._message is not None:
            try:
                await self._message.edit(view=self)
            except discord.HTTPException:
                pass


class HelpCog(commands.Cog, name="❓ Help"):
    """Provides a detailed and organized help command focusing on Slash Commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _locale(self, ctx: commands.Context) -> str:
        return await self.bot.db.get_locale(ctx.guild.id) if ctx.guild else "en"

    async def _enabled(self, ctx: commands.Context):
        """The guild's enabled features, or None in DMs / without a DB — None
        means "don't mark anything as off"."""
        if not ctx.guild or not self.bot.db:
            return None
        try:
            return await self.bot.db.get_enabled_features(ctx.guild.id)
        except Exception:
            return None

    async def _help_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Suggests category names and command names for /help <query>."""
        current = current.lower()
        choices: list[app_commands.Choice[str]] = []
        for cog in _visible_cogs(self.bot):
            if current in cog.qualified_name.lower():
                choices.append(app_commands.Choice(name=cog.qualified_name, value=cog.qualified_name))
            for cmd in cog.get_commands():
                if cmd.hidden:
                    continue
                if current in cmd.qualified_name.lower():
                    choices.append(
                        app_commands.Choice(name=f"/{cmd.qualified_name}", value=cmd.qualified_name)
                    )
        return choices[:25]

    @commands.hybrid_command(name="help", description="Shows information about commands and categories.")
    @app_commands.describe(query="A category or command to get details on. Leave empty for the menu.")
    @app_commands.autocomplete(query=_help_autocomplete)
    async def help(self, ctx: commands.Context, *, query: str = None):
        """Shows a list of command categories, or details for a specific category/command."""
        if not query:
            await self.send_main_help(ctx)
        else:
            await self.send_specific_help(ctx, query)

    async def send_main_help(self, ctx: commands.Context):
        """Sends the interactive main help page with a category dropdown."""
        loc = await self._locale(ctx)
        enabled = await self._enabled(ctx)
        embed = build_main_embed(self.bot, loc, enabled)
        view = HelpView(self.bot, ctx.author.id, loc, enabled)
        await reply(ctx, embed=embed, ephemeral=True, view=view)
        # Capture the sent message so the view can disable itself on timeout.
        if ctx.interaction is not None:
            try:
                view._message = await ctx.interaction.original_response()
            except discord.HTTPException:
                pass

    async def send_specific_help(self, ctx: commands.Context, query: str):
        """Sends help for a specific command or cog."""
        query_lower = query.lower()

        # Check if query is a cog
        for cog in self.bot.cogs.values():
            if query_lower == cog.qualified_name.lower():
                await self.send_cog_help(ctx, cog)
                return

        # Check if query is a command
        command = self.bot.get_command(query_lower)
        if command and not command.hidden:
            await self.send_command_help(ctx, command)
            return

        loc = await self._locale(ctx)
        await reply(ctx, content=t(loc, "help.not_found", query=query), ephemeral=True)

    async def send_cog_help(self, ctx: commands.Context, cog: commands.Cog):
        """Sends help for a specific cog (category)."""
        loc = await self._locale(ctx)
        embed = build_cog_embed(cog, loc, await self._enabled(ctx))
        await reply(ctx, embed=embed, ephemeral=True)

    async def send_command_help(self, ctx: commands.Context, command: commands.Command):
        """Sends detailed help for a specific command."""
        loc = await self._locale(ctx)
        embed = discord.Embed(
            title=t(loc, "help.cmd_title", command=command.name),
            description=command.help or command.short_doc or t(loc, "help.no_desc_available"),
            color=discord.Color.gold()
        )
        signature = f"/{command.qualified_name} {command.signature}".strip()
        embed.add_field(name=t(loc, "help.usage"), value=f"```\n{signature}\n```", inline=False)

        if isinstance(command, (commands.HybridGroup, commands.Group)):
            subcommands = sorted([sub for sub in command.commands if not sub.hidden], key=lambda c: c.name)
            if subcommands:
                sub_list = "\n".join([f"**`/{sub.qualified_name}`** - {sub.short_doc}" for sub in subcommands])
                embed.add_field(name=t(loc, "help.subcommands"), value=sub_list, inline=False)
        await reply(ctx, embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    bot.remove_command("help")
    await bot.add_cog(HelpCog(bot))
