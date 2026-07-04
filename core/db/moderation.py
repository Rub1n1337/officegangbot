# core/db/moderation.py
"""Warnings, timed punishments, mod-roles, cases, temp-roles, audit (mixin for DatabaseManager)."""
import datetime
from typing import Optional, List, Dict, Any
from core.logger import logger


class _ModerationMixin:

    # -------------------------
    # Warnings
    # -------------------------

    async def add_warning(self, guild_id: int, user_id: int, reason: str,
                          moderator_id: int, moderator_name: str) -> int:
        """Adds a warning and returns its ID."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO warnings (guild_id, user_id, reason, moderator_id, moderator_name)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                guild_id, user_id, reason, moderator_id, moderator_name
            )
            return row['id']

    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Returns all warnings for a user."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, reason, moderator_id, moderator_name, created_at
                FROM warnings
                WHERE guild_id = $1 AND user_id = $2
                ORDER BY created_at ASC
                """,
                guild_id, user_id
            )
            return [dict(r) for r in rows]

    async def count_active_warnings(self, guild_id: int, user_id: int, expiry_hours: int = 0) -> int:
        """Counts a user's warnings, honouring the decay window (0 = never decay)."""
        async with self.pool.acquire() as conn:
            if expiry_hours and int(expiry_hours) > 0:
                return int(await conn.fetchval(
                    "SELECT COUNT(*) FROM warnings WHERE guild_id = $1 AND user_id = $2 "
                    "AND created_at > NOW() - ($3 || ' hours')::interval",
                    guild_id, user_id, str(int(expiry_hours)),
                ))
            return int(await conn.fetchval(
                "SELECT COUNT(*) FROM warnings WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id,
            ))

    async def get_warn_escalation(self, guild_id: int) -> Dict[str, Any]:
        """Returns the manual-warning escalation config for a guild."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT warn_escalation_enabled, warn_expiry_hours, warn_mute_at, "
                "warn_kick_at, warn_ban_at FROM guilds WHERE guild_id = $1",
                guild_id,
            )
        return {
            "enabled": bool(row["warn_escalation_enabled"]) if row else False,
            "expiry_hours": int(row["warn_expiry_hours"]) if row and row["warn_expiry_hours"] is not None else 0,
            "mute_at": int(row["warn_mute_at"]) if row and row["warn_mute_at"] is not None else 0,
            "kick_at": int(row["warn_kick_at"]) if row and row["warn_kick_at"] is not None else 0,
            "ban_at": int(row["warn_ban_at"]) if row and row["warn_ban_at"] is not None else 0,
        }

    async def set_warn_escalation(
        self, guild_id: int, enabled: bool, expiry_hours: int,
        mute_at: int, kick_at: int, ban_at: int,
    ) -> None:
        """Persists the manual-warning escalation config."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE guilds SET warn_escalation_enabled = $1, warn_expiry_hours = $2, "
                "warn_mute_at = $3, warn_kick_at = $4, warn_ban_at = $5, updated_at = NOW() "
                "WHERE guild_id = $6",
                bool(enabled), int(expiry_hours), int(mute_at), int(kick_at), int(ban_at), guild_id,
            )

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        """Clears all warnings for a user. Returns count deleted."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )
            return int(result.split()[-1])

    # -------------------------
    # Dashboard audit trail
    # -------------------------

    async def add_dashboard_audit(
        self, guild_id: int, *, actor_id: int, actor_name: str,
        action: str, target: str = None, detail: str = None,
    ) -> None:
        """Records a dashboard action (best-effort; never raises to the caller)."""
        try:
            await self.ensure_guild(guild_id)
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO dashboard_audit (guild_id, actor_id, actor_name, action, target, detail)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    guild_id, actor_id or None, (actor_name or None),
                    action, (target[:200] if target else None), (detail[:1000] if detail else None),
                )
        except Exception as e:
            logger.warning(f"Failed to write dashboard_audit for guild {guild_id}: {e}")

    async def get_dashboard_audit(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent dashboard audit entries for a guild."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, actor_id, actor_name, action, target, detail, created_at
                FROM dashboard_audit
                WHERE guild_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                guild_id, limit,
            )
            return [dict(r) for r in rows]

    async def get_recent_warnings(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent warnings across the whole guild (for the dashboard)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, reason, moderator_id, moderator_name, created_at
                FROM warnings
                WHERE guild_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                guild_id, limit
            )
            return [dict(r) for r in rows]

    async def delete_warning(self, guild_id: int, warning_id: int) -> bool:
        """Deletes a single warning by id. Returns True if a row was removed."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM warnings WHERE guild_id = $1 AND id = $2",
                guild_id, warning_id
            )
            return int(result.split()[-1]) > 0

    # -------------------------
    # Timed Punishments
    # -------------------------

    async def add_timed_punishment(self, guild_id: int, user_id: int,
                                    punishment_type: str, expires_at: datetime.datetime,
                                    reason: str = None, moderator_id: int = None) -> None:
        """Adds or replaces a timed punishment."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO timed_punishments (guild_id, user_id, punishment_type, expires_at, reason, moderator_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (guild_id, user_id) DO UPDATE
                SET punishment_type = EXCLUDED.punishment_type,
                    expires_at = EXCLUDED.expires_at,
                    reason = EXCLUDED.reason,
                    moderator_id = EXCLUDED.moderator_id,
                    created_at = NOW()
                """,
                guild_id, user_id, punishment_type, expires_at, reason, moderator_id
            )

    async def get_expired_punishments(self) -> List[Dict[str, Any]]:
        """Returns all punishments that have expired."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT guild_id, user_id, punishment_type
                FROM timed_punishments
                WHERE expires_at <= NOW()
                """
            )
            return [dict(r) for r in rows]

    async def remove_timed_punishment(self, guild_id: int, user_id: int) -> None:
        """Removes a timed punishment after it has been lifted."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM timed_punishments WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )

    async def get_timed_punishments(self, guild_id: int) -> List[Dict[str, Any]]:
        """Returns all active timed punishments for a guild."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, punishment_type, expires_at, reason
                FROM timed_punishments
                WHERE guild_id = $1
                ORDER BY expires_at ASC
                """,
                guild_id
            )
            return [dict(r) for r in rows]

    # -------------------------
    # Mod Roles
    # -------------------------

    async def set_mod_role(self, guild_id: int, role_id: int, role_type: str) -> None:
        """Adds a role to mod_roles table for a specific permission type."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mod_roles (guild_id, role_id, role_type)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, role_id, role_type) DO NOTHING
                """,
                guild_id, role_id, role_type
            )

    async def remove_mod_role(self, guild_id: int, role_type: str, role_id: int = None) -> None:
        """Removes roles from mod_roles. If role_id is provided, removes specific role; otherwise removes all roles of that type."""
        async with self.pool.acquire() as conn:
            if role_id:
                await conn.execute(
                    "DELETE FROM mod_roles WHERE guild_id = $1 AND role_type = $2 AND role_id = $3",
                    guild_id, role_type, role_id
                )
            else:
                await conn.execute(
                    "DELETE FROM mod_roles WHERE guild_id = $1 AND role_type = $2",
                    guild_id, role_type
                )

    async def get_mod_roles(self, guild_id: int) -> Dict[str, List[int]]:
        """Returns all mod roles for a guild grouped by type."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT role_id, role_type FROM mod_roles WHERE guild_id = $1",
                guild_id
            )
            result = {}
            for r in rows:
                rtype = r['role_type']
                if rtype not in result:
                    result[rtype] = []
                result[rtype].append(r['role_id'])
            return result

    # --- Moderation cases --------------------------------------------------

    async def add_mod_case(
        self,
        guild_id: int,
        action: str,
        target_id: Optional[int],
        target_name: Optional[str],
        moderator_id: Optional[int],
        moderator_name: Optional[str],
        reason: Optional[str],
    ) -> int:
        """Records a moderation action with the next per-guild case number and
        returns it. A per-guild advisory lock serializes number allocation so two
        concurrent actions can't collide on the UNIQUE (guild_id, case_number)."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock($1)", guild_id)
                row = await conn.fetchrow(
                    "INSERT INTO mod_cases "
                    "(guild_id, case_number, action, target_id, target_name, "
                    " moderator_id, moderator_name, reason) "
                    "VALUES ($1, (SELECT COALESCE(MAX(case_number), 0) + 1 FROM mod_cases WHERE guild_id = $1), "
                    "$2, $3, $4, $5, $6, $7) RETURNING case_number",
                    guild_id, str(action)[:100],
                    int(target_id) if target_id else None,
                    str(target_name)[:100] if target_name else None,
                    int(moderator_id) if moderator_id else None,
                    str(moderator_name)[:100] if moderator_name else None,
                    str(reason)[:1000] if reason else None,
                )
        return row["case_number"]

    async def get_mod_case(self, guild_id: int, case_number: int) -> Optional[Dict[str, Any]]:
        """Returns a single case by its per-guild number, or None."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT case_number, action, target_id, target_name, moderator_id, "
                "moderator_name, reason, created_at FROM mod_cases "
                "WHERE guild_id = $1 AND case_number = $2",
                guild_id, int(case_number),
            )
        return dict(row) if row else None

    async def get_mod_cases(
        self, guild_id: int, target_id: Optional[int] = None, limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Returns recent cases for a guild, optionally filtered to one target,
        newest first."""
        limit = max(1, min(int(limit), 100))
        async with self.pool.acquire() as conn:
            if target_id is not None:
                rows = await conn.fetch(
                    "SELECT case_number, action, target_id, target_name, moderator_name, "
                    "reason, created_at FROM mod_cases WHERE guild_id = $1 AND target_id = $2 "
                    "ORDER BY case_number DESC LIMIT $3",
                    guild_id, int(target_id), limit,
                )
            else:
                rows = await conn.fetch(
                    "SELECT case_number, action, target_id, target_name, moderator_name, "
                    "reason, created_at FROM mod_cases WHERE guild_id = $1 "
                    "ORDER BY case_number DESC LIMIT $2",
                    guild_id, limit,
                )
        return [dict(r) for r in rows]

    # --- Temporary roles ---------------------------------------------------

    async def add_temp_role(
        self, guild_id: int, user_id: int, role_id: int, expires_at, moderator_id: Optional[int]
    ) -> None:
        """Adds (or reschedules) a temporary role assignment."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO temp_roles (guild_id, user_id, role_id, expires_at, moderator_id) "
                "VALUES ($1, $2, $3, $4, $5) "
                "ON CONFLICT (guild_id, user_id, role_id) DO UPDATE "
                "SET expires_at = EXCLUDED.expires_at, moderator_id = EXCLUDED.moderator_id",
                guild_id, int(user_id), int(role_id), expires_at,
                int(moderator_id) if moderator_id else None,
            )

    async def get_expired_temp_roles(self) -> List[Dict[str, Any]]:
        """Returns all temp-role assignments whose expiry has passed."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT guild_id, user_id, role_id FROM temp_roles WHERE expires_at <= NOW()"
            )
        return [dict(r) for r in rows]

    async def remove_temp_role(self, guild_id: int, user_id: int, role_id: int) -> None:
        """Removes a temp-role record (after it expires or is lifted)."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM temp_roles WHERE guild_id = $1 AND user_id = $2 AND role_id = $3",
                guild_id, int(user_id), int(role_id),
            )

    async def get_temp_roles(self, guild_id: int, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns active temp-role assignments for a guild (optionally one user)."""
        async with self.pool.acquire() as conn:
            if user_id is not None:
                rows = await conn.fetch(
                    "SELECT user_id, role_id, expires_at, moderator_id FROM temp_roles "
                    "WHERE guild_id = $1 AND user_id = $2 ORDER BY expires_at",
                    guild_id, int(user_id),
                )
            else:
                rows = await conn.fetch(
                    "SELECT user_id, role_id, expires_at, moderator_id FROM temp_roles "
                    "WHERE guild_id = $1 ORDER BY expires_at",
                    guild_id,
                )
        return [dict(r) for r in rows]
