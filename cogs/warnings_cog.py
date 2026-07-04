# cogs/warnings_cog.py
import discord
from discord.ext import commands
from discord import app_commands
from core.logger import logger
from core.permissions import has_permission
from core.i18n import t
from core.warn_escalation import maybe_escalate_warning
from .utils import reply, send_paginated
import datetime


class WarningsCog(commands.Cog, name="⚠️ Warnings"):
    """Warning system with persistent storage in PostgreSQL."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="warn", description="Issue a warning to a server member.")
    @app_commands.describe(member="Member to warn.", reason="Reason for the warning.")
    @commands.cooldown(3, 10, commands.BucketType.user)
    @has_permission("warn")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        if member.id == ctx.author.id:
            return await reply(ctx, t(loc, "warn.cannot_self"), ephemeral=True)
        if member.bot:
            return await reply(ctx, t(loc, "warn.cannot_bot"), ephemeral=True)

        await self.bot.db.add_warning(
            ctx.guild.id, member.id, reason, ctx.author.id, str(ctx.author)
        )
        warnings = await self.bot.db.get_warnings(ctx.guild.id, member.id)

        # Attempt to DM the user
        try:
            dm_embed = discord.Embed(
                title=t(loc, "warn.dm_title", guild=ctx.guild.name),
                color=discord.Color.yellow()
            )
            dm_embed.add_field(name=t(loc, "field.reason"), value=reason, inline=False)
            dm_embed.add_field(name=t(loc, "field.moderator"), value=str(ctx.author), inline=False)
            dm_embed.add_field(name=t(loc, "field.total_warnings"), value=str(len(warnings)), inline=False)
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        embed = discord.Embed(title=t(loc, "warn.issued_title"), color=discord.Color.yellow())
        embed.add_field(name=t(loc, "field.user"), value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name=t(loc, "field.reason"), value=reason, inline=False)
        embed.add_field(name=t(loc, "field.moderator"), value=ctx.author.mention, inline=False)
        embed.add_field(name=t(loc, "field.total_warnings"), value=f"**{len(warnings)}**", inline=False)

        # Auto-escalate (mute/kick/ban) if the guild's warning thresholds are crossed.
        escalated = await maybe_escalate_warning(self.bot.db, ctx.guild, member)
        if escalated:
            embed.add_field(name=t(loc, "warn.escalated_field"), value=t(loc, "warn.escalated", action=escalated), inline=False)

        await reply(ctx, embed=embed)
        logger.info(f"Warning issued to {member} in {ctx.guild.name} by {ctx.author}. Reason: {reason}")

    @commands.hybrid_command(name="warnings", description="Shows the list of warnings for a member.")
    @app_commands.describe(member="Member whose warnings to view.")
    @has_permission("warn")
    async def warnings(self, ctx: commands.Context, member: discord.Member):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        warnings = await self.bot.db.get_warnings(ctx.guild.id, member.id)

        if not warnings:
            embed = discord.Embed(
                title=t(loc, "warnings.title", member=member.display_name),
                description=t(loc, "warnings.none"),
                color=discord.Color.orange(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            return await reply(ctx, embed=embed, ephemeral=True)

        per_page = 5
        total_pages = (len(warnings) + per_page - 1) // per_page
        pages = []

        for page in range(total_pages):
            chunk = warnings[page * per_page:(page + 1) * per_page]
            embed = discord.Embed(
                title=t(loc, "warnings.title", member=member.display_name),
                description=t(loc, "warnings.total", count=len(warnings)),
                color=discord.Color.orange(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            for offset, w in enumerate(chunk):
                number = page * per_page + offset + 1
                timestamp = w['created_at']
                if isinstance(timestamp, datetime.datetime):
                    timestamp_str = timestamp.strftime('%d.%m.%Y %H:%M')
                else:
                    timestamp_str = str(timestamp)
                embed.add_field(
                    name=t(loc, "warnings.entry_name", number=number, time=timestamp_str),
                    value=t(loc, "warnings.entry_value", reason=w['reason'], moderator=w['moderator_name']),
                    inline=False,
                )
            embed.set_footer(text=t(loc, "page.indicator", current=page + 1, total=total_pages))
            pages.append(embed)

        await send_paginated(ctx, pages, ephemeral=True)

    @commands.hybrid_command(name="clearwarnings", description="Clears all warnings for a member.")
    @app_commands.describe(member="Member whose warnings to clear.")
    @has_permission("warn")
    async def clearwarnings(self, ctx: commands.Context, member: discord.Member):
        loc = await self.bot.db.get_locale(ctx.guild.id)
        count = await self.bot.db.clear_warnings(ctx.guild.id, member.id)
        await reply(ctx, t(loc, "warnings.cleared", count=count, member=member.mention), ephemeral=True)
        logger.info(f"Cleared {count} warnings for {member} in {ctx.guild.name} by {ctx.author}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(WarningsCog(bot))
