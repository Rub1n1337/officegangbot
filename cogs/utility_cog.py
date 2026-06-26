# cogs/utility_cog.py
import discord
from discord.ext import commands
from discord import app_commands
from core.i18n import t
from .utils import reply
from typing import Optional


class UtilityCog(commands.Cog, name="🛠️ Utility"):
    """Utility commands for user and server information."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="userinfo", description="Shows information about a server member.")
    @app_commands.describe(member="Server member. If not specified, shows your own info.")
    async def userinfo(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        member = member or ctx.author
        loc = await self.bot.db.get_locale(ctx.guild.id)

        status_map = {
            discord.Status.online: t(loc, "status.online"),
            discord.Status.idle: t(loc, "status.idle"),
            discord.Status.dnd: t(loc, "status.dnd"),
            discord.Status.offline: t(loc, "status.offline"),
        }
        status = status_map.get(member.status, t(loc, "status.offline"))

        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"][:5]
        roles_text = ", ".join(roles) if roles else t(loc, "userinfo.no_roles")

        embed = discord.Embed(
            title=t(loc, "userinfo.title"),
            color=member.color if member.color != discord.Color.default() else discord.Color.blurple()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name=t(loc, "info.id"), value=f"`{member.id}`", inline=True)
        embed.add_field(name=t(loc, "userinfo.status"), value=status, inline=True)
        embed.add_field(name=t(loc, "userinfo.bot"), value=t(loc, "common.yes") if member.bot else t(loc, "common.no"), inline=True)
        embed.add_field(
            name=t(loc, "userinfo.account_created"),
            value=f"<t:{int(member.created_at.timestamp())}:F>\n(<t:{int(member.created_at.timestamp())}:R>)",
            inline=False
        )
        embed.add_field(
            name=t(loc, "userinfo.joined"),
            value=f"<t:{int(member.joined_at.timestamp())}:F>\n(<t:{int(member.joined_at.timestamp())}:R>)" if member.joined_at else t(loc, "common.unknown"),
            inline=False
        )
        embed.add_field(name=t(loc, "userinfo.roles", count=len(roles)), value=roles_text, inline=False)
        embed.set_footer(text=t(loc, "common.requested_by", user=ctx.author), icon_url=ctx.author.display_avatar.url)

        await reply(ctx, embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Shows information about the server.")
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        loc = await self.bot.db.get_locale(guild.id)
        total = guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        humans = total - bots

        embed = discord.Embed(
            title=t(loc, "serverinfo.title"),
            description=guild.description or t(loc, "serverinfo.no_description"),
            color=discord.Color.blurple()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name=t(loc, "serverinfo.name"), value=guild.name, inline=True)
        embed.add_field(name=t(loc, "info.id"), value=f"`{guild.id}`", inline=True)
        embed.add_field(name=t(loc, "serverinfo.owner"), value=guild.owner.mention if guild.owner else t(loc, "common.unknown"), inline=True)
        embed.add_field(
            name=t(loc, "serverinfo.members"),
            value=t(loc, "serverinfo.members_value", total=total, humans=humans, bots=bots),
            inline=True
        )
        embed.add_field(
            name=t(loc, "serverinfo.channels"),
            value=t(loc, "serverinfo.channels_value", text=len(guild.text_channels), voice=len(guild.voice_channels), categories=len(guild.categories)),
            inline=True
        )
        embed.add_field(name=t(loc, "serverinfo.emojis"), value=f"**{len(guild.emojis)}** / {guild.emoji_limit}", inline=True)
        embed.add_field(
            name=t(loc, "serverinfo.created"),
            value=f"<t:{int(guild.created_at.timestamp())}:F>\n(<t:{int(guild.created_at.timestamp())}:R>)",
            inline=False
        )
        embed.set_footer(text=t(loc, "common.requested_by", user=ctx.author), icon_url=ctx.author.display_avatar.url)

        await reply(ctx, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
