# cogs/help_cog.py
import discord
from discord.ext import commands
from .utils import reply

class HelpCog(commands.Cog, name="❓ Help"):
    """Provides a detailed and organized help command focusing on Slash Commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Shows information about commands and categories.")
    async def help(self, ctx: commands.Context, *, query: str = None):
        """Shows a list of command categories, or details for a specific category/command."""
        if not query:
            await self.send_main_help(ctx)
        else:
            await self.send_specific_help(ctx, query)

    async def send_main_help(self, ctx: commands.Context):
        """Sends the main help page with all command categories."""
        embed = discord.Embed(
            title="Bot Help Desk",
            description="All commands are available as **Slash Commands** (`/`).\n"
                        "Use `/help <category>` or `/help <command>` for more details.",
            color=discord.Color.blue()
        )

        cogs_with_commands = [cog for cog in self.bot.cogs.values() if [cmd for cmd in cog.get_commands() if not cmd.hidden]]

        for cog in sorted(cogs_with_commands, key=lambda c: c.qualified_name):
            commands_list = sorted([cmd.name for cmd in cog.get_commands() if not cmd.hidden])
            if commands_list:
                embed.add_field(
                    name=cog.qualified_name,
                    value=f"`{'`, `'.join(commands_list)}`",
                    inline=False
                )
        await reply(ctx, embed=embed, ephemeral=True)

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

        await reply(ctx, content=f"Sorry, I couldn't find a category or command named `{query}`.", ephemeral=True)

    async def send_cog_help(self, ctx: commands.Context, cog: commands.Cog):
        """Sends help for a specific cog (category)."""
        embed = discord.Embed(
            title=f"{cog.qualified_name} Help",
            description=cog.description or "No description available for this category.",
            color=discord.Color.green()
        )
        visible_commands = sorted([cmd for cmd in cog.get_commands() if not cmd.hidden], key=lambda c: c.name)
        for cmd in visible_commands:
            # All user-facing commands are slash commands.
            signature = f"/{cmd.name} {cmd.signature}".strip()
            embed.add_field(name=f"`{signature}`", value=cmd.short_doc or "No description.", inline=False)
        await reply(ctx, embed=embed, ephemeral=True)

    async def send_command_help(self, ctx: commands.Context, command: commands.Command):
        """Sends detailed help for a specific command."""
        embed = discord.Embed(
            title=f"Help: `/{command.name}`",
            description=command.help or command.short_doc or "No description available.",
            color=discord.Color.gold()
        )
        signature = f"/{command.qualified_name} {command.signature}".strip()
        embed.add_field(name="Usage", value=f"```\n{signature}\n```", inline=False)

        if isinstance(command, (commands.HybridGroup, commands.Group)):
            subcommands = sorted([sub for sub in command.commands if not sub.hidden], key=lambda c: c.name)
            if subcommands:
                sub_list = "\n".join([f"**`/{sub.qualified_name}`** - {sub.short_doc}" for sub in subcommands])
                embed.add_field(name="Subcommands", value=sub_list, inline=False)
        await reply(ctx, embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    bot.remove_command("help")
    await bot.add_cog(HelpCog(bot))
