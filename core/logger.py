# core/logger.py

"""
This module sets up a centralized, advanced logger for the entire bot.
-------------------------------------------------------------
Why use a logger instead of `print()`?
- Levels: You can have different log levels (INFO, WARNING, ERROR, CRITICAL).
  You can choose to only show warnings and errors in production.
- Formatting: Logs are automatically timestamped and formatted, making them easy to read.
- Output to File: It can write logs to both the console and a file simultaneously,
  so you have a permanent record of what the bot was doing.
- Centralized: All files can import and use the same logger instance, ensuring
  consistent logging across the entire application.
"""

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

# --- Configuration ---
LOG_DIRECTORY = "data"
LOG_FILE_NAME = "bot.log"
LOG_LEVEL = os.getenv("BOT_LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL, logging.INFO)
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

def setup_logger() -> logging.Logger:
    """Sets up and returns a centralized logger with rotation and environment-configurable log level."""
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)

    logger = logging.getLogger("DiscordBot")
    logger.setLevel(LOG_LEVEL)

    log_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)

    # Rotating File Handler
    log_file_path = os.path.join(LOG_DIRECTORY, LOG_FILE_NAME)
    file_handler = RotatingFileHandler(log_file_path, mode='a', encoding='utf-8', maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    file_handler.setFormatter(log_format)

    # Prevent duplicate handlers
    if not logger.hasHandlers():
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger

logger: logging.Logger = setup_logger()