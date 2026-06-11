# cogs/filter_cog.py
import discord
import re
from discord.ext import commands
from discord import app_commands
from core.logger import logger
from core.permissions import has_permission
from core.settings_manager import SettingsManager
from .utils import reply

# A default list of profanities. This can be expanded.
DEFAULT_BANNED_WORDS = [
    "fuck", "shit", "bitch", "cunt", "asshole", "dick", "pussy",
    "bastard", "damn", "hell", "nigger", "faggot"
]

DEFAULT_FILTER_SETTINGS = {
    "filter_enabled": False,
    "filter_words": []
}

class FilterCog(commands.Cog, name="🚫 Filter"):
    """Handles message filtering and managing the banned words list."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager = bot.settings_manager
        self._pattern_cache: dict = {}  # Local fallback if Redis unavailable

    async def _get_pattern(self, guild_id: int):
        """Returns compiled regex pattern from Redis cache or builds it."""
        # Try Redis first
        if self.bot.redis:
            cached = await self.bot.redis.get_filter_pattern(guild_id)
            if cached:
                return re.compile(cached, re.IGNORECASE)

        # Build pattern from settings
        words = self.settings_manager.get_setting(guild_id, 'filter_words', [])
        if not words:
            return None

        pattern_str = r'\b(' + '|'.join(re.escape(w) for w in words) + r')\b'

        # Cache in Redis
        if self.bot.redis:
            await self.bot.redis.set_filter_pattern(guild_id, pattern_str)
        else:
            self._pattern_cache[guild_id] = re.compile(pattern_str, re.IGNORECASE)

        return re.compile(pattern_str, re.IGNORECASE)

    async def _invalidate_pattern(self, guild_id: int):
        """Invalidates pattern cache when word list changes."""
        if self.bot.redis:
            await self.bot.redis.invalidate_filter_pattern(guild_id)
        if guild_id in self._pattern_cache:
            del self._pattern_cache[guild_id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot or message.author.guild_permissions.administrator:
            return

        settings = self.settings_manager.get_setting(message.guild.id, 'message_filter', DEFAULT_FILTER_SETTINGS)
        if not settings.get('filter_enabled'):
            return

        pattern = await self._get_pattern(message.guild.id)
        if pattern and pattern.search(message.content):
            try:
                await message.delete()
                await message.channel.send(f"{message.author.mention}, your message contained inappropriate language and was deleted.", delete_after=10)
                logger.info(f"Deleted a message from {message.author} in {message.guild.name} due to profanity.")
                
                log_channel_id = self.settings_manager.get_setting(message.guild.id, 'punishment_log_id')
                if log_channel_id and (log_channel := self.bot.get_channel(log_channel_id)):
                    embed = discord.Embed(
                        title="Moderation Action: Message Filtered",
                        color=discord.Color.magenta(),
                        timestamp=message.created_at
                    )
                    embed.add_field(name="User", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
                    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                    embed.add_field(name="Original Message", value=f"```{discord.utils.escape_markdown(message.content)}```", inline=False)
                    embed.set_footer(text=f"User ID: {message.author.id}")
                    await log_channel.send(embed=embed)

            except discord.Forbidden:
                logger.warning(f"Failed to delete a filtered message in {message.channel.mention}. Missing permissions.")
            except Exception as e:
                logger.error(f"Error in on_message for filter cog in guild {message.guild.id}: {e}", exc_info=True)

    # Local error handler removed. The global handler in bot.py will now manage errors.

    @commands.hybrid_group(name="filter")
    @has_permission("config")
    async def filter(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            help_cog = self.bot.get_cog("❓ Help")
            if help_cog:
                await help_cog.send_command_help(ctx, ctx.command)
            else:
                await reply(ctx, "The help command is currently unavailable.", ephemeral=True)

    @filter.command(name="toggle", description="Enables or disables the profanity filter.")
    @has_permission("config")
    async def filter_toggle(self, ctx: commands.Context):
        settings = self.settings_manager.get_setting(ctx.guild.id, 'message_filter', DEFAULT_FILTER_SETTINGS)
        new_status = not settings.get('filter_enabled', False)
        settings['filter_enabled'] = new_status
        await self.settings_manager.update_setting(ctx.guild.id, 'message_filter', settings)
        await reply(ctx, f"✅ The profanity filter has been **{'enabled' if new_status else 'disabled'}**.")

    @filter.command(name="add", description="Adds a word to the filter.")
    @app_commands.describe(word="The word to add to the filter.")
    @has_permission("config")
    async def filter_add(self, ctx: commands.Context, word: str):
        word = word.lower()
        settings = self.settings_manager.get_setting(ctx.guild.id, 'message_filter', DEFAULT_FILTER_SETTINGS)
        banned_words = settings.setdefault('filter_words', [])
        if word in banned_words:
            await reply(ctx, f"The word `{word}` is already in the filter.")
            return
        banned_words.append(word)
        await self.settings_manager.update_setting(ctx.guild.id, 'message_filter', settings)
        await self._invalidate_pattern(ctx.guild.id)
        await reply(ctx, f"✅ The word `{word}` has been added to the filter.")

    @filter.command(name="add_defaults", description="Adds the default list of profanities to the filter.")
    async def filter_add_defaults(self, ctx: commands.Context):
        """Adds a predefined list of common profanities to the server's filter."""
        # The `reply` helper will handle deferring automatically.
        settings = self.settings_manager.get_setting(ctx.guild.id, 'message_filter', DEFAULT_FILTER_SETTINGS)
        banned_words = settings.setdefault('filter_words', [])
        
        new_words = [word for word in DEFAULT_BANNED_WORDS if word not in banned_words]
        added_count = len(new_words)
        
        if added_count == 0:
            await reply(ctx, "✅ All default profanities are already in your filter list.")
            return
        
        banned_words.extend(new_words)
        await self.settings_manager.update_setting(ctx.guild.id, 'message_filter', settings)
        await self._invalidate_pattern(ctx.guild.id)
        await reply(ctx, f"✅ Added **{added_count}** new words from the default profanity list to your filter.")

    @filter.command(name="remove", description="Removes a word from the filter.")
    @app_commands.describe(word="The word to remove from the filter.")
    @has_permission("config")
    async def filter_remove(self, ctx: commands.Context, word: str):
        word = word.lower()
        settings = self.settings_manager.get_setting(ctx.guild.id, 'message_filter', DEFAULT_FILTER_SETTINGS)
        banned_words = settings.get('filter_words', [])
        if word not in banned_words:
            await reply(ctx, f"The word `{word}` is not in the filter.")
            return
        banned_words.remove(word)
        await self.settings_manager.update_setting(ctx.guild.id, 'message_filter', settings)
        await self._invalidate_pattern(ctx.guild.id)
        await reply(ctx, f"✅ The word `{word}` has been removed from the filter.")

    @filter.command(name="list", description="Lists all words in the filter.")
    @has_permission("config")
    async def filter_list(self, ctx: commands.Context):
        banned_words = self.settings_manager.get_setting(ctx.guild.id, 'message_filter', {}).get('filter_words', [])
        if not banned_words:
            await reply(ctx, "There are no words in the filter.")
            return
        description = ", ".join(f"`{word}`" for word in sorted(banned_words))
        if len(description) > 4000:
            description = description[:4000] + "..."
        embed = discord.Embed(title="🚫 Filtered Words", description=description, color=discord.Color.red())
        await reply(ctx, embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(FilterCog(bot))