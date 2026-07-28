# core/db/backups.py
"""Per-guild config backups (mixin for DatabaseManager). Each backup is a full
JSON snapshot of the guild's feature config; the newest ``_BACKUP_KEEP`` are
retained, older ones are pruned."""
import json
from typing import Any, Dict, List, Optional


class _BackupsMixin:
    _BACKUP_KEEP = 14

    async def create_config_backup(self, guild_id: int, kind: str, data: dict) -> Optional[int]:
        """Store a snapshot and prune to the retention limit. Returns the new id,
        or None when the snapshot is identical to the most recent one (so a
        no-change day doesn't pile up duplicate backups)."""
        await self.ensure_guild(guild_id)
        payload = json.dumps(data, sort_keys=True)
        async with self.pool.acquire() as conn:
            latest = await conn.fetchval(
                "SELECT data::text FROM config_backups WHERE guild_id = $1 ORDER BY created_at DESC LIMIT 1",
                guild_id,
            )
            if latest is not None and json.dumps(json.loads(latest), sort_keys=True) == payload:
                return None
            new_id = await conn.fetchval(
                "INSERT INTO config_backups (guild_id, kind, data) VALUES ($1, $2, $3::jsonb) RETURNING id",
                guild_id, kind, payload,
            )
            await conn.execute(
                """
                DELETE FROM config_backups
                WHERE guild_id = $1 AND id NOT IN (
                    SELECT id FROM config_backups WHERE guild_id = $1
                    ORDER BY created_at DESC LIMIT $2
                )
                """,
                guild_id, self._BACKUP_KEEP,
            )
        return new_id

    async def list_config_backups(self, guild_id: int) -> List[Dict[str, Any]]:
        """Backup metadata (no data) newest-first."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, kind, created_at FROM config_backups WHERE guild_id = $1 ORDER BY created_at DESC",
                guild_id,
            )
        return [
            {"id": r["id"], "kind": r["kind"], "createdAt": r["created_at"].isoformat()}
            for r in rows
        ]

    async def get_config_backup(self, guild_id: int, backup_id: int) -> Optional[dict]:
        """The full snapshot data for one backup, or None."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data::text AS data FROM config_backups WHERE guild_id = $1 AND id = $2",
                guild_id, backup_id,
            )
        return json.loads(row["data"]) if row else None
