# cogs/automod.py
import discord
from discord.ext import commands
from core.logger import logger
import datetime

class AutoModCog(commands.Cog, name="🛡️ AutoMod"):
    """
    Basic auto-moderation:
    - Anti-spam: timeouts users sending 5+ messages in 3 seconds for 10 minutes.
    - Anti-mention-spam: deletes messages with 5+ user/role mentions.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._message_log: dict = {} # Fallback if Redis unavailable

    async def _apply_timeout(self, member: discord.Member, reason: str):
        """Applies native Discord timeout (10 minutes)."""
        duration = datetime.timedelta(minutes=10)
        try:
            await member.timeout(duration, reason=reason)
            logger.info(f"AutoMod: Timed out {member} in {member.guild.name} for 10 minutes. Reason: {reason}")
            
            # Note: We don't need to add to timed_punishments table for timeouts
            # as Discord handles the expiry natively.
        except discord.Forbidden:
            logger.warning(f"AutoMod: Cannot timeout {member} in {member.guild.name} — missing permissions")
        except Exception as e:
            logger.error(f"AutoMod: Error timing out {member}: {e}")

    async def _log_automod(self, guild: discord.Guild, description: str):
        """Sends a log message to the moderation log channel."""
        # Check if logging feature is enabled
        enabled_features = await self.bot.db.get_enabled_features(guild.id)
        if "logging" not in enabled_features:
            return

        log_channel_id = await self.bot.db.get_guild_setting(guild.id, 'punishment_log_id')
        if not log_channel_id:
            return
            
        channel = guild.get_channel(int(log_channel_id))
        if not channel:
            # Try to fetch if not in cache
            try:
                channel = await guild.fetch_channel(int(log_channel_id))
            except:
                return

        embed = discord.Embed(
            title="🛡️ AutoMod Action",
            description=description,
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Check if user is admin or has manage_messages (bypass automod)
        if message.author.guild_permissions.manage_messages:
            return

        # Check automod is enabled
        enabled_features = await self.bot.db.get_enabled_features(message.guild.id)
        if "automod" not in enabled_features:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()

        # --- Anti-mention spam ---
        total_mentions = len(message.mentions) + len(message.role_mentions)
        if total_mentions > 5:
            try:
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} Your message was removed for containing too many mentions.",
                    delete_after=5
                )
                await self._log_automod(
                    message.guild,
                    f"**Mention Spam** by {message.author.mention} (`{user_id}`)\n"
                    f"Message contained **{total_mentions}** mentions and was deleted."
                )
            except discord.Forbidden:
                pass
            return

        # --- Anti-spam (5 messages in 3 seconds) ---
        if self.bot.redis:
            msg_count = await self.bot.redis.log_message(guild_id, user_id)
            if msg_count >= 5:
                await self.bot.redis.clear_message_log(guild_id, user_id)
                try:
                    await message.channel.send(
                        f"⚠️ {message.author.mention} You are sending messages too fast. "
                        f"You have been timed out for **10 minutes**.",
                        delete_after=10
                    )
                except discord.Forbidden:
                    pass
                await self._log_automod(
                    message.guild,
                    f"**Spam Detection** — {message.author.mention} (`{user_id}`)\n"
                    f"Sent 5+ messages in 3 seconds. Auto-timeout for **10 minutes**."
                )
                await self._apply_timeout(message.author, "AutoMod: spam detection")
        else:
            # Fallback to in-memory if Redis unavailable
            guild_log = self._message_log.setdefault(guild_id, {})
            user_log = guild_log.setdefault(user_id, [])

            # Keep only messages from the last 3 seconds
            user_log[:] = [t for t in user_log if now - t < 3]
            user_log.append(now)

            # Drop empty per-user/per-guild entries so the fallback dict doesn't
            # grow unbounded over time (only matters when Redis is unavailable).
            for uid in [uid for uid, log in guild_log.items() if not log and uid != user_id]:
                del guild_log[uid]
            if not guild_log:
                self._message_log.pop(guild_id, None)

            if len(user_log) >= 5:
                user_log.clear()
                try:
                    await message.channel.send(
                        f"⚠️ {message.author.mention} You are sending messages too fast. "
                        f"You have been timed out for **10 minutes**.",
                        delete_after=10
                    )
                except discord.Forbidden:
                    pass

                await self._log_automod(
                    message.guild,
                    f"**Spam Detection** — {message.author.mention} (`{user_id}`)\n"
                    f"Sent 5+ messages in 3 seconds. Auto-timeout for **10 minutes**."
                )
                await self._apply_timeout(message.author, "AutoMod: spam detection")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoModCog(bot))
