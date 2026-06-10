# cogs/tickets.py
import discord
from discord.ext import commands
from discord import app_commands
from core.logger import logger
from core.permissions import has_permission
from .utils import reply
from typing import Optional
import asyncio


class CloseTicketView(discord.ui.View):
    """View with a close button inside a ticket channel."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔒 Ticket will be closed in **5 seconds**...",
            ephemeral=False
        )
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
            logger.info(f"Ticket channel {interaction.channel.name} closed by {interaction.user}")
        except discord.Forbidden:
            await interaction.channel.send("❌ I don't have permission to delete this channel.")
        except discord.NotFound:
            pass


class OpenTicketView(discord.ui.View):
    """Persistent view with an open ticket button."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📩 Open Ticket",
        style=discord.ButtonStyle.primary,
        custom_id="open_ticket"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user

        # Check if ticket already exists
        existing = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{member.name.lower().replace(' ', '-')}"
        )
        if existing:
            await interaction.response.send_message(
                f"❌ You already have an open ticket: {existing.mention}",
                ephemeral=True
            )
            return

        # Get support role from settings
        bot = interaction.client
        support_role_id = bot.settings_manager.get_setting(guild.id, 'ticket_support_role_id')
        support_role = guild.get_role(int(support_role_id)) if support_role_id else None

        # Get ticket category
        category_id = bot.settings_manager.get_setting(guild.id, 'ticket_category_id')
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
                name=f"ticket-{member.name.lower().replace(' ', '-')}",
                overwrites=overwrites,
                category=category,
                reason=f"Ticket opened by {member}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to create channels.",
                ephemeral=True
            )
            return

        # Send ticket message
        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=(
                f"Welcome {member.mention}! Support staff will be with you shortly.\n\n"
                f"Please describe your issue and wait for a response.\n"
                f"Click the button below when your issue is resolved."
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Ticket opened by {member}", icon_url=member.display_avatar.url)

        await channel.send(
            content=f"{member.mention}" + (f" | {support_role.mention}" if support_role else ""),
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Your ticket has been created: {channel.mention}",
            ephemeral=True
        )
        logger.info(f"Ticket opened by {member} in {guild.name}: #{channel.name}")


class TicketsCog(commands.Cog, name="🎫 Tickets"):
    """Ticket support system with persistent buttons."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager = bot.settings_manager
        # Register persistent views
        bot.add_view(OpenTicketView())
        bot.add_view(CloseTicketView())

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
        # Save settings
        if support_role:
            await self.settings_manager.update_setting(
                ctx.guild.id, 'ticket_support_role_id', str(support_role.id)
            )
        if category:
            await self.settings_manager.update_setting(
                ctx.guild.id, 'ticket_category_id', str(category.id)
            )

        embed = discord.Embed(
            title="🎫 Support Tickets",
            description=(
                "Need help? Click the button below to open a private support ticket.\n\n"
                "Our staff will assist you as soon as possible."
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

        try:
            await channel.send(embed=embed, view=OpenTicketView())
            await reply(ctx, f"✅ Ticket panel sent to {channel.mention}.", ephemeral=True)
            logger.info(f"Ticket panel set up in #{channel.name} by {ctx.author} in {ctx.guild.name}")
        except discord.Forbidden:
            await reply(ctx, "❌ I don't have permission to send messages in that channel.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
