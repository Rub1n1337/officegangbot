# cogs/automod.py
import discord
from discord.ext import commands, tasks
from core.logger import logger
import datetime
import asyncio


class AutoModCog(commands.Cog, name="🛡️ AutoMod"):
    """
    Basic auto-moderation:
    - Anti-spam: mutes users sending 5+ messages in 3 seconds for 10 minutes.
    - Anti-mention-spam: deletes messages with 5+ user/role mentions.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager = bot.settings_manager
        # Message log now handled by Redis (no in-memory dict needed)
        # Fallback if Redis unavailable
        self._message_log: dict = {}

    async def _apply_mute(self, member: discord.Member, guild: discord.Guild, reason: str):
        """Applies mute and saves to timed_punishments for auto-expiry via TimedEventsCog."""
        mute_role = discord.utils.get(guild.roles, name="Muted")
        if not mute_role:
            try:
                mute_role = await guild.create_role(name="Muted", reason="AutoMod mute role")
                for channel in guild.channels:
                    try:
                        await channel.set_permissions(mute_role, send_messages=False, speak=False)
                    except discord.Forbidden:
                        pass
            except discord.Forbidden:
                logger.warning(f"AutoMod: Cannot create Muted role in {guild.name}")
                return

        try:
            await member.add_roles(mute_role, reason=reason)
            logger.info(f"AutoMod: Muted {member} in {guild.name} for 10 minutes. Reason: {reason}")

            # Save to PostgreSQL for auto-expiry via TimedEventsCog
            expires_at_dt = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

            if self.bot.db:
                await self.bot.db.add_timed_punishment(
                    guild_id=guild.id,
                    user_id=member.id,
                    punishment_type='mute',
                    expires_at=expires_at_dt.replace(tzinfo=datetime.timezone.utc),
                    reason=reason,
                    moderator_id=self.bot.user.id
                )
            else:
                # Fallback to JSON if DB unavailable
                timed = self.bot.settings_manager.get_setting(guild.id, 'timed_punishments', {})
                timed[str(member.id)] = {
                    'type': 'mute',
                    'expires_at': expires_at_dt.timestamp(),
                    'reason': reason,
                    'moderator_id': self.bot.user.id
                }
                await self.bot.settings_manager.update_setting(guild.id, 'timed_punishments', timed)

        except discord.Forbidden:
            logger.warning(f"AutoMod: Cannot mute {member} in {guild.name} — missing permissions")

    async def _log_automod(self, guild: discord.Guild, description: str):
        """Sends a log message to the moderation log channel."""
        log_channel_id = self.settings_manager.get_setting(guild.id, 'punishment_log_id')
        if not log_channel_id:
            return
        channel = guild.get_channel(int(log_channel_id))
        if not channel:
            return
        embed = discord.Embed(
            title="🛡️ AutoMod Action",
            description=description,
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Check automod is enabled
        if not self.settings_manager.get_setting(message.guild.id, 'automod_enabled', True):
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.datetime.utcnow().timestamp()

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
                        f"You have been muted for **10 minutes**.",
                        delete_after=10
                    )
                except discord.Forbidden:
                    pass
                await self._log_automod(
                    message.guild,
                    f"**Spam Detection** — {message.author.mention} (`{user_id}`)\n"
                    f"Sent 5+ messages in 3 seconds. Auto-muted for **10 minutes**."
                )
                await self._apply_mute(message.author, message.guild, "AutoMod: spam detection")
        else:
            # Fallback to in-memory if Redis unavailable
            guild_log = self._message_log.setdefault(guild_id, {})
            user_log = guild_log.setdefault(user_id, [])

            # Keep only messages from the last 3 seconds
            user_log[:] = [t for t in user_log if now - t < 3]
            user_log.append(now)

            if len(user_log) >= 5:
                user_log.clear()
                try:
                    await message.channel.send(
                        f"⚠️ {message.author.mention} You are sending messages too fast. "
                        f"You have been muted for **10 minutes**.",
                        delete_after=10
                    )
                except discord.Forbidden:
                    pass

                await self._log_automod(
                    message.guild,
                    f"**Spam Detection** — {message.author.mention} (`{user_id}`)\n"
                    f"Sent 5+ messages in 3 seconds. Auto-muted for **10 minutes**."
                )
                await self._apply_mute(message.author, message.guild, "AutoMod: spam detection")




async def setup(bot: commands.Bot):
    await bot.add_cog(AutoModCog(bot))
