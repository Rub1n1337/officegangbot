# cogs/warnings_cog.py
import discord
from discord.ext import commands
from discord import app_commands
from core.logger import logger
from core.permissions import has_permission
from .utils import reply
import datetime


class WarningsCog(commands.Cog, name="⚠️ Warnings"):
    """Warning system with persistent storage via SettingsManager."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @commands.hybrid_command(name="warn", description="Issue a warning to a server member.")
    @app_commands.describe(member="Member to warn.", reason="Reason for the warning.")
    @commands.cooldown(3, 10, commands.BucketType.user)
    @has_permission("warn")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.id == ctx.author.id:
            return await reply(ctx, "❌ You cannot warn yourself.", ephemeral=True)
        if member.bot:
            return await reply(ctx, "❌ You cannot warn bots.", ephemeral=True)

        await self.bot.db.add_warning(
            ctx.guild.id, member.id, reason, ctx.author.id, str(ctx.author)
        )
        warnings = await self.bot.db.get_warnings(ctx.guild.id, member.id)

        # Attempt to DM the user
        try:
            dm_embed = discord.Embed(
                title=f"⚠️ You have received a warning in {ctx.guild.name}",
                color=discord.Color.yellow()
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
            dm_embed.add_field(name="Total Warnings", value=str(len(warnings)), inline=False)
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        embed = discord.Embed(title="⚠️ Warning Issued", color=discord.Color.yellow())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.add_field(name="Total Warnings", value=f"**{len(warnings)}**", inline=False)

        await reply(ctx, embed=embed)
        logger.info(f"Warning issued to {member} in {ctx.guild.name} by {ctx.author}. Reason: {reason}")

    @commands.hybrid_command(name="warnings", description="Shows the list of warnings for a member.")
    @app_commands.describe(member="Member whose warnings to view.")
    @has_permission("warn")
    async def warnings(self, ctx: commands.Context, member: discord.Member):
        warnings = await self.bot.db.get_warnings(ctx.guild.id, member.id)

        embed = discord.Embed(
            title=f"⚠️ Warnings: {member.display_name}",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        if not warnings:
            embed.description = "✅ This member has no warnings."
        else:
            embed.description = f"Total warnings: **{len(warnings)}**"
            for i, w in enumerate(warnings, 1):
                timestamp = w['created_at']
                if isinstance(timestamp, datetime.datetime):
                    timestamp_str = timestamp.strftime('%d.%m.%Y %H:%M')
                else:
                    timestamp_str = str(timestamp)
                embed.add_field(
                    name=f"#{i} — {timestamp_str} UTC",
                    value=f"**Reason:** {w['reason']}\n**Moderator:** {w['moderator_name']}",
                    inline=False
                )

        await reply(ctx, embed=embed, ephemeral=True)

    @commands.hybrid_command(name="clearwarnings", description="Clears all warnings for a member.")
    @app_commands.describe(member="Member whose warnings to clear.")
    @has_permission("warn")
    async def clearwarnings(self, ctx: commands.Context, member: discord.Member):
        count = await self.bot.db.clear_warnings(ctx.guild.id, member.id)
        await reply(ctx, f"✅ Cleared **{count}** warning(s) for {member.mention}.", ephemeral=True)
        logger.info(f"Cleared {count} warnings for {member} in {ctx.guild.name} by {ctx.author}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(WarningsCog(bot))
