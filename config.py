# config.py

"""
This module handles loading configuration for the bot.
Its only job is to securely load the Discord Bot Token.
-------------------------------------------------------------
How it works:
- It uses the `dotenv` library to load variables from a `.env` file in your project folder.
- This is the standard, secure way to handle secret keys. You should NEVER write
  your token directly in the code.

What you need to do:
1. Create a file named `.env` in the same directory as this file.
2. Inside `.env`, add this line:
   DISCORD_TOKEN=your_super_secret_bot_token_here
3. Make sure the `python-dotenv` library is installed (`pip install python-dotenv`).
"""

import os
from dotenv import load_dotenv
from core.logger import logger

def load_config() -> dict:
    """
    Loads environment variables from .env and validates required fields.
    Returns a config dict. Logs warnings if variables are missing.
    """
    load_dotenv()
    config = {}
    config['DISCORD_TOKEN'] = os.getenv("DISCORD_TOKEN")
    if not config['DISCORD_TOKEN']:
        logger.critical("DISCORD_TOKEN not found in environment variables. Please add it to your .env file.")
        raise RuntimeError("DISCORD_TOKEN not found in environment variables. Please add it to your .env file.")
    config['OWNER_ID'] = int(os.getenv("BOT_OWNER_ID", "0"))
    config['APPLICATION_ID'] = int(os.getenv("APPLICATION_ID", "0"))
    return config

# You can add other configuration variables here as well.
# For example:
# OWNER_ID = os.getenv('BOT_OWNER_ID')