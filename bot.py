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
from core.logger import logger
from config import load_config
# from core.webserver import keep_alive
from core.settings_manager import SettingsManager
from core.health_monitor import HealthMonitor
from core.db_manager import DatabaseManager
from cogs.utils import reply

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

        # Set up the global error handler for slash commands
        self.tree.on_error = self.on_app_command_error

    async def close(self):
        if hasattr(self, 'db') and self.db:
            await self.db.close()
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
        except discord.HTTPException as e:
            logger.error(f"Failed to send slash command error message: {e}")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global error handler for all prefix commands."""
        if getattr(ctx, 'error_handled', False):
            return

        # Default error message
        message = "🐞 An unexpected error occurred with a prefix command. The developers have been notified."

        # Handle specific, common errors with user-friendly messages
        if isinstance(error, commands.CommandNotFound):
            return  # Don't respond to commands that don't exist
        elif isinstance(error, commands.CommandOnCooldown):
            message = f"❄️ This command is on cooldown. Please try again in {error.retry_after:.2f} seconds."
        elif isinstance(error, (commands.CheckFailure, commands.MissingPermissions)):
            message = "🚫 You don't have the required permissions to use this command."
        elif isinstance(error, commands.UserInputError):
            message = f"🤔 Invalid input. Check the help for `{ctx.prefix}{ctx.command.name}` for correct usage."
        elif isinstance(error, commands.HybridCommandError):
            # Log the detailed hybrid error but show a generic message to the user
            logger.error(f"Hybrid command '{ctx.command.name}' failed. Original error: {error.original}", exc_info=error.original)
        else:
            # For any other errors, log them for debugging
            logger.error(f"An unhandled error occurred in a prefix command: {error}", exc_info=error)

        # Use the robust reply function to send the error message.
        # This prevents the error handler from crashing and causing a spam loop.
        try:
            # `ephemeral` is safely ignored by the `reply` function for prefix commands.
            await reply(ctx, content=message, ephemeral=True)
        except Exception as e:
            logger.critical(f"FATAL: The global error handler itself failed to send a message.", exc_info=e)

async def main():
    """Initializes and runs the bot, ensuring only one instance is running."""
    # Set up asyncio exception handler
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(lambda loop, ctx: logger.error(f"Unhandled asyncio exception: {ctx}"))

    LOCK_FILE_PATH = os.path.join("data", "bot.lock")

    if os.path.exists(LOCK_FILE_PATH):
        logger.critical(f"Lock file found at {LOCK_FILE_PATH}. Another instance may be running. Aborting.")
        sys.exit(1)

    # Set up logging first
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.INFO)
    discord_logger.propagate = False
    for handler in logger.handlers:
        discord_logger.addHandler(handler)

    # Load config and environment variables
    config = load_config()

    # Initialize components
    settings_manager = SettingsManager()
    bot = MyBot(settings_manager=settings_manager)
    health_monitor = HealthMonitor(bot)
    bot.health_monitor = health_monitor
    health_monitor.start()

    # Set bot instance for API server
    from api_server import set_bot_instance
    set_bot_instance(bot)

    try:
        # Create the lock file
        with open(LOCK_FILE_PATH, 'w') as f:
            f.write(str(os.getpid()))

        if not config['DISCORD_TOKEN']:
            logger.critical("DISCORD_TOKEN is not set. The bot cannot start.")
            sys.exit(1)

        async with bot:
            await bot.start(config['DISCORD_TOKEN'])

    except KeyboardInterrupt:
        logger.info("Shutdown initiated by user. Cleaning up...")
    except Exception as e:
        logger.critical(f"An unexpected error occurred during bot runtime: {e}", exc_info=True)
    finally:
        # Shutdown/cleanup hooks
        if hasattr(bot, 'health_monitor'):
            if health_monitor.running:
                health_monitor.stop()
        # Clean up bot and other components
        if 'bot' in locals() and bot and not bot.is_closed():
            await bot.close()
        
        # Clean up the lock file
        if os.path.exists(LOCK_FILE_PATH):
            os.remove(LOCK_FILE_PATH)
            
        logger.info("Bot shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown initiated by user from console.")
    except Exception as e:
        logger.critical(f"A fatal error occurred in the main execution block: {e}", exc_info=True)
        sys.exit(1)
