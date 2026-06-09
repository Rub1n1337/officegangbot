# core/settings_manager.py

import json
import os
import asyncio
from core.logger import logger

class SettingsManager:
    """
    Singleton manager for per-guild settings. Uses an in-memory dict with atomic async file saves.
    Not process-safe: if you run multiple bot processes/shards, use a database or IPC.
    """
    _instance: 'SettingsManager' = None

    def __new__(cls, *args, **kwargs) -> 'SettingsManager':
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, file_path: str = "data/guild_settings.json") -> None:
        if hasattr(self, '_initialized'):
            return
        self.file_path: str = file_path
        self._write_lock: asyncio.Lock = asyncio.Lock()
        self.data: dict = self._load()
        self._initialized = True

    def _load(self) -> dict:
        """Loads settings from the JSON file, creating the directory if needed. Surfaces errors."""
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        except OSError as e:
            logger.critical(f"Could not create data directory: {e}", exc_info=True)
            raise
        if not os.path.exists(self.file_path):
            logger.info(f"Settings file not found at '{self.file_path}'. A new one will be created.")
            return {}
        try:
            with open(self.file_path, "r", encoding='utf-8') as f:
                loaded_data = json.load(f)
                logger.info(f"Successfully loaded settings for {len(loaded_data)} guilds.")
                return loaded_data
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading settings from '{self.file_path}': {e}. Starting with empty settings.", exc_info=True)
            return {}

    async def _save(self) -> None:
        """Atomically saves the current settings to the JSON file. Surfaces errors to logs."""
        async with self._write_lock:
            try:
                os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
                temp_file_path = self.file_path + ".tmp"
                with open(temp_file_path, "w", encoding='utf-8') as f:
                    json.dump(self.data, f, indent=4)
                os.replace(temp_file_path, self.file_path)
            except IOError as e:
                logger.error(f"Could not save settings to file: {e}", exc_info=True)

    def get_guild_settings(self, guild_id: int) -> dict:
        """Returns the entire settings dictionary for a guild."""
        return self.data.get(str(guild_id), {})

    def get_setting(self, guild_id: int, key: str, default=None):
        """Returns a single setting value for a guild."""
        guild_settings = self.get_guild_settings(guild_id)
        return guild_settings.get(key, default)

    async def update_setting(self, guild_id: int, key: str, value) -> None:
        """Updates a single setting for a guild and saves."""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.data:
            self.data[guild_id_str] = {}
        self.data[guild_id_str][key] = value
        await self._save()

    async def save_settings(self) -> None:
        """Public method to explicitly trigger a save."""
        await self._save()

    async def update_guild_settings(self, guild_id: int, new_settings: dict) -> None:
        """Updates multiple settings for a guild at once."""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.data:
            self.data[guild_id_str] = {}
        self.data[guild_id_str].update(new_settings)
        await self._save()

    async def remove_guild_settings(self, guild_id: int) -> None:
        """Removes all settings for a guild."""
        guild_id_str = str(guild_id)
        if guild_id_str in self.data:
            del self.data[guild_id_str]
            await self._save()
            logger.info(f"Removed all settings for guild {guild_id}.")
