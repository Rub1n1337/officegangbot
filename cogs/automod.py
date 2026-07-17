# cogs/automod.py
import discord
from discord.ext import commands
from core.logger import logger
from core.permissions import bot_can_act_on
from core.i18n import t
from core.content_filter import contains_invite, first_disallowed_link, build_words_pattern, first_banned_word
from core.automod_rules import compile_rules, first_match
import datetime

class AutoModCog(commands.Cog, name="🛡️ AutoMod"):
    """
    Auto-moderation:
    - Content filter (invites / links / banned words), configurable anti-spam
      and mention limits.
    - Custom regex rules and a strike-escalation system (mute/kick/ban).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._message_log: dict = {} # Fallback if Redis unavailable
        # Cache of compiled regex rules per guild, keyed by a signature of the
        # rule list so it recompiles only when the rules actually change.
        self._rules_cache: dict = {}
        # Same idea for the banned-words pattern.
        self._words_cache: dict = {}

    def _get_compiled_rules(self, guild_id: int, rules: list):
        """Returns compiled [(regex, action)] for a guild, recompiling only when
        the rule set changes."""
        signature = tuple((r["pattern"], r["action"], r["enabled"]) for r in rules)
        cached = self._rules_cache.get(guild_id)
        if cached and cached[0] == signature:
            return cached[1]
        compiled = compile_rules(rules)
        self._rules_cache[guild_id] = (signature, compiled)
        return compiled

    def _get_words_pattern(self, guild_id: int, words: list):
        """Returns the compiled banned-words pattern, recompiling only when the
        word list changes."""
        signature = tuple(words)
        cached = self._words_cache.get(guild_id)
        if cached and cached[0] == signature:
            return cached[1]
        compiled = build_words_pattern(words)
        self._words_cache[guild_id] = (signature, compiled)
        return compiled

    async def _register_strike(self, message: discord.Message, reason: str):
        """If strikes are enabled, record one and escalate (mute/kick/ban) once
        the active strike count crosses the configured thresholds."""
        config = await self.bot.db.get_automod_config(message.guild.id)
        if not config.get("strikes_enabled"):
            return
        member = message.author
        guild = message.guild
        if config.get("dry_run"):
            # Dry-run: report the strike that *would* be issued, but don't
            # touch the strike count or escalate.
            await self._log_automod(
                guild,
                f"🧪 **[Dry-run]** Would add a **strike** to {member.mention} "
                f"(`{member.id}`) — {reason}",
            )
            return
        try:
            count = await self.bot.db.add_strike(
                guild.id, member.id, reason, config.get("strike_expiry_hours", 24)
            )
        except Exception as e:
            logger.exception(f"AutoMod: failed to record strike: {e}")
            return

        ban_at = config.get("strike_ban_at", 0)
        kick_at = config.get("strike_kick_at", 0)
        mute_at = config.get("strike_mute_at", 0)
        action = None
        if ban_at and count >= ban_at:
            action = "ban"
        elif kick_at and count >= kick_at:
            action = "kick"
        elif mute_at and count >= mute_at:
            action = "mute"

        escalated = None
        # Same hierarchy rule as the manual commands: never the owner or anyone
        # at/above the bot. Discord would refuse anyway (403); skipping cleanly
        # avoids the attempt and the noisy Forbidden log.
        if action and not bot_can_act_on(
            target_id=member.id,
            target_top_role_pos=member.top_role.position,
            bot_id=self.bot.user.id,
            bot_top_role_pos=guild.me.top_role.position,
            owner_id=guild.owner_id,
        ):
            logger.info(f"AutoMod: escalation ({action}) skipped for {member} — protected by hierarchy")
            action = None
        try:
            if action == "ban":
                await guild.ban(member, reason=f"AutoMod: {count} strikes")
                escalated = "banned"
            elif action == "kick":
                await member.kick(reason=f"AutoMod: {count} strikes")
                escalated = "kicked"
            elif action == "mute":
                await member.timeout(datetime.timedelta(minutes=10), reason=f"AutoMod: {count} strikes")
                escalated = "muted 10m"
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"AutoMod: could not escalate ({action}) on {member} in {guild.name}: {e}")

        desc = f"**Strike {count}** for {member.mention} (`{member.id}`) — {reason}"
        if escalated:
            desc += f" → **{escalated}**"
        await self._log_automod(guild, desc)

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
            logger.exception(f"AutoMod: Error timing out {member}: {e}")

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
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
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

    async def _block_message(self, message: discord.Message, loc: str, notice_key: str,
                             log_description: str, dry_run: bool = False):
        """Delete a message that broke a content rule, briefly notify the author,
        and record it in the AutoMod log. In dry-run mode nothing is deleted —
        only a log entry is written so admins can see what *would* have happened."""
        if dry_run:
            await self._log_automod(message.guild, f"🧪 **[Dry-run]** No action — {log_description}")
            return
        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            return
        try:
            await message.channel.send(
                t(loc, notice_key, mention=message.author.mention),
                delete_after=5,
            )
        except discord.Forbidden:
            pass
        await self._log_automod(message.guild, log_description)

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
        loc = await self.bot.db.get_locale(guild_id)

        # --- Content filter (invite / link blocking) ---
        config = await self.bot.db.get_automod_config(guild_id)

        # Exemptions: skip AutoMod entirely in opted-out channels (or their
        # category) and for members holding an exempt role.
        ignored_channels = config.get("ignored_channels") or []
        if message.channel.id in ignored_channels or getattr(message.channel, "category_id", None) in ignored_channels:
            return
        ignored_roles = config.get("ignored_roles") or []
        if ignored_roles and any(r.id in ignored_roles for r in getattr(message.author, "roles", [])):
            return

        # In dry-run mode we still run every detection below, but log what *would*
        # have happened instead of deleting/timing-out/striking.
        dry_run = config["dry_run"]

        # --- Banned words (the standalone word filter, merged into AutoMod so
        # it shares the exemptions, dry-run and strike escalation above/below) ---
        banned_words = config.get("banned_words") or []
        if banned_words:
            word = first_banned_word(message.content, self._get_words_pattern(guild_id, banned_words))
            if word:
                await self._block_message(
                    message, loc, "filter.deleted",
                    f"**Banned word** by {message.author.mention} (`{user_id}`) — message deleted.",
                    dry_run=dry_run,
                )
                await self._register_strike(message, "banned word")
                return

        if config["block_invites"] and contains_invite(message.content):
            await self._block_message(
                message, loc, "automod.invite_blocked",
                f"**Invite link** by {message.author.mention} (`{user_id}`) — message deleted.",
                dry_run=dry_run,
            )
            await self._register_strike(message, "invite link")
            return
        if config["block_links"]:
            bad = first_disallowed_link(message.content, config["allowed_domains"])
            if bad:
                await self._block_message(
                    message, loc, "automod.link_blocked",
                    f"**Disallowed link** by {message.author.mention} (`{user_id}`) — message deleted.",
                    dry_run=dry_run,
                )
                await self._register_strike(message, "disallowed link")
                return

        # --- Custom regex rules ---
        rules = config.get("rules") or []
        if rules:
            matched = first_match(self._get_compiled_rules(guild_id, rules), message.content)
            if matched:
                await self._block_message(
                    message, loc, "automod.rule_blocked",
                    f"**Custom filter** matched a message by {message.author.mention} (`{user_id}`) — deleted.",
                    dry_run=dry_run,
                )
                if matched == "strike":
                    await self._register_strike(message, "custom filter match")
                return

        # --- Mass mentions (@everyone / @here) ---
        if config["block_mass_mentions"] and message.mention_everyone:
            await self._block_message(
                message, loc, "automod.mass_mention_blocked",
                f"**Mass mention** (@everyone/@here) by {message.author.mention} "
                f"(`{user_id}`) — message deleted.",
                dry_run=dry_run,
            )
            await self._register_strike(message, "mass mention")
            return

        # --- Anti-mention spam ---
        mention_limit = config["mention_limit"]
        total_mentions = len(message.mentions) + len(message.role_mentions)
        if total_mentions > mention_limit:
            await self._block_message(
                message, loc, "automod.mention_spam",
                f"**Mention Spam** by {message.author.mention} (`{user_id}`)\n"
                f"Message contained **{total_mentions}** mentions and was deleted.",
                dry_run=dry_run,
            )
            await self._register_strike(message, "mention spam")
            return

        # --- Anti-spam (configurable: N messages within a time window) ---
        spam_count = config["spam_count"]
        spam_window = config["spam_window"]

        # Count recent messages via Redis (atomic, cross-process). None means
        # Redis couldn't answer — fall back to the in-memory counter so a Redis
        # blip can't silently switch spam detection off (the mirror of the XP
        # cooldown fix).
        msg_count = (
            await self.bot.redis.log_message(guild_id, user_id, spam_window)
            if self.bot.redis
            else None
        )
        used_redis = msg_count is not None
        user_log = None
        if not used_redis:
            guild_log = self._message_log.setdefault(guild_id, {})
            user_log = guild_log.setdefault(user_id, [])
            # Keep only messages from within the configured window.
            user_log[:] = [ts for ts in user_log if now - ts < spam_window]
            user_log.append(now)
            # Drop empty entries so the fallback dict doesn't grow unbounded.
            for uid in [uid for uid, log in guild_log.items() if not log and uid != user_id]:
                del guild_log[uid]
            if not guild_log:
                self._message_log.pop(guild_id, None)
            msg_count = len(user_log)

        if msg_count >= spam_count:
            # Reset the window so the next burst starts from zero.
            if used_redis:
                await self.bot.redis.clear_message_log(guild_id, user_id)
            elif user_log is not None:
                user_log.clear()
            if dry_run:
                await self._log_automod(
                    message.guild,
                    f"🧪 **[Dry-run]** No action — **spam** by {message.author.mention} "
                    f"(`{user_id}`): {spam_count}+ messages in {spam_window}s "
                    f"(would time out 10m)."
                )
            else:
                try:
                    await message.channel.send(
                        t(loc, "automod.spam_timeout", mention=message.author.mention),
                        delete_after=10
                    )
                except discord.Forbidden:
                    pass
                await self._log_automod(
                    message.guild,
                    f"**Spam Detection** — {message.author.mention} (`{user_id}`)\n"
                    f"Sent {spam_count}+ messages in {spam_window} seconds. Auto-timeout for **10 minutes**."
                )
                await self._apply_timeout(message.author, "AutoMod: spam detection")
            await self._register_strike(message, "spam")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoModCog(bot))
