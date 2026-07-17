"""check_xp_cooldown must distinguish "not on cooldown" from "Redis errored".

Returning False on error meant every message during a Redis blip granted XP
with no cooldown — the leveling cog now falls back to its in-memory cooldown
only when this returns None, so the None-on-error contract is load-bearing.
The suite drives coroutines with asyncio.run (no pytest-asyncio), like
tests/test_integration.py.
"""
import asyncio

from core.redis_manager import RedisManager


class _FakeRedis:
    """Stands in for aioredis; `set` returns a canned value or raises."""

    def __init__(self, result=None, boom=False):
        self._result = result
        self._boom = boom
        self.calls = 0

    async def set(self, *args, **kwargs):
        self.calls += 1
        if self._boom:
            raise ConnectionError("redis down")
        return self._result


def _cooldown(result=None, boom=False):
    mgr = RedisManager()
    mgr._redis = _FakeRedis(result=result, boom=boom)
    return asyncio.run(mgr.check_xp_cooldown(1, 2))


def test_first_message_is_not_on_cooldown():
    # SET NX succeeds -> redis returns "OK" -> key did not exist -> not on cooldown.
    assert _cooldown(result="OK") is False


def test_repeat_message_is_on_cooldown():
    # SET NX fails because the key exists -> redis returns None -> on cooldown.
    assert _cooldown(result=None) is True


def test_redis_error_returns_none_not_false():
    # The bug: this used to return False ("not on cooldown"), so a Redis outage
    # removed the cooldown and let XP be farmed. None tells the cog to fall back.
    assert _cooldown(boom=True) is None
