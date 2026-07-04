# core/db/levels.py
"""XP, levels, multipliers, prestige and seasons (mixin for DatabaseManager)."""
from typing import List, Dict, Any
from core.logger import logger


class _LevelsMixin:

    # -------------------------
    # XP / Levels
    # -------------------------

    async def get_user_xp(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Returns XP data for a user."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT xp, level, display_name, prestige FROM users_xp WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )
            if row:
                return dict(row)
            return {'xp': 0, 'level': 0, 'display_name': None, 'prestige': 0}

    async def upsert_user_xp(self, guild_id: int, user_id: int, xp: int, level: int, display_name: str) -> None:
        """Inserts or updates XP data for a user."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users_xp (guild_id, user_id, xp, level, display_name, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (guild_id, user_id) DO UPDATE
                SET xp = EXCLUDED.xp,
                    level = EXCLUDED.level,
                    display_name = EXCLUDED.display_name,
                    updated_at = NOW()
                """,
                guild_id, user_id, xp, level, display_name
            )

    async def bulk_upsert_xp(self, records: List[Dict[str, Any]]) -> None:
        """
        Bulk upsert XP records for multiple users at once.
        records: list of dicts with keys: guild_id, user_id, xp, level, display_name
        """
        if not records:
            return
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO users_xp (guild_id, user_id, xp, level, display_name, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (guild_id, user_id) DO UPDATE
                SET xp = EXCLUDED.xp,
                    level = EXCLUDED.level,
                    display_name = EXCLUDED.display_name,
                    updated_at = NOW()
                """,
                [(r['guild_id'], r['user_id'], r['xp'], r['level'], r['display_name']) for r in records]
            )
        logger.info(f"Bulk XP upsert: {len(records)} records.")

    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns top N users by XP for a guild."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, xp, level, display_name, prestige
                FROM users_xp
                WHERE guild_id = $1
                ORDER BY prestige DESC, xp DESC
                LIMIT $2
                """,
                guild_id, limit
            )
            return [dict(r) for r in rows]

    # -------------------------
    # Level Roles
    # -------------------------

    async def set_level_role(self, guild_id: int, level: int, role_id: int) -> None:
        """Sets a role reward for a specific level."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO level_roles (guild_id, level, role_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, level) DO UPDATE SET role_id = EXCLUDED.role_id
                """,
                guild_id, level, role_id
            )

    async def get_level_roles(self, guild_id: int) -> Dict[int, int]:
        """Returns {level: role_id} mapping for a guild."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT level, role_id FROM level_roles WHERE guild_id = $1",
                guild_id
            )
            return {r['level']: r['role_id'] for r in rows}

    async def remove_level_role(self, guild_id: int, level: int) -> None:
        """Removes the role reward configured for a specific level."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM level_roles WHERE guild_id = $1 AND level = $2",
                guild_id, level
            )

    # -------------------------
    # Levels config (voice XP, multipliers, prestige, seasons)
    # -------------------------

    async def get_levels_config(self, guild_id: int) -> Dict[str, Any]:
        """Returns the guild's leveling config (cached, read on every XP award):
        voice XP, global multiplier, prestige threshold, season number and the
        per-role multiplier map {role_id: multiplier}."""
        cached = self._levels_cache.get(guild_id)
        if cached is not None:
            return cached
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT levels_voice_xp_enabled, levels_voice_xp_per_min, levels_xp_multiplier, "
                "levels_prestige_level, levels_season FROM guilds WHERE guild_id = $1",
                guild_id,
            )
            mult_rows = await conn.fetch(
                "SELECT role_id, multiplier FROM level_multiplier_roles WHERE guild_id = $1",
                guild_id,
            )
        config = {
            "voice_xp_enabled": bool(row["levels_voice_xp_enabled"]) if row else False,
            "voice_xp_per_min": int(row["levels_voice_xp_per_min"]) if row and row["levels_voice_xp_per_min"] is not None else 5,
            "xp_multiplier": float(row["levels_xp_multiplier"]) if row and row["levels_xp_multiplier"] is not None else 1.0,
            "prestige_level": int(row["levels_prestige_level"]) if row and row["levels_prestige_level"] is not None else 100,
            "season": int(row["levels_season"]) if row and row["levels_season"] is not None else 1,
            "role_multipliers": {int(r["role_id"]): float(r["multiplier"]) for r in mult_rows},
        }
        self._levels_cache[guild_id] = config
        return config

    async def set_levels_config(
        self,
        guild_id: int,
        voice_xp_enabled: bool,
        voice_xp_per_min: int,
        xp_multiplier: float,
        prestige_level: int,
    ) -> None:
        """Persists the leveling config columns and invalidates the cache."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE guilds SET levels_voice_xp_enabled = $1, levels_voice_xp_per_min = $2, "
                "levels_xp_multiplier = $3, levels_prestige_level = $4, updated_at = NOW() "
                "WHERE guild_id = $5",
                bool(voice_xp_enabled), int(voice_xp_per_min), float(xp_multiplier),
                int(prestige_level), guild_id,
            )
        self._levels_cache.pop(guild_id, None)

    async def replace_level_multiplier_roles(self, guild_id: int, roles: List[Dict[str, Any]]) -> None:
        """Replaces the per-role XP multipliers for a guild (sanitized upstream)."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM level_multiplier_roles WHERE guild_id = $1", guild_id)
                for r in roles:
                    await conn.execute(
                        "INSERT INTO level_multiplier_roles (guild_id, role_id, multiplier) "
                        "VALUES ($1, $2, $3) ON CONFLICT (guild_id, role_id) DO UPDATE "
                        "SET multiplier = EXCLUDED.multiplier",
                        guild_id, int(r["role_id"]), float(r["multiplier"]),
                    )
        self._levels_cache.pop(guild_id, None)

    async def prestige_user(self, guild_id: int, user_id: int) -> int:
        """Resets a user's season XP/level to 0 and increments their prestige.
        Returns the new prestige count (0 if the user had no XP row)."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE users_xp SET xp = 0, level = 0, prestige = prestige + 1, updated_at = NOW() "
                "WHERE guild_id = $1 AND user_id = $2 RETURNING prestige",
                guild_id, user_id,
            )
        return int(row["prestige"]) if row else 0

    async def reset_season(self, guild_id: int, standings: str) -> int:
        """Archives the current standings (a JSON string), zeroes every member's
        season XP/level (prestige preserved) and bumps the season number. Returns
        the new season number."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                cur = await conn.fetchval("SELECT levels_season FROM guilds WHERE guild_id = $1", guild_id)
                season = int(cur) if cur is not None else 1
                await conn.execute(
                    "INSERT INTO level_seasons (guild_id, season_number, standings) VALUES ($1, $2, $3::jsonb)",
                    guild_id, season, standings,
                )
                await conn.execute("UPDATE users_xp SET xp = 0, level = 0, updated_at = NOW() WHERE guild_id = $1", guild_id)
                new_season = season + 1
                await conn.execute(
                    "UPDATE guilds SET levels_season = $1, updated_at = NOW() WHERE guild_id = $2",
                    new_season, guild_id,
                )
        self._levels_cache.pop(guild_id, None)
        return new_season

    async def get_seasons(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns archived past seasons (most recent first)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT season_number, ended_at, standings FROM level_seasons "
                "WHERE guild_id = $1 ORDER BY season_number DESC LIMIT $2",
                guild_id, max(1, min(int(limit), 50)),
            )
        return [dict(r) for r in rows]
