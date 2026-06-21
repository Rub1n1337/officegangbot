# bot.py
# This is the main application file for the Discord Bot. It's the "brain" of the operation.

import sys
import subprocess
import os
import importlib.metadata as metadata
import logging
from typing import Optional, List, Dict, Any, Set
from pathlib import Path
import time

# Dependencies are managed via requirements.txt and the virtual environment.

# --- Bot Imports ---
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import uvicorn
from core.logger import logger
from config import load_config
# from core.webserver import keep_alive
from core.settings_manager import SettingsManager
from core.health_monitor import HealthMonitor
from core.db_manager import DatabaseManager
from core.redis_manager import RedisManager
from cogs.utils import reply
from api_server import app as fastapi_app, set_bot_instance

# --- Bot Initialization ---

async def get_prefix(bot: "MyBot", message: discord.Message) -> List[str]:
    """A callable to retrieve the prefix for a given guild."""
    if not message.guild:
        return commands.when_mentioned_or('!')(bot, message)
    
    # The bot instance is passed to this function, so we can get the manager from it.
    prefix = bot.settings_manager.get_setting(message.guild.id, 'prefix', default='!')
    return commands.when_mentioned_or(prefix)(bot, message)

class MyBot(commands.Bot):
    """Custom Bot class to handle setup, cogs, and command tree."""
    def __init__(self, settings_manager: SettingsManager):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True

        config = load_config()
        owner_id = config.get('OWNER_ID', 0)

        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None,
            application_id=config.get('APPLICATION_ID', 0),
            owner_id=owner_id
        )

        self.settings_manager = settings_manager
        self.db = None
        self.redis = None

        # Set up the global error handler for slash commands
        self.tree.on_error = self.on_app_command_error

    async def close(self):
        if hasattr(self, '_uvicorn_server'):
            self._uvicorn_server.should_exit = True
            if hasattr(self, '_api_task'):
                try:
                    await asyncio.wait_for(self._api_task, timeout=5)
                except asyncio.TimeoutError:
                    self._api_task.cancel()
            logger.info("FastAPI server stopped")
        if hasattr(self, 'db') and self.db:
            await self.db.close()
        if hasattr(self, 'redis') and self.redis:
            await self.redis.close()
        await super().close()

    async def setup_hook(self):
        """This is called once when the bot logs in, to load cogs."""
        # Initialize database
        self.db = DatabaseManager()
        try:
            await self.db.connect()
        except Exception as e:
            logger.critical(f"Failed to initialize database: {e}")
            # Bot continues with JSON fallback if DB is unavailable
            self.db = None

        # Initialize Redis
        self.redis = RedisManager()
        try:
            await self.redis.connect()
            # Start RPC listener for API server requests
            await self.redis.start_rpc_listener("bot:rpc", self._handle_rpc_request)
            logger.info("Redis RPC listener started.")
        except Exception as e:
            logger.warning(f"Redis unavailable, continuing without it: {e}")
            self.redis = None

        # Start FastAPI server as a background task within the same process
        port = int(os.getenv("PORT", 8080))
        config = uvicorn.Config(
            fastapi_app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            loop="asyncio"
        )
        self._uvicorn_server = uvicorn.Server(config)
        self._api_task = asyncio.create_task(self._uvicorn_server.serve())
        logger.info(f"FastAPI server starting on port {port} (embedded in bot process)")

        logger.info("--- Loading Cogs ---")
        cogs_dir = Path(__file__).parent / "cogs"
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("__") and filename != "utils.py":
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    logger.info(f"Successfully loaded cog: {cog_name}")
                except Exception as e:
                    logger.error(f"Failed to load cog: {cog_name}", exc_info=e)
        logger.info("--- Cogs Loaded ---")

    async def on_ready(self):
        """Called when the bot is ready and connected to Discord."""
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the server"))
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')

        # Perform an initial sync to ensure commands are registered with Discord.
        # This is crucial for the first run or after commands have been cleared.
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} commands on startup.")
        except Exception as e:
            logger.error(f"Failed to sync commands on startup.", exc_info=e)

        logger.info('Bot is ready and listening for commands.')
        logger.warning("Manual command syncing via /sync is now the primary method.")

    @staticmethod
    def _snowflake_or_none(value) -> Optional[str]:
        return str(value) if value else None

    async def _get_feature_payload(self, guild_id: int, feature: str) -> dict:
        if not self.db:
            return {"error": "Database unavailable"}
        settings = await self.db.get_all_guild_settings(guild_id)
        feature_data = {
            "rules": {
                "channel": self._snowflake_or_none(settings.get("rules_channel_id")),
                "message": settings.get("rules_message") or "Please follow the server rules.",
            },
            "welcome-message": {
                "channel": self._snowflake_or_none(settings.get("welcome_channel_id")),
                "message": settings.get("welcome_message") or "Welcome {user.mention} to **{server.name}**!",
            },
            "reaction-role": {
                "messageId": self._snowflake_or_none(settings.get("rules_message_id")),
                "channelId": self._snowflake_or_none(settings.get("rules_channel_id")),
                "emoji": settings.get("reaction_emoji") or "✅",
                "roleId": self._snowflake_or_none(settings.get("reaction_role_id")),
            },
            "moderation": {
                "modRoles": [],
                "adminRoles": [],
                "muteRole": None,
            },
            "logging": {
                "logChannel": self._snowflake_or_none(settings.get("punishment_log_id")),
                "events": ["ban", "kick", "mute", "warn"],
            },
        }
        return feature_data.get(feature, {})

    async def _handle_rpc_request(self, payload: dict) -> dict:
        """Handles RPC requests from the API server via Redis Streams."""
        action = payload.get("action")

        if action == "get_guild_info":
            guild_id = payload.get("guild_id")
            guild = self.get_guild(int(guild_id)) if guild_id else None
            if not guild:
                return {"error": "Guild not found"}
            if not self.db:
                return {"error": "Database unavailable"}
            settings = await self.db.get_all_guild_settings(int(guild_id))
            enabled_features = await self.db.get_enabled_features(int(guild_id))
            return {
                "id": str(guild.id),
                "name": guild.name,
                "icon": str(guild.icon) if guild.icon else None,
                "member_count": guild.member_count,
                "owner_id": str(guild.owner_id),
                "settings": settings,
                "enabledFeatures": enabled_features,
            }

        if action == "get_stats":
            import psutil
            return {
                "status": "online",
                "guilds": len(self.guilds),
                "total_users": sum(g.member_count for g in self.guilds),
                "latency_ms": round(self.latency * 1000, 2),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "ram_percent": psutil.virtual_memory().percent,
                "ram_used_mb": round(psutil.virtual_memory().used / 1024 / 1024, 2),
            }

        if action == "get_guilds":
            return {
                "guilds": [
                    {
                        "id": str(g.id),
                        "name": g.name,
                        "icon": str(g.icon) if g.icon else None,
                        "member_count": g.member_count
                    }
                    for g in self.guilds
                ]
            }

        if action == "get_guild_roles":
            guild_id = payload.get("guild_id")
            guild = self.get_guild(int(guild_id)) if guild_id else None
            if not guild:
                return {"error": "Guild not found"}
            return [
                {
                    "id": str(role.id),
                    "name": role.name,
                    "color": role.color.value,
                    "position": role.position,
                }
                for role in guild.roles
                if not role.is_default()
            ]

        if action == "get_guild_channels":
            guild_id = payload.get("guild_id")
            guild = self.get_guild(int(guild_id)) if guild_id else None
            if not guild:
                return {"error": "Guild not found"}
            return [
                {
                    "id": str(ch.id),
                    "name": ch.name,
                    "type": ch.type.value,
                    "category": str(ch.category_id) if ch.category_id else None,
                }
                for ch in guild.channels
            ]

        if action == "get_feature":
            guild_id = int(payload.get("guild_id"))
            feature = payload.get("feature")
            if not self.db:
                return {"error": "Database unavailable"}
            # Check if feature is enabled first
            enabled_features = await self.db.get_enabled_features(guild_id)
            if feature not in enabled_features:
                return {"error": "Feature not enabled"}
            return await self._get_feature_payload(guild_id, feature)

        if action == "enable_feature":
            guild_id = int(payload.get("guild_id"))
            feature = payload.get("feature")
            if not self.db:
                return {"error": "Database unavailable"}
            await self.db.set_feature_enabled(guild_id, feature, True)
            enabled_features = await self.db.get_enabled_features(guild_id)
            return {"success": True, "enabled_features": enabled_features}

        if action == "disable_feature":
            guild_id = int(payload.get("guild_id"))
            feature = payload.get("feature")
            if not self.db:
                return {"error": "Database unavailable"}
            await self.db.set_feature_enabled(guild_id, feature, False)
            enabled_features = await self.db.get_enabled_features(guild_id)
            return {"success": True, "enabled_features": enabled_features}

        if action == "update_feature":
            guild_id = int(payload.get("guild_id"))
            feature = payload.get("feature")
            options = payload.get("options", {})
            if not self.db:
                return {"error": "Database unavailable"}

            # Settings keys that map to BIGINT columns in Postgres and need int conversion
            BIGINT_SETTINGS = {
                "rules_channel_id", "rules_message_id", "welcome_channel_id",
                "reaction_role_id", "punishment_log_id",
            }

            # Map feature options to settings keys
            mapping = {
                "rules": {
                    "channel": "rules_channel_id",
                    "message": "rules_message",
                },
                "welcome-message": {
                    "channel": "welcome_channel_id",
                    "message": "welcome_message",
                },
                "reaction-role": {
                    "messageId": "rules_message_id",
                    "channelId": "rules_channel_id",
                    "emoji": "reaction_emoji",
                    "roleId": "reaction_role_id",
                },
                "logging": {
                    "logChannel": "punishment_log_id",
                },
            }

            if feature in mapping:
                for option_key, setting_key in mapping[feature].items():
                    if option_key in options and options[option_key] is not None:
                        value = options[option_key]
                        if setting_key in BIGINT_SETTINGS:
                            try:
                                value = int(value)
                            except (TypeError, ValueError):
                                return {"error": f"Invalid value for {option_key}: must be a numeric Discord ID"}
                        await self.db.set_guild_setting(
                            guild_id, setting_key, value
                        )
                
                # --- E2E Sync: Rules ---
                if feature == "rules":
                    logger.info(f"Starting Rules E2E sync for guild {guild_id}")
                    guild = self.get_guild(guild_id)
                    if not guild:
                        try:
                            guild = await self.fetch_guild(guild_id)
                            logger.info(f"Guild {guild_id} fetched from API (not in cache)")
                        except discord.NotFound:
                            logger.error(f"Guild {guild_id} not found during Rules sync")
                            return {"error": "Guild not found"}
                    
                    if guild:
                        channel_id = options.get("channel")
                        rules_text = options.get("message")
                        logger.info(f"Sync details: channel={channel_id}, text_len={len(rules_text) if rules_text else 0}")
                        
                        if channel_id and rules_text:
                            try:
                                channel_id_int = int(channel_id)
                                channel = guild.get_channel(channel_id_int)
                                if not channel:
                                    channel = await guild.fetch_channel(channel_id_int)
                                    logger.info(f"Channel {channel_id_int} fetched from API")
                            except (discord.NotFound, discord.Forbidden, ValueError, TypeError) as e:
                                logger.error(f"Channel {channel_id} not found or inaccessible: {e}")
                                return {"error": f"Channel {channel_id} not found or inaccessible."}
                            
                            if channel:
                                perms = channel.permissions_for(guild.me)
                                if not perms.send_messages:
                                    logger.error(f"Missing send_messages perms in {channel.id}")
                                    return {"error": f"Bot lacks 'Send Messages' permission in {channel.mention}."}
                                
                                # Check if we have an existing message to edit
                                msg_id = await self.db.get_guild_setting(guild_id, "rules_message_id")
                                rules_msg = None
                                if msg_id:
                                    try:
                                        rules_msg = await channel.fetch_message(int(msg_id))
                                        logger.info(f"Found existing rules message {msg_id}")
                                    except (discord.NotFound, discord.Forbidden, ValueError, TypeError):
                                        logger.info(f"Existing rules message {msg_id} not found, will post new one")
                                        rules_msg = None
                                
                                try:
                                    if rules_msg:
                                        await rules_msg.edit(content=rules_text)
                                        logger.info(f"Updated rules message in {channel.name} for {guild.name}")
                                    else:
                                        new_msg = await channel.send(content=rules_text)
                                        await self.db.set_guild_setting(guild_id, "rules_message_id", new_msg.id)
                                        logger.info(f"Posted new rules message in {channel.name} for {guild.name}")
                                except Exception as e:
                                    logger.error(f"Failed to post/edit rules: {e}")
                                    return {"error": f"Discord error: {str(e)}"}
                        else:
                            logger.warning(f"Missing channel_id or rules_text in options: {options}")

            return await self._get_feature_payload(guild_id, feature)

        return {"error": f"Unknown action: {action}"}

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Global error handler for all slash commands."""
        logger.error(f"An error occurred in a slash command: {error}", exc_info=error)

        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"❄️ This command is on cooldown. Please try again in {error.retry_after:.2f} seconds."
        elif isinstance(error, app_commands.MissingPermissions):
            message = f"🚫 You don't have the required permissions: `{', '.join(error.missing_permissions)}`"
        elif isinstance(error, app_commands.CheckFailure):
            message = "🚫 You don't have the required permissions to use this command."
        else:
            message = "🐞 An unexpected error occurred. The developers have been notified."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            pass

def main():
    """Main entry point for the bot."""
    # Ensure only one instance of the bot is running (simple lock file check)
    lock_file = Path("bot.lock")
    if lock_file.exists():
        # Check if the process is actually running (simple PID check)
        try:
            with open(lock_file, "r") as f:
                pid = int(f.read().strip())
            import psutil
            if psutil.pid_exists(pid):
                logger.error(f"Another instance of the bot is already running (PID: {pid}).")
                # sys.exit(1)
        except (ValueError, ImportError):
            pass
    
    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))

    # Initialize SettingsManager
    settings_manager = SettingsManager()

    # Create the bot instance
    bot = MyBot(settings_manager)
    set_bot_instance(bot)

    # Setup health monitor
    health_monitor = HealthMonitor(bot)
    # asyncio.create_task(health_monitor.start()) # This would be better in setup_hook

    # Load token from config or environment
    config = load_config()
    token = config.get('DISCORD_TOKEN')

    if not token:
        logger.critical("DISCORD_TOKEN not found in config or environment.")
        sys.exit(1)

    try:
        bot.run(token)
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)
    finally:
        if lock_file.exists():
            lock_file.unlink()

if __name__ == '__main__':
    main()
