"""Unit tests for config-backup create/dedup/prune (core.db.backups) using a
fake asyncpg connection."""
import asyncio
import json

from core.db.backups import _BackupsMixin


class _FakeConn:
    """Emulates just enough of asyncpg for create_config_backup: an in-memory
    list of backups (newest last) with fetchval/execute."""

    def __init__(self):
        self.rows = []  # list of {id, data(str)}
        self._next = 1

    async def fetchval(self, query, *args):
        q = " ".join(query.split())
        if q.startswith("SELECT data::text FROM config_backups"):
            return self.rows[-1]["data"] if self.rows else None
        if q.startswith("INSERT INTO config_backups"):
            _guild, _kind, payload = args
            rid = self._next
            self._next += 1
            self.rows.append({"id": rid, "data": payload})
            return rid
        return None

    async def execute(self, query, *args):
        # the prune DELETE — keep only the newest `keep`
        if "DELETE FROM config_backups" in query:
            keep = args[1]
            self.rows = self.rows[-keep:]

    def transaction(self):  # unused here
        raise NotImplementedError


class _Acquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return _Acquire(self._conn)


class _DB(_BackupsMixin):
    _BACKUP_KEEP = 3

    def __init__(self):
        self.conn = _FakeConn()
        self.pool = _FakePool(self.conn)

    async def ensure_guild(self, guild_id):
        pass


def _run(coro):
    return asyncio.run(coro)


def test_create_returns_id_and_stores():
    db = _DB()
    bid = _run(db.create_config_backup(1, "manual", {"a": 1}))
    assert bid == 1
    assert len(db.conn.rows) == 1


def test_identical_snapshot_is_deduped():
    db = _DB()
    _run(db.create_config_backup(1, "auto", {"a": 1, "b": 2}))
    # key order differs but content is identical -> skipped
    again = _run(db.create_config_backup(1, "auto", {"b": 2, "a": 1}))
    assert again is None
    assert len(db.conn.rows) == 1


def test_prune_keeps_only_newest():
    db = _DB()
    for i in range(6):
        _run(db.create_config_backup(1, "auto", {"v": i}))
    assert len(db.conn.rows) == db._BACKUP_KEEP
    assert json.loads(db.conn.rows[-1]["data"])["v"] == 5
