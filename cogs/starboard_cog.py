"""Starboard: messages that reach N ⭐ reactions are reposted to a showcase
channel, and the entry's count updates as stars come and go.

Config lives in guild settings (starboard_channel_id / starboard_threshold),
set via /starboard. The decision (create/update/remove/none) is the pure,
unit-tested core in core.starboard; this cog does the Discord I/O.
"""
import discord
from discord import app_commands
from discord.ext import commands

from core.logger import logger
from core.starboard import starboard_action, DEFAULT_THRESHOLD

STAR = "⭐"


def _star_embed(message: discord.Message, count: int) -> discord.Embed:
    embed = discord.Embed(
        description=message.content or "",
        color=discord.Color.gold(),
        timestamp=message.created_at,
    )
    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
    for att in message.attachments:
        if (att.content_type or "").startswith("image"):
            embed.set_image(url=att.url)
            break
    embed.add_field(name="Source", value=f"[Jump to message]({message.jump_url})", inline=False)
    embed.set_footer(text=f"{STAR} {count}")
    return embed


class StarboardCog(commands.Cog, name="⭐ Starboard"):
    starboard = app_commands.Group(name="starboard", description="Showcase top-starred messages.", guild_only=True)

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _handle(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None or str(payload.emoji) != STAR or not self.bot.db:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel_id = await self.bot.db.get_guild_setting(guild.id, "starboard_channel_id")
        if not channel_id:
            return  # disabled
        sb_channel = guild.get_channel(int(channel_id))
        if not sb_channel or payload.channel_id == int(channel_id):
            return  # not configured, or a reaction on a starboard post itself
        src_channel = guild.get_channel(payload.channel_id)
        if not isinstance(src_channel, (discord.TextChannel, discord.Thread)):
            return
        try:
            message = await src_channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

        count = next((r.count for r in message.reactions if str(r.emoji) == STAR), 0)
        threshold = int(await self.bot.db.get_guild_setting(guild.id, "starboard_threshold") or DEFAULT_THRESHOLD)
        existing = await self.bot.db.get_starboard_post(message.id)
        action = starboard_action(count, threshold, existing is not None)

        try:
            if action == "create":
                sb_msg = await sb_channel.send(
                    content=f"{STAR} **{count}** · {src_channel.mention}",
                    embed=_star_embed(message, count),
                )
                await self.bot.db.upsert_starboard_post(message.id, guild.id, sb_msg.id, count)
            elif action == "update":
                try:
                    sb_msg = await sb_channel.fetch_message(existing["starboard_message_id"])
                    await sb_msg.edit(
                        content=f"{STAR} **{count}** · {src_channel.mention}",
                        embed=_star_embed(message, count),
                    )
                    await self.bot.db.upsert_starboard_post(message.id, guild.id, sb_msg.id, count)
                except discord.NotFound:
                    # the starboard entry was deleted — repost it
                    sb_msg = await sb_channel.send(
                        content=f"{STAR} **{count}** · {src_channel.mention}",
                        embed=_star_embed(message, count),
                    )
                    await self.bot.db.upsert_starboard_post(message.id, guild.id, sb_msg.id, count)
            elif action == "remove":
                try:
                    sb_msg = await sb_channel.fetch_message(existing["starboard_message_id"])
                    await sb_msg.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass
                await self.bot.db.delete_starboard_post(message.id)
        except discord.Forbidden:
            pass
        except Exception:
            logger.exception(f"Starboard update failed for message {message.id}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._handle(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._handle(payload)

    @starboard.command(name="set", description="Set the starboard channel and star threshold.")
    @app_commands.describe(channel="Where starred messages are showcased", threshold="Stars needed (default 3)")
    async def set_starboard(self, interaction: discord.Interaction, channel: discord.TextChannel, threshold: int = DEFAULT_THRESHOLD):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need the Manage Server permission.", ephemeral=True)
            return
        threshold = max(1, min(threshold, 100))
        await self.bot.db.set_guild_setting(interaction.guild_id, "starboard_channel_id", channel.id)
        await self.bot.db.set_guild_setting(interaction.guild_id, "starboard_threshold", threshold)
        await interaction.response.send_message(
            f"Starboard set to {channel.mention} at {threshold} {STAR}.", ephemeral=True
        )

    @starboard.command(name="disable", description="Turn the starboard off.")
    async def disable_starboard(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need the Manage Server permission.", ephemeral=True)
            return
        await self.bot.db.set_guild_setting(interaction.guild_id, "starboard_channel_id", None)
        await interaction.response.send_message("Starboard disabled.", ephemeral=True)

    @starboard.command(name="status", description="Show the current starboard settings.")
    async def starboard_status(self, interaction: discord.Interaction):
        channel_id = await self.bot.db.get_guild_setting(interaction.guild_id, "starboard_channel_id")
        if not channel_id:
            await interaction.response.send_message("Starboard is off. Set it up with `/starboard set`.", ephemeral=True)
            return
        threshold = int(await self.bot.db.get_guild_setting(interaction.guild_id, "starboard_threshold") or DEFAULT_THRESHOLD)
        await interaction.response.send_message(f"Starboard: <#{channel_id}> at {threshold} {STAR}.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StarboardCog(bot))
