# cogs/utility_cog.py
import discord
from discord.ext import commands
from discord import app_commands
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

        status_map = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🟡 Idle",
            discord.Status.dnd: "🔴 Do Not Disturb",
            discord.Status.offline: "⚫ Offline",
        }
        status = status_map.get(member.status, "⚫ Offline")

        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"][:5]
        roles_text = ", ".join(roles) if roles else "No roles"

        embed = discord.Embed(
            title="👤 Member Information",
            color=member.color if member.color != discord.Color.default() else discord.Color.blurple()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="📡 Status", value=status, inline=True)
        embed.add_field(name="🤖 Bot?", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(
            name="📅 Account Created",
            value=f"<t:{int(member.created_at.timestamp())}:F>\n(<t:{int(member.created_at.timestamp())}:R>)",
            inline=False
        )
        embed.add_field(
            name="📥 Joined Server",
            value=f"<t:{int(member.joined_at.timestamp())}:F>\n(<t:{int(member.joined_at.timestamp())}:R>)" if member.joined_at else "Unknown",
            inline=False
        )
        embed.add_field(name=f"🎭 Roles [{len(roles)}]", value=roles_text, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await reply(ctx, embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Shows information about the server.")
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        total = guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        humans = total - bots

        embed = discord.Embed(
            title="📊 Server Information",
            description=guild.description or "No description set.",
            color=discord.Color.blurple()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="🏷️ Name", value=guild.name, inline=True)
        embed.add_field(name="🆔 ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(
            name="👥 Members",
            value=f"Total: **{total}**\n👤 Humans: **{humans}**\n🤖 Bots: **{bots}**",
            inline=True
        )
        embed.add_field(
            name="💬 Channels",
            value=f"📝 Text: **{len(guild.text_channels)}**\n🔊 Voice: **{len(guild.voice_channels)}**\n📁 Categories: **{len(guild.categories)}**",
            inline=True
        )
        embed.add_field(name="😀 Emojis", value=f"**{len(guild.emojis)}** / {guild.emoji_limit}", inline=True)
        embed.add_field(
            name="📅 Server Created",
            value=f"<t:{int(guild.created_at.timestamp())}:F>\n(<t:{int(guild.created_at.timestamp())}:R>)",
            inline=False
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await reply(ctx, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
