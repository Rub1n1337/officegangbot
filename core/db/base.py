# core/db/base.py
"""Connection pool, schema init and shared helpers (mixin for DatabaseManager)."""
import asyncpg
import os
from typing import Optional, List, Dict, Any
from core.logger import logger


class _BaseDB:
    """
    Async PostgreSQL manager with connection pooling via asyncpg.
    Initialize once at bot startup via connect(), close pool via close().
    """

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        # Per-guild locale cache (locale changes rarely; invalidated on set_locale).
        self._locale_cache: Dict[int, str] = {}
        # Per-guild enabled-features cache. get_enabled_features is called on
        # every message (automod/filter/levels), so hitting Postgres each time
        # would hammer the DB on busy servers. Invalidated on set_feature_enabled.
        self._enabled_features_cache: Dict[int, List[str]] = {}
        # Per-guild AutoMod content-filter config (read on every message when
        # AutoMod is on). Invalidated on set_automod_config.
        self._automod_cache: Dict[int, Dict[str, Any]] = {}
        # Per-guild Levels config (voice XP, multipliers, prestige/season). Read
        # on every XP award; invalidated on set_levels_config / role-mult / season.
        self._levels_cache: Dict[int, Dict[str, Any]] = {}

    async def connect(self) -> None:
        """Creates the asyncpg connection pool. Call this in bot.setup_hook()."""
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise ValueError("DATABASE_URL environment variable is not set.")
        try:
            self._pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            logger.info("PostgreSQL connection pool created successfully.")
            await self._init_schema()
        except Exception as e:
            logger.critical(f"Failed to connect to PostgreSQL: {e}", exc_info=True)
            raise

    async def close(self) -> None:
        """Closes the connection pool. Call this in bot.close()."""
        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL connection pool closed.")

    async def _init_schema(self) -> None:
        """Runs the SQL schema initialization script."""
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'init_db.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        async with self._pool.acquire() as conn:
            await conn.execute(schema_sql)
        logger.info("Database schema initialized.")

    @property
    def pool(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("DatabaseManager is not connected. Call connect() first.")
        return self._pool

    # -------------------------
    # Guild settings
    # -------------------------

    async def ensure_guild(self, guild_id: int) -> None:
        """Inserts guild row if it doesn't exist (upsert)."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guilds (guild_id) VALUES ($1)
                ON CONFLICT (guild_id) DO NOTHING
                """,
                guild_id
            )
